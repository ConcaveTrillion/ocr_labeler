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
            with ui.card():
                with ui.row():
                    ui.icon("analytics")
                    self.summary_label = ui.label("No matches to display")

            # Scrollable container for word matches
            with ui.scroll_area().classes("fit"):
                self.lines_container = ui.column()

        self.container = container
        return container

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
        if stats["total_words"] == 0:
            self.summary_label.set_text("Ready to analyze word matches")
            return

        summary_text = (
            f"📊 {stats['total_words']} words • "
            f"✅ {stats['exact_matches']} exact ({stats['exact_percentage']:.1f}%) • "
            f"⚠️ {stats['fuzzy_matches']} fuzzy • "
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
                with ui.card():
                    with ui.card_section():
                        ui.icon("info")
                        ui.label("No line matches found")
                        ui.label(
                            "Load a page with OCR and ground truth to see word comparisons"
                        )
            return

        # Display each line match in cards
        with self.lines_container:
            for line_match in self.view_model.line_matches:
                self._create_line_card(line_match)

    def _create_line_card(self, line_match):
        """Create a card display for a single line match."""
        with ui.column():
            with ui.row():
                # Header with line info and status
                with ui.column():
                    with ui.row():
                        ui.icon("format_list_numbered")
                        ui.label(f"Line {line_match.line_index + 1}")
                    # Statistics section in a separate area
                    with ui.row():
                        ui.icon("bar_chart")
                        stats_items = [
                            f"✓ {line_match.exact_match_count}",
                            f"⚠ {line_match.fuzzy_match_count}",
                            f"✗ {line_match.mismatch_count}",
                        ]
                        ui.label(" • ".join(stats_items))
                    # with ui.row():
                    #     # Status chip
                    #     ui.chip(
                    #         line_match.overall_match_status.value.title(),
                    #         icon=self._get_status_icon(line_match.overall_match_status.value)
                    #     )

            # Card content with word comparison table
            with ui.row():
                # Word comparison table
                with ui.column():
                    self._create_word_comparison_table(line_match)

    def _create_word_comparison_table(self, line_match):
        """Create a table layout with each column representing one complete word item."""
        if not line_match.word_matches:
            ui.label("No words found")
            return

        logger.debug(
            f"Creating word comparison table with {len(line_match.word_matches)} word matches"
        )

        with ui.row():
            # Create a column for each word
            for word_match in line_match.word_matches:
                with ui.column():
                    # Image cell
                    self._create_image_cell(word_match)
                    # OCR text cell
                    self._create_ocr_cell(word_match)
                    # Ground Truth text cell
                    self._create_gt_cell(word_match)
                    # Status cell
                    self._create_status_cell(word_match)

    def _create_image_cell(self, word_match):
        """Create image cell for a word."""
        with ui.row().classes("fit"):
            word_image = self._get_word_image(word_match)
            if word_image:
                ui.interactive_image(word_image).style("height: 2.25em")
            else:
                ui.icon("image_not_supported")

    def _create_ocr_cell(self, word_match):
        """Create OCR text cell for a word."""
        with ui.row():
            if word_match.ocr_text.strip():
                ocr_element = ui.label(word_match.ocr_text)
                tooltip_content = self._create_word_tooltip(word_match)
                if tooltip_content:
                    ocr_element.tooltip(tooltip_content)
            else:
                ui.label("[empty]")

    def _create_gt_cell(self, word_match):
        """Create Ground Truth text cell for a word."""
        with ui.row():
            if word_match.ground_truth_text.strip():
                gt_element = ui.label(word_match.ground_truth_text)
                tooltip_content = self._create_word_tooltip(word_match)
                if tooltip_content:
                    gt_element.tooltip(tooltip_content)
            else:
                ui.label("[no GT]")

    def _create_status_cell(self, word_match):
        """Create status cell for a word."""
        status_icon = self._get_status_icon(word_match.match_status.value)

        with ui.row():
            with ui.column():
                ui.icon(status_icon)
                if word_match.fuzz_score is not None:
                    ui.label(f"{word_match.fuzz_score:.2f}")

    def _create_word_text_display(self, word_matches, text_type):
        """Create a display of words with appropriate coloring."""
        if not word_matches:
            ui.label("No words found")
            return

        with ui.row():
            for word_match in word_matches:
                if text_type == "ocr":
                    text = word_match.ocr_text
                else:  # gt
                    text = word_match.ground_truth_text

                if not text.strip():
                    # Show placeholder for missing text
                    placeholder_text = "[empty]" if text_type == "ocr" else "[no GT]"
                    word_element = ui.label(placeholder_text)
                    continue

                # Create tooltip content
                tooltip_content = self._create_word_tooltip(word_match)

                # Create word element with tooltip
                word_element = ui.label(text)
                if tooltip_content:
                    word_element.tooltip(tooltip_content)

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
                    if (
                        wm is word_match
                    ):  # Use 'is' instead of 'in' to avoid __eq__ comparison
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
            _, buffer = cv2.imencode(".png", cropped_img)
            img_base64 = base64.b64encode(buffer).decode("utf-8")

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.debug(f"Error creating word image: {e}")
            return None

    def _get_status_icon(self, status: str) -> str:
        """Get icon for match status."""
        icon_map = {
            "exact": "check_circle",
            "fuzzy": "warning",  # Changed from "adjust" to avoid confusion with exact match
            "mismatch": "cancel",
            "unmatched_ocr": "help",
            "unmatched_gt": "info",
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
