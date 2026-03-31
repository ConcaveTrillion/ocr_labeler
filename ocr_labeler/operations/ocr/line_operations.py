"""Line operations for OCR labeling tasks.

This module contains operations that can be performed on lines within pages,
such as copying ground truth to OCR text, word-level editing, and line-level
transformations. These operations are separated from state management to
maintain clear architectural boundaries.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .word_operations import WordOperations

if TYPE_CHECKING:
    from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


@runtime_checkable
class _ParagraphLike(Protocol):
    def recompute_bounding_box(self) -> None: ...


@runtime_checkable
class _PageWithParagraphs(Protocol):
    @property
    def paragraphs(self) -> Sequence[object]: ...


class LineOperations:
    """Handle line-level operations like ground truth copying and word editing.

    This class provides functionality for:
    - Copying ground truth text to OCR text for entire lines
    - Word-level editing within lines
    - Line-level text transformations
    - Line validation and consistency checks

    Operations are designed to be stateless and work with dependency injection
    to avoid tight coupling with state management classes.
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
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = line.words
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                gt_text = word.ground_truth_text
                if gt_text:
                    # Copy ground truth to OCR text
                    word.text = gt_text
                    modified_count += 1
                    logger.debug(
                        f"Copied GT→OCR for word {word_idx} in line {line_index}: '{gt_text}'"
                    )

            if modified_count > 0:
                logger.info(
                    f"Copied GT→OCR for {modified_count} words in line {line_index}"
                )
                return True
            else:
                logger.info(f"No ground truth text found to copy in line {line_index}")
                return False

        except Exception as e:
            logger.exception(f"Error copying GT→OCR for line {line_index}: {e}")
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
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = line.words
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                ocr_text = word.text
                if ocr_text:
                    # Copy OCR text to ground truth
                    word.ground_truth_text = ocr_text
                    modified_count += 1
                    logger.debug(
                        f"Copied OCR→GT for word {word_idx} in line {line_index}: '{ocr_text}'"
                    )

            if modified_count > 0:
                logger.info(
                    f"Copied OCR→GT for {modified_count} words in line {line_index}"
                )
                return True
            else:
                logger.info(f"No OCR text found to copy in line {line_index}")
                return False

        except Exception as e:
            logger.exception(f"Error copying OCR→GT for line {line_index}: {e}")
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
                line_words = self._validated_line_words(page, line_index)
                if (
                    line_words is None
                    or word_index < 0
                    or word_index >= len(line_words)
                ):
                    continue

                target_word = line_words[word_index]
                ocr_text = str(getattr(target_word, "text", "") or "")
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
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = line.words
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                if word.ground_truth_text:
                    word.ground_truth_text = ""
                    modified_count += 1
                    logger.debug(f"Cleared GT for word {word_idx} in line {line_index}")

            if modified_count > 0:
                logger.info(
                    f"Cleared GT for {modified_count} words in line {line_index}"
                )
                return True
            else:
                logger.info(f"No ground truth text found to clear in line {line_index}")
                return False

        except Exception as e:
            logger.exception(f"Error clearing GT for line {line_index}: {e}")
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
            line_words = self._validated_line_words(page, line_index)
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
            if (
                str(getattr(target_word, "ground_truth_text", "") or "")
                == normalized_value
            ):
                logger.debug(
                    "Word GT unchanged for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return True

            target_word.ground_truth_text = normalized_value

            lines = list(page.lines)
            target_line = lines[line_index]
            if hasattr(target_line, "words"):
                line_gt = " ".join(
                    str(getattr(word, "ground_truth_text", "") or "")
                    for word in list(getattr(target_line, "words", []) or [])
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
            line_words = self._validated_line_words(page, line_index)
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
            word_ops = WordOperations()

            desired_italic = bool(italic)
            desired_small_caps = bool(small_caps)
            desired_blackletter = bool(blackletter)
            desired_left_footnote = bool(left_footnote)
            desired_right_footnote = bool(right_footnote)

            if (
                word_ops.read_word_attribute(
                    target_word, "italic", aliases=("is_italic",)
                )
                == desired_italic
                and word_ops.read_word_attribute(
                    target_word, "small_caps", aliases=("is_small_caps",)
                )
                == desired_small_caps
                and word_ops.read_word_attribute(
                    target_word, "blackletter", aliases=("is_blackletter",)
                )
                == desired_blackletter
                and word_ops.read_word_attribute(
                    target_word, "left_footnote", aliases=("is_left_footnote",)
                )
                == desired_left_footnote
                and word_ops.read_word_attribute(
                    target_word, "right_footnote", aliases=("is_right_footnote",)
                )
                == desired_right_footnote
            ):
                logger.debug(
                    "Word attributes unchanged for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return True

            word_ops.update_word_attributes(
                target_word,
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

    def validate_line_consistency(
        self, page: "Page", line_index: int
    ) -> dict[str, any]:
        """Validate consistency of OCR vs ground truth for a line.

        Args:
            page: Page containing the line to validate
            line_index: Zero-based line index to validate

        Returns:
            dict: Validation results with statistics and issues
        """
        if not page:
            logger.warning("No page provided for line validation")
            return {"valid": False, "error": "No page provided"}

        try:
            lines = page.lines
            if line_index < 0 or line_index >= len(lines):
                return {
                    "valid": False,
                    "error": f"Line index {line_index} out of range (0-{len(lines) - 1})",
                }

            line = lines[line_index]
            words = line.words
            if not words:
                return {
                    "valid": True,
                    "words": 0,
                    "with_gt": 0,
                    "matches": 0,
                    "mismatches": 0,
                }

            total_words = len(words)
            words_with_gt = 0
            exact_matches = 0
            mismatches = []

            for word_idx, word in enumerate(words):
                ocr_text = word.text
                gt_text = word.ground_truth_text

                if gt_text:
                    words_with_gt += 1
                    if ocr_text == gt_text:
                        exact_matches += 1
                    else:
                        mismatches.append(
                            {
                                "word_index": word_idx,
                                "ocr_text": ocr_text,
                                "gt_text": gt_text,
                            }
                        )

            return {
                "valid": True,
                "words": total_words,
                "with_gt": words_with_gt,
                "matches": exact_matches,
                "mismatches": len(mismatches),
                "mismatch_details": mismatches,
                "accuracy": exact_matches / words_with_gt if words_with_gt > 0 else 1.0,
            }

        except Exception as e:
            logger.exception(f"Error validating line {line_index}: {e}")
            return {"valid": False, "error": str(e)}

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
            from pd_book_tools.ocr.block import Block

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
                    if not self._is_geometry_normalization_error(merge_error):
                        raise
                    logger.warning(
                        "Line merge hit malformed bbox metadata (primary=%s secondary=%s): %s; applying merge fallback",
                        primary_index,
                        index,
                        merge_error,
                    )
                    if not self._merge_line_blocks_fallback(
                        primary_line,
                        secondary_line,
                    ):
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
                self._finalize_page_structure(page)
            except Exception as finalize_error:
                if not self._is_geometry_normalization_error(finalize_error):
                    raise
                logger.warning(
                    "Merged lines but skipped final bbox recompute due to malformed geometry: %s",
                    finalize_error,
                )
                self._remove_empty_items_safely(page)
                self._recompute_paragraph_bboxes_with_block_api(page)

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

    def merge_paragraphs(self, page: "Page", paragraph_indices: list[int]) -> bool:
        """Merge selected paragraphs into the first selected paragraph.

        Args:
            page: Page containing paragraphs to merge.
            paragraph_indices: Zero-based paragraph indices to merge.

        Returns:
            bool: True if merge succeeded and modified the page, False otherwise.
        """
        if not page:
            logger.warning("No page provided for paragraph merge")
            return False

        try:
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            paragraph_count_before = len(paragraphs)

            logger.debug(
                "merge_paragraphs start: page_type=%s, paragraph_count=%d, requested=%s",
                type(page).__name__,
                paragraph_count_before,
                paragraph_indices,
            )

            unique_indices = sorted(set(paragraph_indices or []))
            if len(unique_indices) < 2:
                logger.warning(
                    "Paragraph merge requires selecting at least two paragraphs"
                )
                return False

            for index in unique_indices:
                if index < 0 or index >= paragraph_count_before:
                    logger.warning(
                        "Paragraph index %s out of range (0-%s)",
                        index,
                        paragraph_count_before - 1,
                    )
                    return False

            primary_index = unique_indices[0]
            primary_paragraph = paragraphs[primary_index]

            for index in unique_indices[1:]:
                primary_paragraph.merge(paragraphs[index])

            for index in reversed(unique_indices[1:]):
                if not self._remove_nested_block(page, paragraphs[index]):
                    logger.warning(
                        "Failed to remove merged paragraph at index %s", index
                    )
                    return False

            if hasattr(page, "remove_empty_items") and callable(
                getattr(page, "remove_empty_items")
            ):
                page.remove_empty_items()
            if hasattr(page, "recompute_bounding_box") and callable(
                getattr(page, "recompute_bounding_box")
            ):
                page.recompute_bounding_box()

            paragraph_count_after = len(list(getattr(page, "paragraphs", []) or []))
            logger.info(
                "Merged %d paragraphs into paragraph %d (paragraph_count %d -> %d)",
                len(unique_indices),
                primary_index,
                paragraph_count_before,
                paragraph_count_after,
            )
            return True

        except Exception as e:
            logger.exception("Error merging paragraphs %s: %s", paragraph_indices, e)
            return False

    def delete_paragraphs(self, page: "Page", paragraph_indices: list[int]) -> bool:
        """Delete selected paragraphs from a page.

        Args:
            page: Page containing paragraphs to delete.
            paragraph_indices: Zero-based paragraph indices to delete.

        Returns:
            bool: True if deletion succeeded and modified the page, False otherwise.
        """
        if not page:
            logger.warning("No page provided for paragraph deletion")
            return False

        try:
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            paragraph_count_before = len(paragraphs)

            unique_indices = sorted(set(paragraph_indices or []))
            if not unique_indices:
                logger.warning("Paragraph deletion requires selecting at least one")
                return False

            for index in unique_indices:
                if index < 0 or index >= paragraph_count_before:
                    logger.warning(
                        "Paragraph index %s out of range (0-%s)",
                        index,
                        paragraph_count_before - 1,
                    )
                    return False

            for index in reversed(unique_indices):
                if not self._remove_nested_block(page, paragraphs[index]):
                    logger.warning(
                        "Failed to remove paragraph at index %s during deletion",
                        index,
                    )
                    return False

            if hasattr(page, "remove_empty_items") and callable(
                getattr(page, "remove_empty_items")
            ):
                page.remove_empty_items()
            if hasattr(page, "recompute_bounding_box") and callable(
                getattr(page, "recompute_bounding_box")
            ):
                page.recompute_bounding_box()

            paragraph_count_after = len(list(getattr(page, "paragraphs", []) or []))
            logger.info(
                "Deleted %d paragraphs (paragraph_count %d -> %d)",
                len(unique_indices),
                paragraph_count_before,
                paragraph_count_after,
            )
            return True

        except Exception as e:
            logger.exception("Error deleting paragraphs %s: %s", paragraph_indices, e)
            return False

    def split_paragraphs(self, page: "Page", paragraph_indices: list[int]) -> bool:
        """Split selected paragraphs into one paragraph per line.

        Args:
            page: Page containing paragraphs to split.
            paragraph_indices: Zero-based paragraph indices to split.

        Returns:
            bool: True if any selected paragraph was split, False otherwise.
        """
        if not page:
            logger.warning("No page provided for paragraph split")
            return False

        try:
            from pd_book_tools.ocr.block import Block, BlockCategory

            paragraphs = list(getattr(page, "paragraphs", []) or [])
            paragraph_count_before = len(paragraphs)

            logger.debug(
                "split_paragraphs start: page_type=%s, paragraph_count=%d, requested=%s",
                type(page).__name__,
                paragraph_count_before,
                paragraph_indices,
            )

            unique_indices = sorted(set(paragraph_indices or []))
            if not unique_indices:
                logger.warning(
                    "Paragraph split requires selecting at least one paragraph"
                )
                return False

            for index in unique_indices:
                if index < 0 or index >= paragraph_count_before:
                    logger.warning(
                        "Paragraph index %s out of range (0-%s)",
                        index,
                        paragraph_count_before - 1,
                    )
                    return False

            changed = False
            for index in reversed(unique_indices):
                paragraph = paragraphs[index]
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                if len(paragraph_lines) < 2:
                    logger.debug(
                        "Skipping paragraph %s split; requires at least 2 lines", index
                    )
                    continue

                parent = self._find_parent_block(page, paragraph)
                if parent is None:
                    logger.warning(
                        "Unable to find parent for paragraph index %s", index
                    )
                    continue

                if not self._replace_block_with_split_paragraphs(
                    parent,
                    paragraph,
                    paragraph_lines,
                    Block,
                    BlockCategory,
                ):
                    logger.warning("Unable to split paragraph index %s", index)
                    continue
                changed = True

            if not changed:
                logger.info("No selected paragraphs were split")
                return False

            if hasattr(page, "remove_empty_items") and callable(
                getattr(page, "remove_empty_items")
            ):
                page.remove_empty_items()
            if hasattr(page, "recompute_bounding_box") and callable(
                getattr(page, "recompute_bounding_box")
            ):
                page.recompute_bounding_box()

            paragraph_count_after = len(list(getattr(page, "paragraphs", []) or []))
            logger.info(
                "Split selected paragraphs (paragraph_count %d -> %d)",
                paragraph_count_before,
                paragraph_count_after,
            )
            return True

        except Exception as e:
            logger.exception("Error splitting paragraphs %s: %s", paragraph_indices, e)
            return False

    def split_paragraph_after_line(self, page: "Page", line_index: int) -> bool:
        """Split the containing paragraph immediately after the selected line.

        Args:
            page: Page containing the line and paragraph to split.
            line_index: Zero-based line index used as the split point.

        Returns:
            bool: True when paragraph split is applied, False otherwise.
        """
        if not page:
            logger.warning("No page provided for paragraph split-after-line")
            return False

        try:
            from pd_book_tools.ocr.block import Block, BlockCategory

            lines = list(getattr(page, "lines", []) or [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range for paragraph split (0-%s)",
                    line_index,
                    len(lines) - 1,
                )
                return False

            selected_line = lines[line_index]
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            target_paragraph = None
            target_paragraph_lines: list[object] = []

            for paragraph in paragraphs:
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                if selected_line in paragraph_lines:
                    target_paragraph = paragraph
                    target_paragraph_lines = paragraph_lines
                    break

            if target_paragraph is None:
                logger.warning(
                    "Unable to find paragraph containing line index %s", line_index
                )
                return False

            split_offset = target_paragraph_lines.index(selected_line)
            if split_offset >= len(target_paragraph_lines) - 1:
                logger.warning(
                    "Cannot split paragraph after last line (line index %s)",
                    line_index,
                )
                return False

            first_lines = target_paragraph_lines[: split_offset + 1]
            second_lines = target_paragraph_lines[split_offset + 1 :]
            if not first_lines or not second_lines:
                logger.warning(
                    "Paragraph split produced empty segment(s) for line index %s",
                    line_index,
                )
                return False

            parent = self._find_parent_block(page, target_paragraph)
            if parent is None:
                logger.warning(
                    "Unable to locate parent block for paragraph split after line %s",
                    line_index,
                )
                return False

            current_items = list(getattr(parent, "items", []) or [])
            if target_paragraph not in current_items:
                logger.warning(
                    "Target paragraph not found in parent items for line index %s",
                    line_index,
                )
                return False

            paragraph_idx = current_items.index(target_paragraph)
            replacement = [
                Block(items=first_lines, block_category=BlockCategory.PARAGRAPH),
                Block(items=second_lines, block_category=BlockCategory.PARAGRAPH),
            ]
            setattr(
                parent,
                "items",
                current_items[:paragraph_idx]
                + replacement
                + current_items[paragraph_idx + 1 :],
            )

            if hasattr(page, "remove_empty_items") and callable(
                getattr(page, "remove_empty_items")
            ):
                page.remove_empty_items()
            if hasattr(page, "recompute_bounding_box") and callable(
                getattr(page, "recompute_bounding_box")
            ):
                page.recompute_bounding_box()

            logger.info("Split paragraph after line index %s", line_index)
            return True

        except Exception as e:
            logger.exception(
                "Error splitting paragraph after line index %s: %s", line_index, e
            )
            return False

    def split_paragraph_with_selected_lines(
        self, page: "Page", line_indices: list[int]
    ) -> bool:
        """Split a paragraph into selected lines and unselected lines.

        Args:
            page: Page containing selected lines and paragraph to split.
            line_indices: Zero-based selected line indices.

        Returns:
            bool: True when split is applied, False otherwise.
        """
        if not page:
            logger.warning("No page provided for paragraph split-by-selected-lines")
            return False

        try:
            from pd_book_tools.ocr.block import Block, BlockCategory

            lines = list(getattr(page, "lines", []) or [])
            unique_indices = sorted(set(line_indices or []))
            if not unique_indices:
                logger.warning(
                    "Split-by-selected-lines requires at least one selected line"
                )
                return False

            for line_index in unique_indices:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "Line index %s out of range for split-by-selected-lines (0-%s)",
                        line_index,
                        len(lines) - 1,
                    )
                    return False

            selected_lines = [lines[line_index] for line_index in unique_indices]
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            target_paragraph = None
            target_paragraph_lines: list[object] = []

            for paragraph in paragraphs:
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                if any(line in paragraph_lines for line in selected_lines):
                    target_paragraph = paragraph
                    target_paragraph_lines = paragraph_lines
                    break

            if target_paragraph is None:
                logger.warning(
                    "Unable to find paragraph containing selected lines %s",
                    unique_indices,
                )
                return False

            if not all(line in target_paragraph_lines for line in selected_lines):
                logger.warning(
                    "Selected lines %s span multiple paragraphs; split requires one paragraph",
                    unique_indices,
                )
                return False

            selected_line_set = set(selected_lines)
            selected_paragraph_lines = [
                line for line in target_paragraph_lines if line in selected_line_set
            ]
            unselected_paragraph_lines = [
                line for line in target_paragraph_lines if line not in selected_line_set
            ]

            if not selected_paragraph_lines or not unselected_paragraph_lines:
                logger.warning(
                    "Split-by-selected-lines requires selecting a strict subset of a paragraph"
                )
                return False

            parent = self._find_parent_block(page, target_paragraph)
            if parent is None:
                logger.warning(
                    "Unable to locate parent block for split-by-selected-lines %s",
                    unique_indices,
                )
                return False

            current_items = list(getattr(parent, "items", []) or [])
            if target_paragraph not in current_items:
                logger.warning(
                    "Target paragraph missing in parent items for selected lines %s",
                    unique_indices,
                )
                return False

            paragraph_idx = current_items.index(target_paragraph)
            replacement = [
                Block(
                    items=selected_paragraph_lines,
                    block_category=BlockCategory.PARAGRAPH,
                ),
                Block(
                    items=unselected_paragraph_lines,
                    block_category=BlockCategory.PARAGRAPH,
                ),
            ]
            setattr(
                parent,
                "items",
                current_items[:paragraph_idx]
                + replacement
                + current_items[paragraph_idx + 1 :],
            )

            if hasattr(page, "remove_empty_items") and callable(
                getattr(page, "remove_empty_items")
            ):
                page.remove_empty_items()
            if hasattr(page, "recompute_bounding_box") and callable(
                getattr(page, "recompute_bounding_box")
            ):
                page.recompute_bounding_box()

            logger.info(
                "Split paragraph by selected lines %s into selected/unselected groups",
                unique_indices,
            )
            return True

        except Exception as e:
            logger.exception(
                "Error splitting paragraph with selected lines %s: %s",
                line_indices,
                e,
            )
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
                    line_words = self._validated_line_words(page, line_index)
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
                line_words = self._validated_line_words(page, line_index)
                if line_words is None:
                    return False
                for word_index in sorted(word_indices, reverse=True):
                    if not self._remove_word_from_line(
                        page=page,
                        line_index=line_index,
                        word_index=word_index,
                        line_words=line_words,
                    ):
                        return False

            self._finalize_page_structure(page)

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
        return self._merge_adjacent_words(
            page=page,
            line_index=line_index,
            word_index=word_index,
            direction="left",
        )

    def merge_word_right(self, page: "Page", line_index: int, word_index: int) -> bool:
        """Merge the selected word with its immediate right neighbor.

        Args:
            page: Page containing lines/words.
            line_index: Zero-based line index.
            word_index: Zero-based word index to merge with the right neighbor.

        Returns:
            bool: True when merge succeeds, False otherwise.
        """
        return self._merge_adjacent_words(
            page=page,
            line_index=line_index,
            word_index=word_index,
            direction="right",
        )

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
            words = list(getattr(line, "words", []) or [])
            if word_index < 0 or word_index >= len(words):
                logger.warning(
                    "Word split index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(words) - 1,
                )
                return False

            word = words[word_index]
            word_text = str(getattr(word, "text", "") or "")
            if len(word_text) < 2:
                logger.warning(
                    "Word split requires at least two characters (line=%s, word=%s)",
                    line_index,
                    word_index,
                )
                return False

            bbox = getattr(word, "bounding_box", None)
            bbox_width = float(getattr(bbox, "width", 0.0) or 0.0)
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

            split_word = getattr(line, "split_word", None)
            if callable(split_word):
                split_word(
                    split_word_index=word_index,
                    bbox_split_offset=bbox_split_offset,
                    character_split_index=character_split_index,
                )
            else:
                word_left, word_right = word.split(
                    bbox_split_offset=bbox_split_offset,
                    character_split_index=character_split_index,
                )
                remove_item = getattr(line, "remove_item", None)
                add_item = getattr(line, "add_item", None)
                if callable(remove_item) and callable(add_item):
                    remove_item(word)
                    add_item(word_left)
                    add_item(word_right)
                else:
                    logger.warning(
                        "Line type %s does not support split replacement APIs",
                        type(line).__name__,
                    )
                    return False

            updated_words = self._validated_line_words(page, line_index)
            if updated_words is None:
                return False
            for updated_word in updated_words:
                updated_word.ground_truth_text = ""

            self._finalize_page_structure(page)

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
        lines_before_split = list(getattr(page, "lines", []) or [])
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
            lines = list(getattr(page, "lines", []) or [])
            source_words = list(getattr(source_line, "words", []) or [])
            if word_index < 0 or word_index + 1 >= len(source_words):
                logger.warning(
                    "Post-split word indices %s/%s unavailable on line %s",
                    word_index,
                    word_index + 1,
                    line_index,
                )
                return False

            split_words = [source_words[word_index], source_words[word_index + 1]]
            line_midpoints = {
                id(line): self._line_vertical_midpoint(line) for line in lines
            }

            touched_lines: dict[int, object] = {id(source_line): source_line}
            for split_piece in split_words:
                midpoint_y = self._word_vertical_midpoint(split_piece)
                target_line = self._closest_line_by_midpoint(
                    lines,
                    line_midpoints,
                    midpoint_y,
                    fallback_line=source_line,
                )
                touched_lines[id(target_line)] = target_line

                if target_line is source_line:
                    continue

                if not self._move_word_between_lines(
                    source_line, target_line, split_piece
                ):
                    logger.warning(
                        "Failed to move split word piece to closest line (line=%s word=%s)",
                        line_index,
                        word_index,
                    )
                    return False

            for touched_line in touched_lines.values():
                touched_words = list(getattr(touched_line, "words", []) or [])
                for touched_word in touched_words:
                    touched_word.ground_truth_text = ""
                recompute_line = getattr(touched_line, "recompute_bounding_box", None)
                if callable(recompute_line):
                    recompute_line()

            self._finalize_page_structure(page)

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
            from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType

            lines = list(getattr(page, "lines", []) or [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "Line index %s out of range for line split (0-%s)",
                    line_index,
                    len(lines) - 1,
                )
                return False

            target_line = lines[line_index]
            line_words = list(getattr(target_line, "words", []) or [])
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

            paragraphs = list(getattr(page, "paragraphs", []) or [])
            target_paragraph = None
            for paragraph in paragraphs:
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                if target_line in paragraph_lines:
                    target_paragraph = paragraph
                    break

            if target_paragraph is None:
                logger.warning(
                    "Unable to find paragraph containing line index %s",
                    line_index,
                )
                return False

            parent = self._find_parent_block(page, target_paragraph)
            if parent is None:
                logger.warning(
                    "Unable to locate parent block for line split after word (%s, %s)",
                    line_index,
                    word_index,
                )
                return False

            paragraph_items = list(getattr(target_paragraph, "items", []) or [])
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

            self._finalize_page_structure(page)

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
            line_words = self._validated_line_words(page, line_index)
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

            from pd_book_tools.geometry.bounding_box import BoundingBox
            from pd_book_tools.geometry.point import Point

            word = line_words[word_index]
            existing_bbox = getattr(word, "bounding_box", None)
            is_normalized = bool(getattr(existing_bbox, "is_normalized", False))

            if is_normalized:
                page_width, page_height = self._resolve_page_dimensions(page)
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
                self._refine_word_bbox(page, word)
            self._finalize_page_structure(page)

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

    def refine_words(self, page: "Page", word_keys: list[tuple[int, int]]) -> bool:
        """Refine selected word bounding boxes.

        Args:
            page: Page containing lines/words.
            word_keys: List of (line_index, word_index) tuples.

        Returns:
            bool: True if any selected words were refined, False otherwise.
        """
        if not page:
            logger.warning("No page provided for word refine")
            return False

        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning("Word refine requires selecting at least one word")
            return False

        try:
            refined_any = False
            for line_index, word_index in unique_keys:
                line_words = self._validated_line_words(page, line_index)
                if line_words is None:
                    return False
                if word_index < 0 or word_index >= len(line_words):
                    logger.warning(
                        "Word refine index %s out of range for line %s (0-%s)",
                        word_index,
                        line_index,
                        len(line_words) - 1,
                    )
                    return False

                refined_any = (
                    self._refine_word_bbox(page, line_words[word_index]) or refined_any
                )

            if not refined_any:
                logger.warning("Selected words could not be refined")
                return False

            self._finalize_page_structure(page)
            logger.info("Refined %d selected words", len(unique_keys))
            return True
        except Exception as e:
            logger.exception("Error refining words %s: %s", unique_keys, e)
            return False

    def expand_then_refine_words(
        self,
        page: "Page",
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Expand then refine selected word bounding boxes.

        Args:
            page: Page containing lines/words.
            word_keys: List of (line_index, word_index) tuples.

        Returns:
            bool: True if any selected words were expanded/refined, False otherwise.
        """
        if not page:
            logger.warning("No page provided for expand-then-refine")
            return False

        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning("Expand-then-refine requires selecting at least one word")
            return False

        try:
            refined_any = False
            for line_index, word_index in unique_keys:
                line_words = self._validated_line_words(page, line_index)
                if line_words is None:
                    return False
                if word_index < 0 or word_index >= len(line_words):
                    logger.warning(
                        "Expand-then-refine word index %s out of range for line %s (0-%s)",
                        word_index,
                        line_index,
                        len(line_words) - 1,
                    )
                    return False

                refined_any = (
                    self._expand_then_refine_word_bbox(page, line_words[word_index])
                    or refined_any
                )

            if not refined_any:
                logger.warning("Selected words could not be expanded/refined")
                return False

            self._finalize_page_structure(page)
            logger.info("Expand-then-refined %d selected words", len(unique_keys))
            return True
        except Exception as e:
            logger.exception("Error expand-then-refining words %s: %s", unique_keys, e)
            return False

    def refine_lines(self, page: "Page", line_indices: list[int]) -> bool:
        """Refine all words/bboxes in selected lines.

        Args:
            page: Page containing lines.
            line_indices: Zero-based selected line indices.

        Returns:
            bool: True if any selected lines were refined, False otherwise.
        """
        if not page:
            logger.warning("No page provided for line refine")
            return False

        unique_indices = sorted(set(line_indices or []))
        if not unique_indices:
            logger.warning("Line refine requires selecting at least one line")
            return False

        try:
            lines = list(page.lines)
            refined_any = False
            for line_index in unique_indices:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "Line refine index %s out of range (0-%s)",
                        line_index,
                        len(lines) - 1,
                    )
                    return False
                refined_any = (
                    self._refine_block_words(page, lines[line_index]) or refined_any
                )

            if not refined_any:
                logger.warning("Selected lines could not be refined")
                return False

            self._finalize_page_structure(page)
            logger.info("Refined %d selected lines", len(unique_indices))
            return True
        except Exception as e:
            logger.exception("Error refining lines %s: %s", unique_indices, e)
            return False

    def refine_paragraphs(self, page: "Page", paragraph_indices: list[int]) -> bool:
        """Refine all words/bboxes in selected paragraphs.

        Args:
            page: Page containing paragraphs.
            paragraph_indices: Zero-based selected paragraph indices.

        Returns:
            bool: True if any selected paragraphs were refined, False otherwise.
        """
        if not page:
            logger.warning("No page provided for paragraph refine")
            return False

        unique_indices = sorted(set(paragraph_indices or []))
        if not unique_indices:
            logger.warning("Paragraph refine requires selecting at least one paragraph")
            return False

        try:
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            if not paragraphs:
                logger.warning("Page has no paragraphs to refine")
                return False

            refined_any = False
            for paragraph_index in unique_indices:
                if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                    logger.warning(
                        "Paragraph refine index %s out of range (0-%s)",
                        paragraph_index,
                        len(paragraphs) - 1,
                    )
                    return False

                paragraph = paragraphs[paragraph_index]
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                for line in paragraph_lines:
                    refined_any = self._refine_block_words(page, line) or refined_any
                recompute_paragraph = getattr(paragraph, "recompute_bounding_box", None)
                if callable(recompute_paragraph):
                    recompute_paragraph()

            if not refined_any:
                logger.warning("Selected paragraphs could not be refined")
                return False

            self._finalize_page_structure(page)
            logger.info("Refined %d selected paragraphs", len(unique_indices))
            return True
        except Exception as e:
            logger.exception(
                "Error refining paragraphs %s: %s",
                unique_indices,
                e,
            )
            return False

    def expand_then_refine_lines(self, page: "Page", line_indices: list[int]) -> bool:
        """Expand then refine all words/bboxes in selected lines.

        Args:
            page: Page containing lines.
            line_indices: Zero-based selected line indices.

        Returns:
            bool: True if any selected lines were expanded/refined, False otherwise.
        """
        if not page:
            logger.warning("No page provided for expand-then-refine lines")
            return False

        unique_indices = sorted(set(line_indices or []))
        if not unique_indices:
            logger.warning(
                "Expand-then-refine lines requires selecting at least one line"
            )
            return False

        try:
            lines = list(page.lines)
            refined_any = False
            for line_index in unique_indices:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "Expand-then-refine line index %s out of range (0-%s)",
                        line_index,
                        len(lines) - 1,
                    )
                    return False
                line = lines[line_index]
                line_words = list(getattr(line, "words", []) or [])
                for word in line_words:
                    refined_any = (
                        self._expand_then_refine_word_bbox(page, word) or refined_any
                    )
                recompute_line = getattr(line, "recompute_bounding_box", None)
                if callable(recompute_line):
                    recompute_line()

            if not refined_any:
                logger.warning("Selected lines could not be expanded/refined")
                return False

            self._finalize_page_structure(page)
            logger.info("Expand-then-refined %d selected lines", len(unique_indices))
            return True
        except Exception as e:
            logger.exception(
                "Error expand-then-refining lines %s: %s", unique_indices, e
            )
            return False

    def expand_then_refine_paragraphs(
        self, page: "Page", paragraph_indices: list[int]
    ) -> bool:
        """Expand then refine all words/bboxes in selected paragraphs.

        Args:
            page: Page containing paragraphs.
            paragraph_indices: Zero-based selected paragraph indices.

        Returns:
            bool: True if any selected paragraphs were expanded/refined, False otherwise.
        """
        if not page:
            logger.warning("No page provided for expand-then-refine paragraphs")
            return False

        unique_indices = sorted(set(paragraph_indices or []))
        if not unique_indices:
            logger.warning(
                "Expand-then-refine paragraphs requires selecting at least one paragraph"
            )
            return False

        try:
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            if not paragraphs:
                logger.warning("Page has no paragraphs to expand-then-refine")
                return False

            refined_any = False
            for paragraph_index in unique_indices:
                if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                    logger.warning(
                        "Expand-then-refine paragraph index %s out of range (0-%s)",
                        paragraph_index,
                        len(paragraphs) - 1,
                    )
                    return False

                paragraph = paragraphs[paragraph_index]
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                for line in paragraph_lines:
                    line_words = list(getattr(line, "words", []) or [])
                    for word in line_words:
                        refined_any = (
                            self._expand_then_refine_word_bbox(page, word)
                            or refined_any
                        )
                    recompute_line = getattr(line, "recompute_bounding_box", None)
                    if callable(recompute_line):
                        recompute_line()
                recompute_paragraph = getattr(paragraph, "recompute_bounding_box", None)
                if callable(recompute_paragraph):
                    recompute_paragraph()

            if not refined_any:
                logger.warning("Selected paragraphs could not be expanded/refined")
                return False

            self._finalize_page_structure(page)
            logger.info(
                "Expand-then-refined %d selected paragraphs", len(unique_indices)
            )
            return True
        except Exception as e:
            logger.exception(
                "Error expand-then-refining paragraphs %s: %s",
                unique_indices,
                e,
            )
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
            from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType

            lines = list(getattr(page, "lines", []) or [])

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
            selected_words_for_new_line: list[object] = []
            source_line_bboxes: list[object] = []
            containing_paragraphs: list[object] = []
            line_insertion_points: list[tuple[object, int]] = []
            emptied_line_ids: set[int] = set()
            for line_index in sorted(line_to_selected_word_indices):
                selected_word_indices = line_to_selected_word_indices[line_index]
                target_line = lines[line_index]
                line_words = list(getattr(target_line, "words", []) or [])
                source_line_original_bbox = getattr(target_line, "bounding_box", None)

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
                if self._has_usable_bbox(source_line_original_bbox):
                    source_line_bboxes.append(source_line_original_bbox)

                # Find parent paragraph
                paragraphs = list(getattr(page, "paragraphs", []) or [])
                target_paragraph = None
                for paragraph in paragraphs:
                    paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                    if target_line in paragraph_lines:
                        target_paragraph = paragraph
                        break

                if target_paragraph is None:
                    logger.warning(
                        "Unable to find paragraph containing line %s", line_index
                    )
                    return False
                containing_paragraphs.append(target_paragraph)

                paragraph_items = list(getattr(target_paragraph, "items", []) or [])
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

                recompute_target_line = getattr(
                    target_line, "recompute_bounding_box", None
                )
                if unselected_words and callable(recompute_target_line):
                    try:
                        recompute_target_line()
                    except Exception as recompute_error:
                        if not self._is_geometry_normalization_error(recompute_error):
                            raise
                        logger.warning(
                            "Skipped source line bbox recompute due to malformed geometry on line %s: %s",
                            line_index,
                            recompute_error,
                        )

                if (
                    unselected_words
                    and not self._has_usable_bbox(
                        getattr(target_line, "bounding_box", None)
                    )
                    and self._has_usable_bbox(source_line_original_bbox)
                ):
                    target_line.bounding_box = source_line_original_bbox

            if not selected_words_for_new_line:
                logger.warning("No selected words found for single-line extraction")
                return False

            new_line = Block(
                items=selected_words_for_new_line,
                bounding_box=self._first_usable_bbox(source_line_bboxes),
                child_type=BlockChildType.WORDS,
                block_category=BlockCategory.LINE,
            )
            recompute_new_line = getattr(new_line, "recompute_bounding_box", None)
            if callable(recompute_new_line):
                try:
                    recompute_new_line()
                except Exception as recompute_error:
                    if not self._is_geometry_normalization_error(recompute_error):
                        raise
                    logger.warning(
                        "Skipped extracted line bbox recompute due to malformed geometry: %s",
                        recompute_error,
                    )

            if (
                not self._has_usable_bbox(getattr(new_line, "bounding_box", None))
                and source_line_bboxes
            ):
                new_line.bounding_box = self._first_usable_bbox(source_line_bboxes)

            unique_paragraphs = []
            for paragraph in containing_paragraphs:
                if paragraph not in unique_paragraphs:
                    unique_paragraphs.append(paragraph)

            if len(unique_paragraphs) == 1 and line_insertion_points:
                target_paragraph = unique_paragraphs[0]
                original_paragraph_items = list(
                    getattr(target_paragraph, "items", []) or []
                )
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
                    bounding_box=self._first_usable_bbox(
                        source_line_bboxes
                        + [
                            getattr(paragraph, "bounding_box", None)
                            for paragraph in unique_paragraphs
                        ]
                    ),
                    child_type=BlockChildType.BLOCKS,
                    block_category=BlockCategory.PARAGRAPH,
                )
                page.items = list(getattr(page, "items", []) or []) + [new_paragraph]

            self._finalize_page_structure(page)
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
            from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType

            lines = list(getattr(page, "lines", []) or [])

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
                line_words = list(getattr(target_line, "words", []) or [])

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

                paragraphs = list(getattr(page, "paragraphs", []) or [])
                target_paragraph = None
                for paragraph in paragraphs:
                    paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                    if target_line in paragraph_lines:
                        target_paragraph = paragraph
                        break

                if target_paragraph is None:
                    logger.warning(
                        "Unable to find paragraph containing line %s",
                        line_index,
                    )
                    return False

                paragraph_items = list(getattr(target_paragraph, "items", []) or [])
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

                parent = self._find_parent_block(page, target_paragraph)
                if parent is not None:
                    parent.recompute_bounding_box()

                split_any = True

            if not split_any:
                logger.warning("No lines were split into selected/unselected groups")
                return False

            self._finalize_page_structure(page)
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

    def group_selected_words_into_new_paragraph(
        self,
        page: "Page",
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Move selected words into a newly created paragraph.

        For each affected source line, selected words are moved to one new line in
        the new paragraph while unselected words remain in the original line.

        Selected words may come from multiple source paragraphs and parent
        containers.

        Args:
            page: Page containing lines/words.
            word_keys: List of (line_index, word_index) tuples for selected words.

        Returns:
            bool: True when grouping succeeds, False otherwise.
        """
        if not page:
            logger.warning("No page provided for group-selected-words")
            return False

        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning("Group-selected-words requires at least one selected word")
            return False

        try:
            from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType

            lines = list(getattr(page, "lines", []) or [])
            paragraphs = list(getattr(page, "paragraphs", []) or [])

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

            target_lines = [
                lines[line_index]
                for line_index in sorted(line_to_selected_word_indices)
            ]

            paragraph_for_line: dict[object, object] = {}
            for line in target_lines:
                containing_paragraph = None
                for paragraph in paragraphs:
                    paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                    if line in paragraph_lines:
                        containing_paragraph = paragraph
                        break
                if containing_paragraph is None:
                    logger.warning(
                        "Unable to find paragraph containing selected words %s",
                        unique_keys,
                    )
                    return False
                paragraph_for_line[line] = containing_paragraph

            affected_paragraphs: list[object] = []
            for paragraph in paragraphs:
                if any(
                    paragraph_for_line.get(line) is paragraph for line in target_lines
                ):
                    affected_paragraphs.append(paragraph)

            if not affected_paragraphs:
                logger.warning(
                    "Unable to determine affected paragraphs for selected words %s",
                    unique_keys,
                )
                return False

            selected_lines_for_new_paragraph: list[object] = []
            selected_line_bbox_fallbacks: list[object] = []
            for line_index in sorted(line_to_selected_word_indices):
                selected_word_indices = line_to_selected_word_indices[line_index]
                source_line = lines[line_index]
                line_words = list(getattr(source_line, "words", []) or [])
                source_line_original_bbox = getattr(source_line, "bounding_box", None)

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
                    logger.warning(
                        "Grouping requires at least one selected word for line %s",
                        line_index,
                    )
                    return False

                source_line.items = unselected_words
                source_line.unmatched_ground_truth_words = []
                recompute_source_line = getattr(
                    source_line, "recompute_bounding_box", None
                )
                if callable(recompute_source_line):
                    try:
                        recompute_source_line()
                    except Exception as recompute_error:
                        if not self._is_geometry_normalization_error(recompute_error):
                            raise
                        logger.warning(
                            "Skipped source line bbox recompute due to malformed geometry on line %s: %s",
                            line_index,
                            recompute_error,
                        )

                # Preserve the pre-edit line bbox when recompute cannot produce
                # a valid geometry object from sparse or malformed word bboxes.
                if (
                    unselected_words
                    and not self._has_usable_bbox(
                        getattr(source_line, "bounding_box", None)
                    )
                    and self._has_usable_bbox(source_line_original_bbox)
                ):
                    source_line.bounding_box = source_line_original_bbox

                selected_line = Block(
                    items=selected_words,
                    bounding_box=source_line_original_bbox,
                    child_type=BlockChildType.WORDS,
                    block_category=BlockCategory.LINE,
                )
                recompute_selected_line = getattr(
                    selected_line,
                    "recompute_bounding_box",
                    None,
                )
                if callable(recompute_selected_line):
                    try:
                        recompute_selected_line()
                    except Exception as recompute_error:
                        if not self._is_geometry_normalization_error(recompute_error):
                            raise
                        logger.warning(
                            "Skipped selected line bbox recompute due to malformed geometry on line %s: %s",
                            line_index,
                            recompute_error,
                        )

                if self._has_usable_bbox(getattr(selected_line, "bounding_box", None)):
                    selected_line_bbox_fallbacks.append(selected_line.bounding_box)
                elif self._has_usable_bbox(source_line_original_bbox):
                    selected_line.bounding_box = source_line_original_bbox
                    selected_line_bbox_fallbacks.append(source_line_original_bbox)
                selected_lines_for_new_paragraph.append(selected_line)

            if not selected_lines_for_new_paragraph:
                logger.warning("No selected words available to group into paragraph")
                return False

            new_paragraph = Block(
                items=selected_lines_for_new_paragraph,
                bounding_box=self._first_usable_bbox(
                    selected_line_bbox_fallbacks
                    + [
                        getattr(paragraph, "bounding_box", None)
                        for paragraph in affected_paragraphs
                    ]
                ),
                child_type=BlockChildType.BLOCKS,
                block_category=BlockCategory.PARAGRAPH,
            )

            # Always attach grouped output at page root so selections can span
            # arbitrary source paragraph containers.
            page_items = list(getattr(page, "items", []) or [])
            page.items = page_items + [new_paragraph]

            self._finalize_page_structure(page)

            # Keep a non-empty paragraph bbox for overlay rendering when page-level
            # recompute cannot infer geometry from malformed child coordinates.
            if not self._has_usable_bbox(getattr(new_paragraph, "bounding_box", None)):
                fallback_bbox = self._first_usable_bbox(
                    selected_line_bbox_fallbacks
                    + [
                        getattr(paragraph, "bounding_box", None)
                        for paragraph in affected_paragraphs
                    ]
                )
                if fallback_bbox is not None:
                    new_paragraph.bounding_box = fallback_bbox

            logger.info(
                "Grouped selected words %s into new paragraph with %d line(s)",
                unique_keys,
                len(selected_lines_for_new_paragraph),
            )
            return True
        except Exception as e:
            logger.exception(
                "Error grouping selected words %s into paragraph: %s",
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
            line_words = self._validated_line_words(page, line_index)
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
            bbox = getattr(word, "bounding_box", None)
            if bbox is None:
                logger.warning(
                    "Word bbox nudge requires an existing bbox for line=%s word=%s",
                    line_index,
                    word_index,
                )
                return False

            is_normalized = bool(getattr(bbox, "is_normalized", False))
            if is_normalized:
                page_width, page_height = self._resolve_page_dimensions(page)
                if page_width <= 0.0 or page_height <= 0.0:
                    logger.warning(
                        "Unable to resolve page dimensions for normalized bbox nudge"
                    )
                    return False
                x1 = float(getattr(bbox, "minX", 0.0) or 0.0) * page_width
                y1 = float(getattr(bbox, "minY", 0.0) or 0.0) * page_height
                x2 = float(getattr(bbox, "maxX", 0.0) or 0.0) * page_width
                y2 = float(getattr(bbox, "maxY", 0.0) or 0.0) * page_height
            else:
                x1 = float(getattr(bbox, "minX", 0.0) or 0.0)
                y1 = float(getattr(bbox, "minY", 0.0) or 0.0)
                x2 = float(getattr(bbox, "maxX", 0.0) or 0.0)
                y2 = float(getattr(bbox, "maxY", 0.0) or 0.0)

            nx1 = x1 - float(left_delta)
            ny1 = y1 - float(top_delta)
            nx2 = x2 + float(right_delta)
            ny2 = y2 + float(bottom_delta)

            page_width, page_height = self._resolve_page_dimensions(page)
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

    def _merge_adjacent_words(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        direction: str,
    ) -> bool:
        """Merge adjacent words on a line.

        Direction:
            - "left": merge selected word into immediate left word
            - "right": merge immediate right word into selected word
        """
        if not page:
            logger.warning("No page provided for word merge")
            return False

        try:
            line_words = self._validated_line_words(page, line_index)
            if line_words is None:
                return False
            if len(line_words) < 2:
                logger.warning("Word merge requires at least two words in line")
                return False

            if word_index < 0 or word_index >= len(line_words):
                logger.warning(
                    "Word merge index %s out of range for line %s (0-%s)",
                    word_index,
                    line_index,
                    len(line_words) - 1,
                )
                return False

            if direction == "left":
                if word_index == 0:
                    logger.warning("Cannot merge first word to the left")
                    return False
                keep_index = word_index - 1
                remove_index = word_index
            elif direction == "right":
                if word_index >= len(line_words) - 1:
                    logger.warning("Cannot merge last word to the right")
                    return False
                keep_index = word_index
                remove_index = word_index + 1
            else:
                logger.warning("Unsupported word merge direction: %s", direction)
                return False

            kept_word = line_words[keep_index]
            removed_word = line_words[remove_index]
            kept_word.merge(removed_word)

            if not self._remove_word_from_line(
                page=page,
                line_index=line_index,
                word_index=remove_index,
                line_words=line_words,
            ):
                return False

            updated_words = self._validated_line_words(page, line_index)
            if updated_words is None:
                return False
            for word in updated_words:
                word.ground_truth_text = ""

            self._finalize_page_structure(page)

            logger.info(
                "Merged word %d %s on line %d",
                word_index,
                direction,
                line_index,
            )
            return True

        except Exception as e:
            logger.exception(
                "Error merging word line=%s index=%s direction=%s: %s",
                line_index,
                word_index,
                direction,
                e,
            )
            return False

    def _validated_line_words(
        self, page: "Page", line_index: int
    ) -> list[object] | None:
        """Validate line index and return line words list."""
        lines = list(page.lines)
        if line_index < 0 or line_index >= len(lines):
            logger.warning(
                "Line index %s out of range (0-%s)",
                line_index,
                len(lines) - 1,
            )
            return None

        return list(lines[line_index].words)

    def _is_geometry_normalization_error(self, error: Exception) -> bool:
        """Return True for known malformed-bbox normalization failures."""
        message = str(error)
        return "NoneType" in message and "is_normalized" in message

    def _has_usable_bbox(self, bbox: object) -> bool:
        """Return True when bbox exposes finite corners required for overlay drawing."""
        if bbox is None:
            return False

        try:
            corners = (
                getattr(bbox, "minX", None),
                getattr(bbox, "minY", None),
                getattr(bbox, "maxX", None),
                getattr(bbox, "maxY", None),
            )
            return all(corner is not None for corner in corners)
        except Exception:
            return False

    def _first_usable_bbox(self, bbox_candidates: list[object]) -> object | None:
        """Return first bbox candidate that can be rendered in overlays."""
        for bbox in bbox_candidates:
            if self._has_usable_bbox(bbox):
                return bbox
        return None

    def _merge_line_blocks_fallback(
        self,
        primary_line: object,
        secondary_line: object,
    ) -> bool:
        """Fallback line merge that concatenates items when Block.merge fails on malformed bbox metadata."""
        try:
            if not hasattr(primary_line, "items"):
                logger.warning(
                    "Fallback merge unavailable: primary line has no items attribute (type=%s)",
                    type(primary_line).__name__,
                )
                return False

            merged_items = [
                *list(getattr(primary_line, "items", []) or []),
                *list(getattr(secondary_line, "items", []) or []),
            ]

            if hasattr(primary_line, "_items"):
                primary_line._items = list(merged_items)
                sort_items = getattr(primary_line, "_sort_items", None)
                if callable(sort_items):
                    sort_items()
            else:
                primary_line.items = list(merged_items)

            recompute_line = getattr(primary_line, "recompute_bounding_box", None)
            if callable(recompute_line):
                try:
                    recompute_line()
                except Exception as recompute_error:
                    if not self._is_geometry_normalization_error(recompute_error):
                        raise
                    logger.warning(
                        "Fallback merge skipped line bbox recompute due to malformed geometry: %s",
                        recompute_error,
                    )

            return True
        except Exception as fallback_error:
            logger.exception("Fallback line merge failed: %s", fallback_error)
            return False

    def _refine_block_words(self, page: object, block: object) -> bool:
        """Refine all words in a line-like block and recompute block bbox."""
        words = list(getattr(block, "words", []) or [])
        refined_any = False
        for word in words:
            refined_any = self._refine_word_bbox(page, word) or refined_any

        recompute_block = getattr(block, "recompute_bounding_box", None)
        if callable(recompute_block):
            recompute_block()

        return refined_any

    def _refine_word_bbox(self, page: object, word: object) -> bool:
        """Run available word-level bbox refinement helpers."""
        refined = False
        page_image = getattr(page, "cv2_numpy_page_image", None)

        used_bbox_refine = False
        bbox = getattr(word, "bounding_box", None)
        bbox_refine = getattr(bbox, "refine", None) if bbox is not None else None
        if callable(bbox_refine) and page_image is not None:
            try:
                refined_bbox = bbox_refine(
                    page_image,
                    padding_px=1,
                    expand_beyond_original=False,
                )
                if refined_bbox is not None:
                    setattr(word, "bounding_box", refined_bbox)
                    refined = True
                    used_bbox_refine = True
            except Exception:
                logger.debug(
                    "Bounding-box refine failed during word refine; falling back",
                    exc_info=True,
                )

        if not used_bbox_refine:
            crop_bottom = getattr(word, "crop_bottom", None)
            if callable(crop_bottom):
                try:
                    crop_bottom()
                except TypeError:
                    if page_image is not None:
                        crop_bottom(page_image)
                    else:
                        logger.debug(
                            "Skipping crop_bottom refine; page image unavailable",
                            exc_info=True,
                        )
                refined = True

            expand_to_content = getattr(word, "expand_to_content", None)
            if callable(expand_to_content):
                try:
                    expand_to_content()
                except TypeError:
                    if page_image is not None:
                        expand_to_content(page_image)
                    else:
                        logger.debug(
                            "Skipping expand_to_content refine; page image unavailable",
                            exc_info=True,
                        )
                refined = True

        recompute_word = getattr(word, "recompute_bounding_box", None)
        if not used_bbox_refine and callable(recompute_word):
            recompute_word()
            refined = True

        return refined

    def _expand_then_refine_word_bbox(self, page: object, word: object) -> bool:
        """Run expand-first then refine for a single word bbox."""
        refined = False
        page_image = getattr(page, "cv2_numpy_page_image", None)

        previous_signature = self._word_bbox_signature(word)
        seen_signatures: set[tuple[float, float, float, float, bool] | None] = {
            previous_signature
        }
        for _ in range(8):
            used_bbox_refine = False
            bbox = getattr(word, "bounding_box", None)
            bbox_refine = getattr(bbox, "refine", None) if bbox is not None else None
            if callable(bbox_refine) and page_image is not None:
                try:
                    refined_bbox = bbox_refine(
                        page_image,
                        padding_px=0,
                        expand_beyond_original=True,
                    )
                    if refined_bbox is not None:
                        setattr(word, "bounding_box", refined_bbox)
                        refined = True
                        used_bbox_refine = True
                except Exception:
                    logger.debug(
                        "Bounding-box refine (expand_beyond_original=True) failed; falling back",
                        exc_info=True,
                    )

            if not used_bbox_refine:
                expand_to_content = getattr(word, "expand_to_content", None)
                if callable(expand_to_content):
                    try:
                        expand_to_content()
                    except TypeError:
                        if page_image is not None:
                            expand_to_content(page_image)
                        else:
                            logger.debug(
                                "Skipping expand_to_content; page image unavailable",
                                exc_info=True,
                            )
                    refined = True

                crop_bottom = getattr(word, "crop_bottom", None)
                if callable(crop_bottom):
                    try:
                        crop_bottom()
                    except TypeError:
                        if page_image is not None:
                            crop_bottom(page_image)
                        else:
                            logger.debug(
                                "Skipping crop_bottom; page image unavailable",
                                exc_info=True,
                            )
                    refined = True

            recompute_word = getattr(word, "recompute_bounding_box", None)
            if not used_bbox_refine and callable(recompute_word):
                recompute_word()
                refined = True

            if used_bbox_refine:
                break

            current_signature = self._word_bbox_signature(word)
            if current_signature == previous_signature:
                break
            if current_signature in seen_signatures:
                break

            seen_signatures.add(current_signature)
            previous_signature = current_signature

        return refined

    def _word_bbox_signature(
        self,
        word: object,
    ) -> tuple[float, float, float, float, bool] | None:
        """Return a stable bbox signature for convergence checks."""
        bbox = getattr(word, "bounding_box", None)
        if bbox is None:
            return None

        min_x = float(getattr(bbox, "minX", 0.0) or 0.0)
        min_y = float(getattr(bbox, "minY", 0.0) or 0.0)
        max_x = float(getattr(bbox, "maxX", 0.0) or 0.0)
        max_y = float(getattr(bbox, "maxY", 0.0) or 0.0)
        is_normalized = bool(getattr(bbox, "is_normalized", False))
        return (
            round(min_x, 6),
            round(min_y, 6),
            round(max_x, 6),
            round(max_y, 6),
            is_normalized,
        )

    def _resolve_page_dimensions(self, page: object) -> tuple[float, float]:
        """Return page dimensions in pixels when available."""
        width = float(getattr(page, "width", 0.0) or 0.0)
        height = float(getattr(page, "height", 0.0) or 0.0)
        if width > 0.0 and height > 0.0:
            return width, height

        base_image = getattr(page, "cv2_numpy_page_image", None)
        if getattr(base_image, "shape", None) is not None:
            image_height, image_width = base_image.shape[:2]
            return float(image_width), float(image_height)

        return 0.0, 0.0

    def _remove_word_from_line(
        self,
        page: "Page",
        line_index: int,
        word_index: int,
        line_words: list[object] | None = None,
    ) -> bool:
        """Remove a word from a line using available line APIs."""
        lines = list(page.lines)
        if line_index < 0 or line_index >= len(lines):
            return False

        line = lines[line_index]
        words = list(line_words) if line_words is not None else list(line.words)
        if word_index < 0 or word_index >= len(words):
            return False

        remove_item = getattr(line, "remove_item", None)
        if callable(remove_item):
            remove_item(words[word_index])
            return True

        kept_words = [word for idx, word in enumerate(words) if idx != word_index]
        if hasattr(line, "items"):
            setattr(line, "items", kept_words)
            return True

        logger.warning(
            "Line type %s does not support word removal",
            type(line).__name__,
        )
        return False

    def _move_word_between_lines(
        self,
        source_line: object,
        target_line: object,
        word: object,
    ) -> bool:
        """Move a word object from source line to target line."""
        if source_line is target_line:
            return True

        if not self._remove_word_object_from_line(source_line, word):
            return False

        if self._add_word_to_line(target_line, word):
            return True

        self._add_word_to_line(source_line, word)
        return False

    def _remove_word_object_from_line(self, line: object, word: object) -> bool:
        """Remove a specific word object from a line."""
        remove_item = getattr(line, "remove_item", None)
        if callable(remove_item):
            remove_item(word)
            return True

        items = list(getattr(line, "items", []) or [])
        updated_items = [item for item in items if item is not word]
        if len(updated_items) == len(items):
            return False

        if hasattr(line, "_items"):
            line._items = updated_items
            sort_items = getattr(line, "_sort_items", None)
            if callable(sort_items):
                sort_items()
            return True

        if hasattr(line, "items"):
            line.items = updated_items
            return True

        return False

    def _add_word_to_line(self, line: object, word: object) -> bool:
        """Add a word object to a line and preserve ordering when possible."""
        add_item = getattr(line, "add_item", None)
        if callable(add_item):
            add_item(word)
            return True

        items = list(getattr(line, "items", []) or [])
        items.append(word)

        if hasattr(line, "_items"):
            line._items = items
            sort_items = getattr(line, "_sort_items", None)
            if callable(sort_items):
                sort_items()
            return True

        if hasattr(line, "items"):
            line.items = items
            return True

        return False

    def _bbox_vertical_midpoint(self, bbox: object | None) -> float | None:
        """Return vertical midpoint for a bbox-like object, when available."""
        if bbox is None:
            return None

        min_y = getattr(bbox, "minY", None)
        max_y = getattr(bbox, "maxY", None)
        if min_y is not None and max_y is not None:
            return (float(min_y) + float(max_y)) / 2.0

        top_left = getattr(bbox, "top_left", None)
        bottom_right = getattr(bbox, "bottom_right", None)
        if top_left is not None and bottom_right is not None:
            top_y = getattr(top_left, "y", None)
            bottom_y = getattr(bottom_right, "y", None)
            if top_y is not None and bottom_y is not None:
                return (float(top_y) + float(bottom_y)) / 2.0

        min_y = getattr(bbox, "y", None)
        height = getattr(bbox, "height", None)
        if min_y is not None and height is not None:
            return float(min_y) + (float(height) / 2.0)

        return None

    def _line_vertical_midpoint(self, line: object) -> float | None:
        """Return vertical midpoint for a line bounding box."""
        return self._bbox_vertical_midpoint(getattr(line, "bounding_box", None))

    def _word_vertical_midpoint(self, word: object) -> float | None:
        """Return vertical midpoint for a word bounding box."""
        return self._bbox_vertical_midpoint(getattr(word, "bounding_box", None))

    def _closest_line_by_midpoint(
        self,
        lines: list[object],
        line_midpoints: dict[int, float | None],
        midpoint_y: float | None,
        fallback_line: object,
    ) -> object:
        """Choose the line whose vertical midpoint is closest to midpoint_y."""
        if midpoint_y is None:
            return fallback_line

        closest_line = fallback_line
        closest_distance = float("inf")
        for line in lines:
            line_midpoint = line_midpoints.get(id(line))
            if line_midpoint is None:
                continue

            distance = abs(line_midpoint - midpoint_y)
            if distance < closest_distance:
                closest_distance = distance
                closest_line = line

        return closest_line

    def _finalize_page_structure(self, page: object) -> None:
        """Run optional page cleanup/recompute hooks after structural edits."""
        self._remove_empty_items_safely(page)

        try:
            self._recompute_nested_bounding_boxes(page)
        except Exception as recompute_error:
            if not self._is_geometry_normalization_error(recompute_error):
                raise
            logger.warning(
                "Skipped nested bbox recompute due to malformed geometry: %s",
                recompute_error,
            )
            self._recompute_paragraph_bboxes_with_block_api(page)

        if hasattr(page, "recompute_bounding_box") and callable(
            getattr(page, "recompute_bounding_box")
        ):
            try:
                page.recompute_bounding_box()
            except Exception as recompute_error:
                if not self._is_geometry_normalization_error(recompute_error):
                    raise
                logger.warning(
                    "Skipped page bbox recompute due to malformed geometry: %s",
                    recompute_error,
                )

    def _recompute_nested_bounding_boxes(self, container: object) -> None:
        """Recursively recompute bounding boxes bottom-up for nested blocks."""
        child_items = list(getattr(container, "items", []) or [])
        for child in child_items:
            if hasattr(child, "items"):
                self._recompute_nested_bounding_boxes(child)

        recompute = getattr(container, "recompute_bounding_box", None)
        if child_items and callable(recompute):
            recompute()

    def _find_parent_block(self, container: object, target: object) -> object | None:
        """Find parent block/page that directly contains target in its child items."""
        child_items = list(getattr(container, "items", []) or [])
        if target in child_items:
            return container

        for child in child_items:
            if hasattr(child, "items"):
                parent = self._find_parent_block(child, target)
                if parent is not None:
                    return parent
        return None

    def _remove_nested_block(self, container: object, target: object) -> bool:
        """Remove target from nested page/block hierarchy if present."""
        if target in (getattr(container, "items", []) or []):
            remove_item = getattr(container, "remove_item", None)
            if callable(remove_item):
                try:
                    remove_item(target)
                    return True
                except Exception as removal_error:
                    if not self._is_geometry_normalization_error(removal_error):
                        raise
                    logger.warning(
                        "remove_item fallback for malformed geometry on %s: %s",
                        type(container).__name__,
                        removal_error,
                    )
                    return self._remove_item_without_recompute(container, target)
            return False

        for child in list(getattr(container, "items", []) or []):
            if hasattr(child, "items") and self._remove_nested_block(child, target):
                return True
        return False

    def _remove_item_without_recompute(self, container: object, target: object) -> bool:
        """Best-effort item removal when remove_item triggers malformed bbox recompute errors."""
        items = list(getattr(container, "items", []) or [])
        if target not in items:
            return False

        updated_items = [item for item in items if item is not target]
        if hasattr(container, "_items"):
            container._items = updated_items
            return True
        if hasattr(container, "items"):
            container.items = updated_items
            return True
        return False

    def _remove_empty_items_safely(self, container: object) -> None:
        """Best-effort empty-item pruning that tolerates malformed geometry recompute errors."""
        remove_empty_items = getattr(container, "remove_empty_items", None)
        if not callable(remove_empty_items):
            self._prune_empty_blocks_fallback(container)
            return

        try:
            remove_empty_items()
        except Exception as error:
            if not self._is_geometry_normalization_error(error):
                raise
            logger.warning(
                "Skipped remove_empty_items due to malformed geometry: %s",
                error,
            )

        # Always run deterministic fallback pruning. This guarantees empty lines
        # created by word deletion/movement are removed even when upstream
        # remove_empty_items does not catch them.
        self._prune_empty_blocks_fallback(container)

    def _prune_empty_blocks_fallback(self, container: object) -> None:
        """Recursively remove empty line/paragraph blocks from nested items lists."""
        child_items = list(getattr(container, "items", []) or [])
        if not child_items:
            return

        kept_items: list[object] = []
        changed = False
        for child in child_items:
            if hasattr(child, "items"):
                self._prune_empty_blocks_fallback(child)

            if self._is_empty_structural_block(child):
                changed = True
                continue

            kept_items.append(child)

        if not changed:
            return

        if hasattr(container, "_items"):
            container._items = kept_items
            return
        if hasattr(container, "items"):
            container.items = kept_items

    def _is_empty_structural_block(self, block: object) -> bool:
        """Return True when a block is structurally empty and should be removed."""
        if hasattr(block, "words"):
            words = list(getattr(block, "words", []) or [])
            if len(words) == 0:
                return True

        if hasattr(block, "lines"):
            lines = list(getattr(block, "lines", []) or [])
            if len(lines) == 0:
                return True

        if hasattr(block, "items"):
            items = list(getattr(block, "items", []) or [])
            if len(items) == 0:
                return True

        return False

    def _replace_block_with_split_paragraphs(
        self,
        parent: object,
        paragraph: object,
        paragraph_lines: list[object],
        block_type: type,
        block_category: object,
    ) -> bool:
        """Replace a paragraph with one paragraph per line in the given parent."""
        remove_item = getattr(parent, "remove_item", None)
        add_item = getattr(parent, "add_item", None)
        if not callable(remove_item) or not callable(add_item):
            return False

        remove_item(paragraph)
        for line in paragraph_lines:
            new_paragraph = block_type(
                items=[line],
                block_category=block_category.PARAGRAPH,
            )
            add_item(new_paragraph)
        return True

    def _recompute_paragraph_bboxes_with_block_api(self, page: object) -> None:
        """Best-effort paragraph bbox recompute using paragraph Block APIs only."""
        if not isinstance(page, _PageWithParagraphs):
            return

        try:
            paragraphs = list(page.paragraphs or [])
        except AttributeError:
            return
        except Exception:
            logger.debug(
                "Paragraph collection unavailable during bbox fallback", exc_info=True
            )
            return

        for paragraph in paragraphs:
            if not isinstance(paragraph, _ParagraphLike):
                continue

            try:
                paragraph.recompute_bounding_box()
            except Exception:
                logger.debug(
                    "Paragraph bbox recompute fallback skipped for %s",
                    type(paragraph).__name__,
                    exc_info=True,
                )
