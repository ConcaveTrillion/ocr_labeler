"""Word edit dialog UI extracted from the main word match view."""

from __future__ import annotations

from typing import Any

from nicegui import events, ui

from ...shared.button_styles import (
    ButtonVariant,
    style_word_icon_button,
    style_word_text_button,
)


def render_word_split_marker(view: Any, split_key: tuple[int, int]) -> None:
    """Render persistent marker and hover guide for a word image."""
    image = view._word_split_image_refs.get(split_key)
    if image is None:
        return

    try:
        width, height = view._word_split_image_sizes.get(split_key, (0.0, 0.0))
        marker_x = view._word_split_marker_x.get(split_key)
        marker_y = view._word_split_marker_y.get(split_key)
        marker_x_fraction = view._word_split_fractions.get(split_key)
        marker_y_fraction = view._word_split_y_fractions.get(split_key)
        marker_height = max(1.0, float(height) if height > 0.0 else 1000.0)
        marker_width = max(1.0, float(width) if width > 0.0 else 1000.0)
        center_x = max(1.0, float(width) / 2.0) if width > 0.0 else 1.0
        center_y = max(1.0, float(height) / 2.0) if height > 0.0 else 1.0

        # Keep marker aligned with user intent across rerenders/zoom by
        # deriving pixel coordinates from stored fractions when available.
        if marker_x_fraction is not None and width > 0.0:
            marker_x = float(marker_x_fraction) * float(width)
        if marker_y_fraction is not None and height > 0.0:
            marker_y = float(marker_y_fraction) * float(height)

        overlays: list[str] = []

        # Persistent marker selected by click (solid).
        if marker_x is not None or marker_y is not None:
            solid_x = marker_x if marker_x is not None else center_x
            solid_y = marker_y if marker_y is not None else center_y
            overlays.append(
                f'<line x1="{solid_x:.2f}" y1="0" x2="{solid_x:.2f}" y2="{marker_height:.2f}" '
                'stroke="#2563eb" stroke-width="1" pointer-events="none" />'
            )
            overlays.append(
                f'<line x1="0" y1="{solid_y:.2f}" x2="{marker_width:.2f}" y2="{solid_y:.2f}" '
                'stroke="#2563eb" stroke-width="1" pointer-events="none" />'
            )

        # Hover-follow guide (dashed), even after click.
        if split_key in view._word_split_hover_keys:
            hover_pos = view._word_split_hover_positions.get(split_key)
            if hover_pos is None:
                hover_x, hover_y = center_x, center_y
            else:
                hover_x, hover_y = hover_pos
            overlays.append(
                f'<line x1="{hover_x:.2f}" y1="0" x2="{hover_x:.2f}" y2="{marker_height:.2f}" '
                'stroke="rgba(37, 99, 235, 0.55)" stroke-width="1" stroke-dasharray="4 3" pointer-events="none" />'
            )
            overlays.append(
                f'<line x1="0" y1="{hover_y:.2f}" x2="{marker_width:.2f}" y2="{hover_y:.2f}" '
                'stroke="rgba(37, 99, 235, 0.55)" stroke-width="1" stroke-dasharray="4 3" pointer-events="none" />'
            )

        image.content = "".join(overlays)
    except Exception:
        view._safe_notify_once(
            "word-split-marker-render",
            "Failed to render split marker overlay",
            type_="warning",
        )


def handle_word_image_mouse(
    view: Any,
    line_index: int,
    word_index: int,
    event: events.MouseEventArguments,
) -> None:
    """Handle hover/click interactions for marker overlays."""
    split_key = (line_index, word_index)
    event_type = str(getattr(event, "type", "") or "")

    def _event_coords() -> tuple[float, float] | None:
        image_width, image_height = view._word_split_image_sizes.get(
            split_key, (0.0, 0.0)
        )
        raw_image_x = getattr(event, "image_x", None)
        raw_image_y = getattr(event, "image_y", None)
        raw_fallback_x = getattr(event, "x", None)
        raw_fallback_y = getattr(event, "y", None)

        if raw_image_x is not None:
            image_x = float(raw_image_x)
        elif raw_fallback_x is not None:
            image_x = float(raw_fallback_x)
        else:
            return None

        if raw_image_y is not None:
            image_y = float(raw_image_y)
        elif raw_fallback_y is not None:
            image_y = float(raw_fallback_y)
        else:
            image_y = float(image_height) / 2.0 if image_height > 0.0 else -1.0

        if (
            image_width <= 0.0
            or image_height <= 0.0
            or image_x <= 0.0
            or image_y <= 0.0
            or image_x >= image_width
            or image_y >= image_height
        ):
            return None
        return (image_x, image_y)

    if event_type == "mouseenter":
        view._word_split_hover_keys.add(split_key)
        coords = _event_coords()
        if coords is not None:
            view._word_split_hover_positions[split_key] = coords
        render_word_split_marker(view, split_key)
        return
    if event_type == "mousemove":
        if split_key in view._word_split_hover_keys:
            coords = _event_coords()
            if coords is not None:
                view._word_split_hover_positions[split_key] = coords
            render_word_split_marker(view, split_key)
        return
    if event_type == "mouseleave":
        view._word_split_hover_keys.discard(split_key)
        view._word_split_hover_positions.pop(split_key, None)
        render_word_split_marker(view, split_key)
        return

    handle_word_image_click(view, line_index, word_index, event)


