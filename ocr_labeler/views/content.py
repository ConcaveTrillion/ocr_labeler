from __future__ import annotations

import asyncio

from nicegui import ui

from .callbacks import NavigationCallbacks
from .image_tabs import ImageTabs
from .page_controls import PageControls
from .text_tabs import TextTabs


class ContentArea:
    """Page controls + splitter containing image & text tabs."""

    def __init__(self, state, callbacks: NavigationCallbacks):
        self.state = state
        self.callbacks = callbacks
        self.page_controls: PageControls | None = None
        self.image_tabs = ImageTabs()
        self.text_tabs = TextTabs(state)
        self.splitter = None
        self.page_spinner = None  # spinner shown during page-level navigation/OCR
        self.root = None

    def build(self):
        with ui.column().classes("w-full h-full gap-2") as root:
            self.root = root
            self.page_controls = PageControls(
                self.state,
                on_prev=self._prev_async,
                on_next=self._next_async,
                on_goto=self._goto_async,
                on_save_page=self.callbacks.save_page,
                on_load_page=self.callbacks.load_page,
            )
            self.page_controls.build()
            # Page-level navigation spinner (smaller, inline)
            self.page_spinner = (
                ui.spinner(size="lg")
                .props("color=primary")
                .classes("self-center my-6 hidden")
            )
            # Start with a 50/50 split between image and text tabs as requested
            with ui.splitter(value=50).classes(
                "w-full h-[calc(100vh-170px)]"
            ) as main_split:
                self.splitter = main_split
                with main_split.before:
                    self.image_tabs.build()
                with main_split.after:
                    self.text_tabs.build()
        return root

    # ------------------------------------------------------------ navigation methods
    def _prep_image_spinners(self):
        """Hide images during navigation transitions."""
        for name, img in self.image_tabs.images.items():  # noqa: F841
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
        self.state.project_state.goto_page_number(n)

    async def _prev_async(self):  # pragma: no cover - UI side effects
        """Navigate to previous page."""
        if getattr(self.state, "is_loading", False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.state.project_state.prev_page()

    async def _next_async(self):  # pragma: no cover - UI side effects
        """Navigate to next page."""
        if getattr(self.state, "is_loading", False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.state.project_state.next_page()

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        """Navigate to specific page."""
        if getattr(self.state, "is_loading", False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self._goto_page(value)
