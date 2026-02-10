"""Line matching model for line-level OCR vs Ground Truth comparisons."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from .word_match_model import MatchStatus, WordMatch

logger = logging.getLogger(__name__)


@dataclass
class LineMatch:
    """Represents matching for a complete line."""

    line_index: int
    ocr_line_text: str
    ground_truth_line_text: str
    word_matches: List[WordMatch]
    page_image: Optional[object] = None  # Reference to page image for cropping
    line_object: Optional[object] = (
        None  # Reference to the original line Block object for bbox access
    )

    def __eq__(self, other: object) -> bool:
        """Custom equality that handles numpy arrays properly.

        When comparing page_image and line_object, we use identity (is) instead
        of equality (==) to avoid numpy array element-wise comparison issues.
        """
        if not isinstance(other, LineMatch):
            return NotImplemented

        return (
            self.line_index == other.line_index
            and self.ocr_line_text == other.ocr_line_text
            and self.ground_truth_line_text == other.ground_truth_line_text
            and self.word_matches == other.word_matches
            and self.page_image is other.page_image  # Identity check, not equality
            and self.line_object is other.line_object  # Identity check
        )

    def __hash__(self) -> int:
        """Custom hash that excludes page_image and line_object (unhashable)."""
        return hash(
            (
                self.line_index,
                self.ocr_line_text,
                self.ground_truth_line_text,
                tuple(self.word_matches),
                # page_image and line_object excluded - may be unhashable
            )
        )

    @property
    def exact_match_count(self) -> int:
        """Count of exactly matching words."""
        return sum(
            1 for wm in self.word_matches if wm.match_status == MatchStatus.EXACT
        )

    @property
    def fuzzy_match_count(self) -> int:
        """Count of fuzzy matching words."""
        return sum(
            1 for wm in self.word_matches if wm.match_status == MatchStatus.FUZZY
        )

    @property
    def mismatch_count(self) -> int:
        """Count of mismatched words."""
        return sum(
            1 for wm in self.word_matches if wm.match_status == MatchStatus.MISMATCH
        )

    @property
    def unmatched_gt_count(self) -> int:
        """Count of unmatched ground truth words."""
        return sum(
            1 for wm in self.word_matches if wm.match_status == MatchStatus.UNMATCHED_GT
        )

    @property
    def unmatched_ocr_count(self) -> int:
        """Count of unmatched OCR words."""
        return sum(
            1
            for wm in self.word_matches
            if wm.match_status == MatchStatus.UNMATCHED_OCR
        )

    @property
    def overall_match_status(self) -> MatchStatus:
        """Overall status for the line."""
        if not self.word_matches:
            return MatchStatus.MISMATCH

        if all(wm.match_status == MatchStatus.EXACT for wm in self.word_matches):
            return MatchStatus.EXACT
        elif any(wm.is_match for wm in self.word_matches):
            return MatchStatus.FUZZY
        else:
            return MatchStatus.MISMATCH

    def get_cropped_image(self, page_image=None):
        """Extract cropped line image from page image using bounding box.

        Args:
            page_image: Optional page image to use. If None, uses self.page_image.

        Returns:
            Cropped line image as numpy array, or None if unavailable.
        """
        if page_image is None:
            page_image = self.page_image

        if not self.line_object or page_image is None:
            logger.debug(
                f"No line_object ({self.line_object is not None}) or page_image ({page_image is not None}) for line {self.line_index}"
            )
            return None

        try:
            # Get bounding box from line object
            bbox = getattr(self.line_object, "bounding_box", None)
            if not bbox:
                logger.debug(f"No bounding_box found for line {self.line_index}")
                return None

            logger.debug(f"Processing bbox for line {self.line_index}: {bbox}")

            # Use BoundingBox methods to get pixel coordinates
            height, width = page_image.shape[:2]
            logger.debug(f"Image dimensions: {height}x{width}")

            # Scale to image dimensions if normalized
            if bbox.is_normalized:
                logger.debug("Scaling normalized bbox")
                pixel_bbox = bbox.scale(width, height)
            else:
                logger.debug("Using non-normalized bbox directly")
                pixel_bbox = bbox

            logger.debug(f"Pixel bbox: {pixel_bbox}")

            # Get integer coordinates using the BoundingBox properties
            x1 = int(pixel_bbox.minX)
            y1 = int(pixel_bbox.minY)
            x2 = int(pixel_bbox.maxX)
            y2 = int(pixel_bbox.maxY)

            logger.debug(f"Extracted coordinates: ({x1}, {y1}, {x2}, {y2})")

            # Validate coordinates
            if x1 >= x2 or y1 >= y2:
                logger.debug(f"Invalid bbox coordinates: ({x1}, {y1}, {x2}, {y2})")
                return None

            # Clamp coordinates to image bounds
            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(x1 + 1, min(x2, width))
            y2 = max(y1 + 1, min(y2, height))

            logger.debug(f"Clamped coordinates: ({x1}, {y1}, {x2}, {y2})")

            # Extract the cropped region
            cropped = page_image[y1:y2, x1:x2]

            if cropped.size == 0:
                logger.debug(f"Empty crop for bbox ({x1}, {y1}, {x2}, {y2})")
                return None

            logger.debug(
                f"Successfully cropped line {self.line_index} to shape {cropped.shape}"
            )
            return cropped

        except Exception as e:
            import traceback

            logger.debug(f"Error cropping line image for line {self.line_index}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
