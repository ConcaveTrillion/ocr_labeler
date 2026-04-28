"""Selection state management for the word match view."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)

WordKey = tuple[int, int]


class WordMatchSelection:
    """Manages selection state for lines, words, and paragraphs."""

    def __init__(self, view: WordMatchView) -> None:
        self._view = view
        self.selected_line_indices: set[int] = set()
        self.selected_word_indices: set[WordKey] = set()
        self.selected_paragraph_indices: set[int] = set()
        self._word_checkbox_refs: dict[WordKey, object] = {}
        self._line_checkbox_refs: dict[int, object] = {}
        self._paragraph_checkbox_refs: dict[int, object] = {}
        self._selection_change_callback = None
        self._paragraph_selection_change_callback = None

    def set_selection_change_callback(self, callback) -> None:
        self._selection_change_callback = callback

    def set_paragraph_selection_change_callback(self, callback) -> None:
        self._paragraph_selection_change_callback = callback

    def emit_selection_changed(self) -> None:
        """Emit selected words to listener (for image overlay sync)."""
        if self._selection_change_callback is None:
            return
        self._selection_change_callback(set(self.selected_word_indices))

    def emit_paragraph_selection_changed(self) -> None:
        """Emit selected paragraphs to listener (for image overlay sync)."""
        if self._paragraph_selection_change_callback is None:
            return
        self._paragraph_selection_change_callback(set(self.selected_paragraph_indices))

    def is_line_fully_word_selected(self, line_index: int) -> bool:
        keys = self._view._line_word_keys(line_index)
        return bool(keys) and keys.issubset(self.selected_word_indices)

    def is_paragraph_fully_line_selected(self, paragraph_index: int) -> bool:
        line_indices = self._view._paragraph_line_indices(paragraph_index)
        return bool(line_indices) and line_indices.issubset(self.selected_line_indices)

    def is_line_checked(self, line_index: int) -> bool:
        return (
            line_index in self.selected_line_indices
            or self.is_line_fully_word_selected(line_index)
        )

    def sync_line_selection_from_words(self, line_index: int) -> None:
        if self.is_line_fully_word_selected(line_index):
            self.selected_line_indices.add(line_index)
        else:
            self.selected_line_indices.discard(line_index)

    def sync_paragraph_selection_from_lines(self, paragraph_index: int) -> None:
        if self.is_paragraph_fully_line_selected(paragraph_index):
            self.selected_paragraph_indices.add(paragraph_index)
        else:
            self.selected_paragraph_indices.discard(paragraph_index)

    def sync_all_paragraph_selection_from_lines(self) -> None:
        available_paragraph_indices = {
            paragraph_index
            for paragraph_index in (
                getattr(line_match, "paragraph_index", None)
                for line_match in self._view.view_model.line_matches
            )
            if isinstance(paragraph_index, int)
        }
        self.selected_paragraph_indices.intersection_update(available_paragraph_indices)
        for paragraph_index in available_paragraph_indices:
            self.sync_paragraph_selection_from_lines(paragraph_index)

    def on_line_selection_change(self, line_index: int, selected: bool) -> None:
        """Track selected lines for merge workflow."""
        if selected:
            self.selected_line_indices.add(line_index)
            self.selected_word_indices.update(self._view._line_word_keys(line_index))
        else:
            self.selected_line_indices.discard(line_index)
            self.selected_word_indices.difference_update(
                self._view._line_word_keys(line_index)
            )
        paragraph_index = self._view._line_paragraph_index(line_index)
        if paragraph_index is not None:
            self.sync_paragraph_selection_from_lines(paragraph_index)
        logger.debug(
            "Line selection changed: line_index=%d selected=%s current_selection=%s",
            line_index,
            selected,
            sorted(self.selected_line_indices),
        )
        self._view.refresh_after_selection_change()

    def on_word_selection_change(
        self, selection_key: tuple[int, int], selected: bool
    ) -> None:
        """Track selected words for box/checkbox-driven workflow."""
        if selected:
            self.selected_word_indices.add(selection_key)
        else:
            self.selected_word_indices.discard(selection_key)
        self.sync_line_selection_from_words(selection_key[0])
        paragraph_index = self._view._line_paragraph_index(selection_key[0])
        if paragraph_index is not None:
            self.sync_paragraph_selection_from_lines(paragraph_index)
        logger.debug(
            "Word selection changed: key=%s selected=%s current_words=%s",
            selection_key,
            selected,
            sorted(self.selected_word_indices),
        )
        self._view.refresh_after_selection_change()

    def on_paragraph_selection_change(
        self, paragraph_index: int, selected: bool
    ) -> None:
        """Track selected paragraphs for paragraph actions."""
        paragraph_line_indices = self._view._paragraph_line_indices(paragraph_index)
        paragraph_word_keys = self._view._paragraph_word_keys(paragraph_index)

        if selected:
            self.selected_paragraph_indices.add(paragraph_index)
            self.selected_line_indices.update(paragraph_line_indices)
            self.selected_word_indices.update(paragraph_word_keys)
        else:
            self.selected_paragraph_indices.discard(paragraph_index)
            self.selected_line_indices.difference_update(paragraph_line_indices)
            self.selected_word_indices.difference_update(paragraph_word_keys)
        logger.debug(
            "Paragraph selection changed: paragraph_index=%d selected=%s current_selection=%s",
            paragraph_index,
            selected,
            sorted(self.selected_paragraph_indices),
        )
        self._view.refresh_after_selection_change()

    def set_selected_words(self, selection: set[tuple[int, int]]) -> None:
        """Set selected words externally (e.g., box selection integration)."""
        self.selected_word_indices = set(selection)
        available_line_indices = {
            line_match.line_index for line_match in self._view.view_model.line_matches
        }
        self.selected_line_indices = {
            line_index
            for line_index in available_line_indices
            if self.is_line_fully_word_selected(line_index)
        }
        self.sync_all_paragraph_selection_from_lines()
        self._view.refresh_after_selection_change()

    def set_selected_paragraphs(self, selection: set[int]) -> None:
        """Set selected paragraphs externally (e.g., image box selection)."""
        available_paragraph_indices = {
            line_match.paragraph_index
            for line_match in self._view.view_model.line_matches
            if getattr(line_match, "paragraph_index", None) is not None
        }
        self.selected_paragraph_indices = {
            paragraph_index
            for paragraph_index in selection
            if paragraph_index in available_paragraph_indices
        }
        selected_line_indices: set[int] = set()
        selected_word_indices: set[tuple[int, int]] = set()
        for paragraph_index in self.selected_paragraph_indices:
            paragraph_lines = self._view._paragraph_line_indices(paragraph_index)
            selected_line_indices.update(paragraph_lines)
            for line_index in paragraph_lines:
                selected_word_indices.update(self._view._line_word_keys(line_index))

        self.selected_line_indices = selected_line_indices
        self.selected_word_indices = selected_word_indices
        self._view.refresh_after_selection_change()

    def deselect_lines(self, line_indices: set[int]) -> bool:
        """Remove the given lines (and their words) from the selection.

        Also drops paragraphs that are no longer fully line-selected.
        Returns True if the selection state changed.
        """
        if not line_indices:
            return False
        changed = False
        for line_index in line_indices:
            if line_index in self.selected_line_indices:
                self.selected_line_indices.discard(line_index)
                changed = True
            line_word_keys = self._view._line_word_keys(line_index)
            if line_word_keys & self.selected_word_indices:
                self.selected_word_indices.difference_update(line_word_keys)
                changed = True
        affected_paragraphs = {
            self._view._line_paragraph_index(line_index) for line_index in line_indices
        }
        for paragraph_index in affected_paragraphs:
            if paragraph_index is None:
                continue
            if not self.is_paragraph_fully_line_selected(paragraph_index):
                if paragraph_index in self.selected_paragraph_indices:
                    self.selected_paragraph_indices.discard(paragraph_index)
                    changed = True
        return changed

    def refresh_line_checkbox_states(self) -> None:
        """Update rendered line-checkbox values from current selection state."""
        for line_index, checkbox in list(self._line_checkbox_refs.items()):
            if not self._view._has_active_ui_context(checkbox):
                self._line_checkbox_refs.pop(line_index, None)
                continue

            try:
                self._view._set_checkbox_value(
                    checkbox,
                    self.is_line_checked(line_index),
                )
            except RuntimeError as error:
                if self._view._is_disposed_ui_error(error):
                    self._line_checkbox_refs.pop(line_index, None)
                    continue
                raise
            except AttributeError:
                logger.debug(
                    "Failed to refresh line checkbox for line %s",
                    line_index,
                    exc_info=True,
                )

    def refresh_paragraph_checkbox_states(self) -> None:
        """Update rendered paragraph-checkbox values from current selection state."""
        for paragraph_index, checkbox in list(self._paragraph_checkbox_refs.items()):
            if not self._view._has_active_ui_context(checkbox):
                self._paragraph_checkbox_refs.pop(paragraph_index, None)
                continue

            try:
                self._view._set_checkbox_value(
                    checkbox,
                    paragraph_index in self.selected_paragraph_indices,
                )
            except RuntimeError as error:
                if self._view._is_disposed_ui_error(error):
                    self._paragraph_checkbox_refs.pop(paragraph_index, None)
                    continue
                raise
            except AttributeError:
                logger.debug(
                    "Failed to refresh paragraph checkbox for paragraph %s",
                    paragraph_index,
                    exc_info=True,
                )

    def refresh_word_checkbox_states(self) -> None:
        """Update rendered word-checkbox values from current selection state."""
        for selection_key, checkbox in list(self._word_checkbox_refs.items()):
            if not self._view._has_active_ui_context(checkbox):
                self._word_checkbox_refs.pop(selection_key, None)
                continue

            try:
                self._view._set_checkbox_value(
                    checkbox,
                    selection_key in self.selected_word_indices,
                )
            except RuntimeError as error:
                if self._view._is_disposed_ui_error(error):
                    self._word_checkbox_refs.pop(selection_key, None)
                    continue
                raise
            except AttributeError:
                logger.debug(
                    "Failed to refresh word checkbox for key %s",
                    selection_key,
                    exc_info=True,
                )

    def refresh_all_checkbox_states(self) -> None:
        """Refresh all checkbox types at once."""
        self.refresh_line_checkbox_states()
        self.refresh_word_checkbox_states()
        self.refresh_paragraph_checkbox_states()
