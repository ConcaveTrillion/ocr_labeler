"""Bulk action handlers for the word match view."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from .word_edit_dialog import render_word_split_marker

if TYPE_CHECKING:
    from .word_match import ClickEvent, WordMatchView

logger = logging.getLogger(__name__)


class WordMatchActions:
    """Stateless handler class for bulk action methods on WordMatchView."""

    def __init__(self, view: WordMatchView) -> None:
        self._view = view

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _copy_lines(
        self,
        line_indices: list[int],
        callback: Callable[[int], bool] | None,
        *,
        direction_label: str,
        no_selection_message: str,
        no_text_message: str,
    ) -> None:
        """Copy text for a set of lines, clearing selections like other grid actions."""
        if callback is None:
            self._view._safe_notify("Copy function not available", type_="warning")
            return

        selected_lines = sorted(set(line_indices))
        if not selected_lines:
            self._view._safe_notify(no_selection_message, type_="warning")
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()

        success_count = 0
        for line_index in selected_lines:
            try:
                if callback(line_index):
                    success_count += 1
            except Exception as e:
                logger.exception(
                    "Error copying %s for line %s: %s",
                    direction_label,
                    line_index,
                    e,
                )

        if success_count > 0:
            self._view._safe_notify(
                f"Copied {direction_label} for {success_count} lines",
                type_="positive",
            )
            return

        self._view.selection.selected_line_indices = previous_line_selection
        self._view.selection.selected_word_indices = previous_word_selection
        self._view.selection.selected_paragraph_indices = previous_paragraph_selection
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()
        self._view._safe_notify(no_text_message, type_="warning")

    def _delete_lines(
        self,
        line_indices: list[int],
        *,
        success_message: str,
        failure_message: str,
    ) -> None:
        """Execute line deletion and keep selection state consistent on failure."""
        previously_selected = set(self._view.selection.selected_line_indices)
        previously_selected_words = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        logger.info("Delete requested for lines: %s", line_indices)
        try:
            success = self._view.delete_lines_callback(line_indices)
            logger.info(
                "Delete callback completed: selected=%s success=%s",
                line_indices,
                success,
            )
            if success:
                self._view._safe_notify(success_message, type_="positive")
            else:
                self._view.selection.selected_line_indices = previously_selected
                self._view.selection.selected_word_indices = previously_selected_words
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(failure_message, type_="warning")
        except Exception as e:
            self._view.selection.selected_line_indices = previously_selected
            self._view.selection.selected_word_indices = previously_selected_words
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error deleting lines %s: %s", line_indices, e)
            self._view._safe_notify(f"Error deleting lines: {e}", type_="negative")

    # ------------------------------------------------------------------
    # Page-level copy actions
    # ------------------------------------------------------------------

    def _handle_copy_page_gt_to_ocr(self, _event: ClickEvent = None) -> None:
        self._copy_lines(
            self._view._get_all_line_indices(),
            self._view.copy_gt_to_ocr_callback,
            direction_label="ground truth to OCR",
            no_selection_message="No lines available on this page",
            no_text_message="No ground truth text found to copy",
        )

    def _handle_copy_page_ocr_to_gt(self, _event: ClickEvent = None) -> None:
        self._copy_lines(
            self._view._get_all_line_indices(),
            self._view.copy_ocr_to_gt_callback,
            direction_label="OCR to ground truth",
            no_selection_message="No lines available on this page",
            no_text_message="No OCR text found to copy",
        )

    # ------------------------------------------------------------------
    # Paragraph-level copy actions
    # ------------------------------------------------------------------

    def _handle_copy_selected_paragraphs_gt_to_ocr(
        self, _event: ClickEvent = None
    ) -> None:
        self._copy_lines(
            self._view._get_selected_paragraph_line_indices(),
            self._view.copy_gt_to_ocr_callback,
            direction_label="ground truth to OCR",
            no_selection_message="Select at least one paragraph to copy",
            no_text_message="No ground truth text found to copy",
        )

    def _handle_copy_selected_paragraphs_ocr_to_gt(
        self, _event: ClickEvent = None
    ) -> None:
        self._copy_lines(
            self._view._get_selected_paragraph_line_indices(),
            self._view.copy_ocr_to_gt_callback,
            direction_label="OCR to ground truth",
            no_selection_message="Select at least one paragraph to copy",
            no_text_message="No OCR text found to copy",
        )

    # ------------------------------------------------------------------
    # Line-level copy actions
    # ------------------------------------------------------------------

    def _handle_copy_selected_lines_gt_to_ocr(self, _event: ClickEvent = None) -> None:
        self._copy_lines(
            self._view._get_effective_selected_lines(),
            self._view.copy_gt_to_ocr_callback,
            direction_label="ground truth to OCR",
            no_selection_message="Select at least one line to copy",
            no_text_message="No ground truth text found to copy",
        )

    def _handle_copy_selected_lines_ocr_to_gt(self, _event: ClickEvent = None) -> None:
        self._copy_lines(
            self._view._get_effective_selected_lines(),
            self._view.copy_ocr_to_gt_callback,
            direction_label="OCR to ground truth",
            no_selection_message="Select at least one line to copy",
            no_text_message="No OCR text found to copy",
        )

    # ------------------------------------------------------------------
    # Word-level copy actions
    # ------------------------------------------------------------------

    def _handle_copy_selected_words_gt_to_ocr(self, _event: ClickEvent = None) -> None:
        self._copy_lines(
            self._view._get_selected_word_line_indices(),
            self._view.copy_gt_to_ocr_callback,
            direction_label="ground truth to OCR",
            no_selection_message="Select at least one word to copy",
            no_text_message="No ground truth text found to copy",
        )

    def _handle_copy_selected_words_ocr_to_gt(self, _event: ClickEvent = None) -> None:
        if self._view.copy_selected_words_ocr_to_gt_callback is None:
            self._view._safe_notify("Copy function not available", type_="warning")
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify("Select at least one word to copy", type_="warning")
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()

        try:
            success = self._view.copy_selected_words_ocr_to_gt_callback(selected_words)
        except Exception as e:
            logger.exception(
                "Error copying OCR\u2192GT for selected words %s: %s",
                selected_words,
                e,
            )
            success = False

        if success:
            self._view._safe_notify(
                "Copied OCR to ground truth for selected words",
                type_="positive",
            )
            return

        self._view.selection.selected_line_indices = previous_line_selection
        self._view.selection.selected_word_indices = previous_word_selection
        self._view.selection.selected_paragraph_indices = previous_paragraph_selection
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()
        self._view._safe_notify("No OCR text found to copy", type_="warning")

    # ------------------------------------------------------------------
    # Merge / delete / split actions
    # ------------------------------------------------------------------

    def _handle_merge_selected_lines(self, _event: ClickEvent = None) -> None:
        """Merge selected lines into the first selected line."""
        if self._view.merge_lines_callback is None:
            self._view._safe_notify("Merge function not available", type_="warning")
            return

        selected_indices = self._view._get_effective_selected_lines()
        if len(selected_indices) < 2:
            self._view._safe_notify(
                "Select at least two lines to merge", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()
        logger.info("Merge requested for selected lines: %s", selected_indices)
        try:
            success = self._view.merge_lines_callback(selected_indices)
            logger.info(
                "Merge callback completed: selected=%s success=%s",
                selected_indices,
                success,
            )
            if success:
                self._view._safe_notify(
                    f"Merged {len(selected_indices)} lines", type_="positive"
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to merge selected lines", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception("Error merging selected lines %s: %s", selected_indices, e)
            self._view._safe_notify(
                f"Error merging selected lines: {e}", type_="negative"
            )

    def _handle_merge_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Merge selected paragraphs into the first selected paragraph."""
        if self._view.merge_paragraphs_callback is None:
            self._view._safe_notify(
                "Merge paragraph function not available", type_="warning"
            )
            return

        selected_indices = sorted(self._view.selection.selected_paragraph_indices)
        if len(selected_indices) < 2:
            self._view._safe_notify(
                "Select at least two paragraphs to merge", type_="warning"
            )
            return

        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_paragraph_selection_changed()
        logger.info("Merge requested for selected paragraphs: %s", selected_indices)
        try:
            success = self._view.merge_paragraphs_callback(selected_indices)
            logger.info(
                "Merge paragraph callback completed: selected=%s success=%s",
                selected_indices,
                success,
            )
            if success:
                self._view._safe_notify(
                    f"Merged {len(selected_indices)} paragraphs", type_="positive"
                )
            else:
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to merge selected paragraphs", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error merging selected paragraphs %s: %s",
                selected_indices,
                e,
            )
            self._view._safe_notify(
                f"Error merging selected paragraphs: {e}",
                type_="negative",
            )

    def _handle_delete_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Delete selected paragraphs from the current page."""
        if self._view.delete_paragraphs_callback is None:
            self._view._safe_notify(
                "Delete paragraph function not available", type_="warning"
            )
            return

        selected_indices = sorted(self._view.selection.selected_paragraph_indices)
        if not selected_indices:
            self._view._safe_notify(
                "Select at least one paragraph to delete", type_="warning"
            )
            return

        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_paragraph_selection_changed()
        logger.info("Delete requested for selected paragraphs: %s", selected_indices)
        try:
            success = self._view.delete_paragraphs_callback(selected_indices)
            logger.info(
                "Delete paragraph callback completed: selected=%s success=%s",
                selected_indices,
                success,
            )
            if success:
                self._view._safe_notify(
                    f"Deleted {len(selected_indices)} paragraphs", type_="positive"
                )
            else:
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to delete selected paragraphs",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error deleting selected paragraphs %s: %s",
                selected_indices,
                e,
            )
            self._view._safe_notify(
                f"Error deleting selected paragraphs: {e}",
                type_="negative",
            )

    def _handle_split_paragraph_after_selected_line(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Split the selected line's paragraph immediately after that line."""
        if self._view.split_paragraph_after_line_callback is None:
            self._view._safe_notify(
                "Split paragraph function not available", type_="warning"
            )
            return

        selected_line_indices = sorted(self._view.selection.selected_line_indices)
        if len(selected_line_indices) != 1:
            self._view._safe_notify(
                "Select exactly one line to split paragraph", type_="warning"
            )
            return

        selected_line_index = selected_line_indices[0]
        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()
        logger.info("Split requested after selected line: %s", selected_line_index)
        try:
            success = self._view.split_paragraph_after_line_callback(
                selected_line_index
            )
            logger.info(
                "Split paragraph-after-line callback completed: line=%s success=%s",
                selected_line_index,
                success,
            )
            if success:
                self._view._safe_notify(
                    f"Split paragraph after line {selected_line_index + 1}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify("Failed to split paragraph", type_="warning")
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting paragraph after line %s: %s",
                selected_line_index,
                e,
            )
            self._view._safe_notify(
                f"Error splitting paragraph: {e}",
                type_="negative",
            )

    def _handle_split_paragraph_by_selected_lines(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Move selected lines into a new paragraph."""
        logger.debug(
            "[split_by_selection] handler.start selected_lines=%s selected_words=%s selected_paragraphs=%s",
            sorted(self._view.selection.selected_line_indices),
            sorted(self._view.selection.selected_word_indices),
            sorted(self._view.selection.selected_paragraph_indices),
        )
        if self._view.split_paragraph_with_selected_lines_callback is None:
            self._view._safe_notify(
                "Split paragraph function not available", type_="warning"
            )
            return

        selected_line_indices = sorted(self._view.selection.selected_line_indices)
        if not selected_line_indices:
            self._view._safe_notify(
                "Select one or more lines to form a new paragraph",
                type_="warning",
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        logger.debug("[split_by_selection] handler.selection_cleared")
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()
        logger.info(
            "[split_by_selection] handler.requested lines=%s", selected_line_indices
        )
        try:
            logger.debug(
                "[split_by_selection] handler.callback_invoke lines=%s",
                selected_line_indices,
            )
            success = self._view.split_paragraph_with_selected_lines_callback(
                selected_line_indices
            )
            logger.info(
                "[split_by_selection] handler.callback_done lines=%s success=%s",
                selected_line_indices,
                success,
            )
            if success:
                logger.debug(
                    "[split_by_selection] handler.success awaiting_page_state_refresh"
                )
                self._view._safe_notify(
                    "Formed new paragraph from selected lines",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to form new paragraph from selected lines",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting paragraph by selected lines %s: %s",
                selected_line_indices,
                e,
            )
            self._view._safe_notify(
                f"Error forming new paragraph from selected lines: {e}",
                type_="negative",
            )

    def _handle_split_line_after_selected_word(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Split the selected line immediately after one selected word."""
        if self._view.split_line_after_word_callback is None:
            self._view._safe_notify(
                "Split line function not available", type_="warning"
            )
            return

        if len(self._view.selection.selected_word_indices) != 1:
            self._view._safe_notify(
                "Select exactly one word to split line",
                type_="warning",
            )
            return

        line_index, word_index = next(iter(self._view.selection.selected_word_indices))
        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()
        logger.info(
            "Split line requested after selected word: line=%s word=%s",
            line_index,
            word_index,
        )
        try:
            success = self._view.split_line_after_word_callback(line_index, word_index)
            logger.info(
                "Split line-after-word callback completed: line=%s word=%s success=%s",
                line_index,
                word_index,
                success,
            )
            if success:
                self._view._safe_notify(
                    f"Split line {line_index + 1} after word {word_index + 1}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify("Failed to split line", type_="warning")
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting line after word line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(f"Error splitting line: {e}", type_="negative")

    def _handle_delete_selected_lines(self, _event: ClickEvent = None) -> None:
        """Delete selected lines from the current page."""
        if self._view.delete_lines_callback is None:
            self._view._safe_notify("Delete function not available", type_="warning")
            return

        selected_indices = self._view._get_effective_selected_lines()
        if not selected_indices:
            self._view._safe_notify(
                "Select at least one line to delete", type_="warning"
            )
            return

        self._delete_lines(
            selected_indices,
            success_message=f"Deleted {len(selected_indices)} lines",
            failure_message="Failed to delete selected lines",
        )

    def _handle_delete_selected_words(self, _event: ClickEvent = None) -> None:
        """Delete selected words from the current page."""
        if self._view.delete_words_callback is None:
            self._view._safe_notify(
                "Delete word function not available", type_="warning"
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to delete", type_="warning"
            )
            return

        previously_selected_lines = set(self._view.selection.selected_line_indices)
        previously_selected_words = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        logger.info("Delete requested for selected words: %s", selected_words)
        try:
            success = self._view.delete_words_callback(selected_words)
            logger.info(
                "Delete words callback completed: selected=%s success=%s",
                selected_words,
                success,
            )
            if success:
                self._view._safe_notify(
                    f"Deleted {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previously_selected_lines
                self._view.selection.selected_word_indices = previously_selected_words
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to delete selected words", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previously_selected_lines
            self._view.selection.selected_word_indices = previously_selected_words
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error deleting words %s: %s", selected_words, e)
            self._view._safe_notify(f"Error deleting words: {e}", type_="negative")

    def _handle_merge_selected_words(self, _event: ClickEvent = None) -> None:
        """Merge selected contiguous words into one word on a single line."""
        if self._view.merge_word_right_callback is None:
            self._view._safe_notify(
                "Merge word function not available", type_="warning"
            )
            return

        if len(self._view.selection.selected_word_indices) < 2:
            self._view._safe_notify(
                "Select at least two words to merge", type_="warning"
            )
            return

        if not self._view._can_merge_selected_words():
            self._view._safe_notify(
                "Select contiguous words on a single line to merge",
                type_="warning",
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        line_index = selected_words[0][0]
        base_word_index = selected_words[0][1]
        merge_count = len(selected_words) - 1

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()

        logger.info("Merge requested for selected words: %s", selected_words)
        try:
            success = True
            for _ in range(merge_count):
                if not self._view.merge_word_right_callback(
                    line_index, base_word_index
                ):
                    success = False
                    break

            if success:
                self._view._safe_notify(
                    f"Merged {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to merge selected words", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error merging selected words %s: %s", selected_words, e)
            self._view._safe_notify(
                f"Error merging selected words: {e}", type_="negative"
            )

    # ------------------------------------------------------------------
    # Refine actions
    # ------------------------------------------------------------------

    def _handle_refine_selected_words(self, _event: ClickEvent = None) -> None:
        """Refine selected word bounding boxes."""
        if self._view.refine_words_callback is None:
            self._view._safe_notify(
                "Refine word function not available", type_="warning"
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to refine", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.refine_words_callback(selected_words)
            if success:
                self._view._safe_notify(
                    f"Refined {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to refine selected words", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error refining words %s: %s", selected_words, e)
            self._view._safe_notify(f"Error refining words: {e}", type_="negative")

    def _handle_refine_selected_lines(self, _event: ClickEvent = None) -> None:
        """Refine selected lines."""
        if self._view.refine_lines_callback is None:
            self._view._safe_notify(
                "Refine line function not available", type_="warning"
            )
            return

        selected_lines = self._view._get_effective_selected_lines()
        if not selected_lines:
            self._view._safe_notify(
                "Select at least one line to refine", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.refine_lines_callback(selected_lines)
            if success:
                self._view._safe_notify(
                    f"Refined {len(selected_lines)} lines",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to refine selected lines", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error refining lines %s: %s", selected_lines, e)
            self._view._safe_notify(f"Error refining lines: {e}", type_="negative")

    def _handle_refine_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Refine selected paragraphs."""
        if self._view.refine_paragraphs_callback is None:
            self._view._safe_notify(
                "Refine paragraph function not available", type_="warning"
            )
            return

        selected_paragraphs = sorted(self._view.selection.selected_paragraph_indices)
        if not selected_paragraphs:
            self._view._safe_notify(
                "Select at least one paragraph to refine", type_="warning"
            )
            return

        previous_selection = set(self._view.selection.selected_paragraph_indices)
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_paragraph_selection_changed()
        try:
            success = self._view.refine_paragraphs_callback(selected_paragraphs)
            if success:
                self._view._safe_notify(
                    f"Refined {len(selected_paragraphs)} paragraphs",
                    type_="positive",
                )
            else:
                self._view.selection.selected_paragraph_indices = previous_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to refine selected paragraphs", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_paragraph_indices = previous_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error refining paragraphs %s: %s",
                selected_paragraphs,
                e,
            )
            self._view._safe_notify(f"Error refining paragraphs: {e}", type_="negative")

    # ------------------------------------------------------------------
    # Expand-then-refine actions
    # ------------------------------------------------------------------

    def _handle_expand_then_refine_selected_words(
        self, _event: ClickEvent = None
    ) -> None:
        """Expand then refine selected word bounding boxes."""
        if self._view.expand_then_refine_words_callback is None:
            self._view._safe_notify(
                "Expand-then-refine word function not available", type_="warning"
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to expand-then-refine", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.expand_then_refine_words_callback(selected_words)
            if success:
                self._view._safe_notify(
                    f"Expanded then refined {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to expand-then-refine selected words", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error expand-then-refining words %s: %s", selected_words, e
            )
            self._view._safe_notify(
                f"Error expand-then-refining words: {e}", type_="negative"
            )

    def _handle_expand_bbox_selected_words(self, _event: ClickEvent = None) -> None:
        """Expand selected word bounding boxes by uniform padding."""
        if self._view.expand_word_bboxes_callback is None:
            self._view._safe_notify(
                "Expand bbox function not available", type_="warning"
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to expand", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.expand_word_bboxes_callback(selected_words)
            if success:
                self._view._safe_notify(
                    f"Expanded bboxes for {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to expand selected word bboxes", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error expanding word bboxes %s: %s", selected_words, e)
            self._view._safe_notify(
                f"Error expanding word bboxes: {e}", type_="negative"
            )

    def _handle_expand_then_refine_selected_lines(
        self, _event: ClickEvent = None
    ) -> None:
        """Expand then refine selected lines."""
        if self._view.expand_then_refine_lines_callback is None:
            self._view._safe_notify(
                "Expand-then-refine line function not available", type_="warning"
            )
            return

        selected_lines = self._view._get_effective_selected_lines()
        if not selected_lines:
            self._view._safe_notify(
                "Select at least one line to expand-then-refine", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.expand_then_refine_lines_callback(selected_lines)
            if success:
                self._view._safe_notify(
                    f"Expanded then refined {len(selected_lines)} lines",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to expand-then-refine selected lines", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error expand-then-refining lines %s: %s", selected_lines, e
            )
            self._view._safe_notify(
                f"Error expand-then-refining lines: {e}", type_="negative"
            )

    def _handle_expand_bbox_selected_lines(self, _event: ClickEvent = None) -> None:
        """Expand selected line bounding boxes by uniform padding."""
        if self._view.expand_line_bboxes_callback is None:
            self._view._safe_notify(
                "Expand line bboxes function not available", type_="warning"
            )
            return

        selected_lines = self._view._get_effective_selected_lines()
        if not selected_lines:
            self._view._safe_notify(
                "Select at least one line to expand", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.expand_line_bboxes_callback(selected_lines)
            if success:
                self._view._safe_notify(
                    f"Expanded bboxes in {len(selected_lines)} lines",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    "Failed to expand selected line bboxes", type_="warning"
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception("Error expanding line bboxes %s: %s", selected_lines, e)
            self._view._safe_notify(
                f"Error expanding line bboxes: {e}", type_="negative"
            )

    def _handle_expand_then_refine_selected_paragraphs(
        self, _event: ClickEvent = None
    ) -> None:
        """Expand then refine selected paragraphs."""
        if self._view.expand_then_refine_paragraphs_callback is None:
            self._view._safe_notify(
                "Expand-then-refine paragraph function not available", type_="warning"
            )
            return

        selected_paragraphs = sorted(self._view.selection.selected_paragraph_indices)
        if not selected_paragraphs:
            self._view._safe_notify(
                "Select at least one paragraph to expand-then-refine", type_="warning"
            )
            return

        previous_selection = set(self._view.selection.selected_paragraph_indices)
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_paragraph_selection_changed()
        try:
            success = self._view.expand_then_refine_paragraphs_callback(
                selected_paragraphs
            )
            if success:
                self._view._safe_notify(
                    f"Expanded then refined {len(selected_paragraphs)} paragraphs",
                    type_="positive",
                )
            else:
                self._view.selection.selected_paragraph_indices = previous_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to expand-then-refine selected paragraphs",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_paragraph_indices = previous_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error expand-then-refining paragraphs %s: %s",
                selected_paragraphs,
                e,
            )
            self._view._safe_notify(
                f"Error expand-then-refining paragraphs: {e}", type_="negative"
            )

    def _handle_expand_bbox_selected_paragraphs(
        self, _event: ClickEvent = None
    ) -> None:
        """Expand selected paragraph bounding boxes by uniform padding."""
        if self._view.expand_paragraph_bboxes_callback is None:
            self._view._safe_notify(
                "Expand paragraph bboxes function not available", type_="warning"
            )
            return

        selected_paragraphs = sorted(self._view.selection.selected_paragraph_indices)
        if not selected_paragraphs:
            self._view._safe_notify(
                "Select at least one paragraph to expand", type_="warning"
            )
            return

        previous_selection = set(self._view.selection.selected_paragraph_indices)
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_paragraph_selection_changed()
        try:
            success = self._view.expand_paragraph_bboxes_callback(selected_paragraphs)
            if success:
                self._view._safe_notify(
                    f"Expanded bboxes in {len(selected_paragraphs)} paragraphs",
                    type_="positive",
                )
            else:
                self._view.selection.selected_paragraph_indices = previous_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to expand selected paragraph bboxes",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_paragraph_indices = previous_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error expanding paragraph bboxes %s: %s",
                selected_paragraphs,
                e,
            )
            self._view._safe_notify(
                f"Error expanding paragraph bboxes: {e}", type_="negative"
            )

    # ------------------------------------------------------------------
    # Word-level split / group actions
    # ------------------------------------------------------------------

    def _handle_split_line_by_selected_words(self, _event: ClickEvent = None) -> None:
        """Move selected words into one newly created line."""
        if self._view.split_line_with_selected_words_callback is None:
            self._view._safe_notify(
                "Create line from selected words function not available",
                type_="warning",
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to form a new line",
                type_="warning",
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()

        try:
            success = self._view.split_line_with_selected_words_callback(selected_words)
            if success:
                self._view._safe_notify(
                    "Formed one new line from selected words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to form a new line from selected words",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error forming new line from selected words %s: %s",
                selected_words,
                e,
            )
            self._view._safe_notify(
                f"Error forming a new line from selected words: {e}",
                type_="negative",
            )

    def _handle_split_lines_into_selected_unselected_words(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Split each affected line into selected-word and unselected-word lines."""
        if self._view.split_lines_into_selected_unselected_callback is None:
            self._view._safe_notify(
                "Split lines into selected/unselected words function not available",
                type_="warning",
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to split line(s) by selection",
                type_="warning",
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()

        try:
            success = self._view.split_lines_into_selected_unselected_callback(
                selected_words
            )
            if success:
                self._view._safe_notify(
                    "Split line(s) into selected and unselected words",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to split line(s) into selected and unselected words",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting lines into selected/unselected words %s: %s",
                selected_words,
                e,
            )
            self._view._safe_notify(
                f"Error splitting lines into selected/unselected words: {e}",
                type_="negative",
            )

    def _handle_group_selected_words_into_new_paragraph(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Move selected words into a newly created paragraph."""
        if self._view.group_selected_words_into_paragraph_callback is None:
            self._view._safe_notify(
                "Group selected words function not available",
                type_="warning",
            )
            return

        selected_words = sorted(self._view.selection.selected_word_indices)
        if not selected_words:
            self._view._safe_notify(
                "Select at least one word to group into a new paragraph",
                type_="warning",
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        previous_paragraph_selection = set(
            self._view.selection.selected_paragraph_indices
        )
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.selection.selected_paragraph_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        self._view.selection.emit_paragraph_selection_changed()

        try:
            success = self._view.group_selected_words_into_paragraph_callback(
                selected_words
            )
            if success:
                self._view._safe_notify(
                    "Grouped selected words into new paragraph",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.selection.selected_paragraph_indices = (
                    previous_paragraph_selection
                )
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view.selection.emit_paragraph_selection_changed()
                self._view._safe_notify(
                    "Failed to group selected words into paragraph",
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.selection.selected_paragraph_indices = (
                previous_paragraph_selection
            )
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            self._view.selection.emit_paragraph_selection_changed()
            logger.exception(
                "Error grouping selected words %s into paragraph: %s",
                selected_words,
                e,
            )
            self._view._safe_notify(
                f"Error grouping selected words into paragraph: {e}",
                type_="negative",
            )

    # ------------------------------------------------------------------
    # Single-word actions
    # ------------------------------------------------------------------

    def _handle_refine_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Refine a single word bbox."""
        if self._view.refine_words_callback is None:
            self._view._safe_notify(
                "Refine word function not available", type_="warning"
            )
            return
        if word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word to refine", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.refine_words_callback([(line_index, word_index)])
            if success:
                self._view.renderer.rerender_word_column(line_index, word_index)
                self._view._safe_notify(
                    f"Refined word {word_index + 1} on line {line_index + 1}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    (
                        f"Could not refine line {line_index + 1}, word {word_index + 1}; "
                        "try reloading OCR for this page and retry"
                    ),
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error refining word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error refining line {line_index + 1}, word {word_index + 1}: {e}",
                type_="negative",
            )

    def _handle_expand_then_refine_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Expand then refine a single word bbox."""
        if self._view.expand_then_refine_words_callback is None:
            self._view._safe_notify(
                "Expand-then-refine function not available",
                type_="warning",
            )
            return
        if word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word to refine", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.expand_then_refine_words_callback(
                [(line_index, word_index)]
            )
            if success:
                self._view.renderer.rerender_word_column(line_index, word_index)
                self._view._safe_notify(
                    (
                        f"Expanded then refined word {word_index + 1} "
                        f"on line {line_index + 1}"
                    ),
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    (
                        f"Could not expand-then-refine line {line_index + 1}, "
                        f"word {word_index + 1}; try reloading OCR and retry"
                    ),
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error expand-then-refining word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                (
                    f"Error expanding/refining line {line_index + 1}, "
                    f"word {word_index + 1}: {e}"
                ),
                type_="negative",
            )

    def _handle_delete_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delete a single word from a specific line."""
        if self._view.delete_words_callback is None:
            self._view._safe_notify(
                "Delete word function not available", type_="warning"
            )
            return

        word_key = (line_index, word_index)
        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.delete_words_callback([word_key])
            if success:
                self._view.renderer.refresh_local_line_match_from_line_object(
                    line_index
                )
                self._view._update_summary()
                self._view.renderer.rerender_line_card(line_index)
                self._view._safe_notify(
                    f"Deleted word {word_index + 1} from line {line_index + 1}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    (
                        f"Could not delete line {line_index + 1}, word {word_index + 1}; "
                        "the word may have already changed"
                    ),
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error deleting single word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error deleting line {line_index + 1}, word {word_index + 1}: {e}",
                type_="negative",
            )

    def _handle_merge_word_left(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Merge selected word into its left neighbor."""
        if self._view.merge_word_left_callback is None:
            self._view._safe_notify(
                "Merge word function not available", type_="warning"
            )
            return
        if word_index <= 0:
            self._view._safe_notify("No left word to merge into", type_="warning")
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.merge_word_left_callback(line_index, word_index)
            if success:
                self._view.renderer.refresh_local_line_match_from_line_object(
                    line_index
                )
                self._view._update_summary()
                self._view.renderer.rerender_line_card(line_index)
                self._view._safe_notify(
                    f"Merged word {word_index + 1} into word {word_index}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    (
                        f"Could not merge line {line_index + 1}, word {word_index + 1} "
                        f"into word {word_index}; verify both words still exist"
                    ),
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error merge-word-left (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error merging line {line_index + 1}, word {word_index + 1}: {e}",
                type_="negative",
            )

    def _handle_merge_word_right(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Merge selected word with its right neighbor."""
        if self._view.merge_word_right_callback is None:
            self._view._safe_notify(
                "Merge word function not available", type_="warning"
            )
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.merge_word_right_callback(line_index, word_index)
            if success:
                self._view.renderer.refresh_local_line_match_from_line_object(
                    line_index
                )
                self._view._update_summary()
                self._view.renderer.rerender_line_card(line_index)
                self._view._safe_notify(
                    f"Merged word {word_index + 2} into word {word_index + 1}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    (
                        f"Could not merge line {line_index + 1}, word {word_index + 1} "
                        f"with word {word_index + 2}; verify both words still exist"
                    ),
                    type_="warning",
                )
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error merge-word-right (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error merging line {line_index + 1}, word {word_index + 1}: {e}",
                type_="negative",
            )

    # ------------------------------------------------------------------
    # Split word actions
    # ------------------------------------------------------------------

    def _handle_split_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> bool:
        """Split the selected word at the current marker."""
        if self._view.split_word_callback is None:
            self._view._safe_notify(
                "Split word function not available", type_="warning"
            )
            return False
        if word_index < 0:
            self._view._safe_notify("Select a valid OCR word to split", type_="warning")
            return False

        split_key = (line_index, word_index)
        split_fraction = self._view._word_split_fractions.get(split_key)
        if split_fraction is None:
            self._view._safe_notify(
                "Click inside the word image to choose split position",
                type_="warning",
            )
            return False

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.split_word_callback(
                line_index, word_index, split_fraction
            )
            if success:
                self._view.renderer.refresh_local_line_match_from_line_object(
                    line_index
                )
                self._view._update_summary()
                self._view.renderer.rerender_line_card(line_index)
                self._view._word_split_fractions.pop(split_key, None)
                self._view._word_split_marker_x.pop(split_key, None)
                render_word_split_marker(self._view, split_key)
                split_button = self._view._word_split_button_refs.get(split_key)
                if split_button is not None:
                    split_button.disabled = True
                self._view._safe_notify(
                    f"Split word {word_index + 1} on line {line_index + 1}",
                    type_="positive",
                )
                return True
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    self._view._split_failure_reason(
                        line_index,
                        word_index,
                        split_fraction,
                        vertical=False,
                    ),
                    type_="warning",
                )
                return False
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error split-word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error splitting line {line_index + 1}, word {word_index + 1}: {e}",
                type_="negative",
            )
            return False

    def _handle_split_word_vertical_closest_line(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> bool:
        """Split selected word vertically using the clicked x marker position."""
        if self._view.split_word_vertical_closest_line_callback is None:
            self._view._safe_notify(
                "Vertical split-to-line function not available",
                type_="warning",
            )
            return False
        if word_index < 0:
            self._view._safe_notify("Select a valid OCR word to split", type_="warning")
            return False

        split_key = (line_index, word_index)
        split_fraction = self._view._word_split_fractions.get(split_key)
        if split_fraction is None:
            self._view._safe_notify(
                "Click inside the word image to choose split position",
                type_="warning",
            )
            return False

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()
        try:
            success = self._view.split_word_vertical_closest_line_callback(
                line_index,
                word_index,
                split_fraction,
            )
            if success:
                for line_match in self._view.view_model.line_matches:
                    self._view.renderer.refresh_local_line_match_from_line_object(
                        line_match.line_index
                    )
                self._view._update_summary()
                self._view.renderer.update_lines_display()
                self._view._word_split_fractions.pop(split_key, None)
                self._view._word_split_marker_x.pop(split_key, None)
                self._view._word_split_marker_y.pop(split_key, None)
                render_word_split_marker(self._view, split_key)
                split_button = self._view._word_split_button_refs.get(split_key)
                if split_button is not None:
                    split_button.disabled = True
                vertical_split_button = self._view._word_vertical_split_button_refs.get(
                    split_key
                )
                if vertical_split_button is not None:
                    vertical_split_button.disabled = True
                self._view._safe_notify(
                    (
                        f"Split word {word_index + 1} on line {line_index + 1} "
                        "and reassigned pieces to closest lines"
                    ),
                    type_="positive",
                )
                return True
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify(
                    self._view._split_failure_reason(
                        line_index,
                        word_index,
                        split_fraction,
                        vertical=True,
                    ),
                    type_="warning",
                )
                return False
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error split-word-vertical (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                (
                    f"Error splitting vertically on line {line_index + 1}, "
                    f"word {word_index + 1}: {e}"
                ),
                type_="negative",
            )
            return False

    # ------------------------------------------------------------------
    # Bbox facade actions (delegate to bbox sub-class)
    # ------------------------------------------------------------------

    def _handle_start_rebox_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Start rebox mode for a selected word."""
        self._view.bbox.handle_start_rebox_word(line_index, word_index, _event)

    def _handle_nudge_single_word_bbox(
        self,
        line_index: int,
        word_index: int,
        *,
        left_units: float,
        right_units: float,
        top_units: float,
        bottom_units: float,
        _event: ClickEvent = None,
    ) -> None:
        """Accumulate a pending bbox nudge for a single word."""
        self._view.bbox.handle_nudge_single_word_bbox(
            line_index,
            word_index,
            left_units=left_units,
            right_units=right_units,
            top_units=top_units,
            bottom_units=bottom_units,
            _event=_event,
        )

    # ------------------------------------------------------------------
    # Single-line actions
    # ------------------------------------------------------------------

    def _handle_delete_line(self, line_index: int) -> None:
        """Delete a single line from the current page."""
        if self._view.delete_lines_callback is None:
            self._view._safe_notify("Delete function not available", type_="warning")
            return

        self._delete_lines(
            [line_index],
            success_message=f"Deleted line {line_index + 1}",
            failure_message=f"Failed to delete line {line_index + 1}",
        )

    def _handle_copy_gt_to_ocr(self, line_index: int):
        """Handle the GT->OCR button click."""
        logger.debug("Handling GT->OCR copy for line index %d", line_index)
        if self._view.copy_gt_to_ocr_callback:
            try:
                logger.debug("Calling copy_gt_to_ocr_callback for line %d", line_index)
                success = self._view.copy_gt_to_ocr_callback(line_index)
                if success:
                    logger.debug("GT->OCR copy successful for line %d", line_index)
                    self._view._safe_notify(
                        f"Copied ground truth to OCR text for line {line_index + 1}",
                        type_="positive",
                    )
                else:
                    logger.debug(
                        "GT->OCR copy failed - no ground truth text found for line %d",
                        line_index,
                    )
                    self._view._safe_notify(
                        f"No ground truth text found to copy in line {line_index + 1}",
                        type_="warning",
                    )
            except Exception as e:
                logger.exception(f"Error copying GT->OCR for line {line_index}: {e}")
                self._view._safe_notify(f"Error copying GT->OCR: {e}", type_="negative")
        else:
            logger.debug("No copy_gt_to_ocr_callback available")
            self._view._safe_notify("Copy function not available", type_="warning")

    def _handle_copy_ocr_to_gt(self, line_index: int):
        """Handle the OCR->GT button click."""
        logger.debug("Handling OCR->GT copy for line index %d", line_index)
        if self._view.copy_ocr_to_gt_callback:
            try:
                logger.debug("Calling copy_ocr_to_gt_callback for line %d", line_index)
                success = self._view.copy_ocr_to_gt_callback(line_index)
                if success:
                    logger.debug("OCR->GT copy successful for line %d", line_index)
                    self._view._safe_notify(
                        f"Copied OCR to ground truth text for line {line_index + 1}",
                        type_="positive",
                    )
                else:
                    logger.debug(
                        "OCR->GT copy failed - no OCR text found for line %d",
                        line_index,
                    )
                    self._view._safe_notify(
                        f"No OCR text found to copy in line {line_index + 1}",
                        type_="warning",
                    )
            except Exception as e:
                logger.exception(f"Error copying OCR->GT for line {line_index}: {e}")
                self._view._safe_notify(f"Error copying OCR->GT: {e}", type_="negative")
        else:
            logger.debug("No copy_ocr_to_gt_callback available")
            self._view._safe_notify("Copy function not available", type_="warning")
