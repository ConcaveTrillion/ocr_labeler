"""Focused processor for selected-word style operations in the Matches view."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from pd_book_tools.ocr.label_normalization import (
    ALLOWED_TEXT_STYLE_LABEL_SCOPES,
    ALLOWED_TEXT_STYLE_LABELS,
    normalize_text_style_label,
    normalize_text_style_label_scope,
)

from ....operations.ocr.word_operations import WordOperations

if TYPE_CHECKING:
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)

Severity = str
WordSelection = tuple[int, int]
LegacyAttributeSetter = Callable[[int, int, bool, bool, bool, bool, bool], bool]
WordRefreshCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class WordOperationResult:
    updated_count: int
    message: str
    severity: Severity


STYLE_TO_LEGACY_FLAGS = {
    "italics": (True, False, False, False, False),
    "small caps": (False, True, False, False, False),
    "blackletter": (False, False, True, False, False),
}


class SelectedWordOperationsProcessor:
    """Apply immediate style operations to the current word selection."""

    def __init__(
        self,
        view: WordMatchView,
        set_word_attributes_callback: LegacyAttributeSetter | None,
        refresh_word_callback: WordRefreshCallback,
    ) -> None:
        self._view = view
        self._set_word_attributes_callback = set_word_attributes_callback
        self._refresh_word_callback = refresh_word_callback
        self._word_ops = WordOperations()

    @property
    def supported_styles(self) -> tuple[str, ...]:
        return tuple(
            style for style in sorted(ALLOWED_TEXT_STYLE_LABELS) if style != "regular"
        )

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return tuple(sorted(ALLOWED_TEXT_STYLE_LABEL_SCOPES))

    def selection_has_scope_target(self) -> bool:
        """Return True when selected words already have a non-regular text style."""
        for line_index, word_index in self._selected_words():
            try:
                word_match = self._view._line_word_match_by_ocr_index(
                    line_index, word_index
                )
            except AttributeError:
                logger.debug(
                    "Skipping scope-target detection for placeholder match at line=%s word=%s",
                    line_index,
                    word_index,
                )
                continue
            word_object = (
                getattr(word_match, "word_object", None) if word_match else None
            )
            if word_object is None:
                continue
            try:
                style_labels = self._word_ops._read_text_style_labels(word_object)
            except Exception:
                logger.debug(
                    "Skipping scope-target detection for line=%s word=%s",
                    line_index,
                    word_index,
                    exc_info=True,
                )
                continue
            style_labels = [label for label in style_labels if label != "regular"]
            if style_labels:
                return True
        return False

    def apply_style_to_selection(self, style: str) -> WordOperationResult:
        selection = self._selected_words()
        if not selection:
            return WordOperationResult(0, "Select at least one word", "warning")

        try:
            normalized_style = normalize_text_style_label(style)
        except ValueError as error:
            logger.warning("Invalid apply-style label %r: %s", style, error)
            return WordOperationResult(0, str(error), "warning")

        updated_count = 0
        failed_count = 0
        for line_index, word_index in selection:
            word_match = self._view._line_word_match_by_ocr_index(
                line_index, word_index
            )
            word_object = (
                getattr(word_match, "word_object", None) if word_match else None
            )
            if word_object is None:
                failed_count += 1
                continue

            if normalized_style in STYLE_TO_LEGACY_FLAGS:
                flags = STYLE_TO_LEGACY_FLAGS[normalized_style]
                if self._set_word_attributes_callback is None:
                    failed_count += 1
                    continue
                try:
                    success = self._set_word_attributes_callback(
                        line_index,
                        word_index,
                        *flags,
                    )
                except Exception:
                    logger.exception(
                        "Apply-style callback failed for line=%s word=%s style=%s",
                        line_index,
                        word_index,
                        normalized_style,
                    )
                    success = False
                if success:
                    updated_count += 1
                else:
                    failed_count += 1
                continue

            try:
                changed = self._word_ops.apply_style_scope(
                    word_object,
                    normalized_style,
                    "whole",
                )
            except Exception:
                logger.exception(
                    "Apply-style mutation failed for line=%s word=%s style=%s",
                    line_index,
                    word_index,
                    normalized_style,
                )
                changed = False

            if changed:
                updated_count += 1
                self._refresh_word_callback(line_index, word_index)
            else:
                failed_count += 1

        return self._result_for(
            updated_count,
            failed_count,
            success_message=f"Applied style '{normalized_style}' to {updated_count} word(s)",
            failure_message=f"Failed to apply style '{normalized_style}'",
        )

    def apply_scope_to_selection(self, scope: str) -> WordOperationResult:
        selection = self._selected_words()
        if not selection:
            return WordOperationResult(0, "Select at least one word", "warning")

        try:
            normalized_scope = normalize_text_style_label_scope(scope)
        except ValueError as error:
            logger.warning("Invalid apply-scope value %r: %s", scope, error)
            return WordOperationResult(0, str(error), "warning")

        updated_count = 0
        failed_count = 0
        for line_index, word_index in selection:
            word_match = self._view._line_word_match_by_ocr_index(
                line_index, word_index
            )
            word_object = (
                getattr(word_match, "word_object", None) if word_match else None
            )
            if word_object is None:
                failed_count += 1
                continue

            style_labels = list(getattr(word_object, "text_style_labels", []) or [])
            candidate_styles = [label for label in style_labels if label != "regular"]
            if not candidate_styles:
                failed_count += 1
                continue

            changed = False
            for style_label in candidate_styles:
                try:
                    self._word_ops.apply_style_scope(
                        word_object, style_label, normalized_scope
                    )
                    changed = True
                except Exception:
                    logger.exception(
                        "Apply-scope mutation failed for line=%s word=%s scope=%s style=%s",
                        line_index,
                        word_index,
                        normalized_scope,
                        style_label,
                    )

            if changed:
                updated_count += 1
                self._refresh_word_callback(line_index, word_index)
            else:
                failed_count += 1

        return self._result_for(
            updated_count,
            failed_count,
            success_message=f"Applied scope '{normalized_scope}' to existing styles on {updated_count} word(s)",
            failure_message=(
                f"Failed to apply scope '{normalized_scope}'; select word(s) with an existing style"
            ),
        )

    def _selected_words(self) -> list[WordSelection]:
        return sorted(set(self._view.selection.selected_word_indices))

    def _result_for(
        self,
        updated_count: int,
        failed_count: int,
        *,
        success_message: str,
        failure_message: str,
    ) -> WordOperationResult:
        if updated_count > 0 and failed_count == 0:
            return WordOperationResult(updated_count, success_message, "positive")
        if updated_count > 0:
            return WordOperationResult(
                updated_count,
                f"{success_message}; {failed_count} skipped",
                "warning",
            )
        return WordOperationResult(0, failure_message, "warning")
