"""Word matching view component for displaying OCR vs Ground Truth comparisons with color coding."""

from __future__ import annotations

import logging
from typing import Optional

from nicegui import events, ui
from pd_book_tools.ocr.page import Page

from ....models.line_match_model import LineMatch
from ....models.word_match_model import MatchStatus
from ....viewmodels.project.word_match_view_model import WordMatchViewModel

logger = logging.getLogger(__name__)


class WordMatchView:
    """View component for displaying word-level OCR vs Ground Truth matching with color coding."""

    def __init__(
        self,
        copy_gt_to_ocr_callback=None,
        copy_ocr_to_gt_callback=None,
        merge_lines_callback=None,
        delete_lines_callback=None,
        merge_paragraphs_callback=None,
        delete_paragraphs_callback=None,
        split_paragraph_after_line_callback=None,
        split_paragraph_with_selected_lines_callback=None,
        delete_words_callback=None,
        merge_word_left_callback=None,
        merge_word_right_callback=None,
        split_word_callback=None,
        edit_word_ground_truth_callback=None,
        notify_callback=None,
    ):
        logger.debug(
            "Initializing WordMatchView with copy_gt_to_ocr_callback=%s, copy_ocr_to_gt_callback=%s",
            copy_gt_to_ocr_callback is not None,
            copy_ocr_to_gt_callback is not None,
        )
        self.view_model = WordMatchViewModel()
        self.container = None
        self.summary_label = None
        self.lines_container = None
        self.filter_selector = None
        self.show_only_mismatches = True  # Default to showing only mismatched lines
        self.copy_gt_to_ocr_callback = copy_gt_to_ocr_callback
        self.copy_ocr_to_gt_callback = copy_ocr_to_gt_callback
        self.merge_lines_callback = merge_lines_callback
        self.delete_lines_callback = delete_lines_callback
        self.merge_paragraphs_callback = merge_paragraphs_callback
        self.delete_paragraphs_callback = delete_paragraphs_callback
        self.split_paragraph_after_line_callback = split_paragraph_after_line_callback
        self.split_paragraph_with_selected_lines_callback = (
            split_paragraph_with_selected_lines_callback
        )
        self.delete_words_callback = delete_words_callback
        self.merge_word_left_callback = merge_word_left_callback
        self.merge_word_right_callback = merge_word_right_callback
        self.split_word_callback = split_word_callback
        self.edit_word_ground_truth_callback = edit_word_ground_truth_callback
        self.selected_line_indices: set[int] = set()
        self.selected_word_indices: set[tuple[int, int]] = set()
        self.selected_paragraph_indices: set[int] = set()
        self._word_split_fractions: dict[tuple[int, int], float] = {}
        self._word_split_marker_x: dict[tuple[int, int], float] = {}
        self._word_split_image_refs: dict[tuple[int, int], object] = {}
        self._word_split_image_sizes: dict[tuple[int, int], tuple[float, float]] = {}
        self._word_split_button_refs: dict[tuple[int, int], object] = {}
        self._word_gt_input_refs: dict[tuple[int, int], object] = {}
        self._selection_change_callback = None
        self._paragraph_selection_change_callback = None
        self.merge_lines_button = None
        self.delete_lines_button = None
        self.merge_paragraphs_button = None
        self.delete_paragraphs_button = None
        self.split_paragraph_after_line_button = None
        self.split_paragraph_by_selection_button = None
        self.delete_words_button = None
        self.notify_callback = notify_callback
        self._last_display_signature = None
        self._display_update_call_count = 0
        self._display_update_render_count = 0
        self._display_update_skip_count = 0
        logger.debug("WordMatchView initialization complete")

    def _safe_notify(self, message: str, type_: str = "info"):
        """Safely call ui.notify, catching context errors during navigation."""
        if self.notify_callback is not None:
            try:
                self.notify_callback(message, type_)
                return
            except Exception:
                logger.debug(
                    "Notify callback failed; falling back to ui.notify", exc_info=True
                )

        try:
            ui.notify(message, type=type_)
        except RuntimeError as e:
            # Parent element deleted during navigation - this is expected
            if "parent element" in str(e) and "deleted" in str(e):
                logger.debug(
                    f"Skipping notification during navigation cleanup: {message}"
                )
            else:
                raise

    def _is_disposed_ui_error(self, error: RuntimeError) -> bool:
        """Return True when runtime error indicates expected UI teardown race."""
        message = str(error).lower()
        return "client this element belongs to has been deleted" in message or (
            "parent element" in message and "deleted" in message
        )

    def build(self):
        """Build the UI components."""
        logger.debug("Building WordMatchView UI components")
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

                    # Paragraph operations row
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Paragraph Operations").classes(
                            "text-sm font-semibold"
                        )
                        self.merge_paragraphs_button = (
                            ui.button(
                                "Merge",
                                icon="call_merge",
                                on_click=self._handle_merge_selected_paragraphs,
                            )
                            .props("size=sm")
                            .tooltip("Merge selected paragraphs")
                        )
                        self.delete_paragraphs_button = (
                            ui.button(
                                "Delete",
                                icon="delete",
                                color="negative",
                                on_click=self._handle_delete_selected_paragraphs,
                            )
                            .props("size=sm")
                            .tooltip("Delete selected paragraphs")
                        )
                        self.split_paragraph_after_line_button = (
                            ui.button(
                                "Split After",
                                icon="call_split",
                                on_click=self._handle_split_paragraph_after_selected_line,
                            )
                            .props("size=sm")
                            .tooltip(
                                "Split the containing paragraph immediately after the selected line"
                            )
                        )
                        self.split_paragraph_by_selection_button = (
                            ui.button(
                                "Split Select",
                                icon="call_split",
                                on_click=self._handle_split_paragraph_by_selected_lines,
                            )
                            .props("size=sm")
                            .tooltip(
                                "Split one paragraph into selected and unselected lines"
                            )
                        )

                    # Line operations row
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Line Operations").classes("text-sm font-semibold")
                        self.merge_lines_button = (
                            ui.button(
                                "Merge",
                                icon="call_merge",
                                on_click=self._handle_merge_selected_lines,
                            )
                            .props("size=sm")
                            .tooltip(
                                "Merge selected lines into the first selected line"
                            )
                        )
                        self.delete_lines_button = (
                            ui.button(
                                "Delete",
                                icon="delete",
                                color="negative",
                                on_click=self._handle_delete_selected_lines,
                            )
                            .props("size=sm")
                            .tooltip("Delete selected lines")
                        )

                    # Word operations row
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Word Operations").classes("text-sm font-semibold")
                        self.delete_words_button = (
                            ui.button(
                                "Delete",
                                icon="delete",
                                color="negative",
                                on_click=self._handle_delete_selected_words,
                            )
                            .props("size=sm")
                            .tooltip("Delete selected words")
                        )

            # Scrollable container for word matches
            with ui.scroll_area().classes("fit"):
                self.lines_container = ui.column()

        self.container = container
        logger.debug("WordMatchView UI build complete, container created")
        return container

    def update_from_page(self, page: Page) -> None:
        """Update the view with matches from a page."""
        try:
            # Defensive logging for test compatibility
            block_count = (
                len(page.blocks)
                if (page and hasattr(page, "blocks") and page.blocks)
                else 0
            )
            logger.debug(
                "Updating WordMatchView from page with %d blocks",
                block_count,
            )
        except (TypeError, AttributeError):
            logger.debug("Updating WordMatchView from page (block count unavailable)")

        try:
            # Update the view model with the new page
            self.view_model.update_from_page(page)
            # Update the UI
            self._update_summary()
            self._update_lines_display()
            logger.debug("WordMatchView update complete")

        except RuntimeError as e:
            if self._is_disposed_ui_error(e):
                logger.debug("Skipping word match update during UI disposal: %s", e)
                return
            logger.exception(f"Error updating word match view: {e}")
        except Exception as e:
            logger.exception(f"Error updating word match view: {e}")

    def _update_summary(self):
        """Update the summary statistics display."""
        logger.debug("Updating summary statistics")
        if not self.summary_label:
            logger.debug("No summary_label available, skipping update")
            return

        stats = self.view_model.get_summary_stats()
        logger.debug("Retrieved summary stats: %s", stats)
        if stats["total_words"] == 0:
            self.summary_label.set_text("Ready to analyze word matches")
            logger.debug("Set summary to 'Ready to analyze' (no words)")
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
        logger.debug("Updated summary text: %s", summary_text)

    def _update_lines_display(self):
        """Update the lines display with word matches."""
        self._display_update_call_count += 1
        logger.info(
            "_update_lines_display called (call=%d, rendered=%d, skipped=%d)",
            self._display_update_call_count,
            self._display_update_render_count,
            self._display_update_skip_count,
        )
        if not self.lines_container:
            logger.info("No lines_container, returning")
            return

        available_line_indices = {
            line_match.line_index for line_match in self.view_model.line_matches
        }
        if self.selected_line_indices:
            self.selected_line_indices.intersection_update(available_line_indices)
        if self.selected_word_indices:
            word_count_by_line = {
                line_match.line_index: len(line_match.word_matches)
                for line_match in self.view_model.line_matches
            }
            self.selected_word_indices = {
                (line_index, word_index)
                for line_index, word_index in self.selected_word_indices
                if line_index in available_line_indices
                and 0 <= word_index < word_count_by_line.get(line_index, 0)
            }
        for line_index in available_line_indices:
            self._sync_line_selection_from_words(line_index)
        valid_split_keys = {
            (line_match.line_index, word_match.word_index)
            for line_match in self.view_model.line_matches
            for word_match in line_match.word_matches
            if word_match.word_index is not None
        }
        self._word_split_fractions = {
            key: value
            for key, value in self._word_split_fractions.items()
            if key in valid_split_keys
        }
        self._word_split_marker_x = {
            key: value
            for key, value in self._word_split_marker_x.items()
            if key in valid_split_keys
        }
        available_paragraph_indices = {
            line_match.paragraph_index
            for line_match in self.view_model.line_matches
            if getattr(line_match, "paragraph_index", None) is not None
        }
        self.selected_paragraph_indices.intersection_update(available_paragraph_indices)
        self._update_action_button_state()

        display_signature = self._compute_display_signature()
        if display_signature == self._last_display_signature:
            self._display_update_skip_count += 1
            logger.info(
                "Skipping lines display refresh; no visible changes detected "
                "(call=%d, rendered=%d, skipped=%d)",
                self._display_update_call_count,
                self._display_update_render_count,
                self._display_update_skip_count,
            )
            logger.debug("Skipping lines display refresh; no visible changes detected")
            return

        # Clear existing content
        self.lines_container.clear()
        self._word_split_image_refs = {}
        self._word_split_image_sizes = {}
        self._word_split_button_refs = {}
        self._word_gt_input_refs = {}

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
            self._display_update_render_count += 1
            self._last_display_signature = display_signature
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
            self._display_update_render_count += 1
            self._last_display_signature = display_signature
            return

        # Display filtered line matches in collapsible paragraph sections
        logger.info(f"Displaying {len(lines_to_display)} line matches")
        with self.lines_container:
            for (
                paragraph_index,
                paragraph_line_matches,
            ) in self._group_lines_by_paragraph(lines_to_display):
                with ui.expansion(
                    self._format_paragraph_label(paragraph_index),
                    value=True,
                    icon="subject",
                ).classes("full-width"):
                    if paragraph_index is not None:
                        with ui.row().classes("items-center"):
                            ui.checkbox(
                                value=paragraph_index in self.selected_paragraph_indices
                            ).props("size=sm").on_value_change(
                                lambda event, index=paragraph_index: (
                                    self._on_paragraph_selection_change(
                                        index,
                                        bool(event.value),
                                    )
                                )
                            )
                            ui.label("Select paragraph")
                    with ui.column().classes("full-width"):
                        for line_match in paragraph_line_matches:
                            self._create_line_card(line_match)

        self._display_update_render_count += 1
        self._last_display_signature = display_signature

    def _compute_display_signature(self):
        """Return a stable signature for visible line-match content."""
        line_signatures = []
        for line_match in self.view_model.line_matches:
            word_signatures = tuple(
                (
                    word_match.match_status.value,
                    word_match.ocr_text,
                    word_match.ground_truth_text,
                    round(word_match.fuzz_score, 6)
                    if word_match.fuzz_score is not None
                    else None,
                )
                for word_match in line_match.word_matches
            )

            line_signatures.append(
                (
                    line_match.line_index,
                    getattr(line_match, "paragraph_index", None),
                    line_match.overall_match_status.value,
                    line_match.exact_match_count,
                    line_match.fuzzy_match_count,
                    line_match.mismatch_count,
                    line_match.unmatched_gt_count,
                    line_match.unmatched_ocr_count,
                    word_signatures,
                )
            )

        return (
            self.show_only_mismatches,
            tuple(sorted(self.selected_line_indices)),
            tuple(sorted(self.selected_word_indices)),
            tuple(sorted(self.selected_paragraph_indices)),
            tuple(line_signatures),
        )

    def _group_lines_by_paragraph(self, line_matches: list[LineMatch]):
        """Group line matches by paragraph index, keeping unassigned lines last."""
        grouped: dict[Optional[int], list[LineMatch]] = {}
        for line_match in line_matches:
            paragraph_index = getattr(line_match, "paragraph_index", None)
            grouped.setdefault(paragraph_index, []).append(line_match)

        ordered_groups = []
        for paragraph_index in sorted(k for k in grouped if k is not None):
            ordered_groups.append((paragraph_index, grouped[paragraph_index]))

        if None in grouped:
            ordered_groups.append((None, grouped[None]))

        return ordered_groups

    @staticmethod
    def _format_paragraph_label(paragraph_index: Optional[int]) -> str:
        """Return a user-facing label for a paragraph index."""
        if paragraph_index is None:
            return "Paragraph Unassigned"
        return f"Paragraph {paragraph_index + 1}"

    def set_selection_change_callback(self, callback) -> None:
        """Register callback invoked when selected words change."""
        self._selection_change_callback = callback

    def set_paragraph_selection_change_callback(self, callback) -> None:
        """Register callback invoked when selected paragraphs change."""
        self._paragraph_selection_change_callback = callback

    def _emit_selection_changed(self) -> None:
        """Emit selected words to listener (for image overlay sync)."""
        if self._selection_change_callback is None:
            return
        try:
            self._selection_change_callback(set(self.selected_word_indices))
        except Exception:
            logger.debug("Selection change callback failed", exc_info=True)

    def _emit_paragraph_selection_changed(self) -> None:
        """Emit selected paragraphs to listener (for image overlay sync)."""
        if self._paragraph_selection_change_callback is None:
            return
        try:
            self._paragraph_selection_change_callback(
                set(self.selected_paragraph_indices)
            )
        except Exception:
            logger.debug("Paragraph selection callback failed", exc_info=True)

    def _line_match_by_index(self, line_index: int):
        for line_match in self.view_model.line_matches:
            if line_match.line_index == line_index:
                return line_match
        return None

    def _line_word_keys(self, line_index: int) -> set[tuple[int, int]]:
        line_match = self._line_match_by_index(line_index)
        if line_match is None:
            return set()
        return {
            (line_index, word_index)
            for word_index, _ in enumerate(line_match.word_matches)
        }

    def _is_line_fully_word_selected(self, line_index: int) -> bool:
        keys = self._line_word_keys(line_index)
        return bool(keys) and keys.issubset(self.selected_word_indices)

    def _is_line_checked(self, line_index: int) -> bool:
        return (
            line_index in self.selected_line_indices
            or self._is_line_fully_word_selected(line_index)
        )

    def _sync_line_selection_from_words(self, line_index: int) -> None:
        if self._is_line_fully_word_selected(line_index):
            self.selected_line_indices.add(line_index)
        else:
            self.selected_line_indices.discard(line_index)

    def _create_line_card(self, line_match):
        """Create a card display for a single line match."""
        logger.debug(
            "Creating line card for line %d with status %s",
            line_match.line_index,
            line_match.overall_match_status.value,
        )
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
                        ui.checkbox(
                            value=self._is_line_checked(line_match.line_index)
                        ).props("size=sm").on_value_change(
                            lambda event, index=line_match.line_index: (
                                self._on_line_selection_change(
                                    index,
                                    bool(event.value),
                                )
                            )
                        )
                        ui.label(f"Line {line_match.line_index + 1}")
                        ui.label(
                            self._format_paragraph_label(
                                getattr(line_match, "paragraph_index", None)
                            )
                        ).classes("text-caption")
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

                    # Right side: Action buttons
                    logger.debug(
                        f"Line {line_match.line_index}: status={line_match.overall_match_status}, gt_to_ocr_callback={self.copy_gt_to_ocr_callback is not None}, ocr_to_gt_callback={self.copy_ocr_to_gt_callback is not None}"
                    )
                    with ui.row().classes("items-center"):
                        if (
                            line_match.overall_match_status != MatchStatus.EXACT
                            and self.copy_gt_to_ocr_callback
                        ):
                            logger.debug(
                                f"Adding GT→OCR button for line {line_match.line_index}"
                            )
                            ui.button(
                                "GT→OCR", icon="content_copy", color="primary"
                            ).props("size=sm").tooltip(
                                "Copy ground truth text to OCR text for all words in this line"
                            ).on_click(
                                lambda: self._handle_copy_gt_to_ocr(
                                    line_match.line_index
                                )
                            )

                        if (
                            line_match.overall_match_status != MatchStatus.EXACT
                            and self.copy_ocr_to_gt_callback
                        ):
                            logger.debug(
                                f"Adding OCR→GT button for line {line_match.line_index}"
                            )
                            ui.button(
                                "OCR→GT", icon="content_copy", color="primary"
                            ).props("size=sm").tooltip(
                                "Copy OCR text to ground truth text for all words in this line"
                            ).on_click(
                                lambda: self._handle_copy_ocr_to_gt(
                                    line_match.line_index
                                )
                            )

                        delete_button = (
                            ui.button(icon="delete", color="negative")
                            .props("size=sm flat round")
                            .tooltip("Delete this line")
                        )
                        if self.delete_lines_callback:
                            delete_button.on_click(
                                lambda: self._handle_delete_line(line_match.line_index)
                            )
                        else:
                            delete_button.disabled = True
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
        logger.debug("Line card creation complete for line %d", line_match.line_index)

    def _create_word_comparison_table(self, line_match):
        """Create a table layout with each column representing one complete word item."""
        logger.debug(
            "Creating word comparison table for line %d with %d word matches",
            line_match.line_index,
            len(line_match.word_matches),
        )
        if not line_match.word_matches:
            logger.debug("No word matches found for line %d", line_match.line_index)
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
                    self._create_word_selection_cell(line_match.line_index, word_idx)
                    # Image cell
                    split_word_index = (
                        word_match.word_index
                        if word_match.word_index is not None
                        else -1
                    )
                    self._create_image_cell(
                        line_match.line_index,
                        split_word_index,
                        word_match,
                    )
                    # OCR text cell
                    self._create_ocr_cell(word_match)
                    # Ground Truth text cell
                    self._create_gt_cell(
                        line_match.line_index,
                        split_word_index,
                        word_match,
                    )
                    # Status cell
                    self._create_status_cell(word_match)
                    # Per-word actions
                    self._create_word_actions_cell(
                        line_match.line_index,
                        word_idx,
                        split_word_index,
                        len(line_match.word_matches),
                    )
        logger.debug(
            "Word comparison table creation complete for line %d", line_match.line_index
        )

    def _create_word_selection_cell(self, line_index: int, word_index: int) -> None:
        """Create a selection checkbox for a word column."""
        selection_key = (line_index, word_index)
        with ui.row().classes("items-center"):
            ui.checkbox(value=selection_key in self.selected_word_indices).props(
                "size=xs dense"
            ).tooltip("Select word").on_value_change(
                lambda event, key=selection_key: self._on_word_selection_change(
                    key,
                    bool(event.value),
                )
            )

    def _create_image_cell(
        self,
        line_index: int,
        split_word_index: int,
        word_match,
    ):
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
                    image_source: str | None = None
                    image_width: float | None = None
                    image_height: float | None = None

                    if isinstance(word_image, tuple) and len(word_image) == 3:
                        image_source, image_width, image_height = word_image
                    elif isinstance(word_image, str):
                        image_source = word_image

                    if not image_source:
                        ui.icon("image_not_supported")
                        return

                    image = ui.interactive_image(
                        image_source,
                        events=["mousedown"],
                        on_mouse=lambda event, li=line_index, wi=split_word_index: (
                            self._handle_word_image_click(li, wi, event)
                        ),
                        sanitize=False,
                    ).style("height: 2.25em")
                    if split_word_index >= 0:
                        key = (line_index, split_word_index)
                        self._word_split_image_refs[key] = image
                        if image_width is not None and image_height is not None:
                            self._word_split_image_sizes[key] = (
                                float(image_width),
                                float(image_height),
                            )
                        self._render_word_split_marker(key)
                else:
                    ui.icon("image_not_supported")

    def _create_ocr_cell(self, word_match):
        """Create OCR text cell for a word."""
        with ui.row():
            if word_match.ocr_text.strip():
                ocr_element = ui.label(word_match.ocr_text).classes("monospace")
                tooltip_content = self._create_word_tooltip(word_match)
                if tooltip_content:
                    ocr_element.tooltip(tooltip_content)
            else:
                # Show different placeholders based on match status
                if word_match.match_status == MatchStatus.UNMATCHED_GT:
                    ui.label("[missing]").classes("text-blue-600 monospace")
                else:
                    ui.label("[empty]").classes("monospace")

    def _create_gt_cell(self, line_index: int, word_index: int, word_match):
        """Create Ground Truth text cell for a word."""
        with ui.row():
            if word_index >= 0:
                initial_value = str(word_match.ground_truth_text or "")
                input_element = (
                    ui.input(value=initial_value)
                    .props("dense outlined")
                    .classes("monospace")
                )
                current_key = (line_index, word_index)
                self._word_gt_input_refs[current_key] = input_element
                self._set_word_gt_input_width(
                    input_element,
                    value=initial_value,
                    fallback_text=str(word_match.ocr_text or ""),
                )
                input_element.on_value_change(
                    lambda event: self._handle_word_gt_input_change(
                        input_element,
                        str(event.value or ""),
                        str(word_match.ocr_text or ""),
                    )
                )
                input_element.on(
                    "blur",
                    lambda _event, li=line_index, wi=word_index: (
                        self._commit_word_gt_input_change(
                            li,
                            wi,
                            input_element,
                        )
                    ),
                )
                input_element.on(
                    "keydown.enter",
                    lambda _event, li=line_index, wi=word_index: (
                        self._commit_word_gt_input_change(
                            li,
                            wi,
                            input_element,
                        )
                    ),
                )
                input_element.on(
                    "keydown",
                    lambda event, key=current_key: self._handle_word_gt_keydown(
                        event, key
                    ),
                )
                input_element.enabled = self.edit_word_ground_truth_callback is not None
                tooltip_content = self._create_word_tooltip(word_match)
                if tooltip_content:
                    input_element.tooltip(tooltip_content)
            elif word_match.ground_truth_text.strip():
                gt_element = ui.label(word_match.ground_truth_text).classes("monospace")
                tooltip_content = self._create_word_tooltip(word_match)
                if tooltip_content:
                    gt_element.tooltip(tooltip_content)
            else:
                ui.label("[no GT]").classes("monospace")

    def _handle_word_gt_input_change(
        self,
        input_element,
        ground_truth_text: str,
        fallback_text: str,
    ) -> None:
        """Resize GT input while user types."""
        self._set_word_gt_input_width(
            input_element,
            value=ground_truth_text,
            fallback_text=fallback_text,
        )

    def _commit_word_gt_input_change(
        self,
        line_index: int,
        word_index: int,
        input_element,
    ) -> None:
        """Persist GT edit when focus leaves the input (Quasar blur event)."""
        self._handle_word_gt_edit(
            line_index,
            word_index,
            str(getattr(input_element, "value", "") or ""),
        )

    def _next_word_gt_key(
        self,
        current_key: tuple[int, int],
        reverse: bool = False,
    ) -> tuple[int, int] | None:
        """Return adjacent GT input key in reading order."""
        ordered_keys = sorted(self._word_gt_input_refs.keys())
        if not ordered_keys:
            return None

        try:
            index = ordered_keys.index(current_key)
        except ValueError:
            return None

        next_index = index - 1 if reverse else index + 1
        if next_index < 0 or next_index >= len(ordered_keys):
            return None
        return ordered_keys[next_index]

    def _focus_word_gt_input(self, key: tuple[int, int]) -> None:
        """Move focus to a GT input if available."""
        input_element = self._word_gt_input_refs.get(key)
        if input_element is None:
            return
        try:
            input_element.focus()
        except Exception:
            logger.debug("Failed to focus GT input for key %s", key, exc_info=True)

    def _handle_word_gt_keydown(self, event, current_key: tuple[int, int]) -> None:
        """Handle GT input keyboard navigation keys."""
        event_args = getattr(event, "args", {}) or {}
        if str(event_args.get("key", "")) != "Tab":
            return

        is_reverse = bool(event_args.get("shiftKey", False))
        self._handle_word_gt_tab_navigation(current_key, is_reverse)

    def _handle_word_gt_tab_navigation(
        self,
        current_key: tuple[int, int],
        is_reverse: bool,
    ) -> None:
        """Handle Tab/Shift+Tab navigation between GT inputs."""
        current_input = self._word_gt_input_refs.get(current_key)
        if current_input is None:
            return

        self._commit_word_gt_input_change(current_key[0], current_key[1], current_input)
        target_key = self._next_word_gt_key(current_key, reverse=is_reverse)
        if target_key is None:
            return

        ui.timer(
            0,
            lambda key=target_key: self._focus_word_gt_input(key),
            once=True,
        )

    def _set_word_gt_input_width(
        self,
        input_element,
        value: str,
        fallback_text: str,
    ) -> None:
        """Apply monospace width based on current/fallback text length."""
        width_chars = self._word_gt_input_width_chars(value, fallback_text)
        try:
            input_element.style(
                f"width: {width_chars}ch; min-width: 4ch; max-width: 100%;"
            )
        except Exception:
            logger.debug("Failed to apply GT input width", exc_info=True)

    def _word_gt_input_width_chars(self, value: str, fallback_text: str) -> int:
        """Compute desired GT input width in monospace character units."""
        effective_text = str(value or "") or str(fallback_text or "")
        return max(6, len(effective_text) + 3)

    def _handle_word_gt_edit(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> None:
        """Handle updates to per-word GT text from inline input fields."""
        if self.edit_word_ground_truth_callback is None:
            self._safe_notify(
                "Edit ground truth function not available", type_="warning"
            )
            return

        try:
            success = self.edit_word_ground_truth_callback(
                line_index,
                word_index,
                ground_truth_text,
            )
            if not success:
                self._safe_notify("Failed to update word ground truth", type_="warning")
        except Exception as e:
            logger.exception(
                "Error updating word ground truth (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(
                f"Error updating word ground truth: {e}", type_="negative"
            )

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

    def _create_word_actions_cell(
        self,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_count: int,
    ) -> None:
        """Create per-word action buttons displayed below each word."""
        with ui.row().classes("items-center gap-1"):
            merge_left_button = (
                ui.button(
                    icon="keyboard_arrow_left",
                    on_click=lambda: self._handle_merge_word_left(
                        line_index, word_index
                    ),
                )
                .props("size=xs flat round")
                .tooltip("Merge with left word")
            )
            merge_left_button.disabled = (
                self.merge_word_left_callback is None or word_index <= 0
            )

            merge_right_button = (
                ui.button(
                    icon="keyboard_arrow_right",
                    on_click=lambda: self._handle_merge_word_right(
                        line_index, word_index
                    ),
                )
                .props("size=xs flat round")
                .tooltip("Merge with right word")
            )
            merge_right_button.disabled = (
                self.merge_word_right_callback is None or word_index >= word_count - 1
            )

            delete_button = (
                ui.button(
                    icon="delete",
                    color="negative",
                    on_click=lambda: self._handle_delete_single_word(
                        line_index, word_index
                    ),
                )
                .props("size=xs flat round")
                .tooltip("Delete word")
            )
            delete_button.disabled = self.delete_words_callback is None

            split_button = (
                ui.button(
                    icon="call_split",
                    on_click=lambda: self._handle_split_word(
                        line_index,
                        split_word_index,
                    ),
                )
                .props("size=xs flat round")
                .tooltip("Split word at selected marker")
            )
            if split_word_index >= 0:
                split_key = (line_index, split_word_index)
                self._word_split_button_refs[split_key] = split_button
            split_button.disabled = not self._is_split_action_enabled(
                line_index,
                split_word_index,
            )

    def _line_word_match_by_ocr_index(
        self,
        line_index: int,
        word_index: int,
    ):
        line_match = self._line_match_by_index(line_index)
        if line_match is None:
            return None
        for word_match in line_match.word_matches:
            if word_match.word_index == word_index:
                return word_match
        return None

    def _is_split_action_enabled(self, line_index: int, word_index: int) -> bool:
        if self.split_word_callback is None or word_index < 0:
            return False

        word_match = self._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            return False
        word_text = str(getattr(word_match, "ocr_text", "") or "")
        if len(word_text) < 2:
            return False

        return (line_index, word_index) in self._word_split_fractions

    def _render_word_split_marker(self, split_key: tuple[int, int]) -> None:
        image = self._word_split_image_refs.get(split_key)
        if image is None:
            return

        marker_x = self._word_split_marker_x.get(split_key)
        if marker_x is None:
            try:
                image.content = ""
            except Exception:
                logger.debug("Failed to clear split marker", exc_info=True)
            return

        try:
            _width, height = self._word_split_image_sizes.get(split_key, (0.0, 0.0))
            marker_height = max(1.0, float(height) if height > 0.0 else 1000.0)
            image.content = (
                f'<line x1="{marker_x:.2f}" y1="0" x2="{marker_x:.2f}" y2="{marker_height:.2f}" '
                'stroke="#2563eb" stroke-width="2" pointer-events="none" />'
            )
        except Exception:
            logger.debug("Failed to render split marker", exc_info=True)

    def _handle_word_image_click(
        self,
        line_index: int,
        word_index: int,
        event: events.MouseEventArguments,
    ) -> None:
        if word_index < 0:
            return

        word_match = self._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            return

        split_key = (line_index, word_index)
        image_width = self._word_split_image_sizes.get(split_key, (0.0, 0.0))[0]
        image_x = float(getattr(event, "image_x", -1.0))
        if image_width <= 0.0 or image_x <= 0.0 or image_x >= image_width:
            return

        split_fraction = image_x / image_width
        if split_fraction <= 0.0 or split_fraction >= 1.0:
            return

        self._word_split_fractions[split_key] = split_fraction
        self._word_split_marker_x[split_key] = image_x
        self._render_word_split_marker(split_key)

        split_button = self._word_split_button_refs.get(split_key)
        if split_button is not None:
            split_button.disabled = not self._is_split_action_enabled(
                line_index,
                word_index,
            )

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
        """Get cropped word image as base64 data URL with image dimensions."""
        logger.debug(
            "Getting word image for match with status %s", word_match.match_status.value
        )
        try:
            # Get the current page from the view model to access page image
            if not self.view_model.line_matches:
                logger.debug("No line matches in view model, cannot get word image")
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
                logger.debug("No line match found or no page image available")
                return None

            logger.debug(
                "Found line match with page image, attempting to crop word image"
            )
            # Get cropped image from word match
            try:
                cropped_img = word_match.get_cropped_image(line_match.page_image)
                if cropped_img is None:
                    logger.debug("Cropped image is None")
                    return None
                logger.debug(
                    "Successfully cropped image, shape: %s",
                    cropped_img.shape if hasattr(cropped_img, "shape") else "unknown",
                )
            except Exception as e:
                logger.debug(f"Error cropping word image: {e}")
                return None

            # Convert to base64 data URL for display in browser
            import base64

            import cv2

            # Encode image as PNG
            _, buffer = cv2.imencode(".png", cropped_img)
            img_base64 = base64.b64encode(buffer).decode("utf-8")
            data_url = f"data:image/png;base64,{img_base64}"
            logger.debug(
                "Successfully encoded image as base64 data URL (length: %d)",
                len(data_url),
            )

            height, width = cropped_img.shape[:2]
            return data_url, float(width), float(height)

        except Exception as e:
            logger.debug(f"Error creating word image: {e}")
            return None

    def _get_line_image(self, line_match: "LineMatch") -> Optional[str]:
        """Get cropped line image as base64 data URL.

        Args:
            line_match: The LineMatch object containing the line to crop.

        Returns:
            Base64 data URL string for the cropped line image, or None if unavailable.
        """
        logger.debug(f"Getting line image for line {line_match.line_index}")
        try:
            # Get cropped image from line match
            try:
                cropped_img = line_match.get_cropped_image()
                if cropped_img is None:
                    logger.debug("Cropped line image is None")
                    return None
                logger.debug(
                    "Successfully cropped line image, shape: %s",
                    cropped_img.shape if hasattr(cropped_img, "shape") else "unknown",
                )
            except Exception as e:
                logger.debug(f"Error cropping line image: {e}")
                return None

            # Convert to base64 data URL for display in browser
            import base64

            import cv2

            # Encode image as PNG
            _, buffer = cv2.imencode(".png", cropped_img)
            img_base64 = base64.b64encode(buffer).decode("utf-8")
            data_url = f"data:image/png;base64,{img_base64}"
            logger.debug(
                "Successfully encoded line image as base64 data URL (length: %d)",
                len(data_url),
            )

            return data_url

        except Exception as e:
            logger.debug(f"Error creating line image: {e}")
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
        logger.debug(f"Filter change event triggered: {event}")
        logger.debug(f"Filter selector value: {self.filter_selector.value}")
        self.show_only_mismatches = self.filter_selector.value == "Mismatched Lines"
        logger.debug(f"Show only mismatches set to: {self.show_only_mismatches}")
        self._update_lines_display()
        logger.debug("Filter change handling complete")

    def _on_line_selection_change(self, line_index: int, selected: bool) -> None:
        """Track selected lines for merge workflow."""
        if selected:
            self.selected_line_indices.add(line_index)
            self.selected_word_indices.update(self._line_word_keys(line_index))
        else:
            self.selected_line_indices.discard(line_index)
            self.selected_word_indices.difference_update(
                self._line_word_keys(line_index)
            )
        logger.debug(
            "Line selection changed: line_index=%d selected=%s current_selection=%s",
            line_index,
            selected,
            sorted(self.selected_line_indices),
        )
        self._update_action_button_state()
        self._emit_selection_changed()
        self._update_lines_display()

    def _on_word_selection_change(
        self, selection_key: tuple[int, int], selected: bool
    ) -> None:
        """Track selected words for box/checkbox-driven workflow."""
        if selected:
            self.selected_word_indices.add(selection_key)
        else:
            self.selected_word_indices.discard(selection_key)
        self._sync_line_selection_from_words(selection_key[0])
        logger.debug(
            "Word selection changed: key=%s selected=%s current_words=%s",
            selection_key,
            selected,
            sorted(self.selected_word_indices),
        )
        self._update_action_button_state()
        self._emit_selection_changed()
        self._update_lines_display()

    def _on_paragraph_selection_change(
        self, paragraph_index: int, selected: bool
    ) -> None:
        """Track selected paragraphs for paragraph actions."""
        if selected:
            self.selected_paragraph_indices.add(paragraph_index)
        else:
            self.selected_paragraph_indices.discard(paragraph_index)
        logger.debug(
            "Paragraph selection changed: paragraph_index=%d selected=%s current_selection=%s",
            paragraph_index,
            selected,
            sorted(self.selected_paragraph_indices),
        )
        self._update_action_button_state()
        self._emit_paragraph_selection_changed()
        self._update_lines_display()

    def _get_effective_selected_lines(self) -> list[int]:
        """Return selected lines from both line and word selections."""
        line_selection = set(self.selected_line_indices)
        line_selection.update(
            line_index for line_index, _ in self.selected_word_indices
        )
        return sorted(line_selection)

    def set_selected_words(self, selection: set[tuple[int, int]]) -> None:
        """Set selected words externally (e.g., box selection integration)."""
        self.selected_word_indices = set(selection)
        available_line_indices = {
            line_match.line_index for line_match in self.view_model.line_matches
        }
        self.selected_line_indices = {
            line_index
            for line_index in available_line_indices
            if self._is_line_fully_word_selected(line_index)
        }
        self._update_action_button_state()
        self._emit_selection_changed()
        self._update_lines_display()

    def set_selected_paragraphs(self, selection: set[int]) -> None:
        """Set selected paragraphs externally (e.g., image box selection)."""
        available_paragraph_indices = {
            line_match.paragraph_index
            for line_match in self.view_model.line_matches
            if getattr(line_match, "paragraph_index", None) is not None
        }
        self.selected_paragraph_indices = {
            paragraph_index
            for paragraph_index in selection
            if paragraph_index in available_paragraph_indices
        }
        self._update_action_button_state()
        self._emit_paragraph_selection_changed()
        self._update_lines_display()

    def _update_action_button_state(self) -> None:
        """Enable/disable line and paragraph action buttons based on selection."""
        selected_lines = self._get_effective_selected_lines()
        if self.merge_lines_button is None:
            pass
        else:
            self.merge_lines_button.disabled = (
                self.merge_lines_callback is None or len(selected_lines) < 2
            )

        if self.delete_lines_button is not None:
            self.delete_lines_button.disabled = (
                self.delete_lines_callback is None or len(selected_lines) < 1
            )

        if self.merge_paragraphs_button is not None:
            self.merge_paragraphs_button.disabled = (
                self.merge_paragraphs_callback is None
                or len(self.selected_paragraph_indices) < 2
            )

        if self.delete_paragraphs_button is not None:
            self.delete_paragraphs_button.disabled = (
                self.delete_paragraphs_callback is None
                or len(self.selected_paragraph_indices) < 1
            )

        if self.split_paragraph_after_line_button is not None:
            self.split_paragraph_after_line_button.disabled = (
                self.split_paragraph_after_line_callback is None
                or len(selected_lines) != 1
            )

        if self.split_paragraph_by_selection_button is not None:
            self.split_paragraph_by_selection_button.disabled = (
                self.split_paragraph_with_selected_lines_callback is None
                or len(selected_lines) < 1
            )

        if self.delete_words_button is not None:
            self.delete_words_button.disabled = (
                self.delete_words_callback is None
                or len(self.selected_word_indices) < 1
            )

    def _handle_merge_selected_lines(self):
        """Merge selected lines into the first selected line."""
        if self.merge_lines_callback is None:
            self._safe_notify("Merge function not available", type_="warning")
            return

        selected_indices = self._get_effective_selected_lines()
        if len(selected_indices) < 2:
            self._safe_notify("Select at least two lines to merge", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        # Clear selection before invoking merge callback because merge can trigger
        # synchronous page-state notifications and UI refreshes before callback
        # returns; stale indices may otherwise map to different visible mismatch
        # lines after reindexing.
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        logger.info("Merge requested for selected lines: %s", selected_indices)
        try:
            success = self.merge_lines_callback(selected_indices)
            logger.info(
                "Merge callback completed: selected=%s success=%s",
                selected_indices,
                success,
            )
            if success:
                self._safe_notify(
                    f"Merged {len(selected_indices)} lines", type_="positive"
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to merge selected lines", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception("Error merging selected lines %s: %s", selected_indices, e)
            self._safe_notify(f"Error merging selected lines: {e}", type_="negative")

    def _handle_merge_selected_paragraphs(self):
        """Merge selected paragraphs into the first selected paragraph."""
        if self.merge_paragraphs_callback is None:
            self._safe_notify("Merge paragraph function not available", type_="warning")
            return

        selected_indices = sorted(self.selected_paragraph_indices)
        if len(selected_indices) < 2:
            self._safe_notify(
                "Select at least two paragraphs to merge", type_="warning"
            )
            return

        previous_paragraph_selection = set(self.selected_paragraph_indices)
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_paragraph_selection_changed()
        logger.info("Merge requested for selected paragraphs: %s", selected_indices)
        try:
            success = self.merge_paragraphs_callback(selected_indices)
            logger.info(
                "Merge paragraph callback completed: selected=%s success=%s",
                selected_indices,
                success,
            )
            if success:
                self._safe_notify(
                    f"Merged {len(selected_indices)} paragraphs", type_="positive"
                )
            else:
                self.selected_paragraph_indices = previous_paragraph_selection
                self._update_action_button_state()
                self._emit_paragraph_selection_changed()
                self._safe_notify(
                    "Failed to merge selected paragraphs", type_="warning"
                )
        except Exception as e:
            self.selected_paragraph_indices = previous_paragraph_selection
            self._update_action_button_state()
            self._emit_paragraph_selection_changed()
            logger.exception(
                "Error merging selected paragraphs %s: %s",
                selected_indices,
                e,
            )
            self._safe_notify(
                f"Error merging selected paragraphs: {e}",
                type_="negative",
            )

    def _handle_delete_selected_paragraphs(self):
        """Delete selected paragraphs from the current page."""
        if self.delete_paragraphs_callback is None:
            self._safe_notify(
                "Delete paragraph function not available", type_="warning"
            )
            return

        selected_indices = sorted(self.selected_paragraph_indices)
        if not selected_indices:
            self._safe_notify(
                "Select at least one paragraph to delete", type_="warning"
            )
            return

        previous_paragraph_selection = set(self.selected_paragraph_indices)
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_paragraph_selection_changed()
        logger.info("Delete requested for selected paragraphs: %s", selected_indices)
        try:
            success = self.delete_paragraphs_callback(selected_indices)
            logger.info(
                "Delete paragraph callback completed: selected=%s success=%s",
                selected_indices,
                success,
            )
            if success:
                self._safe_notify(
                    f"Deleted {len(selected_indices)} paragraphs", type_="positive"
                )
            else:
                self.selected_paragraph_indices = previous_paragraph_selection
                self._update_action_button_state()
                self._emit_paragraph_selection_changed()
                self._safe_notify(
                    "Failed to delete selected paragraphs",
                    type_="warning",
                )
        except Exception as e:
            self.selected_paragraph_indices = previous_paragraph_selection
            self._update_action_button_state()
            self._emit_paragraph_selection_changed()
            logger.exception(
                "Error deleting selected paragraphs %s: %s",
                selected_indices,
                e,
            )
            self._safe_notify(
                f"Error deleting selected paragraphs: {e}",
                type_="negative",
            )

    def _handle_split_paragraph_after_selected_line(self):
        """Split the selected line's paragraph immediately after that line."""
        if self.split_paragraph_after_line_callback is None:
            self._safe_notify("Split paragraph function not available", type_="warning")
            return

        selected_line_indices = self._get_effective_selected_lines()
        if len(selected_line_indices) != 1:
            self._safe_notify(
                "Select exactly one line to split paragraph", type_="warning"
            )
            return

        selected_line_index = selected_line_indices[0]
        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        previous_paragraph_selection = set(self.selected_paragraph_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        logger.info("Split requested after selected line: %s", selected_line_index)
        try:
            success = self.split_paragraph_after_line_callback(selected_line_index)
            logger.info(
                "Split paragraph-after-line callback completed: line=%s success=%s",
                selected_line_index,
                success,
            )
            if success:
                self._safe_notify(
                    f"Split paragraph after line {selected_line_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self.selected_paragraph_indices = previous_paragraph_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._emit_paragraph_selection_changed()
                self._safe_notify("Failed to split paragraph", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self.selected_paragraph_indices = previous_paragraph_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            self._emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting paragraph after line %s: %s",
                selected_line_index,
                e,
            )
            self._safe_notify(
                f"Error splitting paragraph: {e}",
                type_="negative",
            )

    def _handle_split_paragraph_by_selected_lines(self):
        """Split one paragraph into selected and unselected lines."""
        logger.debug(
            "[split_by_selection] handler.start selected_lines=%s selected_words=%s selected_paragraphs=%s",
            sorted(self.selected_line_indices),
            sorted(self.selected_word_indices),
            sorted(self.selected_paragraph_indices),
        )
        if self.split_paragraph_with_selected_lines_callback is None:
            self._safe_notify("Split paragraph function not available", type_="warning")
            return

        selected_line_indices = self._get_effective_selected_lines()
        if not selected_line_indices:
            self._safe_notify(
                "Select one or more lines to split paragraph", type_="warning"
            )
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        previous_paragraph_selection = set(self.selected_paragraph_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self.selected_paragraph_indices.clear()
        logger.debug("[split_by_selection] handler.selection_cleared")
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        logger.info(
            "[split_by_selection] handler.requested lines=%s", selected_line_indices
        )
        try:
            logger.debug(
                "[split_by_selection] handler.callback_invoke lines=%s",
                selected_line_indices,
            )
            success = self.split_paragraph_with_selected_lines_callback(
                selected_line_indices
            )
            logger.info(
                "[split_by_selection] handler.callback_done lines=%s success=%s",
                selected_line_indices,
                success,
            )
            if success:
                logger.debug(
                    "[split_by_selection] handler.success awaiting_page_state_refresh"
                )
                self._safe_notify("Split paragraph by selected lines", type_="positive")
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self.selected_paragraph_indices = previous_paragraph_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._emit_paragraph_selection_changed()
                self._safe_notify("Failed to split paragraph", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self.selected_paragraph_indices = previous_paragraph_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            self._emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting paragraph by selected lines %s: %s",
                selected_line_indices,
                e,
            )
            self._safe_notify(
                f"Error splitting paragraph: {e}",
                type_="negative",
            )

    def _handle_delete_selected_lines(self):
        """Delete selected lines from the current page."""
        if self.delete_lines_callback is None:
            self._safe_notify("Delete function not available", type_="warning")
            return

        selected_indices = self._get_effective_selected_lines()
        if not selected_indices:
            self._safe_notify("Select at least one line to delete", type_="warning")
            return

        self._delete_lines(
            selected_indices,
            success_message=f"Deleted {len(selected_indices)} lines",
            failure_message="Failed to delete selected lines",
        )

    def _handle_delete_selected_words(self):
        """Delete selected words from the current page."""
        if self.delete_words_callback is None:
            self._safe_notify("Delete word function not available", type_="warning")
            return

        selected_words = sorted(self.selected_word_indices)
        if not selected_words:
            self._safe_notify("Select at least one word to delete", type_="warning")
            return

        previously_selected_lines = set(self.selected_line_indices)
        previously_selected_words = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        logger.info("Delete requested for selected words: %s", selected_words)
        try:
            success = self.delete_words_callback(selected_words)
            logger.info(
                "Delete words callback completed: selected=%s success=%s",
                selected_words,
                success,
            )
            if success:
                self._safe_notify(
                    f"Deleted {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previously_selected_lines
                self.selected_word_indices = previously_selected_words
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to delete selected words", type_="warning")
        except Exception as e:
            self.selected_line_indices = previously_selected_lines
            self.selected_word_indices = previously_selected_words
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception("Error deleting words %s: %s", selected_words, e)
            self._safe_notify(f"Error deleting words: {e}", type_="negative")

    def _handle_delete_single_word(self, line_index: int, word_index: int) -> None:
        """Delete a single word from a specific line."""
        if self.delete_words_callback is None:
            self._safe_notify("Delete word function not available", type_="warning")
            return

        word_key = (line_index, word_index)
        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.delete_words_callback([word_key])
            if success:
                self._safe_notify(
                    f"Deleted word {word_index + 1} from line {line_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to delete word", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error deleting single word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error deleting word: {e}", type_="negative")

    def _handle_merge_word_left(self, line_index: int, word_index: int) -> None:
        """Merge selected word into its left neighbor."""
        if self.merge_word_left_callback is None:
            self._safe_notify("Merge word function not available", type_="warning")
            return
        if word_index <= 0:
            self._safe_notify("No left word to merge into", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.merge_word_left_callback(line_index, word_index)
            if success:
                self._safe_notify(
                    f"Merged word {word_index + 1} into word {word_index}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to merge word left", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error merge-word-left (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error merging word: {e}", type_="negative")

    def _handle_merge_word_right(self, line_index: int, word_index: int) -> None:
        """Merge selected word with its right neighbor."""
        if self.merge_word_right_callback is None:
            self._safe_notify("Merge word function not available", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.merge_word_right_callback(line_index, word_index)
            if success:
                self._safe_notify(
                    f"Merged word {word_index + 2} into word {word_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to merge word right", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error merge-word-right (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error merging word: {e}", type_="negative")

    def _handle_split_word(self, line_index: int, word_index: int) -> None:
        """Split the selected word at the current marker."""
        if self.split_word_callback is None:
            self._safe_notify("Split word function not available", type_="warning")
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word to split", type_="warning")
            return

        split_key = (line_index, word_index)
        split_fraction = self._word_split_fractions.get(split_key)
        if split_fraction is None:
            self._safe_notify(
                "Click inside the word image to choose split position",
                type_="warning",
            )
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.split_word_callback(line_index, word_index, split_fraction)
            if success:
                self._word_split_fractions.pop(split_key, None)
                self._word_split_marker_x.pop(split_key, None)
                self._render_word_split_marker(split_key)
                split_button = self._word_split_button_refs.get(split_key)
                if split_button is not None:
                    split_button.disabled = True
                self._safe_notify(
                    f"Split word {word_index + 1} on line {line_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to split word", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error split-word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error splitting word: {e}", type_="negative")

    def _handle_delete_line(self, line_index: int) -> None:
        """Delete a single line from the current page."""
        if self.delete_lines_callback is None:
            self._safe_notify("Delete function not available", type_="warning")
            return

        self._delete_lines(
            [line_index],
            success_message=f"Deleted line {line_index + 1}",
            failure_message=f"Failed to delete line {line_index + 1}",
        )

    def _delete_lines(
        self,
        line_indices: list[int],
        *,
        success_message: str,
        failure_message: str,
    ) -> None:
        """Execute line deletion and keep selection state consistent on failure."""
        previously_selected = set(self.selected_line_indices)
        previously_selected_words = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        logger.info("Delete requested for lines: %s", line_indices)
        try:
            success = self.delete_lines_callback(line_indices)
            logger.info(
                "Delete callback completed: selected=%s success=%s",
                line_indices,
                success,
            )
            if success:
                self._safe_notify(success_message, type_="positive")
            else:
                self.selected_line_indices = previously_selected
                self.selected_word_indices = previously_selected_words
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify(failure_message, type_="warning")
        except Exception as e:
            self.selected_line_indices = previously_selected
            self.selected_word_indices = previously_selected_words
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception("Error deleting lines %s: %s", line_indices, e)
            self._safe_notify(f"Error deleting lines: {e}", type_="negative")

    def _filter_lines_for_display(self):
        """Filter lines based on current filter setting."""
        logger.debug(
            f"Filtering lines. Show only mismatches: {self.show_only_mismatches}"
        )
        logger.debug(
            f"Total line matches available: {len(self.view_model.line_matches)}"
        )

        if not self.show_only_mismatches:
            # Show all lines
            logger.debug("Returning all lines (no filtering)")
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
                    logger.debug(
                        f"Line {line_match.line_index} has mismatches, including in filtered results"
                    )
                else:
                    logger.debug(
                        f"Line {line_match.line_index} has no mismatches, excluding from filtered results"
                    )
            logger.debug(f"Filtered to {len(filtered_lines)} lines with mismatches")
            return filtered_lines

    def _handle_copy_gt_to_ocr(self, line_index: int):
        """Handle the GT→OCR button click."""
        logger.debug("Handling GT→OCR copy for line index %d", line_index)
        if self.copy_gt_to_ocr_callback:
            try:
                logger.debug("Calling copy_gt_to_ocr_callback for line %d", line_index)
                success = self.copy_gt_to_ocr_callback(line_index)
                if success:
                    logger.debug("GT→OCR copy successful for line %d", line_index)
                    self._safe_notify(
                        f"Copied ground truth to OCR text for line {line_index + 1}",
                        type_="positive",
                    )
                else:
                    logger.debug(
                        "GT→OCR copy failed - no ground truth text found for line %d",
                        line_index,
                    )
                    self._safe_notify(
                        f"No ground truth text found to copy in line {line_index + 1}",
                        type_="warning",
                    )
            except Exception as e:
                logger.exception(f"Error copying GT→OCR for line {line_index}: {e}")
                self._safe_notify(f"Error copying GT→OCR: {e}", type_="negative")
        else:
            logger.debug("No copy_gt_to_ocr_callback available")
            self._safe_notify("Copy function not available", type_="warning")

    def _handle_copy_ocr_to_gt(self, line_index: int):
        """Handle the OCR→GT button click."""
        logger.debug("Handling OCR→GT copy for line index %d", line_index)
        if self.copy_ocr_to_gt_callback:
            try:
                logger.debug("Calling copy_ocr_to_gt_callback for line %d", line_index)
                success = self.copy_ocr_to_gt_callback(line_index)
                if success:
                    logger.debug("OCR→GT copy successful for line %d", line_index)
                    self._safe_notify(
                        f"Copied OCR to ground truth text for line {line_index + 1}",
                        type_="positive",
                    )
                else:
                    logger.debug(
                        "OCR→GT copy failed - no OCR text found for line %d",
                        line_index,
                    )
                    self._safe_notify(
                        f"No OCR text found to copy in line {line_index + 1}",
                        type_="warning",
                    )
            except Exception as e:
                logger.exception(f"Error copying OCR→GT for line {line_index}: {e}")
                self._safe_notify(f"Error copying OCR→GT: {e}", type_="negative")
        else:
            logger.debug("No copy_ocr_to_gt_callback available")
            self._safe_notify("Copy function not available", type_="warning")

    def clear(self):
        """Clear the display."""
        logger.debug("Clearing WordMatchView display")
        if self.lines_container:
            self.lines_container.clear()
            logger.debug("Cleared lines container")
        if self.summary_label:
            self.summary_label.set_text("No matches to display")
            logger.debug("Reset summary label text")
        self._last_display_signature = None
        self._display_update_call_count = 0
        self._display_update_render_count = 0
        self._display_update_skip_count = 0
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        logger.debug("WordMatchView clear complete")
