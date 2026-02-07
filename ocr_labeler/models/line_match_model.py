"""Line matching model for line-level OCR vs Ground Truth comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .word_match_model import MatchStatus, WordMatch


@dataclass
class LineMatch:
    """Represents matching for a complete line."""

    line_index: int
    ocr_line_text: str
    ground_truth_line_text: str
    word_matches: List[WordMatch]
    page_image: Optional[object] = None  # Reference to page image for cropping

    def __eq__(self, other: object) -> bool:
        """Custom equality that handles numpy arrays properly.

        When comparing page_image, we use identity (is) instead of equality (==)
        to avoid numpy array element-wise comparison issues.
        """
        if not isinstance(other, LineMatch):
            return NotImplemented

        return (
            self.line_index == other.line_index
            and self.ocr_line_text == other.ocr_line_text
            and self.ground_truth_line_text == other.ground_truth_line_text
            and self.word_matches == other.word_matches
            and self.page_image is other.page_image  # Identity check, not equality
        )

    def __hash__(self) -> int:
        """Custom hash that excludes page_image (unhashable numpy array)."""
        return hash(
            (
                self.line_index,
                self.ocr_line_text,
                self.ground_truth_line_text,
                tuple(self.word_matches),
                # page_image excluded - numpy arrays are unhashable
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
