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
                primary_line.merge(lines[index])

            remove_line_if_exists = page.remove_line_if_exists
            if not callable(remove_line_if_exists):
                logger.warning(
                    "Page does not support remove_line_if_exists() (page_type=%s)",
                    type(page).__name__,
                )
                return False

            for index in reversed(unique_indices[1:]):
                remove_line_if_exists(lines[index])

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

    def _finalize_page_structure(self, page: object) -> None:
        """Run optional page cleanup/recompute hooks after structural edits."""
        if hasattr(page, "remove_empty_items") and callable(
            getattr(page, "remove_empty_items")
        ):
            page.remove_empty_items()
        if hasattr(page, "recompute_bounding_box") and callable(
            getattr(page, "recompute_bounding_box")
        ):
            page.recompute_bounding_box()

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
                remove_item(target)
                return True
            return False

        for child in list(getattr(container, "items", []) or []):
            if hasattr(child, "items") and self._remove_nested_block(child, target):
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
