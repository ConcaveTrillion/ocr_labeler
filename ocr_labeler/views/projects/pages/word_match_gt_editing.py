"""Ground truth editing and word style management for the word match view."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nicegui import events, ui

if TYPE_CHECKING:
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)

WordKey = tuple[int, int]
ClickEvent = events.ClickEventArguments | None

WORD_LABEL_ITALIC = "italic"
WORD_LABEL_SMALL_CAPS = "small_caps"
WORD_LABEL_BLACKLETTER = "blackletter"
WORD_LABEL_LEFT_FOOTNOTE = "left_footnote"
WORD_LABEL_RIGHT_FOOTNOTE = "right_footnote"


class WordMatchGtEditing:
    """Manages ground truth text editing and word style attributes for WordMatchView."""

    def __init__(self, view: WordMatchView) -> None:
        self._view = view
        self._word_gt_input_refs: dict[WordKey, object] = {}
        self._word_style_button_refs: dict[
            WordKey, tuple[object, object, object, object, object]
        ] = {}

    def create_gt_cell(self, line_index: int, word_index: int, word_match):
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
                input_element.enabled = (
                    self._view.edit_word_ground_truth_callback is not None
                )
                tooltip_content = self._view._create_word_tooltip(word_match)
                if tooltip_content:
                    input_element.tooltip(tooltip_content)
            elif word_match.ground_truth_text.strip():
                gt_element = ui.label(word_match.ground_truth_text).classes("monospace")
                tooltip_content = self._view._create_word_tooltip(word_match)
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
        if self._view.edit_word_ground_truth_callback is None:
            self._view._safe_notify(
                "Edit ground truth function not available", type_="warning"
            )
            return

        try:
            success = self._view.edit_word_ground_truth_callback(
                line_index,
                word_index,
                ground_truth_text,
            )
            if not success:
                self._view._safe_notify(
                    "Failed to update word ground truth", type_="warning"
                )
                return

            self._view.renderer.apply_local_word_gt_update(
                line_index=line_index,
                word_index=word_index,
                ground_truth_text=ground_truth_text,
            )
            self._view._update_summary()
            self._view.renderer.rerender_line_card(line_index)
            self._view.toolbar.update_button_state()
            self._view.selection.refresh_word_checkbox_states()
            self._view.selection.refresh_line_checkbox_states()
            self._view.selection.refresh_paragraph_checkbox_states()
        except Exception as e:
            logger.exception(
                "Error updating word ground truth (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error updating word ground truth: {e}", type_="negative"
            )

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
        """Persist per-word style attributes via callback."""
        if self._view.set_word_attributes_callback is None:
            self._view._safe_notify(
                "Set word attributes function not available", type_="warning"
            )
            return

        if word_index < 0:
            self._view._safe_notify(
                "Cannot set attributes for unmatched word", type_="warning"
            )
            return

        try:
            success = self._view.set_word_attributes_callback(
                line_index,
                word_index,
                bool(italic),
                bool(small_caps),
                bool(blackletter),
                bool(left_footnote),
                bool(right_footnote),
            )
            if not success:
                self._view._safe_notify(
                    "Failed to update word attributes", type_="warning"
                )
                return
            self._apply_local_word_style_update(
                line_index=line_index,
                word_index=word_index,
                italic=bool(italic),
                small_caps=bool(small_caps),
                blackletter=bool(blackletter),
                left_footnote=bool(left_footnote),
                right_footnote=bool(right_footnote),
            )
            self._set_word_style_button_states(
                line_index=line_index,
                word_index=word_index,
                italic=bool(italic),
                small_caps=bool(small_caps),
                blackletter=bool(blackletter),
                left_footnote=bool(left_footnote),
                right_footnote=bool(right_footnote),
            )
        except Exception as e:
            logger.exception(
                "Error updating word attributes (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error updating word attributes: {e}", type_="negative"
            )

    def _handle_toggle_word_attribute(
        self,
        line_index: int,
        word_index: int,
        attribute: str,
        _event: ClickEvent = None,
    ) -> None:
        """Toggle one style attribute using current runtime flags (no stale closure values)."""
        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            self._view._safe_notify(
                "Cannot set attributes for unmatched word", type_="warning"
            )
            return

        italic, small_caps, blackletter, left_footnote, right_footnote = (
            self._view._word_style_flags(word_match)
        )
        if attribute == WORD_LABEL_ITALIC:
            italic = not italic
        elif attribute == WORD_LABEL_SMALL_CAPS:
            small_caps = not small_caps
        elif attribute == WORD_LABEL_BLACKLETTER:
            blackletter = not blackletter
        elif attribute == WORD_LABEL_LEFT_FOOTNOTE:
            left_footnote = not left_footnote
        elif attribute == WORD_LABEL_RIGHT_FOOTNOTE:
            right_footnote = not right_footnote
        else:
            return

        self._handle_set_word_attributes(
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
        logger.debug(
            "[word_match_refresh] targeted.word_gt_changed.apply line=%s word=%s",
            line_index,
            word_index,
        )
        self._view.renderer.apply_local_word_gt_update(
            line_index=line_index,
            word_index=word_index,
            ground_truth_text=ground_truth_text,
        )
        self._view._update_summary()
        self._view.renderer.rerender_line_card(line_index)
        self._view.toolbar.update_button_state()
        self._view.selection.refresh_word_checkbox_states()
        self._view.selection.refresh_line_checkbox_states()
        self._view.selection.refresh_paragraph_checkbox_states()

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
        self._apply_local_word_style_update(
            line_index=line_index,
            word_index=word_index,
            italic=bool(italic),
            small_caps=bool(small_caps),
            blackletter=bool(blackletter),
            left_footnote=bool(left_footnote),
            right_footnote=bool(right_footnote),
        )
        self._set_word_style_button_states(
            line_index=line_index,
            word_index=word_index,
            italic=bool(italic),
            small_caps=bool(small_caps),
            blackletter=bool(blackletter),
            left_footnote=bool(left_footnote),
            right_footnote=bool(right_footnote),
        )

    def _set_word_style_button_states(
        self,
        *,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> None:
        """Update only I/SC/BL/LFN/RFN button colors for a word without rerendering the column."""
        key = (line_index, word_index)
        button_refs = self._word_style_button_refs.get(key)
        if button_refs is None:
            return

        if any(not self._view._has_active_ui_context(button) for button in button_refs):
            self._word_style_button_refs.pop(key, None)
            return

        states = (italic, small_caps, blackletter, left_footnote, right_footnote)
        for button, enabled in zip(button_refs, states, strict=False):
            try:
                if enabled:
                    button.props("color=primary")
                else:
                    button.props("color=grey-5 text-color=black")
                button.update()
            except RuntimeError as error:
                if self._view._is_disposed_ui_error(error):
                    self._word_style_button_refs.pop(key, None)
                    return
                raise
            except Exception:
                logger.debug(
                    "Failed to update style button state for key=%s",
                    key,
                    exc_info=True,
                )
                self._view._safe_notify_once(
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
        left_footnote: bool,
        right_footnote: bool,
    ) -> None:
        """Apply style labels locally for stable subsequent toggle computations."""
        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
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

        if left_footnote:
            labels_set.add(WORD_LABEL_LEFT_FOOTNOTE)
        else:
            labels_set.discard(WORD_LABEL_LEFT_FOOTNOTE)

        if right_footnote:
            labels_set.add(WORD_LABEL_RIGHT_FOOTNOTE)
        else:
            labels_set.discard(WORD_LABEL_RIGHT_FOOTNOTE)

        ordered = [label for label in labels if label in labels_set]
        ordered.extend(
            sorted(label for label in labels_set if label not in set(ordered))
        )
        word_object.word_labels = ordered