def handle_word_image_click(
    view: Any,
    line_index: int,
    word_index: int,
    event: events.MouseEventArguments,
) -> None:
    """Store marker position from interactive image click."""
    if word_index < 0:
        return

    word_match = view._line_word_match_by_ocr_index(line_index, word_index)
    if word_match is None:
        return

    split_key = (line_index, word_index)
    image_width, image_height = view._word_split_image_sizes.get(split_key, (0.0, 0.0))

    # Get click coordinates
    raw_image_x = getattr(event, "image_x", None)
    raw_image_y = getattr(event, "image_y", None)
    raw_fallback_x = getattr(event, "x", None)
    raw_fallback_y = getattr(event, "y", None)

    if raw_image_x is not None:
        image_x = float(raw_image_x)
    elif raw_fallback_x is not None:
        image_x = float(raw_fallback_x)
    else:
        image_x = -1.0

    if raw_image_y is not None:
        image_y = float(raw_image_y)
    elif raw_fallback_y is not None:
        image_y = float(raw_fallback_y)
    else:
        # Keep backward compatibility with x-only click payloads.
        image_y = float(image_height) / 2.0 if image_height > 0.0 else -1.0

    # Validate coordinates are within bounds
    if (
        image_width <= 0.0
        or image_height <= 0.0
        or image_x <= 0.0
        or image_y <= 0.0
        or image_x >= image_width
        or image_y >= image_height
    ):
        return

    # Store both fractions for horizontal and vertical splits
    horizontal_fraction = image_x / image_width
    vertical_fraction = image_y / image_height

    if horizontal_fraction <= 0.0 or horizontal_fraction >= 1.0:
        return
    if vertical_fraction <= 0.0 or vertical_fraction >= 1.0:
        return

    # Store click position
    view._word_split_fractions[split_key] = horizontal_fraction
    view._word_split_y_fractions[split_key] = vertical_fraction
    view._word_split_marker_x[split_key] = image_x
    view._word_split_marker_y[split_key] = image_y
    render_word_split_marker(view, split_key)

    # Enable both split buttons
    split_button = view._word_split_button_refs.get(split_key)
    if split_button is not None:
        split_button.disabled = not view._is_split_action_enabled(
            line_index,
            word_index,
        )

    vertical_split_button = view._word_vertical_split_button_refs.get(split_key)
    if vertical_split_button is not None:
        vertical_split_button.disabled = not view._is_vertical_split_action_enabled(
            line_index,
            word_index,
        )


_COMPONENT_DISPLAY_LABELS = {
    "footnote marker": "Footnote Marker",
    "drop cap": "Drop Cap",
    "subscript": "Subscript",
    "superscript": "Superscript",
}


