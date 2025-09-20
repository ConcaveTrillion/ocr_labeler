from __future__ import annotations

import asyncio

from nicegui import ui

from ..state import AppState
from .callbacks import NavigationCallbacks
from .content import ContentArea
from .page_controls import PageControls


class ProjectView:  # pragma: no cover - heavy UI wiring
    """Project-specific view handling navigation, content display, and page operations."""

    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.page_controls: PageControls | None = None
        self.content: ContentArea | None = None
        self.callbacks: NavigationCallbacks | None = None
        self.root = None

    def build(self):
        """Build the project view UI components."""
        # Root container for the entire project view
        with ui.column().classes("w-full h-full") as root:
            self.root = root

            # Set up navigation callbacks
            self.callbacks = NavigationCallbacks(
                save_page=self._save_page_async,
                load_page=self._load_page_async,
            )

            # Page controls (navigation, save/load)
            self.page_controls = PageControls(
                self.app_state,
                on_prev=self._prev_async,
                on_next=self._next_async,
                on_goto=self._goto_async,
                on_save_page=self.callbacks.save_page if self.callbacks else None,
                on_load_page=self.callbacks.load_page if self.callbacks else None,
            )
            self.page_controls.build()

            # Content area (images and text)
            self.content = ContentArea(self.app_state, self.callbacks)
            self.content.build()

        return root

    def refresh(self):
        """Refresh the project view based on current state."""
        loading = getattr(self.app_state, "is_loading", False)

        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = self.app_state.project_state.current_page_index
        image_name = ""
        if 0 <= current_index < len(self.app_state.project_state.project.image_paths):
            image_name = self.app_state.project_state.project.image_paths[
                current_index
            ].name
        page = None if loading else self.app_state.project_state.current_page()
        total = len(self.app_state.project_state.project.pages)

        # Content visibility and loading states
        if self.content and self.content.root:
            # Toggle splitter vs spinners
            if self.content.splitter and self.content.page_spinner:
                if loading:  # page-level
                    self.content.splitter.classes(add="hidden")
                    self.content.page_spinner.classes(remove="hidden")
                else:
                    self.content.splitter.classes(remove="hidden")
                    self.content.page_spinner.classes(add="hidden")

        # Page meta
        if self.page_controls:
            if total:
                # Use immediate index+1 and image filename while OCR loads
                display_index = current_index + 1 if current_index >= 0 else 1
                display_name = image_name or (page.name if page else "(no page)")
                self.page_controls.set_page(display_index, display_name, total)
            else:
                self.page_controls.set_page(1, "(no page)", 0)

        # Images and text
        if not loading:
            self._update_images()
            self._update_text()

    def _prep_image_spinners(self):
        """Hide images during navigation transitions."""
        if self.content and hasattr(self.content, "image_tabs"):
            for name, img in self.content.image_tabs.images.items():  # noqa: F841
                if img:
                    img.set_visibility(False)

    def _goto_page(self, raw_value):
        """Navigate to a specific page number with validation."""
        try:
            n = int(raw_value)
        except Exception:  # noqa: BLE001
            n = 1
        if n < 1:
            n = 1
        self.app_state.project_state.goto_page_number(n)

    async def _prev_async(self):  # pragma: no cover - UI side effects
        """Navigate to previous page."""
        if getattr(self.app_state, "is_loading", False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.app_state.project_state.prev_page()

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        if getattr(self.app_state, "is_loading", False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.app_state.project_state.next_page()

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if getattr(self.app_state, "is_loading", False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self._goto_page(value)

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if getattr(self.app_state, "is_loading", False):
            return

        page = self.app_state.project_state.current_page()
        if not page:
            ui.notify("No current page to save", type="warning")
            return

        try:
            # Run save in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.app_state.project_state.save_current_page,
            )

            if success:
                ui.notify("Page saved successfully", type="positive")
            else:
                ui.notify("Failed to save page", type="negative")

        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Save failed: {exc}", type="negative")

    async def _load_page_async(self):  # pragma: no cover - UI side effects
        """Load the current page from saved files asynchronously."""
        if getattr(self.app_state, "is_loading", False):
            return

        try:
            # Run load in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.app_state.project_state.load_current_page,
            )

            if success:
                ui.notify("Page loaded successfully", type="positive")
                # Trigger UI refresh to show loaded page
                self.refresh()
            else:
                ui.notify("No saved page found for current page", type="warning")

        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Load failed: {exc}", type="negative")

    # --- refactored: delegate image/text update to tabs.py ---
    def _update_images(self):
        if self.content and hasattr(self.content, "image_tabs"):
            self.content.image_tabs.update_images(self.app_state)

    def _update_text(self):
        if self.content and hasattr(self.content, "text_tabs"):
            self.content.text_tabs.update_text(self.app_state)
