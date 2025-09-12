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
    word_object: Optional[object] = None  # Reference to the original word object for image access
    
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
            logger.debug(f"No word_object ({self.word_object is not None}) or page_image ({page_image is not None}) for word: {self.ocr_text}")
            return None
            
        try:
            # Get bounding box from word object
            bbox = getattr(self.word_object, 'bounding_box', None)
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
            logger.debug(f"Getting coordinates from pixel_bbox.minX={pixel_bbox.minX}, type={type(pixel_bbox.minX)}")
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
                
            logger.debug(f"Successfully cropped word '{self.ocr_text}' to shape {cropped.shape}")
            return cropped
            
        except Exception as e:
            import traceback
            logger.debug(f"Error cropping word image for '{self.ocr_text}': {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None


@dataclass 
class LineMatch:
    """Represents matching for a complete line."""
    line_index: int
    ocr_line_text: str
    ground_truth_line_text: str
    word_matches: List[WordMatch]
    page_image: Optional[object] = None  # Reference to page image for cropping
    
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
                line_match = self._create_line_match(line_idx, line, page)
                if line_match:
                    self.line_matches.append(line_match)
                    
        except Exception as e:
            logger.exception(f"Error updating word match view model: {e}")
    
    def _create_line_match(self, line_idx: int, line, page) -> Optional[LineMatch]:
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
            
            page_image=getattr(page, 'cv2_numpy_page_image', None) if page else None
            if page_image is None:
                logger.error(f"No page image available for line {line_idx}")

            return LineMatch(
                line_index=line_idx,
                ocr_line_text=ocr_line_text,
                ground_truth_line_text=ground_truth_line_text,
                word_matches=word_matches,
                page_image=page_image
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
                    word_index=word_idx,
                    word_object=word
                )
            
            # First, do a strict exact text comparison - this is the ONLY way to be marked as exact
            if ocr_text.strip() == ground_truth_text.strip():
                return WordMatch(
                    ocr_text=ocr_text,
                    ground_truth_text=ground_truth_text,
                    match_status=MatchStatus.EXACT,
                    fuzz_score=1.0,
                    word_index=word_idx,
                    word_object=word
                )
            
            # If not exact, compute fuzzy score for non-exact matches
            fuzz_score = None
            if hasattr(word, 'fuzz_score_against') and callable(getattr(word, 'fuzz_score_against')):
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
                word_object=word
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
