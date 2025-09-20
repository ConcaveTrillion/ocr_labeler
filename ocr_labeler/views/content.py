from __future__ import annotations

from nicegui import ui

from .callbacks import NavigationCallbacks
from .image_tabs import ImageTabs
from .text_tabs import TextTabs


class ContentArea:
    """Image & text tabs content area (page controls moved to separate component)."""

    def __init__(self, state, callbacks: NavigationCallbacks):
        self.state = state
        self.callbacks = callbacks
        self.image_tabs = ImageTabs()
        self.text_tabs = TextTabs(
            page_state=state.project_state.get_page_state(
                state.project_state.current_page_index
            ),
            page_index=state.project_state.current_page_index,
            on_save_page=None,  # Moved to PageControls
            on_load_page=None,  # Moved to PageControls
        )
        self.splitter = None
        self.page_spinner = None  # spinner shown during page-level navigation/OCR
        self.root = None

    def build(self):
        with ui.column().classes("w-full h-full gap-2") as root:
            self.root = root
            # Page-level navigation spinner (smaller, inline)
            self.page_spinner = (
                ui.spinner(size="lg")
                .props("color=primary")
                .classes("self-center my-6 hidden")
            )
            # Start with a 50/50 split between image and text tabs as requested
            with (
                ui.splitter(value=50).classes(
                    "w-full h-[calc(100vh-220px)]"  # Adjusted height since page controls moved out
                ) as main_split
            ):
                self.splitter = main_split
                with main_split.before:
                    self.image_tabs.build()
                with main_split.after:
                    self.text_tabs.build()
        return root
