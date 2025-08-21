from __future__ import annotations
from nicegui import ui

if True:  # pragma: no cover
    class ImageTabs:
        """Left side image tabs with image elements."""

        def __init__(self):
            self._tab_ids = ["Original", "Paragraphs", "Lines", "Words", "Mismatches"]
            # image refs
            self.images = {}
            self.container = None

        def build(self):
            with ui.column().classes("w-full h-full") as col:
                with ui.tabs() as tabs:
                    for name in self._tab_ids:
                        ui.tab(name)
                with ui.tab_panels(tabs, value="Original").classes("w-full h-full"):
                    for name in self._tab_ids:
                        with ui.tab_panel(name):
                            with ui.column().classes("items-center justify-center w-full h-full"):
                                img = ui.image().props("fit=contain").classes("max-h-full")
                                self.images[name] = img
            self.container = col
            return col

    class TextTabs:
        """Right side text tabs (ground truth + OCR)."""

        def __init__(self):
            self.gt_text = None
            self.ocr_text = None
            self.container = None

        def build(self):
            with ui.column().classes("w-full h-full") as col:
                with ui.tabs() as text_tabs:
                    ui.tab("Matches")
                    ui.tab("Ground Truth")
                    ui.tab("OCR")
                with ui.tab_panels(text_tabs, value="Matches").classes("w-full h-full"):
                    with ui.tab_panel("Matches"):
                        pass  # Placeholder for future match text tab
                    with ui.tab_panel("Ground Truth"):
                        self.gt_text = ui.textarea(label="", value="", placeholder="No Ground Truth Text") \
                            .props("outlined readonly autogrow") \
                            .classes("w-full h-full") \
                            .style("font-family: monospace; white-space: pre; overflow:auto;")
                    with ui.tab_panel("OCR"):
                        self.ocr_text = ui.textarea(label="", value="", placeholder="No OCR Text") \
                            .props("outlined readonly autogrow") \
                            .classes("w-full h-full") \
                            .style("font-family: monospace; white-space: pre; overflow:auto;")
            self.container = col
            return col
