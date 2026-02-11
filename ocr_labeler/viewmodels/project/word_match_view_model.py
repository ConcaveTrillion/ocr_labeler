"""Word matching view model for displaying OCR vs Ground Truth comparisons."""

from __future__ import annotations

import logging
from dataclasses import field
from typing import List, Optional

from nicegui import binding
from pd_book_tools.ocr.block import Block
from pd_book_tools.ocr.page import Page

from ...models.line_match_model import LineMatch
from ...models.word_match_model import MatchStatus, WordMatch
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class WordMatchViewModel(BaseViewModel):
    """View model for word-level OCR vs Ground Truth matching display."""

    # UI-bound properties
    line_matches: List[LineMatch] = field(default_factory=list)
    fuzz_threshold: float = field(default=0.8)  # Threshold for fuzzy matches

    # Filtering and display options
    show_exact_matches: bool = field(default=True)
    show_fuzzy_matches: bool = field(default=True)
    show_mismatches: bool = field(default=True)
    show_unmatched_ocr: bool = field(default=True)
    show_unmatched_gt: bool = field(default=True)

    # Statistics
    total_words: int = field(default=0)
    exact_matches_count: int = field(default=0)
    fuzzy_matches_count: int = field(default=0)
    mismatches_count: int = field(default=0)
    unmatched_gt_count: int = field(default=0)
    unmatched_ocr_count: int = field(default=0)
    exact_percentage: float = field(default=0.0)
    match_percentage: float = field(default=0.0)

    def __post_init__(self):
        """Initialize after dataclass construction."""
        super().__post_init__()
        # Ensure binding properties are properly initialized
        # The dataclass fields are already set, binding system will handle them

    def update_from_page(self, page: Page) -> None:
        """Update the view model from a Page object."""
        # Create a new list instead of modifying in place to trigger NiceGUI binding
        new_line_matches = []

        if not page:
            self.line_matches = new_line_matches
            self._update_statistics()
            return

        # Get lines from the page using the convenience method
        try:
            lines = page.lines if hasattr(page, "lines") else []

            # Defensive check for Mock objects in tests - check if iterable
            try:
                iter(lines)
            except TypeError:
                logger.debug("Lines attribute is not iterable (likely a Mock in tests)")
                self.line_matches = new_line_matches
                self._update_statistics()
                return

            if not lines:
                logger.debug("No lines found in page")
                self.line_matches = new_line_matches
                self._update_statistics()
                return

            # Defensive logging for test compatibility with Mock objects
            try:
                line_count = len(lines)
                logger.debug(f"Found {line_count} lines in page")
            except (TypeError, AttributeError):
                logger.debug("Found lines in page (count unavailable)")

            for line_idx, line in enumerate(lines):
                line_match = self._create_line_match(line_idx, line, page)
                if line_match:
                    new_line_matches.append(line_match)

        except Exception as e:
            logger.exception(f"Error updating word match view model: {e}")

        # Assign the new list (triggers NiceGUI binding)
        self.line_matches = new_line_matches
        self._update_statistics()

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
                logger.debug(f"No page image available for line {line_idx}")

            return LineMatch(
                line_index=line_idx,
                ocr_line_text=line.text,
                ground_truth_line_text=line.ground_truth_text,
                word_matches=word_matches,
                page_image=page_image,
                line_object=line,  # Pass line object for bbox access
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

    def _update_statistics(self):
        """Update statistics based on current line matches."""
        # Check if binding properties are initialized (avoid accessing during __init__)
        if not hasattr(self, "total_words"):
            return

        old_total = self.total_words
        old_exact = self.exact_matches_count
        old_fuzzy = self.fuzzy_matches_count
        old_mismatches = self.mismatches_count
        old_unmatched_gt = self.unmatched_gt_count
        old_unmatched_ocr = self.unmatched_ocr_count
        old_exact_pct = self.exact_percentage
        old_match_pct = self.match_percentage

        self.total_words = sum(len(lm.word_matches) for lm in self.line_matches)
        self.exact_matches_count = sum(lm.exact_match_count for lm in self.line_matches)
        self.fuzzy_matches_count = sum(lm.fuzzy_match_count for lm in self.line_matches)
        self.mismatches_count = sum(lm.mismatch_count for lm in self.line_matches)
        self.unmatched_gt_count = sum(lm.unmatched_gt_count for lm in self.line_matches)
        self.unmatched_ocr_count = sum(
            lm.unmatched_ocr_count for lm in self.line_matches
        )

        self.exact_percentage = (
            (self.exact_matches_count / self.total_words * 100)
            if self.total_words > 0
            else 0.0
        )
        self.match_percentage = (
            (
                (self.exact_matches_count + self.fuzzy_matches_count)
                / self.total_words
                * 100
            )
            if self.total_words > 0
            else 0.0
        )

        # Notify changes
        changes = [
            ("total_words", old_total, self.total_words),
            ("exact_matches_count", old_exact, self.exact_matches_count),
            ("fuzzy_matches_count", old_fuzzy, self.fuzzy_matches_count),
            ("mismatches_count", old_mismatches, self.mismatches_count),
            ("unmatched_gt_count", old_unmatched_gt, self.unmatched_gt_count),
            ("unmatched_ocr_count", old_unmatched_ocr, self.unmatched_ocr_count),
            ("exact_percentage", old_exact_pct, self.exact_percentage),
            ("match_percentage", old_match_pct, self.match_percentage),
        ]

        for prop_name, old_val, new_val in changes:
            if old_val != new_val:
                self.notify_property_changed(prop_name, new_val)

    def get_summary_stats(self) -> dict:
        """Get summary statistics for all matches."""
        return {
            "total_words": self.total_words,
            "exact_matches": self.exact_matches_count,
            "fuzzy_matches": self.fuzzy_matches_count,
            "mismatches": self.mismatches_count,
            "unmatched_gt": self.unmatched_gt_count,
            "unmatched_ocr": self.unmatched_ocr_count,
            "exact_percentage": self.exact_percentage,
            "total_matches": self.exact_matches_count + self.fuzzy_matches_count,
            "match_percentage": self.match_percentage,
        }

    # Command methods for UI actions

    def command_set_fuzz_threshold(self, threshold: float) -> bool:
        """Command to set the fuzzy matching threshold.

        Args:
            threshold: New threshold value (0.0 to 1.0).

        Returns:
            True if threshold was set successfully.
        """
        try:
            if not (0.0 <= threshold <= 1.0):
                logger.warning(
                    f"Invalid fuzz threshold {threshold}, must be between 0.0 and 1.0"
                )
                return False

            old_threshold = self.fuzz_threshold
            self.fuzz_threshold = threshold

            if old_threshold != self.fuzz_threshold:
                self.notify_property_changed("fuzz_threshold", self.fuzz_threshold)
                logger.debug(
                    f"Fuzz threshold changed from {old_threshold} to {threshold}"
                )

            return True

        except Exception as e:
            logger.exception(f"Error setting fuzz threshold to {threshold}: {e}")
            return False

    def command_toggle_match_type_filter(self, match_type: str, enabled: bool) -> bool:
        """Command to toggle visibility of a match type.

        Args:
            match_type: Type of match to toggle ('exact', 'fuzzy', 'mismatch', 'unmatched_ocr', 'unmatched_gt').
            enabled: Whether to show this match type.

        Returns:
            True if filter was toggled successfully.
        """
        try:
            filter_map = {
                "exact": "show_exact_matches",
                "fuzzy": "show_fuzzy_matches",
                "mismatch": "show_mismatches",
                "unmatched_ocr": "show_unmatched_ocr",
                "unmatched_gt": "show_unmatched_gt",
            }

            if match_type not in filter_map:
                logger.warning(f"Unknown match type filter: {match_type}")
                return False

            attr_name = filter_map[match_type]
            old_value = getattr(self, attr_name)
            setattr(self, attr_name, enabled)

            if old_value != enabled:
                self.notify_property_changed(attr_name, enabled)
                logger.debug(
                    f"Filter {attr_name} changed from {old_value} to {enabled}"
                )

            return True

        except Exception as e:
            logger.exception(f"Error toggling filter {match_type}: {e}")
            return False

    def command_reset_filters(self) -> bool:
        """Command to reset all filters to show everything.

        Returns:
            True if filters were reset successfully.
        """
        try:
            old_filters = {
                "show_exact_matches": self.show_exact_matches,
                "show_fuzzy_matches": self.show_fuzzy_matches,
                "show_mismatches": self.show_mismatches,
                "show_unmatched_ocr": self.show_unmatched_ocr,
                "show_unmatched_gt": self.show_unmatched_gt,
            }

            self.show_exact_matches = True
            self.show_fuzzy_matches = True
            self.show_mismatches = True
            self.show_unmatched_ocr = True
            self.show_unmatched_gt = True

            # Notify changes
            for attr_name, old_value in old_filters.items():
                new_value = getattr(self, attr_name)
                if old_value != new_value:
                    self.notify_property_changed(attr_name, new_value)

            logger.debug("All filters reset to show all match types")
            return True

        except Exception:
            logger.exception("Error resetting filters")
            return False

    def command_get_filtered_line_matches(self) -> List[LineMatch]:
        """Command to get line matches filtered according to current filter settings.

        Returns:
            List of filtered LineMatch objects.
        """
        try:
            filtered_lines = []

            for line_match in self.line_matches:
                filtered_words = []

                for word_match in line_match.word_matches:
                    should_include = False

                    if (
                        word_match.match_status == MatchStatus.EXACT
                        and self.show_exact_matches
                    ):
                        should_include = True
                    elif (
                        word_match.match_status == MatchStatus.FUZZY
                        and self.show_fuzzy_matches
                    ):
                        should_include = True
                    elif (
                        word_match.match_status == MatchStatus.MISMATCH
                        and self.show_mismatches
                    ):
                        should_include = True
                    elif (
                        word_match.match_status == MatchStatus.UNMATCHED_OCR
                        and self.show_unmatched_ocr
                    ):
                        should_include = True
                    elif (
                        word_match.match_status == MatchStatus.UNMATCHED_GT
                        and self.show_unmatched_gt
                    ):
                        should_include = True

                    if should_include:
                        filtered_words.append(word_match)

                # Only include lines that have words after filtering
                if filtered_words:
                    filtered_line = LineMatch(
                        line_index=line_match.line_index,
                        ocr_line_text=line_match.ocr_line_text,
                        ground_truth_line_text=line_match.ground_truth_line_text,
                        word_matches=filtered_words,
                        page_image=line_match.page_image,
                        line_object=line_match.line_object,  # Preserve line object
                    )
                    filtered_lines.append(filtered_line)

            return filtered_lines

        except Exception:
            logger.exception("Error getting filtered line matches")
            return self.line_matches.copy()  # Return unfiltered on error

    def command_get_display_stats(self) -> dict:
        """Command to get statistics formatted for display.

        Returns:
            Dictionary with formatted statistics.
        """
        try:
            stats = self.get_summary_stats()
            return {
                "total_words": f"{stats['total_words']:,}",
                "exact_matches": f"{stats['exact_matches']:,}",
                "fuzzy_matches": f"{stats['fuzzy_matches']:,}",
                "mismatches": f"{stats['mismatches']:,}",
                "unmatched_gt": f"{stats['unmatched_gt']:,}",
                "unmatched_ocr": f"{stats['unmatched_ocr']:,}",
                "exact_percentage": f"{stats['exact_percentage']:.1f}%",
                "match_percentage": f"{stats['match_percentage']:.1f}%",
            }
        except Exception:
            logger.exception("Error getting display stats")
            return {
                "total_words": "0",
                "exact_matches": "0",
                "fuzzy_matches": "0",
                "mismatches": "0",
                "unmatched_gt": "0",
                "unmatched_ocr": "0",
                "exact_percentage": "0.0%",
                "match_percentage": "0.0%",
            }
