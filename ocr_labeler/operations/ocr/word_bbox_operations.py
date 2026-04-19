"""Word/line/paragraph bounding box refinement and expansion operations.

This module provides refine, expand, and expand-then-refine operations
for word, line, and paragraph bounding boxes.  It is designed as a mixin
used by ``LineOperations``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


class WordBboxOperationsMixin:
    """Bounding box refinement and expansion operations.

    Provides refine, expand, and expand-then-refine for words, lines,
    and paragraphs.  Requires ``PageStructureOperations`` helpers via MRO.
    """

    # ------------------------------------------------------------------
    # Public word-level bbox operations
    # ------------------------------------------------------------------

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

    def expand_word_bboxes(
        self,
        page: "Page",
        word_keys: list[tuple[int, int]],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand selected word bounding boxes by a uniform pixel padding.

        Unlike expand-then-refine, this does not run content-aware refine
        afterward — the bbox is simply grown by *padding_px* on every edge,
        clamped to page bounds.

        Args:
            page: Page containing lines/words.
            word_keys: List of (line_index, word_index) tuples.
            padding_px: Number of pixels to add on each edge.

        Returns:
            bool: True if any word bboxes were expanded, False otherwise.
        """
        if not page:
            logger.warning("No page provided for expand-bbox")
            return False

        unique_keys = sorted(set(word_keys or []))
        if not unique_keys:
            logger.warning("Expand-bbox requires selecting at least one word")
            return False

        page_width, page_height = self._resolve_page_dimensions(page)

        try:
            expanded_any = False
            for line_index, word_index in unique_keys:
                line_words = self._validated_line_words(page, line_index)
                if line_words is None:
                    return False
                if word_index < 0 or word_index >= len(line_words):
                    logger.warning(
                        "Expand-bbox word index %s out of range for line %s (0-%s)",
                        word_index,
                        line_index,
                        len(line_words) - 1,
                    )
                    return False

                word = line_words[word_index]
                expanded_any = (
                    self._expand_single_word_bbox(
                        word, padding_px, page_width, page_height
                    )
                    or expanded_any
                )

            if not expanded_any:
                logger.warning("Selected words could not be expanded")
                return False

            self._finalize_page_structure(page)
            logger.info("Expanded bboxes for %d selected words", len(unique_keys))
            return True
        except Exception as e:
            logger.exception("Error expanding word bboxes %s: %s", unique_keys, e)
            return False

    # ------------------------------------------------------------------
    # Public line-level bbox operations
    # ------------------------------------------------------------------

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

    def expand_line_bboxes(
        self,
        page: "Page",
        line_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand all word bboxes in selected lines by uniform pixel padding.

        Args:
            page: Page containing lines.
            line_indices: Zero-based selected line indices.
            padding_px: Pixels to add on each edge.

        Returns:
            bool: True if any words were expanded, False otherwise.
        """
        if not page:
            logger.warning("No page provided for expand-line-bboxes")
            return False

        unique_indices = sorted(set(line_indices or []))
        if not unique_indices:
            logger.warning("Expand-line-bboxes requires selecting at least one line")
            return False

        page_width, page_height = self._resolve_page_dimensions(page)

        try:
            lines = list(page.lines)
            expanded_any = False
            for line_index in unique_indices:
                if line_index < 0 or line_index >= len(lines):
                    logger.warning(
                        "Expand-line-bboxes line index %s out of range (0-%s)",
                        line_index,
                        len(lines) - 1,
                    )
                    return False
                line = lines[line_index]
                line_words = list(getattr(line, "words", []) or [])
                for word in line_words:
                    expanded_any = (
                        self._expand_single_word_bbox(
                            word, padding_px, page_width, page_height
                        )
                        or expanded_any
                    )
                recompute_line = getattr(line, "recompute_bounding_box", None)
                if callable(recompute_line):
                    recompute_line()

            if not expanded_any:
                logger.warning("Selected lines could not be expanded")
                return False

            self._finalize_page_structure(page)
            logger.info("Expanded bboxes in %d selected lines", len(unique_indices))
            return True
        except Exception as e:
            logger.exception("Error expanding line bboxes %s: %s", unique_indices, e)
            return False

    def expand_paragraph_bboxes(
        self,
        page: "Page",
        paragraph_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand all word bboxes in selected paragraphs by uniform pixel padding.

        Args:
            page: Page containing paragraphs.
            paragraph_indices: Zero-based selected paragraph indices.
            padding_px: Pixels to add on each edge.

        Returns:
            bool: True if any words were expanded, False otherwise.
        """
        if not page:
            logger.warning("No page provided for expand-paragraph-bboxes")
            return False

        unique_indices = sorted(set(paragraph_indices or []))
        if not unique_indices:
            logger.warning(
                "Expand-paragraph-bboxes requires selecting at least one paragraph"
            )
            return False

        page_width, page_height = self._resolve_page_dimensions(page)

        try:
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            if not paragraphs:
                logger.warning("Page has no paragraphs to expand bboxes")
                return False

            expanded_any = False
            for paragraph_index in unique_indices:
                if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                    logger.warning(
                        "Expand-paragraph-bboxes index %s out of range (0-%s)",
                        paragraph_index,
                        len(paragraphs) - 1,
                    )
                    return False

                paragraph = paragraphs[paragraph_index]
                paragraph_lines = list(getattr(paragraph, "lines", []) or [])
                for line in paragraph_lines:
                    line_words = list(getattr(line, "words", []) or [])
                    for word in line_words:
                        expanded_any = (
                            self._expand_single_word_bbox(
                                word, padding_px, page_width, page_height
                            )
                            or expanded_any
                        )
                    recompute_line = getattr(line, "recompute_bounding_box", None)
                    if callable(recompute_line):
                        recompute_line()
                recompute_paragraph = getattr(paragraph, "recompute_bounding_box", None)
                if callable(recompute_paragraph):
                    recompute_paragraph()

            if not expanded_any:
                logger.warning("Selected paragraphs could not be expanded")
                return False

            self._finalize_page_structure(page)
            logger.info(
                "Expanded bboxes in %d selected paragraphs", len(unique_indices)
            )
            return True
        except Exception as e:
            logger.exception(
                "Error expanding paragraph bboxes %s: %s",
                unique_indices,
                e,
            )
            return False

    # ------------------------------------------------------------------
    # Private bbox helpers
    # ------------------------------------------------------------------

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

    def _expand_single_word_bbox(
        self,
        word: object,
        padding_px: float,
        page_width: float,
        page_height: float,
    ) -> bool:
        """Expand a single word's bbox by uniform pixel padding.

        Returns True if the bbox was successfully expanded.
        """
        bbox = getattr(word, "bounding_box", None)
        if bbox is None:
            return False

        from pd_book_tools.geometry.bounding_box import BoundingBox
        from pd_book_tools.geometry.point import Point

        is_normalized = bool(getattr(bbox, "is_normalized", False))
        if is_normalized:
            if page_width <= 0.0 or page_height <= 0.0:
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

        nx1 = max(0.0, x1 - padding_px)
        ny1 = max(0.0, y1 - padding_px)
        nx2 = x2 + padding_px
        ny2 = y2 + padding_px
        if page_width > 0.0:
            nx2 = min(nx2, page_width)
        if page_height > 0.0:
            ny2 = min(ny2, page_height)

        if nx2 <= nx1 or ny2 <= ny1:
            return False

        if is_normalized:
            new_bbox = BoundingBox(
                Point(nx1 / page_width, ny1 / page_height),
                Point(nx2 / page_width, ny2 / page_height),
                is_normalized=True,
            )
        else:
            new_bbox = BoundingBox(
                Point(nx1, ny1),
                Point(nx2, ny2),
                is_normalized=False,
            )

        word.bounding_box = new_bbox
        return True

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
