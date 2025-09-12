"""Word matching view model for displaying OCR vs Ground Truth comparisons."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import logging

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
    
    @property
    def css_class(self) -> str:
        """Return CSS class for styling based on match status."""
        return f"word-match-{self.match_status.value}"
    
    @property
    def is_match(self) -> bool:
        """Return True if this is a match (exact or fuzzy)."""
        return self.match_status in (MatchStatus.EXACT, MatchStatus.FUZZY)


@dataclass 
class LineMatch:
    """Represents matching for a complete line."""
    line_index: int
    ocr_line_text: str
    ground_truth_line_text: str
    word_matches: List[WordMatch]
    
    @property
    def exact_match_count(self) -> int:
        """Count of exactly matching words."""
        return sum(1 for wm in self.word_matches if wm.match_status == MatchStatus.EXACT)
    
    @property
    def fuzzy_match_count(self) -> int:
        """Count of fuzzy matching words.""" 
        return sum(1 for wm in self.word_matches if wm.match_status == MatchStatus.FUZZY)
    
    @property
    def mismatch_count(self) -> int:
        """Count of mismatched words."""
        return sum(1 for wm in self.word_matches if wm.match_status == MatchStatus.MISMATCH)
    
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


class WordMatchViewModel:
    """View model for word-level OCR vs Ground Truth matching display."""
    
    def __init__(self):
        self.line_matches: List[LineMatch] = []
        self.fuzz_threshold: float = 0.8  # Threshold for fuzzy matches
    
    def update_from_page(self, page) -> None:
        """Update the view model from a Page object."""
        self.line_matches.clear()
        
        if not page:
            return
            
        # Get lines from the page
        try:
            lines = getattr(page, 'lines', [])
            if not lines:
                logger.debug("No lines found in page")
                return
                
            for line_idx, line in enumerate(lines):
                line_match = self._create_line_match(line_idx, line)
                if line_match:
                    self.line_matches.append(line_match)
                    
        except Exception as e:
            logger.exception(f"Error updating word match view model: {e}")
    
    def _create_line_match(self, line_idx: int, line) -> Optional[LineMatch]:
        """Create a LineMatch from a line object."""
        try:
            # Get words from the line
            words = getattr(line, 'words', [])
            if not words:
                logger.debug(f"No words found in line {line_idx}")
                return None
            
            # Get line text
            ocr_line_text = getattr(line, 'text', '')
            ground_truth_line_text = getattr(line, 'ground_truth_text', '')
            
            word_matches = []
            for word_idx, word in enumerate(words):
                word_match = self._create_word_match(word_idx, word)
                if word_match:
                    word_matches.append(word_match)
            
            return LineMatch(
                line_index=line_idx,
                ocr_line_text=ocr_line_text,
                ground_truth_line_text=ground_truth_line_text,
                word_matches=word_matches
            )
            
        except Exception as e:
            logger.exception(f"Error creating line match for line {line_idx}: {e}")
            return None
    
    def _create_word_match(self, word_idx: int, word) -> Optional[WordMatch]:
        """Create a WordMatch from a word object."""
        try:
            ocr_text = getattr(word, 'text', '')
            ground_truth_text = getattr(word, 'ground_truth_text', '')
            
            # If no ground truth, mark as unmatched OCR
            if not ground_truth_text:
                return WordMatch(
                    ocr_text=ocr_text,
                    ground_truth_text='',
                    match_status=MatchStatus.UNMATCHED_OCR,
                    word_index=word_idx
                )
            
            # Check for exact match
            if hasattr(word, 'ground_truth_exact_match') and getattr(word, 'ground_truth_exact_match', False):
                return WordMatch(
                    ocr_text=ocr_text,
                    ground_truth_text=ground_truth_text,
                    match_status=MatchStatus.EXACT,
                    fuzz_score=1.0,
                    word_index=word_idx
                )
            
            # Compute fuzzy score
            fuzz_score = None
            if hasattr(word, 'fuzz_score_against') and callable(getattr(word, 'fuzz_score_against')):
                try:
                    fuzz_score = word.fuzz_score_against(ground_truth_text)
                except Exception as e:
                    logger.debug(f"Error computing fuzz score for word {word_idx}: {e}")
            
            # Determine match status based on fuzz score
            if fuzz_score is not None:
                if fuzz_score >= 1.0:
                    match_status = MatchStatus.EXACT
                elif fuzz_score >= self.fuzz_threshold:
                    match_status = MatchStatus.FUZZY
                else:
                    match_status = MatchStatus.MISMATCH
            else:
                # Fallback to simple text comparison
                if ocr_text.strip().lower() == ground_truth_text.strip().lower():
                    match_status = MatchStatus.EXACT
                    fuzz_score = 1.0
                else:
                    match_status = MatchStatus.MISMATCH
                    fuzz_score = 0.0
            
            return WordMatch(
                ocr_text=ocr_text,
                ground_truth_text=ground_truth_text,
                match_status=match_status,
                fuzz_score=fuzz_score,
                word_index=word_idx
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
        
        return {
            'total_words': total_words,
            'exact_matches': exact_matches,
            'fuzzy_matches': fuzzy_matches,
            'mismatches': mismatches,
            'exact_percentage': (exact_matches / total_words * 100) if total_words > 0 else 0,
            'total_matches': exact_matches + fuzzy_matches,
            'match_percentage': ((exact_matches + fuzzy_matches) / total_words * 100) if total_words > 0 else 0
        }
