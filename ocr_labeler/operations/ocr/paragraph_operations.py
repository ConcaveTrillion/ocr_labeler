"""Paragraph-level operations for OCR labeling tasks.

This module provides paragraph merge, delete, split, and word-grouping
operations.  It is designed as a mixin used by ``LineOperations``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


class ParagraphOperationsMixin:
    """Paragraph-level structural editing operations.

    Provides merge, delete, split, and word-to-paragraph grouping.
    Requires ``PageStructureOperations`` helpers via MRO.
    """

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
