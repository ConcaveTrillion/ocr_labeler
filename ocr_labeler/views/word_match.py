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
            # Header card with summary stats
            with ui.card().classes("full-width q-mb-sm").style("padding: 12px;"):
                with ui.row().classes("items-center"):
                    ui.icon("analytics").classes("text-blue-6 q-mr-sm")
                    self.summary_label = ui.label("No matches to display").classes("text-subtitle2 text-grey-7")
            
            # Scrollable container for word matches
            with ui.scroll_area().classes("full-width").style("height: calc(100% - 80px);"):
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
        
        /* Line containers - using card styling */
        .line-match-card {
            transition: box-shadow 0.2s ease;
        }
        
        .line-match-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
        }
        
        .line-match-exact {
            border-left: 4px solid #4caf50 !important;
        }
        
        .line-match-fuzzy {
            border-left: 4px solid #ff9800 !important;
        }
        
        .line-match-mismatch {
            border-left: 4px solid #f44336 !important;
        }
        
        .line-header-chip {
            background-color: #f5f5f5 !important;
            color: #666 !important;
            font-size: 0.85em !important;
            padding: 4px 8px !important;
            border-radius: 12px !important;
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
            self.summary_label.set_text("Ready to analyze word matches")
            return
        
        summary_text = (
            f"📊 {stats['total_words']} words • "
            f"✅ {stats['exact_matches']} exact ({stats['exact_percentage']:.1f}%) • "
            f"⚡ {stats['fuzzy_matches']} fuzzy • "
            f"❌ {stats['mismatches']} mismatches • "
            f"🎯 {stats['match_percentage']:.1f}% match rate"
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
                with ui.card().classes("full-width text-center"):
                    with ui.card_section():
                        ui.icon("info").classes("text-grey-5 text-h4 q-mb-sm")
                        ui.label("No line matches found").classes("text-grey-7")
                        ui.label("Load a page with OCR and ground truth to see word comparisons").classes("text-caption text-grey-5")
            return
        
        # Display each line match in cards
        with self.lines_container:
            for line_match in self.view_model.line_matches:
                self._create_line_card(line_match)
    
    def _create_line_card(self, line_match):
        """Create a card display for a single line match."""
        line_class = f"line-match-card line-match-{line_match.overall_match_status.value}"
        
        with ui.card().classes(f"full-width {line_class}").style("margin-bottom: 8px;"):
            # Card header with line info and status
            with ui.card_section().classes("q-pb-none"):
                with ui.row().classes("items-center justify-between"):
                    with ui.row().classes("items-center"):
                        ui.icon("format_list_numbered").classes("text-grey-6 q-mr-xs")
                        ui.label(f"Line {line_match.line_index + 1}").classes("text-subtitle2 text-weight-medium")
                    
                    # Status chip
                    status_color = self._get_status_color(line_match.overall_match_status.value)
                    ui.chip(
                        line_match.overall_match_status.value.title(),
                        icon=self._get_status_icon(line_match.overall_match_status.value)
                    ).classes(f"text-{status_color}")
            
            # Card content with word comparison table
            with ui.card_section():
                # Word comparison table
                with ui.expansion("Word Comparison", icon="compare_arrows", value=True).classes("full-width q-mb-sm"):
                    with ui.column().classes("q-pa-sm"):
                        self._create_word_comparison_table(line_match)
                
                # Statistics section in a separate area
                with ui.row().classes("items-center q-gutter-sm"):
                    ui.icon("bar_chart").classes("text-grey-5")
                    stats_items = [
                        f"✓ {line_match.exact_match_count}",
                        f"~ {line_match.fuzzy_match_count}", 
                        f"✗ {line_match.mismatch_count}"
                    ]
                    ui.label(" • ".join(stats_items)).classes("text-caption text-grey-7")
    
    def _create_word_comparison_table(self, line_match):
        """Create a table layout comparing OCR and GT words with images."""
        if not line_match.word_matches:
            ui.label("No words found").classes("text-grey-5 text-center q-pa-sm")
            return
        
        # Create table-like layout
        with ui.column().classes("full-width"):
            # Table header
            with ui.row().classes("items-center q-py-sm").style("background-color: #f5f5f5; border-radius: 4px; margin-bottom: 8px;"):
                ui.label("Word Image").classes("text-weight-medium text-center").style("min-width: 80px; max-width: 80px;")
                ui.label("OCR Text").classes("text-weight-medium text-center q-ml-sm").style("min-width: 120px; flex: 1;")
                ui.label("GT Text").classes("text-weight-medium text-center q-ml-sm").style("min-width: 120px; flex: 1;")
                ui.label("Match").classes("text-weight-medium text-center q-ml-sm").style("min-width: 60px; max-width: 60px;")
            
            # Word rows
            for word_match in line_match.word_matches:
                self._create_word_row(word_match)
    
    def _create_word_row(self, word_match):
        """Create a single word comparison row."""
        with ui.row().classes("items-center q-py-xs word-comparison-row").style("border-bottom: 1px solid #e0e0e0; min-height: 60px;"):
            # Word image column
            with ui.column().classes("items-center").style("min-width: 80px; max-width: 80px;"):
                word_image = self._get_word_image(word_match)
                if word_image:
                    # Display the cropped word image
                    ui.image(word_image).classes("word-image").style("max-width: 70px; max-height: 40px; border: 1px solid #ddd; border-radius: 2px;")
                else:
                    # Placeholder for missing image
                    with ui.card().classes("text-center").style("width: 70px; height: 30px; background-color: #f9f9f9;"):
                        ui.icon("image_not_supported").classes("text-grey-4").style("font-size: 16px; margin-top: 6px;")
            
            # OCR text column
            with ui.column().classes("q-ml-sm").style("min-width: 120px; flex: 1;"):
                if word_match.ocr_text.strip():
                    ocr_element = ui.label(word_match.ocr_text).classes(f"{word_match.css_class}")
                    tooltip_content = self._create_word_tooltip(word_match)
                    if tooltip_content:
                        ocr_element.tooltip(tooltip_content).classes("word-tooltip")
                else:
                    ui.label("[empty]").classes("text-grey-4 text-italic")
            
            # Ground Truth text column  
            with ui.column().classes("q-ml-sm").style("min-width: 120px; flex: 1;"):
                if word_match.ground_truth_text.strip():
                    gt_element = ui.label(word_match.ground_truth_text).classes(f"{word_match.css_class}")
                    tooltip_content = self._create_word_tooltip(word_match)
                    if tooltip_content:
                        gt_element.tooltip(tooltip_content).classes("word-tooltip")
                else:
                    ui.label("[no GT]").classes("text-grey-4 text-italic")
            
            # Match status column
            with ui.column().classes("items-center q-ml-sm").style("min-width: 60px; max-width: 60px;"):
                status_icon = self._get_status_icon(word_match.match_status.value)
                status_color = self._get_status_color(word_match.match_status.value)
                ui.icon(status_icon).classes(f"text-{status_color}").style("font-size: 18px;")
                if word_match.fuzz_score is not None:
                    ui.label(f"{word_match.fuzz_score:.2f}").classes("text-caption text-grey-6")
    
    def _create_word_text_display(self, word_matches, text_type):
        """Create a display of words with appropriate coloring."""
        if not word_matches:
            ui.label("No words found").classes("text-grey-5 text-center q-pa-sm")
            return
            
        with ui.row().classes("q-gutter-xs").style("flex-wrap: wrap; line-height: 1.8;"):
            for word_match in word_matches:
                if text_type == "ocr":
                    text = word_match.ocr_text
                else:  # gt
                    text = word_match.ground_truth_text
                
                if not text.strip():
                    # Show placeholder for missing text
                    placeholder_text = "[empty]" if text_type == "ocr" else "[no GT]"
                    word_element = ui.label(placeholder_text).classes("text-grey-4 text-italic")
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
    
    def _get_word_image(self, word_match):
        """Get cropped word image as base64 data URL."""
        try:
            # Get the current page from the view model to access page image
            if not self.view_model.line_matches:
                return None
            
            # Find the line match that contains this word match
            # Use identity comparison instead of equality to avoid numpy array issues
            line_match = None
            for lm in self.view_model.line_matches:
                for wm in lm.word_matches:
                    if wm is word_match:  # Use 'is' instead of 'in' to avoid __eq__ comparison
                        line_match = lm
                        break
                if line_match:
                    break
                    
            if not line_match or line_match.page_image is None:
                return None
                
            # Get cropped image from word match
            try:
                cropped_img = word_match.get_cropped_image(line_match.page_image)
                if cropped_img is None:
                    return None
            except Exception as e:
                logger.debug(f"Error cropping word image: {e}")
                return None
            
            # Convert to base64 data URL for display in browser
            import cv2
            import base64
            
            # Encode image as PNG
            _, buffer = cv2.imencode('.png', cropped_img)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.debug(f"Error creating word image: {e}")
            return None
    
    def _get_status_color(self, status: str) -> str:
        """Get color class for match status."""
        color_map = {
            "exact": "green-6",
            "fuzzy": "orange-6", 
            "mismatch": "red-6",
            "unmatched_ocr": "purple-6",
            "unmatched_gt": "blue-6"
        }
        return color_map.get(status, "grey-6")
    
    def _get_status_icon(self, status: str) -> str:
        """Get icon for match status."""
        icon_map = {
            "exact": "check_circle",
            "fuzzy": "adjust",
            "mismatch": "cancel", 
            "unmatched_ocr": "help",
            "unmatched_gt": "info"
        }
        return icon_map.get(status, "circle")
    
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
