"""Word matching view component for displaying OCR vs Ground Truth comparisons with color coding."""

from __future__ import annotations
from nicegui import ui
from ..models.word_match import WordMatchViewModel
import logging

logger = logging.getLogger(__name__)


class WordMatchView:
    """View component for displaying word-level OCR vs Ground Truth matching with color coding."""
    
    def __init__(self):
        self.view_model = WordMatchViewModel()
        self.container = None
        self.summary_label = None
        self.lines_container = None
        
    def build(self):
        """Build the UI components."""
        with ui.column().classes("full-width full-height") as container:
            # Header with summary stats
            self.summary_label = ui.label("No matches to display").classes("text-caption text-grey q-mb-md")
            
            # Scrollable container for word matches
            with ui.scroll_area().classes("full-width").style("height: calc(100% - 40px);"):
                self.lines_container = ui.column().classes("full-width q-gutter-sm")
            
        self.container = container
        self._inject_styles()
        return container
    
    def _inject_styles(self):
        """Inject CSS styles for word match coloring."""
        ui.add_head_html("""
        <style>
        /* Word match status colors */
        .word-match-exact {
            background-color: #c8e6c9 !important;
            color: #2e7d32 !important;
            padding: 2px 4px;
            border-radius: 3px;
            margin: 1px;
            display: inline-block;
        }
        
        .word-match-fuzzy {
            background-color: #fff3e0 !important;
            color: #f57c00 !important;
            padding: 2px 4px;
            border-radius: 3px;
            margin: 1px;
            display: inline-block;
        }
        
        .word-match-mismatch {
            background-color: #ffcdd2 !important;
            color: #c62828 !important;
            padding: 2px 4px;
            border-radius: 3px;
            margin: 1px;
            display: inline-block;
        }
        
        .word-match-unmatched-ocr {
            background-color: #f3e5f5 !important;
            color: #7b1fa2 !important;
            padding: 2px 4px;
            border-radius: 3px;
            margin: 1px;
            display: inline-block;
        }
        
        .word-match-unmatched-gt {
            background-color: #e1f5fe !important;
            color: #0277bd !important;
            padding: 2px 4px;
            border-radius: 3px;
            margin: 1px;
            display: inline-block;
        }
        
        /* Line containers */
        .line-match-container {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
        }
        
        .line-match-exact {
            border-left: 4px solid #4caf50;
        }
        
        .line-match-fuzzy {
            border-left: 4px solid #ff9800;
        }
        
        .line-match-mismatch {
            border-left: 4px solid #f44336;
        }
        
        .word-comparison-row {
            display: flex;
            gap: 8px;
            margin: 4px 0;
            align-items: flex-start;
        }
        
        .word-comparison-label {
            min-width: 40px;
            font-weight: 500;
            font-size: 0.9em;
        }
        
        .word-text-container {
            flex: 1;
            line-height: 1.6;
        }
        
        /* Tooltip styles */
        .word-tooltip {
            font-size: 0.8em;
        }
        </style>
        """)
    
    def update_from_page(self, page):
        """Update the view with matches from a page."""
        try:
            # Update the view model
            self.view_model.update_from_page(page)
            
            # Update the UI
            self._update_summary()
            self._update_lines_display()
            
        except Exception as e:
            logger.exception(f"Error updating word match view: {e}")
    
    def _update_summary(self):
        """Update the summary statistics display."""
        if not self.summary_label:
            return
            
        stats = self.view_model.get_summary_stats()
        if stats['total_words'] == 0:
            self.summary_label.set_text("No words to compare")
            return
        
        summary_text = (
            f"Words: {stats['total_words']} | "
            f"Exact: {stats['exact_matches']} ({stats['exact_percentage']:.1f}%) | "
            f"Fuzzy: {stats['fuzzy_matches']} | "
            f"Mismatches: {stats['mismatches']} | "
            f"Total Match: {stats['match_percentage']:.1f}%"
        )
        self.summary_label.set_text(summary_text)
    
    def _update_lines_display(self):
        """Update the lines display with word matches."""
        if not self.lines_container:
            return
            
        # Clear existing content
        self.lines_container.clear()
        
        if not self.view_model.line_matches:
            with self.lines_container:
                ui.label("No line matches found").classes("text-grey text-center q-pa-md")
            return
        
        # Display each line match
        with self.lines_container:
            for line_match in self.view_model.line_matches:
                self._create_line_display(line_match)
    
    def _create_line_display(self, line_match):
        """Create display for a single line match."""
        line_class = f"line-match-container line-match-{line_match.overall_match_status.value}"
        
        with ui.column().classes(line_class):
            # Line header
            ui.label(f"Line {line_match.line_index + 1}").classes("text-subtitle2 text-weight-medium")
            
            # OCR text with word coloring
            with ui.row().classes("word-comparison-row"):
                ui.label("OCR:").classes("word-comparison-label text-blue-8")
                with ui.column().classes("word-text-container"):
                    self._create_word_text_display(line_match.word_matches, "ocr")
            
            # Ground Truth text with word coloring  
            with ui.row().classes("word-comparison-row"):
                ui.label("GT:").classes("word-comparison-label text-green-8")
                with ui.column().classes("word-text-container"):
                    self._create_word_text_display(line_match.word_matches, "gt")
            
            # Match statistics for the line
            stats_text = (
                f"Exact: {line_match.exact_match_count}, "
                f"Fuzzy: {line_match.fuzzy_match_count}, "
                f"Mismatches: {line_match.mismatch_count}"
            )
            ui.label(stats_text).classes("text-caption text-grey")
    
    def _create_word_text_display(self, word_matches, text_type):
        """Create a display of words with appropriate coloring."""
        with ui.row().classes("q-gutter-xs").style("flex-wrap: wrap;"):
            for word_match in word_matches:
                if text_type == "ocr":
                    text = word_match.ocr_text
                else:  # gt
                    text = word_match.ground_truth_text
                
                if not text.strip():
                    continue
                
                # Create tooltip content
                tooltip_content = self._create_word_tooltip(word_match)
                
                # Create word element with tooltip
                word_element = ui.label(text).classes(f"{word_match.css_class}")
                if tooltip_content:
                    word_element.tooltip(tooltip_content).classes("word-tooltip")
    
    def _create_word_tooltip(self, word_match):
        """Create tooltip content for a word match."""
        lines = [f"Status: {word_match.match_status.value.title()}"]
        
        if word_match.fuzz_score is not None:
            lines.append(f"Similarity: {word_match.fuzz_score:.3f}")
        
        if word_match.ocr_text != word_match.ground_truth_text:
            lines.append(f"OCR: '{word_match.ocr_text}'")
            lines.append(f"GT: '{word_match.ground_truth_text}'")
        
        return "\\n".join(lines) if lines else None
    
    def set_fuzz_threshold(self, threshold: float):
        """Set the fuzzy matching threshold."""
        self.view_model.fuzz_threshold = threshold
        # Note: Would need to trigger a refresh of the current page to see changes
    
    def clear(self):
        """Clear the display."""
        if self.lines_container:
            self.lines_container.clear()
        if self.summary_label:
            self.summary_label.set_text("No matches to display")
