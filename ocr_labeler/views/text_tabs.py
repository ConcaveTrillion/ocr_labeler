from nicegui import ui

from ..state.operations.page_operations import PageOperations
from .word_match import WordMatchView


class TextTabs:
    """Right side textual data tabs (Matches placeholder, Ground Truth, OCR)."""

    def __init__(self, state=None, on_save_page=None, on_load_page=None):
        self._page_operations = PageOperations()
        # Keep attribute names for external references, but these will hold code_editor instances.
        self.gt_text = None  # type: ignore[assignment]
        self.ocr_text = None  # type: ignore[assignment]
        self.state = state
        # Keep for backward compatibility but no longer used
        self._on_save_page = on_save_page
        self._on_load_page = on_load_page

        # Create callback for GT→OCR copy functionality
        copy_callback = None
        if state and hasattr(state, "page_state"):
            # Create a wrapper that passes the current page index
            def copy_gt_callback(line_index: int) -> bool:
                return state.project_state.copy_ground_truth_to_ocr(line_index)

            copy_callback = copy_gt_callback

        self.word_match_view = WordMatchView(copy_gt_to_ocr_callback=copy_callback)
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
                        if self.state and hasattr(self.state, "project_state"):
                            self.gt_text.bind_value_from(
                                self.state.project_state, "current_gt_text"
                            )
                # OCR panel
                with ui.tab_panel("OCR").classes("full-width full-height column"):
                    with ui.column().classes("full-width full-height"):
                        self.ocr_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
                        if self.state and hasattr(self.state, "project_state"):
                            self.ocr_text.bind_value_from(
                                self.state.project_state, "current_ocr_text"
                            )
            self._tabs = text_tabs
        self.container = col
        return col

    # --- public helpers -------------------------------------------------
    def update_text(self, state):
        page = state.project_state.current_page()
        if not page:
            if hasattr(self, "word_match_view") and self.word_match_view:
                self.word_match_view.clear()
            return

        # Update word match view
        if hasattr(self, "word_match_view") and self.word_match_view:
            self.word_match_view.update_from_page(page)
