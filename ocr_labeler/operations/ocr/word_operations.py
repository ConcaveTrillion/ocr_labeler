"""Word-level OCR labeling operations.

This module centralizes mutation and inspection of per-word text styling using
the newer pd-book-tools Word label structures.
"""

from __future__ import annotations

import logging

from pd_book_tools.ocr.label_normalization import (
    normalize_text_style_label,
    normalize_text_style_label_scope,
    normalize_word_component,
)

from ocr_labeler.models.word_match_model import MatchStatus

logger = logging.getLogger(__name__)

STYLE_LABEL_BY_ATTR = {
    "italic": "italics",
    "is_italic": "italics",
    "small_caps": "small caps",
    "is_small_caps": "small caps",
    "blackletter": "blackletter",
    "is_blackletter": "blackletter",
}

WORD_COMPONENT_BY_ATTR = {
    "left_footnote": "footnote marker",
    "is_left_footnote": "footnote marker",
    "right_footnote": "footnote marker",
    "is_right_footnote": "footnote marker",
    "footnote": "footnote marker",
    "is_footnote": "footnote marker",
}


class WordOperations:
    """Handle word-level style and component mutations."""

    def read_word_attribute(
        self,
        word: object,
        primary_name: str,
        aliases: tuple[str, ...] = (),
    ) -> bool:
        """Read a legacy boolean word attribute from modern Word structures."""
        style_label = self._resolve_style_label(primary_name, aliases)
        if style_label is not None:
            return style_label in self._read_text_style_labels(word)

        component_label = self._resolve_word_component(primary_name, aliases)
        if component_label is not None:
            return component_label in self._read_word_components(word)

        return False

    def update_word_attributes(
        self,
        word: object,
        *,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> bool:
        """Update text styles and word components for a single Word object."""
        desired_flags = {
            "italic": bool(italic),
            "small_caps": bool(small_caps),
            "blackletter": bool(blackletter),
            "left_footnote": bool(left_footnote),
            "right_footnote": bool(right_footnote),
        }
        current_flags = {
            name: self.read_word_attribute(word, name) for name in desired_flags
        }
        if current_flags == desired_flags:
            return True

        style_labels = self._read_text_style_labels(word)
        style_scopes = self._read_text_style_label_scopes(word)
        word_components = self._read_word_components(word)

        style_labels_set = set(style_labels)
        component_set = set(word_components)

        for attr_name in ("italic", "small_caps", "blackletter"):
            style_label = self._resolve_style_label(attr_name, ())
            if style_label is None:
                continue
            if desired_flags[attr_name]:
                style_labels_set.add(style_label)
                style_scopes.setdefault(style_label, "whole")
            else:
                style_labels_set.discard(style_label)
                style_scopes.pop(style_label, None)

        footnote_component = self._resolve_word_component("left_footnote", ())
        if footnote_component is not None:
            if desired_flags["left_footnote"] or desired_flags["right_footnote"]:
                component_set.add(footnote_component)
            else:
                component_set.discard(footnote_component)

        normalized_style_labels = self._ordered_values(style_labels, style_labels_set)
        normalized_components = self._ordered_values(word_components, component_set)

        if not normalized_style_labels:
            normalized_style_labels = ["regular"]
        elif "regular" in normalized_style_labels and len(normalized_style_labels) > 1:
            normalized_style_labels = [
                label for label in normalized_style_labels if label != "regular"
            ]

        normalized_style_scopes = {
            label: normalize_text_style_label_scope(style_scopes.get(label, "whole"))
            for label in normalized_style_labels
        }

        word.text_style_labels = normalized_style_labels
        word.text_style_label_scopes = normalized_style_scopes
        word.word_components = normalized_components
        return True

    def apply_style_scope(
        self,
        word: object,
        style: str,
        scope: str,
    ) -> bool:
        """Apply a scope to an existing or implied text style label."""
        normalized_style = normalize_text_style_label(style)
        normalized_scope = normalize_text_style_label_scope(scope)

        style_labels = self._read_text_style_labels(word)
        style_scopes = self._read_text_style_label_scopes(word)
        style_set = set(style_labels)
        style_set.add(normalized_style)
        style_set.discard("regular")

        ordered_labels = self._ordered_values(style_labels, style_set)
        if normalized_style not in ordered_labels:
            ordered_labels.append(normalized_style)

        style_scopes[normalized_style] = normalized_scope
        word.text_style_labels = ordered_labels or [normalized_style]
        word.text_style_label_scopes = {
            label: normalize_text_style_label_scope(style_scopes.get(label, "whole"))
            for label in word.text_style_labels
        }
        return True

    def apply_word_component(
        self,
        word: object,
        component: str,
        *,
        enabled: bool,
    ) -> bool:
        """Add or remove a normalized word component label."""
        normalized_component = normalize_word_component(component)
        word_components = self._read_word_components(word)
        component_set = set(word_components)
        if enabled:
            component_set.add(normalized_component)
        else:
            component_set.discard(normalized_component)
        word.word_components = self._ordered_values(word_components, component_set)
        return True

    def remove_text_style_label(self, word: object, style: str) -> bool:
        """Remove a text style label while preserving other style metadata."""
        normalized_style = normalize_text_style_label(style)
        style_labels = self._read_text_style_labels(word)
        style_scopes = self._read_text_style_label_scopes(word)

        style_set = set(style_labels)
        style_set.discard(normalized_style)
        style_scopes.pop(normalized_style, None)

        ordered_labels = self._ordered_values(style_labels, style_set)
        if not ordered_labels:
            ordered_labels = ["regular"]

        word.text_style_labels = ordered_labels
        word.text_style_label_scopes = {
            label: normalize_text_style_label_scope(style_scopes.get(label, "whole"))
            for label in ordered_labels
        }
        return True

    def clear_all_scopes(self, word: object) -> bool:
        """Remove all scope assignments from a word's text style labels.

        Returns True if at least one scope was removed, False otherwise.
        """
        style_labels = self._read_text_style_labels(word)
        candidate_styles = [label for label in style_labels if label != "regular"]
        if not candidate_styles:
            return False

        scopes = self._read_text_style_label_scopes(word)
        changed = False
        for style_label in candidate_styles:
            if style_label in scopes:
                scopes.pop(style_label)
                changed = True

        if changed:
            word.text_style_label_scopes = scopes
        return changed

    @staticmethod
    def classify_match_status(
        ocr_text: str,
        ground_truth_text: str,
        fuzz_threshold: float,
        word_object: object | None = None,
    ) -> tuple[MatchStatus, float | None]:
        """Classify match status between OCR text and ground truth.

        Returns (match_status, fuzz_score).
        """
        if not ground_truth_text:
            return MatchStatus.UNMATCHED_OCR, None

        if ocr_text.strip() == ground_truth_text.strip():
            return MatchStatus.EXACT, 1.0

        fuzz_score = None
        if (
            word_object is not None
            and hasattr(word_object, "fuzz_score_against")
            and callable(getattr(word_object, "fuzz_score_against"))
        ):
            try:
                fuzz_score = word_object.fuzz_score_against(ground_truth_text)
            except Exception:
                logger.debug("Error computing fuzz score", exc_info=True)

        if fuzz_score is not None and fuzz_score >= fuzz_threshold:
            return MatchStatus.FUZZY, fuzz_score

        return MatchStatus.MISMATCH, 0.0 if fuzz_score is None else fuzz_score

    def _read_text_style_labels(self, word: object) -> list[str]:
        try:
            labels = list(getattr(word, "text_style_labels", []) or [])
        except TypeError:
            labels = []
        normalized = []
        for label in labels:
            try:
                normalized.append(normalize_text_style_label(str(label)))
            except ValueError:
                logger.debug("Ignoring invalid text style label %r", label)
        if not normalized:
            return ["regular"]
        return list(dict.fromkeys(normalized))

    def _read_text_style_label_scopes(self, word: object) -> dict[str, str]:
        try:
            scopes = dict(getattr(word, "text_style_label_scopes", {}) or {})
        except (TypeError, ValueError):
            scopes = {}
        normalized: dict[str, str] = {}
        for label, scope in scopes.items():
            try:
                normalized_label = normalize_text_style_label(str(label))
                normalized[normalized_label] = normalize_text_style_label_scope(scope)
            except ValueError:
                logger.debug(
                    "Ignoring invalid text style scope entry %r=%r", label, scope
                )
        return normalized

    def _read_word_components(self, word: object) -> list[str]:
        try:
            components = list(getattr(word, "word_components", []) or [])
        except TypeError:
            components = []
        normalized = []
        for component in components:
            try:
                normalized.append(normalize_word_component(str(component)))
            except ValueError:
                logger.debug("Ignoring invalid word component %r", component)
        return list(dict.fromkeys(normalized))

    def _resolve_style_label(
        self,
        primary_name: str,
        aliases: tuple[str, ...],
    ) -> str | None:
        style_label = STYLE_LABEL_BY_ATTR.get(primary_name)
        if style_label is not None:
            return style_label
        for alias in aliases:
            style_label = STYLE_LABEL_BY_ATTR.get(alias)
            if style_label is not None:
                return style_label
        return None

    def _resolve_word_component(
        self,
        primary_name: str,
        aliases: tuple[str, ...],
    ) -> str | None:
        component_label = WORD_COMPONENT_BY_ATTR.get(primary_name)
        if component_label is not None:
            return component_label
        for alias in aliases:
            component_label = WORD_COMPONENT_BY_ATTR.get(alias)
            if component_label is not None:
                return component_label
        return None

    def _ordered_values(self, original: list[str], values: set[str]) -> list[str]:
        ordered = [value for value in original if value in values]
        ordered.extend(sorted(value for value in values if value not in set(ordered)))
        return ordered
