"""Line-level and word-level ground-truth editing operations for OCR labeling.

This module contains the ``LineOperations`` class, which handles per-line and
per-word GT operations for the labeler UI.  Bulk copy/clear methods delegate
to the model-layer methods added to ``Word``, ``Block``, and ``Page`` in
pd-book-tools.

Structural operations (merge/delete/split lines, words, paragraphs, bbox
refinement) are implemented directly on ``Page`` and dispatched from
``page_state._dispatch_line_op``.
"""

from __future__ import annotations

import logging

from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


class LineOperations:
    """Ground-truth editing operations for lines and words.

    Bulk copy/clear delegates to model-layer methods on ``Block``/``Word``.
    Per-word GT text and style attribute editing is implemented here because
    it requires cross-cutting logic (recomputing line GT after a word edit).
    """

    # ------------------------------------------------------------------
    # Line-level GT copy/clear (delegate to Block methods)
    # ------------------------------------------------------------------

    def _validated_line(self, page: "Page", line_index: int):
        """Return the line at *line_index* or None if invalid."""
        if not page:
            return None
        lines = page.lines
        if line_index < 0 or line_index >= len(lines):
            logger.warning(
                "Line index %s out of range (0-%s)", line_index, len(lines) - 1
            )
            return None
        return lines[line_index]

    def copy_ground_truth_to_ocr(self, page: "Page", line_index: int) -> bool:
        """Copy ground truth text to OCR text for all words in the specified line."""
        line = self._validated_line(page, line_index)
        if line is None:
            return False
        result = line.copy_ground_truth_to_ocr()
        if not result:
            logger.info("No ground truth text found to copy in line %s", line_index)
        return result

    def copy_ocr_to_ground_truth(self, page: "Page", line_index: int) -> bool:
        """Copy OCR text to ground truth text for all words in the specified line."""
        line = self._validated_line(page, line_index)
        if line is None:
            return False
        result = line.copy_ocr_to_ground_truth()
        if not result:
            logger.info("No OCR text found to copy in line %s", line_index)
        return result

    def clear_ground_truth_for_line(self, page: "Page", line_index: int) -> bool:
        """Clear ground truth text for all words in the specified line."""
        line = self._validated_line(page, line_index)
        if line is None:
            return False
        result = line.clear_ground_truth()
        if not result:
            logger.info("No ground truth text found to clear in line %s", line_index)
        return result

    # ------------------------------------------------------------------
    # Selected-word GT copy
    # ------------------------------------------------------------------

    def copy_selected_words_ocr_to_ground_truth(
        self,
        page: "Page",
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Copy OCR text to GT for only the selected word keys.

        Args:
            page: Page containing selected words.
            word_keys: List of (line_index, word_index) pairs.

        Returns:
            bool: True when at least one selected word was updated.
        """
        if not page:
            logger.warning("No page provided for selected-word OCR→GT copy")
            return False

        if not word_keys:
            logger.info("No selected words provided for OCR→GT copy")
            return False

        updated_count = 0
        for line_index, word_index in sorted(set(word_keys)):
            try:
                line_words = page.validated_line_words(line_index)
                if (
                    line_words is None
                    or word_index < 0
                    or word_index >= len(line_words)
                ):
                    continue

                target_word = line_words[word_index]
                if target_word.copy_ocr_to_ground_truth():
                    updated_count += 1
            except Exception:
                logger.debug(
                    "Failed selected-word OCR→GT copy for line=%s word=%s",
                    line_index,
                    word_index,
                    exc_info=True,
                )

        if updated_count > 0:
            logger.info("Copied OCR→GT for %d selected words", updated_count)
            return True

        logger.info("No OCR text found to copy for selected words")
        return False

    # ------------------------------------------------------------------
    # Per-word GT text edit
    # ------------------------------------------------------------------

    def update_word_ground_truth(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> bool:
        """Update ground truth text for a specific word.

        After updating the word, the line's aggregated GT is recomputed.

        Args:
            page: Page containing the line and word to update.
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            ground_truth_text: New ground truth text value.

        Returns:
            bool: True if update succeeded, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word GT update")
            return False

        try:
            line_words = page.validated_line_words(line_index)
            if line_words is None:
                return False

            if word_index < 0 or word_index >= len(line_words):
                logger.warning(
                    "Word index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(line_words) - 1,
                )
                return False

            normalized_value = str(ground_truth_text or "")
            target_word = line_words[word_index]
            if str(target_word.ground_truth_text or "") == normalized_value:
                logger.debug(
                    "Word GT unchanged for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return True

            target_word.ground_truth_text = normalized_value

            lines = list(page.lines)
            target_line = lines[line_index]
            line_gt = " ".join(
                str(word.ground_truth_text or "") for word in list(target_line.words)
            ).strip()
            try:
                target_line.ground_truth_text = line_gt if line_gt else ""
            except Exception:
                logger.debug(
                    "Unable to update line ground_truth_text after word edit",
                    exc_info=True,
                )

            logger.info("Updated GT for line=%d word=%d", line_index, word_index)
            return True

        except Exception as e:
            logger.exception(
                "Error updating word GT line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

    # ------------------------------------------------------------------
    # Per-word style attribute edit
    # ------------------------------------------------------------------

    def update_word_attributes(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> bool:
        """Update style attributes for a specific word.

        Args:
            page: Page containing the line and word to update.
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            italic: Whether word is italic.
            small_caps: Whether word is small caps.
            blackletter: Whether word is blackletter.
            left_footnote: Whether word has a left footnote marker.
            right_footnote: Whether word has a right footnote marker.

        Returns:
            bool: True if update succeeded, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word attribute update")
            return False

        try:
            line_words = page.validated_line_words(line_index)
            if line_words is None:
                return False

            if word_index < 0 or word_index >= len(line_words):
                logger.warning(
                    "Word index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(line_words) - 1,
                )
                return False

            target_word = line_words[word_index]

            desired_italic = bool(italic)
            desired_small_caps = bool(small_caps)
            desired_blackletter = bool(blackletter)
            desired_left_footnote = bool(left_footnote)
            desired_right_footnote = bool(right_footnote)

            if (
                target_word.read_style_attribute("italic", aliases=("is_italic",))
                == desired_italic
                and target_word.read_style_attribute(
                    "small_caps", aliases=("is_small_caps",)
                )
                == desired_small_caps
                and target_word.read_style_attribute(
                    "blackletter", aliases=("is_blackletter",)
                )
                == desired_blackletter
                and target_word.read_style_attribute(
                    "left_footnote", aliases=("is_left_footnote",)
                )
                == desired_left_footnote
                and target_word.read_style_attribute(
                    "right_footnote", aliases=("is_right_footnote",)
                )
                == desired_right_footnote
            ):
                logger.debug(
                    "Word attributes unchanged for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return True

            target_word.update_style_attributes(
                italic=desired_italic,
                small_caps=desired_small_caps,
                blackletter=desired_blackletter,
                left_footnote=desired_left_footnote,
                right_footnote=desired_right_footnote,
            )

            logger.info(
                "Updated attributes for line=%d word=%d italic=%s small_caps=%s "
                "blackletter=%s left_footnote=%s right_footnote=%s",
                line_index,
                word_index,
                desired_italic,
                desired_small_caps,
                desired_blackletter,
                desired_left_footnote,
                desired_right_footnote,
            )
            return True

        except Exception as e:
            logger.exception(
                "Error updating attributes line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False
