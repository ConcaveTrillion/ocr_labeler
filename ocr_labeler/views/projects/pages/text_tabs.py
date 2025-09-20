import logging

from nicegui import binding, ui

from ....state import PageState
from .word_match import WordMatchView

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class TextTabsModel:
    """Holds references to the text editor data from page state. Don't directly bind to page state, bindable properties avoid tight coupling with state management classes."""

    _page_state: PageState | None = None
    gt_text: str = ""  # Ground Truth text
    ocr_text: str = ""  # OCR text

    def __init__(self, page_state: PageState | None = None):
        logger.debug(
            f"Initializing TextTabsModel with page_state: {page_state is not None}"
        )
        self._page_state = page_state
        if self._page_state:
            logger.debug("Registering page state change listener")
            self._page_state.on_change.append(self._on_page_state_change)
            logger.debug("Registered page state change listener")
        self.update()

    def __setattr__(self, name: str, value):
        """Intercept attribute changes to propagate to PageState."""
        super().__setattr__(name, value)
        if name == "gt_text" and self._page_state:
            logger.debug(f"Propagating GT text change to PageState: '{value[:50]}...'")
            self._page_state.current_gt_text = value
        elif name == "ocr_text" and self._page_state:
            logger.debug(f"Propagating OCR text change to PageState: '{value[:50]}...'")
            self._page_state.current_ocr_text = value

    def update(self):
        """Sync model from PageState."""
        logger.debug("Updating TextTabsModel from PageState")
        if self._page_state:
            self.gt_text = self._page_state.current_gt_text
            self.ocr_text = self._page_state.current_ocr_text
            logger.debug(f"GT text updated to: '{self.gt_text[:50]}...'")
            logger.debug(f"OCR text updated to: '{self.ocr_text[:50]}...'")
        else:
            logger.debug("No page state available, clearing text")
            self.gt_text = ""
            self.ocr_text = ""

    def _on_page_state_change(self):
        """Listener for PageState changes; update model properties."""
        logger.debug("PageState change detected, updating model")
        self.update()


class TextTabs:
    """Right side textual data tabs (Matches placeholder, Ground Truth, OCR)."""

    def __init__(
        self,
        page_state: PageState | None = None,
        page_index=0,
        on_save_page=None,
        on_load_page=None,
    ):
        logger.info(f"Initializing TextTabs for page {page_index}")
        logger.debug(f"Page state provided: {page_state is not None}")
        self.page_state = page_state
        self.page_index = page_index

        # Instantiate the model as the intermediary
        self.model = TextTabsModel(page_state)

        # Set the page index on the page_state so it knows which page to cache
        if page_state:
            page_state._current_page_index = page_index
            logger.debug(f"Set current page index to {page_index}")

        # Create callback for GT→OCR copy functionality
        copy_callback = None
        if page_state:
            # Create a wrapper that passes the current page index
            def copy_gt_callback(line_index: int) -> bool:
                logger.debug(
                    f"Copying GT to OCR for line {line_index} on page {page_index}"
                )
                result = page_state.copy_ground_truth_to_ocr(page_index, line_index)
                logger.debug(f"Copy operation result: {result}")
                return result

            copy_callback = copy_gt_callback
            logger.debug("Created GT to OCR copy callback")

        self.word_match_view = WordMatchView(copy_gt_to_ocr_callback=copy_callback)
        self.container = None
        self._tabs = None

    def build(self):
        logger.info("Building TextTabs UI components")
        # Root container uses Quasar growth classes; so flex children can shrink.
        # Root must be flex container with so nested 100% heights can resolve
        with ui.column().classes("full-width full-height") as col:
            logger.debug("Creating tabs container")
            with ui.tabs() as text_tabs:
                ui.tab("Matches")
                ui.tab("Ground Truth")
                ui.tab("OCR")
            # Panels area should expand to fill remaining height (col makes it flex already).
            logger.debug("Creating tab panels")
            with ui.tab_panels(text_tabs, value="Matches").classes(
                "full-width full-height column"
            ):
                # Matches panel with word matching view
                with ui.tab_panel("Matches").classes("full-width full-height column"):
                    logger.debug("Building word match view")
                    self.word_match_view.build()
                # Ground Truth panel
                with ui.tab_panel("Ground Truth").classes(
                    "full-width full-height column"
                ):
                    logger.debug("Building ground truth panel")
                    with ui.column().classes("full-width full-height"):
                        self.gt_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
                        # Bind to model instead of page_state
                        self.gt_text.bind_value(self.model, "gt_text")
                        logger.debug("Bound GT text editor to model")
                # OCR panel
                with ui.tab_panel("OCR").classes("full-width full-height column"):
                    logger.debug("Building OCR panel")
                    with ui.column().classes("full-width full-height"):
                        self.ocr_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
                        # Bind to model instead of page_state
                        self.ocr_text.bind_value(self.model, "ocr_text")
                        logger.debug("Bound OCR text editor to model")
            self._tabs = text_tabs
        self.container = col
        logger.info("TextTabs UI build completed")
        return col
