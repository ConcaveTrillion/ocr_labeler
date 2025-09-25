import logging

from nicegui import binding

from ..state import PageState

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class PageStateNiceGuiBinding:
    _page_state: PageState

    current_ocr_text: str = ""
    current_gt_text: str = ""
    page_source_text: str = ""

    def __init__(self, page_state: PageState):
        logger.debug(
            f"Initializing PageStateNiceGuiBinding with page_state: {page_state is not None}"
        )

        if page_state is not None and isinstance(page_state, PageState):
            self._page_state = page_state
            logger.debug("Registering page state change listener")
            self._page_state.on_change.append(self._on_page_state_change)
            logger.debug("Registered page state change listener")
        else:
            logger.error(
                "Page state of type PageState not provided to PageStateNiceGuiBinding!"
            )
            raise ValueError(
                "Page state of type PageState not provided to PageStateNiceGuiBinding!"
            )
        self.update()

    # Only propagate one-way from PageState to model, not vice versa
    def update(self):
        """Sync model from PageState via state change listener."""
        logger.debug("Updating PageStateNiceGuiBinding from PageState")
        if self._page_state:
            self.current_ocr_text = self._page_state.current_ocr_text
            self.current_gt_text = self._page_state.current_gt_text
            # Note: page_source_text would need current_page_index passed from outside
            # For now, we'll leave it as is or set a default
            self.page_source_text = "(UNKNOWN)"

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Current OCR text length: {len(self.current_ocr_text)}")
                logger.debug(f"Current GT text length: {len(self.current_gt_text)}")
                logger.debug(f"Page source text: {self.page_source_text}")
                logger.debug("PageStateNiceGuiBinding update complete")
        else:
            logger.error(
                "No page state available when updating PageStateNiceGuiBinding!"
            )
            raise ValueError(
                "No page state available when updating PageStateNiceGuiBinding!"
            )

    def update_page_source(self, page_index: int, is_loading: bool = False):
        """Update the page source text for a specific page index."""
        if self._page_state:
            self.page_source_text = self._page_state.get_page_source_text(
                page_index, is_loading
            )
            logger.debug(
                f"Updated page_source_text to '{self.page_source_text}' for page {page_index}"
            )

    def _on_page_state_change(self):
        """Listener for PageState changes; update model properties."""
        logger.debug("Page State change detected, updating model")
        self.update()
