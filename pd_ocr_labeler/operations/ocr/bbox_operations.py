"""Bbox refinement and expansion operations for selected words, lines, and paragraphs.

This module contains the ``BboxOperations`` class, which handles the
iterative "apply to selected items" bbox operations that were previously
implemented as methods on ``Page`` in pd-book-tools.

These operations take a ``Page`` object and selection keys/indices, then
iterate over the selected items applying Word/Block-level bbox operations.
"""

from __future__ import annotations

import logging
from typing import Callable

from pd_book_tools.ocr.block import Block
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

logger = logging.getLogger(__name__)


class BboxOperations:
    """Bbox refinement and expansion operations for selected page items."""

    # ------------------------------------------------------------------
    # Internal recompute helper
    # ------------------------------------------------------------------

    @staticmethod
    def _recompute_lines_and_ancestors(
        page: Page, affected_line_indices: set[int]
    ) -> None:
        """Recompute bboxes for affected lines, their parent items, and the page.

        Replaces the full ``page.finalize_page_structure()`` call with a
        targeted recompute scoped to the lines that actually changed.
        Works with both flat page structures (page → lines → words) and
        hierarchical structures (page → paragraphs → lines → words).
        """
        if not affected_line_indices:
            return

        lines = list(page.lines)

        # Recompute each affected line's bbox (unions its word bboxes)
        affected_line_objects: set[int] = set()
        for li in affected_line_indices:
            if 0 <= li < len(lines):
                affected_line_objects.add(id(lines[li]))
                try:
                    lines[li].recompute_bounding_box()
                except Exception:
                    logger.warning("Failed to recompute bbox for line %s", li)

        # Recompute each top-level page item (paragraph or line) that contains
        # at least one affected line.  ``item.lines`` safely returns [self] for
        # WORDS blocks and traverses into children for BLOCKS blocks, so this
        # works regardless of the page's nesting depth.
        seen_item_ids: set[int] = set()
        for item in page.items:
            item_id = id(item)
            if item_id in seen_item_ids:
                continue
            try:
                item_lines = item.lines
            except Exception:
                continue
            if any(id(line) in affected_line_objects for line in item_lines):
                seen_item_ids.add(item_id)
                try:
                    item.recompute_bounding_box()
                except Exception:
                    logger.warning("Failed to recompute parent item bbox")

        # Recompute the page bbox (unions top-level item bboxes)
        try:
            page.recompute_bounding_box()
        except Exception:
            logger.warning("Failed to recompute page bbox")

    # ------------------------------------------------------------------
    # Internal iteration helpers
    # ------------------------------------------------------------------

    def _apply_to_word_keys(
        self,
        page: Page,
        word_keys: list[tuple[int, int]],
        operation: Callable[[Word], bool],
        label: str,
    ) -> bool:
        """Validate word keys and apply *operation* to each selected word."""
        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning("%s requires selecting at least one word", label)
            return False
        try:
            changed = False
            affected_line_indices: set[int] = set()
            for line_index, word_index in unique_keys:
                line_words = page.validated_line_words(line_index)
                if line_words is None:
                    return False
                if word_index < 0 or word_index >= len(line_words):
                    logger.warning(
                        "%s word index %s out of range for line %s (0-%s)",
                        label,
                        word_index,
                        line_index,
                        len(line_words) - 1,
                    )
                    return False
                if operation(line_words[word_index]):
                    changed = True
                    affected_line_indices.add(line_index)
            if not changed:
                logger.warning("Selected words could not be processed (%s)", label)
                return False
            self._recompute_lines_and_ancestors(page, affected_line_indices)
            logger.info("%s %d selected words", label, len(unique_keys))
            return True
        except Exception as e:
            logger.exception("Error in %s for words %s: %s", label, word_keys, e)
            return False

    def _apply_to_line_indices(
        self,
        page: Page,
        line_indices: list[int],
        operation: Callable[[Block], bool],
        label: str,
    ) -> bool:
        """Validate line indices and apply *operation* to each selected line."""
        unique_indices = sorted(set(line_indices or []))
        if not unique_indices:
            logger.warning("%s requires selecting at least one line", label)
            return False
        try:
            lines = list(page.lines)
            changed = False
            changed_line_indices: set[int] = set()
            for line_index in unique_indices:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "%s line index %s out of range (0-%s)",
                        label,
                        line_index,
                        len(lines) - 1,
                    )
                    return False
                if operation(lines[line_index]):
                    changed = True
                    changed_line_indices.add(line_index)
            if not changed:
                logger.warning("Selected lines could not be processed (%s)", label)
                return False
            self._recompute_lines_and_ancestors(page, changed_line_indices)
            logger.info("%s %d selected lines", label, len(unique_indices))
            return True
        except Exception as e:
            logger.exception("Error in %s for lines %s: %s", label, line_indices, e)
            return False

    def _apply_to_paragraph_indices(
        self,
        page: Page,
        paragraph_indices: list[int],
        operation: Callable[[Block], bool],
        label: str,
    ) -> bool:
        """Validate paragraph indices and apply *operation* to each selected paragraph."""
        unique_indices = sorted(set(paragraph_indices or []))
        if not unique_indices:
            logger.warning("%s requires selecting at least one paragraph", label)
            return False
        try:
            paragraphs = list(page.paragraphs)
            if not paragraphs:
                logger.warning("Page has no paragraphs (%s)", label)
                return False
            changed = False
            changed_paragraph_indices: set[int] = set()
            for paragraph_index in unique_indices:
                if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                    logger.warning(
                        "%s paragraph index %s out of range (0-%s)",
                        label,
                        paragraph_index,
                        len(paragraphs) - 1,
                    )
                    return False
                if operation(paragraphs[paragraph_index]):
                    changed = True
                    changed_paragraph_indices.add(paragraph_index)
            if not changed:
                logger.warning("Selected paragraphs could not be processed (%s)", label)
                return False
            # Targeted recompute: lines within changed paragraphs, then
            # paragraphs themselves, then the page.  The _op functions for
            # expand/refine paragraphs already call line and paragraph
            # recompute; doing it again here is idempotent and ensures
            # correctness for all paragraph operation variants.
            for paragraph_index in changed_paragraph_indices:
                para = paragraphs[paragraph_index]
                for line in getattr(para, "lines", None) or []:
                    try:
                        line.recompute_bounding_box()
                    except Exception:
                        logger.warning(
                            "Failed to recompute line bbox in paragraph %s",
                            paragraph_index,
                        )
                try:
                    para.recompute_bounding_box()
                except Exception:
                    logger.warning(
                        "Failed to recompute paragraph %s bbox", paragraph_index
                    )
            try:
                page.recompute_bounding_box()
            except Exception:
                logger.warning("Failed to recompute page bbox")
            logger.info("%s %d selected paragraphs", label, len(unique_indices))
            return True
        except Exception as e:
            logger.exception(
                "Error in %s for paragraphs %s: %s", label, paragraph_indices, e
            )
            return False

    # ------------------------------------------------------------------
    # Word-level bbox operations
    # ------------------------------------------------------------------

    def refine_words(self, page: Page, word_keys: list[tuple[int, int]]) -> bool:
        """Refine selected word bounding boxes."""
        return self._apply_to_word_keys(
            page,
            word_keys,
            lambda w: w.refine_bbox(page.cv2_numpy_page_image),
            "Refined",
        )

    def expand_then_refine_words(
        self, page: Page, word_keys: list[tuple[int, int]]
    ) -> bool:
        """Expand then refine selected word bounding boxes."""
        return self._apply_to_word_keys(
            page,
            word_keys,
            lambda w: w.expand_then_refine_bbox(page.cv2_numpy_page_image),
            "Expand-then-refined",
        )

    def expand_word_bboxes(
        self,
        page: Page,
        word_keys: list[tuple[int, int]],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand selected word bounding boxes by uniform pixel padding."""
        page_width, page_height = page.resolved_dimensions
        return self._apply_to_word_keys(
            page,
            word_keys,
            lambda w: w.expand_bbox(padding_px, page_width, page_height),
            "Expanded bboxes for",
        )

    # ------------------------------------------------------------------
    # Line-level bbox operations
    # ------------------------------------------------------------------

    def refine_lines(self, page: Page, line_indices: list[int]) -> bool:
        """Refine all word bboxes in selected lines."""
        return self._apply_to_line_indices(
            page,
            line_indices,
            lambda line: line.refine_word_bboxes(page.cv2_numpy_page_image),
            "Refined",
        )

    def expand_then_refine_lines(self, page: Page, line_indices: list[int]) -> bool:
        """Expand then refine all word bboxes in selected lines."""

        def _op(line: Block) -> bool:
            changed = False
            for word in line.words:
                changed = (
                    word.expand_then_refine_bbox(page.cv2_numpy_page_image) or changed
                )
            line.recompute_bounding_box()
            return changed

        return self._apply_to_line_indices(
            page, line_indices, _op, "Expand-then-refined"
        )

    def expand_line_bboxes(
        self,
        page: Page,
        line_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand all word bboxes in selected lines by uniform pixel padding."""
        page_width, page_height = page.resolved_dimensions

        def _op(line: Block) -> bool:
            changed = False
            for word in line.words:
                changed = (
                    word.expand_bbox(padding_px, page_width, page_height) or changed
                )
            line.recompute_bounding_box()
            return changed

        return self._apply_to_line_indices(
            page, line_indices, _op, "Expanded bboxes in"
        )

    # ------------------------------------------------------------------
    # Paragraph-level bbox operations
    # ------------------------------------------------------------------

    def refine_paragraphs(self, page: Page, paragraph_indices: list[int]) -> bool:
        """Refine all word bboxes in selected paragraphs."""

        def _op(paragraph: Block) -> bool:
            changed = False
            for line in paragraph.lines:
                changed = line.refine_word_bboxes(page.cv2_numpy_page_image) or changed
            paragraph.recompute_bounding_box()
            return changed

        return self._apply_to_paragraph_indices(page, paragraph_indices, _op, "Refined")

    def expand_then_refine_paragraphs(
        self, page: Page, paragraph_indices: list[int]
    ) -> bool:
        """Expand then refine all word bboxes in selected paragraphs."""

        def _op(paragraph: Block) -> bool:
            changed = False
            for line in paragraph.lines:
                for word in line.words:
                    changed = (
                        word.expand_then_refine_bbox(page.cv2_numpy_page_image)
                        or changed
                    )
                line.recompute_bounding_box()
            paragraph.recompute_bounding_box()
            return changed

        return self._apply_to_paragraph_indices(
            page, paragraph_indices, _op, "Expand-then-refined"
        )

    def expand_paragraph_bboxes(
        self,
        page: Page,
        paragraph_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand all word bboxes in selected paragraphs by uniform pixel padding."""
        page_width, page_height = page.resolved_dimensions

        def _op(paragraph: Block) -> bool:
            changed = False
            for line in paragraph.lines:
                for word in line.words:
                    changed = (
                        word.expand_bbox(padding_px, page_width, page_height) or changed
                    )
                line.recompute_bounding_box()
            paragraph.recompute_bounding_box()
            return changed

        return self._apply_to_paragraph_indices(
            page, paragraph_indices, _op, "Expanded bboxes in"
        )
