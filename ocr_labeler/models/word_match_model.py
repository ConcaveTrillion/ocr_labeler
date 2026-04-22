"""Word matching model for individual word comparisons between OCR and Ground Truth."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from pd_book_tools.ocr.image_utilities import crop_image_to_bbox

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
    fuzz_score: float | None = None
    word_index: int | None = None
    word_object: object | None = (
        None  # Reference to the original word object for image access
    )
    is_validated: bool = False

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
            and self.is_validated == other.is_validated
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
                self.is_validated,
                # word_object excluded - may contain unhashable types
            )
        )

    @property
    def is_match(self) -> bool:
        """Return True if this is a match (exact or fuzzy)."""
        return self.match_status in (MatchStatus.EXACT, MatchStatus.FUZZY)

    def get_cropped_image(self, page_image):
        """Extract cropped word image from page image using bounding box."""
        return crop_image_to_bbox(
            self.word_object,
            page_image,
            label=f"word '{self.ocr_text}'",
        )
