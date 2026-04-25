"""Word matching view model for displaying OCR vs Ground Truth comparisons."""

from __future__ import annotations

import logging
from dataclasses import field

from nicegui import binding
from pd_book_tools.ocr.block import Block
from pd_book_tools.ocr.page import Page

from ...models.line_match_model import LineMatch
from ...models.word_match_model import MatchStatus, WordMatch
from ...operations.ocr.word_operations import WordOperations
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class WordMatchViewModel(BaseViewModel):
    """View model for word-level OCR vs Ground Truth matching display."""

    # UI-bound properties
    line_matches: list[LineMatch] = field(default_factory=list)
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
    validated_words_count: int = field(default=0)

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
            paragraph_lookup = self._build_line_paragraph_lookup(page)

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
                logger.debug("Found %s lines in page", line_count)
            except (TypeError, AttributeError):
                logger.debug("Found lines in page (count unavailable)")

            for line_idx, line in enumerate(lines):
                line_match = self._create_line_match(
                    line_idx,
                    line,
                    page,
                    paragraph_lookup.get(id(line)),
                )
                if line_match:
                    new_line_matches.append(line_match)

        except Exception:
            logger.exception("Error updating word match view model")

        # Assign the new list (triggers NiceGUI binding)
        self.line_matches = new_line_matches
        self._update_statistics()

    def _create_line_match(
        self,
        line_idx: int,
        line: Block,
        page: Page,
        paragraph_index: int | None = None,
    ) -> LineMatch | None:
        """Create a LineMatch from a line object."""
        try:
            # Create enhanced word matches that include unmatched GT words
            word_matches = self._create_enhanced_word_matches(line)
            logger.debug(
                "Line %s has %s word matches after enhancement",
                line_idx,
                len(word_matches),
            )

            # Only skip the line if there are neither OCR words nor unmatched GT words
            if not word_matches:
                logger.debug(
                    "No words or unmatched GT words found in line %s", line_idx
                )
                return None

            page_image = getattr(page, "cv2_numpy_page_image", None) if page else None
            if page_image is None:
                logger.debug("No page image available for line %s", line_idx)

            return LineMatch(
                line_index=line_idx,
                ocr_line_text=line.text,
                ground_truth_line_text=line.ground_truth_text,
                word_matches=word_matches,
                paragraph_index=paragraph_index,
                page_image=page_image,
                line_object=line,  # Pass line object for bbox access
            )

        except Exception:
            logger.exception("Error creating line match for line %s", line_idx)
            return None

    def _build_line_paragraph_lookup(self, page: Page) -> dict[int, int]:
        """Build a mapping of line object identity to zero-based paragraph index."""
        paragraph_lookup: dict[int, int] = {}

        if page is None or not hasattr(page, "paragraphs"):
            return paragraph_lookup

        try:
            paragraphs = page.paragraphs or []
            for paragraph_idx, paragraph in enumerate(paragraphs):
                for paragraph_line in getattr(paragraph, "lines", []) or []:
                    paragraph_lookup[id(paragraph_line)] = paragraph_idx
        except Exception as e:
            logger.debug("Unable to build line-to-paragraph lookup: %s", e)

        return paragraph_lookup

    def _create_enhanced_word_matches(self, line: Block) -> list[WordMatch]:
        """Create word matches including unmatched ground truth words inserted before the next match."""

        enhanced_matches = []

        # Get words and unmatched ground truth words from the line
        words = getattr(line, "words", [])
        unmatched_gt_words = getattr(line, "unmatched_ground_truth_words", [])

        logger.debug(
            "Processing line with %s OCR words and %s unmatched GT words",
            len(words),
            len(unmatched_gt_words) if unmatched_gt_words else 0,
        )

        # Create a list to track insertion points for unmatched GT words
        # unmatched_gt_words is list[tuple[int, str]] where int is insertion index
        insertion_map = {}
        if unmatched_gt_words:
            logger.debug("Unmatched GT words: %s", unmatched_gt_words)
            for insert_idx, gt_word in unmatched_gt_words:
                if insert_idx not in insertion_map:
                    insertion_map[insert_idx] = []
                insertion_map[insert_idx].append(gt_word)
            logger.debug("Insertion map: %s", insertion_map)

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
            "Created %s enhanced matches: %s",
            len(enhanced_matches),
            [
                (
                    wm.ocr_text or "[none]",
                    wm.ground_truth_text or "[none]",
                    wm.match_status.value,
                )
                for wm in enhanced_matches
            ],
        )
        return enhanced_matches

    def _create_word_match(self, word_idx: int, word) -> WordMatch | None:
        """Create a WordMatch from a word object."""
        try:
            ocr_text = getattr(word, "text", "")
            ground_truth_text = getattr(word, "ground_truth_text", "")
            word_labels = set(getattr(word, "word_labels", []) or [])
            is_validated = "validated" in word_labels

            match_status, fuzz_score = WordOperations.classify_match_status(
                ocr_text, ground_truth_text, self.fuzz_threshold, word
            )

            return WordMatch(
                ocr_text=ocr_text,
                ground_truth_text=ground_truth_text,
                match_status=match_status,
                fuzz_score=fuzz_score,
                word_index=word_idx,
                word_object=word,
                is_validated=is_validated,
            )

        except Exception:
            logger.exception("Error creating word match for word %s", word_idx)
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
        old_validated = self.validated_words_count

        self.total_words = sum(len(lm.word_matches) for lm in self.line_matches)
        self.exact_matches_count = sum(lm.exact_match_count for lm in self.line_matches)
        self.fuzzy_matches_count = sum(lm.fuzzy_match_count for lm in self.line_matches)
        self.mismatches_count = sum(lm.mismatch_count for lm in self.line_matches)
        self.unmatched_gt_count = sum(lm.unmatched_gt_count for lm in self.line_matches)
        self.unmatched_ocr_count = sum(
            lm.unmatched_ocr_count for lm in self.line_matches
        )
        self.validated_words_count = sum(
            lm.validated_word_count for lm in self.line_matches
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
            ("validated_words_count", old_validated, self.validated_words_count),
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
            "validated_words": self.validated_words_count,
        }
