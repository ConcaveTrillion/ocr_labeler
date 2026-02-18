from __future__ import annotations

import asyncio
import contextlib
import logging

from nicegui import ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel
from ....viewmodels.project.project_state_view_model import ProjectStateViewModel
from ...callbacks import PageActionCallbacks
from .content import ContentArea
from .page_actions import PageActions

logger = logging.getLogger(__name__)


class PageView:  # pragma: no cover - UI wrapper file
    """Page-layer view: page actions and page content."""

    @classmethod
    def from_project(
        cls,
        project_viewmodel: ProjectStateViewModel,
        on_request_refresh=None,
    ) -> PageView | None:
        """Create a PageView from project state."""
        project_state = getattr(project_viewmodel, "_project_state", None)
        if project_state is None:
            logger.error("Cannot create PageView - no project state available")
            return None

        page_state_viewmodel = PageStateViewModel(project_state)
        return cls(
            project_viewmodel,
            page_state_viewmodel,
            on_request_refresh=on_request_refresh,
        )

    def __init__(
        self,
        project_viewmodel: ProjectStateViewModel,
        page_state_viewmodel: PageStateViewModel,
        on_request_refresh=None,
    ):
        self.project_viewmodel = project_viewmodel
        self.page_state_viewmodel = page_state_viewmodel
        self._on_request_refresh = on_request_refresh

        self.page_action_callbacks = PageActionCallbacks(
            save_page=self._save_page_async,
            load_page=self._load_page_async,
            refine_bboxes=self._refine_bboxes_async,
            expand_refine_bboxes=self._expand_refine_bboxes_async,
            reload_ocr=self._reload_ocr_async,
        )

        self.page_actions: PageActions | None = None
        self.content: ContentArea | None = None
        self.root = None

    def build(self):
        self.page_actions = PageActions(
            self.project_viewmodel,
            on_save_page=self.page_action_callbacks.save_page
            if self.page_action_callbacks
            else None,
            on_load_page=self.page_action_callbacks.load_page
            if self.page_action_callbacks
            else None,
            on_refine_bboxes=self.page_action_callbacks.refine_bboxes
            if self.page_action_callbacks
            else None,
            on_expand_refine_bboxes=self.page_action_callbacks.expand_refine_bboxes
            if self.page_action_callbacks
            else None,
            on_reload_ocr=self.page_action_callbacks.reload_ocr
            if self.page_action_callbacks
            else None,
        )
        self.page_actions.build()

        self.content = ContentArea(
            self.page_state_viewmodel, self.page_action_callbacks
        )
        self.root = self.content.build()
        return self.root

    def refresh(
        self,
        loading: bool,
        busy: bool,
    ):
        """Refresh page-layer content only."""
        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = self.project_viewmodel.current_page_index
        image_name = ""
        project_state = getattr(self.project_viewmodel, "_project_state", None)
        project = getattr(project_state, "project", None)
        if project is not None and hasattr(project, "image_paths"):
            if 0 <= current_index < len(project.image_paths):
                image_name = project.image_paths[current_index].name

        page = None
        if not loading and project_state is not None and project is not None:
            if 0 <= current_index < len(project.pages):
                page = project.pages[current_index]
            self._sync_text_tabs(page)

        total = self.project_viewmodel.page_total
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
        try:
            if self.content and self.content.splitter and self.content.page_spinner:
                if busy:
                    self.content.page_spinner.classes(add="hidden")
                    logger.debug(
                        "Busy overlay active; keeping inline page spinner hidden"
                    )
                else:
                    self.content.splitter.classes(add="hidden")
                    self.content.page_spinner.classes(remove="hidden")
                    logger.debug("Hid content splitter and showed page spinner")
        except Exception:
            logger.debug("Failed to toggle splitter/spinner immediately", exc_info=True)

        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():
                if img:
                    try:
                        img.set_visibility(False)
                        logger.debug("Hidden image: %s", name)
                    except Exception:
                        logger.debug("Failed to hide image: %s", name, exc_info=True)

        try:
            if (
                self.content
                and hasattr(self.content, "text_tabs")
                and getattr(self.content.text_tabs, "word_match_view", None)
            ):
                self.content.text_tabs.word_match_view.clear()
                logger.debug("Cleared word matches for navigation transition")
        except Exception:
            logger.debug("Failed to clear word matches", exc_info=True)

    def _sync_text_tabs(self, page):
        """Synchronize text tabs with the current page."""
        try:
            if self.content and getattr(self.content, "text_tabs", None):
                text_tabs = self.content.text_tabs
                if text_tabs.page_state is not None:
                    text_tabs.page_state.current_page = page
                text_tabs.model.update()
                text_tabs._update_text_editors()
                text_tabs.update_word_matches(page)
        except Exception:
            logger.debug(
                "Failed to synchronize text tabs from project state during refresh",
                exc_info=True,
            )

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
        try:
            app_state_model = getattr(self.project_viewmodel, "_app_state_model", None)
            app_state = getattr(app_state_model, "_app_state", None)
            if app_state is not None:
                app_state.queue_notification(message, type_)
                return
        except Exception:
            logger.debug("Failed to enqueue session notification", exc_info=True)

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
        self.project_viewmodel.set_action_busy(True, message)
        await asyncio.sleep(0.1)
        try:
            yield
        finally:
            self.project_viewmodel.set_action_busy(False)
            if show_spinner:
                self._show_busy_spinner = old_spinner
            try:
                if self._on_request_refresh:
                    self._on_request_refresh()
            except Exception:
                logger.debug("Refresh after page action failed", exc_info=True)

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if self.project_viewmodel.is_project_loading:
            logger.debug("Save blocked - currently loading")
            return

        async with self._action_context("Saving page...", show_spinner=True):
            logger.debug("Starting async save for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_viewmodel.command_save_page()
                if success:
                    logger.info("Page saved successfully")
                    self._notify("Page saved successfully", "positive")
                else:
                    logger.warning("Failed to save page")
                    self._notify("Failed to save page", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("Save failed: %s", exc)
                self._notify(f"Save failed: {exc}", "negative")

    async def _load_page_async(self):  # pragma: no cover - UI side effects
        """Load the current page from saved files asynchronously."""
        if self.project_viewmodel.is_project_loading:
            logger.debug("Load blocked - currently loading")
            return

        async with self._action_context("Loading page...", show_spinner=True):
            logger.debug("Starting async load for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_viewmodel.command_load_page()
                if success:
                    logger.info("Page loaded successfully")
                    self._notify("Page loaded successfully", "positive")
                else:
                    logger.warning("No saved page found for current page")
                    self._notify("No saved page found for current page", "warning")
            except Exception as exc:  # noqa: BLE001
                logger.error("Load failed: %s", exc)
                self._notify(f"Load failed: {exc}", "negative")

    async def _refine_bboxes_async(self):  # pragma: no cover - UI side effects
        """Refine all bounding boxes in the current page asynchronously."""
        if self.project_viewmodel.is_project_loading:
            logger.debug("Refine bboxes blocked - currently loading")
            return

        async with self._action_context(
            "Refining bounding boxes...", show_spinner=True
        ):
            logger.debug("Starting async bbox refinement for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_viewmodel.command_refine_bboxes()
                if success:
                    logger.info("Bboxes refined successfully")
                    self._notify("Bounding boxes refined successfully", "positive")
                else:
                    logger.warning("Failed to refine bboxes")
                    self._notify("Failed to refine bounding boxes", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("Bbox refinement failed: %s", exc)
                self._notify(f"Bbox refinement failed: {exc}", "negative")

    async def _expand_refine_bboxes_async(self):  # pragma: no cover - UI side effects
        """Expand and refine all bounding boxes in the current page asynchronously."""
        if self.project_viewmodel.is_project_loading:
            logger.debug("Expand & refine bboxes blocked - currently loading")
            return

        async with self._action_context(
            "Expanding and refining bounding boxes...", show_spinner=True
        ):
            logger.debug("Starting async bbox expand & refine for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_viewmodel.command_expand_refine_bboxes()
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

    async def _reload_ocr_async(self):  # pragma: no cover - UI side effects
        """Reload the current page with OCR processing asynchronously."""
        if self.project_viewmodel.is_project_loading:
            logger.debug("Reload OCR blocked - currently loading")
            return

        async with self._action_context(
            "Reloading page with OCR...", show_spinner=True
        ):
            logger.debug("Starting async OCR reload for current page")
            await asyncio.sleep(0.1)
            try:
                success = self.project_viewmodel.command_reload_page_with_ocr()
                if success:
                    logger.info("OCR reloaded successfully")
                    self._notify("Page reloaded with OCR", "positive")
                else:
                    logger.warning("Failed to reload OCR")
                    self._notify("Failed to reload OCR", "negative")
            except Exception as exc:  # noqa: BLE001
                logger.error("OCR reload failed: %s", exc)
                self._notify(f"OCR reload failed: {exc}", "negative")
