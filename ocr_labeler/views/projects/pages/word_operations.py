"""Focused processor for selected-word style operations in the Matches view."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from pd_book_tools.ocr.label_normalization import (
    ALLOWED_COMPONENTS,
    ALLOWED_TEXT_STYLE_LABELS,
    normalize_text_style_label,
    normalize_text_style_label_scope,
    normalize_word_component,
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

FOOTNOTE_MARKER_COMPONENT = "footnote marker"
SUPPORTED_WORD_COMPONENTS = tuple(sorted(ALLOWED_COMPONENTS))


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
    def supported_components(self) -> tuple[str, ...]:
        return SUPPORTED_WORD_COMPONENTS

    def apply_style_to_selection(self, style: str) -> WordOperationResult:
        return self._apply_style(style, targets=None)

    def apply_style_to_word(
        self,
        line_index: int,
        word_index: int,
        style: str,
    ) -> WordOperationResult:
        return self._apply_style(style, targets=[(line_index, word_index)])

    def _apply_style(
        self,
        style: str,
        *,
        targets: list[WordSelection] | None,
    ) -> WordOperationResult:
        selection = self._selected_words() if targets is None else sorted(set(targets))
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
        return self._apply_scope(scope, targets=None)

    def apply_scope_to_word(
        self,
        line_index: int,
        word_index: int,
        scope: str,
    ) -> WordOperationResult:
        return self._apply_scope(scope, targets=[(line_index, word_index)])

    def _apply_scope(
        self,
        scope: str,
        *,
        targets: list[WordSelection] | None,
    ) -> WordOperationResult:
        selection = self._selected_words() if targets is None else sorted(set(targets))
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

    def clear_scope_on_word(
        self,
        line_index: int,
        word_index: int,
    ) -> WordOperationResult:
        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
        word_object = getattr(word_match, "word_object", None) if word_match else None
        if word_object is None:
            return WordOperationResult(0, "Select a valid word", "warning")

        style_labels = list(getattr(word_object, "text_style_labels", []) or [])
        candidate_styles = [label for label in style_labels if label != "regular"]
        if not candidate_styles:
            return WordOperationResult(
                0,
                "Failed to clear scope; select a word with an existing style",
                "warning",
            )

        try:
            scopes = dict(getattr(word_object, "text_style_label_scopes", {}) or {})
        except Exception:
            scopes = {}

        changed = False
        for style_label in candidate_styles:
            if style_label in scopes:
                scopes.pop(style_label, None)
                changed = True

        if not changed:
            return WordOperationResult(0, "Scope already cleared", "warning")

        word_object.text_style_label_scopes = scopes
        self._refresh_word_callback(line_index, word_index)
        return WordOperationResult(1, "Cleared scope on 1 word(s)", "positive")

    def apply_scope_to_word_style(
        self,
        line_index: int,
        word_index: int,
        style: str,
        scope: str,
    ) -> WordOperationResult:
        try:
            normalized_style = normalize_text_style_label(style)
            normalized_scope = normalize_text_style_label_scope(scope)
        except ValueError as error:
            logger.warning(
                "Invalid apply-scope-to-style value style=%r scope=%r: %s",
                style,
                scope,
                error,
            )
            return WordOperationResult(0, str(error), "warning")

        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
        word_object = getattr(word_match, "word_object", None) if word_match else None
        if word_object is None:
            return WordOperationResult(0, "Select a valid word", "warning")

        style_labels = [
            str(label).strip().lower()
            for label in list(getattr(word_object, "text_style_labels", []) or [])
            if str(label).strip().lower() != "regular"
        ]
        if normalized_style not in style_labels:
            return WordOperationResult(
                0,
                f"Style '{normalized_style}' is not present on this word",
                "warning",
            )

        try:
            changed = self._word_ops.apply_style_scope(
                word_object,
                normalized_style,
                normalized_scope,
            )
        except Exception:
            logger.exception(
                "Apply-scope-to-style mutation failed for line=%s word=%s style=%s scope=%s",
                line_index,
                word_index,
                normalized_style,
                normalized_scope,
            )
            changed = False

        if not changed:
            return WordOperationResult(
                0,
                f"Failed to apply scope '{normalized_scope}' to style '{normalized_style}'",
                "warning",
            )

        self._refresh_word_callback(line_index, word_index)
        return WordOperationResult(
            1,
            f"Applied scope '{normalized_scope}' to style '{normalized_style}'",
            "positive",
        )

    def clear_scope_on_word_style(
        self,
        line_index: int,
        word_index: int,
        style: str,
    ) -> WordOperationResult:
        try:
            normalized_style = normalize_text_style_label(style)
        except ValueError as error:
            logger.warning("Invalid clear-scope style %r: %s", style, error)
            return WordOperationResult(0, str(error), "warning")

        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
        word_object = getattr(word_match, "word_object", None) if word_match else None
        if word_object is None:
            return WordOperationResult(0, "Select a valid word", "warning")

        style_labels = [
            str(label).strip().lower()
            for label in list(getattr(word_object, "text_style_labels", []) or [])
            if str(label).strip().lower() != "regular"
        ]
        if normalized_style not in style_labels:
            return WordOperationResult(
                0,
                f"Style '{normalized_style}' is not present on this word",
                "warning",
            )

        try:
            scopes = dict(getattr(word_object, "text_style_label_scopes", {}) or {})
        except Exception:
            scopes = {}

        if normalized_style not in scopes:
            return WordOperationResult(
                0,
                f"No explicit scope set for style '{normalized_style}'",
                "warning",
            )

        scopes.pop(normalized_style, None)
        word_object.text_style_label_scopes = scopes
        self._refresh_word_callback(line_index, word_index)
        return WordOperationResult(
            1,
            f"Cleared explicit scope for style '{normalized_style}'",
            "positive",
        )

    def apply_component_to_selection(
        self,
        component: str,
        *,
        enabled: bool,
    ) -> WordOperationResult:
        return self._apply_component(component, enabled=enabled, targets=None)

    def apply_component_to_word(
        self,
        line_index: int,
        word_index: int,
        component: str,
        *,
        enabled: bool,
    ) -> WordOperationResult:
        return self._apply_component(
            component,
            enabled=enabled,
            targets=[(line_index, word_index)],
        )

    def clear_style_on_word(
        self,
        line_index: int,
        word_index: int,
        style: str,
    ) -> WordOperationResult:
        try:
            normalized_style = normalize_text_style_label(style)
        except ValueError as error:
            logger.warning("Invalid clear-style label %r: %s", style, error)
            return WordOperationResult(0, str(error), "warning")

        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
        word_object = getattr(word_match, "word_object", None) if word_match else None
        if word_object is None:
            return WordOperationResult(0, "Select a valid word", "warning")

        if (
            self._set_word_attributes_callback is not None
            and normalized_style in STYLE_TO_LEGACY_FLAGS
        ):
            italic, small_caps, blackletter, left_footnote, right_footnote = (
                self._view._word_style_flags(word_match)
            )
            if normalized_style == "italics":
                italic = False
            elif normalized_style == "small caps":
                small_caps = False
            elif normalized_style == "blackletter":
                blackletter = False

            try:
                success = self._set_word_attributes_callback(
                    line_index,
                    word_index,
                    italic,
                    small_caps,
                    blackletter,
                    left_footnote,
                    right_footnote,
                )
            except Exception:
                logger.exception(
                    "Clear-style callback failed for line=%s word=%s style=%s",
                    line_index,
                    word_index,
                    normalized_style,
                )
                success = False

            if success:
                return WordOperationResult(
                    1,
                    f"Removed style '{normalized_style}' from 1 word(s)",
                    "positive",
                )
            return WordOperationResult(
                0,
                f"Failed to remove style '{normalized_style}'",
                "warning",
            )

        try:
            changed = self._word_ops.remove_text_style_label(
                word_object,
                normalized_style,
            )
        except Exception:
            logger.exception(
                "Clear-style mutation failed for line=%s word=%s style=%s",
                line_index,
                word_index,
                normalized_style,
            )
            changed = False

        if changed:
            self._refresh_word_callback(line_index, word_index)
            return WordOperationResult(
                1,
                f"Removed style '{normalized_style}' from 1 word(s)",
                "positive",
            )
        return WordOperationResult(
            0,
            f"Failed to remove style '{normalized_style}'",
            "warning",
        )

    def clear_component_on_word(
        self,
        line_index: int,
        word_index: int,
        component: str,
    ) -> WordOperationResult:
        return self.apply_component_to_word(
            line_index,
            word_index,
            component,
            enabled=False,
        )

    def _apply_component(
        self,
        component: str,
        *,
        enabled: bool,
        targets: list[WordSelection] | None,
    ) -> WordOperationResult:
        selection = self._selected_words() if targets is None else sorted(set(targets))
        if not selection:
            return WordOperationResult(0, "Select at least one word", "warning")

        try:
            normalized_component = normalize_word_component(component)
        except ValueError as error:
            logger.warning("Invalid apply-component label %r: %s", component, error)
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

            italic, small_caps, blackletter, left_footnote, right_footnote = (
                self._view._word_style_flags(word_match)
            )

            if (
                self._set_word_attributes_callback is not None
                and normalized_component == FOOTNOTE_MARKER_COMPONENT
            ):
                left_footnote = enabled
                right_footnote = enabled
                try:
                    success = self._set_word_attributes_callback(
                        line_index,
                        word_index,
                        italic,
                        small_caps,
                        blackletter,
                        left_footnote,
                        right_footnote,
                    )
                except Exception:
                    logger.exception(
                        "Apply-component callback failed for line=%s word=%s component=%s enabled=%s",
                        line_index,
                        word_index,
                        normalized_component,
                        enabled,
                    )
                    success = False
                if success:
                    updated_count += 1
                else:
                    failed_count += 1
                continue

            try:
                changed = self._word_ops.apply_word_component(
                    word_object,
                    normalized_component,
                    enabled=enabled,
                )
            except Exception:
                logger.exception(
                    "Apply-component mutation failed for line=%s word=%s component=%s enabled=%s",
                    line_index,
                    word_index,
                    normalized_component,
                    enabled,
                )
                changed = False

            if changed:
                updated_count += 1
                self._refresh_word_callback(line_index, word_index)
            else:
                failed_count += 1

        action = "Applied" if enabled else "Removed"
        return self._result_for(
            updated_count,
            failed_count,
            success_message=(
                f"{action} component '{normalized_component}' on {updated_count} word(s)"
            ),
            failure_message=(f"Failed to update component '{normalized_component}'"),
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
