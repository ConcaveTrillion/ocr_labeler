from __future__ import annotations

import asyncio
import logging
from typing import Any

from nicegui import ui

from ...viewmodels.project.page_state_view_model import PageStateViewModel
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from ..callbacks import NavigationCallbacks
from ..shared.base_view import BaseView
from .pages.content import ContentArea
from .pages.page_controls import PageControls

logger = logging.getLogger(__name__)


class ProjectView(
    BaseView[ProjectStateViewModel]
):  # pragma: no cover - heavy UI wiring
    """Project-specific view handling navigation, content display, and page operations."""

    def __init__(self, viewmodel: ProjectStateViewModel):
        """Initialize the project view with its view model.

        Args:
            viewmodel: The project state view model for this view.
        """
        logger.debug("Initializing ProjectView with ProjectStateViewModel")
        super().__init__(viewmodel)

        self.page_state_viewmodel: PageStateViewModel | None = None
        self.page_controls: PageControls | None = None
        self.content: ContentArea | None = None
        self.callbacks: NavigationCallbacks | None = None
        # Track whether a refresh request arrived before build completed
        self._pending_refresh: bool = False
        logger.debug("ProjectView initialized successfully")

    def build(self):
        """Build the project view UI components."""
        logger.debug("Building ProjectView UI components")

        # Create page state viewmodel only if project_state is available
        if getattr(self.viewmodel, "_project_state", None) is not None:
            self.page_state_viewmodel = PageStateViewModel(
                self.viewmodel._project_state
            )
            logger.debug("PageStateViewModel created")
        else:
            logger.error(
                "Cannot create PageStateViewModel - no project state available"
            )
            # Build an empty column so the UI can continue; refresh will retry later
            return ui.column()

        # Root container for the entire project view
        with ui.column().classes("w-full h-full") as self._root:
            # Set up navigation callbacks
            self.callbacks = NavigationCallbacks(
                save_page=self._save_page_async,
                load_page=self._load_page_async,
                refine_bboxes=self._refine_bboxes_async,
                expand_refine_bboxes=self._expand_refine_bboxes_async,
            )
            logger.debug("Navigation callbacks initialized")

            # Page controls (navigation, save/load)
            self.page_controls = PageControls(
                self.viewmodel,
                on_prev=self._prev_async,
                on_next=self._next_async,
                on_goto=self._goto_async,
                on_save_page=self.callbacks.save_page if self.callbacks else None,
                on_load_page=self.callbacks.load_page if self.callbacks else None,
                on_refine_bboxes=self.callbacks.refine_bboxes
                if self.callbacks
                else None,
                on_expand_refine_bboxes=self.callbacks.expand_refine_bboxes
                if self.callbacks
                else None,
            )
            self.page_controls.build()
            logger.debug("Page controls built")

            # Content area (images and text)
            self.content = ContentArea(
                page_state_viewmodel=self.page_state_viewmodel, callbacks=self.callbacks
            )
            self.content.build()
            logger.debug("Content area built")

        logger.debug("ProjectView UI build completed")
        self.mark_as_built()
        # If property changes arrived before the view was built, apply one
        # deferred refresh now that the view is ready.
        try:
            if getattr(self, "_pending_refresh", False):
                logger.debug("Applying pending refresh after build completion")
                self.refresh()
                self._pending_refresh = False
        except Exception:
            logger.debug("Deferred refresh failed", exc_info=True)
        return self._root

    def refresh(self):
        """Refresh the project view based on current view model state."""
        if not self.is_built:
            logger.warning("Cannot refresh ProjectView before it is built")
            return

        loading = self.viewmodel.is_project_loading
        logger.debug("Refreshing ProjectView - loading: %s", loading)

        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = self.viewmodel.current_page_index
        image_name = ""
        # Note: We need to access the underlying project through the viewmodel
        if hasattr(self.viewmodel, "_project_state") and hasattr(
            self.viewmodel._project_state, "project"
        ):
            project = self.viewmodel._project_state.project
            if 0 <= current_index < len(project.image_paths):
                image_name = project.image_paths[current_index].name
        page = None if loading else self.viewmodel._project_state.current_page()
        total = self.viewmodel.page_total

        logger.debug(
            "Current page state - index: %d, image_name: %s, total_pages: %d, page_loaded: %s",
            current_index,
            image_name,
            total,
            page is not None,
        )

        # Content visibility and loading states
        if self.content and self.content.root:
            # Toggle splitter vs spinners
            if self.content.splitter and self.content.page_spinner:
                if loading:  # page-level
                    self.content.splitter.classes(add="hidden")
                    self.content.page_spinner.classes(remove="hidden")
                    logger.debug("Showing page spinner, hiding content splitter")
                else:
                    self.content.splitter.classes(remove="hidden")
                    self.content.page_spinner.classes(add="hidden")
                    logger.debug("Showing content splitter, hiding page spinner")
                    # Show images when content is visible
                    self._show_images()

        # Page meta
        if self.page_controls:
            if total:
                # Use immediate index+1 and image filename while OCR loads
                display_index = current_index + 1 if current_index >= 0 else 1
                display_name = image_name or (page.name if page else "(no page)")
                self.page_controls.set_page(display_index, display_name, total)
                logger.debug(
                    "Updated page controls - display_index: %d, display_name: %s, total: %d",
                    display_index,
                    display_name,
                    total,
                )
            else:
                self.page_controls.set_page(1, "(no page)", 0)
                logger.debug("No pages available, set page controls to default state")

        # Images are now updated automatically through data binding
        # No need for manual _update_images call

    def _prep_image_spinners(self):
        """Hide images during navigation transitions."""
        logger.debug("Preparing image spinners for navigation transition")
        # Immediately hide the main content splitter and show the page-level
        # spinner so the user sees immediate feedback that navigation started.
        try:
            if self.content and self.content.splitter and self.content.page_spinner:
                # Hide the content area
                self.content.splitter.classes(add="hidden")
                # Show the page-level spinner
                self.content.page_spinner.classes(remove="hidden")
                logger.debug("Hid content splitter and showed page spinner")
        except Exception:
            logger.debug("Failed to toggle splitter/spinner immediately", exc_info=True)

        # Also hide individual images (if any) to free up rendering work
        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():  # noqa: F841
                if img:
                    try:
                        img.set_visibility(False)
                        logger.debug("Hidden image: %s", name)
                    except Exception:
                        logger.debug("Failed to hide image: %s", name, exc_info=True)

        # Clear/hide the matches panel immediately so it doesn't flash stale data
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
        logger.debug("Image spinners preparation completed")

    def _show_images(self):
        """Show images after navigation completes."""
        logger.debug("Showing images after navigation")
        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():  # noqa: F841
                if img:
                    img.set_visibility(True)
                    logger.debug("Shown image: %s", name)
        logger.debug("Images shown")

    def _goto_page(self, raw_value):
        """Navigate to a specific page number with validation."""
        try:
            n = int(raw_value)
            logger.debug("Parsed goto page value: %s -> %d", raw_value, n)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to parse goto page value: %s, defaulting to 1", raw_value
            )
            n = 1
        if n < 1:
            logger.debug("Page number %d is less than 1, setting to 1", n)
            n = 1
        logger.debug("Navigating to page number: %d", n)
        # Use viewmodel command
        self.viewmodel.command_navigate_to_page(n - 1)  # Convert to 0-based index

    async def _prev_async(self):  # pragma: no cover - UI side effects
        """Navigate to previous page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            ui.notify("Navigation blocked: project is loading", type="warning")
            return
        # Notify user that navigation attempt started and show diagnostic state
        vm = self.viewmodel
        try:
            idx = getattr(vm, "current_page_index", -1)
            total = getattr(vm, "page_total", 0)
            can_prev = getattr(vm, "can_navigate_prev", False)
            controls_disabled = getattr(vm, "is_controls_disabled", False)
            ui.notify(
                f"Attempting prev — idx={idx}, total={total}, can_prev={can_prev}, disabled={controls_disabled}",
                type="info",
            )
        except Exception:
            ui.notify("Attempting prev", type="info")

        logger.debug("Navigating to previous page")
        self._prep_image_spinners()
        await asyncio.sleep(0)
        success = self.viewmodel.command_navigate_prev()
        if not success:
            ui.notify("Navigation prevented by viewmodel (prev)", type="warning")
            logger.debug("Previous page navigation prevented by viewmodel")
        else:
            logger.debug("Previous page navigation completed")

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            ui.notify("Navigation blocked: project is loading", type="warning")
            return
        # Ensure viewmodel is up-to-date with underlying state before attempting
        vm = self.viewmodel
        try:
            # Try to refresh computed properties from the current project state
            try:
                vm.update()
            except Exception:
                # Non-fatal; continue to diagnostics
                logger.debug("vm.update() raised during debug refresh", exc_info=True)

            idx = getattr(vm, "current_page_index", -1)
            total = getattr(vm, "page_total", 0)
            can_next = getattr(vm, "can_navigate_next", False)
            controls_disabled = getattr(vm, "is_controls_disabled", False)
            is_navigating = getattr(vm, "is_navigating", False)
            is_busy = getattr(vm, "is_busy", False)

            # Inspect underlying project pages cache where available
            next_page_cached = None
            try:
                ps = getattr(vm, "_project_state", None)
                if ps and hasattr(ps, "project") and ps.project and ps.project.pages:
                    tgt = idx + 1
                    if 0 <= tgt < len(ps.project.pages):
                        next_page_cached = ps.project.pages[tgt]
            except Exception:
                next_page_cached = None

            ui.notify(
                f"Attempting next — idx={idx}, total={total}, can_next={can_next}, disabled={controls_disabled}, navigating={is_navigating}, busy={is_busy}, next_cached={'yes' if next_page_cached is not None else 'no'}",
                type="info",
            )
        except Exception:
            ui.notify("Attempting next (diagnostics unavailable)", type="info")

        logger.debug("Navigating to next page")
        self._prep_image_spinners()
        await asyncio.sleep(0)
        success = self.viewmodel.command_navigate_next()
        if not success:
            # Provide clearer reason to the user where possible
            reason = "unknown"
            try:
                if getattr(vm, "page_total", 0) <= 1:
                    reason = "only one page available"
                elif getattr(vm, "is_controls_disabled", False):
                    reason = "controls disabled"
                elif not getattr(vm, "can_navigate_next", False):
                    reason = "cannot navigate next (viewmodel)"
            except Exception:
                reason = "inspection-failed"
            ui.notify(
                f"Navigation prevented by viewmodel (next): {reason}", type="warning"
            )
            logger.debug("Next page navigation prevented by viewmodel: %s", reason)
        else:
            ui.notify("Navigation started to next page", type="positive")
            logger.debug("Next page navigation completed")

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            ui.notify("Navigation blocked: project is loading", type="warning")
            return
        # Notify user that navigation attempt started and show diagnostic state
        vm = self.viewmodel
        try:
            idx = getattr(vm, "current_page_index", -1)
            total = getattr(vm, "page_total", 0)
            can_nav = getattr(vm, "can_navigate", False)
            controls_disabled = getattr(vm, "is_controls_disabled", False)
            ui.notify(
                f"Attempting goto {value} — idx={idx}, total={total}, can_navigate={can_nav}, disabled={controls_disabled}",
                type="info",
            )
        except Exception:
            ui.notify(f"Attempting goto {value}", type="info")

        logger.debug("Navigating to page: %s", value)
        self._prep_image_spinners()
        await asyncio.sleep(0)
        success = self.viewmodel.command_navigate_to_page(int(value) - 1)
        if not success:
            ui.notify("Navigation prevented by viewmodel (goto)", type="warning")
            logger.debug(
                "Goto page navigation prevented by viewmodel for value: %s", value
            )
        else:
            logger.debug("Goto page navigation completed for value: %s", value)

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Save blocked - currently loading")
            return

        logger.debug("Starting async save for current page")
        try:
            # Run save in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.viewmodel.command_save_page,
            )

            if success:
                logger.info("Page saved successfully")
                ui.notify("Page saved successfully", type="positive")
            else:
                logger.warning("Failed to save page")
                ui.notify("Failed to save page", type="negative")

        except Exception as exc:  # noqa: BLE001
            logger.error("Save failed: %s", exc)
            ui.notify(f"Save failed: {exc}", type="negative")

    async def _load_page_async(self):  # pragma: no cover - UI side effects
        """Load the current page from saved files asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Load blocked - currently loading")
            return

        logger.debug("Starting async load for current page")
        try:
            # Run load in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.viewmodel.command_load_page,
            )

            if success:
                logger.info("Page loaded successfully")
                ui.notify("Page loaded successfully", type="positive")
                # Trigger UI refresh to show loaded page
                self.refresh()
                logger.debug("UI refresh triggered after successful load")
            else:
                logger.warning("No saved page found for current page")
                ui.notify("No saved page found for current page", type="warning")

        except Exception as exc:  # noqa: BLE001
            logger.error("Load failed: %s", exc)
            ui.notify(f"Load failed: {exc}", type="negative")

    async def _refine_bboxes_async(self):  # pragma: no cover - UI side effects
        """Refine all bounding boxes in the current page asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Refine bboxes blocked - currently loading")
            return

        logger.debug("Starting async bbox refinement for current page")
        try:
            # Run refinement in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.viewmodel.command_refine_bboxes,
            )

            if success:
                logger.info("Bboxes refined successfully")
                ui.notify("Bounding boxes refined successfully", type="positive")
                # Trigger UI refresh to show updated overlays
                self.refresh()
                logger.debug("UI refresh triggered after successful bbox refinement")
            else:
                logger.warning("Failed to refine bboxes")
                ui.notify("Failed to refine bounding boxes", type="negative")

        except Exception as exc:  # noqa: BLE001
            logger.error("Bbox refinement failed: %s", exc)
            ui.notify(f"Bbox refinement failed: {exc}", type="negative")

    async def _expand_refine_bboxes_async(self):  # pragma: no cover - UI side effects
        """Expand and refine all bounding boxes in the current page asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Expand & refine bboxes blocked - currently loading")
            return

        logger.debug("Starting async bbox expand & refine for current page")
        try:
            # Run expansion and refinement in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.viewmodel.command_expand_refine_bboxes,
            )

            if success:
                logger.info("Bboxes expanded and refined successfully")
                ui.notify(
                    "Bounding boxes expanded and refined successfully", type="positive"
                )
                # Trigger UI refresh to show updated overlays
                self.refresh()
                logger.debug(
                    "UI refresh triggered after successful bbox expand & refine"
                )
            else:
                logger.warning("Failed to expand and refine bboxes")
                ui.notify("Failed to expand and refine bounding boxes", type="negative")

        except Exception as exc:  # noqa: BLE001
            logger.error("Bbox expand & refine failed: %s", exc)
            ui.notify(f"Bbox expand & refine failed: {exc}", type="negative")

    def _on_viewmodel_property_changed(self, property_name: str, value: Any):
        """Handle view model property changes by refreshing the view."""
        logger.debug(f"View model property changed: {property_name} = {value}")
        # If view hasn't been built yet, defer the refresh to avoid spurious
        # UI operations and websocket sends. The build() method will apply a
        # deferred refresh after marking the view built.
        if not self.is_built:
            logger.debug(
                "View model change received but view is not built yet; deferring refresh"
            )
            self._pending_refresh = True
            return

        try:
            self.refresh()
        except Exception:
            logger.exception("Error refreshing ProjectView on property change")
