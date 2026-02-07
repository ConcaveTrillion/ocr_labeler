"""Word matching model for individual word comparisons between OCR and Ground Truth."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class MatchStatus(Enum):
    """Status of word matching between OCR and Ground Truth."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    MISMATCH = "mismatch"
    UNMATCHED_OCR = "unmatched_ocr"
    UNMATCHED_GT = "unmatched_gt"


@dataclass
class WordMatch:
    """Represents a single word match comparison."""

    ocr_text: str
    ground_truth_text: str
    match_status: MatchStatus
    fuzz_score: Optional[float] = None
    word_index: Optional[int] = None
    word_object: Optional[object] = (
        None  # Reference to the original word object for image access
    )

    def __eq__(self, other: object) -> bool:
        """Custom equality that handles word_object using identity check.

        The word_object might have numpy arrays or other complex types,
        so we use identity (is) instead of equality (==).
        """
        if not isinstance(other, WordMatch):
            return NotImplemented

        return (
            self.ocr_text == other.ocr_text
            and self.ground_truth_text == other.ground_truth_text
            and self.match_status == other.match_status
            and self.fuzz_score == other.fuzz_score
            and self.word_index == other.word_index
            and self.word_object is other.word_object  # Identity check
        )

    def __hash__(self) -> int:
        """Custom hash that excludes word_object (may be unhashable)."""
        return hash(
            (
                self.ocr_text,
                self.ground_truth_text,
                self.match_status,
                self.fuzz_score,
                self.word_index,
                # word_object excluded - may contain unhashable types
            )
        )

    @property
    def css_class(self) -> str:
        """Return CSS class for styling based on match status."""
        return f"word-match-{self.match_status.value}"

    @property
    def is_match(self) -> bool:
        """Return True if this is a match (exact or fuzzy)."""
        return self.match_status in (MatchStatus.EXACT, MatchStatus.FUZZY)

    def get_cropped_image(self, page_image):
        """Extract cropped word image from page image using bounding box."""
        if not self.word_object or page_image is None:
            logger.debug(
                f"No word_object ({self.word_object is not None}) or page_image ({page_image is not None}) for word: {self.ocr_text}"
            )
            return None

        try:
            # Get bounding box from word object
            bbox = getattr(self.word_object, "bounding_box", None)
            if not bbox:
                logger.debug(f"No bounding_box found for word: {self.ocr_text}")
                return None

            logger.debug(f"Processing bbox for word '{self.ocr_text}': {bbox}")

            # Use BoundingBox methods to get pixel coordinates
            height, width = page_image.shape[:2]
            logger.debug(f"Image dimensions: {height}x{width}")

            # Scale to image dimensions if normalized
            if bbox.is_normalized:
                logger.debug("Scaling normalized bbox")
                # Use the scale method to convert to pixel coordinates
                pixel_bbox = bbox.scale(width, height)
            else:
                logger.debug("Using non-normalized bbox directly")
                pixel_bbox = bbox

            logger.debug(f"Pixel bbox: {pixel_bbox}")

            # Get integer coordinates using the BoundingBox properties
            logger.debug(
                f"Getting coordinates from pixel_bbox.minX={pixel_bbox.minX}, type={type(pixel_bbox.minX)}"
            )
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
                f"Successfully cropped word '{self.ocr_text}' to shape {cropped.shape}"
            )
            return cropped

        except Exception as e:
            import traceback

            logger.debug(f"Error cropping word image for '{self.ocr_text}': {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
