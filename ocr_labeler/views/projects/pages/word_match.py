"""Word matching view component for displaying OCR vs Ground Truth comparisons with color coding."""

from __future__ import annotations

import logging
import math
from typing import Callable, Optional, Protocol, TypeAlias, runtime_checkable

from nicegui import events, ui
from pd_book_tools.ocr.page import Page

from ....models.line_match_model import LineMatch
from ....models.word_match_model import MatchStatus, WordMatch
from ....viewmodels.project.word_match_view_model import WordMatchViewModel
from ...shared.button_styles import (
    ButtonVariant,
    style_action_button,
    style_word_icon_button,
    style_word_text_button,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class _UiElementLike(Protocol):
    is_deleted: bool
    client: object | None


WordKey: TypeAlias = tuple[int, int]
NotifyCallback: TypeAlias = Callable[[str, str], None]
SelectionChangeCallback: TypeAlias = Callable[[set[WordKey]], None]
ParagraphSelectionCallback: TypeAlias = Callable[[set[int]], None]
ReboxRequestCallback: TypeAlias = Callable[[int, int], None]
ClickEvent: TypeAlias = events.ClickEventArguments | None

SingleLineAction: TypeAlias = Callable[[int], bool]
LineIndicesAction: TypeAlias = Callable[[list[int]], bool]
ParagraphIndicesAction: TypeAlias = Callable[[list[int]], bool]
WordKeysAction: TypeAlias = Callable[[list[WordKey]], bool]
LineWordAction: TypeAlias = Callable[[int, int], bool]
SplitWordAction: TypeAlias = Callable[[int, int, float], bool]
ReboxAction: TypeAlias = Callable[[int, int, float, float, float, float], bool]
NudgeAction: TypeAlias = Callable[[int, int, float, float, float, float, bool], bool]
EditWordGroundTruthAction: TypeAlias = Callable[[int, int, str], bool]
SetWordAttributesAction: TypeAlias = Callable[[int, int, bool, bool, bool], bool]

WORD_LABEL_ITALIC = "italic"
WORD_LABEL_SMALL_CAPS = "small_caps"
WORD_LABEL_BLACKLETTER = "blackletter"


class WordMatchView:
    """View component for displaying word-level OCR vs Ground Truth matching with color coding."""

    _WORD_SLICE_CSS_REGISTERED = False

    def __init__(
        self,
        copy_gt_to_ocr_callback: SingleLineAction | None = None,
        copy_ocr_to_gt_callback: SingleLineAction | None = None,
        merge_lines_callback: LineIndicesAction | None = None,
        delete_lines_callback: LineIndicesAction | None = None,
        merge_paragraphs_callback: ParagraphIndicesAction | None = None,
        delete_paragraphs_callback: ParagraphIndicesAction | None = None,
        split_paragraph_after_line_callback: SingleLineAction | None = None,
        split_paragraph_with_selected_lines_callback: LineIndicesAction | None = None,
        split_line_after_word_callback: LineWordAction | None = None,
        delete_words_callback: WordKeysAction | None = None,
        merge_word_left_callback: LineWordAction | None = None,
        merge_word_right_callback: LineWordAction | None = None,
        split_word_callback: SplitWordAction | None = None,
        rebox_word_callback: ReboxAction | None = None,
        nudge_word_bbox_callback: NudgeAction | None = None,
        refine_words_callback: WordKeysAction | None = None,
        expand_then_refine_words_callback: WordKeysAction | None = None,
        refine_lines_callback: LineIndicesAction | None = None,
        refine_paragraphs_callback: ParagraphIndicesAction | None = None,
        edit_word_ground_truth_callback: EditWordGroundTruthAction | None = None,
        set_word_attributes_callback: SetWordAttributesAction | None = None,
        notify_callback: NotifyCallback | None = None,
        original_image_source_provider: Callable[[], str] | None = None,
    ):
        logger.debug(
            "Initializing WordMatchView with copy_gt_to_ocr_callback=%s, copy_ocr_to_gt_callback=%s",
            copy_gt_to_ocr_callback is not None,
            copy_ocr_to_gt_callback is not None,
        )
        self.view_model = WordMatchViewModel()
        self.container = None
        self.summary_label = None
        self._summary_callback: Callable[[str], None] | None = None
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
        self.split_line_after_word_callback = split_line_after_word_callback
        self.delete_words_callback = delete_words_callback
        self.merge_word_left_callback = merge_word_left_callback
        self.merge_word_right_callback = merge_word_right_callback
        self.split_word_callback = split_word_callback
        self.rebox_word_callback = rebox_word_callback
        self.nudge_word_bbox_callback = nudge_word_bbox_callback
        self.refine_words_callback = refine_words_callback
        self.expand_then_refine_words_callback = expand_then_refine_words_callback
        self.refine_lines_callback = refine_lines_callback
        self.refine_paragraphs_callback = refine_paragraphs_callback
        self._on_refine_bboxes: Callable | None = None
        self._on_expand_refine_bboxes: Callable | None = None
        self.edit_word_ground_truth_callback = edit_word_ground_truth_callback
        self.set_word_attributes_callback = set_word_attributes_callback
        self.selected_line_indices: set[int] = set()
        self.selected_word_indices: set[WordKey] = set()
        self.selected_paragraph_indices: set[int] = set()
        self._word_split_fractions: dict[WordKey, float] = {}
        self._word_split_marker_x: dict[WordKey, float] = {}
        self._word_split_image_refs: dict[WordKey, object] = {}
        self._word_split_image_sizes: dict[WordKey, tuple[float, float]] = {}
        self._word_split_button_refs: dict[WordKey, object] = {}
        self._word_checkbox_refs: dict[WordKey, object] = {}
        self._word_style_button_refs: dict[WordKey, tuple[object, object, object]] = {}
        self._word_column_refs: dict[WordKey, object] = {}
        self._line_card_refs: dict[int, object] = {}
        self._line_checkbox_refs: dict[int, object] = {}
        self._paragraph_checkbox_refs: dict[int, object] = {}
        self._word_gt_input_refs: dict[WordKey, object] = {}
        self._bbox_editor_open_keys: set[WordKey] = set()
        self._bbox_pending_deltas: dict[WordKey, tuple[float, float, float, float]] = {}
        self._bbox_nudge_step_px: int = 5
        self._selection_change_callback: SelectionChangeCallback | None = None
        self._paragraph_selection_change_callback: ParagraphSelectionCallback | None = (
            None
        )
        self._rebox_request_callback: ReboxRequestCallback | None = None
        self._pending_rebox_word_key: WordKey | None = None
        self._paragraph_expanded: dict[Optional[int], bool] = {}
        self.merge_lines_button = None
        self.delete_lines_button = None
        self.refine_lines_button = None
        self.merge_paragraphs_button = None
        self.delete_paragraphs_button = None
        self.refine_paragraphs_button = None
        self.split_paragraph_after_line_button = None
        self.split_paragraph_by_selection_button = None
        self.split_line_after_word_button = None
        self.merge_words_button = None
        self.delete_words_button = None
        self.refine_words_button = None
        self.notify_callback = notify_callback
        self._original_image_source_provider = original_image_source_provider
        self._last_word_view_source: str = ""
        self._last_display_signature = None
        self._display_update_call_count = 0
        self._display_update_render_count = 0
        self._display_update_skip_count = 0
        self._notified_error_keys: set[str] = set()
        logger.debug("WordMatchView initialization complete")

    def _safe_notify(self, message: str, type_: str = "info"):
        """Notify through callback when available, with direct UI fallback."""
        if self.notify_callback is not None:
            try:
                self.notify_callback(message, type_)
                return
            except Exception:
                logger.debug("Notify callback failed", exc_info=True)

        try:
            ui.notify(message, type=type_)
        except RuntimeError as error:
            if self._is_disposed_ui_error(error):
                logger.debug("Skipping notification during UI disposal: %s", message)
                return
            raise

    def _safe_notify_once(self, key: str, message: str, type_: str = "warning") -> None:
        """Emit a UI notification once per key to avoid repetitive toast spam."""
        if key in self._notified_error_keys:
            return
        self._notified_error_keys.add(key)
        self._safe_notify(message, type_=type_)

    def _is_disposed_ui_error(self, error: RuntimeError) -> bool:
        """Return True when runtime error indicates expected UI teardown race."""
        message = str(error).lower()
        return "client this element belongs to has been deleted" in message or (
            "parent element" in message and "deleted" in message
        )

    def _has_active_ui_context(self, element: object | None) -> bool:
        """Return True when a NiceGUI element is still attached to an active client."""
        if not isinstance(element, _UiElementLike):
            return False
        if element.is_deleted:
            return False
        return element.client is not None

    def build(self):
        """Build the UI components."""
        logger.debug("Building WordMatchView UI components")
        self._ensure_word_slice_css_registered()
        with ui.column().classes("full-width full-height") as container:
            # Header card with filter and operation controls
            with ui.card():
                with ui.column():
                    # Filter controls row
                    with ui.row().classes("items-center"):
                        ui.icon("filter_list")
                        self.filter_selector = ui.toggle(
                            options=["Mismatched Lines", "All Lines"],
                            value="Mismatched Lines",
                        )
                        self.filter_selector.on_value_change(self._on_filter_change)

                    # Page operations row
                    with ui.row().classes("items-center gap-2 full-width"):
                        ui.label("Page Operations").classes(
                            "text-sm font-semibold min-w-44 text-right"
                        )
                        if self._on_refine_bboxes:
                            self.refine_bboxes_button = ui.button(
                                "Refine Bboxes",
                                icon="auto_fix_high",
                                on_click=self._on_refine_bboxes,
                            ).tooltip("Refine all bounding boxes on this page")
                            style_action_button(self.refine_bboxes_button)
                        if self._on_expand_refine_bboxes:
                            self.expand_refine_bboxes_button = ui.button(
                                "Expand & Refine",
                                icon="zoom_out_map",
                                on_click=self._on_expand_refine_bboxes,
                            ).tooltip(
                                "Expand then refine all bounding boxes on this page"
                            )
                            style_action_button(self.expand_refine_bboxes_button)

                    # Paragraph operations row
                    with ui.row().classes("items-center gap-2 full-width"):
                        ui.label("Paragraph Operations").classes(
                            "text-sm font-semibold min-w-44 text-right"
                        )
                        self.merge_paragraphs_button = ui.button(
                            "Merge",
                            icon="call_merge",
                            on_click=self._handle_merge_selected_paragraphs,
                        ).tooltip("Merge selected paragraphs")
                        style_action_button(self.merge_paragraphs_button)
                        self.refine_paragraphs_button = ui.button(
                            "Refine",
                            icon="auto_fix_high",
                            on_click=self._handle_refine_selected_paragraphs,
                        ).tooltip("Refine selected paragraphs")
                        style_action_button(self.refine_paragraphs_button)
                        self.split_paragraph_after_line_button = ui.button(
                            "Split After",
                            icon="call_split",
                            on_click=self._handle_split_paragraph_after_selected_line,
                        ).tooltip(
                            "Split the containing paragraph immediately after the selected line"
                        )
                        style_action_button(self.split_paragraph_after_line_button)
                        self.split_paragraph_by_selection_button = ui.button(
                            "Split Select",
                            icon="call_split",
                            on_click=self._handle_split_paragraph_by_selected_lines,
                        ).tooltip(
                            "Split one paragraph into selected and unselected lines"
                        )
                        style_action_button(self.split_paragraph_by_selection_button)
                        self.delete_paragraphs_button = (
                            ui.button(
                                "Delete",
                                icon="delete",
                                on_click=self._handle_delete_selected_paragraphs,
                            )
                            .classes("ml-auto")
                            .tooltip("Delete selected paragraphs")
                        )
                        style_action_button(
                            self.delete_paragraphs_button,
                            variant=ButtonVariant.DELETE,
                        )

                    # Line operations row
                    with ui.row().classes("items-center gap-2 full-width"):
                        ui.label("Line Operations").classes(
                            "text-sm font-semibold min-w-44 text-right"
                        )
                        self.merge_lines_button = ui.button(
                            "Merge",
                            icon="call_merge",
                            on_click=self._handle_merge_selected_lines,
                        ).tooltip("Merge selected lines into the first selected line")
                        style_action_button(self.merge_lines_button)
                        self.refine_lines_button = ui.button(
                            "Refine",
                            icon="auto_fix_high",
                            on_click=self._handle_refine_selected_lines,
                        ).tooltip("Refine selected lines")
                        style_action_button(self.refine_lines_button)
                        self.split_line_after_word_button = ui.button(
                            "Split After Word",
                            icon="call_split",
                            on_click=self._handle_split_line_after_selected_word,
                        ).tooltip(
                            "Split the selected line immediately after the selected word"
                        )
                        style_action_button(self.split_line_after_word_button)
                        self.delete_lines_button = (
                            ui.button(
                                "Delete",
                                icon="delete",
                                on_click=self._handle_delete_selected_lines,
                            )
                            .classes("ml-auto")
                            .tooltip("Delete selected lines")
                        )
                        style_action_button(
                            self.delete_lines_button,
                            variant=ButtonVariant.DELETE,
                        )

                    # Word operations row
                    with ui.row().classes("items-center gap-2 full-width"):
                        ui.label("Word Operations").classes(
                            "text-sm font-semibold min-w-44 text-right"
                        )
                        self.merge_words_button = ui.button(
                            "Merge",
                            icon="call_merge",
                            on_click=self._handle_merge_selected_words,
                        ).tooltip("Merge selected words on the same line")
                        style_action_button(self.merge_words_button)
                        self.refine_words_button = ui.button(
                            "Refine",
                            icon="auto_fix_high",
                            on_click=self._handle_refine_selected_words,
                        ).tooltip("Refine selected words")
                        style_action_button(self.refine_words_button)
                        self.delete_words_button = (
                            ui.button(
                                "Delete",
                                icon="delete",
                                on_click=self._handle_delete_selected_words,
                            )
                            .classes("ml-auto")
                            .tooltip("Delete selected words")
                        )
                        style_action_button(
                            self.delete_words_button,
                            variant=ButtonVariant.DELETE,
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
            self._safe_notify("Failed to update word matches", type_="negative")
        except Exception as e:
            logger.exception(f"Error updating word match view: {e}")
            self._safe_notify("Failed to update word matches", type_="negative")

    def _update_summary(self):
        """Update the summary statistics display."""
        logger.debug("Updating summary statistics")

        stats = self.view_model.get_summary_stats()
        logger.debug("Retrieved summary stats: %s", stats)
        if stats["total_words"] == 0:
            text = "Ready to analyze word matches"
        else:
            text = (
                f"📊 {stats['total_words']} words • "
                f"✅ {stats['exact_matches']} exact ({stats['exact_percentage']:.1f}%) • "
                f"⚠️ {stats['fuzzy_matches']} fuzzy • "
                f"❌ {stats['mismatches']} mismatches • "
                f"🔵 {stats['unmatched_gt']} unmatched GT • "
                f"⚫ {stats['unmatched_ocr']} unmatched OCR • "
                f"🎯 {stats['match_percentage']:.1f}% match rate"
            )

        if self._summary_callback is not None:
            self._summary_callback(text)
        elif self._has_active_ui_context(self.summary_label):
            self.summary_label.set_text(text)
        else:
            logger.debug("No summary_label or callback available, skipping update")
            return
        logger.debug("Updated summary text: %s", text)

    def _update_lines_display(self):
        """Update the lines display with word matches."""
        self._display_update_call_count += 1
        logger.info(
            "_update_lines_display called (call=%d, rendered=%d, skipped=%d)",
            self._display_update_call_count,
            self._display_update_render_count,
            self._display_update_skip_count,
        )
        if not self._has_active_ui_context(self.lines_container):
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
        self._bbox_editor_open_keys.intersection_update(valid_split_keys)
        available_paragraph_indices = {
            line_match.paragraph_index
            for line_match in self.view_model.line_matches
            if getattr(line_match, "paragraph_index", None) is not None
        }
        self.selected_paragraph_indices.intersection_update(available_paragraph_indices)
        available_paragraph_keys = {
            getattr(line_match, "paragraph_index", None)
            for line_match in self.view_model.line_matches
        }
        self._paragraph_expanded = {
            paragraph_index: expanded
            for paragraph_index, expanded in self._paragraph_expanded.items()
            if paragraph_index in available_paragraph_keys
        }
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
        self._refresh_word_slice_source()
        self._word_split_image_refs = {}
        self._word_split_image_sizes = {}
        self._word_split_button_refs = {}
        self._word_checkbox_refs = {}
        self._word_style_button_refs = {}
        self._word_column_refs = {}
        self._line_card_refs = {}
        self._line_checkbox_refs = {}
        self._paragraph_checkbox_refs = {}
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
                paragraph_is_expanded = self._paragraph_expanded.get(
                    paragraph_index,
                    True,
                )
                with ui.column().classes("full-width"):
                    with ui.row().classes("items-center full-width no-wrap gap-1"):
                        if paragraph_index is not None:
                            paragraph_checkbox = (
                                ui.checkbox(
                                    text="",
                                    value=paragraph_index
                                    in self.selected_paragraph_indices,
                                )
                                .props("size=sm dense")
                                .classes("shrink-0 self-center")
                                .style("margin-right: 0.125rem;")
                                .on_value_change(
                                    lambda event, index=paragraph_index: (
                                        self._on_paragraph_selection_change(
                                            index,
                                            bool(event.value),
                                        )
                                    )
                                )
                            )
                            self._paragraph_checkbox_refs[paragraph_index] = (
                                paragraph_checkbox
                            )

                        toggle_icon = (
                            "expand_more" if paragraph_is_expanded else "chevron_right"
                        )
                        ui.button(
                            icon=toggle_icon,
                            on_click=lambda _event, index=paragraph_index: (
                                self._toggle_paragraph_expanded(index)
                            ),
                        ).props("flat round dense size=sm").classes("shrink-0")

                        ui.button(
                            self._format_paragraph_label(paragraph_index),
                            on_click=lambda _event, index=paragraph_index: (
                                self._toggle_paragraph_expanded(index)
                            ),
                        ).props("flat dense no-caps align=left").classes(
                            "grow justify-start text-left"
                        )

                    if paragraph_is_expanded:
                        with ui.column().classes("full-width"):
                            for line_match in paragraph_line_matches:
                                with ui.column().classes("full-width") as line_slot:
                                    self._line_card_refs[line_match.line_index] = (
                                        line_slot
                                    )
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
                    self._word_match_bbox_signature(word_match),
                    self._word_match_attribute_signature(word_match),
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
            tuple(
                sorted(
                    (paragraph_index, expanded)
                    for paragraph_index, expanded in self._paragraph_expanded.items()
                )
            ),
            tuple(sorted(self._bbox_editor_open_keys)),
            tuple(sorted(self._bbox_pending_deltas.items())),
            tuple(line_signatures),
        )

    def _word_match_bbox_signature(self, word_match: object) -> str:
        """Return a stable bbox signature for a word-match object."""
        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return ""

        bbox = getattr(word_object, "bounding_box", None)
        if bbox is None:
            return ""

        min_x = float(getattr(bbox, "minX", 0.0) or 0.0)
        min_y = float(getattr(bbox, "minY", 0.0) or 0.0)
        max_x = float(getattr(bbox, "maxX", 0.0) or 0.0)
        max_y = float(getattr(bbox, "maxY", 0.0) or 0.0)
        is_normalized = bool(getattr(bbox, "is_normalized", False))
        return f"{min_x:.6f}:{min_y:.6f}:{max_x:.6f}:{max_y:.6f}:{int(is_normalized)}"

    def _word_match_attribute_signature(self, word_match: object) -> str:
        """Return a stable signature for word style attributes."""
        italic, small_caps, blackletter = self._word_style_flags(word_match)
        return f"{int(italic)}:{int(small_caps)}:{int(blackletter)}"

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

    def set_selection_change_callback(
        self,
        callback: SelectionChangeCallback | None,
    ) -> None:
        """Register callback invoked when selected words change."""
        self._selection_change_callback = callback

    def set_paragraph_selection_change_callback(
        self,
        callback: ParagraphSelectionCallback | None,
    ) -> None:
        """Register callback invoked when selected paragraphs change."""
        self._paragraph_selection_change_callback = callback

    def set_rebox_request_callback(
        self,
        callback: ReboxRequestCallback | None,
    ) -> None:
        """Register callback invoked when user starts a word rebox request."""
        self._rebox_request_callback = callback

    def set_summary_callback(
        self,
        callback: Callable[[str], None] | None,
    ) -> None:
        """Register callback to receive summary stats text for display outside the matches tab."""
        self._summary_callback = callback

    def set_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Refine Bboxes action."""
        self._on_refine_bboxes = callback

    def set_expand_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Expand & Refine Bboxes action."""
        self._on_expand_refine_bboxes = callback

    def _emit_selection_changed(self) -> None:
        """Emit selected words to listener (for image overlay sync)."""
        if self._selection_change_callback is None:
            return
        self._selection_change_callback(set(self.selected_word_indices))

    def _emit_paragraph_selection_changed(self) -> None:
        """Emit selected paragraphs to listener (for image overlay sync)."""
        if self._paragraph_selection_change_callback is None:
            return
        self._paragraph_selection_change_callback(set(self.selected_paragraph_indices))

    def _line_match_by_index(self, line_index: int) -> LineMatch | None:
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

    def _line_paragraph_index(self, line_index: int) -> int | None:
        line_match = self._line_match_by_index(line_index)
        if line_match is None:
            return None
        paragraph_index = getattr(line_match, "paragraph_index", None)
        return paragraph_index if isinstance(paragraph_index, int) else None

    def _toggle_paragraph_expanded(self, paragraph_index: Optional[int]) -> None:
        is_expanded = self._paragraph_expanded.get(paragraph_index, True)
        self._paragraph_expanded[paragraph_index] = not is_expanded
        self._update_lines_display()

    def _paragraph_line_indices(self, paragraph_index: int) -> set[int]:
        return {
            line_match.line_index
            for line_match in self.view_model.line_matches
            if getattr(line_match, "paragraph_index", None) == paragraph_index
        }

    def _paragraph_word_keys(self, paragraph_index: int) -> set[tuple[int, int]]:
        word_keys: set[tuple[int, int]] = set()
        for line_index in self._paragraph_line_indices(paragraph_index):
            word_keys.update(self._line_word_keys(line_index))
        return word_keys

    def _is_line_fully_word_selected(self, line_index: int) -> bool:
        keys = self._line_word_keys(line_index)
        return bool(keys) and keys.issubset(self.selected_word_indices)

    def _is_paragraph_fully_line_selected(self, paragraph_index: int) -> bool:
        line_indices = self._paragraph_line_indices(paragraph_index)
        return bool(line_indices) and line_indices.issubset(self.selected_line_indices)

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

    def _sync_paragraph_selection_from_lines(self, paragraph_index: int) -> None:
        if self._is_paragraph_fully_line_selected(paragraph_index):
            self.selected_paragraph_indices.add(paragraph_index)
        else:
            self.selected_paragraph_indices.discard(paragraph_index)

    def _sync_all_paragraph_selection_from_lines(self) -> None:
        available_paragraph_indices = {
            paragraph_index
            for paragraph_index in (
                getattr(line_match, "paragraph_index", None)
                for line_match in self.view_model.line_matches
            )
            if isinstance(paragraph_index, int)
        }
        self.selected_paragraph_indices.intersection_update(available_paragraph_indices)
        for paragraph_index in available_paragraph_indices:
            self._sync_paragraph_selection_from_lines(paragraph_index)

    def _set_checkbox_value(self, checkbox: object, value: bool) -> None:
        """Best-effort checkbox update without triggering full UI rebuild."""
        setter = getattr(checkbox, "set_value", None)
        if callable(setter):
            setter(value)
            return

        logger.debug(
            "Skipping checkbox value update; set_value is unavailable for %s",
            type(checkbox).__name__,
        )

    def _refresh_line_checkbox_states(self) -> None:
        """Update rendered line-checkbox values from current selection state."""
        for line_index, checkbox in list(self._line_checkbox_refs.items()):
            if not self._has_active_ui_context(checkbox):
                self._line_checkbox_refs.pop(line_index, None)
                continue

            try:
                self._set_checkbox_value(
                    checkbox,
                    self._is_line_checked(line_index),
                )
            except RuntimeError as error:
                if self._is_disposed_ui_error(error):
                    self._line_checkbox_refs.pop(line_index, None)
                    continue
                raise
            except AttributeError:
                logger.debug(
                    "Failed to refresh line checkbox for line %s",
                    line_index,
                    exc_info=True,
                )

    def _refresh_paragraph_checkbox_states(self) -> None:
        """Update rendered paragraph-checkbox values from current selection state."""
        for paragraph_index, checkbox in list(self._paragraph_checkbox_refs.items()):
            if not self._has_active_ui_context(checkbox):
                self._paragraph_checkbox_refs.pop(paragraph_index, None)
                continue

            try:
                self._set_checkbox_value(
                    checkbox,
                    paragraph_index in self.selected_paragraph_indices,
                )
            except RuntimeError as error:
                if self._is_disposed_ui_error(error):
                    self._paragraph_checkbox_refs.pop(paragraph_index, None)
                    continue
                raise
            except AttributeError:
                logger.debug(
                    "Failed to refresh paragraph checkbox for paragraph %s",
                    paragraph_index,
                    exc_info=True,
                )

    def _refresh_word_checkbox_states(self) -> None:
        """Update rendered word-checkbox values from current selection state."""
        for selection_key, checkbox in list(self._word_checkbox_refs.items()):
            if not self._has_active_ui_context(checkbox):
                self._word_checkbox_refs.pop(selection_key, None)
                continue

            try:
                self._set_checkbox_value(
                    checkbox,
                    selection_key in self.selected_word_indices,
                )
            except RuntimeError as error:
                if self._is_disposed_ui_error(error):
                    self._word_checkbox_refs.pop(selection_key, None)
                    continue
                raise
            except AttributeError:
                logger.debug(
                    "Failed to refresh word checkbox for key %s",
                    selection_key,
                    exc_info=True,
                )

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
                        line_checkbox = (
                            ui.checkbox(
                                text="",
                                value=self._is_line_checked(line_match.line_index),
                            )
                            .props("size=sm")
                            .on_value_change(
                                lambda event, index=line_match.line_index: (
                                    self._on_line_selection_change(
                                        index,
                                        bool(event.value),
                                    )
                                )
                            )
                        )
                        self._line_checkbox_refs[line_match.line_index] = line_checkbox
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
                            gt_to_ocr_button = ui.button(
                                "GT→OCR",
                                icon="content_copy",
                            ).tooltip(
                                "Copy ground truth text to OCR text for all words in this line"
                            )
                            style_action_button(gt_to_ocr_button)
                            gt_to_ocr_button.on_click(
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
                            ocr_to_gt_button = ui.button(
                                "OCR→GT",
                                icon="content_copy",
                            ).tooltip(
                                "Copy OCR text to ground truth text for all words in this line"
                            )
                            style_action_button(ocr_to_gt_button)
                            ocr_to_gt_button.on_click(
                                lambda: self._handle_copy_ocr_to_gt(
                                    line_match.line_index
                                )
                            )

                        delete_button = ui.button(icon="delete").tooltip(
                            "Delete this line"
                        )
                        style_word_icon_button(
                            delete_button,
                            variant=ButtonVariant.DELETE,
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

    def _rerender_line_card(self, line_index: int) -> None:
        """Rerender a single line card in-place when only that line changed."""
        line_slot = self._line_card_refs.get(line_index)
        line_match = self._line_match_by_index(line_index)
        if line_slot is None or line_match is None:
            return
        if not self._has_active_ui_context(line_slot):
            self._line_card_refs.pop(line_index, None)
            return

        self._line_checkbox_refs.pop(line_index, None)
        for key in [key for key in self._word_checkbox_refs if key[0] == line_index]:
            self._word_checkbox_refs.pop(key, None)
            self._word_style_button_refs.pop(key, None)
            self._word_column_refs.pop(key, None)
            self._word_gt_input_refs.pop(key, None)
            self._word_split_button_refs.pop(key, None)
            self._word_split_image_refs.pop(key, None)
            self._word_split_image_sizes.pop(key, None)

        line_slot.clear()
        with line_slot:
            self._create_line_card(line_match)

    def _rerender_word_column(self, line_index: int, word_index: int) -> None:
        """Rerender a single OCR word column in-place when only that word changed."""
        word_key = (line_index, word_index)
        word_slot = self._word_column_refs.get(word_key)
        if word_slot is None:
            return
        if not self._has_active_ui_context(word_slot):
            self._word_column_refs.pop(word_key, None)
            return

        line_match = self._line_match_by_index(line_index)
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

        self._word_checkbox_refs.pop(word_key, None)
        self._word_style_button_refs.pop(word_key, None)
        self._word_gt_input_refs.pop(word_key, None)
        self._word_split_button_refs.pop(word_key, None)
        self._word_split_image_refs.pop(word_key, None)
        self._word_split_image_sizes.pop(word_key, None)

        word_slot.clear()
        with word_slot:
            self._create_word_selection_cell(
                line_index,
                display_word_index,
                word_index,
                len(line_match.word_matches),
            )
            self._create_image_cell(
                line_index,
                word_index,
                target_word_match,
            )
            self._create_ocr_cell(target_word_match)
            self._create_gt_cell(
                line_index,
                word_index,
                target_word_match,
            )
            self._create_status_cell(target_word_match)
            self._create_word_actions_cell(
                line_index,
                word_index,
                target_word_match,
            )

    def _apply_local_word_gt_update(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> None:
        """Apply GT text update to in-memory line matches for incremental UI refresh."""
        line_match = self._line_match_by_index(line_index)
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
                self._safe_notify_once(
                    "word-fuzz-compute",
                    "Unable to compute some fuzzy scores; using fallback matching",
                    type_="warning",
                )

        if fuzz_score is not None and fuzz_score >= self.view_model.fuzz_threshold:
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
                self._safe_notify_once(
                    "word-local-fuzz-rebuild",
                    "Unable to compute some fuzzy scores during refresh",
                    type_="warning",
                )

        if fuzz_score is not None and fuzz_score >= self.view_model.fuzz_threshold:
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

    def _refresh_local_line_match_from_line_object(self, line_index: int) -> bool:
        """Refresh one LineMatch from its line object for targeted line rerender."""
        line_match = self._line_match_by_index(line_index)
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

        self.view_model._update_statistics()
        return True

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
                        split_word_index,
                        word_match,
                    )
        logger.debug(
            "Word comparison table creation complete for line %d", line_match.line_index
        )

    def _create_word_selection_cell(
        self,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_count: int,
    ) -> None:
        """Create a selection checkbox for a word column."""
        selection_key = (line_index, word_index)
        with ui.row().classes("items-center"):
            word_checkbox = (
                ui.checkbox(
                    text="",
                    value=selection_key in self.selected_word_indices,
                )
                .props("size=xs dense")
                .tooltip("Select word")
                .on_value_change(
                    lambda event, key=selection_key: self._on_word_selection_change(
                        key,
                        bool(event.value),
                    )
                )
            )
            self._word_checkbox_refs[selection_key] = word_checkbox

            merge_button = ui.button(
                icon="call_merge",
                on_click=lambda event: self._handle_merge_word_right(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Merge with next word")
            style_word_icon_button(merge_button)
            merge_button.disabled = (
                self.merge_word_right_callback is None
                or split_word_index < 0
                or word_index >= word_count - 1
            )

            split_button = ui.button(
                icon="call_split",
                on_click=lambda event: self._handle_split_word(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Split word at selected marker")
            style_word_icon_button(split_button)
            if split_word_index >= 0:
                split_key = (line_index, split_word_index)
                self._word_split_button_refs[split_key] = split_button
            split_button.disabled = not self._is_split_action_enabled(
                line_index,
                split_word_index,
            )

            delete_button = ui.button(
                icon="delete",
                on_click=lambda event: self._handle_delete_single_word(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Delete word")
            style_word_icon_button(delete_button, variant=ButtonVariant.DELETE)
            delete_button.disabled = (
                self.delete_words_callback is None or split_word_index < 0
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
                    word_image_slice = self._get_word_image_slice(
                        word_match,
                        line_index=line_index,
                        word_index=split_word_index,
                    )
                except Exception as e:
                    logger.error(f"Error getting word image: {e}")
                    word_image_slice = None
                    ui.icon("error").classes("text-red-600").style("height: 2.25em")
                    self._safe_notify_once(
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

                    safe_bg = (
                        background_source.replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace('"', '\\"')
                    )

                    image = ui.interactive_image(
                        image_source,
                        events=["mousedown"],
                        on_mouse=lambda event, li=line_index, wi=split_word_index: (
                            self._handle_word_image_click(li, wi, event)
                        ),
                        sanitize=False,
                    ).classes("word-slice-image")
                    image.style(
                        f"width: {image_width:.2f}px; "
                        f"height: {image_height:.2f}px; "
                        f"background-image: url('{safe_bg}'); "
                        f"background-repeat: no-repeat; "
                        f"background-size: {background_width:.2f}px {background_height:.2f}px; "
                        f"background-position: -{background_x:.2f}px -{background_y:.2f}px;"
                    )
                    if split_word_index >= 0:
                        key = (line_index, split_word_index)
                        self._word_split_image_refs[key] = image
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
        input_element.focus()

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
        input_element.style(f"width: {width_chars}ch; min-width: 4ch; max-width: 100%;")

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
                return

            self._apply_local_word_gt_update(
                line_index=line_index,
                word_index=word_index,
                ground_truth_text=ground_truth_text,
            )
            self._update_summary()
            self._rerender_line_card(line_index)
            self._update_action_button_state()
            self._refresh_word_checkbox_states()
            self._refresh_line_checkbox_states()
            self._refresh_paragraph_checkbox_states()
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

    def _word_style_flags(self, word_match: object) -> tuple[bool, bool, bool]:
        """Return (italic, small_caps, blackletter) for a word match."""
        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return False, False, False

        try:
            word_labels = {str(label) for label in word_object.word_labels}
        except AttributeError:
            return False, False, False
        except TypeError:
            return False, False, False

        italic = WORD_LABEL_ITALIC in word_labels
        small_caps = WORD_LABEL_SMALL_CAPS in word_labels
        blackletter = WORD_LABEL_BLACKLETTER in word_labels
        return italic, small_caps, blackletter

    def _handle_set_word_attributes(
        self,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
    ) -> None:
        """Persist per-word style attributes via callback."""
        if self.set_word_attributes_callback is None:
            self._safe_notify(
                "Set word attributes function not available", type_="warning"
            )
            return

        if word_index < 0:
            self._safe_notify(
                "Cannot set attributes for unmatched word", type_="warning"
            )
            return

        try:
            success = self.set_word_attributes_callback(
                line_index,
                word_index,
                bool(italic),
                bool(small_caps),
                bool(blackletter),
            )
            if not success:
                self._safe_notify("Failed to update word attributes", type_="warning")
                return
            self._apply_local_word_style_update(
                line_index=line_index,
                word_index=word_index,
                italic=bool(italic),
                small_caps=bool(small_caps),
                blackletter=bool(blackletter),
            )
            self._set_word_style_button_states(
                line_index=line_index,
                word_index=word_index,
                italic=bool(italic),
                small_caps=bool(small_caps),
                blackletter=bool(blackletter),
            )
        except Exception as e:
            logger.exception(
                "Error updating word attributes (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error updating word attributes: {e}", type_="negative")

    def apply_word_style_change(
        self,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
    ) -> None:
        """Apply a targeted style-only update from state event routing."""
        self._apply_local_word_style_update(
            line_index=line_index,
            word_index=word_index,
            italic=bool(italic),
            small_caps=bool(small_caps),
            blackletter=bool(blackletter),
        )
        self._set_word_style_button_states(
            line_index=line_index,
            word_index=word_index,
            italic=bool(italic),
            small_caps=bool(small_caps),
            blackletter=bool(blackletter),
        )

    def apply_word_ground_truth_change(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> None:
        """Apply a targeted GT-only update from state event routing."""
        logger.debug(
            "[word_match_refresh] targeted.word_gt_changed.apply line=%s word=%s",
            line_index,
            word_index,
        )
        self._apply_local_word_gt_update(
            line_index=line_index,
            word_index=word_index,
            ground_truth_text=ground_truth_text,
        )
        self._update_summary()
        self._rerender_line_card(line_index)
        self._update_action_button_state()
        self._refresh_word_checkbox_states()
        self._refresh_line_checkbox_states()
        self._refresh_paragraph_checkbox_states()

    def _set_word_style_button_states(
        self,
        *,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
    ) -> None:
        """Update only I/SC/BL button colors for a word without rerendering the column."""
        key = (line_index, word_index)
        button_refs = self._word_style_button_refs.get(key)
        if button_refs is None:
            return

        if any(not self._has_active_ui_context(button) for button in button_refs):
            self._word_style_button_refs.pop(key, None)
            return

        states = (italic, small_caps, blackletter)
        for button, enabled in zip(button_refs, states, strict=False):
            try:
                if enabled:
                    button.props("color=primary")
                else:
                    button.props("color=grey-5 text-color=black")
                button.update()
            except RuntimeError as error:
                if self._is_disposed_ui_error(error):
                    self._word_style_button_refs.pop(key, None)
                    return
                raise
            except Exception:
                logger.debug(
                    "Failed to update style button state for key=%s",
                    key,
                    exc_info=True,
                )
                self._safe_notify_once(
                    "word-style-button-refresh",
                    "Failed to refresh word style controls",
                    type_="warning",
                )

    def _apply_local_word_style_update(
        self,
        *,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
    ) -> None:
        """Apply style labels locally for stable subsequent toggle computations."""
        word_match = self._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            return
        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return
        try:
            labels = [str(label) for label in word_object.word_labels]
        except AttributeError:
            return
        except TypeError:
            return

        labels_set = set(labels)
        if italic:
            labels_set.add(WORD_LABEL_ITALIC)
        else:
            labels_set.discard(WORD_LABEL_ITALIC)

        if small_caps:
            labels_set.add(WORD_LABEL_SMALL_CAPS)
        else:
            labels_set.discard(WORD_LABEL_SMALL_CAPS)

        if blackletter:
            labels_set.add(WORD_LABEL_BLACKLETTER)
        else:
            labels_set.discard(WORD_LABEL_BLACKLETTER)

        ordered = [label for label in labels if label in labels_set]
        ordered.extend(
            sorted(label for label in labels_set if label not in set(ordered))
        )
        word_object.word_labels = ordered

    def _handle_toggle_word_attribute(
        self,
        line_index: int,
        word_index: int,
        attribute: str,
        _event: ClickEvent = None,
    ) -> None:
        """Toggle one style attribute using current runtime flags (no stale closure values)."""
        word_match = self._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            self._safe_notify(
                "Cannot set attributes for unmatched word", type_="warning"
            )
            return

        italic, small_caps, blackletter = self._word_style_flags(word_match)
        if attribute == WORD_LABEL_ITALIC:
            italic = not italic
        elif attribute == WORD_LABEL_SMALL_CAPS:
            small_caps = not small_caps
        elif attribute == WORD_LABEL_BLACKLETTER:
            blackletter = not blackletter
        else:
            return

        self._handle_set_word_attributes(
            line_index,
            word_index,
            italic,
            small_caps,
            blackletter,
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
        split_word_index: int,
        word_match,
    ) -> None:
        """Create per-word action buttons displayed below each word."""
        italic, small_caps, blackletter = self._word_style_flags(word_match)
        style_button_width = "width: 3rem;"

        with ui.row().classes("items-center gap-1"):
            italic_button = (
                ui.button(
                    "I",
                    on_click=lambda event: self._handle_toggle_word_attribute(
                        line_index,
                        split_word_index,
                        WORD_LABEL_ITALIC,
                        event,
                    ),
                )
                .style(style_button_width)
                .tooltip("Toggle italic")
            )
            italic_button.disabled = (
                self.set_word_attributes_callback is None or split_word_index < 0
            )
            style_word_text_button(
                italic_button,
                variant=ButtonVariant.TOGGLE,
                active=italic,
            )

            small_caps_button = (
                ui.button(
                    "SC",
                    on_click=lambda event: self._handle_toggle_word_attribute(
                        line_index,
                        split_word_index,
                        WORD_LABEL_SMALL_CAPS,
                        event,
                    ),
                )
                .style(style_button_width)
                .tooltip("Toggle small caps")
            )
            small_caps_button.disabled = (
                self.set_word_attributes_callback is None or split_word_index < 0
            )
            style_word_text_button(
                small_caps_button,
                variant=ButtonVariant.TOGGLE,
                active=small_caps,
            )

            blackletter_button = (
                ui.button(
                    "BL",
                    on_click=lambda event: self._handle_toggle_word_attribute(
                        line_index,
                        split_word_index,
                        WORD_LABEL_BLACKLETTER,
                        event,
                    ),
                )
                .style(style_button_width)
                .tooltip("Toggle blackletter")
            )
            blackletter_button.disabled = (
                self.set_word_attributes_callback is None or split_word_index < 0
            )
            style_word_text_button(
                blackletter_button,
                variant=ButtonVariant.TOGGLE,
                active=blackletter,
            )

            if split_word_index >= 0:
                self._word_style_button_refs[(line_index, split_word_index)] = (
                    italic_button,
                    small_caps_button,
                    blackletter_button,
                )

        with ui.row().classes("items-center gap-1"):
            rebox_button = ui.button(
                icon="crop_free",
                on_click=lambda event: self._handle_start_rebox_word(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Redraw word bounding box")
            style_word_icon_button(rebox_button)
            rebox_button.disabled = (
                self.rebox_word_callback is None or split_word_index < 0
            )

            refine_button = ui.button(
                icon="auto_fix_high",
                on_click=lambda event: self._handle_refine_single_word(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Refine word bounding box")
            style_word_icon_button(refine_button)
            refine_button.disabled = (
                self.refine_words_callback is None or split_word_index < 0
            )

            expand_then_refine_button = ui.button(
                icon="unfold_more",
                on_click=lambda event: self._handle_expand_then_refine_single_word(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Expand then refine word bounding box")
            style_word_icon_button(expand_then_refine_button)
            expand_then_refine_button.disabled = (
                self.expand_then_refine_words_callback is None or split_word_index < 0
            )

            edit_bbox_button = ui.button(
                icon="tune",
                on_click=lambda event: self._toggle_bbox_fine_tune(
                    line_index,
                    split_word_index,
                    event,
                ),
            ).tooltip("Fine-tune word bbox by pixels")
            style_word_icon_button(edit_bbox_button)
            edit_bbox_button.disabled = (
                self.nudge_word_bbox_callback is None or split_word_index < 0
            )

        fine_tune_key = (line_index, split_word_index)
        if (
            fine_tune_key in self._bbox_editor_open_keys
            and self.nudge_word_bbox_callback is not None
            and split_word_index >= 0
        ):
            pending_left, pending_right, pending_top, pending_bottom = (
                self._bbox_pending_deltas.get(
                    fine_tune_key,
                    (0.0, 0.0, 0.0, 0.0),
                )
            )
            logger.debug(
                "Rendering bbox fine-tune controls for key=%s with step=%spx",
                fine_tune_key,
                self._bbox_nudge_step_px,
            )
            with ui.row().classes("items-center gap-1"):
                ui.label("Fine tune")
                ui.radio(
                    options={1: "1px", 5: "5px", 10: "10px"},
                    value=self._bbox_nudge_step_px,
                    on_change=lambda event: self._set_bbox_nudge_step(event.value),
                ).props("inline dense")
            with ui.row().classes("items-center gap-1"):
                ui.label("Left")
                left_minus_button = ui.button(
                    "X-",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=-1.0,
                        right_units=0.0,
                        top_units=0.0,
                        bottom_units=0.0,
                        _event=event,
                    ),
                )
                style_word_text_button(left_minus_button, compact=True)
                left_plus_button = ui.button(
                    "X+",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=1.0,
                        right_units=0.0,
                        top_units=0.0,
                        bottom_units=0.0,
                        _event=event,
                    ),
                )
                style_word_text_button(left_plus_button, compact=True)

                ui.label("Right")
                right_minus_button = ui.button(
                    "X-",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=0.0,
                        right_units=-1.0,
                        top_units=0.0,
                        bottom_units=0.0,
                        _event=event,
                    ),
                )
                style_word_text_button(right_minus_button, compact=True)
                right_plus_button = ui.button(
                    "X+",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=0.0,
                        right_units=1.0,
                        top_units=0.0,
                        bottom_units=0.0,
                        _event=event,
                    ),
                )
                style_word_text_button(right_plus_button, compact=True)

            with ui.row().classes("items-center gap-1"):
                ui.label("Top")
                top_minus_button = ui.button(
                    "Y-",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=0.0,
                        right_units=0.0,
                        top_units=-1.0,
                        bottom_units=0.0,
                        _event=event,
                    ),
                )
                style_word_text_button(top_minus_button, compact=True)
                top_plus_button = ui.button(
                    "Y+",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=0.0,
                        right_units=0.0,
                        top_units=1.0,
                        bottom_units=0.0,
                        _event=event,
                    ),
                )
                style_word_text_button(top_plus_button, compact=True)

                ui.label("Bottom")
                bottom_minus_button = ui.button(
                    "Y-",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=0.0,
                        right_units=0.0,
                        top_units=0.0,
                        bottom_units=-1.0,
                        _event=event,
                    ),
                )
                style_word_text_button(bottom_minus_button, compact=True)
                bottom_plus_button = ui.button(
                    "Y+",
                    on_click=lambda event: self._handle_nudge_single_word_bbox(
                        line_index,
                        split_word_index,
                        left_units=0.0,
                        right_units=0.0,
                        top_units=0.0,
                        bottom_units=1.0,
                        _event=event,
                    ),
                )
                style_word_text_button(bottom_plus_button, compact=True)

            with ui.row().classes("items-center gap-2"):
                ui.label(
                    "Pending "
                    f"L:{pending_left:.0f} "
                    f"R:{pending_right:.0f} "
                    f"T:{pending_top:.0f} "
                    f"B:{pending_bottom:.0f} px"
                ).classes("text-xs")
                reset_button = ui.button(
                    "↺",
                    on_click=lambda event: self._reset_pending_single_word_bbox_nudge(
                        line_index,
                        split_word_index,
                        event,
                    ),
                ).tooltip("Reset pending bbox edits")
                style_word_text_button(reset_button, compact=True)
                apply_button = ui.button(
                    "✓",
                    on_click=lambda event: self._apply_pending_single_word_bbox_nudge(
                        line_index,
                        split_word_index,
                        refine_after=False,
                        _event=event,
                    ),
                ).tooltip("Apply pending bbox edits")
                style_word_text_button(apply_button, compact=True)
                apply_refine_button = ui.button(
                    "✓✨",
                    on_click=lambda event: self._apply_pending_single_word_bbox_nudge(
                        line_index,
                        split_word_index,
                        refine_after=True,
                        _event=event,
                    ),
                ).tooltip("Apply pending bbox edits and refine")
                style_word_text_button(apply_refine_button, compact=True)

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
                self._safe_notify_once(
                    "word-split-marker-clear",
                    "Failed to refresh split marker overlay",
                    type_="warning",
                )
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
            self._safe_notify_once(
                "word-split-marker-render",
                "Failed to render split marker overlay",
                type_="warning",
            )

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

        italic, small_caps, blackletter = self._word_style_flags(word_match)
        active_attributes: list[str] = []
        if italic:
            active_attributes.append("italic")
        if small_caps:
            active_attributes.append("small_caps")
        if blackletter:
            active_attributes.append("blackletter")
        if active_attributes:
            lines.append(f"Attributes: {', '.join(active_attributes)}")

        if word_match.fuzz_score is not None:
            lines.append(f"Similarity: {word_match.fuzz_score:.3f}")

        if word_match.ocr_text != word_match.ground_truth_text:
            lines.append(f"OCR: '{word_match.ocr_text}'")
            lines.append(f"GT: '{word_match.ground_truth_text}'")

        return "\\n".join(lines) if lines else None

    def _get_word_image_slice(
        self,
        word_match,
        *,
        line_index: int,
        word_index: int,
    ):
        """Get client-side slice metadata for a word image from original page image."""
        logger.debug(
            "Getting word image for match with status %s", word_match.match_status.value
        )
        try:
            image_source = self._get_original_image_source()
            if not image_source:
                logger.debug("Original image source unavailable for word slicing")
                return None

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

            page_image = line_match.page_image
            preview_bbox = self._preview_bbox_for_word(
                word_match,
                page_image,
                line_index=line_index,
                word_index=word_index,
            )
            if preview_bbox is None:
                logger.debug(
                    "Preview bbox invalid for key=%s", (line_index, word_index)
                )
                return None

            page_shape = getattr(page_image, "shape", None)
            if page_shape is None or len(page_shape) < 2:
                return None
            page_height = int(page_shape[0])
            page_width = int(page_shape[1])
            if page_width <= 0 or page_height <= 0:
                return None

            encoded_width, encoded_height = self._compute_encoded_dimensions(
                page_width,
                page_height,
            )
            scale_x = float(encoded_width) / float(page_width)
            scale_y = float(encoded_height) / float(page_height)

            px1, py1, px2, py2 = preview_bbox
            sx1 = max(0, min(int(math.floor(float(px1) * scale_x)), encoded_width - 1))
            sy1 = max(0, min(int(math.floor(float(py1) * scale_y)), encoded_height - 1))
            sx2 = max(sx1 + 1, min(int(math.ceil(float(px2) * scale_x)), encoded_width))
            sy2 = max(
                sy1 + 1, min(int(math.ceil(float(py2) * scale_y)), encoded_height)
            )

            slice_width = max(1, sx2 - sx1)
            slice_height = max(1, sy2 - sy1)

            target_height = 36.0
            display_scale = target_height / float(slice_height)
            display_width = max(1.0, float(slice_width) * display_scale)
            display_height = max(1.0, float(slice_height) * display_scale)

            max_display_width = 240.0
            if display_width > max_display_width:
                display_scale = max_display_width / float(slice_width)
                display_width = max_display_width
                display_height = max(1.0, float(slice_height) * display_scale)

            bg_width = float(encoded_width) * display_scale
            bg_height = float(encoded_height) * display_scale
            bg_x = float(sx1) * display_scale
            bg_y = float(sy1) * display_scale

            return {
                "slice_source": self._build_slice_placeholder_source(
                    int(round(display_width)),
                    int(round(display_height)),
                ),
                "display_width": float(display_width),
                "display_height": float(display_height),
                "background_source": image_source,
                "background_width": float(bg_width),
                "background_height": float(bg_height),
                "background_x": float(bg_x),
                "background_y": float(bg_y),
            }

        except Exception as e:
            logger.debug(f"Error creating word image: {e}")
            return None

    def _get_original_image_source(self) -> str:
        """Return encoded original image source for client-side slice rendering."""
        provider = self._original_image_source_provider
        if provider is None:
            return ""
        try:
            return str(provider() or "")
        except Exception:
            logger.debug(
                "Failed to resolve original image source provider", exc_info=True
            )
            return ""

    def on_image_sources_updated(self, image_dict: dict[str, str]) -> None:
        """React to state image updates and rerender if word-view source changed."""
        source = str(image_dict.get("word_view_original_image_source", "") or "")
        if source == self._last_word_view_source:
            return

        self._last_word_view_source = source
        if not source:
            return
        if not self._has_active_ui_context(self.lines_container):
            return

        self._last_display_signature = None
        self._update_lines_display()

    def _refresh_word_slice_source(self) -> None:
        """Publish original image source once on the lines container as a CSS variable."""
        if self.lines_container is None:
            return

        source = self._get_original_image_source()
        if not source:
            self.lines_container.style("--wm-page-src: none;")
            return

        safe_source = source.replace("\\", "\\\\").replace("'", "\\'")
        self.lines_container.style(f"--wm-page-src: url('{safe_source}');")

    def _compute_encoded_dimensions(
        self,
        width: int,
        height: int,
        *,
        max_dimension: int = 1200,
    ) -> tuple[int, int]:
        """Mirror page image encoding resize logic for precise client-side slices."""
        if width <= 0 or height <= 0:
            return 1, 1

        if width <= max_dimension and height <= max_dimension:
            return int(width), int(height)

        if width > height:
            new_width = int(max_dimension)
            new_height = max(1, int(height * max_dimension / width))
        else:
            new_height = int(max_dimension)
            new_width = max(1, int(width * max_dimension / height))
        return new_width, new_height

    def _build_slice_placeholder_source(self, width: int, height: int) -> str:
        """Build tiny transparent SVG source that preserves interactive-image geometry."""
        safe_width = max(1, int(width))
        safe_height = max(1, int(height))
        return (
            "data:image/svg+xml;utf8,"
            "<svg xmlns='http://www.w3.org/2000/svg' "
            f"width='{safe_width}' height='{safe_height}' viewBox='0 0 {safe_width} {safe_height}'></svg>"
        )

    def _ensure_word_slice_css_registered(self) -> None:
        """Inject shared CSS for word-slice interactive image rendering once."""
        if WordMatchView._WORD_SLICE_CSS_REGISTERED:
            return

        ui.add_head_html(
            """
            <style>
            .word-slice-image {
                overflow: hidden;
                background-color: transparent;
            }
            .word-slice-image img {
                opacity: 0 !important;
            }
            </style>
            """
        )
        WordMatchView._WORD_SLICE_CSS_REGISTERED = True

    def _preview_bbox_for_word(
        self,
        word_match,
        page_image,
        *,
        line_index: int,
        word_index: int,
    ) -> tuple[int, int, int, int] | None:
        """Build clamped preview bbox in pixel coordinates for a word image crop."""
        if word_index < 0:
            return None

        shape = getattr(page_image, "shape", None)
        if shape is None or len(shape) < 2:
            return None

        page_height = int(shape[0])
        page_width = int(shape[1])
        if page_width <= 0 or page_height <= 0:
            return None

        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return None
        bbox = getattr(word_object, "bounding_box", None)
        if bbox is None:
            return None

        is_normalized = bool(getattr(bbox, "is_normalized", False))
        if is_normalized:
            x1 = float(getattr(bbox, "minX", 0.0) or 0.0) * float(page_width)
            y1 = float(getattr(bbox, "minY", 0.0) or 0.0) * float(page_height)
            x2 = float(getattr(bbox, "maxX", 0.0) or 0.0) * float(page_width)
            y2 = float(getattr(bbox, "maxY", 0.0) or 0.0) * float(page_height)
        else:
            x1 = float(getattr(bbox, "minX", 0.0) or 0.0)
            y1 = float(getattr(bbox, "minY", 0.0) or 0.0)
            x2 = float(getattr(bbox, "maxX", 0.0) or 0.0)
            y2 = float(getattr(bbox, "maxY", 0.0) or 0.0)

        left_delta, right_delta, top_delta, bottom_delta = (
            self._bbox_pending_deltas.get(
                (line_index, word_index),
                (0.0, 0.0, 0.0, 0.0),
            )
        )
        x1 -= float(left_delta)
        x2 += float(right_delta)
        y1 -= float(top_delta)
        y2 += float(bottom_delta)

        ix1 = max(0, min(int(x1), page_width - 1))
        iy1 = max(0, min(int(y1), page_height - 1))
        ix2 = max(ix1 + 1, min(int(x2), page_width))
        iy2 = max(iy1 + 1, min(int(y2), page_height))

        if ix2 <= ix1 or iy2 <= iy1:
            return None

        return ix1, iy1, ix2, iy2

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

    def _on_filter_change(self, event: events.ValueChangeEventArguments) -> None:
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
        paragraph_index = self._line_paragraph_index(line_index)
        if paragraph_index is not None:
            self._sync_paragraph_selection_from_lines(paragraph_index)
        logger.debug(
            "Line selection changed: line_index=%d selected=%s current_selection=%s",
            line_index,
            selected,
            sorted(self.selected_line_indices),
        )
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        self._refresh_word_checkbox_states()
        self._refresh_line_checkbox_states()
        self._refresh_paragraph_checkbox_states()

    def _on_word_selection_change(
        self, selection_key: tuple[int, int], selected: bool
    ) -> None:
        """Track selected words for box/checkbox-driven workflow."""
        if selected:
            self.selected_word_indices.add(selection_key)
        else:
            self.selected_word_indices.discard(selection_key)
        self._sync_line_selection_from_words(selection_key[0])
        paragraph_index = self._line_paragraph_index(selection_key[0])
        if paragraph_index is not None:
            self._sync_paragraph_selection_from_lines(paragraph_index)
        logger.debug(
            "Word selection changed: key=%s selected=%s current_words=%s",
            selection_key,
            selected,
            sorted(self.selected_word_indices),
        )
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        self._refresh_word_checkbox_states()
        self._refresh_line_checkbox_states()
        self._refresh_paragraph_checkbox_states()

    def _on_paragraph_selection_change(
        self, paragraph_index: int, selected: bool
    ) -> None:
        """Track selected paragraphs for paragraph actions."""
        paragraph_line_indices = self._paragraph_line_indices(paragraph_index)
        paragraph_word_keys = self._paragraph_word_keys(paragraph_index)

        if selected:
            self.selected_paragraph_indices.add(paragraph_index)
            self.selected_line_indices.update(paragraph_line_indices)
            self.selected_word_indices.update(paragraph_word_keys)
        else:
            self.selected_paragraph_indices.discard(paragraph_index)
            self.selected_line_indices.difference_update(paragraph_line_indices)
            self.selected_word_indices.difference_update(paragraph_word_keys)
        logger.debug(
            "Paragraph selection changed: paragraph_index=%d selected=%s current_selection=%s",
            paragraph_index,
            selected,
            sorted(self.selected_paragraph_indices),
        )
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        self._refresh_word_checkbox_states()
        self._refresh_line_checkbox_states()
        self._refresh_paragraph_checkbox_states()

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
        self._sync_all_paragraph_selection_from_lines()
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        self._refresh_word_checkbox_states()
        self._refresh_line_checkbox_states()
        self._refresh_paragraph_checkbox_states()

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
        selected_line_indices: set[int] = set()
        selected_word_indices: set[tuple[int, int]] = set()
        for paragraph_index in self.selected_paragraph_indices:
            paragraph_lines = self._paragraph_line_indices(paragraph_index)
            selected_line_indices.update(paragraph_lines)
            for line_index in paragraph_lines:
                selected_word_indices.update(self._line_word_keys(line_index))

        self.selected_line_indices = selected_line_indices
        self.selected_word_indices = selected_word_indices
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        self._refresh_word_checkbox_states()
        self._refresh_line_checkbox_states()
        self._refresh_paragraph_checkbox_states()

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

        if self.refine_lines_button is not None:
            self.refine_lines_button.disabled = (
                self.refine_lines_callback is None or len(selected_lines) < 1
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

        if self.refine_paragraphs_button is not None:
            self.refine_paragraphs_button.disabled = (
                self.refine_paragraphs_callback is None
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

        if self.split_line_after_word_button is not None:
            self.split_line_after_word_button.disabled = (
                self.split_line_after_word_callback is None
                or len(self.selected_word_indices) != 1
            )

        if self.delete_words_button is not None:
            self.delete_words_button.disabled = (
                self.delete_words_callback is None
                or len(self.selected_word_indices) < 1
            )

        if self.merge_words_button is not None:
            self.merge_words_button.disabled = (
                self.merge_word_right_callback is None
                or not self._can_merge_selected_words()
            )

        if self.refine_words_button is not None:
            self.refine_words_button.disabled = (
                self.refine_words_callback is None
                or len(self.selected_word_indices) < 1
            )

    def _handle_merge_selected_lines(self, _event: ClickEvent = None) -> None:
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
        previous_paragraph_selection = set(self.selected_paragraph_indices)
        # Clear selection before invoking merge callback because merge can trigger
        # synchronous page-state notifications and UI refreshes before callback
        # returns; stale indices may otherwise map to different visible mismatch
        # lines after reindexing.
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
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
                self.selected_paragraph_indices = previous_paragraph_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._emit_paragraph_selection_changed()
                self._safe_notify("Failed to merge selected lines", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self.selected_paragraph_indices = previous_paragraph_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            self._emit_paragraph_selection_changed()
            logger.exception("Error merging selected lines %s: %s", selected_indices, e)
            self._safe_notify(f"Error merging selected lines: {e}", type_="negative")

    def _handle_merge_selected_paragraphs(self, _event: ClickEvent = None) -> None:
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

    def _handle_delete_selected_paragraphs(self, _event: ClickEvent = None) -> None:
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

    def _handle_split_paragraph_after_selected_line(
        self,
        _event: ClickEvent = None,
    ) -> None:
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

    def _handle_split_paragraph_by_selected_lines(
        self,
        _event: ClickEvent = None,
    ) -> None:
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

    def _handle_split_line_after_selected_word(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Split the selected line immediately after one selected word."""
        if self.split_line_after_word_callback is None:
            self._safe_notify("Split line function not available", type_="warning")
            return

        if len(self.selected_word_indices) != 1:
            self._safe_notify(
                "Select exactly one word to split line",
                type_="warning",
            )
            return

        line_index, word_index = next(iter(self.selected_word_indices))
        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        previous_paragraph_selection = set(self.selected_paragraph_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        logger.info(
            "Split line requested after selected word: line=%s word=%s",
            line_index,
            word_index,
        )
        try:
            success = self.split_line_after_word_callback(line_index, word_index)
            logger.info(
                "Split line-after-word callback completed: line=%s word=%s success=%s",
                line_index,
                word_index,
                success,
            )
            if success:
                self._safe_notify(
                    f"Split line {line_index + 1} after word {word_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self.selected_paragraph_indices = previous_paragraph_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._emit_paragraph_selection_changed()
                self._safe_notify("Failed to split line", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self.selected_paragraph_indices = previous_paragraph_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            self._emit_paragraph_selection_changed()
            logger.exception(
                "Error splitting line after word line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error splitting line: {e}", type_="negative")

    def _handle_delete_selected_lines(self, _event: ClickEvent = None) -> None:
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

    def _handle_delete_selected_words(self, _event: ClickEvent = None) -> None:
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

    def _can_merge_selected_words(self) -> bool:
        """Return True when current selected words can be merged as one block."""
        selected_words = sorted(self.selected_word_indices)
        if len(selected_words) < 2:
            return False

        selected_line_indices = {line_index for line_index, _ in selected_words}
        if len(selected_line_indices) != 1:
            return False

        word_indices = [word_index for _, word_index in selected_words]
        expected_indices = list(range(word_indices[0], word_indices[-1] + 1))
        return word_indices == expected_indices

    def _handle_merge_selected_words(self, _event: ClickEvent = None) -> None:
        """Merge selected contiguous words into one word on a single line."""
        if self.merge_word_right_callback is None:
            self._safe_notify("Merge word function not available", type_="warning")
            return

        if len(self.selected_word_indices) < 2:
            self._safe_notify("Select at least two words to merge", type_="warning")
            return

        if not self._can_merge_selected_words():
            self._safe_notify(
                "Select contiguous words on a single line to merge",
                type_="warning",
            )
            return

        selected_words = sorted(self.selected_word_indices)
        line_index = selected_words[0][0]
        base_word_index = selected_words[0][1]
        merge_count = len(selected_words) - 1

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()

        logger.info("Merge requested for selected words: %s", selected_words)
        try:
            success = True
            for _ in range(merge_count):
                if not self.merge_word_right_callback(line_index, base_word_index):
                    success = False
                    break

            if success:
                self._safe_notify(
                    f"Merged {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to merge selected words", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception("Error merging selected words %s: %s", selected_words, e)
            self._safe_notify(f"Error merging selected words: {e}", type_="negative")

    def _handle_refine_selected_words(self, _event: ClickEvent = None) -> None:
        """Refine selected word bounding boxes."""
        if self.refine_words_callback is None:
            self._safe_notify("Refine word function not available", type_="warning")
            return

        selected_words = sorted(self.selected_word_indices)
        if not selected_words:
            self._safe_notify("Select at least one word to refine", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.refine_words_callback(selected_words)
            if success:
                self._safe_notify(
                    f"Refined {len(selected_words)} words",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to refine selected words", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception("Error refining words %s: %s", selected_words, e)
            self._safe_notify(f"Error refining words: {e}", type_="negative")

    def _handle_refine_selected_lines(self, _event: ClickEvent = None) -> None:
        """Refine selected lines."""
        if self.refine_lines_callback is None:
            self._safe_notify("Refine line function not available", type_="warning")
            return

        selected_lines = self._get_effective_selected_lines()
        if not selected_lines:
            self._safe_notify("Select at least one line to refine", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.refine_lines_callback(selected_lines)
            if success:
                self._safe_notify(
                    f"Refined {len(selected_lines)} lines",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to refine selected lines", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception("Error refining lines %s: %s", selected_lines, e)
            self._safe_notify(f"Error refining lines: {e}", type_="negative")

    def _handle_refine_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Refine selected paragraphs."""
        if self.refine_paragraphs_callback is None:
            self._safe_notify(
                "Refine paragraph function not available", type_="warning"
            )
            return

        selected_paragraphs = sorted(self.selected_paragraph_indices)
        if not selected_paragraphs:
            self._safe_notify(
                "Select at least one paragraph to refine", type_="warning"
            )
            return

        previous_selection = set(self.selected_paragraph_indices)
        self.selected_paragraph_indices.clear()
        self._update_action_button_state()
        self._emit_paragraph_selection_changed()
        try:
            success = self.refine_paragraphs_callback(selected_paragraphs)
            if success:
                self._safe_notify(
                    f"Refined {len(selected_paragraphs)} paragraphs",
                    type_="positive",
                )
            else:
                self.selected_paragraph_indices = previous_selection
                self._update_action_button_state()
                self._emit_paragraph_selection_changed()
                self._safe_notify(
                    "Failed to refine selected paragraphs", type_="warning"
                )
        except Exception as e:
            self.selected_paragraph_indices = previous_selection
            self._update_action_button_state()
            self._emit_paragraph_selection_changed()
            logger.exception(
                "Error refining paragraphs %s: %s",
                selected_paragraphs,
                e,
            )
            self._safe_notify(f"Error refining paragraphs: {e}", type_="negative")

    def _handle_refine_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Refine a single word bbox."""
        if self.refine_words_callback is None:
            self._safe_notify("Refine word function not available", type_="warning")
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word to refine", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.refine_words_callback([(line_index, word_index)])
            if success:
                self._rerender_word_column(line_index, word_index)
                self._safe_notify(
                    f"Refined word {word_index + 1} on line {line_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to refine word", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error refining word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error refining word: {e}", type_="negative")

    def _handle_expand_then_refine_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Expand then refine a single word bbox."""
        if self.expand_then_refine_words_callback is None:
            self._safe_notify(
                "Expand-then-refine function not available",
                type_="warning",
            )
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word to refine", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()
        try:
            success = self.expand_then_refine_words_callback([(line_index, word_index)])
            if success:
                self._rerender_word_column(line_index, word_index)
                self._safe_notify(
                    (
                        f"Expanded then refined word {word_index + 1} "
                        f"on line {line_index + 1}"
                    ),
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to expand then refine word", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error expand-then-refining word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(
                f"Error expanding then refining word: {e}",
                type_="negative",
            )

    def _handle_delete_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
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
                self._refresh_local_line_match_from_line_object(line_index)
                self._update_summary()
                self._rerender_line_card(line_index)
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

    def _handle_merge_word_left(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
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
                self._refresh_local_line_match_from_line_object(line_index)
                self._update_summary()
                self._rerender_line_card(line_index)
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

    def _handle_merge_word_right(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
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
                self._refresh_local_line_match_from_line_object(line_index)
                self._update_summary()
                self._rerender_line_card(line_index)
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

    def _handle_split_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
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
                self._refresh_local_line_match_from_line_object(line_index)
                self._update_summary()
                self._rerender_line_card(line_index)
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

    def _handle_start_rebox_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Start rebox mode for a selected word."""
        if self.rebox_word_callback is None:
            self._safe_notify("Rebox word function not available", type_="warning")
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word to rebox", type_="warning")
            return

        self._pending_rebox_word_key = (line_index, word_index)
        if self._rebox_request_callback is not None:
            try:
                self._rebox_request_callback(line_index, word_index)
            except Exception:
                logger.debug("Rebox request callback failed", exc_info=True)
        self._safe_notify(
            (
                f"Rebox word {word_index + 1} on line {line_index + 1}: "
                "draw a new rectangle on the Words image"
            ),
            type_="info",
        )

    def _toggle_bbox_fine_tune(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Toggle fine-tune controls for a single word bbox."""
        if self.nudge_word_bbox_callback is None:
            self._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word bbox to edit", type_="warning")
            return
        key = (line_index, word_index)
        try:
            if key in self._bbox_editor_open_keys:
                self._bbox_editor_open_keys.remove(key)
                self._bbox_pending_deltas.pop(key, None)
                logger.debug("Closed bbox fine-tune controls for key=%s", key)
            else:
                self._bbox_editor_open_keys.add(key)
                logger.debug("Opened bbox fine-tune controls for key=%s", key)
            self._rerender_word_column(line_index, word_index)
        except Exception as e:
            logger.exception("Error toggling bbox fine-tune controls for key=%s", key)
            self._safe_notify(
                f"Error opening fine-tune controls: {e}", type_="negative"
            )
            raise

    def _set_bbox_nudge_step(self, value: object) -> None:
        """Set active bbox nudge step in pixels."""
        try:
            step = int(float(value))

            if step <= 0:
                logger.debug("Ignored invalid non-positive bbox nudge step: %s", value)
                return
            if step == self._bbox_nudge_step_px:
                logger.debug("BBox nudge step unchanged at %spx", step)
                return

            logger.debug(
                "Updating bbox nudge step from %spx to %spx",
                self._bbox_nudge_step_px,
                step,
            )
            self._bbox_nudge_step_px = step
            for line_index, word_index in sorted(self._bbox_editor_open_keys):
                self._rerender_word_column(line_index, word_index)
        except Exception as e:
            logger.exception("Error updating bbox nudge step from value=%s", value)
            self._safe_notify(f"Error updating nudge step: {e}", type_="negative")
            raise

    def _handle_nudge_single_word_bbox(
        self,
        line_index: int,
        word_index: int,
        *,
        left_units: float,
        right_units: float,
        top_units: float,
        bottom_units: float,
        _event: ClickEvent = None,
    ) -> None:
        """Accumulate a pending bbox nudge for a single word."""
        if self.nudge_word_bbox_callback is None:
            self._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word bbox to edit", type_="warning")
            return

        key = (line_index, word_index)
        try:
            left_delta = float(left_units) * float(self._bbox_nudge_step_px)
            right_delta = float(right_units) * float(self._bbox_nudge_step_px)
            top_delta = float(top_units) * float(self._bbox_nudge_step_px)
            bottom_delta = float(bottom_units) * float(self._bbox_nudge_step_px)
            current_left, current_right, current_top, current_bottom = (
                self._bbox_pending_deltas.get(
                    key,
                    (0.0, 0.0, 0.0, 0.0),
                )
            )
            self._bbox_pending_deltas[key] = (
                current_left + left_delta,
                current_right + right_delta,
                current_top + top_delta,
                current_bottom + bottom_delta,
            )
            self._rerender_word_column(line_index, word_index)
        except Exception as e:
            logger.exception(
                "Error accumulating nudge for word bbox (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(
                f"Error updating pending bbox edit: {e}", type_="negative"
            )
            raise

    def _reset_pending_single_word_bbox_nudge(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Reset pending bbox deltas for a single word."""
        key = (line_index, word_index)
        self._bbox_pending_deltas.pop(key, None)
        self._rerender_word_column(line_index, word_index)

    def _apply_pending_single_word_bbox_nudge(
        self,
        line_index: int,
        word_index: int,
        refine_after: bool = True,
        _event: ClickEvent = None,
    ) -> None:
        """Apply pending bbox deltas for a single word.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            refine_after: Whether to run refine after applying nudge.
            _event: Optional click event.
        """
        if self.nudge_word_bbox_callback is None:
            self._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._safe_notify("Select a valid OCR word bbox to edit", type_="warning")
            return

        key = (line_index, word_index)
        left_delta, right_delta, top_delta, bottom_delta = (
            self._bbox_pending_deltas.get(
                key,
                (0.0, 0.0, 0.0, 0.0),
            )
        )
        if (
            left_delta == 0.0
            and right_delta == 0.0
            and top_delta == 0.0
            and bottom_delta == 0.0
        ):
            self._safe_notify("No pending bbox edits to apply", type_="warning")
            return

        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()

        try:
            success = self.nudge_word_bbox_callback(
                line_index,
                word_index,
                left_delta,
                right_delta,
                top_delta,
                bottom_delta,
                refine_after,
            )
            if success:
                self._bbox_pending_deltas.pop(key, None)
                self._rerender_word_column(line_index, word_index)
                if refine_after:
                    self._safe_notify(
                        "Applied bbox fine-tune edits and refined",
                        type_="positive",
                    )
                else:
                    self._safe_notify("Applied bbox fine-tune edits", type_="positive")
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to apply bbox edits", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error applying pending bbox nudge (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error applying bbox edits: {e}", type_="negative")
            raise

    def apply_rebox_bbox(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Apply a drawn bbox to the currently pending rebox word target."""
        if self.rebox_word_callback is None:
            self._safe_notify("Rebox word function not available", type_="warning")
            return

        target_key = self._pending_rebox_word_key
        if target_key is None:
            self._safe_notify("No active word rebox request", type_="warning")
            return

        line_index, word_index = target_key
        previous_line_selection = set(self.selected_line_indices)
        previous_word_selection = set(self.selected_word_indices)
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self._update_action_button_state()
        self._emit_selection_changed()

        try:
            success = self.rebox_word_callback(
                line_index,
                word_index,
                x1,
                y1,
                x2,
                y2,
            )
            if success:
                self._pending_rebox_word_key = None
                self._rerender_word_column(line_index, word_index)
                self._safe_notify(
                    f"Reboxed word {word_index + 1} on line {line_index + 1}",
                    type_="positive",
                )
            else:
                self.selected_line_indices = previous_line_selection
                self.selected_word_indices = previous_word_selection
                self._update_action_button_state()
                self._emit_selection_changed()
                self._safe_notify("Failed to rebox word", type_="warning")
        except Exception as e:
            self.selected_line_indices = previous_line_selection
            self.selected_word_indices = previous_word_selection
            self._update_action_button_state()
            self._emit_selection_changed()
            logger.exception(
                "Error reboxing word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._safe_notify(f"Error reboxing word: {e}", type_="negative")

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
        if self._summary_callback is not None:
            self._summary_callback("No matches to display")
        elif self.summary_label:
            self.summary_label.set_text("No matches to display")
        logger.debug("Reset summary label text")
        self._last_display_signature = None
        self._display_update_call_count = 0
        self._display_update_render_count = 0
        self._display_update_skip_count = 0
        self.selected_line_indices.clear()
        self.selected_word_indices.clear()
        self.selected_paragraph_indices.clear()
        self._bbox_editor_open_keys.clear()
        self._bbox_pending_deltas.clear()
        self._word_style_button_refs = {}
        self._word_column_refs = {}
        self._pending_rebox_word_key = None
        self._update_action_button_state()
        self._emit_selection_changed()
        self._emit_paragraph_selection_changed()
        logger.debug("WordMatchView clear complete")
