from __future__ import annotations

import logging

from nicegui import ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel
from ...callbacks import NavigationCallbacks
from .image_tabs import ImageTabs
from .text_tabs import TextTabs

logger = logging.getLogger(__name__)


class ContentArea:
    """Image & text tabs content area (page controls moved to separate component)."""

    def __init__(
        self, page_state_viewmodel: PageStateViewModel, callbacks: NavigationCallbacks
    ):
        logger.debug("Initializing ContentArea")
        self.page_state_viewmodel = page_state_viewmodel
        self.callbacks = callbacks
        logger.debug("Creating ImageTabs component")
        self.image_tabs = ImageTabs(page_state_viewmodel=self.page_state_viewmodel)
        logger.debug("Creating TextTabs component")
        self.text_tabs = TextTabs(
            page_state=self.page_state_viewmodel._page_state,
            on_save_page=None,  # Moved to PageControls
            on_load_page=None,  # Moved to PageControls
        )
        self.splitter = None
        self.page_spinner = None  # spinner shown during page-level navigation/OCR
        self.root = None
        logger.debug("ContentArea initialization complete")

    def build(self):
        logger.debug("Building ContentArea UI components")
        with ui.column().classes("w-full h-full gap-2") as root:
            self.root = root
            logger.debug("Adding page-level navigation spinner")
            # Page-level navigation spinner (smaller, inline)
            self.page_spinner = (
                ui.spinner(size="lg")
                .props("color=primary")
                .classes("self-center my-6 hidden")
            )
            logger.debug("Creating main splitter with 50/50 split")
            # Start with a 50/50 split between image and text tabs as requested
            with (
                ui.splitter(value=50).classes(
                    "w-full h-[calc(100vh-220px)]"  # Adjusted height since page controls moved out
                ) as main_split
            ):
                self.splitter = main_split
                logger.debug("Building image tabs in splitter before section")
                with main_split.before:
                    self.image_tabs.build()
                logger.debug("Building text tabs in splitter after section")
                with main_split.after:
                    self.text_tabs.build()
        logger.debug("ContentArea build complete, returning root: %s", root)
        return root