class WordEditDialog:
    """Per-word edit dialog: encapsulates state and UI building.

    Replaces the former ``open_word_edit_dialog`` procedural function.
    Closures that shared mutable state via ``nonlocal`` are now methods
    and the shared state lives as instance attributes.
    """

    def __init__(
        self,
        view: Any,
        *,
        line_index: int,
        word_index: int,
        split_word_index: int,
        word_match: Any,
    ) -> None:
        self._view = view
        self._line_index = line_index
        self._word_index = word_index
        self._split_word_index = split_word_index
        self._word_match = word_match
        self._split_key: tuple[int, int] = (line_index, split_word_index)

        # Mutable state (formerly ``nonlocal``)
        self._current_zoom: float = 2.0
        self._bbox_nudge_step_px: int = 5
        self._pending_bbox_deltas: tuple[float, float, float, float] = (
            0.0,
            0.0,
            0.0,
            0.0,
        )

        # Neighbour words
        line_match = view._line_match_by_index(line_index)
        indexed = {
            wm.word_index: wm
            for wm in (line_match.word_matches if line_match else [])
            if wm.word_index is not None
        }
        self._previous_word_match = indexed.get(split_word_index - 1)
        self._next_word_match = indexed.get(split_word_index + 1)
        self._can_merge_previous = (
            view.merge_word_left_callback is not None
            and split_word_index >= 0
            and self._previous_word_match is not None
        )
        self._can_merge_next = (
            view.merge_word_right_callback is not None
            and split_word_index >= 0
            and self._next_word_match is not None
        )

        # Style / scope / component options and current selection
        self._style_options: dict[str, str] = {
            sl: str(sl).title() for sl in view.word_operations.supported_styles
        }
        self._scope_options: dict[str, str] = {
            "": "--",
            "whole": "Whole",
            "part": "Part",
        }
        self._component_options: dict[str, str] = {
            cl: _COMPONENT_DISPLAY_LABELS.get(cl, str(cl).title())
            for cl in view.word_operations.supported_components
        }
        self._selected_style_value: str | None = next(iter(self._style_options), None)
        self._selected_scope_value: str = ""
        self._selected_component_value: str | None = next(
            iter(self._component_options), None
        )

        # UI elements – populated in ``open()``
        self._dialog: Any = None
        self._dialog_card: Any = None
        self._scope_select: Any = None
        self._current_image_slot: Any = None
        self._tag_chips_slot: Any = None
        self._split_button: Any = None
        self._vertical_split_button: Any = None
        self._saved_image_ref: Any = None
        self._saved_image_size: Any = None

    # -- Word match helpers -------------------------------------------------

    def _render_word_preview(
        self,
        title: str,
        preview_word_index: int,
        preview_word_match: Any,
    ) -> None:
        with ui.column().classes("items-center").style("min-width: 10rem; gap: 2px;"):
            ui.label(title).classes("text-caption")
            if preview_word_match is None:
                ui.label("No word").classes("text-grey-6 text-caption")
                return
            self._view.renderer.create_image_cell(
                self._line_index,
                preview_word_index,
                preview_word_match,
                interactive=False,
            )
            ui.label(str(preview_word_match.ocr_text or "[empty]")).classes(
                "text-caption monospace"
            )

    def _latest_word_match(self) -> Any:
        latest = self._view._line_match_by_index(self._line_index)
        if latest is None:
            return self._word_match
        for wm in latest.word_matches:
            if wm.word_index == self._split_word_index:
                return wm
        if latest.word_matches:
            return latest.word_matches[0]
        return self._word_match

    def _current_word_match_for_render(self) -> Any:
        latest = self._view._line_match_by_index(self._line_index)
        if latest is None:
            return self._word_match
        for wm in latest.word_matches:
            if wm.word_index == self._split_word_index:
                return wm
        return self._word_match

    def _rerender_dialog(self) -> None:
        self._dialog.close()
        ui.timer(
            0,
            lambda: open_word_edit_dialog(
                self._view,
                line_index=self._line_index,
                word_index=self._word_index,
                split_word_index=self._split_word_index,
                word_match=self._latest_word_match(),
            ),
            once=True,
        )

    # -- Layout helpers -----------------------------------------------------

    def _column_target_width(
        self,
        preview_word_index: int,
        preview_word_match: Any,
        *,
        zoom: float,
    ) -> float:
        if preview_word_match is None:
            return 160.0
        try:
            slice_meta = self._view.bbox.get_word_image_slice(
                preview_word_match,
                line_index=self._line_index,
                word_index=preview_word_index,
            )
        except Exception:
            slice_meta = None
        base_image_width = float(
            (slice_meta or {}).get("display_width", 120.0) or 120.0
        )
        rendered_image_width = base_image_width * max(0.5, float(zoom))
        return max(160.0, rendered_image_width + 24.0)

    def _dialog_card_style_for_content(self) -> str:
        prev_width = self._column_target_width(
            self._split_word_index - 1, self._previous_word_match, zoom=1.0
        )
        curr_width = self._column_target_width(
            self._split_word_index,
            self._current_word_match_for_render(),
            zoom=self._current_zoom,
        )
        next_width = self._column_target_width(
            self._split_word_index + 1, self._next_word_match, zoom=1.0
        )
        needed_px = prev_width + curr_width + next_width + 24.0 + 96.0
        needed_px = min(max(760.0, needed_px), 1600.0)
        return f"max-width: {needed_px:.0f}px; width: min(98vw, {needed_px:.0f}px);"

    # -- Image / tag rendering ----------------------------------------------

    def _render_current_interactive_image(self) -> None:
        self._current_image_slot.clear()
        with self._current_image_slot:
            self._view.renderer.create_image_cell(
                self._line_index,
                self._split_word_index,
                self._current_word_match_for_render(),
                interactive=True,
                zoom_scale=self._current_zoom,
                bbox_preview_deltas=self._pending_bbox_deltas,
            )

    def _refresh_open_dialog_content(self) -> None:
        self._dialog_card.style(self._dialog_card_style_for_content())
        self._render_current_interactive_image()

    def _render_tag_chips(self) -> None:
        self._tag_chips_slot.clear()
        current_tag_items = self._view._word_display_tag_items(
            self._current_word_match_for_render()
        )
        if not current_tag_items:
            return

        with self._tag_chips_slot:
            with ui.row().classes("items-center justify-start gap-1 full-width"):
                for item in current_tag_items:
                    with (
                        ui.row()
                        .classes("items-center gap-1 word-edit-tag-chip")
                        .style(self._view._word_tag_chip_style(item["kind"]))
                    ) as chip:
                        chip.props('data-testid="word-edit-tag-chip"')
                        ui.label(item["display"]).classes("text-caption")
                        clear_button = ui.button(
                            icon="close",
                            on_click=lambda _event, tag=item: (
                                (
                                    self._refresh_open_dialog_content(),
                                    self._render_tag_chips(),
                                )
                                if self._view._clear_word_tag(
                                    self._line_index,
                                    self._split_word_index,
                                    kind=tag["kind"],
                                    label=tag["label"],
                                )
                                else None
                            ),
                        ).props(
                            'flat dense round size=xs data-testid="word-edit-tag-clear-button"'
                        )
                        clear_button.classes("word-edit-tag-clear-button")
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

    # -- Zoom ---------------------------------------------------------------

    def _set_current_zoom(self, value: object) -> None:
        if value not in (1, 2, 5):
            return
        self._current_zoom = float(value)
        self._dialog_card.style(self._dialog_card_style_for_content())
        self._render_current_interactive_image()

    # -- Style / scope / component ------------------------------------------

    def _scope_value_for_style(self, style_value: str | None) -> str:
        if not style_value:
            return ""
        render_word_match = self._current_word_match_for_render()
        word_object = getattr(render_word_match, "word_object", None)
        if word_object is None:
            return ""
        try:
            style_scopes = dict(
                getattr(word_object, "text_style_label_scopes", {}) or {}
            )
        except Exception:
            return ""
        scope_value = style_scopes.get(str(style_value).strip().lower())
        if scope_value is None:
            return ""
        normalized = str(scope_value).strip().lower()
        return normalized if normalized in {"whole", "part"} else ""

    def _sync_scope_value_for_selected_style(self) -> None:
        self._selected_scope_value = self._scope_value_for_style(
            self._selected_style_value
        )
        if self._scope_select is not None:
            self._scope_select.value = self._selected_scope_value

    def _set_selected_style(self, event: Any) -> None:
        self._selected_style_value = str(event.value) if event.value else None
        self._sync_scope_value_for_selected_style()

    def _set_selected_component(self, event: Any) -> None:
        self._selected_component_value = str(event.value) if event.value else None

    def _apply_selected_style_from_dialog(self) -> None:
        if self._split_word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word to apply style", type_="warning"
            )
            return
        if not self._selected_style_value:
            self._view._safe_notify("Select a style to apply", type_="warning")
            return
        result = self._view.word_operations.apply_style_to_word(
            self._line_index,
            self._split_word_index,
            self._selected_style_value,
        )
        self._view._safe_notify(result.message, type_=result.severity)
        if result.updated_count > 0:
            self._refresh_open_dialog_content()
            self._sync_scope_value_for_selected_style()
            self._render_tag_chips()

    def _apply_scope_for_selected_style(self, scope_value: str) -> None:
        if self._split_word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word to apply scope",
                type_="warning",
            )
            return
        if not self._selected_style_value:
            self._view._safe_notify(
                "Select a style before setting scope",
                type_="warning",
            )
            return

        if scope_value in {"whole", "part"}:
            result = self._view.word_operations.apply_scope_to_word_style(
                self._line_index,
                self._split_word_index,
                self._selected_style_value,
                scope_value,
            )
        else:
            result = self._view.word_operations.clear_scope_on_word_style(
                self._line_index,
                self._split_word_index,
                self._selected_style_value,
            )

        self._view._safe_notify(result.message, type_=result.severity)
        if result.updated_count > 0:
            self._refresh_open_dialog_content()
            self._sync_scope_value_for_selected_style()
            self._render_tag_chips()

    def _apply_selected_component_from_dialog(self, *, enabled: bool) -> None:
        if self._split_word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word to apply component",
                type_="warning",
            )
            return
        if not self._selected_component_value:
            self._view._safe_notify(
                "Select a component to update",
                type_="warning",
            )
            return
        result = self._view.word_operations.apply_component_to_word(
            self._line_index,
            self._split_word_index,
            self._selected_component_value,
            enabled=enabled,
        )
        self._view._safe_notify(result.message, type_=result.severity)
        if result.updated_count > 0:
            self._refresh_open_dialog_content()
            self._render_tag_chips()

    # -- Bounding box -------------------------------------------------------

    def _set_bbox_nudge_step(self, value: object) -> None:
        try:
            step = int(float(value))
        except Exception:
            return
        if step <= 0:
            return
        self._bbox_nudge_step_px = step

    def _accumulate_bbox_nudge(
        self,
        *,
        left_units: float,
        right_units: float,
        top_units: float,
        bottom_units: float,
    ) -> None:
        step = float(self._bbox_nudge_step_px)
        pl, pr, pt, pb = self._pending_bbox_deltas
        self._pending_bbox_deltas = (
            pl + float(left_units) * step,
            pr + float(right_units) * step,
            pt + float(top_units) * step,
            pb + float(bottom_units) * step,
        )
        self._refresh_open_dialog_content()

    def _stage_crop_to_marker(self, direction: str) -> None:  # noqa: C901
        view = self._view
        split_key = self._split_key
        split_word_index = self._split_word_index
        line_index = self._line_index

        if view.nudge_word_bbox_callback is None:
            view._safe_notify("Edit bbox function not available", type_="warning")
            return
        if split_word_index < 0:
            view._safe_notify(
                "Select a valid OCR word bbox to edit",
                type_="warning",
            )
            return

        split_x_fraction = view._word_split_fractions.get(split_key)
        split_y_fraction = view._word_split_y_fractions.get(split_key)
        split_y_px = view._word_split_marker_y.get(split_key)
        image_size = view._word_split_image_sizes.get(split_key)
        if image_size is None:
            view._safe_notify(
                "Click inside the word image to place a marker first",
                type_="warning",
            )
            return

        line_word_match = view._line_word_match_by_ocr_index(
            line_index,
            split_word_index,
        )
        if line_word_match is None:
            view._safe_notify(
                "Selected word is no longer available",
                type_="warning",
            )
            return

        bbox_width = 0.0
        bbox_height = 0.0
        line_match = view._line_match_by_index(line_index)
        page_image = getattr(line_match, "page_image", None) if line_match else None
        if page_image is not None:
            try:
                preview_bbox = view.bbox.preview_bbox_for_word(
                    line_word_match,
                    page_image,
                    line_index=line_index,
                    word_index=split_word_index,
                    bbox_preview_deltas=self._pending_bbox_deltas,
                )
            except Exception:
                preview_bbox = None
            if preview_bbox is not None:
                px1, py1, px2, py2 = preview_bbox
                bbox_width = max(0.0, float(px2) - float(px1))
                bbox_height = max(0.0, float(py2) - float(py1))

        if bbox_width <= 0.0 or bbox_height <= 0.0:
            word_object = getattr(line_word_match, "word_object", None)
            bbox = getattr(word_object, "bounding_box", None)
            bbox_width = float(getattr(bbox, "width", 0.0) or 0.0)
            bbox_height = float(getattr(bbox, "height", 0.0) or 0.0)

        image_width, image_height = image_size
        if (
            bbox_width <= 0.0
            or bbox_height <= 0.0
            or image_width <= 0.0
            or image_height <= 0.0
        ):
            view._safe_notify(
                "Cannot crop: invalid word bounding box",
                type_="warning",
            )
            return

        left_delta = 0.0
        right_delta = 0.0
        top_delta = 0.0
        bottom_delta = 0.0

        if direction == "above":
            if split_y_fraction is None:
                if split_y_px is None:
                    view._safe_notify(
                        "Click inside the word image to place a marker first",
                        type_="warning",
                    )
                    return
                split_y_fraction = float(split_y_px) / float(image_height)
            else:
                split_y_fraction = float(split_y_fraction)
            if split_y_fraction <= 0.0 or split_y_fraction >= 1.0:
                view._safe_notify("Marker is out of bounds", type_="warning")
                return
            top_delta = -bbox_height * split_y_fraction
        elif direction == "below":
            if split_y_fraction is None:
                if split_y_px is None:
                    view._safe_notify(
                        "Click inside the word image to place a marker first",
                        type_="warning",
                    )
                    return
                split_y_fraction = float(split_y_px) / float(image_height)
            else:
                split_y_fraction = float(split_y_fraction)
            if split_y_fraction <= 0.0 or split_y_fraction >= 1.0:
                view._safe_notify("Marker is out of bounds", type_="warning")
                return
            bottom_delta = -bbox_height * (1.0 - split_y_fraction)
        elif direction == "left":
            if split_x_fraction is None:
                view._safe_notify(
                    "Click inside the word image to place a marker first",
                    type_="warning",
                )
                return
            split_x_fraction = float(split_x_fraction)
            if split_x_fraction <= 0.0 or split_x_fraction >= 1.0:
                view._safe_notify("Marker is out of bounds", type_="warning")
                return
            left_delta = -bbox_width * split_x_fraction
        elif direction == "right":
            if split_x_fraction is None:
                view._safe_notify(
                    "Click inside the word image to place a marker first",
                    type_="warning",
                )
                return
            split_x_fraction = float(split_x_fraction)
            if split_x_fraction <= 0.0 or split_x_fraction >= 1.0:
                view._safe_notify("Marker is out of bounds", type_="warning")
                return
            right_delta = -bbox_width * (1.0 - split_x_fraction)
        else:
            view._safe_notify("Unsupported crop direction", type_="warning")
            return

        pl, pr, pt, pb = self._pending_bbox_deltas
        self._pending_bbox_deltas = (
            pl + left_delta,
            pr + right_delta,
            pt + top_delta,
            pb + bottom_delta,
        )
        self._refresh_open_dialog_content()

    def _reset_pending_bbox_nudges(self) -> None:
        self._pending_bbox_deltas = (0.0, 0.0, 0.0, 0.0)
        self._refresh_open_dialog_content()

    def _apply_pending_bbox_nudges(self, *, refine_after: bool) -> None:
        view = self._view
        if view.nudge_word_bbox_callback is None:
            view._safe_notify(
                "Edit bbox function not available",
                type_="warning",
            )
            return
        if self._split_word_index < 0:
            view._safe_notify(
                "Select a valid OCR word bbox to edit",
                type_="warning",
            )
            return

        left_delta, right_delta, top_delta, bottom_delta = self._pending_bbox_deltas
        if (
            left_delta == 0.0
            and right_delta == 0.0
            and top_delta == 0.0
            and bottom_delta == 0.0
        ):
            view._safe_notify("No pending bbox edits to apply", type_="warning")
            return

        try:
            success = view.nudge_word_bbox_callback(
                self._line_index,
                self._split_word_index,
                left_delta,
                right_delta,
                top_delta,
                bottom_delta,
                refine_after,
            )
            if success:
                self._pending_bbox_deltas = (0.0, 0.0, 0.0, 0.0)
                view._refresh_local_line_match_from_line_object(self._line_index)
                view._update_summary()
                view.renderer.rerender_word_column(
                    self._line_index, self._split_word_index
                )
                self._refresh_open_dialog_content()
                if refine_after:
                    view._safe_notify(
                        "Applied bbox fine-tune edits and refined",
                        type_="positive",
                    )
                else:
                    view._safe_notify(
                        "Applied bbox fine-tune edits",
                        type_="positive",
                    )
            else:
                view._safe_notify("Failed to apply bbox edits", type_="warning")
        except Exception as error:
            view._safe_notify(
                f"Error applying bbox edits: {error}",
                type_="negative",
            )

    def _stage_refine_preview(self, *, expand: bool) -> None:
        deltas = self._view.bbox.compute_refine_preview_deltas(
            self._line_index,
            self._split_word_index,
            expand=expand,
            pending_deltas=self._pending_bbox_deltas,
        )
        if deltas is None:
            self._view._safe_notify(
                "Could not compute refine preview",
                type_="warning",
            )
            return
        self._pending_bbox_deltas = deltas
        self._refresh_open_dialog_content()

    def _apply_and_close(self) -> None:
        left, right, top, bottom = self._pending_bbox_deltas
        if left != 0.0 or right != 0.0 or top != 0.0 or bottom != 0.0:
            self._apply_pending_bbox_nudges(refine_after=False)
        self._dialog.close()

    def _cleanup(self) -> None:
        view = self._view
        split_key = self._split_key
        view._word_split_button_refs.pop(split_key, None)
        view._word_vertical_split_button_refs.pop(split_key, None)
        if self._saved_image_ref is not None:
            view._word_split_image_refs[split_key] = self._saved_image_ref
        else:
            view._word_split_image_refs.pop(split_key, None)
        if self._saved_image_size is not None:
            view._word_split_image_sizes[split_key] = self._saved_image_size
        else:
            view._word_split_image_sizes.pop(split_key, None)
        view._word_split_hover_positions.pop(split_key, None)
        view._word_split_hover_keys.discard(split_key)
        view._word_split_y_fractions.pop(split_key, None)
        if view.renderer._word_dialog_refresh_key == split_key:
            view.renderer._word_dialog_refresh_key = None
            view.renderer._word_dialog_refresh_callback = None
        if self._split_word_index >= 0:
            view.gt_editing._word_style_button_refs.pop(split_key, None)

    # -- Main dialog UI builder ---------------------------------------------

    def open(self) -> None:  # noqa: C901
        """Build and display the dialog."""
        view = self._view
        line_index = self._line_index
        word_index = self._word_index
        split_word_index = self._split_word_index
        word_match = self._word_match
        split_key = self._split_key

        dialog_host = (
            view.container if view._has_active_ui_context(view.container) else None
        )
        if dialog_host is not None:
            with dialog_host:
                self._dialog = ui.dialog()
        else:
            self._dialog = ui.dialog()

        with self._dialog:
            self._dialog_card = ui.card().classes("w-full")
            self._dialog_card.style(self._dialog_card_style_for_content())
        with self._dialog_card:
            with ui.row().classes("items-center justify-between full-width"):
                ui.label(f"Edit Line {line_index + 1}, Word {word_index + 1}").classes(
                    "text-subtitle1"
                )
                with ui.row().classes("items-center gap-1"):
                    ui.button(icon="check", on_click=self._apply_and_close).props(
                        'flat round dense color=green-7 data-testid="dialog-apply-close-button"'
                    ).tooltip("Apply and close")
                    ui.button(icon="close", on_click=self._dialog.close).props(
                        'flat round dense color=grey-7 data-testid="dialog-close-button"'
                    ).tooltip("Close without saving")

            with ui.column().classes("full-width").style("gap: 8px;"):
                with (
                    ui.row()
                    .classes("full-width justify-between no-wrap")
                    .style("column-gap: 12px; overflow-x: auto;")
                ):
                    self._render_word_preview(
                        "Previous",
                        split_word_index - 1,
                        self._previous_word_match,
                    )
                    with (
                        ui.column()
                        .classes("items-center")
                        .style("min-width: 10rem; gap: 2px;")
                    ):
                        ui.label("Current").classes("text-caption")
                        self._current_image_slot = ui.column().classes("items-center")

                        self._saved_image_ref = view._word_split_image_refs.get(
                            split_key
                        )
                        self._saved_image_size = view._word_split_image_sizes.get(
                            split_key
                        )

                        self._tag_chips_slot = (
                            ui.column().classes("full-width").style("gap: 0;")
                        )

                        self._render_current_interactive_image()
                        view.renderer._word_dialog_refresh_key = split_key
                        view.renderer._word_dialog_refresh_callback = (
                            self._refresh_open_dialog_content
                        )
                        ui.toggle(
                            options={1: "1x", 2: "2x", 5: "5x"},
                            value=2,
                            on_change=lambda event: self._set_current_zoom(event.value),
                        ).props("dense")
                        ui.label(str(word_match.ocr_text or "[empty]")).classes(
                            "text-caption monospace"
                        )
                        gt_initial_value = str(word_match.ground_truth_text or "")
                        gt_input = (
                            ui.input(
                                label="GT",
                                value=gt_initial_value,
                            )
                            .props("dense outlined")
                            .classes("monospace")
                        )
                        view.gt_editing._set_word_gt_input_width(
                            gt_input,
                            value=gt_initial_value,
                            fallback_text=str(word_match.ocr_text or ""),
                        )
                        gt_input.on_value_change(
                            lambda event: view.gt_editing._handle_word_gt_input_change(
                                gt_input,
                                str(event.value or ""),
                                str(word_match.ocr_text or ""),
                            )
                        )
                        gt_input.on(
                            "blur",
                            lambda _event: view._commit_word_gt_input_change(
                                line_index,
                                split_word_index,
                                gt_input,
                            ),
                        )
                        gt_input.on(
                            "keydown.enter",
                            lambda _event: view._commit_word_gt_input_change(
                                line_index,
                                split_word_index,
                                gt_input,
                            ),
                        )
                        gt_input.enabled = (
                            view.edit_word_ground_truth_callback is not None
                            and split_word_index >= 0
                        )

                        self._sync_scope_value_for_selected_style()

                    self._render_word_preview(
                        "Next",
                        split_word_index + 1,
                        self._next_word_match,
                    )

                ui.separator()
                with (
                    ui.row()
                    .classes("items-end justify-start gap-1 full-width")
                    .style("flex-wrap: wrap;")
                ):
                    style_select = ui.select(
                        options=self._style_options,
                        value=self._selected_style_value,
                        label="Style",
                    ).props("dense outlined options-dense")
                    style_select.classes("text-caption")
                    style_select.style(
                        "min-width: 122px; max-width: 140px; font-size: 0.72rem;"
                    )
                    style_select.on_value_change(self._set_selected_style)
                    style_select.enabled = split_word_index >= 0

                    self._scope_select = ui.select(
                        options=self._scope_options,
                        value=self._selected_scope_value,
                        label="Scope",
                    ).props("dense outlined options-dense")
                    self._scope_select.classes("text-caption")
                    self._scope_select.style(
                        "min-width: 96px; max-width: 108px; font-size: 0.72rem;"
                    )
                    self._scope_select.on_value_change(
                        lambda event: self._apply_scope_for_selected_style(
                            str(event.value or "")
                        )
                    )
                    self._scope_select.enabled = split_word_index >= 0

                    apply_style_button = ui.button(
                        "Apply Style",
                        on_click=self._apply_selected_style_from_dialog,
                    ).props("dense no-caps size=sm")
                    style_word_text_button(apply_style_button, compact=True)
                    apply_style_button.style(
                        "min-width: 80px; padding-left: 6px; padding-right: 6px; "
                        "font-size: 0.72rem;"
                    )
                    apply_style_button.props('data-testid="dialog-apply-style-button"')

                    component_select = ui.select(
                        options=self._component_options,
                        value=self._selected_component_value,
                        label="Component",
                    ).props("dense outlined options-dense")
                    component_select.classes("text-caption")
                    component_select.style(
                        "min-width: 138px; max-width: 162px; font-size: 0.72rem;"
                    )
                    component_select.on_value_change(self._set_selected_component)
                    component_select.enabled = split_word_index >= 0
                    apply_component_button = ui.button(
                        "Apply Component",
                        on_click=lambda: self._apply_selected_component_from_dialog(
                            enabled=True
                        ),
                    ).props("dense no-caps size=sm")
                    style_word_text_button(apply_component_button, compact=True)
                    apply_component_button.style(
                        "min-width: 98px; padding-left: 6px; padding-right: 6px; "
                        "font-size: 0.72rem;"
                    )
                    apply_component_button.props(
                        'data-testid="dialog-apply-component-button"'
                    )
                    clear_component_button = ui.button(
                        "Clear Component",
                        on_click=lambda: self._apply_selected_component_from_dialog(
                            enabled=False
                        ),
                    ).props("dense no-caps size=sm outline")
                    style_word_text_button(clear_component_button, compact=True)
                    clear_component_button.style(
                        "min-width: 102px; padding-left: 6px; padding-right: 6px; "
                        "font-size: 0.72rem;"
                    )
                    clear_component_button.props(
                        'data-testid="dialog-clear-component-button"'
                    )

                self._render_tag_chips()

                ui.separator()
                ui.label("Merge / Split").classes("text-caption text-grey-7")
                with ui.row().classes("items-center gap-2"):
                    merge_previous_button = ui.button(
                        "Merge Prev",
                        icon="call_merge",
                        on_click=lambda event: (
                            view.actions._handle_merge_word_left(
                                line_index,
                                split_word_index,
                                event,
                            ),
                            self._rerender_dialog(),
                        ),
                    ).tooltip("Merge current word into previous word")
                    style_word_text_button(merge_previous_button, compact=True)
                    merge_previous_button.style(
                        "min-width: 96px; padding-left: 6px; padding-right: 6px;"
                    )
                    merge_previous_button.disabled = not self._can_merge_previous
                    merge_previous_button.props(
                        'data-testid="dialog-merge-prev-button"'
                    )

                    merge_next_button = ui.button(
                        "Merge Next",
                        icon="call_merge",
                        on_click=lambda event: (
                            view.actions._handle_merge_word_right(
                                line_index,
                                split_word_index,
                                event,
                            ),
                            self._rerender_dialog(),
                        ),
                    ).tooltip("Merge with next word")
                    style_word_text_button(merge_next_button, compact=True)
                    merge_next_button.style(
                        "min-width: 96px; padding-left: 6px; padding-right: 6px;"
                    )
                    merge_next_button.disabled = not self._can_merge_next
                    merge_next_button.props('data-testid="dialog-merge-next-button"')

                    self._split_button = ui.button(
                        "H",
                        icon="call_split",
                        on_click=lambda event: (
                            self._rerender_dialog()
                            if view.actions._handle_split_word(
                                line_index,
                                split_word_index,
                                event,
                            )
                            else None
                        ),
                    ).tooltip("Split horizontally at marker (H-split: vertical line)")
                    style_word_text_button(self._split_button, compact=True)
                    self._split_button.style(
                        "min-width: 42px; padding-left: 4px; padding-right: 4px;"
                    )
                    self._split_button.disabled = not view._is_split_action_enabled(
                        line_index,
                        split_word_index,
                    )
                    self._split_button.props('data-testid="dialog-split-h-button"')

                    self._vertical_split_button = ui.button(
                        "V",
                        icon="call_split",
                        on_click=lambda event: (
                            self._rerender_dialog()
                            if view.actions._handle_split_word_vertical_closest_line(
                                line_index,
                                split_word_index,
                                event,
                            )
                            else None
                        ),
                    ).tooltip(
                        "Split vertically at marker (V-split: horizontal line, assign to closest line)"
                    )
                    style_word_text_button(self._vertical_split_button, compact=True)
                    self._vertical_split_button.style(
                        "min-width: 42px; padding-left: 4px; padding-right: 4px;"
                    )
                    self._vertical_split_button.disabled = (
                        not view._is_vertical_split_action_enabled(
                            line_index,
                            split_word_index,
                        )
                    )
                    self._vertical_split_button.props(
                        'data-testid="dialog-split-v-button"'
                    )

                    delete_button = ui.button(
                        icon="delete",
                        on_click=lambda event: view.actions._handle_delete_single_word(
                            line_index,
                            split_word_index,
                            event,
                        ),
                    ).tooltip("Delete word")
                    style_word_icon_button(delete_button, variant=ButtonVariant.DELETE)
                    delete_button.disabled = (
                        view.delete_words_callback is None or split_word_index < 0
                    )
                    delete_button.props('data-testid="dialog-delete-word-button"')

                ui.separator()
                ui.label("Bounding Box").classes("text-caption text-grey-7")

                if view.nudge_word_bbox_callback is not None and split_word_index >= 0:
                    pending_left, pending_right, pending_top, pending_bottom = (
                        self._pending_bbox_deltas
                    )
                    with ui.row().classes("items-center gap-2"):
                        crop_above_button = ui.button(
                            "Crop Above",
                            on_click=lambda _event: self._stage_crop_to_marker("above"),
                        ).tooltip("Stage removal above horizontal marker")
                        style_word_text_button(crop_above_button, compact=True)
                        crop_above_button.props(
                            'data-testid="dialog-crop-above-button"'
                        )
                        crop_below_button = ui.button(
                            "Crop Below",
                            on_click=lambda _event: self._stage_crop_to_marker("below"),
                        ).tooltip("Stage removal below horizontal marker")
                        style_word_text_button(crop_below_button, compact=True)
                        crop_below_button.props(
                            'data-testid="dialog-crop-below-button"'
                        )
                        crop_left_button = ui.button(
                            "Crop Left",
                            on_click=lambda _event: self._stage_crop_to_marker("left"),
                        ).tooltip("Stage removal left of vertical marker")
                        style_word_text_button(crop_left_button, compact=True)
                        crop_left_button.props('data-testid="dialog-crop-left-button"')
                        crop_right_button = ui.button(
                            "Crop Right",
                            on_click=lambda _event: self._stage_crop_to_marker("right"),
                        ).tooltip("Stage removal right of vertical marker")
                        style_word_text_button(crop_right_button, compact=True)
                        crop_right_button.props(
                            'data-testid="dialog-crop-right-button"'
                        )

                    with ui.row().classes("items-center gap-2"):
                        refine_preview_button = ui.button(
                            "Refine",
                            icon="auto_fix_high",
                            on_click=lambda _event: self._stage_refine_preview(
                                expand=False
                            ),
                        ).tooltip("Preview refine (stage without applying)")
                        style_word_text_button(refine_preview_button, compact=True)
                        refine_preview_button.disabled = (
                            view.refine_words_callback is None or split_word_index < 0
                        )
                        refine_preview_button.props(
                            'data-testid="dialog-refine-preview-button"'
                        )
                        expand_refine_preview_button = ui.button(
                            "Expand + Refine",
                            icon="unfold_more",
                            on_click=lambda _event: self._stage_refine_preview(
                                expand=True
                            ),
                        ).tooltip("Preview expand then refine (stage without applying)")
                        style_word_text_button(
                            expand_refine_preview_button, compact=True
                        )
                        expand_refine_preview_button.disabled = (
                            view.expand_then_refine_words_callback is None
                            or split_word_index < 0
                        )
                        expand_refine_preview_button.props(
                            'data-testid="dialog-expand-refine-preview-button"'
                        )

                    with ui.row().classes("items-center gap-1"):
                        ui.label("Fine tune")
                        ui.radio(
                            options={1: "1px", 5: "5px", 10: "10px"},
                            value=self._bbox_nudge_step_px,
                            on_change=lambda event: self._set_bbox_nudge_step(
                                event.value
                            ),
                        ).props("inline dense")
                    with ui.row().classes("items-center gap-1"):
                        ui.label("Left")
                        left_minus_button = ui.button(
                            "X-",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=-1.0,
                                right_units=0.0,
                                top_units=0.0,
                                bottom_units=0.0,
                            ),
                        )
                        style_word_text_button(left_minus_button, compact=True)
                        left_plus_button = ui.button(
                            "X+",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=1.0,
                                right_units=0.0,
                                top_units=0.0,
                                bottom_units=0.0,
                            ),
                        )
                        style_word_text_button(left_plus_button, compact=True)

                        ui.label("Right")
                        right_minus_button = ui.button(
                            "X-",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=0.0,
                                right_units=-1.0,
                                top_units=0.0,
                                bottom_units=0.0,
                            ),
                        )
                        style_word_text_button(right_minus_button, compact=True)
                        right_plus_button = ui.button(
                            "X+",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=0.0,
                                right_units=1.0,
                                top_units=0.0,
                                bottom_units=0.0,
                            ),
                        )
                        style_word_text_button(right_plus_button, compact=True)

                    with ui.row().classes("items-center gap-1"):
                        ui.label("Top")
                        top_minus_button = ui.button(
                            "Y-",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=0.0,
                                right_units=0.0,
                                top_units=-1.0,
                                bottom_units=0.0,
                            ),
                        )
                        style_word_text_button(top_minus_button, compact=True)
                        top_plus_button = ui.button(
                            "Y+",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=0.0,
                                right_units=0.0,
                                top_units=1.0,
                                bottom_units=0.0,
                            ),
                        )
                        style_word_text_button(top_plus_button, compact=True)

                        ui.label("Bottom")
                        bottom_minus_button = ui.button(
                            "Y-",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=0.0,
                                right_units=0.0,
                                top_units=0.0,
                                bottom_units=-1.0,
                            ),
                        )
                        style_word_text_button(bottom_minus_button, compact=True)
                        bottom_plus_button = ui.button(
                            "Y+",
                            on_click=lambda _event: self._accumulate_bbox_nudge(
                                left_units=0.0,
                                right_units=0.0,
                                top_units=0.0,
                                bottom_units=1.0,
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
                            "Reset",
                            on_click=lambda _event: self._reset_pending_bbox_nudges(),
                        ).tooltip("Reset pending bbox edits")
                        style_word_text_button(reset_button, compact=True)
                        reset_button.props('data-testid="dialog-reset-nudges-button"')
                        apply_button = ui.button(
                            "Apply",
                            on_click=lambda _event: self._apply_pending_bbox_nudges(
                                refine_after=False
                            ),
                        ).tooltip("Apply pending bbox edits")
                        style_word_text_button(apply_button, compact=True)
                        apply_button.props('data-testid="dialog-apply-nudges-button"')
                        apply_refine_button = ui.button(
                            "Apply + Refine",
                            on_click=lambda _event: self._apply_pending_bbox_nudges(
                                refine_after=True
                            ),
                        ).tooltip("Apply pending bbox edits and refine")
                        style_word_text_button(apply_refine_button, compact=True)
                        apply_refine_button.props(
                            'data-testid="dialog-apply-refine-nudges-button"'
                        )

        if split_word_index >= 0:
            view._word_split_button_refs[split_key] = self._split_button
            view._word_vertical_split_button_refs[split_key] = (
                self._vertical_split_button
            )
        self._dialog.on("hide", lambda _event: self._cleanup())
        self._dialog.open()


def open_word_edit_dialog(
    view: Any,
    *,
    line_index: int,
    word_index: int,
    split_word_index: int,
    word_match: Any,
) -> None:
    """Build and open the per-word edit dialog.

    The view object is expected to be WordMatchView-like and provide the methods
    and attributes referenced below.
    """
    WordEditDialog(
        view,
        line_index=line_index,
        word_index=word_index,
        split_word_index=split_word_index,
        word_match=word_match,
    ).open()
