from __future__ import annotations

import asyncio
from pathlib import Path

from nicegui import ui

from ..state import AppState
from .callbacks import NavigationCallbacks
from .content import ContentArea
from .header import HeaderBar


class LabelerView:  # pragma: no cover - heavy UI wiring
    """Composite main view orchestrating header + content areas."""

    def __init__(self, state: AppState):
        self.state = state
        self.state.on_change = self.refresh
        self.header_bar: HeaderBar | None = None
        self.content: ContentArea | None = None
        self._no_project_placeholder = None
        self._global_loading = None

    # ------------------------------------------------------------ mount
    def mount(self):
        self.header_bar = HeaderBar(self.state)
        self.header_bar.build()

        callbacks = NavigationCallbacks(
            save_page=self._save_page_async,
            load_page=self._load_page_async,
        )
        self.content = ContentArea(self.state, callbacks)
        self.content.build()

        # Placeholder shown before any project has been loaded
        self._no_project_placeholder = ui.column().classes(
            "w-full h-[calc(100vh-160px)] items-center justify-center text-gray-500 gap-2 hidden"
        )
        with self._no_project_placeholder:  # type: ignore
            ui.icon("folder_open").classes("text-4xl opacity-40")
            ui.label("No Project Loaded").classes("text-lg font-medium")
            ui.label("Select a project above and click LOAD to begin.")

        # Global project-loading spinner (centered overlay)
        self._global_loading = (
            ui.spinner(size="xl")
            .props("color=primary")
            .classes(
                "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-40 pointer-events-none hidden"
            )
        )

        self.refresh()

    # ------------------------------------------------------------ actions
    async def _open_project_from_path(self, path: Path):
        try:
            await self.state.load_project(path)
            if self.header_bar:
                self.header_bar.project_controls.update_path_label()
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Open failed: {exc}", type="negative")

    async def _save_page_async(self):  # pragma: no cover - UI side effects
        """Save the current page asynchronously."""
        if getattr(self.state, "is_loading", False):
            return

        page = self.state.project_state.current_page()
        if not page:
            ui.notify("No current page to save", type="warning")
            return

        try:
            # Run save in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.state.project_state.save_current_page
            )

            if success:
                ui.notify("Page saved successfully", type="positive")
            else:
                ui.notify("Failed to save page", type="negative")

        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Save failed: {exc}", type="negative")

    async def _load_page_async(self):  # pragma: no cover - UI side effects
        """Load the current page from saved files asynchronously."""
        if getattr(self.state, "is_loading", False):
            return

        try:
            # Run load in background thread to avoid blocking UI
            success = await asyncio.to_thread(
                self.state.project_state.load_current_page
            )

            if success:
                ui.notify("Page loaded successfully", type="positive")
                # Trigger UI refresh to show loaded page
                self.refresh()
            else:
                ui.notify("No saved page found for current page", type="warning")

        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Load failed: {exc}", type="negative")

    # ------------------------------------------------------------ refresh
    def refresh(self):
        loading = getattr(self.state, "is_loading", False)
        project_loading = getattr(self.state, "is_project_loading", False)
        # Avoid calling current_page() while loading; it would synchronously create the page
        # and block the UI, defeating async navigation. We'll treat page as None until
        # background thread populates current page and loading flips False.
        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = self.state.project_state.current_page_index
        image_name = ""
        if 0 <= current_index < len(self.state.project_state.project.image_paths):
            image_name = self.state.project_state.project.image_paths[
                current_index
            ].name
        page = None if loading else self.state.project_state.current_page()
        total = len(self.state.project_state.project.pages)

        # Update project path label (keep header visible even while loading)
        if self.header_bar:
            self.header_bar.project_controls.update_path_label()

        # Toggle global spinner
        if self._global_loading:
            if project_loading:
                self._global_loading.classes(remove="hidden")
            else:
                self._global_loading.classes(add="hidden")

        # Content & placeholder visibility
        no_project = not getattr(self.state.project_state.project, "image_paths", [])
        if self.content and self.content.root:
            # Keep overall root visible once a project is loaded; hide entirely only if no project.
            if no_project:
                self.content.root.classes(add="hidden")
            else:
                self.content.root.classes(remove="hidden")
            # Toggle splitter vs spinners
            if self.content.splitter and self.content.page_spinner:
                if project_loading:
                    self.content.splitter.classes(add="hidden")
                    self.content.page_spinner.classes(add="hidden")
                elif loading:  # page-level
                    self.content.splitter.classes(add="hidden")
                    self.content.page_spinner.classes(remove="hidden")
                else:
                    self.content.splitter.classes(remove="hidden")
                    self.content.page_spinner.classes(add="hidden")
        if self._no_project_placeholder:
            if no_project and not loading:
                self._no_project_placeholder.classes(remove="hidden")
            else:
                self._no_project_placeholder.classes(add="hidden")

        # Page meta
        if self.content and self.content.page_controls:
            if total:
                # Use immediate index+1 and image filename while OCR loads
                display_index = current_index + 1 if current_index >= 0 else 1
                display_name = image_name or (page.name if page else "(no page)")
                self.content.page_controls.set_page(display_index, display_name, total)
            else:
                self.content.page_controls.set_page(1, "(no page)", 0)

        # Images and text
        if not loading:
            self._update_images()
            self._update_text()

    # --- refactored: delegate image/text update to tabs.py ---
    def _update_images(self):
        if self.content and hasattr(self.content, "image_tabs"):
            self.content.image_tabs.update_images(self.state)

    def _update_text(self):
        if self.content and hasattr(self.content, "text_tabs"):
            self.content.text_tabs.update_text(self.state)
