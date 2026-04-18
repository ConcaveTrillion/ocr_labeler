"""Word matching view component for displaying OCR vs Ground Truth comparisons with color coding."""

from __future__ import annotations

import logging
from typing import Callable, Optional, Protocol, TypeAlias, runtime_checkable

from nicegui import events, ui
from pd_book_tools.ocr.page import Page

from ....models.line_match_model import LineMatch
from ....models.word_match_model import WordMatch
from ....operations.ocr.word_operations import WordOperations
from ....viewmodels.project.word_match_view_model import WordMatchViewModel
from .word_match_actions import WordMatchActions
from .word_match_bbox import WordMatchBbox
from .word_match_gt_editing import WordMatchGtEditing
from .word_match_renderer import WordMatchRenderer
from .word_match_selection import WordMatchSelection
from .word_match_toolbar import WordMatchToolbar
from .word_operations import SelectedWordOperationsProcessor

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
SetWordAttributesAction: TypeAlias = Callable[
    [int, int, bool, bool, bool, bool, bool], bool
]

WORD_LABEL_ITALIC = "italic"
WORD_LABEL_SMALL_CAPS = "small_caps"
WORD_LABEL_BLACKLETTER = "blackletter"
WORD_LABEL_LEFT_FOOTNOTE = "left_footnote"
WORD_LABEL_RIGHT_FOOTNOTE = "right_footnote"


