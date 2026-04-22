"""Line matching model for line-level OCR vs Ground Truth comparisons."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pd_book_tools.ocr.image_utilities import crop_image_to_bbox

from .word_match_model import MatchStatus, WordMatch

logger = logging.getLogger(__name__)


@dataclass
class LineMatch:
    """Represents matching for a complete line."""

    line_index: int
    ocr_line_text: str
    ground_truth_line_text: str
    word_matches: list[WordMatch]
    paragraph_index: int | None = None
    page_image: object | None = None  # Reference to page image for cropping
    line_object: object | None = (
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
            and self.paragraph_index == other.paragraph_index
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
                self.paragraph_index,
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
    def validated_word_count(self) -> int:
        """Count of validated words."""
        return sum(1 for wm in self.word_matches if wm.is_validated)

    @property
    def total_word_count(self) -> int:
        """Total number of words in this line."""
        return len(self.word_matches)

    @property
    def is_fully_validated(self) -> bool:
        """Return True if all words in this line are validated."""
        return bool(self.word_matches) and all(
            wm.is_validated for wm in self.word_matches
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

        return crop_image_to_bbox(
            self.line_object,
            page_image,
            label=f"line {self.line_index}",
        )
