"""Page-wide structural helpers for OCR operations.

Shared private helpers used by line, paragraph, and bbox operations:
bounding box geometry, page finalization, block tree manipulation,
and word-level list management.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .image_utils import is_geometry_normalization_error

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


class PageStructureOperations:
    """Base class providing shared structural helpers for page editing operations.

    Provides:
    - Bounding box geometry utilities (midpoints, ranges, closest-line logic)
    - Page finalization (empty block pruning, nested bbox recompute)
    - Block tree manipulation (find parent, remove nested, replace with splits)
    - Word-level list management (add/remove/move words between lines)
    - Line validation and consistency checks
    """

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def validate_line_consistency(
        self, page: "Page", line_index: int
    ) -> dict[str, Any]:
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
            logger.exception("Error validating line %s", line_index)
            return {"valid": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Word-level list helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Bounding box geometry helpers
    # ------------------------------------------------------------------

    def _detect_page_normalization(self, page: object) -> bool:
        """Return True if existing word bboxes on the page are normalized."""
        for line in list(getattr(page, "lines", []) or []):
            words = list(getattr(line, "items", []) or [])
            for word in words:
                bbox = getattr(word, "bounding_box", None)
                if bbox is not None:
                    return bool(getattr(bbox, "is_normalized", False))
        return False

    def _is_geometry_normalization_error(self, error: Exception) -> bool:
        """Return True for known malformed-bbox normalization failures."""
        return is_geometry_normalization_error(error)

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

    def _bbox_horizontal_midpoint(self, bbox: object | None) -> float | None:
        """Return horizontal midpoint for a bbox-like object, when available."""
        if bbox is None:
            return None

        min_x = getattr(bbox, "minX", None)
        max_x = getattr(bbox, "maxX", None)
        if min_x is not None and max_x is not None:
            return (float(min_x) + float(max_x)) / 2.0

        top_left = getattr(bbox, "top_left", None)
        bottom_right = getattr(bbox, "bottom_right", None)
        if top_left is not None and bottom_right is not None:
            left_x = getattr(top_left, "x", None)
            right_x = getattr(bottom_right, "x", None)
            if left_x is not None and right_x is not None:
                return (float(left_x) + float(right_x)) / 2.0

        min_x = getattr(bbox, "x", None)
        width = getattr(bbox, "width", None)
        if min_x is not None and width is not None:
            return float(min_x) + (float(width) / 2.0)

        return None

    def _line_horizontal_midpoint(self, line: object) -> float | None:
        """Return horizontal midpoint for a line bounding box."""
        return self._bbox_horizontal_midpoint(getattr(line, "bounding_box", None))

    def _bbox_y_range(self, bbox: object | None) -> tuple[float, float] | None:
        """Return (min_y, max_y) for a bbox-like object, or None if unavailable."""
        if bbox is None:
            return None

        min_y = getattr(bbox, "minY", None)
        max_y = getattr(bbox, "maxY", None)
        if min_y is not None and max_y is not None:
            return float(min_y), float(max_y)

        top_left = getattr(bbox, "top_left", None)
        bottom_right = getattr(bbox, "bottom_right", None)
        if top_left is not None and bottom_right is not None:
            top_y = getattr(top_left, "y", None)
            bottom_y = getattr(bottom_right, "y", None)
            if top_y is not None and bottom_y is not None:
                return float(min(top_y, bottom_y)), float(max(top_y, bottom_y))

        min_y = getattr(bbox, "y", None)
        height = getattr(bbox, "height", None)
        if min_y is not None and height is not None:
            return float(min_y), float(min_y) + float(height)

        return None

    def _line_y_range(self, line: object) -> tuple[float, float] | None:
        """Return (min_y, max_y) for a line bounding box."""
        return self._bbox_y_range(getattr(line, "bounding_box", None))

    def _closest_line_by_y_range_then_x(
        self,
        lines: list[object],
        center_x: float,
        center_y: float,
        fallback_line: object,
    ) -> object:
        """Choose the best line for a point at (center_x, center_y).

        Strategy:
        1. Collect all lines whose Y range contains center_y (fuzzy vertical match).
        2. If any such lines exist, pick the one with the smallest horizontal
           distance from its center X to center_x — this correctly breaks ties
           between parallel columns or side-notes at the same Y.
        3. If no line's Y range contains center_y, fall back to the line whose
           vertical midpoint is closest (pure vertical distance).
        """
        # Step 1: Y-range candidates.
        y_candidates: list[object] = []
        for line in lines:
            y_range = self._line_y_range(line)
            if y_range is not None and y_range[0] <= center_y <= y_range[1]:
                y_candidates.append(line)

        if y_candidates:
            # Step 2: break ties by horizontal distance.
            best_line = y_candidates[0]
            best_x_dist = float("inf")
            for line in y_candidates:
                lx = self._line_horizontal_midpoint(line)
                if lx is None:
                    continue
                x_dist = abs(lx - center_x)
                if x_dist < best_x_dist:
                    best_x_dist = x_dist
                    best_line = line
            return best_line

        # Step 3: fall back to closest vertical midpoint.
        line_midpoints = {
            id(line): self._line_vertical_midpoint(line) for line in lines
        }
        return self._closest_line_by_midpoint(
            lines, line_midpoints, center_y, fallback_line
        )

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

    # ------------------------------------------------------------------
    # Page finalization and block tree manipulation
    # ------------------------------------------------------------------

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