class WordMatchView:
    """View component for displaying word-level OCR vs Ground Truth matching with color coding."""

    def __init__(
        self,
        copy_gt_to_ocr_callback: SingleLineAction | None = None,
        copy_ocr_to_gt_callback: SingleLineAction | None = None,
        copy_selected_words_ocr_to_gt_callback: WordKeysAction | None = None,
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
        split_word_vertical_closest_line_callback: SplitWordAction | None = None,
        rebox_word_callback: ReboxAction | None = None,
        add_word_callback: Callable[[float, float, float, float], bool] | None = None,
        nudge_word_bbox_callback: NudgeAction | None = None,
        refine_words_callback: WordKeysAction | None = None,
        expand_then_refine_words_callback: WordKeysAction | None = None,
        refine_lines_callback: LineIndicesAction | None = None,
        expand_then_refine_lines_callback: LineIndicesAction | None = None,
        refine_paragraphs_callback: ParagraphIndicesAction | None = None,
        expand_then_refine_paragraphs_callback: ParagraphIndicesAction | None = None,
        split_line_with_selected_words_callback: WordKeysAction | None = None,
        split_lines_into_selected_unselected_callback: WordKeysAction | None = None,
        group_selected_words_into_paragraph_callback: WordKeysAction | None = None,
        edit_word_ground_truth_callback: EditWordGroundTruthAction | None = None,
        set_word_attributes_callback: SetWordAttributesAction | None = None,
        toggle_word_validated_callback: LineWordAction | None = None,
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
        self.filter_mode = "Unvalidated Lines"  # Default filter mode
        self.copy_gt_to_ocr_callback = copy_gt_to_ocr_callback
        self.copy_ocr_to_gt_callback = copy_ocr_to_gt_callback
        self.copy_selected_words_ocr_to_gt_callback = (
            copy_selected_words_ocr_to_gt_callback
        )
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
        self.split_word_vertical_closest_line_callback = (
            split_word_vertical_closest_line_callback
        )
        self.rebox_word_callback = rebox_word_callback
        self.add_word_callback: Callable[[float, float, float, float], bool] | None = (
            add_word_callback
        )
        self.nudge_word_bbox_callback = nudge_word_bbox_callback
        self.refine_words_callback = refine_words_callback
        self.expand_then_refine_words_callback = expand_then_refine_words_callback
        self.refine_lines_callback = refine_lines_callback
        self.expand_then_refine_lines_callback = expand_then_refine_lines_callback
        self.refine_paragraphs_callback = refine_paragraphs_callback
        self.expand_then_refine_paragraphs_callback = (
            expand_then_refine_paragraphs_callback
        )
        self.split_line_with_selected_words_callback = (
            split_line_with_selected_words_callback
        )
        self.split_lines_into_selected_unselected_callback = (
            split_lines_into_selected_unselected_callback
        )
        self.group_selected_words_into_paragraph_callback = (
            group_selected_words_into_paragraph_callback
        )
        self._on_refine_bboxes: Callable | None = None
        self._on_expand_refine_bboxes: Callable | None = None
        self.edit_word_ground_truth_callback = edit_word_ground_truth_callback
        self.set_word_attributes_callback = set_word_attributes_callback
        self.toggle_word_validated_callback = toggle_word_validated_callback
        self.selection = WordMatchSelection(self)
        self.toolbar = WordMatchToolbar(self)
        self.gt_editing = WordMatchGtEditing(self)
        self.bbox = WordMatchBbox(self)
        self.actions = WordMatchActions(self)
        self.word_operations = SelectedWordOperationsProcessor(
            self,
            set_word_attributes_callback,
            refresh_word_callback=self._refresh_word_after_local_operation,
        )
        self.renderer = WordMatchRenderer(self)
        self.bbox._original_image_source_provider = original_image_source_provider
        self._word_split_fractions: dict[WordKey, float] = {}
        self._word_split_y_fractions: dict[WordKey, float] = {}
        self._word_split_marker_x: dict[WordKey, float] = {}
        self._word_split_marker_y: dict[WordKey, float] = {}
        self._word_split_hover_keys: set[WordKey] = set()
        self._word_split_hover_positions: dict[WordKey, tuple[float, float]] = {}
        self._word_split_image_refs: dict[WordKey, object] = {}
        self._word_split_image_sizes: dict[WordKey, tuple[float, float]] = {}
        self._word_split_button_refs: dict[WordKey, object] = {}
        self._word_vertical_split_button_refs: dict[WordKey, object] = {}
        self._word_crop_button_refs: dict[
            WordKey, tuple[object, object, object, object]
        ] = {}
        self.notify_callback = notify_callback
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
        self.bbox.ensure_word_slice_css_registered()
        with ui.column().classes("full-width full-height gap-0") as container:
            with (
                ui.row()
                .classes("items-center gap-1 q-px-sm q-py-none")
                .style("margin: 0; padding-top: 2px; padding-bottom: 2px;")
            ):
                ui.icon("filter_list")
                self.filter_selector = ui.toggle(
                    options=["Unvalidated Lines", "Mismatched Lines", "All Lines"],
                    value="Unvalidated Lines",
                )
                self.filter_selector.on_value_change(self._on_filter_change)

            # Scrollable container for word matches
            with (
                ui.column()
                .classes("fit overflow-auto q-pa-none")
                .style("padding: 0; margin: 0;")
            ):
                self.lines_container = (
                    ui.column()
                    .classes("full-width")
                    .style("gap: 0; padding: 0; margin: 0;")
                )

        self.container = container
        logger.debug("WordMatchView UI build complete, container created")
        return container

    def build_actions_toolbar(self):
        """Build the scope-action icon grid (Page/Paragraph/Line/Word operations)."""
        self.toolbar.build_actions_toolbar()

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
            self.selection.selected_line_indices.clear()
            self.selection.selected_word_indices.clear()
            self.selection.selected_paragraph_indices.clear()
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
                f"🎯 {stats['match_percentage']:.1f}% match rate • "
                f"☑️ {stats['validated_words']}/{stats['total_words']} validated"
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
        self.renderer.update_lines_display()

    def _compute_display_signature(self):
        """Return a stable signature for visible line-match content."""
        return self.renderer._compute_display_signature()

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
        italic, small_caps, blackletter, left_footnote, right_footnote = (
            self._word_style_flags(word_match)
        )
        is_validated = getattr(word_match, "is_validated", False)
        return f"{int(italic)}:{int(small_caps)}:{int(blackletter)}:{int(left_footnote)}:{int(right_footnote)}:{int(is_validated)}"

    def _group_lines_by_paragraph(self, line_matches: list[LineMatch]):
        """Group line matches by paragraph index, keeping unassigned lines last."""
        return self.renderer._group_lines_by_paragraph(line_matches)

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
        self.selection.set_selection_change_callback(callback)

    def set_paragraph_selection_change_callback(
        self,
        callback: ParagraphSelectionCallback | None,
    ) -> None:
        """Register callback invoked when selected paragraphs change."""
        self.selection.set_paragraph_selection_change_callback(callback)

    def set_rebox_request_callback(
        self,
        callback: ReboxRequestCallback | None,
    ) -> None:
        """Register callback invoked when user starts a word rebox request."""
        self.bbox.set_rebox_request_callback(callback)

    def set_add_word_request_callback(
        self,
        callback: Callable[[], None] | None,
    ) -> None:
        """Register callback invoked when user requests to start an add-word draw."""
        self.bbox.set_add_word_request_callback(callback)

    def apply_add_word_bbox(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Forward drawn add-word rectangle to bbox handler."""
        self.bbox.apply_add_word_bbox(x1, y1, x2, y2)

    def set_summary_callback(
        self,
        callback: Callable[[str], None] | None,
    ) -> None:
        """Register callback to receive summary stats text for display outside the matches tab."""
        self._summary_callback = callback

    def set_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Refine Bboxes action."""
        self._on_refine_bboxes = callback
        self.toolbar.set_refine_bboxes_callback(callback)

    def set_expand_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Expand & Refine Bboxes action."""
        self._on_expand_refine_bboxes = callback
        self.toolbar.set_expand_refine_bboxes_callback(callback)

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
        self.renderer._toggle_paragraph_expanded(paragraph_index)

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

    def _create_line_card(self, line_match):
        """Create a card display for a single line match."""
        self.renderer._create_line_card(line_match)

    def _build_word_match_from_word_object(
        self,
        word_index: int,
        word_object: object,
    ) -> WordMatch:
        """Build a WordMatch from a line word object using current fuzz settings."""
        return self.renderer._build_word_match_from_word_object(word_index, word_object)

    def _refresh_local_line_match_from_line_object(self, line_index: int) -> bool:
        """Refresh one LineMatch from its line object for targeted line rerender."""
        return self.renderer.refresh_local_line_match_from_line_object(line_index)

    def _create_word_comparison_table(self, line_match):
        """Create a table layout with each column representing one complete word item."""
        self.renderer._create_word_comparison_table(line_match)

    def _create_word_selection_cell(
        self,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_count: int,
        word_match,
    ) -> None:
        """Create compact per-word controls for fast initial rendering."""
        self.renderer._create_word_selection_cell(
            line_index,
            word_index,
            split_word_index,
            word_count,
            word_match,
        )

    def _open_word_edit_dialog(
        self,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_match,
    ) -> None:
        """Open the extracted word edit dialog module."""
        self.renderer._open_word_edit_dialog(
            line_index,
            word_index,
            split_word_index,
            word_match,
        )

    def _handle_crop_word_to_marker(
        self,
        line_index: int,
        word_index: int,
        direction: str,
        _event: ClickEvent = None,
    ) -> None:
        """Trim current word bbox on the named side using marker-based fraction."""
        self.bbox.handle_crop_word_to_marker(line_index, word_index, direction, _event)

    def _create_ocr_cell(self, word_match):
        """Create OCR text cell for a word."""
        self.renderer._create_ocr_cell(word_match)

    def _word_style_flags(
        self, word_match: object
    ) -> tuple[bool, bool, bool, bool, bool]:
        """Return (italic, small_caps, blackletter, left_footnote, right_footnote) for a word match."""
        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return False, False, False, False, False

        word_ops = WordOperations()
        italic = word_ops.read_word_attribute(
            word_object, "italic", aliases=("is_italic",)
        )
        small_caps = word_ops.read_word_attribute(
            word_object,
            "small_caps",
            aliases=("is_small_caps",),
        )
        blackletter = word_ops.read_word_attribute(
            word_object,
            "blackletter",
            aliases=("is_blackletter",),
        )
        footnote_marker = word_ops.read_word_attribute(
            word_object,
            "left_footnote",
            aliases=("is_left_footnote",),
        )
        return italic, small_caps, blackletter, footnote_marker, footnote_marker

    def _handle_set_word_attributes(
        self,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._handle_set_word_attributes(
            line_index,
            word_index,
            italic,
            small_caps,
            blackletter,
            left_footnote,
            right_footnote,
        )

    def apply_word_style_change(
        self,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> None:
        """Apply a targeted style-only update from state event routing."""
        self.gt_editing.apply_word_style_change(
            line_index,
            word_index,
            italic,
            small_caps,
            blackletter,
            left_footnote,
            right_footnote,
        )

    def apply_word_ground_truth_change(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> None:
        """Apply a targeted GT-only update from state event routing."""
        self.gt_editing.apply_word_ground_truth_change(
            line_index,
            word_index,
            ground_truth_text,
        )

    def apply_word_validation_change(
        self,
        line_index: int,
        word_index: int,
        is_validated: bool,
    ) -> None:
        """Apply a targeted validation-only update from state event routing.

        Updates the in-memory model and statistics only.  Callers (renderer
        click handlers, toolbar bulk handlers) are responsible for triggering
        the appropriate rerender so that single-word and bulk toggles can
        each choose the most efficient rendering strategy.
        """
        line_match = self._line_match_by_index(line_index)
        if line_match is None:
            return
        for wm in line_match.word_matches:
            if wm.word_index == word_index:
                wm.is_validated = is_validated
                break
        self.view_model._update_statistics()
        self._update_summary()

    def _set_word_style_button_states(self, **kwargs) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._set_word_style_button_states(**kwargs)

    def _apply_local_word_style_update(self, **kwargs) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._apply_local_word_style_update(**kwargs)

    def _handle_toggle_word_attribute(
        self,
        line_index: int,
        word_index: int,
        attribute: str,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._handle_toggle_word_attribute(
            line_index,
            word_index,
            attribute,
            _event,
        )

    def _handle_word_gt_edit(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._handle_word_gt_edit(
            line_index,
            word_index,
            ground_truth_text,
        )

    def _commit_word_gt_input_change(
        self,
        line_index: int,
        word_index: int,
        input_element,
    ) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._commit_word_gt_input_change(
            line_index,
            word_index,
            input_element,
        )

    def _next_word_gt_key(
        self,
        current_key: tuple[int, int],
        reverse: bool = False,
    ) -> tuple[int, int] | None:
        """Delegate to gt_editing."""
        return self.gt_editing._next_word_gt_key(current_key, reverse=reverse)

    def _word_gt_input_width_chars(self, value: str, fallback_text: str) -> int:
        """Delegate to gt_editing."""
        return self.gt_editing._word_gt_input_width_chars(value, fallback_text)

    def _handle_word_gt_keydown(self, event, current_key: tuple[int, int]) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._handle_word_gt_keydown(event, current_key)

    def _handle_word_gt_tab_navigation(
        self,
        current_key: tuple[int, int],
        is_reverse: bool,
    ) -> None:
        """Delegate to gt_editing."""
        self.gt_editing._handle_word_gt_tab_navigation(current_key, is_reverse)

    def _create_status_cell(self, word_match):
        """Create status cell for a word."""
        self.renderer._create_status_cell(word_match)

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

    def _refresh_open_word_dialog_for(self, line_index: int, word_index: int) -> None:
        """Refresh an open word-edit dialog in-place for the active key."""
        self.renderer.refresh_open_word_dialog_for(line_index, word_index)

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

    def _is_vertical_split_action_enabled(
        self, line_index: int, word_index: int
    ) -> bool:
        if self.split_word_vertical_closest_line_callback is None or word_index < 0:
            return False

        word_match = self._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            return False
        word_text = str(getattr(word_match, "ocr_text", "") or "")
        if len(word_text) < 2:
            return False

        return (line_index, word_index) in self._word_split_fractions

    def _split_failure_reason(
        self,
        line_index: int,
        word_index: int,
        split_fraction: float | None,
        *,
        vertical: bool = False,
    ) -> str:
        """Return a specific user-facing reason when a split callback returns False."""
        axis_label = "vertically" if vertical else "horizontally"
        if split_fraction is None:
            return "Click inside the word image to choose split position"

        if split_fraction <= 0.0 or split_fraction >= 1.0:
            return (
                "Split marker is out of bounds; click again inside the word image "
                "before splitting"
            )

        word_match = self._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            return (
                f"Selected word no longer exists on line {line_index + 1}; "
                "refresh and try again"
            )

        word_text = str(getattr(word_match, "ocr_text", "") or "")
        if len(word_text) < 2:
            shown_word = word_text if word_text else "[empty]"
            return (
                f"Cannot split {shown_word!r} {axis_label}: "
                "word must contain at least 2 characters"
            )

        word_object = getattr(word_match, "word_object", None)
        bbox = getattr(word_object, "bounding_box", None)
        bbox_width = float(getattr(bbox, "width", 0.0) or 0.0)
        if bbox is None or bbox_width <= 0.0:
            return "Cannot split: word has an invalid bounding box"

        if vertical:
            return (
                "Unable to split vertically and reassign to closest lines; "
                "try a different marker position"
            )
        return "Unable to split word at the selected position; try a different marker"

    def _create_word_text_display(self, word_matches, text_type):
        """Create a display of words with appropriate coloring."""
        self.renderer._create_word_text_display(word_matches, text_type)

    def _create_word_tooltip(self, word_match):
        """Create tooltip content for a word match."""
        lines = [f"Status: {word_match.match_status.value.title()}"]

        italic, small_caps, blackletter, left_footnote, right_footnote = (
            self._word_style_flags(word_match)
        )
        active_attributes: list[str] = []
        if italic:
            active_attributes.append("italic")
        if small_caps:
            active_attributes.append("small_caps")
        if blackletter:
            active_attributes.append("blackletter")
        if left_footnote or right_footnote:
            active_attributes.append("footnote_marker")
        if active_attributes:
            lines.append(f"Attributes: {', '.join(active_attributes)}")

        if word_match.fuzz_score is not None:
            lines.append(f"Similarity: {word_match.fuzz_score:.3f}")

        if word_match.ocr_text != word_match.ground_truth_text:
            lines.append(f"OCR: '{word_match.ocr_text}'")
            lines.append(f"GT: '{word_match.ground_truth_text}'")

        return "\\n".join(lines) if lines else None

    def _word_display_tag_items(self, word_match: object) -> list[dict[str, str]]:
        """Return style/component tag metadata for display and removal."""
        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return []

        style_map = {
            "italics": "Italics",
            "small caps": "Small Caps",
            "blackletter": "Blackletter",
            "all caps": "All Caps",
            "bold": "Bold",
            "underline": "Underline",
            "strikethrough": "Strikethrough",
            "monospace": "Monospace",
            "handwritten": "Handwritten",
        }
        component_map = {
            "footnote marker": "Footnote Marker",
            "drop cap": "Drop Cap",
            "subscript": "Subscript",
            "superscript": "Superscript",
        }

        style_labels = list(getattr(word_object, "text_style_labels", []) or [])
        component_labels = list(getattr(word_object, "word_components", []) or [])
        try:
            style_scopes = dict(
                getattr(word_object, "text_style_label_scopes", {}) or {}
            )
        except Exception:
            style_scopes = {}

        tag_items: list[dict[str, str]] = []
        for label in style_labels:
            normalized = str(label).strip().lower()
            if not normalized or normalized == "regular":
                continue
            display = style_map.get(normalized, normalized.title())
            explicit_scope = style_scopes.get(normalized)
            if explicit_scope is not None:
                normalized_scope = str(explicit_scope).strip().lower()
                if normalized_scope in {"whole", "part"}:
                    display = f"{display} ({normalized_scope.title()})"
            tag_items.append(
                {
                    "kind": "style",
                    "label": normalized,
                    "display": display,
                }
            )

        for label in component_labels:
            normalized = str(label).strip().lower()
            if not normalized:
                continue
            tag_items.append(
                {
                    "kind": "component",
                    "label": normalized,
                    "display": component_map.get(normalized, normalized.title()),
                }
            )

        return tag_items

    def _word_tag_chip_style(self, kind: str) -> str:
        """Return visual style string for a word tag chip by kind."""
        base = "font-size: 0.62rem; line-height: 1; padding: 2px 6px; border-radius: 9999px;"
        if kind == "style":
            return f"{base} background: #e7f0ff; border: 1px solid #b8ccf3; color: #1f4b99;"
        if kind == "component":
            return f"{base} background: #e7f8ee; border: 1px solid #b7dfc3; color: #1f6b3a;"
        return f"{base} background: #eef2f7; border: 1px solid #cfd8e3;"

    def _word_display_tags(self, word_match: object) -> list[str]:
        """Return compact style/component tag labels for display."""
        return [item["display"] for item in self._word_display_tag_items(word_match)]

    def _clear_word_tag(
        self,
        line_index: int,
        word_index: int,
        *,
        kind: str,
        label: str,
    ) -> bool:
        """Clear one style/component tag from a word and notify the user."""
        if kind == "style":
            result = self.word_operations.clear_style_on_word(
                line_index,
                word_index,
                label,
            )
        elif kind == "component":
            result = self.word_operations.clear_component_on_word(
                line_index,
                word_index,
                label,
            )
        else:
            self._safe_notify(f"Unknown tag type '{kind}'", type_="warning")
            return False

        self._safe_notify(result.message, type_=result.severity)
        if result.updated_count > 0:
            self._refresh_word_after_local_operation(line_index, word_index)
            self.toolbar.update_button_state()
            return True

        return False

    def _get_original_image_source(self) -> str:
        """Return encoded original image source for client-side slice rendering."""
        return self.bbox._get_original_image_source()

    def on_image_sources_updated(self, image_dict: dict[str, str]) -> None:
        """React to state image updates and rerender if word-view source changed."""
        self.bbox.on_image_sources_updated(image_dict)

    def _compute_encoded_dimensions(
        self,
        width: int,
        height: int,
        *,
        max_dimension: int = 1200,
    ) -> tuple[int, int]:
        """Mirror page image encoding resize logic for precise client-side slices."""
        return self.bbox.compute_encoded_dimensions(
            width, height, max_dimension=max_dimension
        )

    def _build_slice_placeholder_source(self, width: int, height: int) -> str:
        """Build tiny transparent SVG source that preserves interactive-image geometry."""
        return self.bbox._build_slice_placeholder_source(width, height)

    def _preview_bbox_for_word(
        self,
        word_match,
        page_image,
        *,
        line_index: int,
        word_index: int,
        bbox_preview_deltas: tuple[float, float, float, float] | None = None,
    ) -> tuple[int, int, int, int] | None:
        """Build clamped preview bbox in pixel coordinates for a word image crop."""
        return self.bbox.preview_bbox_for_word(
            word_match,
            page_image,
            line_index=line_index,
            word_index=word_index,
            bbox_preview_deltas=bbox_preview_deltas,
        )

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

    def _on_filter_change(self, event: events.ValueChangeEventArguments) -> None:
        """Handle filter selection change."""
        logger.debug(f"Filter change event triggered: {event}")
        logger.debug(f"Filter selector value: {self.filter_selector.value}")
        self.filter_mode = self.filter_selector.value
        logger.debug(f"Filter mode set to: {self.filter_mode}")
        self._update_lines_display()
        logger.debug("Filter change handling complete")

    def _get_effective_selected_lines(self) -> list[int]:
        """Return selected lines from both line and word selections."""
        line_selection = set(self.selection.selected_line_indices)
        line_selection.update(
            line_index for line_index, _ in self.selection.selected_word_indices
        )
        return sorted(line_selection)

    def _get_all_line_indices(self) -> list[int]:
        """Return all line indices currently displayed in the page model."""
        return sorted(
            {line_match.line_index for line_match in self.view_model.line_matches}
        )

    def _get_selected_paragraph_line_indices(self) -> list[int]:
        """Return line indices belonging to selected paragraphs."""
        line_indices: set[int] = set()
        for paragraph_index in self.selection.selected_paragraph_indices:
            line_indices.update(self._paragraph_line_indices(paragraph_index))
        return sorted(line_indices)

    def _get_selected_word_line_indices(self) -> list[int]:
        """Return distinct line indices containing selected words."""
        return sorted(
            {line_index for line_index, _ in self.selection.selected_word_indices}
        )

    def set_selected_words(self, selection: set[tuple[int, int]]) -> None:
        """Set selected words externally (e.g., box selection integration)."""
        self.selection.set_selected_words(selection)

    def set_selected_paragraphs(self, selection: set[int]) -> None:
        """Set selected paragraphs externally (e.g., image box selection)."""
        self.selection.set_selected_paragraphs(selection)

    def refresh_after_selection_change(self) -> None:
        """Centralized post-selection-change refresh."""
        self.toolbar.update_button_state()
        self.selection.emit_selection_changed()
        self.selection.emit_paragraph_selection_changed()
        self.selection.refresh_all_checkbox_states()

    def refresh_after_action(self) -> None:
        """Centralized post-action refresh: toolbar + selection emit."""
        self.toolbar.update_button_state()
        self.selection.emit_selection_changed()
        self.selection.emit_paragraph_selection_changed()

    def _refresh_word_after_local_operation(
        self,
        line_index: int,
        word_index: int,
    ) -> None:
        """Refresh local UI after direct word-object style mutations."""
        self.renderer.rerender_line_card(line_index)
        self._refresh_open_word_dialog_for(line_index, word_index)
        self._update_summary()
        self.refresh_after_action()

    def _update_action_button_state(self) -> None:
        """Enable/disable line and paragraph action buttons based on selection."""
        self.toolbar.update_button_state()

    def _copy_lines(
        self,
        line_indices: list[int],
        callback: Callable[[int], bool] | None,
        *,
        direction_label: str,
        no_selection_message: str,
        no_text_message: str,
    ) -> None:
        """Delegate to actions."""
        self.actions._copy_lines(
            line_indices,
            callback,
            direction_label=direction_label,
            no_selection_message=no_selection_message,
            no_text_message=no_text_message,
        )

    def _handle_copy_page_gt_to_ocr(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_page_gt_to_ocr(_event)

    def _handle_copy_page_ocr_to_gt(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_page_ocr_to_gt(_event)

    def _handle_copy_selected_paragraphs_gt_to_ocr(
        self, _event: ClickEvent = None
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_selected_paragraphs_gt_to_ocr(_event)

    def _handle_copy_selected_paragraphs_ocr_to_gt(
        self, _event: ClickEvent = None
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_selected_paragraphs_ocr_to_gt(_event)

    def _handle_copy_selected_lines_gt_to_ocr(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_selected_lines_gt_to_ocr(_event)

    def _handle_copy_selected_lines_ocr_to_gt(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_selected_lines_ocr_to_gt(_event)

    def _handle_copy_selected_words_gt_to_ocr(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_selected_words_gt_to_ocr(_event)

    def _handle_copy_selected_words_ocr_to_gt(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_copy_selected_words_ocr_to_gt(_event)

    def _handle_merge_selected_lines(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_merge_selected_lines(_event)

    def _handle_merge_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_merge_selected_paragraphs(_event)

    def _handle_delete_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_delete_selected_paragraphs(_event)

    def _handle_split_paragraph_after_selected_line(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_split_paragraph_after_selected_line(_event)

    def _handle_split_paragraph_by_selected_lines(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_split_paragraph_by_selected_lines(_event)

    def _handle_split_line_after_selected_word(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_split_line_after_selected_word(_event)

    def _handle_delete_selected_lines(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_delete_selected_lines(_event)

    def _handle_delete_selected_words(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_delete_selected_words(_event)

    def _can_merge_selected_words(self) -> bool:
        """Return True when current selected words can be merged as one block."""
        selected_words = sorted(self.selection.selected_word_indices)
        if len(selected_words) < 2:
            return False

        selected_line_indices = {line_index for line_index, _ in selected_words}
        if len(selected_line_indices) != 1:
            return False

        word_indices = [word_index for _, word_index in selected_words]
        expected_indices = list(range(word_indices[0], word_indices[-1] + 1))
        return word_indices == expected_indices

    def _handle_merge_selected_words(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_merge_selected_words(_event)

    def _handle_refine_selected_words(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_refine_selected_words(_event)

    def _handle_refine_selected_lines(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_refine_selected_lines(_event)

    def _handle_refine_selected_paragraphs(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_refine_selected_paragraphs(_event)

    def _handle_expand_then_refine_selected_words(
        self, _event: ClickEvent = None
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_expand_then_refine_selected_words(_event)

    def _handle_expand_then_refine_selected_lines(
        self, _event: ClickEvent = None
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_expand_then_refine_selected_lines(_event)

    def _handle_expand_then_refine_selected_paragraphs(
        self, _event: ClickEvent = None
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_expand_then_refine_selected_paragraphs(_event)

    def _handle_split_line_by_selected_words(self, _event: ClickEvent = None) -> None:
        """Delegate to actions."""
        self.actions._handle_split_line_by_selected_words(_event)

    def _handle_split_lines_into_selected_unselected_words(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_split_lines_into_selected_unselected_words(_event)

    def _handle_group_selected_words_into_new_paragraph(
        self,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_group_selected_words_into_new_paragraph(_event)

    def _handle_refine_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_refine_single_word(line_index, word_index, _event)

    def _handle_expand_then_refine_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_expand_then_refine_single_word(
            line_index, word_index, _event
        )

    def _handle_delete_single_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_delete_single_word(line_index, word_index, _event)

    def _handle_merge_word_left(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_merge_word_left(line_index, word_index, _event)

    def _handle_merge_word_right(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_merge_word_right(line_index, word_index, _event)

    def _handle_split_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> bool:
        """Delegate to actions."""
        return self.actions._handle_split_word(line_index, word_index, _event)

    def _handle_split_word_vertical_closest_line(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> bool:
        """Delegate to actions."""
        return self.actions._handle_split_word_vertical_closest_line(
            line_index, word_index, _event
        )

    def _handle_start_rebox_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Delegate to actions."""
        self.actions._handle_start_rebox_word(line_index, word_index, _event)

    def _toggle_bbox_fine_tune(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Toggle fine-tune controls for a single word bbox."""
        self.bbox.toggle_bbox_fine_tune(line_index, word_index, _event)

    def _set_bbox_nudge_step(self, value: object) -> None:
        """Set active bbox nudge step in pixels."""
        self.bbox.set_bbox_nudge_step(value)

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
        """Delegate to actions."""
        self.actions._handle_nudge_single_word_bbox(
            line_index,
            word_index,
            left_units=left_units,
            right_units=right_units,
            top_units=top_units,
            bottom_units=bottom_units,
            _event=_event,
        )

    def _apply_pending_single_word_bbox_nudge(
        self,
        line_index: int,
        word_index: int,
        refine_after: bool = True,
        _event: ClickEvent = None,
    ) -> None:
        """Apply pending bbox deltas for a single word."""
        self.bbox.apply_pending_single_word_bbox_nudge(
            line_index, word_index, refine_after, _event
        )

    def apply_rebox_bbox(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Apply a drawn bbox to the currently pending rebox word target."""
        self.bbox.apply_rebox_bbox(x1, y1, x2, y2)

    def _handle_delete_line(self, line_index: int) -> None:
        """Delegate to actions."""
        self.actions._handle_delete_line(line_index)

    def _delete_lines(
        self,
        line_indices: list[int],
        *,
        success_message: str,
        failure_message: str,
    ) -> None:
        """Delegate to actions."""
        self.actions._delete_lines(
            line_indices,
            success_message=success_message,
            failure_message=failure_message,
        )

    def _filter_lines_for_display(self):
        """Filter lines based on current filter setting."""
        return self.renderer._filter_lines_for_display()

    def _handle_copy_gt_to_ocr(self, line_index: int):
        """Delegate to actions."""
        self.actions._handle_copy_gt_to_ocr(line_index)

    def _handle_copy_ocr_to_gt(self, line_index: int):
        """Delegate to actions."""
        self.actions._handle_copy_ocr_to_gt(line_index)

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
        self.renderer._last_display_signature = None
        self.renderer._display_update_call_count = 0
        self.renderer._display_update_render_count = 0
        self.renderer._display_update_skip_count = 0
        self.selection.selected_line_indices.clear()
        self.selection.selected_word_indices.clear()
        self.selection.selected_paragraph_indices.clear()
        self.bbox.clear()
        self.renderer._word_dialog_refresh_key = None
        self.renderer._word_dialog_refresh_callback = None
        self.gt_editing._word_style_button_refs = {}
        self.renderer._word_column_refs = {}
        self.toolbar.update_button_state()
        self.selection.emit_selection_changed()
        self.selection.emit_paragraph_selection_changed()
        logger.debug("WordMatchView clear complete")
