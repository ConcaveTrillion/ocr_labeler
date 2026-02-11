from __future__ import annotations

import asyncio
import contextlib
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
        self.project_root_snapshot: str | None = None
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
                reload_ocr=self._reload_ocr_async,
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
                on_reload_ocr=self.callbacks.reload_ocr if self.callbacks else None,
            )
            self.page_controls.build()
            logger.debug("Page controls built")

            self.content = ContentArea(self.page_state_viewmodel, self.callbacks)
            self.content.build()
            logger.debug("Content area built")

            # Snapshot the project root at build time so we can detect project switches
            self.project_root_snapshot = getattr(self.viewmodel, "project_root", None)

            # Busy overlay for page-level actions
            self._busy_overlay = (
                ui.column()
                .classes(
                    "fixed inset-0 bg-black/20 z-[100] items-center justify-center hidden"
                )
                .style("backdrop-filter: blur(2px)")
            )
            with self._busy_overlay:
                ui.spinner(size="xl", color="primary")
                self._busy_label = ui.label("Working...").classes(
                    "text-white text-lg font-bold"
                )

            # Bind busy overlay visibility to viewmodel.is_busy
            self._busy_overlay.bind_visibility_from(self.viewmodel, "is_busy")
            # Bind busy label text to viewmodel.busy_message
            self._busy_label.bind_text_from(self.viewmodel, "busy_message")

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

        loading = (
            self.viewmodel.is_project_loading
            or self.viewmodel.is_navigating
            or getattr(self.viewmodel, "is_busy", False)
        )
        busy = getattr(self.viewmodel, "is_busy", False)
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
                if busy:
                    # Keep content visible under overlay; just hide inline spinner
                    self.content.page_spinner.classes(add="hidden")
                    logger.debug("Busy overlay active; leaving content visible")
                elif loading:  # page-level
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
        busy = getattr(self.viewmodel, "is_busy", False)
        # Immediately hide the main content splitter and show the page-level
        # spinner so the user sees immediate feedback that navigation started.
        try:
            if self.content and self.content.splitter and self.content.page_spinner:
                # Leave content visible; only toggle inline spinner as needed
                if busy:
                    self.content.page_spinner.classes(add="hidden")
                    logger.debug(
                        "Busy overlay active; keeping inline page spinner hidden"
                    )
                else:
                    # Show the page-level spinner and hide content area
                    self.content.splitter.classes(add="hidden")
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

    @contextlib.asynccontextmanager
    async def _action_context(self, message: str, show_spinner: bool = False):
        """Context manager to show a notification and overlay during an action.

        Args:
            message: The message to show in the notification and overlay.
            show_spinner: Whether to show a full-page spinner overlay.
        """
        print(
            f"DEBUG: _action_context called with message={message}, show_spinner={show_spinner}"
        )
        # Record old spinner state
        old_spinner = getattr(self, "_show_busy_spinner", False)
        if show_spinner:
            self._show_busy_spinner = True

        ui.notify(message, type="info")
        self.viewmodel.set_action_busy(True, message)
        # Yield control to allow NiceGUI to update the UI
        await asyncio.sleep(0.1)
        try:
            yield
        finally:
            self.viewmodel.set_action_busy(False)
            if show_spinner:
                self._show_busy_spinner = old_spinner
            # Ensure UI returns to visible state after action completes
            try:
                self.refresh()
            except Exception:
                logger.debug("Refresh after action context failed", exc_info=True)

    async def _prev_async(self):  # pragma: no cover - UI side effects
        """Navigate to previous page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            ui.notify("Navigation blocked: project is loading", type="warning")
            return

        async with self._action_context(
            "Navigating to previous page (OCR may run in background)...",
            show_spinner=True,
        ):
            logger.debug("Navigating to previous page")
            self._prep_image_spinners()
            await asyncio.sleep(0.1)
            success = self.viewmodel.command_navigate_prev()
            if not success:
                # Provide clearer reason to the user where possible
                reason = "unknown"
                try:
                    vm = self.viewmodel
                    if getattr(vm, "page_total", 0) <= 1:
                        reason = "only one page available"
                    elif getattr(vm, "is_first_page", False) or not getattr(
                        vm, "can_navigate_prev", False
                    ):
                        reason = "at first page"
                    elif getattr(vm, "is_controls_disabled", False):
                        reason = "controls disabled (loading/override)"
                except Exception:
                    reason = "inspection-failed"
                ui.notify(
                    f"Navigation prevented by viewmodel (prev): {reason}",
                    type="warning",
                )
                logger.debug(
                    "Previous page navigation prevented by viewmodel: %s", reason
                )
            else:
                logger.debug("Previous page navigation initiated successfully")
                # Show success notification when navigation completes
                # (note: actual page load happens asynchronously in background)
                ui.notify("Navigated to previous page", type="positive")

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            ui.notify("Navigation blocked: project is loading", type="warning")
            return

        async with self._action_context(
            "Navigating to next page (OCR may run in background)...", show_spinner=True
        ):
            logger.debug("Navigating to next page")
            self._prep_image_spinners()
            await asyncio.sleep(0.1)
            success = self.viewmodel.command_navigate_next()
            if not success:
                # Provide clearer reason to the user where possible
                reason = "unknown"
                try:
                    vm = self.viewmodel
                    if getattr(vm, "page_total", 0) <= 1:
                        reason = "only one page available"
                    elif getattr(vm, "is_last_page", False) or not getattr(
                        vm, "can_navigate_next", False
                    ):
                        reason = "at last page"
                    elif getattr(vm, "is_controls_disabled", False):
                        reason = "controls disabled (loading/override)"
                except Exception:
                    reason = "inspection-failed"
                ui.notify(
                    f"Navigation prevented by viewmodel (next): {reason}",
                    type="warning",
                )
                logger.debug("Next page navigation prevented by viewmodel: %s", reason)
            else:
                logger.debug("Next page navigation initiated successfully")
                # Show success notification when navigation completes
                # (note: actual page load happens asynchronously in background)
                ui.notify("Navigated to next page", type="positive")

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            ui.notify("Navigation blocked: project is loading", type="warning")
            return

        try:
            target_page = int(value)
        except (ValueError, TypeError):
            target_page = None

        display_value = target_page if target_page is not None else (value or "?")

        async with self._action_context(
            f"Navigating to page {display_value} (OCR may run in background)...",
            show_spinner=True,
        ):
            logger.debug("Navigating to page: %s", value)
            self._prep_image_spinners()
            await asyncio.sleep(0.1)
            if target_page is None:
                success = False
            else:
                page_idx = target_page - 1
                success = self.viewmodel.command_navigate_to_page(page_idx)

            if not success:
                # Provide clearer reason to the user where possible
                reason = "unknown"
                try:
                    vm = self.viewmodel
                    if not (0 <= (int(value) - 1) < getattr(vm, "page_total", 0)):
                        reason = "page index out of range"
                    elif getattr(vm, "is_controls_disabled", False):
                        reason = "controls disabled (loading/override)"
                except Exception:
                    reason = "inspection-failed"

                ui.notify(
                    f"Navigation prevented by viewmodel (goto): {reason}",
                    type="warning",
                )
                logger.debug(
                    "Goto page navigation prevented by viewmodel for value: %s, reason: %s",
                    value,
                    reason,
                )
            else:
                logger.debug(
                    "Goto page navigation initiated successfully for value: %s",
                    display_value,
                )
                # Show success notification when navigation completes
                # (note: actual page load happens asynchronously in background)
                ui.notify(f"Navigated to page {display_value}", type="positive")

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Save blocked - currently loading")
            return

        async with self._action_context("Saving page...", show_spinner=True):
            logger.debug("Starting async save for current page")
            await asyncio.sleep(0.1)
            try:
                # Run save
                success = self.viewmodel.command_save_page()

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

        async with self._action_context("Loading page...", show_spinner=True):
            logger.debug("Starting async load for current page")
            await asyncio.sleep(0.1)
            try:
                # Run load
                success = self.viewmodel.command_load_page()

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

        async with self._action_context(
            "Refining bounding boxes...", show_spinner=True
        ):
            logger.debug("Starting async bbox refinement for current page")
            await asyncio.sleep(0.1)
            try:
                # Run refinement
                success = self.viewmodel.command_refine_bboxes()

                if success:
                    logger.info("Bboxes refined successfully")
                    ui.notify("Bounding boxes refined successfully", type="positive")
                    # Trigger UI refresh to show updated overlays
                    self.refresh()
                    logger.debug(
                        "UI refresh triggered after successful bbox refinement"
                    )
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

        async with self._action_context(
            "Expanding and refining bounding boxes...", show_spinner=True
        ):
            logger.debug("Starting async bbox expand & refine for current page")
            await asyncio.sleep(0.1)
            try:
                # Run expansion and refinement
                success = self.viewmodel.command_expand_refine_bboxes()

                if success:
                    logger.info("Bboxes expanded and refined successfully")
                    ui.notify(
                        "Bounding boxes expanded and refined successfully",
                        type="positive",
                    )
                    # Trigger UI refresh to show updated overlays
                    self.refresh()
                    logger.debug(
                        "UI refresh triggered after successful bbox expand & refine"
                    )
                else:
                    logger.warning("Failed to expand and refine bboxes")
                    ui.notify(
                        "Failed to expand and refine bounding boxes", type="negative"
                    )

            except Exception as exc:  # noqa: BLE001
                logger.error("Bbox expand & refine failed: %s", exc)
                ui.notify(f"Bbox expand & refine failed: {exc}", type="negative")

    async def _reload_ocr_async(self):  # pragma: no cover - UI side effects
        """Reload the current page with OCR processing asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Reload OCR blocked - currently loading")
            return

        async with self._action_context(
            "Reloading page with OCR...", show_spinner=True
        ):
            logger.debug("Starting async OCR reload for current page")
            await asyncio.sleep(0.1)
            try:
                # Run OCR
                success = self.viewmodel.command_reload_page_with_ocr()

                if success:
                    logger.info("OCR reloaded successfully")
                    ui.notify("Page reloaded with OCR", type="positive")
                    # Trigger UI refresh
                    self.refresh()
                else:
                    logger.warning("Failed to reload OCR")
                    ui.notify("Failed to reload OCR", type="negative")

            except Exception as exc:  # noqa: BLE001
                logger.error("OCR reload failed: %s", exc)
                ui.notify(f"OCR reload failed: {exc}", type="negative")

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
