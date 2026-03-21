"""Toolbar management for the word match view."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from nicegui import ui

from ...shared.button_styles import ButtonVariant, style_word_icon_button

if TYPE_CHECKING:
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)


class WordMatchToolbar:
    """Manages the actions toolbar and button state for WordMatchView."""

    def __init__(self, view: WordMatchView) -> None:
        self._view = view
        self._on_refine_bboxes: Callable | None = None
        self._on_expand_refine_bboxes: Callable | None = None
        # Button refs
        self.merge_lines_button = None
        self.delete_lines_button = None
        self.copy_gt_to_ocr_page_button = None
        self.copy_ocr_to_gt_page_button = None
        self.copy_gt_to_ocr_paragraphs_button = None
        self.copy_ocr_to_gt_paragraphs_button = None
        self.copy_gt_to_ocr_lines_button = None
        self.copy_ocr_to_gt_lines_button = None
        self.copy_gt_to_ocr_words_button = None
        self.copy_ocr_to_gt_words_button = None
        self.refine_lines_button = None
        self.expand_then_refine_lines_button = None
        self.merge_paragraphs_button = None
        self.delete_paragraphs_button = None
        self.refine_paragraphs_button = None
        self.expand_then_refine_paragraphs_button = None
        self.split_paragraph_after_line_button = None
        self.split_paragraph_by_selection_button = None
        self.split_line_after_word_button = None
        self.split_line_by_selection_button = None
        self.extract_line_from_selection_button = None
        self.merge_words_button = None
        self.delete_words_button = None
        self.refine_words_button = None
        self.expand_then_refine_words_button = None
        self.group_selected_words_into_paragraph_button = None

    def set_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Refine Bboxes action."""
        self._on_refine_bboxes = callback

    def set_expand_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Expand & Refine Bboxes action."""
        self._on_expand_refine_bboxes = callback

    def build_actions_toolbar(self):
        """Build the scope-action icon grid (Page/Paragraph/Line/Word operations)."""
        # Operations grid: columns = scope label | Merge | Refine | Expand+Refine |
        # Split After | Split Select | Word Select | To Paragraph | GT->OCR | OCR->GT | Delete
        with (
            ui.grid(columns="auto auto auto auto auto auto auto auto auto auto auto")
            .classes("items-center justify-items-center w-auto pl-2")
            .style("display: inline-grid; column-gap: 2px; row-gap: 2px")
        ):
            # Page row
            ui.label("Page").classes("text-sm font-semibold justify-self-start pr-1")
            ui.element("div")  # no Merge for page
            if self._on_refine_bboxes:
                self.refine_bboxes_button = ui.button(
                    icon="auto_fix_high",
                    on_click=self._on_refine_bboxes,
                ).tooltip("Refine all bounding boxes on this page")
                style_word_icon_button(self.refine_bboxes_button)
            else:
                ui.element("div")
            if self._on_expand_refine_bboxes:
                self.expand_refine_bboxes_button = ui.button(
                    icon="zoom_out_map",
                    on_click=self._on_expand_refine_bboxes,
                ).tooltip("Expand then refine all bounding boxes on this page")
                style_word_icon_button(self.expand_refine_bboxes_button)
            else:
                ui.element("div")
            ui.element("div")  # no Split After for page
            ui.element("div")  # no Split Select for page
            ui.element("div")  # no Word Select for page
            ui.element("div")  # no To Paragraph for page
            self.copy_gt_to_ocr_page_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_page_gt_to_ocr,
            ).tooltip("Copy all ground truth text to OCR on this page")
            self.copy_gt_to_ocr_page_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_page_button)
            self.copy_ocr_to_gt_page_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_page_ocr_to_gt,
            ).tooltip("Copy all OCR text to ground truth on this page")
            style_word_icon_button(self.copy_ocr_to_gt_page_button)
            ui.element("div")  # no Delete for page

            # Paragraph row
            ui.label("Paragraph").classes(
                "text-sm font-semibold justify-self-start pr-1"
            )
            self.merge_paragraphs_button = ui.button(
                icon="call_merge",
                on_click=self._view.actions._handle_merge_selected_paragraphs,
            ).tooltip("Merge selected paragraphs")
            style_word_icon_button(self.merge_paragraphs_button)
            self.refine_paragraphs_button = ui.button(
                icon="auto_fix_high",
                on_click=self._view.actions._handle_refine_selected_paragraphs,
            ).tooltip("Refine selected paragraphs")
            style_word_icon_button(self.refine_paragraphs_button)
            self.expand_then_refine_paragraphs_button = ui.button(
                icon="zoom_out_map",
                on_click=self._view.actions._handle_expand_then_refine_selected_paragraphs,
            ).tooltip("Expand then refine selected paragraphs")
            style_word_icon_button(self.expand_then_refine_paragraphs_button)
            self.split_paragraph_after_line_button = ui.button(
                icon="call_split",
                on_click=self._view.actions._handle_split_paragraph_after_selected_line,
            ).tooltip(
                "Split the containing paragraph immediately after the selected line"
            )
            style_word_icon_button(self.split_paragraph_after_line_button)
            ui.element("div")  # no Split Select for paragraph
            ui.element("div")  # no Word->Paragraph on paragraph scope
            ui.element("div")  # no To Paragraph on paragraph scope
            self.copy_gt_to_ocr_paragraphs_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_paragraphs_gt_to_ocr,
            ).tooltip("Copy ground truth text to OCR for selected paragraphs")
            self.copy_gt_to_ocr_paragraphs_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_paragraphs_button)
            self.copy_ocr_to_gt_paragraphs_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_paragraphs_ocr_to_gt,
            ).tooltip("Copy OCR text to ground truth for selected paragraphs")
            style_word_icon_button(self.copy_ocr_to_gt_paragraphs_button)
            self.delete_paragraphs_button = ui.button(
                icon="delete",
                on_click=self._view.actions._handle_delete_selected_paragraphs,
            ).tooltip("Delete selected paragraphs")
            style_word_icon_button(
                self.delete_paragraphs_button, variant=ButtonVariant.DELETE
            )

            # Line row
            ui.label("Line").classes("text-sm font-semibold justify-self-start pr-1")
            self.merge_lines_button = ui.button(
                icon="call_merge",
                on_click=self._view.actions._handle_merge_selected_lines,
            ).tooltip("Merge selected lines into the first selected line")
            style_word_icon_button(self.merge_lines_button)
            self.refine_lines_button = ui.button(
                icon="auto_fix_high",
                on_click=self._view.actions._handle_refine_selected_lines,
            ).tooltip("Refine selected lines")
            style_word_icon_button(self.refine_lines_button)
            self.expand_then_refine_lines_button = ui.button(
                icon="zoom_out_map",
                on_click=self._view.actions._handle_expand_then_refine_selected_lines,
            ).tooltip("Expand then refine selected lines")
            style_word_icon_button(self.expand_then_refine_lines_button)
            self.split_line_after_word_button = ui.button(
                icon="call_split",
                on_click=self._view.actions._handle_split_line_after_selected_word,
            ).tooltip("Split the selected line immediately after the selected word")
            style_word_icon_button(self.split_line_after_word_button)
            self.split_line_by_selection_button = ui.button(
                icon="vertical_split",
                on_click=self._view.actions._handle_split_lines_into_selected_unselected_words,
            ).tooltip("Split line(s) into selected and unselected words")
            style_word_icon_button(self.split_line_by_selection_button)
            ui.element("div")  # moved to word scope
            self.split_paragraph_by_selection_button = ui.button(
                icon="subject",
                on_click=self._view.actions._handle_split_paragraph_by_selected_lines,
            ).tooltip("Select lines to form a new paragraph")
            style_word_icon_button(self.split_paragraph_by_selection_button)
            self.copy_gt_to_ocr_lines_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_lines_gt_to_ocr,
            ).tooltip("Copy ground truth text to OCR for selected lines")
            self.copy_gt_to_ocr_lines_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_lines_button)
            self.copy_ocr_to_gt_lines_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_lines_ocr_to_gt,
            ).tooltip("Copy OCR text to ground truth for selected lines")
            style_word_icon_button(self.copy_ocr_to_gt_lines_button)
            self.delete_lines_button = ui.button(
                icon="delete",
                on_click=self._view.actions._handle_delete_selected_lines,
            ).tooltip("Delete selected lines")
            style_word_icon_button(
                self.delete_lines_button, variant=ButtonVariant.DELETE
            )

            # Word row
            ui.label("Word").classes("text-sm font-semibold justify-self-start pr-1")
            self.merge_words_button = ui.button(
                icon="call_merge",
                on_click=self._view.actions._handle_merge_selected_words,
            ).tooltip("Merge selected words on the same line")
            style_word_icon_button(self.merge_words_button)
            self.refine_words_button = ui.button(
                icon="auto_fix_high",
                on_click=self._view.actions._handle_refine_selected_words,
            ).tooltip("Refine selected words")
            style_word_icon_button(self.refine_words_button)
            self.expand_then_refine_words_button = ui.button(
                icon="zoom_out_map",
                on_click=self._view.actions._handle_expand_then_refine_selected_words,
            ).tooltip("Expand then refine selected words")
            style_word_icon_button(self.expand_then_refine_words_button)
            ui.element("div")  # no Split After for word
            ui.element("div")  # no Split Select for word
            self.extract_line_from_selection_button = ui.button(
                icon="short_text",
                on_click=self._view.actions._handle_split_line_by_selected_words,
            ).tooltip("Form one new line from selected words")
            style_word_icon_button(self.extract_line_from_selection_button)
            self.group_selected_words_into_paragraph_button = ui.button(
                icon="format_paragraph",
                on_click=self._view.actions._handle_group_selected_words_into_new_paragraph,
            ).tooltip(
                "Select words to form a new paragraph (one new line per source line)"
            )
            style_word_icon_button(self.group_selected_words_into_paragraph_button)
            self.copy_gt_to_ocr_words_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_words_gt_to_ocr,
            ).tooltip("Copy ground truth text to OCR for selected words")
            self.copy_gt_to_ocr_words_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_words_button)
            self.copy_ocr_to_gt_words_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_words_ocr_to_gt,
            ).tooltip("Copy OCR text to ground truth for selected words")
            style_word_icon_button(self.copy_ocr_to_gt_words_button)
            self.delete_words_button = ui.button(
                icon="delete",
                on_click=self._view.actions._handle_delete_selected_words,
            ).tooltip("Delete selected words")
            style_word_icon_button(
                self.delete_words_button, variant=ButtonVariant.DELETE
            )

    def update_button_state(self) -> None:
        """Enable/disable line and paragraph action buttons based on selection."""
        selected_lines = self._view._get_effective_selected_lines()
        if self.merge_lines_button is None:
            pass
        else:
            self.merge_lines_button.disabled = (
                self._view.merge_lines_callback is None or len(selected_lines) < 2
            )

        if self.delete_lines_button is not None:
            self.delete_lines_button.disabled = (
                self._view.delete_lines_callback is None or len(selected_lines) < 1
            )

        if self.refine_lines_button is not None:
            self.refine_lines_button.disabled = (
                self._view.refine_lines_callback is None or len(selected_lines) < 1
            )

        if self.expand_then_refine_lines_button is not None:
            self.expand_then_refine_lines_button.disabled = (
                self._view.expand_then_refine_lines_callback is None
                or len(selected_lines) < 1
            )

        if self.merge_paragraphs_button is not None:
            self.merge_paragraphs_button.disabled = (
                self._view.merge_paragraphs_callback is None
                or len(self._view.selection.selected_paragraph_indices) < 2
            )

        if self.delete_paragraphs_button is not None:
            self.delete_paragraphs_button.disabled = (
                self._view.delete_paragraphs_callback is None
                or len(self._view.selection.selected_paragraph_indices) < 1
            )

        if self.refine_paragraphs_button is not None:
            self.refine_paragraphs_button.disabled = (
                self._view.refine_paragraphs_callback is None
                or len(self._view.selection.selected_paragraph_indices) < 1
            )

        if self.expand_then_refine_paragraphs_button is not None:
            self.expand_then_refine_paragraphs_button.disabled = (
                self._view.expand_then_refine_paragraphs_callback is None
                or len(self._view.selection.selected_paragraph_indices) < 1
            )

        if self.split_paragraph_after_line_button is not None:
            self.split_paragraph_after_line_button.disabled = (
                self._view.split_paragraph_after_line_callback is None
                or len(self._view.selection.selected_line_indices) != 1
            )

        if self.split_paragraph_by_selection_button is not None:
            self.split_paragraph_by_selection_button.disabled = (
                self._view.split_paragraph_with_selected_lines_callback is None
                or len(self._view.selection.selected_line_indices) < 1
            )

        if self.split_line_after_word_button is not None:
            self.split_line_after_word_button.disabled = (
                self._view.split_line_after_word_callback is None
                or len(self._view.selection.selected_word_indices) != 1
            )

        if self.delete_words_button is not None:
            self.delete_words_button.disabled = (
                self._view.delete_words_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.merge_words_button is not None:
            self.merge_words_button.disabled = (
                self._view.merge_word_right_callback is None
                or not self._view._can_merge_selected_words()
            )

        if self.split_line_by_selection_button is not None:
            self.split_line_by_selection_button.disabled = (
                self._view.split_lines_into_selected_unselected_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.extract_line_from_selection_button is not None:
            self.extract_line_from_selection_button.disabled = (
                self._view.split_line_with_selected_words_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.group_selected_words_into_paragraph_button is not None:
            self.group_selected_words_into_paragraph_button.disabled = (
                self._view.group_selected_words_into_paragraph_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.refine_words_button is not None:
            self.refine_words_button.disabled = (
                self._view.refine_words_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.expand_then_refine_words_button is not None:
            self.expand_then_refine_words_button.disabled = (
                self._view.expand_then_refine_words_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.copy_gt_to_ocr_page_button is not None:
            self.copy_gt_to_ocr_page_button.disabled = (
                self._view.copy_gt_to_ocr_callback is None
                or len(self._view._get_all_line_indices()) < 1
            )

        if self.copy_ocr_to_gt_page_button is not None:
            self.copy_ocr_to_gt_page_button.disabled = (
                self._view.copy_ocr_to_gt_callback is None
                or len(self._view._get_all_line_indices()) < 1
            )

        if self.copy_gt_to_ocr_paragraphs_button is not None:
            self.copy_gt_to_ocr_paragraphs_button.disabled = (
                self._view.copy_gt_to_ocr_callback is None
                or len(self._view.selection.selected_paragraph_indices) < 1
            )

        if self.copy_ocr_to_gt_paragraphs_button is not None:
            self.copy_ocr_to_gt_paragraphs_button.disabled = (
                self._view.copy_ocr_to_gt_callback is None
                or len(self._view.selection.selected_paragraph_indices) < 1
            )

        if self.copy_gt_to_ocr_lines_button is not None:
            self.copy_gt_to_ocr_lines_button.disabled = (
                self._view.copy_gt_to_ocr_callback is None or len(selected_lines) < 1
            )

        if self.copy_ocr_to_gt_lines_button is not None:
            self.copy_ocr_to_gt_lines_button.disabled = (
                self._view.copy_ocr_to_gt_callback is None or len(selected_lines) < 1
            )

        if self.copy_gt_to_ocr_words_button is not None:
            self.copy_gt_to_ocr_words_button.disabled = (
                self._view.copy_gt_to_ocr_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )

        if self.copy_ocr_to_gt_words_button is not None:
            self.copy_ocr_to_gt_words_button.disabled = (
                self._view.copy_selected_words_ocr_to_gt_callback is None
                or len(self._view.selection.selected_word_indices) < 1
            )
