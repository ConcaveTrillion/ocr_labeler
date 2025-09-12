from nicegui import ui
from ..state.ground_truth import find_ground_truth_text
from .word_match import WordMatchView


class TextTabs:
    """Right side textual data tabs (Matches placeholder, Ground Truth, OCR)."""

    def __init__(self):
        # Keep attribute names for external references, but these will hold code_editor instances.
        self.gt_text = None  # type: ignore[assignment]
        self.ocr_text = None  # type: ignore[assignment]
        self.word_match_view = WordMatchView()
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
                # Matches panel with word matching view
                with ui.tab_panel("Matches").classes("full-width full-height column"):
                    self.word_match_view.build()
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

    def update_text(self, state):
        page = state.project_state.current_page()
        if not page:
            if hasattr(self, "ocr_text") and self.ocr_text:
                self.set_ocr_text("")
            if hasattr(self, "gt_text") and self.gt_text:
                self.set_ground_truth_text("")
            if hasattr(self, "word_match_view") and self.word_match_view:
                self.word_match_view.clear()
            return
        if hasattr(self, "ocr_text") and self.ocr_text:
            self.set_ocr_text(getattr(page, 'text', '') or '')
        if hasattr(page, 'ground_truth_text'):
            gt = (getattr(page, 'ground_truth_text', '') or '')
            if not gt.strip():
                try:
                    name = getattr(page, 'name', '')
                    gt_lookup = find_ground_truth_text(name, state.project_state.project.ground_truth_map)
                    if gt_lookup:
                        gt = gt_lookup
                        page.add_ground_truth(gt_lookup)
                except Exception:
                    pass
            if hasattr(self, "set_ground_truth_text"):
                self.set_ground_truth_text(gt if gt.strip() else '')
        
        # Update word match view
        if hasattr(self, "word_match_view") and self.word_match_view:
            self.word_match_view.update_from_page(page)
