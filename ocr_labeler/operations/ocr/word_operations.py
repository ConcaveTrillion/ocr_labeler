"""Word-level OCR labeling operations.

Provides ``classify_match_status`` for comparing OCR and ground-truth text,
and re-exports style-related constants from ``Word``.
"""

from __future__ import annotations

import logging

from pd_book_tools.ocr.word import Word

from ocr_labeler.models.word_match_model import MatchStatus

# Re-export constants so existing imports keep working.
STYLE_LABEL_BY_ATTR = Word.STYLE_LABEL_BY_ATTR
WORD_COMPONENT_BY_ATTR = Word.WORD_COMPONENT_BY_ATTR

logger = logging.getLogger(__name__)


class WordOperations:
    """Word-level match-status classification."""

    @staticmethod
    def classify_match_status(
        ocr_text: str,
        ground_truth_text: str,
        fuzz_threshold: float,
        word_object: object | None = None,
    ) -> tuple[MatchStatus, float | None]:
        """Classify match status between OCR text and ground truth.

        Returns (match_status, fuzz_score).
        """
        if not ground_truth_text:
            return MatchStatus.UNMATCHED_OCR, None

        if ocr_text.strip() == ground_truth_text.strip():
            return MatchStatus.EXACT, 1.0

        fuzz_score = None
        if (
            word_object is not None
            and hasattr(word_object, "fuzz_score_against")
            and callable(getattr(word_object, "fuzz_score_against"))
        ):
            try:
                fuzz_score = word_object.fuzz_score_against(ground_truth_text)
            except Exception:
                logger.debug("Error computing fuzz score", exc_info=True)

        if fuzz_score is not None and fuzz_score >= fuzz_threshold:
            return MatchStatus.FUZZY, fuzz_score

        return MatchStatus.MISMATCH, 0.0 if fuzz_score is None else fuzz_score
