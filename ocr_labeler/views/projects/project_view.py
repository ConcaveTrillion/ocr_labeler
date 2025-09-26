from __future__ import annotations

import asyncio
import logging
from typing import Any

from nicegui import ui

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

        self.page_controls: PageControls | None = None
        self.content: ContentArea | None = None
        self.callbacks: NavigationCallbacks | None = None
        logger.debug("ProjectView initialized successfully")

    def build(self):
        """Build the project view UI components."""
        logger.debug("Building ProjectView UI components")

        # Root container for the entire project view
        with ui.column().classes("w-full h-full") as self._root:
            # Set up navigation callbacks
            self.callbacks = NavigationCallbacks(
                save_page=self._save_page_async,
                load_page=self._load_page_async,
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
            )
            self.page_controls.build()
            logger.debug("Page controls built")

            # Content area (images and text)
            # Note: ContentArea still takes the old state - this will need to be updated
            # For now, we'll access the state through the viewmodel
            if hasattr(self.viewmodel, "_project_state"):
                self.content = ContentArea(
                    self.viewmodel._project_state.current_page_state, self.callbacks
                )
                self.content.build()
                logger.debug("Content area built")

        logger.debug("ProjectView UI build completed")
        self.mark_as_built()
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

        # Images and text
        if not loading:
            logger.debug("Not loading, updating images")
            self._update_images()
        else:
            logger.debug("Still loading, skipping image update")

    def _prep_image_spinners(self):
        """Hide images during navigation transitions."""
        logger.debug("Preparing image spinners for navigation transition")
        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():  # noqa: F841
                if img:
                    img.set_visibility(False)
                    logger.debug("Hidden image: %s", name)
        logger.debug("Image spinners preparation completed")

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
            return
        logger.debug("Navigating to previous page")
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.viewmodel.command_navigate_prev()
        logger.debug("Previous page navigation completed")

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            return
        logger.debug("Navigating to next page")
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.viewmodel.command_navigate_next()
        logger.debug("Next page navigation completed")

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if self.viewmodel.is_project_loading:
            logger.debug("Navigation blocked - currently loading")
            return
        logger.debug("Navigating to page: %s", value)
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self._goto_page(value)
        logger.debug("Goto page navigation completed for value: %s", value)

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Save blocked - currently loading")
            return

        # Note: Save functionality needs to be implemented in the viewmodel
        # For now, we'll access the underlying state
        if hasattr(self.viewmodel, "_project_state"):
            page = self.viewmodel._project_state.current_page()
            if not page:
                logger.warning("No current page to save")
                ui.notify("No current page to save", type="warning")
                return

            logger.debug(
                "Starting async save for page: %s", page.name if page else "unknown"
            )
            try:
                # Run save in background thread to avoid blocking UI
                success = await asyncio.to_thread(
                    self.viewmodel._project_state.save_current_page,
                )

                if success:
                    logger.info(
                        "Page saved successfully: %s", page.name if page else "unknown"
                    )
                    ui.notify("Page saved successfully", type="positive")
                else:
                    logger.warning(
                        "Failed to save page: %s", page.name if page else "unknown"
                    )
                    ui.notify("Failed to save page", type="negative")

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Save failed for page %s: %s", page.name if page else "unknown", exc
                )
                ui.notify(f"Save failed: {exc}", type="negative")

    async def _load_page_async(self):  # pragma: no cover - UI side effects
        """Load the current page from saved files asynchronously."""
        if self.viewmodel.is_project_loading:
            logger.debug("Load blocked - currently loading")
            return

        logger.debug("Starting async load for current page")
        try:
            # Note: Load functionality needs to be implemented in the viewmodel
            # For now, we'll access the underlying state
            if hasattr(self.viewmodel, "_project_state"):
                # Run load in background thread to avoid blocking UI
                success = await asyncio.to_thread(
                    self.viewmodel._project_state.load_current_page,
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

    def _on_viewmodel_property_changed(self, property_name: str, value: Any):
        """Handle view model property changes by refreshing the view."""
        logger.debug(f"View model property changed: {property_name} = {value}")
        self.refresh()
