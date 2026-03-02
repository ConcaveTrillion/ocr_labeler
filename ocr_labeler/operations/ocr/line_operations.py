"""Line operations for OCR labeling tasks.

This module contains operations that can be performed on lines within pages,
such as copying ground truth to OCR text, word-level editing, and line-level
transformations. These operations are separated from state management to
maintain clear architectural boundaries.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


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
            lines = getattr(page, "lines", [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = getattr(line, "words", [])
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                gt_text = getattr(word, "ground_truth_text", "")
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
            lines = getattr(page, "lines", [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = getattr(line, "words", [])
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                ocr_text = getattr(word, "text", "")
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
            lines = getattr(page, "lines", [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = getattr(line, "words", [])
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                if hasattr(word, "ground_truth_text") and getattr(
                    word, "ground_truth_text", ""
                ):
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
            lines = getattr(page, "lines", [])
            if line_index < 0 or line_index >= len(lines):
                return {
                    "valid": False,
                    "error": f"Line index {line_index} out of range (0-{len(lines) - 1})",
                }

            line = lines[line_index]
            words = getattr(line, "words", [])
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
                ocr_text = getattr(word, "text", "")
                gt_text = getattr(word, "ground_truth_text", "")

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

            lines = list(getattr(page, "lines", []))
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
                primary_line.merge(lines[index])

            if not hasattr(page, "remove_line_if_exists") or not callable(
                getattr(page, "remove_line_if_exists")
            ):
                logger.warning(
                    "Page does not support remove_line_if_exists() (page_type=%s)",
                    type(page).__name__,
                )
                return False

            for index in reversed(unique_indices[1:]):
                page.remove_line_if_exists(lines[index])

            lines_after = len(list(getattr(page, "lines", [])))
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
