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
    split_key = (line_index, split_word_index)
    line_match = view._line_match_by_index(line_index)
    indexed_word_matches = {
        wm.word_index: wm
        for wm in (line_match.word_matches if line_match else [])
        if wm.word_index is not None
    }
    previous_word_match = indexed_word_matches.get(split_word_index - 1)
    next_word_match = indexed_word_matches.get(split_word_index + 1)

    can_merge_previous = (
        view.merge_word_left_callback is not None
        and split_word_index >= 0
        and previous_word_match is not None
    )
    can_merge_next = (
        view.merge_word_right_callback is not None
        and split_word_index >= 0
        and next_word_match is not None
    )

    def _render_word_preview(
        title: str,
        preview_word_index: int,
        preview_word_match: Any,
    ) -> None:
        with ui.column().classes("items-center").style("min-width: 10rem; gap: 2px;"):
            ui.label(title).classes("text-caption")
            if preview_word_match is None:
                ui.label("No word").classes("text-grey-6 text-caption")
                return
            view._create_image_cell(
                line_index,
                preview_word_index,
                preview_word_match,
                interactive=False,
            )
            ui.label(str(preview_word_match.ocr_text or "[empty]")).classes(
                "text-caption monospace"
            )

    def _latest_word_match() -> Any:
        latest_line_match = view._line_match_by_index(line_index)
        if latest_line_match is None:
            return word_match
        for wm in latest_line_match.word_matches:
            if wm.word_index == split_word_index:
                return wm
        if latest_line_match.word_matches:
            return latest_line_match.word_matches[0]
        return word_match

    def _current_word_match_for_render() -> Any:
        """Resolve a live word-match instance for image rendering."""
        latest_line_match = view._line_match_by_index(line_index)
        if latest_line_match is None:
            return word_match
        for wm in latest_line_match.word_matches:
            if wm.word_index == split_word_index:
                return wm
        return word_match

    def _rerender_dialog() -> None:
        dialog.close()
        ui.timer(
            0,
            lambda: open_word_edit_dialog(
                view,
                line_index=line_index,
                word_index=word_index,
                split_word_index=split_word_index,
                word_match=_latest_word_match(),
            ),
            once=True,
        )

    current_zoom = 2.0

    def _column_target_width(
        preview_word_index: int,
        preview_word_match: Any,
        *,
        zoom: float,
    ) -> float:
        """Estimate column width from the rendered image width plus label padding."""
        if preview_word_match is None:
            return 160.0
        try:
            slice_meta = view._get_word_image_slice(
                preview_word_match,
                line_index=line_index,
                word_index=preview_word_index,
            )
        except Exception:
            slice_meta = None
        base_image_width = float(
            (slice_meta or {}).get("display_width", 120.0) or 120.0
        )
        rendered_image_width = base_image_width * max(0.5, float(zoom))
        return max(160.0, rendered_image_width + 24.0)

    def _dialog_card_style_for_content() -> str:
        prev_width = _column_target_width(
            split_word_index - 1,
            previous_word_match,
            zoom=1.0,
        )
        curr_width = _column_target_width(
            split_word_index,
            _current_word_match_for_render(),
            zoom=current_zoom,
        )
        next_width = _column_target_width(
            split_word_index + 1,
            next_word_match,
            zoom=1.0,
        )
        # 2 gaps between 3 columns + extra card padding and section chrome.
        needed_px = prev_width + curr_width + next_width + 24.0 + 96.0
        needed_px = min(max(760.0, needed_px), 1600.0)
        return f"max-width: {needed_px:.0f}px; width: min(98vw, {needed_px:.0f}px);"

    dialog_host = (
        view.container if view._has_active_ui_context(view.container) else None
    )
    if dialog_host is not None:
        with dialog_host:
            dialog = ui.dialog()
    else:
        dialog = ui.dialog()

    with dialog:
        dialog_card = ui.card().classes("w-full")
        dialog_card.style(_dialog_card_style_for_content())
    with (
        dialog_card,
    ):
        with ui.row().classes("items-center justify-between full-width"):
            ui.label(f"Edit Line {line_index + 1}, Word {word_index + 1}").classes(
                "text-subtitle1"
            )
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round dense color=grey-7"
            ).tooltip("Close")

        with ui.column().classes("full-width").style("gap: 8px;"):
            with (
                ui.row()
                .classes("full-width justify-between no-wrap")
                .style("column-gap: 12px; overflow-x: auto;")
            ):
                _render_word_preview(
                    "Previous",
                    split_word_index - 1,
                    previous_word_match,
                )
                with (
                    ui.column()
                    .classes("items-center")
                    .style("min-width: 10rem; gap: 2px;")
                ):
                    ui.label("Current").classes("text-caption")
                    current_image_slot = ui.column().classes("items-center")

                    def _render_current_interactive_image() -> None:
                        current_image_slot.clear()
                        with current_image_slot:
                            render_word_match = _current_word_match_for_render()
                            view._create_image_cell(
                                line_index,
                                split_word_index,
                                render_word_match,
                                interactive=True,
                                zoom_scale=current_zoom,
                            )

                    def _refresh_open_dialog_content() -> None:
                        dialog_card.style(_dialog_card_style_for_content())
                        _render_current_interactive_image()

                    def _set_current_zoom(value: object) -> None:
                        nonlocal current_zoom
                        if value not in (1, 2, 5):
                            return
                        current_zoom = float(value)
                        dialog_card.style(_dialog_card_style_for_content())
                        _render_current_interactive_image()

                    _render_current_interactive_image()
                    view._word_dialog_refresh_key = split_key
                    view._word_dialog_refresh_callback = _refresh_open_dialog_content
                    ui.toggle(
                        options={1: "1x", 2: "2x", 5: "5x"},
                        value=2,
                        on_change=lambda event: _set_current_zoom(event.value),
                    ).props("dense")
                    ui.label(str(word_match.ocr_text or "[empty]")).classes(
                        "text-caption monospace"
                    )
                _render_word_preview(
                    "Next",
                    split_word_index + 1,
                    next_word_match,
                )

            ui.separator()
            ui.label("Merge").classes("text-caption text-grey-7")
            with ui.row().classes("items-center gap-2"):
                merge_previous_button = ui.button(
                    "Merge Prev",
                    icon="call_merge",
                    on_click=lambda event: view._handle_merge_word_left(
                        line_index,
                        split_word_index,
                        event,
                    ),
                ).tooltip("Merge current word into previous word")
                style_word_text_button(merge_previous_button, compact=True)
                merge_previous_button.style(
                    "min-width: 96px; padding-left: 6px; padding-right: 6px;"
                )
                merge_previous_button.disabled = not can_merge_previous

                merge_next_button = ui.button(
                    "Merge Next",
                    icon="call_merge",
                    on_click=lambda event: view._handle_merge_word_right(
                        line_index,
                        split_word_index,
                        event,
                    ),
                ).tooltip("Merge with next word")
                style_word_text_button(merge_next_button, compact=True)
                merge_next_button.style(
                    "min-width: 96px; padding-left: 6px; padding-right: 6px;"
                )
                merge_next_button.disabled = not can_merge_next

            ui.label("Split / Delete").classes("text-caption text-grey-7")
            with ui.row().classes("items-center gap-2"):
                split_button = ui.button(
                    "H",
                    icon="call_split",
                    on_click=lambda event: (
                        _rerender_dialog()
                        if view._handle_split_word(
                            line_index,
                            split_word_index,
                            event,
                        )
                        else None
                    ),
                ).tooltip("Split horizontally at marker (H-split: vertical line)")
                style_word_text_button(split_button, compact=True)
                split_button.style(
                    "min-width: 42px; padding-left: 4px; padding-right: 4px;"
                )
                split_button.disabled = not view._is_split_action_enabled(
                    line_index,
                    split_word_index,
                )

                vertical_split_button = ui.button(
                    "V",
                    icon="call_split",
                    on_click=lambda event: (
                        _rerender_dialog()
                        if view._handle_split_word_vertical_closest_line(
                            line_index,
                            split_word_index,
                            event,
                        )
                        else None
                    ),
                ).tooltip(
                    "Split vertically at marker (V-split: horizontal line, assign to closest line)"
                )
                style_word_text_button(vertical_split_button, compact=True)
                vertical_split_button.style(
                    "min-width: 42px; padding-left: 4px; padding-right: 4px;"
                )
                vertical_split_button.disabled = (
                    not view._is_vertical_split_action_enabled(
                        line_index,
                        split_word_index,
                    )
                )

                delete_button = ui.button(
                    icon="delete",
                    on_click=lambda event: view._handle_delete_single_word(
                        line_index,
                        split_word_index,
                        event,
                    ),
                ).tooltip("Delete word")
                style_word_icon_button(delete_button, variant=ButtonVariant.DELETE)
                delete_button.disabled = (
                    view.delete_words_callback is None or split_word_index < 0
                )

            ui.separator()
            ui.label("Attributes & Bounding Box").classes("text-caption text-grey-7")
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Crop Above",
                    on_click=lambda event: view._handle_crop_word_to_marker(
                        line_index,
                        split_word_index,
                        "above",
                        event,
                    ),
                ).tooltip("Keep region above horizontal marker")
                ui.button(
                    "Crop Below",
                    on_click=lambda event: view._handle_crop_word_to_marker(
                        line_index,
                        split_word_index,
                        "below",
                        event,
                    ),
                ).tooltip("Keep region below horizontal marker")
                ui.button(
                    "Crop Left",
                    on_click=lambda event: view._handle_crop_word_to_marker(
                        line_index,
                        split_word_index,
                        "left",
                        event,
                    ),
                ).tooltip("Keep region left of vertical marker")
                ui.button(
                    "Crop Right",
                    on_click=lambda event: view._handle_crop_word_to_marker(
                        line_index,
                        split_word_index,
                        "right",
                        event,
                    ),
                ).tooltip("Keep region right of vertical marker")

            if view.nudge_word_bbox_callback is not None and split_word_index >= 0:
                view._bbox_editor_open_keys.add(split_key)
            view._create_word_actions_cell(
                line_index,
                split_word_index,
                word_match,
            )

    def _cleanup() -> None:
        view._word_split_button_refs.pop(split_key, None)
        view._word_vertical_split_button_refs.pop(split_key, None)
        view._word_split_image_refs.pop(split_key, None)
        view._word_split_image_sizes.pop(split_key, None)
        view._word_split_hover_positions.pop(split_key, None)
        view._word_split_hover_keys.discard(split_key)
        view._word_split_y_fractions.pop(split_key, None)
        view._bbox_editor_open_keys.discard(split_key)
        view._bbox_pending_deltas.pop(split_key, None)
        if view._word_dialog_refresh_key == split_key:
            view._word_dialog_refresh_key = None
            view._word_dialog_refresh_callback = None
        if split_word_index >= 0:
            view._word_style_button_refs.pop(split_key, None)

    if split_word_index >= 0:
        view._word_split_button_refs[split_key] = split_button
        view._word_vertical_split_button_refs[split_key] = vertical_split_button
    dialog.on("hide", lambda _event: _cleanup())
    dialog.open()
