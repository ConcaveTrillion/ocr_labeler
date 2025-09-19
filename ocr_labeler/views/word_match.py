"""Word matching view component for displaying OCR vs Ground Truth comparisons with color coding."""

from __future__ import annotations

import logging

from nicegui import ui
from pd_book_tools.ocr.page import Page

from ..models.word_match_model import MatchStatus
from ..models.word_match_view_model import WordMatchViewModel

logger = logging.getLogger(__name__)


class WordMatchView:
    """View component for displaying word-level OCR vs Ground Truth matching with color coding."""

    def __init__(self, copy_gt_to_ocr_callback=None):
        self.view_model = WordMatchViewModel()
        self.container = None
        self.summary_label = None
        self.lines_container = None
        self.filter_selector = None
        self.show_only_mismatches = True  # Default to showing only mismatched lines
        self.copy_gt_to_ocr_callback = copy_gt_to_ocr_callback

    def build(self):
        """Build the UI components."""
        with ui.column().classes("full-width full-height") as container:
            # Header card with summary stats and filter controls
            with ui.card():
                with ui.column():
                    # Summary stats row
                    with ui.row().classes("items-center"):
                        ui.icon("analytics")
                        self.summary_label = ui.label("No matches to display")

                    # Filter controls row
                    with ui.row().classes("items-center"):
                        ui.icon("filter_list")
                        self.filter_selector = ui.toggle(
                            options=["Mismatched Lines", "All Lines"],
                            value="Mismatched Lines",
                        )
                        self.filter_selector.on_value_change(self._on_filter_change)

            # Scrollable container for word matches
            with ui.scroll_area().classes("fit"):
                self.lines_container = ui.column()

        self.container = container
        return container

    def update_from_page(self, page: Page) -> None:
        """Update the view with matches from a page."""
        try:
            # Update the view model with the new page
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
            f"🔵 {stats['unmatched_gt']} unmatched GT • "
            f"⚫ {stats['unmatched_ocr']} unmatched OCR • "
            f"🎯 {stats['match_percentage']:.1f}% match rate"
        )
        self.summary_label.set_text(summary_text)

    def _update_lines_display(self):
        """Update the lines display with word matches."""
        logger.info("_update_lines_display called")
        if not self.lines_container:
            logger.info("No lines_container, returning")
            return

        # Clear existing content
        self.lines_container.clear()

        if not self.view_model.line_matches:
            logger.info("No line matches in view model")
            with self.lines_container:
                with ui.card():
                    with ui.card_section():
                        ui.icon("info")
                        ui.label("No line matches found")
                        ui.label(
                            "Load a page with OCR and ground truth to see word comparisons"
                        )
            return

        # Filter lines based on current selection
        lines_to_display = self._filter_lines_for_display()

        if not lines_to_display:
            logger.info("No lines to display after filtering")
            with self.lines_container:
                with ui.card():
                    with ui.card_section():
                        ui.icon("filter_list_off")
                        ui.label("No lines match the current filter")
                        if self.show_only_mismatches:
                            ui.label(
                                "All lines have perfect matches. Try selecting 'All lines' to see them."
                            )
            return

        # Display filtered line matches in cards
        logger.info(f"Displaying {len(lines_to_display)} line matches")
        with self.lines_container:
            for line_match in lines_to_display:
                self._create_line_card(line_match)

    def _create_line_card(self, line_match):
        """Create a card display for a single line match."""
        with ui.column():
            # Color background bar based on overall match status
            status_classes = self._get_status_classes(
                line_match.overall_match_status.value
            )
            with ui.row().classes(f"full-width p-2 rounded {status_classes}"):
                # Header with line info and status
                with ui.row().classes("items-center justify-between"):
                    # Left side: Line info and stats
                    with ui.row().classes("items-center"):
                        ui.label(f"Line {line_match.line_index + 1}")
                        ui.icon("bar_chart")
                        stats_items = [
                            f"✓ {line_match.exact_match_count}",
                            f"⚠ {line_match.fuzzy_match_count}",
                            f"✗ {line_match.mismatch_count}",
                        ]
                        if line_match.unmatched_gt_count > 0:
                            stats_items.append(f"🔵 {line_match.unmatched_gt_count}")
                        if line_match.unmatched_ocr_count > 0:
                            stats_items.append(f"⚫ {line_match.unmatched_ocr_count}")
                        ui.label(" • ".join(stats_items))

                    # Right side: Action button (only if not 100% match)
                    logger.info(
                        f"Line {line_match.line_index}: status={line_match.overall_match_status}, callback={self.copy_gt_to_ocr_callback is not None}"
                    )
                    if (
                        line_match.overall_match_status != MatchStatus.EXACT
                        and self.copy_gt_to_ocr_callback
                    ):
                        logger.info(
                            f"Adding GT→OCR button for line {line_match.line_index}"
                        )
                        with ui.row():
                            ui.button(
                                "GT→OCR", icon="content_copy", color="primary"
                            ).props("size=sm").tooltip(
                                "Copy ground truth text to OCR text for all words in this line"
                            ).on_click(
                                lambda: self._handle_copy_gt_to_ocr(
                                    line_match.line_index
                                )
                            )
                    else:
                        logger.info(
                            f"Not adding button for line {line_match.line_index}: status={line_match.overall_match_status}, has_callback={self.copy_gt_to_ocr_callback is not None}"
                        )
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

        # Debug: Log the match statuses we're displaying
        match_statuses = [wm.match_status.value for wm in line_match.word_matches]
        logger.debug(f"Word match statuses: {match_statuses}")

        with ui.row():
            # Create a column for each word
            for word_idx, word_match in enumerate(line_match.word_matches):
                logger.debug(
                    f"Creating column {word_idx} for word match: OCR='{word_match.ocr_text}', GT='{word_match.ground_truth_text}', Status={word_match.match_status.value}"
                )

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
            # Unmatched GT words don't have images since they don't have word objects
            if word_match.match_status == MatchStatus.UNMATCHED_GT:
                ui.icon("text_fields").classes("text-blue-600").style("height: 2.25em")
            else:
                try:
                    word_image = self._get_word_image(word_match)
                except Exception as e:
                    logger.error(f"Error getting word image: {e}")
                    word_image = None
                    ui.icon("error").classes("text-red-600").style("height: 2.25em")
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
                # Show different placeholders based on match status
                if word_match.match_status == MatchStatus.UNMATCHED_GT:
                    ui.label("[missing]").classes("text-blue-600")
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
        status_color_classes = self._get_status_color_classes(
            word_match.match_status.value
        )

        with ui.row():
            with ui.column():
                ui.icon(status_icon).classes(status_color_classes)
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
            import base64

            import cv2

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

    def _get_status_classes(self, status: str) -> str:
        """Get CSS classes for match status background."""
        class_map = {
            "exact": "bg-green-100",  # Light green for exact matches
            "fuzzy": "bg-yellow-100",  # Light yellow for fuzzy matches
            "mismatch": "bg-red-100",  # Light red for mismatches
            "unmatched_ocr": "bg-gray-100",  # Light gray for unmatched OCR
            "unmatched_gt": "bg-blue-100",  # Light blue for unmatched GT
        }
        return class_map.get(status, "bg-gray-50")  # Default light gray

    def _get_status_color_classes(self, status: str) -> str:
        """Get Tailwind CSS classes for status icon colors."""
        color_class_map = {
            "exact": "text-green-600",  # Green for exact matches
            "fuzzy": "text-yellow-600",  # Yellow/amber for fuzzy matches
            "mismatch": "text-red-600",  # Red for mismatches
            "unmatched_ocr": "text-gray-500",  # Gray for unmatched OCR
            "unmatched_gt": "text-blue-600",  # Blue for unmatched ground truth
        }
        return color_class_map.get(status, "text-gray-400")  # Default gray

    def set_fuzz_threshold(self, threshold: float):
        """Set the fuzzy matching threshold."""
        self.view_model.fuzz_threshold = threshold
        # Note: Would need to trigger a refresh of the current page to see changes

    def _on_filter_change(self, event):
        """Handle filter selection change."""
        logger.info(f"Filter change event: {event}")
        logger.info(f"Filter selector value: {self.filter_selector.value}")
        self.show_only_mismatches = self.filter_selector.value == "Mismatched Lines"
        logger.info(f"Show only mismatches: {self.show_only_mismatches}")
        self._update_lines_display()

    def _filter_lines_for_display(self):
        """Filter lines based on current filter setting."""
        logger.info(
            f"Filtering lines. Show only mismatches: {self.show_only_mismatches}"
        )
        logger.info(f"Total line matches: {len(self.view_model.line_matches)}")

        if not self.show_only_mismatches:
            # Show all lines
            logger.info("Returning all lines")
            return self.view_model.line_matches
        else:
            # Show only lines with mismatches (any word that's not an exact match)
            # This includes fuzzy matches, mismatches, unmatched OCR, and unmatched GT
            filtered_lines = []
            for line_match in self.view_model.line_matches:
                has_mismatch = any(
                    wm.match_status != MatchStatus.EXACT
                    for wm in line_match.word_matches
                )
                if has_mismatch:
                    filtered_lines.append(line_match)
            logger.info(f"Filtered to {len(filtered_lines)} lines with mismatches")
            return filtered_lines

    def _handle_copy_gt_to_ocr(self, line_index: int):
        """Handle the GT→OCR button click."""
        if self.copy_gt_to_ocr_callback:
            try:
                success = self.copy_gt_to_ocr_callback(line_index)
                if success:
                    ui.notify(
                        f"Copied ground truth to OCR text for line {line_index + 1}",
                        type="positive",
                    )
                else:
                    ui.notify(
                        f"No ground truth text found to copy in line {line_index + 1}",
                        type="warning",
                    )
            except Exception as e:
                logger.exception(f"Error copying GT→OCR for line {line_index}: {e}")
                ui.notify(f"Error copying GT→OCR: {e}", type="negative")
        else:
            ui.notify("Copy function not available", type="warning")

    def clear(self):
        """Clear the display."""
        if self.lines_container:
            self.lines_container.clear()
        if self.summary_label:
            self.summary_label.set_text("No matches to display")
