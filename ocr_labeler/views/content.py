from __future__ import annotations
from nicegui import ui
from .page_controls import PageControls
from .tabs import ImageTabs, TextTabs

if True:  # pragma: no cover
    class ContentArea:
        """Page controls + splitter containing image & text tabs."""

        def __init__(self, state, callbacks):
            self.state = state
            self.callbacks = callbacks
            self.page_controls: PageControls | None = None
            self.image_tabs = ImageTabs()
            self.text_tabs = TextTabs()
            self.splitter = None
            self.page_spinner = None  # spinner shown during page-level navigation/OCR
            self.root = None

        def build(self):
            with ui.column().classes("w-full h-full gap-2") as root:
                self.root = root
                self.page_controls = PageControls(
                    self.state,
                    on_prev=self.callbacks['prev'],
                    on_next=self.callbacks['next'],
                    on_goto=self.callbacks['goto'],
                )
                self.page_controls.build()
                # Page-level navigation spinner (smaller, inline)
                self.page_spinner = (
                    ui.spinner(size="lg")
                    .props("color=primary")
                    .classes("self-center my-6 hidden")
                )
                with ui.splitter(value=65).classes("w-full h-[calc(100vh-170px)]") as main_split:
                    self.splitter = main_split
                    with main_split.before:
                        self.image_tabs.build()
                    with main_split.after:
                        self.text_tabs.build()
            return root
