import logging

from nicegui import binding, ui
from pd_book_tools.ocr.page import Page

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

    # Only propagate one-way from PageState to model
    #
    # def __setattr__(self, name: str, value):
    #     """Intercept attribute changes to propagate to PageState."""
    #     super().__setattr__(name, value)
    #     if name == "gt_text" and self._page_state:
    #         logger.debug(f"Propagating GT text change to PageState: '{value[:50]}...'")
    #         self._page_state.current_gt_text = value
    #     elif name == "ocr_text" and self._page_state:
    #         logger.debug(f"Propagating OCR text change to PageState: '{value[:50]}...'")
    #         self._page_state.current_ocr_text = value

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
        # Notify TextTabs that state changed so it can update word matches
        logger.debug(
            f"Checking for callback: hasattr={hasattr(self, '_on_state_change_callback')}, "
            f"is_set={getattr(self, '_on_state_change_callback', None) is not None}"
        )
        if (
            hasattr(self, "_on_state_change_callback")
            and self._on_state_change_callback
        ):
            logger.debug("Calling TextTabs state change callback")
            self._on_state_change_callback()
        else:
            # Only log as debug in case this is a test scenario with mocks
            logger.debug("TextTabs callback not set or not callable")


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

        # Register callback so model can notify us of state changes
        # Do this BEFORE any updates so callbacks work from the start
        self.model._on_state_change_callback = self._on_page_state_changed

        # Set the page index on the page_state so it knows which page to cache
        if page_state:
            page_state._current_page_index = page_index
            logger.debug(f"Set current page index to {page_index}")

        # Also listen to ProjectState changes for navigation events
        # PageState has a reference to ProjectState, so we can register there too
        if (
            page_state
            and hasattr(page_state, "_project_state")
            and page_state._project_state
        ):
            logger.debug("Registering ProjectState change listener")
            page_state._project_state.on_change.append(self._on_project_state_changed)
            logger.debug("Registered ProjectState change listener")

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

        notify_callback = None
        if (
            page_state
            and hasattr(page_state, "_project_state")
            and page_state._project_state
        ):

            def notify_callback(message: str, type_: str = "info") -> None:
                page_state._project_state.queue_notification(message, type_)

        self.word_match_view = WordMatchView(
            copy_gt_to_ocr_callback=copy_callback,
            notify_callback=notify_callback,
        )
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
                            "full-width full-height monospace"
                        )
                        # Don't use bind_value for large text - it's slow
                        # We'll update directly in _update_text_editors()
                        logger.debug("Created GT text editor (manual updates)")
                # OCR panel
                with ui.tab_panel("OCR").classes("full-width full-height column"):
                    logger.debug("Building OCR panel")
                    with ui.column().classes("full-width full-height"):
                        self.ocr_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height monospace"
                        )
                        # Don't use bind_value for large text - it's slow
                        # We'll update directly in _update_text_editors()
                        logger.debug("Created OCR text editor (manual updates)")
            self._tabs = text_tabs
        self.container = col
        logger.info("TextTabs UI build completed")

        # Update text editors with initial values from model
        self._update_text_editors()

        # Perform initial word match update if page is already available
        if self.page_state and hasattr(self.page_state, "current_page"):
            page = self.page_state.current_page
            if page:
                logger.debug("Performing initial word match update with current page")
                self.update_word_matches(page)
            else:
                logger.debug("No current page available at build time")

        return col

    def _update_text_editors(self):
        """Update text editor values directly (avoids slow binding propagation)."""
        if hasattr(self, "gt_text") and self.gt_text:
            self.gt_text.value = self.model.gt_text
        if hasattr(self, "ocr_text") and self.ocr_text:
            self.ocr_text.value = self.model.ocr_text

    def _on_page_state_changed(self):
        """Called when page state changes; update word matches automatically."""
        logger.debug("TextTabs received page state change notification")
        # Update text editors directly instead of relying on bindings
        self._update_text_editors()
        if self.page_state and hasattr(self.page_state, "current_page"):
            page = self.page_state.current_page
            logger.debug(f"Current page available: {page is not None}")
            self.update_word_matches(page)
        else:
            logger.debug("No page state or current_page available")
            self.update_word_matches(None)

    def _on_project_state_changed(self):
        """Called when project state changes (e.g., navigation); update word matches."""
        logger.debug("TextTabs received project state change notification")
        # Get the current page from the ProjectState
        if (
            self.page_state
            and hasattr(self.page_state, "_project_state")
            and self.page_state._project_state
        ):
            project_state = self.page_state._project_state
            page = project_state.current_page()
            logger.debug(f"Current page from ProjectState: {page is not None}")
            # Update the PageState's current_page reference so both are in sync
            if page is not None:
                self.page_state.current_page = page
            self.update_word_matches(page)
        else:
            logger.debug("No ProjectState reference available")
            self.update_word_matches(None)

    # ----- Word match coordination -------------------------------------------------

    def update_word_matches(self, page: Page | None):
        """Refresh the word match panel with the provided page data."""
        if not getattr(self, "word_match_view", None):
            logger.debug("Word match view not initialized; skipping update")
            return

        if page is None:
            logger.debug("No page available for word matches; clearing view")
            self.word_match_view.clear()
            return

        logger.debug(
            "Updating word matches for page: %s",
            getattr(page, "name", getattr(page, "index", "unknown")),
        )
        self.word_match_view.update_from_page(page)
