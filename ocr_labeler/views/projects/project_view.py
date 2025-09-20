from __future__ import annotations

import asyncio
import logging

from nicegui import ui

from ...state import ProjectState
from ..callbacks import NavigationCallbacks
from .pages.content import ContentArea
from .pages.page_controls import PageControls

logger = logging.getLogger(__name__)


class ProjectView:  # pragma: no cover - heavy UI wiring
    """Project-specific view handling navigation, content display, and page operations."""

    def __init__(self, project_state: ProjectState):
        project_id = ""
        if project_state:
            if hasattr(project_state, "project"):
                project_id = getattr(project_state.project, "project_id", "")
                if project_id == "":
                    project_id = "Project with Empty ID"
            else:
                project_id = "No Project"
        else:
            project_id = "No ProjectState"

        logger.debug("Initializing ProjectView with project ID: %s", project_id)
        self.project_state = project_state
        self.page_controls: PageControls | None = None
        self.content: ContentArea | None = None
        self.callbacks: NavigationCallbacks | None = None
        self.root = None
        logger.debug("ProjectView initialized successfully")

    def build(self):
        """Build the project view UI components."""
        logger.debug("Building ProjectView UI components")
        # Root container for the entire project view
        with ui.column().classes("w-full h-full") as root:
            self.root = root

            # Set up navigation callbacks
            self.callbacks = NavigationCallbacks(
                save_page=self._save_page_async,
                load_page=self._load_page_async,
            )
            logger.debug("Navigation callbacks initialized")

            # Page controls (navigation, save/load)
            self.page_controls = PageControls(
                self.project_state,
                on_prev=self._prev_async,
                on_next=self._next_async,
                on_goto=self._goto_async,
                on_save_page=self.callbacks.save_page if self.callbacks else None,
                on_load_page=self.callbacks.load_page if self.callbacks else None,
            )
            self.page_controls.build()
            logger.debug("Page controls built")

            # Content area (images and text)
            self.content = ContentArea(
                self.project_state.current_page_state, self.callbacks
            )
            self.content.build()
            logger.debug("Content area built")

        logger.debug("ProjectView UI build completed")
        return root

    def refresh(self):
        """Refresh the project view based on current state."""
        loading = self.project_state.is_loading
        logger.debug("Refreshing ProjectView - loading: %s", loading)

        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = self.project_state.current_page_index
        image_name = ""
        if 0 <= current_index < len(self.project_state.project.image_paths):
            image_name = self.project_state.project.image_paths[current_index].name
        page = None if loading else self.project_state.current_page()
        total = len(self.project_state.project.pages)

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
        self.project_state.goto_page_number(n)

    async def _prev_async(self):  # pragma: no cover - UI side effects
        """Navigate to previous page."""
        if self.project_state.is_loading:
            logger.debug("Navigation blocked - currently loading")
            return
        logger.debug("Navigating to previous page")
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.project_state.prev_page()
        logger.debug("Previous page navigation completed")

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        if self.project_state.is_loading:
            logger.debug("Navigation blocked - currently loading")
            return
        logger.debug("Navigating to next page")
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.project_state.next_page()
        logger.debug("Next page navigation completed")

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if self.project_state.is_loading:
            logger.debug("Navigation blocked - currently loading")
            return
        logger.debug("Navigating to page: %s", value)
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self._goto_page(value)
        logger.debug("Goto page navigation completed for value: %s", value)

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if self.project_state.is_loading:
            logger.debug("Save blocked - currently loading")
            return

        page = self.project_state.current_page()
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
                self.project_state.save_current_page,
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
        if self.project_state.is_loading:
            logger.debug("Load blocked - currently loading")
            return

        logger.debug("Starting async load for current page")
        try:
            # Run load in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.project_state.load_current_page,
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

    # --- refactored: delegate image/text update to tabs.py ---
    def _update_images(self):
        logger.debug("Updating images via content.image_tabs")
        if self.content and hasattr(self.content, "image_tabs"):
            self.content.image_tabs.update_images(self.project_state)
            logger.debug("Images updated successfully")
        else:
            logger.warning("Cannot update images - content or image_tabs not available")
