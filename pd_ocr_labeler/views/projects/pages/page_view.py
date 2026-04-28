from __future__ import annotations

import asyncio
import contextlib
import logging

from nicegui import events, ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel
from ....viewmodels.project.project_state_view_model import ProjectStateViewModel
from ...callbacks import PageActionCallbacks
from .content import ContentArea
from .page_actions import PageActions

logger = logging.getLogger(__name__)

PageActionEvent = events.ClickEventArguments | None


class PageView:  # pragma: no cover - UI wrapper file
    """Page-layer view: page actions and page content."""

    @classmethod
    def from_project(
        cls,
        project_view_model: ProjectStateViewModel,
        on_request_refresh=None,
    ) -> PageView | None:
        """Create a PageView from project state."""
        project_state = getattr(project_view_model, "_project_state", None)
        if project_state is None:
            logger.error("Cannot create PageView - no project state available")
            return None

        page_state_view_model = PageStateViewModel(project_state)
        return cls(
            project_view_model,
            page_state_view_model,
            on_request_refresh=on_request_refresh,
        )

    def __init__(
        self,
        project_view_model: ProjectStateViewModel,
        page_state_view_model: PageStateViewModel,
        on_request_refresh=None,
    ):
        self.project_view_model = project_view_model
        self.page_state_view_model = page_state_view_model
        self._on_request_refresh = on_request_refresh

        self.page_action_callbacks = PageActionCallbacks(
            save_page=self._save_page_async,
            save_project=self._save_project_async,
            load_page=self._load_page_async,
            refine_bboxes=self._refine_bboxes_async,
            expand_refine_bboxes=self._expand_refine_bboxes_async,
            reload_ocr=self._reload_ocr_async,
            reload_ocr_edited=self._reload_ocr_edited_async,
            rematch_gt=self._rematch_gt_async,
        )

        self.page_actions: PageActions | None = None
        self.content: ContentArea | None = None
        self.root = None

    def build(self):
        self.page_actions = PageActions(
            self.project_view_model,
            self.page_state_view_model,
            on_save_page=self.page_action_callbacks.save_page
            if self.page_action_callbacks
            else None,
            on_save_project=self.page_action_callbacks.save_project
            if self.page_action_callbacks
            else None,
            on_load_page=self.page_action_callbacks.load_page
            if self.page_action_callbacks
            else None,
            on_reload_ocr=self.page_action_callbacks.reload_ocr
            if self.page_action_callbacks
            else None,
            on_reload_ocr_edited=self.page_action_callbacks.reload_ocr_edited
            if self.page_action_callbacks
            else None,
            on_rematch_gt=self.page_action_callbacks.rematch_gt
            if self.page_action_callbacks
            else None,
        )
        self.page_actions.build()

        self.content = ContentArea(
            self.page_state_view_model, self.page_action_callbacks
        )
        self.root = self.content.build()
        return self.root

    def set_page_metadata(self, name: str) -> None:
        """Set page-level metadata displayed by page actions."""
        if self.page_actions:
            self.page_actions.set_page_metadata(name)

    def refresh(
        self,
        loading: bool,
        busy: bool,
    ):
        """Refresh page-layer content only."""
        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = self.project_view_model.current_page_index
        image_name = ""
        project_state = getattr(self.project_view_model, "_project_state", None)
        project = getattr(project_state, "project", None)
        if project is not None and hasattr(project, "image_paths"):
            if 0 <= current_index < len(project.image_paths):
                image_name = project.image_paths[current_index].name

        page = None
        if not loading and project_state is not None and project is not None:
            if 0 <= current_index < len(project.pages):
                page = project.pages[current_index]
            self._sync_text_tabs(page)

        total = self.project_view_model.page_total
        display_name = image_name or "(no page)" if total else "(no page)"
        self.set_page_metadata(display_name)
        if self.page_actions:
            self.page_actions.sync_control_states()
        logger.debug(
            "Current page state - index: %d, image_name: %s, total_pages: %d, page_loaded: %s",
            current_index,
            image_name,
            total,
            page is not None,
        )

        if self.content and self.content.root:
            if self.content.splitter and self.content.page_spinner:
                if busy:
                    self.content.page_spinner.classes(add="hidden")
                    logger.debug("Busy overlay active; leaving content visible")
                elif loading:
                    self.content.splitter.classes(add="hidden")
                    self.content.page_spinner.classes(remove="hidden")
                    logger.debug("Showing page spinner, hiding content splitter")
                else:
                    self.content.splitter.classes(remove="hidden")
                    self.content.page_spinner.classes(add="hidden")
                    logger.debug("Showing content splitter, hiding page spinner")
                    self._show_images()

    def prepare_navigation_transition(self, busy: bool):
        """Prepare page content for navigation transitions."""
        logger.debug("Preparing page-layer transition state")
        if self.content and self.content.splitter and self.content.page_spinner:
            if busy:
                self.content.page_spinner.classes(add="hidden")
                logger.debug("Busy overlay active; keeping inline page spinner hidden")
            else:
                self.content.splitter.classes(add="hidden")
                self.content.page_spinner.classes(remove="hidden")
                logger.debug("Hid content splitter and showed page spinner")

        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():
                if img:
                    img.set_visibility(False)
                    logger.debug("Hidden image: %s", name)

        if (
            self.content
            and hasattr(self.content, "text_tabs")
            and getattr(self.content.text_tabs, "word_match_view", None)
        ):
            self.content.text_tabs.word_match_view.clear()
            logger.debug("Cleared word matches for navigation transition")

    def _sync_text_tabs(self, page):
        """Synchronize text tabs with the current page."""
        if self.content and getattr(self.content, "text_tabs", None):
            text_tabs = self.content.text_tabs
            if text_tabs.page_state is not None:
                text_tabs.page_state.current_page = page
            text_tabs.model.update()
            text_tabs._update_text_editors()
            text_tabs.update_word_matches(page)

    def _show_images(self):
        """Show images after navigation completes."""
        logger.debug("Showing images after navigation")
        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():
                if img:
                    img.set_visibility(True)
                    logger.debug("Shown image: %s", name)

    def _notify(self, message: str, type_: str = "info"):
        """Route notifications through per-session queue with UI fallback."""
        app_state_model = getattr(self.project_view_model, "_app_state_model", None)
        app_state = getattr(app_state_model, "_app_state", None)
        if app_state is not None:
            app_state.queue_notification(message, type_)
            return

        ui.notify(message, type=type_)

    @contextlib.asynccontextmanager
    async def _action_context(self, message: str, show_spinner: bool = False):
        """Context manager to show notifications and busy overlay during actions."""
        logger.debug(
            "PageView action context: %s (show_spinner=%s)", message, show_spinner
        )
        old_spinner = getattr(self, "_show_busy_spinner", False)
        if show_spinner:
            self._show_busy_spinner = True

        self._notify(message, "info")
        self.project_view_model.set_action_busy(True, message)
        await asyncio.sleep(0.1)
        try:
            yield
        finally:
            self.project_view_model.set_action_busy(False)
            if show_spinner:
                self._show_busy_spinner = old_spinner
            if self._on_request_refresh:
                self._on_request_refresh()

    async def _save_page_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if self.project_view_model.is_project_loading:
            logger.debug("Save blocked - currently loading")
            return

        async with self._action_context("Saving page...", show_spinner=True):
            logger.debug("Starting async save for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_view_model.command_save_page()
                if success:
                    logger.info("Page saved successfully")
                    self._notify("Page saved successfully", "positive")
                else:
                    logger.warning("Failed to save page")
                    self._notify("Failed to save page", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("Save failed: %s", exc)
                self._notify(f"Save failed: {exc}", "negative")

    async def _save_project_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Save all loaded pages in the project asynchronously."""
        if self.project_view_model.is_project_loading:
            logger.debug("Save project blocked - currently loading")
            return

        async with self._action_context("Saving project...", show_spinner=True):
            logger.debug("Starting async save for all loaded pages")
            await asyncio.sleep(0.1)
            try:
                result = self.project_view_model.command_save_project()
                if result.failed_count == 0 and result.saved_count > 0:
                    logger.info("Project saved: %s", result.summary)
                    self._notify(result.summary, "positive")
                elif result.failed_count > 0:
                    logger.warning("Project save had failures: %s", result.summary)
                    self._notify(result.summary, "warning")
                else:
                    logger.info("Project save: %s", result.summary)
                    self._notify(result.summary, "info")
            except Exception as exc:  # noqa: BLE001
                logger.error("Save project failed: %s", exc)
                self._notify(f"Save project failed: {exc}", "negative")

    async def _load_page_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Load the current page from saved files asynchronously."""
        if self.project_view_model.is_project_loading:
            logger.debug("Load blocked - currently loading")
            return

        async with self._action_context("Loading page...", show_spinner=True):
            logger.debug("Starting async load for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_view_model.command_load_page()
                if success:
                    logger.info("Page loaded successfully")
                    self._notify("Page loaded successfully", "positive")
                else:
                    logger.warning("No saved page found for current page")
                    self._notify("No saved page found for current page", "warning")
            except Exception as exc:  # noqa: BLE001
                logger.error("Load failed: %s", exc)
                self._notify(f"Load failed: {exc}", "negative")

    async def _refine_bboxes_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Refine all bounding boxes in the current page asynchronously."""
        if self.project_view_model.is_project_loading:
            logger.debug("Refine bboxes blocked - currently loading")
            return

        async with self._action_context(
            "Refining bounding boxes...", show_spinner=True
        ):
            logger.debug("Starting async bbox refinement for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_view_model.command_refine_bboxes()
                if success:
                    logger.info("Bboxes refined successfully")
                    self._notify("Bounding boxes refined successfully", "positive")
                else:
                    logger.warning("Failed to refine bboxes")
                    self._notify("Failed to refine bounding boxes", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("Bbox refinement failed: %s", exc)
                self._notify(f"Bbox refinement failed: {exc}", "negative")

    async def _expand_refine_bboxes_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Expand and refine all bounding boxes in the current page asynchronously."""
        if self.project_view_model.is_project_loading:
            logger.debug("Expand & refine bboxes blocked - currently loading")
            return

        async with self._action_context(
            "Expanding and refining bounding boxes...", show_spinner=True
        ):
            logger.debug("Starting async bbox expand & refine for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_view_model.command_expand_refine_bboxes()
                if success:
                    logger.info("Bboxes expanded and refined successfully")
                    self._notify(
                        "Bounding boxes expanded and refined successfully",
                        "positive",
                    )
                else:
                    logger.warning("Failed to expand and refine bboxes")
                    self._notify(
                        "Failed to expand and refine bounding boxes", "negative"
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("Bbox expand & refine failed: %s", exc)
                self._notify(f"Bbox expand & refine failed: {exc}", "negative")

    async def _reload_ocr_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Reload OCR using the original source image asynchronously."""
        if self.project_view_model.is_project_loading:
            logger.debug("Reload OCR blocked - currently loading")
            return

        async with self._action_context(
            "Reloading page with OCR...", show_spinner=True
        ):
            logger.debug("Starting async OCR reload for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_view_model.command_reload_page_with_ocr()
                if success:
                    project_state = getattr(
                        self.project_view_model, "_project_state", None
                    )
                    current_page = None
                    if project_state is not None:
                        project = getattr(project_state, "project", None)
                        page_index = getattr(
                            project_state,
                            "current_page_index",
                            self.project_view_model.current_page_index,
                        )
                        if (
                            project is not None
                            and hasattr(project, "pages")
                            and 0 <= page_index < len(project.pages)
                        ):
                            current_page = project.pages[page_index]

                    if current_page is not None:
                        self._sync_text_tabs(current_page)

                    # Ensure image tabs refresh even when page index does not change.
                    self.page_state_view_model.command_refresh_images()

                    logger.info("OCR reloaded successfully")
                    self._notify("Page reloaded with OCR", "positive")
                else:
                    logger.warning("Failed to reload OCR")
                    self._notify("Failed to reload OCR", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("OCR reload failed: %s", exc)
                self._notify(f"OCR reload failed: {exc}", "negative")

    async def _reload_ocr_edited_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Reload OCR using the current in-memory edited page image."""
        if self.project_view_model.is_project_loading:
            logger.debug("Reload OCR (edited image) blocked - currently loading")
            return

        async with self._action_context(
            "Reloading OCR from edited image...", show_spinner=True
        ):
            logger.debug("Starting async OCR reload from edited image")
            await asyncio.sleep(0.1)
            try:
                success = self.project_view_model.command_reload_page_with_ocr(
                    use_edited_image=True
                )
                if success:
                    project_state = getattr(
                        self.project_view_model, "_project_state", None
                    )
                    current_page = None
                    if project_state is not None:
                        project = getattr(project_state, "project", None)
                        page_index = getattr(
                            project_state,
                            "current_page_index",
                            self.project_view_model.current_page_index,
                        )
                        if (
                            project is not None
                            and hasattr(project, "pages")
                            and 0 <= page_index < len(project.pages)
                        ):
                            current_page = project.pages[page_index]

                    if current_page is not None:
                        self._sync_text_tabs(current_page)

                    self.page_state_view_model.command_refresh_images()

                    logger.info("OCR reloaded from edited image successfully")
                    self._notify("Page reloaded with OCR from edited image", "positive")
                else:
                    logger.warning("Failed to reload OCR from edited image")
                    self._notify("Failed to reload OCR from edited image", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("OCR reload from edited image failed: %s", exc)
                self._notify(f"OCR reload from edited image failed: {exc}", "negative")

    async def _rematch_gt_async(
        self,
        _event: PageActionEvent = None,
    ):  # pragma: no cover - UI side effects
        """Re-run bulk GT matching on the current page, replacing per-word edits."""
        if self.project_view_model.is_project_loading:
            logger.debug("Rematch GT blocked - currently loading")
            return

        async with self._action_context("Re-matching ground truth..."):
            try:
                success = self.project_view_model.command_rematch_gt()
                if success:
                    current_page = self.project_view_model.get_current_page()
                    if current_page is not None:
                        self._sync_text_tabs(current_page)

                    logger.info("Ground truth re-matched successfully")
                    self._notify("Ground truth re-matched from source text", "positive")
                else:
                    logger.warning("Failed to rematch ground truth")
                    self._notify(
                        "No ground truth text available for this page", "warning"
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("GT rematch failed: %s", exc)
                self._notify(f"GT rematch failed: {exc}", "negative")
