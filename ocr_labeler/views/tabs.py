from nicegui import ui


class ImageTabs:
    """Left side image tabs showing progressively processed page imagery."""

    def __init__(self):
        self._tab_ids = ["Original", "Paragraphs", "Lines", "Words", "Mismatches"]
        self.images: dict[str, ui.image] = {}
        self.container = None

    def build(self):
        # Root column uses Quasar full-height/width utility classes.
        with ui.column().classes("full-width full-height") as col:
            with ui.tabs().props("dense no-caps shrink") as tabs:
                for name in self._tab_ids:
                    ui.tab(name).props("ripple")
            # Tab panels fill available space; each panel centers its image.
            with ui.tab_panels(tabs, value="Original").classes(
                "full-width full-height"
            ):
                for name in self._tab_ids:
                    with ui.tab_panel(name).classes("column full-width full-height"):
                        with ui.column().classes(
                            "items-center justify-center full-width full-height"
                        ):
                            img = (
                                ui.image()
                                .props(
                                    "fit=contain no-spinner"
                                )  # rely on intrinsic container sizing
                                .classes("full-width full-height")
                            )
                            self.images[name] = img
        self.container = col
        return col


class TextTabs:
    """Right side textual data tabs (Matches placeholder, Ground Truth, OCR)."""

    def __init__(self):
        # Keep attribute names for external references, but these will hold code_editor instances.
        self.gt_text = None  # type: ignore[assignment]
        self.ocr_text = None  # type: ignore[assignment]
        self.container = None
        self._tabs = None

    def build(self):
        # Root container uses Quasar growth classes; so flex children can shrink.
        # Root must be flex container with so nested 100% heights can resolve
        with ui.column().classes("full-width full-height") as col:
            with ui.tabs() as text_tabs:
                ui.tab("Matches")
                ui.tab("Ground Truth")
                ui.tab("OCR")
            # Panels area should expand to fill remaining height (col makes it flex already).
            with ui.tab_panels(text_tabs, value="Matches").classes(
                "full-width full-height column"
            ):
                # Matches placeholder
                with ui.tab_panel("Matches").classes("full-width full-height column"):
                    ui.label("(Not implemented yet)").classes("text-caption text-grey")
                # Ground Truth panel
                with ui.tab_panel("Ground Truth").classes(
                    "full-width full-height column"
                ):
                    with ui.column().classes("full-width full-height"):
                        self.gt_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
                # OCR panel
                with ui.tab_panel("OCR").classes("full-width full-height column"):
                    with ui.column().classes("full-width full-height"):
                        self.ocr_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
            self._tabs = text_tabs
        self.container = col
        return col

    # --- public helpers -------------------------------------------------
    def set_ocr_text(self, text: str):
        if self.ocr_text is not None:
            self.ocr_text.set_value(text or "")

    def set_ground_truth_text(self, text: str):
        if self.gt_text is not None:
            self.gt_text.set_value(text or "")
