"""Line-level and word-level structural/GT operations for OCR labeling.

This module contains the ``LineOperations`` class that provides all
line/word structural and ground-truth editing methods, paragraph-level
operations, and word/line/paragraph bbox refinement operations.

All delegation is done directly to ``Page``, ``Block``, ``Word``, and
``BoundingBox`` methods rather than through intermediate mixin classes.
"""

from __future__ import annotations

import logging

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

logger = logging.getLogger(__name__)


class LineOperations:
    """Handle line-level and word-level structural/GT operations.

    Provides:

    - Copying ground truth ↔ OCR text for lines and selected words
    - Clearing ground truth text
    - Word-level GT and attribute editing
    - Line merging, deletion, and splitting
    - Word merging, splitting, deletion, reboxing, and nudging
    - Paragraph-level operations (merge, delete, split, group)
    - Word/line/paragraph bbox refinement and expansion
    """

    def copy_ground_truth_to_ocr(self, page: "Page", line_index: int) -> bool:
        """Copy ground truth text to OCR text for all words in the specified line.

        Args:
            page: Page containing the line to process
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        if not page:
            logger.warning("No page provided for GT→OCR copy")
            return False

        try:
            lines = page.lines
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range (0-%s)", line_index, len(lines) - 1
                )
                return False

            line = lines[line_index]
            words = line.words
            if not words:
                logger.info("No words found in line %s", line_index)
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                gt_text = word.ground_truth_text
                if gt_text:
                    # Copy ground truth to OCR text
                    word.text = gt_text
                    modified_count += 1
                    logger.debug(
                        "Copied GT→OCR for word %s in line %s: '%s'",
                        word_idx,
                        line_index,
                        gt_text,
                    )

            if modified_count > 0:
                logger.info(
                    "Copied GT→OCR for %s words in line %s", modified_count, line_index
                )
                return True
            else:
                logger.info("No ground truth text found to copy in line %s", line_index)
                return False

        except Exception:
            logger.exception("Error copying GT→OCR for line %s", line_index)
            return False

    def copy_ocr_to_ground_truth(self, page: "Page", line_index: int) -> bool:
        """Copy OCR text to ground truth text for all words in the specified line.

        Args:
            page: Page containing the line to process
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        if not page:
            logger.warning("No page provided for OCR→GT copy")
            return False

        try:
            lines = page.lines
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range (0-%s)", line_index, len(lines) - 1
                )
                return False

            line = lines[line_index]
            words = line.words
            if not words:
                logger.info("No words found in line %s", line_index)
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                ocr_text = word.text
                if ocr_text:
                    # Copy OCR text to ground truth
                    word.ground_truth_text = ocr_text
                    modified_count += 1
                    logger.debug(
                        "Copied OCR→GT for word %s in line %s: '%s'",
                        word_idx,
                        line_index,
                        ocr_text,
                    )

            if modified_count > 0:
                logger.info(
                    "Copied OCR→GT for %s words in line %s", modified_count, line_index
                )
                return True
            else:
                logger.info("No OCR text found to copy in line %s", line_index)
                return False

        except Exception:
            logger.exception("Error copying OCR→GT for line %s", line_index)
            return False

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
                ocr_text = str(target_word.text or "")
                if not ocr_text.strip():
                    continue

                if self.update_word_ground_truth(
                    page, line_index, word_index, ocr_text
                ):
                    updated_count += 1
            except Exception:
                logger.debug(
                    "Failed selected-word OCR→GT copy for line=%s word=%s",
                    line_index,
                    word_index,
                    exc_info=True,
                )

        if updated_count > 0:
            logger.info(
                "Copied OCR→GT for %d selected words",
                updated_count,
            )
            return True

        logger.info("No OCR text found to copy for selected words")
        return False

    def clear_ground_truth_for_line(self, page: "Page", line_index: int) -> bool:
        """Clear ground truth text for all words in the specified line.

        Args:
            page: Page containing the line to process
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        if not page:
            logger.warning("No page provided for GT clearing")
            return False

        try:
            lines = page.lines
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range (0-%s)", line_index, len(lines) - 1
                )
                return False

            line = lines[line_index]
            words = line.words
            if not words:
                logger.info("No words found in line %s", line_index)
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                if word.ground_truth_text:
                    word.ground_truth_text = ""
                    modified_count += 1
                    logger.debug(
                        "Cleared GT for word %s in line %s", word_idx, line_index
                    )

            if modified_count > 0:
                logger.info(
                    "Cleared GT for %s words in line %s", modified_count, line_index
                )
                return True
            else:
                logger.info(
                    "No ground truth text found to clear in line %s", line_index
                )
                return False

        except Exception:
            logger.exception("Error clearing GT for line %s", line_index)
            return False

    def update_word_ground_truth(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> bool:
        """Update ground truth text for a specific word.

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
            with_gt = bool(line_gt)
            try:
                target_line.ground_truth_text = line_gt if with_gt else ""
            except Exception:
                logger.debug(
                    "Unable to update line ground_truth_text after word edit",
                    exc_info=True,
                )

            logger.info(
                "Updated GT for line=%d word=%d",
                line_index,
                word_index,
            )
            return True

        except Exception as e:
            logger.exception(
                "Error updating word GT line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

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
                "Updated attributes for line=%d word=%d italic=%s small_caps=%s blackletter=%s left_footnote=%s right_footnote=%s",
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

    def merge_lines(self, page: "Page", line_indices: list[int]) -> bool:
        """Merge multiple lines into the first selected line.

        Args:
            page: Page containing the lines to merge.
            line_indices: Zero-based line indices to merge. At least two indices are required.

        Returns:
            bool: True if merge succeeded and modified the page, False otherwise.
        """
        if not page:
            logger.warning("No page provided for line merge")
            return False

        try:
            lines = list(page.lines)
            line_count_before = len(lines)

            logger.debug(
                "merge_lines start: page_type=%s, line_count=%d, requested=%s",
                type(page).__name__,
                line_count_before,
                line_indices,
            )

            if line_count_before < 2:
                logger.warning("Line merge requires at least two available lines")
                return False

            unique_indices = sorted(set(line_indices or []))
            if len(unique_indices) < 2:
                logger.warning("Line merge requires selecting at least two lines")
                return False

            for index in unique_indices:
                if index < 0 or index >= line_count_before:
                    logger.warning(
                        "Line index %s out of range (0-%s)",
                        index,
                        line_count_before - 1,
                    )
                    return False
                if not isinstance(lines[index], Block):
                    logger.warning(
                        "Selected line is not a Block (index=%s, type=%s)",
                        index,
                        type(lines[index]).__name__,
                    )
                    return False

            primary_index = unique_indices[0]
            primary_line = lines[primary_index]
            for index in unique_indices[1:]:
                secondary_line = lines[index]
                try:
                    primary_line.merge(secondary_line)
                except Exception as merge_error:
                    if not BoundingBox.is_geometry_normalization_error(merge_error):
                        raise
                    logger.warning(
                        "Line merge hit malformed bbox metadata (primary=%s secondary=%s): %s; applying merge fallback",
                        primary_index,
                        index,
                        merge_error,
                    )
                    if not primary_line.merge_fallback(secondary_line):
                        return False

            remove_line_if_exists = page.remove_line_if_exists
            if not callable(remove_line_if_exists):
                logger.warning(
                    "Page does not support remove_line_if_exists() (page_type=%s)",
                    type(page).__name__,
                )
                return False

            for index in reversed(unique_indices[1:]):
                remove_line_if_exists(lines[index])

            try:
                page.finalize_page_structure()
            except Exception as finalize_error:
                if not BoundingBox.is_geometry_normalization_error(finalize_error):
                    raise
                logger.warning(
                    "Merged lines but skipped final bbox recompute due to malformed geometry: %s",
                    finalize_error,
                )
                page._remove_empty_items_safely()
                page._recompute_paragraph_bboxes()

            lines_after = len(list(page.lines))
            logger.info(
                "Merged %d lines into line %d (line_count %d -> %d)",
                len(unique_indices),
                primary_index,
                line_count_before,
                lines_after,
            )
            return True

        except Exception as e:
            logger.exception("Error merging lines %s: %s", line_indices, e)
            return False

    def delete_lines(self, page: "Page", line_indices: list[int]) -> bool:
        """Delete selected lines from a page.

        Args:
            page: Page containing the lines to delete.
            line_indices: Zero-based line indices to delete. At least one index is required.

        Returns:
            bool: True if deletion succeeded and modified the page, False otherwise.
        """
        if not page:
            logger.warning("No page provided for line deletion")
            return False

        try:
            lines = list(page.lines)
            line_count_before = len(lines)

            logger.debug(
                "delete_lines start: page_type=%s, line_count=%d, requested=%s",
                type(page).__name__,
                line_count_before,
                line_indices,
            )

            unique_indices = sorted(set(line_indices or []))
            if not unique_indices:
                logger.warning("Line deletion requires selecting at least one line")
                return False

            for index in unique_indices:
                if index < 0 or index >= line_count_before:
                    logger.warning(
                        "Line index %s out of range (0-%s)",
                        index,
                        line_count_before - 1,
                    )
                    return False

            remove_line_if_exists = page.remove_line_if_exists
            if not callable(remove_line_if_exists):
                logger.warning(
                    "Page does not support remove_line_if_exists() (page_type=%s)",
                    type(page).__name__,
                )
                return False

            for index in reversed(unique_indices):
                remove_line_if_exists(lines[index])

            lines_after = len(list(page.lines))
            logger.info(
                "Deleted %d lines (line_count %d -> %d)",
                len(unique_indices),
                line_count_before,
                lines_after,
            )
            return True

        except Exception as e:
            logger.exception("Error deleting lines %s: %s", line_indices, e)
            return False

    def delete_words(self, page: "Page", word_keys: list[tuple[int, int]]) -> bool:
        """Delete selected words from a page.

        Args:
            page: Page containing lines/words.
            word_keys: List of (line_index, word_index) pairs to delete.

        Returns:
            bool: True if deletion succeeded and modified the page, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word deletion")
            return False

        try:
            unique_keys = sorted(set(word_keys or []))
            if not unique_keys:
                logger.warning("Word deletion requires selecting at least one word")
                return False

            validated_by_line: dict[int, list[object]] = {}

            for line_index, word_index in unique_keys:
                line_words = validated_by_line.get(line_index)
                if line_words is None:
                    line_words = page.validated_line_words(line_index)
                    if line_words is None:
                        return False
                    validated_by_line[line_index] = line_words
                if word_index < 0 or word_index >= len(line_words):
                    logger.warning(
                        "Word index %s out of range for line %s (0-%s)",
                        word_index,
                        line_index,
                        len(line_words) - 1,
                    )
                    return False

            keys_by_line: dict[int, list[int]] = {}
            for line_index, word_index in unique_keys:
                keys_by_line.setdefault(line_index, []).append(word_index)

            for line_index, word_indices in keys_by_line.items():
                line_words = page.validated_line_words(line_index)
                if line_words is None:
                    return False
                lines = list(page.lines)
                for word_index in sorted(word_indices, reverse=True):
                    if line_index < 0 or line_index >= len(lines):
                        return False
                    line = lines[line_index]
                    words = list(line_words)
                    if word_index < 0 or word_index >= len(words):
                        return False
                    line.remove_item(words[word_index])

            page.finalize_page_structure()

            logger.info("Deleted %d selected words", len(unique_keys))
            return True

        except Exception as e:
            logger.exception("Error deleting selected words %s: %s", word_keys, e)
            return False

    def merge_word_left(self, page: "Page", line_index: int, word_index: int) -> bool:
        """Merge the selected word into its immediate left neighbor.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index.
            word_index: Zero-based word index to merge into the left neighbor.

        Returns:
            bool: True when merge succeeds, False otherwise.
        """
        lines = list(page.lines)
        if line_index < 0 or line_index >= len(lines):
            logger.warning(
                "Line index %s out of range (0-%s)",
                line_index,
                len(lines) - 1,
            )
            return False
        return lines[line_index].merge_adjacent_words(word_index, "left")

    def merge_word_right(self, page: "Page", line_index: int, word_index: int) -> bool:
        """Merge the selected word with its immediate right neighbor.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index.
            word_index: Zero-based word index to merge with the right neighbor.

        Returns:
            bool: True when merge succeeds, False otherwise.
        """
        lines = list(page.lines)
        if line_index < 0 or line_index >= len(lines):
            logger.warning(
                "Line index %s out of range (0-%s)",
                line_index,
                len(lines) - 1,
            )
            return False
        return lines[line_index].merge_adjacent_words(word_index, "right")

    def split_word(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        split_fraction: float,
    ) -> bool:
        """Split a word into two words at a relative horizontal position.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index.
            word_index: Zero-based word index to split.
            split_fraction: Relative split position in range (0, 1).

        Returns:
            bool: True when split succeeds, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word split")
            return False

        if split_fraction <= 0.0 or split_fraction >= 1.0:
            logger.warning(
                "Word split fraction must be between 0 and 1 (exclusive), got %s",
                split_fraction,
            )
            return False

        try:
            lines = list(page.lines)
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range (0-%s)",
                    line_index,
                    len(lines) - 1,
                )
                return False

            line = lines[line_index]
            words = list(line.words)
            if word_index < 0 or word_index >= len(words):
                logger.warning(
                    "Word split index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(words) - 1,
                )
                return False

            word = words[word_index]
            word_text = str(word.text or "")
            if len(word_text) < 2:
                logger.warning(
                    "Word split requires at least two characters (line=%s, word=%s)",
                    line_index,
                    word_index,
                )
                return False

            bbox = word.bounding_box
            bbox_width = float(bbox.width if bbox else 0.0)
            if bbox is None or bbox_width <= 0.0:
                logger.warning(
                    "Word split requires valid non-zero bounding box (line=%s, word=%s)",
                    line_index,
                    word_index,
                )
                return False

            character_split_index = int(round(len(word_text) * split_fraction))
            character_split_index = max(
                1, min(len(word_text) - 1, character_split_index)
            )

            epsilon = min(1e-6, bbox_width / 10) if bbox_width > 0 else 0.0
            bbox_split_offset = bbox_width * split_fraction
            bbox_split_offset = max(
                epsilon, min(bbox_width - epsilon, bbox_split_offset)
            )

            line.split_word(
                split_word_index=word_index,
                bbox_split_offset=bbox_split_offset,
                character_split_index=character_split_index,
            )

            updated_words = page.validated_line_words(line_index)
            if updated_words is None:
                return False
            for updated_word in updated_words:
                updated_word.ground_truth_text = ""

            page.finalize_page_structure()

            logger.info(
                "Split word line=%d index=%d fraction=%.3f char_index=%d",
                line_index,
                word_index,
                split_fraction,
                character_split_index,
            )
            return True

        except Exception as e:
            logger.exception(
                "Error splitting word line=%s index=%s split_fraction=%s: %s",
                line_index,
                word_index,
                split_fraction,
                e,
            )
            return False

    def split_word_vertically_and_assign_to_closest_line(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        split_fraction: float,
    ) -> bool:
        """Split a word, then assign each resulting piece to the closest line by y-midpoint.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based source line index.
            word_index: Zero-based word index to split.
            split_fraction: Relative split position in range (0, 1).

        Returns:
            bool: True when split/reassignment succeeds, False otherwise.
        """
        lines_before_split = list(page.lines)
        if line_index < 0 or line_index >= len(lines_before_split):
            logger.warning(
                "Line index %s out of range (0-%s)",
                line_index,
                len(lines_before_split) - 1,
            )
            return False
        source_line = lines_before_split[line_index]

        if not self.split_word(page, line_index, word_index, split_fraction):
            return False

        try:
            lines = list(page.lines)
            source_words = list(source_line.words)
            if word_index < 0 or word_index + 1 >= len(source_words):
                logger.warning(
                    "Post-split word indices %s/%s unavailable on line %s",
                    word_index,
                    word_index + 1,
                    line_index,
                )
                return False

            split_words = [source_words[word_index], source_words[word_index + 1]]

            touched_lines: dict[int, object] = {id(source_line): source_line}
            for split_piece in split_words:
                piece_bbox = split_piece.bounding_box
                midpoint_y = (
                    piece_bbox.vertical_midpoint if piece_bbox is not None else None
                )
                target_line = Page.closest_line_by_midpoint(
                    lines,
                    midpoint_y,
                    fallback_line=source_line,
                )
                touched_lines[id(target_line)] = target_line

                if target_line is source_line:
                    continue

                if not Page.move_word_between_lines(
                    source_line, target_line, split_piece
                ):
                    logger.warning(
                        "Failed to move split word piece to closest line (line=%s word=%s)",
                        line_index,
                        word_index,
                    )
                    return False

            for touched_line in touched_lines.values():
                touched_words = list(touched_line.words)
                for touched_word in touched_words:
                    touched_word.ground_truth_text = ""
                touched_line.recompute_bounding_box()

            page.finalize_page_structure()

            logger.info(
                "Split word vertically with closest-line assignment line=%d index=%d fraction=%.3f",
                line_index,
                word_index,
                split_fraction,
            )
            return True
        except Exception as e:
            logger.exception(
                "Error splitting word vertically line=%s index=%s split_fraction=%s: %s",
                line_index,
                word_index,
                split_fraction,
                e,
            )
            return False

    def split_line_after_word(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
    ) -> bool:
        """Split a line into two lines immediately after the selected word.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index to split.
            word_index: Zero-based word index used as split point.

        Returns:
            bool: True when split succeeds, False otherwise.
        """
        if not page:
            logger.warning("No page provided for line split-after-word")
            return False

        try:
            lines = list(page.lines)
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range for line split (0-%s)",
                    line_index,
                    len(lines) - 1,
                )
                return False

            target_line = lines[line_index]
            line_words = list(target_line.words)
            if len(line_words) < 2:
                logger.warning(
                    "Line split requires at least two words (line index %s)",
                    line_index,
                )
                return False

            if word_index < 0 or word_index >= len(line_words) - 1:
                logger.warning(
                    "Cannot split line %s after word index %s (valid range: 0-%s)",
                    line_index,
                    word_index,
                    len(line_words) - 2,
                )
                return False

            first_words = line_words[: word_index + 1]
            second_words = line_words[word_index + 1 :]
            if not first_words or not second_words:
                logger.warning(
                    "Line split produced empty segment(s) for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return False

            paragraphs = list(page.paragraphs)
            target_paragraph = None
            for paragraph in paragraphs:
                paragraph_lines = list(paragraph.lines)
                if target_line in paragraph_lines:
                    target_paragraph = paragraph
                    break

            if target_paragraph is None:
                logger.warning(
                    "Unable to find paragraph containing line index %s",
                    line_index,
                )
                return False

            parent = Page._find_parent_block_recursive(page, target_paragraph)
            if parent is None:
                logger.warning(
                    "Unable to locate parent block for line split after word (%s, %s)",
                    line_index,
                    word_index,
                )
                return False

            paragraph_items = list(target_paragraph.items)
            if target_line not in paragraph_items:
                logger.warning(
                    "Target line missing in paragraph items for line split (%s, %s)",
                    line_index,
                    word_index,
                )
                return False

            line_item_index = paragraph_items.index(target_line)
            target_line.items = first_words
            target_line.unmatched_ground_truth_words = []
            target_line.recompute_bounding_box()

            split_line = Block(
                items=second_words,
                child_type=BlockChildType.WORDS,
                block_category=BlockCategory.LINE,
            )

            target_paragraph.items = (
                paragraph_items[: line_item_index + 1]
                + [split_line]
                + paragraph_items[line_item_index + 1 :]
            )
            target_paragraph.recompute_bounding_box()
            parent.recompute_bounding_box()

            page.finalize_page_structure()

            logger.info(
                "Split line %s after word %s",
                line_index,
                word_index,
            )
            return True

        except Exception as e:
            logger.exception(
                "Error splitting line after word line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

    def rebox_word(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        refine_after: bool = True,
    ) -> bool:
        """Replace a word bounding box with the provided rectangle.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index.
            word_index: Zero-based word index to rebox.
            x1: Left x-coordinate in page pixel space.
            y1: Top y-coordinate in page pixel space.
            x2: Right x-coordinate in page pixel space.
            y2: Bottom y-coordinate in page pixel space.
            refine_after: Whether to run word-level refine helpers after rebox.

        Returns:
            bool: True when rebox succeeds, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word rebox")
            return False

        try:
            line_words = page.validated_line_words(line_index)
            if line_words is None:
                return False
            if word_index < 0 or word_index >= len(line_words):
                logger.warning(
                    "Word rebox index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(line_words) - 1,
                )
                return False

            rx1, ry1 = min(float(x1), float(x2)), min(float(y1), float(y2))
            rx2, ry2 = max(float(x1), float(x2)), max(float(y1), float(y2))
            if rx2 <= rx1 or ry2 <= ry1:
                logger.warning(
                    "Invalid rebox rectangle for line=%s word=%s: (%s, %s, %s, %s)",
                    line_index,
                    word_index,
                    rx1,
                    ry1,
                    rx2,
                    ry2,
                )
                return False

            word = line_words[word_index]
            existing_bbox = word.bounding_box
            is_normalized = bool(
                existing_bbox.is_normalized if existing_bbox else False
            )

            if is_normalized:
                page_width, page_height = page.resolved_dimensions
                if page_width <= 0.0 or page_height <= 0.0:
                    logger.warning(
                        "Unable to resolve page dimensions for normalized rebox"
                    )
                    return False
                new_bbox = BoundingBox(
                    Point(rx1 / page_width, ry1 / page_height),
                    Point(rx2 / page_width, ry2 / page_height),
                    is_normalized=True,
                )
            else:
                new_bbox = BoundingBox(
                    Point(rx1, ry1),
                    Point(rx2, ry2),
                    is_normalized=False,
                )

            word.bounding_box = new_bbox
            if refine_after:
                word.refine_bbox(page.cv2_numpy_page_image)
            page.finalize_page_structure()

            logger.info(
                "Reboxed word line=%d index=%d bbox=(%.2f, %.2f, %.2f, %.2f)",
                line_index,
                word_index,
                rx1,
                ry1,
                rx2,
                ry2,
            )
            return True
        except Exception as e:
            logger.exception(
                "Error reboxing word line=%s index=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

    def add_word_to_page(
        self,
        page: "Page",
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        text: str = "",
    ) -> bool:
        """Insert a new word with the given bounding box into the nearest line.

        The target line is chosen by minimum vertical distance between the
        midpoint of the drawn bbox and each line's midpoint.  The new word is
        inserted at the position sorted by its left edge so the line ordering
        remains consistent.

        Args:
            page: Page to insert the word into.
            x1: Left x-coordinate in page pixel space.
            y1: Top y-coordinate in page pixel space.
            x2: Right x-coordinate in page pixel space.
            y2: Bottom y-coordinate in page pixel space.
            text: Optional initial OCR text for the new word (default "").

        Returns:
            bool: True when insertion succeeds, False otherwise.
        """
        if not page:
            logger.warning("No page provided for add_word_to_page")
            return False

        try:
            rx1, ry1 = min(float(x1), float(x2)), min(float(y1), float(y2))
            rx2, ry2 = max(float(x1), float(x2)), max(float(y1), float(y2))
            if rx2 <= rx1 or ry2 <= ry1:
                logger.warning(
                    "Invalid add-word rectangle: (%.2f, %.2f, %.2f, %.2f)",
                    rx1,
                    ry1,
                    rx2,
                    ry2,
                )
                return False

            lines = list(page.lines)
            if not lines:
                logger.warning("No lines found in page for add_word_to_page")
                return False

            # Determine bbox normalization from the first word found.
            is_normalized = page.is_content_normalized
            page_width, page_height = 0.0, 0.0

            if is_normalized:
                page_width, page_height = page.resolved_dimensions
                if page_width <= 0.0 or page_height <= 0.0:
                    logger.warning("Unable to resolve page dimensions for add_word")
                    return False
                new_bbox = BoundingBox(
                    Point(rx1 / page_width, ry1 / page_height),
                    Point(rx2 / page_width, ry2 / page_height),
                    is_normalized=True,
                )
            else:
                new_bbox = BoundingBox(
                    Point(rx1, ry1),
                    Point(rx2, ry2),
                    is_normalized=False,
                )

            new_word = Word(
                text=text,
                bounding_box=new_bbox,
                ocr_confidence=None,
            )

            # Find the nearest line using fuzzy vertical matching:
            # prefer any line whose Y range contains the drawn bbox centre,
            # then break ties by horizontal distance to handle parallel columns.
            # Falls back to closest vertical midpoint when no line spans center_y.
            cx = (rx1 + rx2) / 2.0
            cy = (ry1 + ry2) / 2.0
            if is_normalized:
                cx = cx / page_width
                cy = cy / page_height

            target_line = Page.closest_line_by_y_range_then_x(
                lines,
                cx,
                cy,
                lines[0],
            )

            target_line.add_item(new_word)

            page.finalize_page_structure()

            logger.info(
                "Added new word to page bbox=(%.2f, %.2f, %.2f, %.2f)",
                rx1,
                ry1,
                rx2,
                ry2,
            )
            return True

        except Exception as e:
            logger.exception("Error adding word to page: %s", e)
            return False

    def split_line_with_selected_words(
        self,
        page: "Page",
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Move selected words into exactly one newly created line.

        Selected words are removed from their source lines and inserted into one
        new line (in source order). If selection spans multiple paragraphs,
        the new line is placed in a new paragraph at page root.

        Args:
            page: Page containing lines/words.
            word_keys: List of (line_index, word_index) tuples for selected words.

        Returns:
            bool: True when at least one split was applied, False otherwise.
        """
        if not page:
            logger.warning("No page provided for split-line-by-selected-words")
            return False

        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning(
                "Split-line-by-selected-words requires at least one selected word"
            )
            return False

        try:
            lines = list(page.lines)

            # Group selected word indices by line
            line_to_selected_word_indices: dict[int, set[int]] = {}
            for line_index, word_index in unique_keys:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "Word key (%s, %s) line index out of range (0-%s)",
                        line_index,
                        word_index,
                        len(lines) - 1,
                    )
                    return False
                line_to_selected_word_indices.setdefault(line_index, set()).add(
                    word_index
                )

            # Process lines in visual order to preserve selected-word ordering.
            selected_words_for_new_line: list[Word] = []
            source_line_bboxes: list[object] = []
            containing_paragraphs: list[Block] = []
            line_insertion_points: list[tuple[Block, int]] = []
            emptied_line_ids: set[int] = set()
            for line_index in sorted(line_to_selected_word_indices):
                selected_word_indices = line_to_selected_word_indices[line_index]
                target_line = lines[line_index]
                line_words = list(target_line.words)
                source_line_original_bbox = target_line.bounding_box

                if len(line_words) < 1:
                    logger.warning("Line %s has no words", line_index)
                    return False

                # Validate word indices
                for wi in selected_word_indices:
                    if wi < 0 or wi >= len(line_words):
                        logger.warning(
                            "Word index %s out of range for line %s (0-%s)",
                            wi,
                            line_index,
                            len(line_words) - 1,
                        )
                        return False

                selected_words = [
                    line_words[wi]
                    for wi in range(len(line_words))
                    if wi in selected_word_indices
                ]
                unselected_words = [
                    line_words[wi]
                    for wi in range(len(line_words))
                    if wi not in selected_word_indices
                ]

                if not selected_words:
                    logger.warning("No selected words found on line %s", line_index)
                    return False

                selected_words_for_new_line.extend(selected_words)
                if (
                    source_line_original_bbox is not None
                    and source_line_original_bbox.has_usable_coordinates
                ):
                    source_line_bboxes.append(source_line_original_bbox)

                # Find parent paragraph
                paragraphs = list(page.paragraphs)
                target_paragraph = None
                for paragraph in paragraphs:
                    paragraph_lines = list(paragraph.lines)
                    if target_line in paragraph_lines:
                        target_paragraph = paragraph
                        break

                if target_paragraph is None:
                    logger.warning(
                        "Unable to find paragraph containing line %s", line_index
                    )
                    return False
                containing_paragraphs.append(target_paragraph)

                paragraph_items = list(target_paragraph.items)
                if target_line not in paragraph_items:
                    logger.warning(
                        "Target line missing in paragraph items for line %s",
                        line_index,
                    )
                    return False

                line_item_index = paragraph_items.index(target_line)
                line_insertion_points.append((target_paragraph, line_item_index))

                # Remove selected words from the source line.
                target_line.items = unselected_words
                target_line.unmatched_ground_truth_words = []
                if not unselected_words:
                    emptied_line_ids.add(id(target_line))

                if unselected_words:
                    try:
                        target_line.recompute_bounding_box()
                    except Exception as recompute_error:
                        if not BoundingBox.is_geometry_normalization_error(
                            recompute_error
                        ):
                            raise
                        logger.warning(
                            "Skipped source line bbox recompute due to malformed geometry on line %s: %s",
                            line_index,
                            recompute_error,
                        )

                if (
                    unselected_words
                    and not (
                        target_line.bounding_box is not None
                        and target_line.bounding_box.has_usable_coordinates
                    )
                    and (
                        source_line_original_bbox is not None
                        and source_line_original_bbox.has_usable_coordinates
                    )
                ):
                    target_line.bounding_box = source_line_original_bbox

            if not selected_words_for_new_line:
                logger.warning("No selected words found for single-line extraction")
                return False

            new_line = Block(
                items=selected_words_for_new_line,
                bounding_box=Page.first_usable_bbox(source_line_bboxes),
                child_type=BlockChildType.WORDS,
                block_category=BlockCategory.LINE,
            )
            try:
                new_line.recompute_bounding_box()
            except Exception as recompute_error:
                if not BoundingBox.is_geometry_normalization_error(recompute_error):
                    raise
                logger.warning(
                    "Skipped extracted line bbox recompute due to malformed geometry: %s",
                    recompute_error,
                )

            if (
                not (
                    new_line.bounding_box is not None
                    and new_line.bounding_box.has_usable_coordinates
                )
                and source_line_bboxes
            ):
                new_line.bounding_box = Page.first_usable_bbox(source_line_bboxes)

            unique_paragraphs = []
            for paragraph in containing_paragraphs:
                if paragraph not in unique_paragraphs:
                    unique_paragraphs.append(paragraph)

            if len(unique_paragraphs) == 1 and line_insertion_points:
                target_paragraph = unique_paragraphs[0]
                original_paragraph_items = list(target_paragraph.items)
                paragraph_items = [
                    item
                    for item in original_paragraph_items
                    if id(item) not in emptied_line_ids
                ]
                insert_after = max(
                    item_index
                    for paragraph, item_index in line_insertion_points
                    if paragraph is target_paragraph
                )
                insert_at = sum(
                    1
                    for idx, item in enumerate(original_paragraph_items)
                    if idx <= insert_after and id(item) not in emptied_line_ids
                )
                target_paragraph.items = (
                    paragraph_items[:insert_at]
                    + [new_line]
                    + paragraph_items[insert_at:]
                )
            else:
                new_paragraph = Block(
                    items=[new_line],
                    bounding_box=Page.first_usable_bbox(
                        source_line_bboxes
                        + [paragraph.bounding_box for paragraph in unique_paragraphs]
                    ),
                    child_type=BlockChildType.BLOCKS,
                    block_category=BlockCategory.PARAGRAPH,
                )
                page.items = list(page.items) + [new_paragraph]

            page.finalize_page_structure()
            logger.info(
                "Moved selected words into one new line from %d source line(s)",
                len(line_to_selected_word_indices),
            )
            return True
        except Exception as e:
            logger.exception(
                "Error splitting lines by selected words %s: %s",
                unique_keys,
                e,
            )
            return False

    def split_lines_into_selected_and_unselected_words(
        self,
        page: "Page",
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Split each affected line into selected-word and unselected-word lines.

        This is the per-line split behavior: for every line with selected words,
        keep selected words in the original line and insert one sibling line with
        the unselected words.
        """
        if not page:
            logger.warning("No page provided for split-lines-into-selected-unselected")
            return False

        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning(
                "Split-lines-into-selected-unselected requires at least one selected word"
            )
            return False

        try:
            lines = list(page.lines)

            line_to_selected_word_indices: dict[int, set[int]] = {}
            for line_index, word_index in unique_keys:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "Word key (%s, %s) line index out of range (0-%s)",
                        line_index,
                        word_index,
                        len(lines) - 1,
                    )
                    return False
                line_to_selected_word_indices.setdefault(line_index, set()).add(
                    word_index
                )

            split_any = False
            for line_index in sorted(line_to_selected_word_indices, reverse=True):
                selected_word_indices = line_to_selected_word_indices[line_index]
                target_line = lines[line_index]
                line_words = list(target_line.words)

                if len(line_words) < 2:
                    logger.warning(
                        "Line %s has fewer than 2 words; cannot split by selection",
                        line_index,
                    )
                    continue

                for wi in selected_word_indices:
                    if wi < 0 or wi >= len(line_words):
                        logger.warning(
                            "Word index %s out of range for line %s (0-%s)",
                            wi,
                            line_index,
                            len(line_words) - 1,
                        )
                        return False

                selected_words = [
                    line_words[wi]
                    for wi in range(len(line_words))
                    if wi in selected_word_indices
                ]
                unselected_words = [
                    line_words[wi]
                    for wi in range(len(line_words))
                    if wi not in selected_word_indices
                ]

                if not selected_words or not unselected_words:
                    logger.warning(
                        "Split-by-selection requires selected and unselected words on line %s",
                        line_index,
                    )
                    continue

                paragraphs = list(page.paragraphs)
                target_paragraph = None
                for paragraph in paragraphs:
                    paragraph_lines = list(paragraph.lines)
                    if target_line in paragraph_lines:
                        target_paragraph = paragraph
                        break

                if target_paragraph is None:
                    logger.warning(
                        "Unable to find paragraph containing line %s",
                        line_index,
                    )
                    return False

                paragraph_items = list(target_paragraph.items)
                if target_line not in paragraph_items:
                    logger.warning(
                        "Target line missing in paragraph items for line %s",
                        line_index,
                    )
                    return False

                line_item_index = paragraph_items.index(target_line)

                target_line.items = selected_words
                target_line.unmatched_ground_truth_words = []
                target_line.recompute_bounding_box()

                new_line = Block(
                    items=unselected_words,
                    child_type=BlockChildType.WORDS,
                    block_category=BlockCategory.LINE,
                )

                target_paragraph.items = (
                    paragraph_items[: line_item_index + 1]
                    + [new_line]
                    + paragraph_items[line_item_index + 1 :]
                )
                target_paragraph.recompute_bounding_box()

                parent = Page._find_parent_block_recursive(page, target_paragraph)
                if parent is not None:
                    parent.recompute_bounding_box()

                split_any = True

            if not split_any:
                logger.warning("No lines were split into selected/unselected groups")
                return False

            page.finalize_page_structure()
            logger.info(
                "Split %d line(s) into selected/unselected words",
                len(line_to_selected_word_indices),
            )
            return True
        except Exception as e:
            logger.exception(
                "Error splitting lines into selected/unselected words %s: %s",
                unique_keys,
                e,
            )
            return False

    def nudge_word_bbox(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool = True,
    ) -> bool:
        """Expand/contract a word bounding box by pixel deltas.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            left_delta: Left-edge size delta in pixels (+ expands left, - contracts).
            right_delta: Right-edge size delta in pixels (+ expands right, - contracts).
            top_delta: Top-edge size delta in pixels (+ expands up, - contracts).
            bottom_delta: Bottom-edge size delta in pixels (+ expands down, - contracts).
            refine_after: Whether to run word-level refine helpers after resize.

        Returns:
            bool: True when nudge succeeds, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word bbox nudge")
            return False

        try:
            line_words = page.validated_line_words(line_index)
            if line_words is None:
                return False
            if word_index < 0 or word_index >= len(line_words):
                logger.warning(
                    "Word nudge index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(line_words) - 1,
                )
                return False

            word = line_words[word_index]
            bbox = word.bounding_box
            if bbox is None:
                logger.warning(
                    "Word bbox nudge requires an existing bbox for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return False

            is_normalized = bool(bbox.is_normalized)
            if is_normalized:
                page_width, page_height = page.resolved_dimensions
                if page_width <= 0.0 or page_height <= 0.0:
                    logger.warning(
                        "Unable to resolve page dimensions for normalized bbox nudge"
                    )
                    return False
                x1 = float(bbox.minX or 0.0) * page_width
                y1 = float(bbox.minY or 0.0) * page_height
                x2 = float(bbox.maxX or 0.0) * page_width
                y2 = float(bbox.maxY or 0.0) * page_height
            else:
                x1 = float(bbox.minX or 0.0)
                y1 = float(bbox.minY or 0.0)
                x2 = float(bbox.maxX or 0.0)
                y2 = float(bbox.maxY or 0.0)

            nx1 = x1 - float(left_delta)
            ny1 = y1 - float(top_delta)
            nx2 = x2 + float(right_delta)
            ny2 = y2 + float(bottom_delta)

            page_width, page_height = page.resolved_dimensions
            nx1 = max(0.0, nx1)
            ny1 = max(0.0, ny1)
            if page_width > 0.0:
                nx2 = min(nx2, page_width)
            if page_height > 0.0:
                ny2 = min(ny2, page_height)

            if nx2 <= nx1 or ny2 <= ny1:
                logger.warning(
                    "Invalid bbox size after resize for line=%s word=%s: (%s, %s, %s, %s)",
                    line_index,
                    word_index,
                    nx1,
                    ny1,
                    nx2,
                    ny2,
                )
                return False

            return self.rebox_word(
                page,
                line_index,
                word_index,
                nx1,
                ny1,
                nx2,
                ny2,
                refine_after=refine_after,
            )
        except Exception as e:
            logger.exception(
                "Error resizing word bbox line=%s index=%s deltas=(l=%s r=%s t=%s b=%s): %s",
                line_index,
                word_index,
                left_delta,
                right_delta,
                top_delta,
                bottom_delta,
                e,
            )
            raise

    # ------------------------------------------------------------------
    # Paragraph operations (delegate directly to Page)
    # ------------------------------------------------------------------

    def merge_paragraphs(self, page: Page, paragraph_indices: list[int]) -> bool:
        return page.merge_paragraphs(paragraph_indices)

    def delete_paragraphs(self, page: Page, paragraph_indices: list[int]) -> bool:
        return page.delete_paragraphs(paragraph_indices)

    def split_paragraphs(self, page: Page, paragraph_indices: list[int]) -> bool:
        return page.split_paragraphs(paragraph_indices)

    def split_paragraph_after_line(self, page: Page, line_index: int) -> bool:
        return page.split_paragraph_after_line(line_index)

    def split_paragraph_with_selected_lines(
        self,
        page: Page,
        line_indices: list[int],
    ) -> bool:
        return page.split_paragraph_with_selected_lines(line_indices)

    def group_selected_words_into_new_paragraph(
        self,
        page: Page,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        return page.group_selected_words_into_new_paragraph(word_keys)

    # ------------------------------------------------------------------
    # Word/line/paragraph bbox refinement operations (delegate to Page)
    # ------------------------------------------------------------------

    def refine_words(self, page: Page, word_keys: list[tuple[int, int]]) -> bool:
        return page.refine_words(word_keys)

    def expand_then_refine_words(
        self,
        page: Page,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        return page.expand_then_refine_words(word_keys)

    def expand_word_bboxes(
        self,
        page: Page,
        word_keys: list[tuple[int, int]],
        padding_px: float = 2.0,
    ) -> bool:
        return page.expand_word_bboxes(word_keys, padding_px)

    def refine_lines(self, page: Page, line_indices: list[int]) -> bool:
        return page.refine_lines(line_indices)

    def refine_paragraphs(self, page: Page, paragraph_indices: list[int]) -> bool:
        return page.refine_paragraphs(paragraph_indices)

    def expand_then_refine_lines(
        self,
        page: Page,
        line_indices: list[int],
    ) -> bool:
        return page.expand_then_refine_lines(line_indices)

    def expand_then_refine_paragraphs(
        self,
        page: Page,
        paragraph_indices: list[int],
    ) -> bool:
        return page.expand_then_refine_paragraphs(paragraph_indices)

    def expand_line_bboxes(
        self,
        page: Page,
        line_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        return page.expand_line_bboxes(line_indices, padding_px)

    def expand_paragraph_bboxes(
        self,
        page: Page,
        paragraph_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        return page.expand_paragraph_bboxes(paragraph_indices, padding_px)
