from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from nicegui import ui

from ...routing import sync_url_from_project_state
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from ..shared.base_view import BaseView
from .pages.page_view import PageView
from .project_navigation_controls import ProjectNavigationControls

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

        self.navigation_controls: ProjectNavigationControls | None = None
        self.page_view: PageView | None = None
        self.content = None
        self.project_root_snapshot: str | None = None
        # Track whether a refresh request arrived before build completed
        self._pending_refresh: bool = False
        logger.debug("ProjectView initialized successfully")

    def build(self):
        """Build the project view UI components."""
        logger.debug("Building ProjectView UI components")

        # Build page layer (all non-navigation page UI and callback wiring)
        self.page_view = PageView.from_project(
            self.viewmodel,
            on_request_refresh=self.refresh,
        )
        if self.page_view is None:
            logger.error("Cannot build ProjectView page layer")
            return ui.column()

        # Root container for the entire project view
        with ui.column().classes("w-full h-full") as self._root:
            # Project navigation controls (page navigation + metadata)
            self.navigation_controls = ProjectNavigationControls(
                self.viewmodel,
                on_prev=self._prev_async,
                on_next=self._next_async,
                on_goto=self._goto_async,
            )
            self.navigation_controls.build()
            logger.debug("Project navigation controls built")

            self.page_view.build()
            self.content = self.page_view.content
            logger.debug("Page view built")

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

            # Bind busy overlay visibility to viewmodel.is_busy
            self._busy_overlay.bind_visibility_from(self.viewmodel, "is_busy")

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

        if self.page_view:
            self.page_view.refresh(loading, busy)

        if self.navigation_controls:
            current_index = self.viewmodel.current_page_index
            total = self.viewmodel.page_total
            image_name = ""

            project_state = getattr(self.viewmodel, "_project_state", None)
            project = getattr(project_state, "project", None)
            if project is not None and hasattr(project, "image_paths"):
                if 0 <= current_index < len(project.image_paths):
                    image_name = project.image_paths[current_index].name

            if total:
                display_index = current_index + 1 if current_index >= 0 else 1
                display_name = image_name or "(no page)"
                self.navigation_controls.set_page(display_index, display_name, total)
            else:
                self.navigation_controls.set_page(1, "(no page)", 0)

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

    def _notify(self, message: str, type_: str = "info"):
        """Route notifications through per-session queue with UI fallback."""
        try:
            app_state_model = getattr(self.viewmodel, "_app_state_model", None)
            app_state = getattr(app_state_model, "_app_state", None)
            if app_state is not None:
                app_state.queue_notification(message, type_)
                return
        except Exception:
            logger.debug("Failed to enqueue session notification", exc_info=True)

        ui.notify(message, type=type_)

    @contextlib.asynccontextmanager
    async def _action_context(self, message: str, show_spinner: bool = False):
        """Context manager to show a notification and overlay during an action.

        Args:
            message: The message to show in the notification and overlay.
            show_spinner: Whether to show a full-page spinner overlay.
        """
        logger.debug(
            f"_action_context called with message={message}, show_spinner={show_spinner}"
        )
        # Record old spinner state
        old_spinner = getattr(self, "_show_busy_spinner", False)
        if show_spinner:
            self._show_busy_spinner = True

        self._notify(message, "info")
        logger.info(f"[BLUR] Activating busy overlay for action: {message}")
        self.viewmodel.set_action_busy(True, message)
        # Yield control to allow NiceGUI to update the UI
        await asyncio.sleep(0.1)
        logger.debug("[BLUR] Busy overlay should now be visible")
        try:
            yield
        finally:
            logger.info(f"[BLUR] Deactivating busy overlay after action: {message}")
            self.viewmodel.set_action_busy(False)
            if show_spinner:
                self._show_busy_spinner = old_spinner
            logger.debug("[BLUR] Busy overlay should now be hidden")
            # Ensure UI returns to visible state after action completes
            try:
                self.refresh()
            except Exception:
                logger.debug("Refresh after action context failed", exc_info=True)

    async def _prev_async(self):  # pragma: no cover - UI side effects
        """Navigate to previous page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            self._notify("Navigation blocked: project is loading", "warning")
            return

        async with self._action_context(
            "Navigating to previous page (OCR may run in background)...",
            show_spinner=True,
        ):
            logger.debug("Navigating to previous page")
            if self.page_view:
                self.page_view.prepare_navigation_transition(
                    getattr(self.viewmodel, "is_busy", False)
                )
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
                self._notify(
                    f"Navigation prevented by viewmodel (prev): {reason}",
                    "warning",
                )
                logger.debug(
                    "Previous page navigation prevented by viewmodel: %s", reason
                )
            else:
                logger.debug("Previous page navigation initiated successfully")
                # Show success notification when navigation completes
                # (note: actual page load happens asynchronously in background)
                self._notify("Navigated to previous page", "positive")

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        import threading

        logger.info(
            "[NAV-NEXT] Entry - Thread: %s, Current page: %s",
            threading.current_thread().name,
            self.viewmodel.current_page_index,
        )
        if self.viewmodel.is_project_loading:
            logger.warning("[NAV-NEXT] Navigation blocked - project loading")
            self._notify("Navigation blocked: project is loading", "warning")
            return

        async with self._action_context(
            "Navigating to next page (OCR may run in background)...", show_spinner=True
        ):
            logger.info(
                "[NAV-NEXT] Starting navigation from page %s",
                self.viewmodel.current_page_index,
            )
            if self.page_view:
                self.page_view.prepare_navigation_transition(
                    getattr(self.viewmodel, "is_busy", False)
                )
            await asyncio.sleep(0.1)
            logger.info("[NAV-NEXT] Calling command_navigate_next()")
            success = self.viewmodel.command_navigate_next()
            logger.info("[NAV-NEXT] command_navigate_next() returned: %s", success)
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
                self._notify(
                    f"Navigation prevented by viewmodel (next): {reason}",
                    "warning",
                )
                logger.debug("Next page navigation prevented by viewmodel: %s", reason)
            else:
                logger.info(
                    "[NAV-NEXT] Navigation initiated successfully - now at page index %s",
                    self.viewmodel.current_page_index,
                )
                # Show success notification when navigation completes
                # (note: actual page load happens asynchronously in background)
                self._notify("Navigated to next page", "positive")
        logger.info("[NAV-NEXT] Exit - Thread: %s", threading.current_thread().name)

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            self._notify("Navigation blocked: project is loading", "warning")
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
            if self.page_view:
                self.page_view.prepare_navigation_transition(
                    getattr(self.viewmodel, "is_busy", False)
                )
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

                self._notify(
                    f"Navigation prevented by viewmodel (goto): {reason}",
                    "warning",
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
                self._notify(f"Navigated to page {display_value}", "positive")

    def _sync_browser_url(self):
        """Update the browser URL to reflect the current project/page state.

        Uses ui.navigate.history.replace() so users can copy/share deep links
        without adding extra browser history entries on each page navigation.
        """
        try:
            if not hasattr(self.viewmodel, "_project_state"):
                return
            project_state = self.viewmodel._project_state
            if not project_state or not project_state.project_root:
                return

            sync_url_from_project_state(
                project_state.project_root, project_state.current_page_index
            )
        except Exception:
            logger.debug("Failed to sync browser URL", exc_info=True)

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
            # Sync browser URL when page navigation completes
            if property_name in ["current_page_index", "project_state"]:
                self._sync_browser_url()
        except Exception:
            logger.exception("Error refreshing ProjectView on property change")
