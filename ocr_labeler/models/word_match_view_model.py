"""Word matching view model for displaying OCR vs Ground Truth comparisons."""

from __future__ import annotations

import logging
from typing import List, Optional

from pd_book_tools.ocr.block import Block
from pd_book_tools.ocr.page import Page

from .line_match_model import LineMatch
from .word_match_model import MatchStatus, WordMatch

logger = logging.getLogger(__name__)


class WordMatchViewModel:
    """View model for word-level OCR vs Ground Truth matching display."""

    def __init__(self):
        self.line_matches: List[LineMatch] = []
        self.fuzz_threshold: float = 0.8  # Threshold for fuzzy matches

    def update_from_page(self, page: Page) -> None:
        """Update the view model from a Page object."""
        self.line_matches.clear()

        if not page:
            return

        # Get lines from the page using the convenience method
        try:
            lines = page.lines if hasattr(page, "lines") else []
            if not lines:
                logger.debug("No lines found in page")
                return

            logger.debug(f"Found {len(lines)} lines in page")

            for line_idx, line in enumerate(lines):
                line_match = self._create_line_match(line_idx, line, page)
                if line_match:
                    self.line_matches.append(line_match)

        except Exception as e:
            logger.exception(f"Error updating word match view model: {e}")

    def _create_line_match(
        self, line_idx: int, line: Block, page: Page
    ) -> Optional[LineMatch]:
        """Create a LineMatch from a line object."""
        try:
            # Create enhanced word matches that include unmatched GT words
            word_matches = self._create_enhanced_word_matches(line)
            logger.debug(
                f"Line {line_idx} has {len(word_matches)} word matches after enhancement"
            )

            # Only skip the line if there are neither OCR words nor unmatched GT words
            if not word_matches:
                logger.debug(f"No words or unmatched GT words found in line {line_idx}")
                return None

            page_image = getattr(page, "cv2_numpy_page_image", None) if page else None
            if page_image is None:
                logger.error(f"No page image available for line {line_idx}")

            return LineMatch(
                line_index=line_idx,
                ocr_line_text=line.text,
                ground_truth_line_text=line.ground_truth_text,
                word_matches=word_matches,
                page_image=page_image,
            )

        except Exception as e:
            logger.exception(f"Error creating line match for line {line_idx}: {e}")
            return None

    def _create_enhanced_word_matches(self, line: Block) -> List[WordMatch]:
        """Create word matches including unmatched ground truth words inserted before the next match."""

        enhanced_matches = []

        # Get words and unmatched ground truth words from the line
        words = getattr(line, "words", [])
        unmatched_gt_words = getattr(line, "unmatched_ground_truth_words", [])

        logger.debug(
            f"Processing line with {len(words)} OCR words and {len(unmatched_gt_words) if unmatched_gt_words else 0} unmatched GT words"
        )

        # Create a list to track insertion points for unmatched GT words
        # unmatched_gt_words is List[Tuple[int, str]] where int is insertion index
        insertion_map = {}
        if unmatched_gt_words:
            logger.debug(f"Unmatched GT words: {unmatched_gt_words}")
            for insert_idx, gt_word in unmatched_gt_words:
                if insert_idx not in insertion_map:
                    insertion_map[insert_idx] = []
                insertion_map[insert_idx].append(gt_word)
            logger.debug(f"Insertion map: {insertion_map}")

        # Create word matches for OCR words, inserting unmatched GT words at appropriate positions
        for word_idx, word in enumerate(words):
            # Add the OCR word match
            word_match = self._create_word_match(word_idx, word)
            if word_match:
                enhanced_matches.append(word_match)

            # Insert any unmatched GT words that should come after this OCR word
            if word_idx in insertion_map:
                for gt_word in insertion_map[word_idx]:
                    unmatched_gt_match = WordMatch(
                        ocr_text="",
                        ground_truth_text=gt_word,
                        match_status=MatchStatus.UNMATCHED_GT,
                        word_index=None,
                        word_object=None,
                    )
                    enhanced_matches.append(unmatched_gt_match)

        # Insert any remaining unmatched GT words that should come after the last OCR word
        final_insert_idx = len(words)
        if final_insert_idx in insertion_map:
            for gt_word in insertion_map[final_insert_idx]:
                unmatched_gt_match = WordMatch(
                    ocr_text="",
                    ground_truth_text=gt_word,
                    match_status=MatchStatus.UNMATCHED_GT,
                    word_index=None,
                    word_object=None,
                )
                enhanced_matches.append(unmatched_gt_match)

        logger.debug(
            f"Created {len(enhanced_matches)} enhanced matches: {[(wm.ocr_text or '[none]', wm.ground_truth_text or '[none]', wm.match_status.value) for wm in enhanced_matches]}"
        )
        return enhanced_matches

    def _words_match(self, ocr_text: str, gt_text: str, threshold: float) -> bool:
        """Check if two words match (exact or above fuzzy threshold)."""
        if not ocr_text.strip() or not gt_text.strip():
            return False

        # Exact match
        if ocr_text.strip() == gt_text.strip():
            return True

        # Fuzzy match - compute simple character-based similarity
        try:
            # Simple character-based similarity (Levenshtein-like)
            import difflib

            similarity = difflib.SequenceMatcher(
                None, ocr_text.strip().lower(), gt_text.strip().lower()
            ).ratio()
            return similarity >= threshold
        except Exception:
            # Fallback to exact match only if difflib fails
            return False

    def _create_word_match(self, word_idx: int, word) -> Optional[WordMatch]:
        """Create a WordMatch from a word object."""
        try:
            ocr_text = getattr(word, "text", "")
            ground_truth_text = getattr(word, "ground_truth_text", "")

            # If no ground truth, mark as unmatched OCR
            if not ground_truth_text:
                return WordMatch(
                    ocr_text=ocr_text,
                    ground_truth_text="",
                    match_status=MatchStatus.UNMATCHED_OCR,
                    word_index=word_idx,
                    word_object=word,
                )

            # First, do a strict exact text comparison - this is the ONLY way to be marked as exact
            if ocr_text.strip() == ground_truth_text.strip():
                return WordMatch(
                    ocr_text=ocr_text,
                    ground_truth_text=ground_truth_text,
                    match_status=MatchStatus.EXACT,
                    fuzz_score=1.0,
                    word_index=word_idx,
                    word_object=word,
                )

            # If not exact, compute fuzzy score for non-exact matches
            fuzz_score = None
            if hasattr(word, "fuzz_score_against") and callable(
                getattr(word, "fuzz_score_against")
            ):
                try:
                    fuzz_score = word.fuzz_score_against(ground_truth_text)
                except Exception as e:
                    logger.debug(f"Error computing fuzz score for word {word_idx}: {e}")

            # For non-exact matches, determine if it's fuzzy or mismatch based on score
            if fuzz_score is not None and fuzz_score >= self.fuzz_threshold:
                match_status = MatchStatus.FUZZY
            else:
                match_status = MatchStatus.MISMATCH
                # Set fuzz_score to 0.0 if it wasn't computed or is below threshold
                if fuzz_score is None:
                    fuzz_score = 0.0

            return WordMatch(
                ocr_text=ocr_text,
                ground_truth_text=ground_truth_text,
                match_status=match_status,
                fuzz_score=fuzz_score,
                word_index=word_idx,
                word_object=word,
            )

        except Exception as e:
            logger.exception(f"Error creating word match for word {word_idx}: {e}")
            return None

    def get_summary_stats(self) -> dict:
        """Get summary statistics for all matches."""
        total_words = sum(len(lm.word_matches) for lm in self.line_matches)
        exact_matches = sum(lm.exact_match_count for lm in self.line_matches)
        fuzzy_matches = sum(lm.fuzzy_match_count for lm in self.line_matches)
        mismatches = sum(lm.mismatch_count for lm in self.line_matches)
        unmatched_gt = sum(lm.unmatched_gt_count for lm in self.line_matches)
        unmatched_ocr = sum(lm.unmatched_ocr_count for lm in self.line_matches)

        return {
            "total_words": total_words,
            "exact_matches": exact_matches,
            "fuzzy_matches": fuzzy_matches,
            "mismatches": mismatches,
            "unmatched_gt": unmatched_gt,
            "unmatched_ocr": unmatched_ocr,
            "exact_percentage": (exact_matches / total_words * 100)
            if total_words > 0
            else 0,
            "total_matches": exact_matches + fuzzy_matches,
            "match_percentage": ((exact_matches + fuzzy_matches) / total_words * 100)
            if total_words > 0
            else 0,
        }
