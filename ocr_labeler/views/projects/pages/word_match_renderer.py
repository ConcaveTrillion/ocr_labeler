"""Rendering and display logic for the word match view."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

from nicegui import events, ui

from ....models.word_match_model import MatchStatus, WordMatch
from ...shared.button_styles import (
    ButtonVariant,
    style_action_button,
    style_word_icon_button,
)
from .word_edit_dialog import (
    handle_word_image_mouse,
    open_word_edit_dialog,
    render_word_split_marker,
)

if TYPE_CHECKING:
    from ....models.line_match_model import LineMatch
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)

WordKey = tuple[int, int]
ClickEvent = events.ClickEventArguments | None


class WordMatchRenderer:
    """Manages rendering and display rebuild logic for WordMatchView."""

    def __init__(self, view: WordMatchView) -> None:
        self._view = view
        self._line_card_refs: dict[int, object] = {}
        self._word_column_refs: dict[WordKey, object] = {}
        self._last_display_signature = None
        self._display_update_call_count: int = 0
        self._display_update_render_count: int = 0
        self._display_update_skip_count: int = 0
        self._paragraph_expanded: dict[Optional[int], bool] = {}
        self._word_dialog_refresh_key: WordKey | None = None
        self._word_dialog_refresh_callback: Callable[[], None] | None = None

    # ------------------------------------------------------------------
    # Full display rebuild
    # ------------------------------------------------------------------

    def update_lines_display(self) -> None:
        """Update the lines display with word matches."""
        self._display_update_call_count += 1
        logger.info(
            "_update_lines_display called (call=%d, rendered=%d, skipped=%d)",
            self._display_update_call_count,
            self._display_update_render_count,
            self._display_update_skip_count,
        )
        if not self._view._has_active_ui_context(self._view.lines_container):
            logger.info("No lines_container, returning")
            return

        available_line_indices = {
            line_match.line_index for line_match in self._view.view_model.line_matches
        }
        if self._view.selection.selected_line_indices:
            self._view.selection.selected_line_indices.intersection_update(
                available_line_indices
            )
        if self._view.selection.selected_word_indices:
            word_count_by_line = {
                line_match.line_index: len(line_match.word_matches)
                for line_match in self._view.view_model.line_matches
            }
            self._view.selection.selected_word_indices = {
                (line_index, word_index)
                for line_index, word_index in self._view.selection.selected_word_indices
                if line_index in available_line_indices
                and 0 <= word_index < word_count_by_line.get(line_index, 0)
            }
        for line_index in available_line_indices:
            self._view.selection.sync_line_selection_from_words(line_index)
        valid_split_keys = {
            (line_match.line_index, word_match.word_index)
            for line_match in self._view.view_model.line_matches
            for word_match in line_match.word_matches
            if word_match.word_index is not None
        }
        self._view._word_split_fractions = {
            key: value
            for key, value in self._view._word_split_fractions.items()
            if key in valid_split_keys
        }
        self._view._word_split_y_fractions = {
            key: value
            for key, value in self._view._word_split_y_fractions.items()
            if key in valid_split_keys
        }
        self._view._word_split_marker_x = {
            key: value
            for key, value in self._view._word_split_marker_x.items()
            if key in valid_split_keys
        }
        self._view.bbox._bbox_editor_open_keys.intersection_update(valid_split_keys)
        available_paragraph_indices = {
            line_match.paragraph_index
            for line_match in self._view.view_model.line_matches
            if getattr(line_match, "paragraph_index", None) is not None
        }
        self._view.selection.selected_paragraph_indices.intersection_update(
            available_paragraph_indices
        )
        available_paragraph_keys = {
            getattr(line_match, "paragraph_index", None)
            for line_match in self._view.view_model.line_matches
        }
        self._paragraph_expanded = {
            paragraph_index: expanded
            for paragraph_index, expanded in self._paragraph_expanded.items()
            if paragraph_index in available_paragraph_keys
        }
        self._view.toolbar.update_button_state()

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
        self._view.lines_container.clear()
        self._view.bbox.refresh_word_slice_source()
        self._view._word_split_image_refs = {}
        self._view._word_split_image_sizes = {}
        self._view._word_split_fractions = {}
        self._view._word_split_y_fractions = {}
        self._view._word_split_marker_x = {}
        self._view._word_split_marker_y = {}
        self._view._word_split_hover_keys = set()
        self._view._word_split_hover_positions = {}
        self._view._word_split_button_refs = {}
        self._view._word_vertical_split_button_refs = {}
        self._view._word_crop_button_refs = {}
        self._view.selection._word_checkbox_refs = {}
        self._view.gt_editing._word_style_button_refs = {}
        self._word_column_refs = {}
        self._line_card_refs = {}
        self._view.selection._line_checkbox_refs = {}
        self._view.selection._paragraph_checkbox_refs = {}
        self._view.gt_editing._word_gt_input_refs = {}

        if not self._view.view_model.line_matches:
            logger.info("No line matches in view model")
            with self._view.lines_container:
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
            with self._view.lines_container:
                with ui.card():
                    with ui.card_section():
                        ui.icon("filter_list_off")
                        ui.label("No lines match the current filter")
                        if self._view.filter_mode == "Unvalidated Lines":
                            ui.label(
                                "All lines are validated. Try selecting 'All Lines' to see them."
                            )
                        elif self._view.filter_mode == "Mismatched Lines":
                            ui.label(
                                "All lines have perfect matches. Try selecting 'All Lines' to see them."
                            )
            self._display_update_render_count += 1
            self._last_display_signature = display_signature
            return

        # Display filtered line matches in collapsible paragraph sections
        logger.info(f"Displaying {len(lines_to_display)} line matches")
        with self._view.lines_container:
            for (
                paragraph_index,
                paragraph_line_matches,
            ) in self._group_lines_by_paragraph(lines_to_display):
                paragraph_is_expanded = self._paragraph_expanded.get(
                    paragraph_index,
                    True,
                )
                with ui.column().classes("full-width").style("gap: 0; margin: 0;"):
                    with (
                        ui.row()
                        .classes(
                            "items-center full-width no-wrap gap-1 q-my-none q-py-none"
                        )
                        .style(
                            "margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0;"
                        )
                    ):
                        if paragraph_index is not None:
                            paragraph_checkbox = (
                                ui.checkbox(
                                    text="",
                                    value=paragraph_index
                                    in self._view.selection.selected_paragraph_indices,
                                )
                                .props("size=sm dense")
                                .classes("shrink-0 self-center")
                                .style("margin-right: 0.125rem;")
                                .on_value_change(
                                    lambda event, index=paragraph_index: (
                                        self._view.selection.on_paragraph_selection_change(
                                            index,
                                            bool(event.value),
                                        )
                                    )
                                )
                            )
                            self._view.selection._paragraph_checkbox_refs[
                                paragraph_index
                            ] = paragraph_checkbox

                        toggle_icon = (
                            "expand_more" if paragraph_is_expanded else "chevron_right"
                        )
                        ui.button(
                            icon=toggle_icon,
                            on_click=lambda _event, index=paragraph_index: (
                                self._toggle_paragraph_expanded(index)
                            ),
                        ).props(
                            'flat round dense size=sm data-testid="paragraph-expander-button"'
                        ).classes("shrink-0")

                        ui.button(
                            self._view._format_paragraph_label(paragraph_index),
                            on_click=lambda _event, index=paragraph_index: (
                                self._toggle_paragraph_expanded(index)
                            ),
                        ).props("flat dense no-caps align=left").classes(
                            "grow justify-start text-left"
                        )

                    if paragraph_is_expanded:
                        with (
                            ui.column()
                            .classes("full-width")
                            .style("gap: 0; margin: 0; padding: 0;")
                        ):
                            for line_match in paragraph_line_matches:
                                with (
                                    ui.column()
                                    .classes("full-width")
                                    .style(
                                        "gap: 0; margin: 0; padding: 0;"
                                    ) as line_slot
                                ):
                                    self._line_card_refs[line_match.line_index] = (
                                        line_slot
                                    )
                                    self._create_line_card(line_match)

        self._display_update_render_count += 1
        self._last_display_signature = display_signature

    # ------------------------------------------------------------------
    # Display signature for skip optimisation
    # ------------------------------------------------------------------

    def _compute_display_signature(self):
        """Return a stable signature for visible line-match content."""
        line_signatures = []
        for line_match in self._view.view_model.line_matches:
            word_signatures = tuple(
                (
                    word_match.match_status.value,
                    word_match.ocr_text,
                    word_match.ground_truth_text,
                    round(word_match.fuzz_score, 6)
                    if word_match.fuzz_score is not None
                    else None,
                    self._view._word_match_bbox_signature(word_match),
                    self._view._word_match_attribute_signature(word_match),
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
                    line_match.validated_word_count,
                    word_signatures,
                )
            )

        return (
            self._view.filter_mode,
            tuple(sorted(self._view.selection.selected_line_indices)),
            tuple(sorted(self._view.selection.selected_word_indices)),
            tuple(sorted(self._view.selection.selected_paragraph_indices)),
            tuple(
                sorted(
                    (paragraph_index, expanded)
                    for paragraph_index, expanded in self._paragraph_expanded.items()
                )
            ),
            tuple(sorted(self._view.bbox._bbox_editor_open_keys)),
            tuple(sorted(self._view.bbox._bbox_pending_deltas.items())),
            tuple(line_signatures),
        )

    # ------------------------------------------------------------------
    # Filtering and grouping
    # ------------------------------------------------------------------

    def _filter_lines_for_display(self):
        """Filter lines based on current filter setting."""
        filter_mode = self._view.filter_mode
        logger.debug(f"Filtering lines. Filter mode: {filter_mode}")
        logger.debug(
            f"Total line matches available: {len(self._view.view_model.line_matches)}"
        )

        if filter_mode == "All Lines":
            logger.debug("Returning all lines (no filtering)")
            return self._view.view_model.line_matches
        elif filter_mode == "Unvalidated Lines":
            filtered_lines = [
                lm
                for lm in self._view.view_model.line_matches
                if not lm.is_fully_validated
            ]
            logger.debug(f"Filtered to {len(filtered_lines)} unvalidated lines")
            return filtered_lines
        else:
            # Mismatched Lines: any word that's not an exact match
            filtered_lines = [
                lm
                for lm in self._view.view_model.line_matches
                if any(wm.match_status != MatchStatus.EXACT for wm in lm.word_matches)
            ]
            logger.debug(f"Filtered to {len(filtered_lines)} lines with mismatches")
            return filtered_lines

    def _group_lines_by_paragraph(self, line_matches: list["LineMatch"]):
        """Group line matches by paragraph index, keeping unassigned lines last."""
        grouped: dict[Optional[int], list["LineMatch"]] = {}
        for line_match in line_matches:
            paragraph_index = getattr(line_match, "paragraph_index", None)
            grouped.setdefault(paragraph_index, []).append(line_match)

        ordered_groups = []
        for paragraph_index in sorted(k for k in grouped if k is not None):
            ordered_groups.append((paragraph_index, grouped[paragraph_index]))

        if None in grouped:
            ordered_groups.append((None, grouped[None]))

        return ordered_groups

    def _toggle_paragraph_expanded(self, paragraph_index: Optional[int]) -> None:
        is_expanded = self._paragraph_expanded.get(paragraph_index, True)
        self._paragraph_expanded[paragraph_index] = not is_expanded
        self.update_lines_display()

    # ------------------------------------------------------------------
    # Line card rendering
    # ------------------------------------------------------------------

    def _create_line_card(self, line_match) -> None:
        """Create a card display for a single line match."""
        logger.debug(
            "Creating line card for line %d with status %s",
            line_match.line_index,
            line_match.overall_match_status.value,
        )
        with ui.column().classes("full-width").style("gap: 0; margin: 0; padding: 0;"):
            # Color background bar based on overall match status
            status_classes = self._view._get_status_classes(
                line_match.overall_match_status.value
            )
            with ui.row().classes(f"full-width p-2 rounded {status_classes}"):
                # Header with line info and status
                with ui.row().classes("items-center justify-between"):
                    # Left side: Line info and stats
                    with ui.row().classes("items-center"):
                        line_checkbox = (
                            ui.checkbox(
                                text="",
                                value=self._view.selection.is_line_checked(
                                    line_match.line_index
                                ),
                            )
                            .props("size=sm")
                            .on_value_change(
                                lambda event, index=line_match.line_index: (
                                    self._view.selection.on_line_selection_change(
                                        index,
                                        bool(event.value),
                                    )
                                )
                            )
                        )
                        self._view.selection._line_checkbox_refs[
                            line_match.line_index
                        ] = line_checkbox
                        ui.label(f"Line {line_match.line_index + 1}")
                        ui.label(
                            self._view._format_paragraph_label(
                                getattr(line_match, "paragraph_index", None)
                            )
                        ).classes("text-caption")
                        ui.icon("bar_chart")
                        ui.label(f"\u2713 {line_match.exact_match_count}").tooltip(
                            "Exact matches"
                        )
                        ui.label(f"\u26a0 {line_match.fuzzy_match_count}").tooltip(
                            "Fuzzy matches"
                        )
                        ui.label(f"\u2717 {line_match.mismatch_count}").tooltip(
                            "Mismatches"
                        )
                        if line_match.unmatched_gt_count > 0:
                            ui.label(
                                f"\U0001f535 {line_match.unmatched_gt_count}"
                            ).tooltip("Unmatched ground truth")
                        if line_match.unmatched_ocr_count > 0:
                            ui.label(
                                f"\u26ab {line_match.unmatched_ocr_count}"
                            ).tooltip("Unmatched OCR")

                        # Validation rollup indicator
                        v_count = line_match.validated_word_count
                        v_total = line_match.total_word_count
                        if v_total > 0:
                            if line_match.is_fully_validated:
                                ui.icon("verified").classes(
                                    "text-green-600 text-sm"
                                ).tooltip("All words validated")
                            else:
                                color = (
                                    "text-blue-600" if v_count > 0 else "text-grey-400"
                                )
                                ui.label(f"\u2611 {v_count}/{v_total}").classes(
                                    f"text-xs {color}"
                                ).tooltip(f"{v_count} of {v_total} words validated")

                    # Right side: Action buttons
                    logger.debug(
                        f"Line {line_match.line_index}: status={line_match.overall_match_status}, gt_to_ocr_callback={self._view.copy_gt_to_ocr_callback is not None}, ocr_to_gt_callback={self._view.copy_ocr_to_gt_callback is not None}"
                    )
                    with ui.row().classes("items-center"):
                        if (
                            line_match.overall_match_status != MatchStatus.EXACT
                            and self._view.copy_gt_to_ocr_callback
                        ):
                            logger.debug(
                                f"Adding GT\u2192OCR button for line {line_match.line_index}"
                            )
                            gt_to_ocr_button = ui.button(
                                "GT\u2192OCR",
                                icon="content_copy",
                            ).tooltip(
                                "Copy ground truth text to OCR text for all words in this line"
                            )
                            gt_to_ocr_button.props(
                                'data-testid="line-gt-to-ocr-button"'
                            )
                            style_action_button(gt_to_ocr_button)
                            gt_to_ocr_button.on_click(
                                lambda: self._view.actions._handle_copy_gt_to_ocr(
                                    line_match.line_index
                                )
                            )

                        if (
                            line_match.overall_match_status != MatchStatus.EXACT
                            and self._view.copy_ocr_to_gt_callback
                        ):
                            logger.debug(
                                f"Adding OCR\u2192GT button for line {line_match.line_index}"
                            )
                            ocr_to_gt_button = ui.button(
                                "OCR\u2192GT",
                                icon="content_copy",
                            ).tooltip(
                                "Copy OCR text to ground truth text for all words in this line"
                            )
                            ocr_to_gt_button.props(
                                'data-testid="line-ocr-to-gt-button"'
                            )
                            style_action_button(ocr_to_gt_button)
                            ocr_to_gt_button.on_click(
                                lambda: self._view.actions._handle_copy_ocr_to_gt(
                                    line_match.line_index
                                )
                            )

                        # Validate line button
                        if self._view.toggle_word_validated_callback:
                            v_count = line_match.validated_word_count
                            v_total = line_match.total_word_count
                            all_validated = line_match.is_fully_validated
                            validate_line_btn = ui.button(
                                "Validate" if not all_validated else "Unvalidate",
                                icon="check_circle"
                                if not all_validated
                                else "unpublished",
                            ).tooltip(
                                f"{'Unvalidate' if all_validated else 'Validate'} all words in this line ({v_count}/{v_total})"
                            )
                            validate_line_btn.props(
                                'data-testid="line-validate-button"'
                            )
                            style_action_button(validate_line_btn)
                            if all_validated:
                                validate_line_btn.classes("text-green-600")
                            validate_line_btn.on_click(
                                lambda _e, lm=line_match: self._handle_validate_line(lm)
                            )

                        delete_button = ui.button(icon="delete").tooltip(
                            "Delete this line"
                        )
                        delete_button.props('data-testid="line-delete-button"')
                        style_word_icon_button(
                            delete_button,
                            variant=ButtonVariant.DELETE,
                        )
                        if self._view.delete_lines_callback:
                            delete_button.on_click(
                                lambda: self._view.actions._handle_delete_line(
                                    line_match.line_index
                                )
                            )
                        else:
                            delete_button.disabled = True

            # Card content with word comparison table
            with ui.row():
                # Word comparison table
                with ui.column():
                    self._create_word_comparison_table(line_match)
        logger.debug("Line card creation complete for line %d", line_match.line_index)

    def rerender_line_card(self, line_index: int) -> None:
        """Rerender a single line card in-place when only that line changed."""
        line_slot = self._line_card_refs.get(line_index)
        line_match = self._view._line_match_by_index(line_index)
        if line_slot is None or line_match is None:
            return
        if not self._view._has_active_ui_context(line_slot):
            self._line_card_refs.pop(line_index, None)
            return

        self._view.selection._line_checkbox_refs.pop(line_index, None)
        for key in [
            key
            for key in self._view.selection._word_checkbox_refs
            if key[0] == line_index
        ]:
            self._view.selection._word_checkbox_refs.pop(key, None)
            self._view.gt_editing._word_style_button_refs.pop(key, None)
            self._word_column_refs.pop(key, None)
            self._view.gt_editing._word_gt_input_refs.pop(key, None)
            self._view._word_split_button_refs.pop(key, None)
            self._view._word_vertical_split_button_refs.pop(key, None)
            self._view._word_crop_button_refs.pop(key, None)
            self._view._word_split_image_refs.pop(key, None)
            self._view._word_split_image_sizes.pop(key, None)
            self._view._word_split_fractions.pop(key, None)
            self._view._word_split_y_fractions.pop(key, None)
            self._view._word_split_marker_x.pop(key, None)
            self._view._word_split_marker_y.pop(key, None)
            self._view._word_split_hover_keys.discard(key)
            self._view._word_split_hover_positions.pop(key, None)

        line_slot.clear()
        with line_slot:
            self._create_line_card(line_match)

    def rerender_word_column(self, line_index: int, word_index: int) -> None:
        """Rerender a single OCR word column in-place when only that word changed."""
        word_key = (line_index, word_index)
        word_slot = self._word_column_refs.get(word_key)
        if word_slot is None:
            return
        if not self._view._has_active_ui_context(word_slot):
            self._word_column_refs.pop(word_key, None)
            return

        line_match = self._view._line_match_by_index(line_index)
        if line_match is None:
            return

        display_word_index = -1
        target_word_match = None
        for idx, word_match in enumerate(line_match.word_matches):
            if word_match.word_index == word_index:
                display_word_index = idx
                target_word_match = word_match
                break

        if target_word_match is None:
            return

        self._view.selection._word_checkbox_refs.pop(word_key, None)
        self._view.gt_editing._word_style_button_refs.pop(word_key, None)
        self._view.gt_editing._word_gt_input_refs.pop(word_key, None)
        self._view._word_split_button_refs.pop(word_key, None)
        self._view._word_vertical_split_button_refs.pop(word_key, None)
        self._view._word_crop_button_refs.pop(word_key, None)
        self._view._word_split_image_refs.pop(word_key, None)
        self._view._word_split_image_sizes.pop(word_key, None)
        self._view._word_split_fractions.pop(word_key, None)
        self._view._word_split_y_fractions.pop(word_key, None)
        self._view._word_split_marker_x.pop(word_key, None)
        self._view._word_split_marker_y.pop(word_key, None)
        self._view._word_split_hover_keys.discard(word_key)
        self._view._word_split_hover_positions.pop(word_key, None)

        word_slot.clear()
        with word_slot:
            self._create_word_selection_cell(
                line_index,
                display_word_index,
                word_index,
                len(line_match.word_matches),
                target_word_match,
            )
            self.create_image_cell(
                line_index,
                word_index,
                target_word_match,
                interactive=False,
            )
            self._create_ocr_cell(
                target_word_match,
                line_index=line_index,
                split_word_index=word_index,
            )
            self._view.gt_editing.create_gt_cell(
                line_index,
                word_index,
                target_word_match,
            )
            self._create_status_cell(target_word_match)

    # ------------------------------------------------------------------
    # Word comparison table
    # ------------------------------------------------------------------

    def _create_word_comparison_table(self, line_match) -> None:
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

                with ui.column() as word_column:
                    # Image cell
                    split_word_index = (
                        word_match.word_index
                        if word_match.word_index is not None
                        else -1
                    )
                    if split_word_index >= 0:
                        self._word_column_refs[
                            (line_match.line_index, split_word_index)
                        ] = word_column
                    self._create_word_selection_cell(
                        line_match.line_index,
                        word_idx,
                        split_word_index,
                        len(line_match.word_matches),
                        word_match,
                    )
                    self.create_image_cell(
                        line_match.line_index,
                        split_word_index,
                        word_match,
                        interactive=False,
                    )
                    # OCR text cell
                    self._create_ocr_cell(
                        word_match,
                        line_index=line_match.line_index,
                        split_word_index=split_word_index,
                    )
                    # Ground Truth text cell
                    self._view.gt_editing.create_gt_cell(
                        line_match.line_index,
                        split_word_index,
                        word_match,
                    )
                    # Status cell
                    self._create_status_cell(word_match)
        logger.debug(
            "Word comparison table creation complete for line %d",
            line_match.line_index,
        )

    # ------------------------------------------------------------------
    # Cell rendering helpers
    # ------------------------------------------------------------------

    def _create_word_selection_cell(
        self,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_count: int,
        word_match,
    ) -> None:
        """Create compact per-word controls for fast initial rendering."""
        selection_key = (line_index, word_index)
        with ui.row().classes("items-center"):
            word_checkbox = (
                ui.checkbox(
                    text="",
                    value=selection_key in self._view.selection.selected_word_indices,
                )
                .props("size=xs dense")
                .tooltip("Select word")
                .on_value_change(
                    lambda event, key=selection_key: (
                        self._view.selection.on_word_selection_change(
                            key,
                            bool(event.value),
                        )
                    )
                )
            )
            self._view.selection._word_checkbox_refs[selection_key] = word_checkbox

            edit_button = ui.button(
                icon="edit",
                on_click=lambda _event: self._open_word_edit_dialog(
                    line_index,
                    word_index,
                    split_word_index,
                    word_match,
                ),
            ).tooltip("Edit word actions")
            edit_button.props('data-testid="edit-word-button"')
            style_word_icon_button(edit_button)

            # Validation toggle next to edit button
            validated = getattr(word_match, "is_validated", False)
            val_btn = ui.button(
                icon="check",
                on_click=lambda _event, li=line_index, wi=split_word_index: (
                    self._handle_toggle_word_validated(li, wi, _event)
                ),
            ).tooltip("Validated" if validated else "Mark as validated")
            val_btn.props("size=xs unelevated round")
            if validated:
                val_btn.props("color=green text-color=white")
            else:
                val_btn.props("color=grey text-color=white")
            val_btn.disabled = (
                self._view.toggle_word_validated_callback is None
                or split_word_index < 0
            )

    def _open_word_edit_dialog(
        self,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_match,
    ) -> None:
        """Open the extracted word edit dialog module."""
        open_word_edit_dialog(
            self._view,
            line_index=line_index,
            word_index=word_index,
            split_word_index=split_word_index,
            word_match=word_match,
        )

    def create_image_cell(
        self,
        line_index: int,
        split_word_index: int,
        word_match,
        *,
        interactive: bool = True,
        zoom_scale: float = 1.0,
        bbox_preview_deltas: tuple[float, float, float, float] | None = None,
    ) -> None:
        """Create image cell for a word.

        When interactive is False, renders a lightweight preview image without
        mouse handlers or split-marker tracking.
        """
        with ui.row().classes("fit"):
            # Unmatched GT words don't have images since they don't have word objects
            if word_match.match_status == MatchStatus.UNMATCHED_GT:
                ui.icon("text_fields").classes("text-blue-600").style("height: 2.25em")
            else:
                try:
                    word_image_slice = self._view.bbox.get_word_image_slice(
                        word_match,
                        line_index=line_index,
                        word_index=split_word_index,
                        bbox_preview_deltas=bbox_preview_deltas,
                    )
                except Exception as e:
                    logger.error(f"Error getting word image: {e}")
                    word_image_slice = None
                    ui.icon("error").classes("text-red-600").style("height: 2.25em")
                    self._view._safe_notify_once(
                        "word-image-render",
                        "Unable to render one or more word images",
                        type_="warning",
                    )
                if word_image_slice:
                    image_source = str(word_image_slice.get("slice_source", "") or "")
                    if not image_source:
                        ui.icon("image_not_supported")
                        return

                    image_width = float(
                        word_image_slice.get("display_width", 1.0) or 1.0
                    )
                    image_height = float(
                        word_image_slice.get("display_height", 1.0) or 1.0
                    )
                    zoom = max(0.5, float(zoom_scale or 1.0))
                    render_width = image_width * zoom
                    render_height = image_height * zoom
                    background_source = str(
                        word_image_slice.get("background_source", "") or ""
                    )
                    background_width = float(
                        word_image_slice.get("background_width", 1.0) or 1.0
                    )
                    background_height = float(
                        word_image_slice.get("background_height", 1.0) or 1.0
                    )
                    background_x = float(
                        word_image_slice.get("background_x", 0.0) or 0.0
                    )
                    background_y = float(
                        word_image_slice.get("background_y", 0.0) or 0.0
                    )
                    render_background_width = background_width * zoom
                    render_background_height = background_height * zoom
                    render_background_x = background_x * zoom
                    render_background_y = background_y * zoom

                    safe_bg = (
                        background_source.replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace('"', '\\"')
                    )

                    if interactive:
                        image = ui.interactive_image(
                            image_source,
                            events=[
                                "mousedown",
                                "click",
                                "mousemove",
                                "mouseenter",
                                "mouseleave",
                            ],
                            on_mouse=lambda event, li=line_index, wi=split_word_index: (
                                handle_word_image_mouse(self._view, li, wi, event)
                            ),
                            sanitize=False,
                        ).classes("word-slice-image")
                        image.style(
                            f"width: {render_width:.2f}px; "
                            f"height: {render_height:.2f}px; "
                            f"background-image: url('{safe_bg}'); "
                            f"background-repeat: no-repeat; "
                            f"background-size: {render_background_width:.2f}px {render_background_height:.2f}px; "
                            f"background-position: -{render_background_x:.2f}px -{render_background_y:.2f}px; "
                            "cursor: crosshair;"
                        )
                        if split_word_index >= 0:
                            key = (line_index, split_word_index)
                            self._view._word_split_image_refs[key] = image
                            self._view._word_split_image_sizes[key] = (
                                float(image_width),
                                float(image_height),
                            )
                            render_word_split_marker(self._view, key)
                    else:
                        image = ui.interactive_image(
                            image_source,
                            events=[],
                            sanitize=False,
                        ).classes("word-slice-image")
                        image.style(
                            f"width: {render_width:.2f}px; "
                            f"height: {render_height:.2f}px; "
                            f"background-image: url('{safe_bg}'); "
                            f"background-repeat: no-repeat; "
                            f"background-size: {render_background_width:.2f}px {render_background_height:.2f}px; "
                            f"background-position: -{render_background_x:.2f}px -{render_background_y:.2f}px; "
                            "cursor: default;"
                        )
                else:
                    ui.icon("image_not_supported")

    def _create_ocr_cell(
        self,
        word_match,
        *,
        line_index: int | None = None,
        split_word_index: int | None = None,
    ) -> None:
        """Create OCR text cell for a word."""
        with ui.row():
            if word_match.ocr_text.strip():
                ocr_element = ui.label(word_match.ocr_text).classes("monospace")
                tooltip_content = self._view._create_word_tooltip(word_match)
                if tooltip_content:
                    ocr_element.tooltip(tooltip_content)
            else:
                # Show different placeholders based on match status
                if word_match.match_status == MatchStatus.UNMATCHED_GT:
                    ui.label("[missing]").classes("text-blue-600 monospace")
                else:
                    ui.label("[empty]").classes("monospace")

        tag_items = self._view._word_display_tag_items(word_match)
        if tag_items:
            with ui.row().classes("items-center gap-1").style("flex-wrap: wrap;"):
                for item in tag_items:
                    with (
                        ui.row()
                        .classes("items-center gap-1 word-tag-chip")
                        .style(self._view._word_tag_chip_style(item["kind"]))
                    ) as chip:
                        chip.props('data-testid="word-tag-chip"')
                        ui.label(item["display"]).classes("text-caption")
                        clear_button = ui.button(
                            icon="close",
                            on_click=lambda _event, tag=item: (
                                self._view._clear_word_tag(
                                    line_index,
                                    split_word_index,
                                    kind=tag["kind"],
                                    label=tag["label"],
                                )
                                if line_index is not None
                                and split_word_index is not None
                                and split_word_index >= 0
                                else None
                            ),
                        ).props(
                            'flat dense round size=xs data-testid="word-tag-clear-button"'
                        )
                        clear_button.classes("word-tag-clear-button")
                        clear_button.style("min-width: 0; width: 14px; height: 14px;")
                        clear_button.visible = False
                        chip.on(
                            "mouseenter",
                            lambda _event, button=clear_button: setattr(
                                button,
                                "visible",
                                True,
                            ),
                        )
                        chip.on(
                            "mouseleave",
                            lambda _event, button=clear_button: setattr(
                                button,
                                "visible",
                                False,
                            ),
                        )

    def _create_status_cell(self, word_match) -> None:
        """Create status cell for a word."""
        status_icon = self._view._get_status_icon(word_match.match_status.value)
        status_color_classes = self._view._get_status_color_classes(
            word_match.match_status.value
        )

        with ui.row():
            with ui.column():
                ui.icon(status_icon).classes(status_color_classes)
                if word_match.fuzz_score is not None:
                    ui.label(f"{word_match.fuzz_score:.2f}")

    def _create_word_text_display(self, word_matches, text_type) -> None:
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
                tooltip_content = self._view._create_word_tooltip(word_match)

                # Create word element with tooltip
                word_element = ui.label(text)
                if tooltip_content:
                    word_element.tooltip(tooltip_content)

    # ------------------------------------------------------------------
    # Word dialog refresh
    # ------------------------------------------------------------------

    def refresh_open_word_dialog_for(self, line_index: int, word_index: int) -> None:
        """Refresh an open word-edit dialog in-place for the active key."""
        key = (line_index, word_index)
        if self._word_dialog_refresh_key != key:
            return
        callback = self._word_dialog_refresh_callback
        if callback is None:
            return
        try:
            callback()
        except Exception:
            logger.debug("Word dialog refresh callback failed", exc_info=True)

    # ------------------------------------------------------------------
    # Validation toggle
    # ------------------------------------------------------------------

    def _handle_toggle_word_validated(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Handle per-word validation toggle."""
        callback = self._view.toggle_word_validated_callback
        if callback is None or word_index < 0:
            return
        callback(line_index, word_index)
        # Re-render line card to update both the word column and the header stats.
        # apply_word_validation_change (called via the event pipeline) updates the
        # in-memory model only; rendering is our responsibility.
        self.rerender_line_card(line_index)

    def _handle_validate_line(self, line_match) -> None:
        """Validate or unvalidate all words in a line."""
        callback = self._view.toggle_word_validated_callback
        if callback is None:
            return
        # Snapshot before the loop: each callback toggles state, so reading
        # is_validated mid-loop would see already-toggled values.
        all_validated = line_match.is_fully_validated
        targets = [
            (wm.word_index, wm.is_validated)
            for wm in line_match.word_matches
            if wm.word_index is not None and wm.word_index >= 0
        ]
        for wi, was_validated in targets:
            if all_validated and was_validated:
                callback(line_match.line_index, wi)
            elif not all_validated and not was_validated:
                callback(line_match.line_index, wi)
        # Re-render line card once after all toggles to update header stats
        self.rerender_line_card(line_match.line_index)

    # ------------------------------------------------------------------
    # Local in-memory state updates
    # ------------------------------------------------------------------

    def apply_local_word_gt_update(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> None:
        """Apply GT text update to in-memory line matches for incremental UI refresh."""
        line_match = self._view._line_match_by_index(line_index)
        if line_match is None:
            return

        target_word_match = None
        for word_match in line_match.word_matches:
            if word_match.word_index == word_index:
                target_word_match = word_match
                break
        if target_word_match is None:
            return

        normalized_gt = str(ground_truth_text or "")
        target_word_match.ground_truth_text = normalized_gt
        ocr_text = str(target_word_match.ocr_text or "")

        if not normalized_gt:
            target_word_match.match_status = MatchStatus.UNMATCHED_OCR
            target_word_match.fuzz_score = None
            return

        if ocr_text.strip() == normalized_gt.strip():
            target_word_match.match_status = MatchStatus.EXACT
            target_word_match.fuzz_score = 1.0
            return

        fuzz_score = None
        word_object = getattr(target_word_match, "word_object", None)
        if (
            word_object is not None
            and hasattr(word_object, "fuzz_score_against")
            and callable(getattr(word_object, "fuzz_score_against"))
        ):
            try:
                fuzz_score = word_object.fuzz_score_against(normalized_gt)
            except Exception:
                logger.debug(
                    "Failed to compute fuzz score for line=%s word=%s",
                    line_index,
                    word_index,
                    exc_info=True,
                )
                self._view._safe_notify_once(
                    "word-fuzz-compute",
                    "Unable to compute some fuzzy scores; using fallback matching",
                    type_="warning",
                )

        if (
            fuzz_score is not None
            and fuzz_score >= self._view.view_model.fuzz_threshold
        ):
            target_word_match.match_status = MatchStatus.FUZZY
            target_word_match.fuzz_score = fuzz_score
        else:
            target_word_match.match_status = MatchStatus.MISMATCH
            target_word_match.fuzz_score = 0.0 if fuzz_score is None else fuzz_score

    def _build_word_match_from_word_object(
        self,
        word_index: int,
        word_object: object,
    ) -> WordMatch:
        """Build a WordMatch from a line word object using current fuzz settings."""
        ocr_text = str(getattr(word_object, "text", "") or "")
        ground_truth_text = str(getattr(word_object, "ground_truth_text", "") or "")

        if not ground_truth_text:
            return WordMatch(
                ocr_text=ocr_text,
                ground_truth_text="",
                match_status=MatchStatus.UNMATCHED_OCR,
                fuzz_score=None,
                word_index=word_index,
                word_object=word_object,
            )

        if ocr_text.strip() == ground_truth_text.strip():
            return WordMatch(
                ocr_text=ocr_text,
                ground_truth_text=ground_truth_text,
                match_status=MatchStatus.EXACT,
                fuzz_score=1.0,
                word_index=word_index,
                word_object=word_object,
            )

        fuzz_score = None
        if hasattr(word_object, "fuzz_score_against") and callable(
            getattr(word_object, "fuzz_score_against")
        ):
            try:
                fuzz_score = word_object.fuzz_score_against(ground_truth_text)
            except Exception:
                logger.debug(
                    "Failed to compute fuzz score for local word match rebuild line=%s word=%s",
                    getattr(word_object, "line_index", None),
                    word_index,
                    exc_info=True,
                )
                self._view._safe_notify_once(
                    "word-local-fuzz-rebuild",
                    "Unable to compute some fuzzy scores during refresh",
                    type_="warning",
                )

        if (
            fuzz_score is not None
            and fuzz_score >= self._view.view_model.fuzz_threshold
        ):
            return WordMatch(
                ocr_text=ocr_text,
                ground_truth_text=ground_truth_text,
                match_status=MatchStatus.FUZZY,
                fuzz_score=fuzz_score,
                word_index=word_index,
                word_object=word_object,
            )

        return WordMatch(
            ocr_text=ocr_text,
            ground_truth_text=ground_truth_text,
            match_status=MatchStatus.MISMATCH,
            fuzz_score=0.0 if fuzz_score is None else fuzz_score,
            word_index=word_index,
            word_object=word_object,
        )

    def refresh_local_line_match_from_line_object(self, line_index: int) -> bool:
        """Refresh one LineMatch from its line object for targeted line rerender."""
        line_match = self._view._line_match_by_index(line_index)
        if line_match is None:
            return False

        line_object = getattr(line_match, "line_object", None)
        if line_object is None:
            return False

        words = list(getattr(line_object, "words", []) or [])
        line_match.word_matches = [
            self._build_word_match_from_word_object(word_index, word_object)
            for word_index, word_object in enumerate(words)
        ]
        line_match.ocr_line_text = str(getattr(line_object, "text", "") or "")
        line_match.ground_truth_line_text = str(
            getattr(line_object, "ground_truth_text", "") or ""
        )

        self._view.view_model._update_statistics()
        return True
