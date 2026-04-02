"""Toolbar management for the word match view."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from nicegui import ui

from ...shared.button_styles import (
    ButtonVariant,
    style_word_icon_button,
    style_word_text_button,
)

if TYPE_CHECKING:
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)


class WordMatchToolbar:
    """Manages the actions toolbar and button state for WordMatchView."""

    def __init__(self, view: WordMatchView) -> None:
        self._view = view
        self._on_refine_bboxes: Callable | None = None
        self._on_expand_refine_bboxes: Callable | None = None
        # Button refs
        self.merge_lines_button = None
        self.delete_lines_button = None
        self.copy_gt_to_ocr_page_button = None
        self.copy_ocr_to_gt_page_button = None
        self.copy_gt_to_ocr_paragraphs_button = None
        self.copy_ocr_to_gt_paragraphs_button = None
        self.copy_gt_to_ocr_lines_button = None
        self.copy_ocr_to_gt_lines_button = None
        self.copy_gt_to_ocr_words_button = None
        self.copy_ocr_to_gt_words_button = None
        self.refine_lines_button = None
        self.expand_then_refine_lines_button = None
        self.merge_paragraphs_button = None
        self.delete_paragraphs_button = None
        self.refine_paragraphs_button = None
        self.expand_then_refine_paragraphs_button = None
        self.split_paragraph_after_line_button = None
        self.split_paragraph_by_selection_button = None
        self.split_line_after_word_button = None
        self.split_line_by_selection_button = None
        self.extract_line_from_selection_button = None
        self.merge_words_button = None
        self.delete_words_button = None
        self.refine_words_button = None
        self.expand_then_refine_words_button = None
        self.group_selected_words_into_paragraph_button = None
        self.validate_page_button = None
        self.unvalidate_page_button = None
        self.validate_paragraphs_button = None
        self.unvalidate_paragraphs_button = None
        self.validate_lines_button = None
        self.unvalidate_lines_button = None
        self.validate_words_button = None
        self.unvalidate_words_button = None
        self.apply_style_select = None
        self.apply_style_button = None
        self.apply_scope_select = None
        self._selected_style_value: str | None = None
        self.apply_component_select = None
        self.apply_component_button = None
        self.clear_component_button = None
        self._selected_component_value: str | None = None

    def set_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Refine Bboxes action."""
        self._on_refine_bboxes = callback

    def set_expand_refine_bboxes_callback(self, callback: Callable | None) -> None:
        """Register callback for the page-level Expand & Refine Bboxes action."""
        self._on_expand_refine_bboxes = callback

    def build_actions_toolbar(self):
        """Build the scope-action icon grid (Page/Paragraph/Line/Word operations)."""
        # Operations grid: columns = scope label | Merge | Refine | Expand+Refine |
        # Split After | Split Select | Word Select | To Paragraph | GT->OCR | OCR->GT | Validate | Unvalidate | Delete
        with (
            ui.grid(
                columns="auto auto auto auto auto auto auto auto auto auto auto auto auto"
            )
            .classes("items-center justify-items-center w-auto pl-2")
            .style("display: inline-grid; column-gap: 2px; row-gap: 2px")
        ):
            # Page row
            ui.label("Page").classes("text-sm font-semibold justify-self-start pr-1")
            ui.element("div")  # no Merge for page
            if self._on_refine_bboxes:
                self.refine_bboxes_button = ui.button(
                    icon="auto_fix_high",
                    on_click=self._on_refine_bboxes,
                ).tooltip("Refine all bounding boxes on this page")
                self.refine_bboxes_button.props(
                    'data-testid="page-refine-bboxes-button"'
                )
                style_word_icon_button(self.refine_bboxes_button)
            else:
                ui.element("div")
            if self._on_expand_refine_bboxes:
                self.expand_refine_bboxes_button = ui.button(
                    icon="zoom_out_map",
                    on_click=self._on_expand_refine_bboxes,
                ).tooltip("Expand then refine all bounding boxes on this page")
                self.expand_refine_bboxes_button.props(
                    'data-testid="page-expand-refine-bboxes-button"'
                )
                style_word_icon_button(self.expand_refine_bboxes_button)
            else:
                ui.element("div")
            ui.element("div")  # no Split After for page
            ui.element("div")  # no Split Select for page
            ui.element("div")  # no Word Select for page
            ui.element("div")  # no To Paragraph for page
            self.copy_gt_to_ocr_page_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_page_gt_to_ocr,
            ).tooltip("Copy all ground truth text to OCR on this page")
            self.copy_gt_to_ocr_page_button.props(
                'data-testid="page-copy-gt-to-ocr-button"'
            )
            self.copy_gt_to_ocr_page_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_page_button)
            self.copy_ocr_to_gt_page_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_page_ocr_to_gt,
            ).tooltip("Copy all OCR text to ground truth on this page")
            self.copy_ocr_to_gt_page_button.props(
                'data-testid="page-copy-ocr-to-gt-button"'
            )
            style_word_icon_button(self.copy_ocr_to_gt_page_button)
            self.validate_page_button = ui.button(
                icon="check_circle",
                on_click=self._handle_validate_page,
            ).tooltip("Validate all words on this page")
            self.validate_page_button.props('data-testid="page-validate-button"')
            style_word_icon_button(self.validate_page_button)
            self.unvalidate_page_button = ui.button(
                icon="unpublished",
                on_click=self._handle_unvalidate_page,
            ).tooltip("Unvalidate all words on this page")
            self.unvalidate_page_button.props('data-testid="page-unvalidate-button"')
            style_word_icon_button(self.unvalidate_page_button)
            ui.element("div")  # no Delete for page

            # Paragraph row
            ui.label("Paragraph").classes(
                "text-sm font-semibold justify-self-start pr-1"
            )
            self.merge_paragraphs_button = ui.button(
                icon="call_merge",
                on_click=self._view.actions._handle_merge_selected_paragraphs,
            ).tooltip("Merge selected paragraphs")
            self.merge_paragraphs_button.props('data-testid="paragraph-merge-button"')
            style_word_icon_button(self.merge_paragraphs_button)
            self.refine_paragraphs_button = ui.button(
                icon="auto_fix_high",
                on_click=self._view.actions._handle_refine_selected_paragraphs,
            ).tooltip("Refine selected paragraphs")
            self.refine_paragraphs_button.props(
                'data-testid="paragraph-refine-bboxes-button"'
            )
            style_word_icon_button(self.refine_paragraphs_button)
            self.expand_then_refine_paragraphs_button = ui.button(
                icon="zoom_out_map",
                on_click=self._view.actions._handle_expand_then_refine_selected_paragraphs,
            ).tooltip("Expand then refine selected paragraphs")
            self.expand_then_refine_paragraphs_button.props(
                'data-testid="paragraph-expand-refine-bboxes-button"'
            )
            style_word_icon_button(self.expand_then_refine_paragraphs_button)
            self.split_paragraph_after_line_button = ui.button(
                icon="call_split",
                on_click=self._view.actions._handle_split_paragraph_after_selected_line,
            ).tooltip(
                "Split the containing paragraph immediately after the selected line"
            )
            self.split_paragraph_after_line_button.props(
                'data-testid="paragraph-split-after-line-button"'
            )
            style_word_icon_button(self.split_paragraph_after_line_button)
            ui.element("div")  # no Split Select for paragraph
            ui.element("div")  # no Word->Paragraph on paragraph scope
            ui.element("div")  # no To Paragraph on paragraph scope
            self.copy_gt_to_ocr_paragraphs_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_paragraphs_gt_to_ocr,
            ).tooltip("Copy ground truth text to OCR for selected paragraphs")
            self.copy_gt_to_ocr_paragraphs_button.props(
                'data-testid="paragraph-copy-gt-to-ocr-button"'
            )
            self.copy_gt_to_ocr_paragraphs_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_paragraphs_button)
            self.copy_ocr_to_gt_paragraphs_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_paragraphs_ocr_to_gt,
            ).tooltip("Copy OCR text to ground truth for selected paragraphs")
            self.copy_ocr_to_gt_paragraphs_button.props(
                'data-testid="paragraph-copy-ocr-to-gt-button"'
            )
            style_word_icon_button(self.copy_ocr_to_gt_paragraphs_button)
            self.validate_paragraphs_button = ui.button(
                icon="check_circle",
                on_click=self._handle_validate_selected_paragraphs,
            ).tooltip("Validate all words in selected paragraphs")
            self.validate_paragraphs_button.props(
                'data-testid="paragraph-validate-button"'
            )
            style_word_icon_button(self.validate_paragraphs_button)
            self.unvalidate_paragraphs_button = ui.button(
                icon="unpublished",
                on_click=self._handle_unvalidate_selected_paragraphs,
            ).tooltip("Unvalidate all words in selected paragraphs")
            self.unvalidate_paragraphs_button.props(
                'data-testid="paragraph-unvalidate-button"'
            )
            style_word_icon_button(self.unvalidate_paragraphs_button)
            self.delete_paragraphs_button = ui.button(
                icon="delete",
                on_click=self._view.actions._handle_delete_selected_paragraphs,
            ).tooltip("Delete selected paragraphs")
            self.delete_paragraphs_button.props('data-testid="paragraph-delete-button"')
            style_word_icon_button(
                self.delete_paragraphs_button, variant=ButtonVariant.DELETE
            )

            # Line row
            ui.label("Line").classes("text-sm font-semibold justify-self-start pr-1")
            self.merge_lines_button = ui.button(
                icon="call_merge",
                on_click=self._view.actions._handle_merge_selected_lines,
            ).tooltip("Merge selected lines into the first selected line")
            self.merge_lines_button.props('data-testid="line-merge-button"')
            style_word_icon_button(self.merge_lines_button)
            self.refine_lines_button = ui.button(
                icon="auto_fix_high",
                on_click=self._view.actions._handle_refine_selected_lines,
            ).tooltip("Refine selected lines")
            self.refine_lines_button.props('data-testid="line-refine-bboxes-button"')
            style_word_icon_button(self.refine_lines_button)
            self.expand_then_refine_lines_button = ui.button(
                icon="zoom_out_map",
                on_click=self._view.actions._handle_expand_then_refine_selected_lines,
            ).tooltip("Expand then refine selected lines")
            self.expand_then_refine_lines_button.props(
                'data-testid="line-expand-refine-bboxes-button"'
            )
            style_word_icon_button(self.expand_then_refine_lines_button)
            self.split_line_after_word_button = ui.button(
                icon="call_split",
                on_click=self._view.actions._handle_split_line_after_selected_word,
            ).tooltip("Split the selected line immediately after the selected word")
            self.split_line_after_word_button.props(
                'data-testid="line-split-after-word-button"'
            )
            style_word_icon_button(self.split_line_after_word_button)
            self.split_line_by_selection_button = ui.button(
                icon="vertical_split",
                on_click=self._view.actions._handle_split_lines_into_selected_unselected_words,
            ).tooltip("Split line(s) into selected and unselected words")
            self.split_line_by_selection_button.props(
                'data-testid="line-split-by-selection-button"'
            )
            style_word_icon_button(self.split_line_by_selection_button)
            ui.element("div")  # moved to word scope
            self.split_paragraph_by_selection_button = ui.button(
                icon="subject",
                on_click=self._view.actions._handle_split_paragraph_by_selected_lines,
            ).tooltip("Select lines to form a new paragraph")
            self.split_paragraph_by_selection_button.props(
                'data-testid="line-form-paragraph-button"'
            )
            style_word_icon_button(self.split_paragraph_by_selection_button)
            self.copy_gt_to_ocr_lines_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_lines_gt_to_ocr,
            ).tooltip("Copy ground truth text to OCR for selected lines")
            self.copy_gt_to_ocr_lines_button.props(
                'data-testid="line-copy-gt-to-ocr-toolbar-button"'
            )
            self.copy_gt_to_ocr_lines_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_lines_button)
            self.copy_ocr_to_gt_lines_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_lines_ocr_to_gt,
            ).tooltip("Copy OCR text to ground truth for selected lines")
            self.copy_ocr_to_gt_lines_button.props(
                'data-testid="line-copy-ocr-to-gt-toolbar-button"'
            )
            style_word_icon_button(self.copy_ocr_to_gt_lines_button)
            self.validate_lines_button = ui.button(
                icon="check_circle",
                on_click=self._handle_validate_selected_lines,
            ).tooltip("Validate all words in selected lines")
            self.validate_lines_button.props(
                'data-testid="line-validate-toolbar-button"'
            )
            style_word_icon_button(self.validate_lines_button)
            self.unvalidate_lines_button = ui.button(
                icon="unpublished",
                on_click=self._handle_unvalidate_selected_lines,
            ).tooltip("Unvalidate all words in selected lines")
            self.unvalidate_lines_button.props(
                'data-testid="line-unvalidate-toolbar-button"'
            )
            style_word_icon_button(self.unvalidate_lines_button)
            self.delete_lines_button = ui.button(
                icon="delete",
                on_click=self._view.actions._handle_delete_selected_lines,
            ).tooltip("Delete selected lines")
            self.delete_lines_button.props('data-testid="line-delete-toolbar-button"')
            style_word_icon_button(
                self.delete_lines_button, variant=ButtonVariant.DELETE
            )

            # Word row
            ui.label("Word").classes("text-sm font-semibold justify-self-start pr-1")
            self.merge_words_button = ui.button(
                icon="call_merge",
                on_click=self._view.actions._handle_merge_selected_words,
            ).tooltip("Merge selected words on the same line")
            self.merge_words_button.props('data-testid="word-merge-button"')
            style_word_icon_button(self.merge_words_button)
            self.refine_words_button = ui.button(
                icon="auto_fix_high",
                on_click=self._view.actions._handle_refine_selected_words,
            ).tooltip("Refine selected words")
            self.refine_words_button.props('data-testid="word-refine-bboxes-button"')
            style_word_icon_button(self.refine_words_button)
            self.expand_then_refine_words_button = ui.button(
                icon="zoom_out_map",
                on_click=self._view.actions._handle_expand_then_refine_selected_words,
            ).tooltip("Expand then refine selected words")
            self.expand_then_refine_words_button.props(
                'data-testid="word-expand-refine-bboxes-button"'
            )
            style_word_icon_button(self.expand_then_refine_words_button)
            ui.element("div")  # no Split After for word
            ui.element("div")  # no Split Select for word
            self.extract_line_from_selection_button = ui.button(
                icon="short_text",
                on_click=self._view.actions._handle_split_line_by_selected_words,
            ).tooltip("Form one new line from selected words")
            self.extract_line_from_selection_button.props(
                'data-testid="word-form-line-button"'
            )
            style_word_icon_button(self.extract_line_from_selection_button)
            self.group_selected_words_into_paragraph_button = ui.button(
                icon="format_paragraph",
                on_click=self._view.actions._handle_group_selected_words_into_new_paragraph,
            ).tooltip(
                "Select words to form a new paragraph (one new line per source line)"
            )
            self.group_selected_words_into_paragraph_button.props(
                'data-testid="word-form-paragraph-button"'
            )
            style_word_icon_button(self.group_selected_words_into_paragraph_button)
            self.copy_gt_to_ocr_words_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_words_gt_to_ocr,
            ).tooltip("Copy ground truth text to OCR for selected words")
            self.copy_gt_to_ocr_words_button.props(
                'data-testid="word-copy-gt-to-ocr-button"'
            )
            self.copy_gt_to_ocr_words_button.classes("copy-icon-flip")
            style_word_icon_button(self.copy_gt_to_ocr_words_button)
            self.copy_ocr_to_gt_words_button = ui.button(
                icon="content_copy",
                on_click=self._view.actions._handle_copy_selected_words_ocr_to_gt,
            ).tooltip("Copy OCR text to ground truth for selected words")
            self.copy_ocr_to_gt_words_button.props(
                'data-testid="word-copy-ocr-to-gt-button"'
            )
            style_word_icon_button(self.copy_ocr_to_gt_words_button)
            self.validate_words_button = ui.button(
                icon="check_circle",
                on_click=self._handle_validate_selected_words,
            ).tooltip("Validate selected words")
            self.validate_words_button.props(
                'data-testid="word-validate-toolbar-button"'
            )
            style_word_icon_button(self.validate_words_button)
            self.unvalidate_words_button = ui.button(
                icon="unpublished",
                on_click=self._handle_unvalidate_selected_words,
            ).tooltip("Unvalidate selected words")
            self.unvalidate_words_button.props(
                'data-testid="word-unvalidate-toolbar-button"'
            )
            style_word_icon_button(self.unvalidate_words_button)
            self.delete_words_button = ui.button(
                icon="delete",
                on_click=self._view.actions._handle_delete_selected_words,
            ).tooltip("Delete selected words")
            self.delete_words_button.props('data-testid="word-delete-button"')
            style_word_icon_button(
                self.delete_words_button, variant=ButtonVariant.DELETE
            )

        self._build_apply_style_toolbar()

    def _build_apply_style_toolbar(self) -> None:
        """Build a dedicated immediate-apply style toolbar for selected words."""
        with (
            ui.row()
            .classes("items-end gap-2 pl-2 pt-2 flex-wrap")
            .style("max-width: 100%;")
        ):
            style_options = {
                style_label: self._display_label(style_label)
                for style_label in self._view.word_operations.supported_styles
            }
            self._selected_style_value = next(iter(style_options), None)
            self.apply_style_select = ui.select(
                options=style_options,
                value=self._selected_style_value,
                label="Style",
            ).props("dense outlined options-dense")
            self.apply_style_select.classes("text-caption")
            self.apply_style_select.style(
                "min-width: 122px; max-width: 140px; font-size: 0.72rem;"
            )
            self.apply_style_select.on_value_change(self._on_style_value_change)

            self.apply_scope_select = ui.select(
                options={"": "--", "whole": "Whole", "part": "Part"},
                value="",
                label="Scope",
            ).props("dense outlined options-dense")
            self.apply_scope_select.classes("text-caption")
            self.apply_scope_select.style(
                "min-width: 96px; max-width: 108px; font-size: 0.72rem;"
            )
            self.apply_scope_select.on_value_change(
                lambda event: (
                    self._apply_scope(str(event.value))
                    if event.value in {"whole", "part"}
                    else None
                )
            )

            self.apply_style_button = ui.button(
                "Apply Style",
                on_click=self._apply_selected_style,
            ).props("dense no-caps size=sm")
            style_word_text_button(self.apply_style_button, compact=True)
            self.apply_style_button.style(
                "min-width: 80px; padding-left: 6px; padding-right: 6px; "
                "font-size: 0.72rem;"
            )
            self.apply_style_button.props('data-testid="apply-style-button"')

            component_options = {
                component_label: self._display_component_label(component_label)
                for component_label in self._view.word_operations.supported_components
            }
            self._selected_component_value = next(iter(component_options), None)
            self.apply_component_select = ui.select(
                options=component_options,
                value=self._selected_component_value,
                label="Component",
            ).props("dense outlined options-dense")
            self.apply_component_select.classes("text-caption")
            self.apply_component_select.style(
                "min-width: 138px; max-width: 162px; font-size: 0.72rem;"
            )
            self.apply_component_select.on_value_change(self._on_component_value_change)

            self.apply_component_button = ui.button(
                "Apply Component",
                on_click=self._apply_selected_component,
            ).props("dense no-caps size=sm")
            style_word_text_button(self.apply_component_button, compact=True)
            self.apply_component_button.style(
                "min-width: 98px; padding-left: 6px; padding-right: 6px; "
                "font-size: 0.72rem;"
            )
            self.apply_component_button.props('data-testid="apply-component-button"')

            self.clear_component_button = ui.button(
                "Clear Component",
                on_click=self._clear_selected_component,
            ).props("dense no-caps size=sm outline")
            style_word_text_button(self.clear_component_button, compact=True)
            self.clear_component_button.style(
                "min-width: 102px; padding-left: 6px; padding-right: 6px; "
                "font-size: 0.72rem;"
            )
            self.clear_component_button.props('data-testid="clear-component-button"')

        # Apply the current selection state immediately so controls are correctly
        # gated when the toolbar first renders.
        self.update_button_state()

    def _display_label(self, value: str) -> str:
        return str(value).title()

    def _display_component_label(self, value: str) -> str:
        component_labels = {
            "footnote marker": "Footnote Marker",
            "drop cap": "Drop Cap",
            "subscript": "Subscript",
            "superscript": "Superscript",
        }
        return component_labels.get(str(value), self._display_label(value))

    def _on_style_value_change(self, event) -> None:
        self._selected_style_value = str(event.value) if event.value else None

    def _on_component_value_change(self, event) -> None:
        self._selected_component_value = str(event.value) if event.value else None

    def _apply_selected_style(self) -> None:
        if not self._selected_style_value:
            self._view._safe_notify("Select a style to apply", type_="warning")
            return
        self._apply_style(self._selected_style_value)

    def _apply_style(self, style: str) -> None:
        result = self._view.word_operations.apply_style_to_selection(style)
        self._view._safe_notify(result.message, type_=result.severity)
        self.update_button_state()

    def _apply_scope(self, scope: str) -> None:
        result = self._view.word_operations.apply_scope_to_selection(scope)
        self._view._safe_notify(result.message, type_=result.severity)
        self.update_button_state()

    def _apply_selected_component(self) -> None:
        if not self._selected_component_value:
            self._view._safe_notify("Select a component to apply", type_="warning")
            return
        self._apply_component(self._selected_component_value, enabled=True)

    def _clear_selected_component(self) -> None:
        if not self._selected_component_value:
            self._view._safe_notify("Select a component to clear", type_="warning")
            return
        self._apply_component(self._selected_component_value, enabled=False)

    def _apply_component(self, component: str, *, enabled: bool) -> None:
        result = self._view.word_operations.apply_component_to_selection(
            component,
            enabled=enabled,
        )
        self._view._safe_notify(result.message, type_=result.severity)
        self.update_button_state()

    # ------------------------------------------------------------------
    # Validation handlers
    # ------------------------------------------------------------------

    def _collect_word_keys_for_lines(
        self, line_indices: list[int]
    ) -> list[tuple[int, int]]:
        """Return (line_index, word_index) pairs for all words in given lines."""
        line_set = set(line_indices)
        keys: list[tuple[int, int]] = []
        for lm in self._view.view_model.line_matches:
            if lm.line_index in line_set:
                for wm in lm.word_matches:
                    wi = wm.word_index
                    if wi is not None and wi >= 0:
                        keys.append((lm.line_index, wi))
        return keys

    def _set_validation_for_keys(
        self, keys: list[tuple[int, int]], *, validate: bool
    ) -> None:
        """Toggle validation for a list of (line_index, word_index) pairs.

        Snapshots each word's current state *before* calling the callback so
        that we never re-read a value that a prior iteration already toggled.
        """
        callback = self._view.toggle_word_validated_callback
        if callback is None:
            return
        # Build snapshot: (line_idx, word_idx, currently_validated)
        snapshot: list[tuple[int, int, bool]] = []
        for line_idx, word_idx in keys:
            lm = self._view._line_match_by_index(line_idx)
            if lm is None:
                continue
            wm = next((w for w in lm.word_matches if w.word_index == word_idx), None)
            if wm is None:
                continue
            snapshot.append((line_idx, word_idx, wm.is_validated))

        toggled_lines: set[int] = set()
        for line_idx, word_idx, was_validated in snapshot:
            if validate and not was_validated:
                callback(line_idx, word_idx)
                toggled_lines.add(line_idx)
            elif not validate and was_validated:
                callback(line_idx, word_idx)
                toggled_lines.add(line_idx)
        # Rerender affected line cards once each
        for line_idx in toggled_lines:
            self._view.renderer.rerender_line_card(line_idx)

    def _handle_validate_page(self) -> None:
        all_lines = self._view._get_all_line_indices()
        keys = self._collect_word_keys_for_lines(all_lines)
        self._set_validation_for_keys(keys, validate=True)

    def _handle_unvalidate_page(self) -> None:
        all_lines = self._view._get_all_line_indices()
        keys = self._collect_word_keys_for_lines(all_lines)
        self._set_validation_for_keys(keys, validate=False)

    def _handle_validate_selected_paragraphs(self) -> None:
        line_indices = self._view._get_selected_paragraph_line_indices()
        keys = self._collect_word_keys_for_lines(line_indices)
        self._set_validation_for_keys(keys, validate=True)

    def _handle_unvalidate_selected_paragraphs(self) -> None:
        line_indices = self._view._get_selected_paragraph_line_indices()
        keys = self._collect_word_keys_for_lines(line_indices)
        self._set_validation_for_keys(keys, validate=False)

    def _handle_validate_selected_lines(self) -> None:
        line_indices = self._view._get_effective_selected_lines()
        keys = self._collect_word_keys_for_lines(line_indices)
        self._set_validation_for_keys(keys, validate=True)

    def _handle_unvalidate_selected_lines(self) -> None:
        line_indices = self._view._get_effective_selected_lines()
        keys = self._collect_word_keys_for_lines(line_indices)
        self._set_validation_for_keys(keys, validate=False)

    def _handle_validate_selected_words(self) -> None:
        keys = list(self._view.selection.selected_word_indices)
        self._set_validation_for_keys(keys, validate=True)

    def _handle_unvalidate_selected_words(self) -> None:
        keys = list(self._view.selection.selected_word_indices)
        self._set_validation_for_keys(keys, validate=False)

    def update_button_state(self) -> None:
        """Enable/disable line and paragraph action buttons based on selection.

        Uses ``button.enabled`` (not ``button.disabled``) because NiceGUI's
        ``DisableableElement`` only reacts to the ``enabled`` property; setting
        an ad-hoc ``disabled`` attribute has no effect on the rendered Quasar
        component.
        """
        selected_lines = self._view._get_effective_selected_lines()
        if self.merge_lines_button is None:
            pass
        else:
            self.merge_lines_button.enabled = (
                self._view.merge_lines_callback is not None and len(selected_lines) >= 2
            )

        if self.delete_lines_button is not None:
            self.delete_lines_button.enabled = (
                self._view.delete_lines_callback is not None
                and len(selected_lines) >= 1
            )

        if self.refine_lines_button is not None:
            self.refine_lines_button.enabled = (
                self._view.refine_lines_callback is not None
                and len(selected_lines) >= 1
            )

        if self.expand_then_refine_lines_button is not None:
            self.expand_then_refine_lines_button.enabled = (
                self._view.expand_then_refine_lines_callback is not None
                and len(selected_lines) >= 1
            )

        if self.merge_paragraphs_button is not None:
            self.merge_paragraphs_button.enabled = (
                self._view.merge_paragraphs_callback is not None
                and len(self._view.selection.selected_paragraph_indices) >= 2
            )

        if self.delete_paragraphs_button is not None:
            self.delete_paragraphs_button.enabled = (
                self._view.delete_paragraphs_callback is not None
                and len(self._view.selection.selected_paragraph_indices) >= 1
            )

        if self.refine_paragraphs_button is not None:
            self.refine_paragraphs_button.enabled = (
                self._view.refine_paragraphs_callback is not None
                and len(self._view.selection.selected_paragraph_indices) >= 1
            )

        if self.expand_then_refine_paragraphs_button is not None:
            self.expand_then_refine_paragraphs_button.enabled = (
                self._view.expand_then_refine_paragraphs_callback is not None
                and len(self._view.selection.selected_paragraph_indices) >= 1
            )

        if self.split_paragraph_after_line_button is not None:
            self.split_paragraph_after_line_button.enabled = (
                self._view.split_paragraph_after_line_callback is not None
                and len(self._view.selection.selected_line_indices) == 1
            )

        if self.split_paragraph_by_selection_button is not None:
            self.split_paragraph_by_selection_button.enabled = (
                self._view.split_paragraph_with_selected_lines_callback is not None
                and len(self._view.selection.selected_line_indices) >= 1
            )

        if self.split_line_after_word_button is not None:
            self.split_line_after_word_button.enabled = (
                self._view.split_line_after_word_callback is not None
                and len(self._view.selection.selected_word_indices) == 1
            )

        if self.delete_words_button is not None:
            self.delete_words_button.enabled = (
                self._view.delete_words_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.merge_words_button is not None:
            self.merge_words_button.enabled = (
                self._view.merge_word_right_callback is not None
                and self._view._can_merge_selected_words()
            )

        if self.split_line_by_selection_button is not None:
            self.split_line_by_selection_button.enabled = (
                self._view.split_lines_into_selected_unselected_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.extract_line_from_selection_button is not None:
            self.extract_line_from_selection_button.enabled = (
                self._view.split_line_with_selected_words_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.group_selected_words_into_paragraph_button is not None:
            self.group_selected_words_into_paragraph_button.enabled = (
                self._view.group_selected_words_into_paragraph_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.refine_words_button is not None:
            self.refine_words_button.enabled = (
                self._view.refine_words_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.expand_then_refine_words_button is not None:
            self.expand_then_refine_words_button.enabled = (
                self._view.expand_then_refine_words_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.copy_gt_to_ocr_page_button is not None:
            self.copy_gt_to_ocr_page_button.enabled = (
                self._view.copy_gt_to_ocr_callback is not None
                and len(self._view._get_all_line_indices()) >= 1
            )

        if self.copy_ocr_to_gt_page_button is not None:
            self.copy_ocr_to_gt_page_button.enabled = (
                self._view.copy_ocr_to_gt_callback is not None
                and len(self._view._get_all_line_indices()) >= 1
            )

        if self.copy_gt_to_ocr_paragraphs_button is not None:
            self.copy_gt_to_ocr_paragraphs_button.enabled = (
                self._view.copy_gt_to_ocr_callback is not None
                and len(self._view.selection.selected_paragraph_indices) >= 1
            )

        if self.copy_ocr_to_gt_paragraphs_button is not None:
            self.copy_ocr_to_gt_paragraphs_button.enabled = (
                self._view.copy_ocr_to_gt_callback is not None
                and len(self._view.selection.selected_paragraph_indices) >= 1
            )

        if self.copy_gt_to_ocr_lines_button is not None:
            self.copy_gt_to_ocr_lines_button.enabled = (
                self._view.copy_gt_to_ocr_callback is not None
                and len(selected_lines) >= 1
            )

        if self.copy_ocr_to_gt_lines_button is not None:
            self.copy_ocr_to_gt_lines_button.enabled = (
                self._view.copy_ocr_to_gt_callback is not None
                and len(selected_lines) >= 1
            )

        if self.copy_gt_to_ocr_words_button is not None:
            self.copy_gt_to_ocr_words_button.enabled = (
                self._view.copy_gt_to_ocr_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        if self.copy_ocr_to_gt_words_button is not None:
            self.copy_ocr_to_gt_words_button.enabled = (
                self._view.copy_selected_words_ocr_to_gt_callback is not None
                and len(self._view.selection.selected_word_indices) >= 1
            )

        has_selected_words = len(self._view.selection.selected_word_indices) > 0
        if self.apply_style_select is not None:
            self.apply_style_select.enabled = has_selected_words
        if self.apply_style_button is not None:
            self.apply_style_button.enabled = has_selected_words
        if self.apply_scope_select is not None:
            self.apply_scope_select.enabled = has_selected_words
        if self.apply_component_select is not None:
            self.apply_component_select.enabled = has_selected_words
        if self.apply_component_button is not None:
            self.apply_component_button.enabled = has_selected_words
        if self.clear_component_button is not None:
            self.clear_component_button.enabled = has_selected_words

        # Validation buttons
        has_callback = self._view.toggle_word_validated_callback is not None
        has_any_lines = len(self._view._get_all_line_indices()) > 0
        has_selected_paragraphs = (
            len(self._view.selection.selected_paragraph_indices) > 0
        )
        has_selected_lines = len(selected_lines) > 0

        for btn in (self.validate_page_button, self.unvalidate_page_button):
            if btn is not None:
                btn.enabled = has_callback and has_any_lines

        for btn in (
            self.validate_paragraphs_button,
            self.unvalidate_paragraphs_button,
        ):
            if btn is not None:
                btn.enabled = has_callback and has_selected_paragraphs

        for btn in (self.validate_lines_button, self.unvalidate_lines_button):
            if btn is not None:
                btn.enabled = has_callback and has_selected_lines

        for btn in (self.validate_words_button, self.unvalidate_words_button):
            if btn is not None:
                btn.enabled = has_callback and has_selected_words
