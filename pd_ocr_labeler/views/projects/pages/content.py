from __future__ import annotations

import logging

from nicegui import ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel
from ...callbacks import PageActionCallbacks
from .image_tabs import ImageTabs
from .text_tabs import TextTabs

logger = logging.getLogger(__name__)


class ContentArea:
    """Image & text tabs content area (actions separated into page actions)."""

    def __init__(
        self, page_state_view_model: PageStateViewModel, callbacks: PageActionCallbacks
    ):
        logger.debug("Initializing ContentArea")
        self.page_state_view_model = page_state_view_model
        self.callbacks = callbacks
        logger.debug("Creating TextTabs component")
        self.text_tabs = TextTabs(
            page_state=self.page_state_view_model._page_state,
            original_image_source_provider=lambda: str(
                self.page_state_view_model.word_view_original_image_source or ""
            ),
            word_image_page_index_provider=lambda: int(
                self.page_state_view_model.word_view_image_page_index or -1
            ),
            on_save_page=None,  # Moved to PageActions
            on_load_page=None,  # Moved to PageActions
        )
        self.page_state_view_model.set_word_view_image_ready_callback(
            self._on_word_view_image_ready
        )
        logger.debug("Creating ImageTabs component")
        self.image_tabs = ImageTabs(
            page_state_view_model=self.page_state_view_model,
            on_words_selected=self._on_words_selected,
            on_paragraphs_selected=self._on_paragraphs_selected,
            on_word_rebox_drawn=self._on_word_rebox_drawn,
            on_word_add_drawn=self._on_word_add_drawn,
            on_erase_rect_drawn=self._on_erase_rect_drawn,
        )
        self.text_tabs.word_match_view.selection.set_selection_change_callback(
            self._on_right_panel_words_selected
        )
        self.text_tabs.word_match_view.selection.set_paragraph_selection_change_callback(
            self._on_right_panel_paragraphs_selected
        )
        self.text_tabs.word_match_view.bbox.set_rebox_request_callback(
            self._on_right_panel_word_rebox_requested
        )
        self.text_tabs.word_match_view.bbox.set_add_word_request_callback(
            self._on_right_panel_add_word_requested
        )
        self.text_tabs.word_match_view.set_summary_callback(self._update_stats_label)
        if callbacks.refine_bboxes:
            self.text_tabs.word_match_view.set_refine_bboxes_callback(
                callbacks.refine_bboxes
            )
        if callbacks.expand_refine_bboxes:
            self.text_tabs.word_match_view.set_expand_refine_bboxes_callback(
                callbacks.expand_refine_bboxes
            )
        self.page_state_view_model.set_image_update_callback(self._on_images_updated)
        self._stats_label = None
        self.splitter = None
        self.page_spinner = None  # spinner shown during page-level navigation/OCR
        self.root = None
        logger.debug("ContentArea initialization complete")

    def _update_stats_label(self, text: str) -> None:
        if self._stats_label:
            model_summary = (
                getattr(self.page_state_view_model, "current_page_ocr_models_text", "")
                or ""
            ).strip()
            if model_summary:
                self._stats_label.set_text(f"{text} • {model_summary}")
            else:
                self._stats_label.set_text(text)

    def _on_images_updated(self, image_dict: dict[str, str]) -> None:
        """Fan out image updates to left image tabs and right word-match slices."""
        self.image_tabs._on_images_updated(image_dict)
        self.text_tabs.word_match_view.bbox.on_image_sources_updated(image_dict)

    def _on_words_selected(self, selection: set[tuple[int, int]]) -> None:
        """Propagate image-driven word selection to the Matches view."""
        self.text_tabs.word_match_view.selection.set_selected_words(selection)

    def _on_right_panel_words_selected(self, selection: set[tuple[int, int]]) -> None:
        """Propagate right-panel word selection to image overlay."""
        self.image_tabs.set_selected_words(selection)

    def _on_paragraphs_selected(self, selection: set[int]) -> None:
        """Propagate image-driven paragraph selection to the Matches view."""
        self.text_tabs.word_match_view.selection.set_selected_paragraphs(selection)

    def _on_right_panel_paragraphs_selected(self, selection: set[int]) -> None:
        """Propagate right-panel paragraph selection to image overlay."""
        self.image_tabs.set_selected_paragraphs(selection)

    def _on_right_panel_word_rebox_requested(
        self,
        line_index: int,
        word_index: int,
    ) -> None:
        """Enable image-side rebox drawing after per-word action request."""
        _ = (line_index, word_index)
        self.image_tabs.enable_word_rebox_mode()

    def _on_right_panel_add_word_requested(self) -> None:
        """Enable image-side add-word drawing mode."""
        self.image_tabs.enable_word_add_mode()

    def _on_word_rebox_drawn(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        """Apply drawn image rectangle to the pending word rebox target."""
        self.text_tabs.word_match_view.bbox.apply_rebox_bbox(x1, y1, x2, y2)

    def _on_word_add_drawn(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        """Apply drawn image rectangle as a new word insertion."""
        self.text_tabs.word_match_view.bbox.apply_add_word_bbox(x1, y1, x2, y2)

    def _on_erase_rect_drawn(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        """Apply drawn image rectangle as an in-place pixel erase."""
        callback = self.text_tabs.word_match_view.erase_pixels_rect_callback
        if callback is None:
            self.text_tabs.word_match_view._safe_notify(
                "Erase pixels is not available",
                type_="warning",
            )
            return

        if not callback(x1, y1, x2, y2):
            self.text_tabs.word_match_view._safe_notify(
                "Failed to erase pixels",
                type_="warning",
            )

    def _on_word_view_image_ready(self, page_index: int, _source: str) -> None:
        """Notify text tabs when the page-matched word image source becomes available."""
        self.text_tabs.on_word_image_source_ready(page_index)

    def build(self):
        logger.debug("Building ContentArea UI components")
        with ui.column().classes("w-full h-full gap-2") as root:
            self.root = root
            logger.debug("Adding stats label row")
            with ui.row().classes("items-center gap-2"):
                ui.icon("analytics").classes("text-base text-gray-400")
                self._stats_label = ui.label("No matches to display").classes(
                    "text-sm text-gray-600"
                )
                self._export_status_sep = ui.label("•").classes("text-sm text-gray-400")
                self._export_status_sep.bind_visibility_from(
                    self.page_state_view_model,
                    "current_export_status_text",
                    backward=lambda t: bool(t),
                )
                self._export_status_label = ui.label("").classes(
                    "text-sm font-semibold text-blue-700"
                )
                self._export_status_label.bind_text_from(
                    self.page_state_view_model,
                    "current_export_status_text",
                )
                self._export_status_label.bind_visibility_from(
                    self.page_state_view_model,
                    "current_export_status_text",
                    backward=lambda t: bool(t),
                )

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
                    "w-full h-[calc(100vh-220px)]"  # Adjusted height since controls moved out
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
