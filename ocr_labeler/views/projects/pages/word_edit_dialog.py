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
            view.renderer.create_image_cell(
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
    bbox_nudge_step_px = 5
    pending_bbox_deltas: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

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
            slice_meta = view.bbox.get_word_image_slice(
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
            with ui.row().classes("items-center gap-1"):

                def _apply_and_close() -> None:
                    left, right, top, bottom = pending_bbox_deltas
                    if left != 0.0 or right != 0.0 or top != 0.0 or bottom != 0.0:
                        _apply_pending_bbox_nudges(refine_after=False)
                    dialog.close()

                ui.button(icon="check", on_click=_apply_and_close).props(
                    'flat round dense color=green-7 data-testid="dialog-apply-close-button"'
                ).tooltip("Apply and close")
                ui.button(icon="close", on_click=dialog.close).props(
                    'flat round dense color=grey-7 data-testid="dialog-close-button"'
                ).tooltip("Close without saving")

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

                    # Preserve the main table's image refs so we can restore
                    # them on dialog close (the dialog's _create_image_cell
                    # will overwrite _word_split_image_refs with its own
                    # interactive image, and cleanup must not simply pop).
                    _saved_image_ref = view._word_split_image_refs.get(split_key)
                    _saved_image_size = view._word_split_image_sizes.get(split_key)

                    def _render_current_interactive_image() -> None:
                        current_image_slot.clear()
                        with current_image_slot:
                            render_word_match = _current_word_match_for_render()
                            view.renderer.create_image_cell(
                                line_index,
                                split_word_index,
                                render_word_match,
                                interactive=True,
                                zoom_scale=current_zoom,
                                bbox_preview_deltas=pending_bbox_deltas,
                            )

                    def _refresh_open_dialog_content() -> None:
                        dialog_card.style(_dialog_card_style_for_content())
                        _render_current_interactive_image()

                    tag_chips_slot = ui.column().classes("full-width").style("gap: 0;")

                    def _render_tag_chips() -> None:
                        tag_chips_slot.clear()
                        current_tag_items = view._word_display_tag_items(
                            _current_word_match_for_render()
                        )
                        if not current_tag_items:
                            return

                        with tag_chips_slot:
                            with ui.row().classes(
                                "items-center justify-start gap-1 full-width"
                            ):
                                for item in current_tag_items:
                                    with (
                                        ui.row()
                                        .classes(
                                            "items-center gap-1 word-edit-tag-chip"
                                        )
                                        .style(view._word_tag_chip_style(item["kind"]))
                                    ) as chip:
                                        chip.props('data-testid="word-edit-tag-chip"')
                                        ui.label(item["display"]).classes(
                                            "text-caption"
                                        )
                                        clear_button = ui.button(
                                            icon="close",
                                            on_click=lambda _event, tag=item: (
                                                (
                                                    _refresh_open_dialog_content(),
                                                    _render_tag_chips(),
                                                )
                                                if view._clear_word_tag(
                                                    line_index,
                                                    split_word_index,
                                                    kind=tag["kind"],
                                                    label=tag["label"],
                                                )
                                                else None
                                            ),
                                        ).props(
                                            'flat dense round size=xs data-testid="word-edit-tag-clear-button"'
                                        )
                                        clear_button.classes(
                                            "word-edit-tag-clear-button"
                                        )
                                        clear_button.style(
                                            "min-width: 0; width: 14px; height: 14px;"
                                        )
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

                    def _set_current_zoom(value: object) -> None:
                        nonlocal current_zoom
                        if value not in (1, 2, 5):
                            return
                        current_zoom = float(value)
                        dialog_card.style(_dialog_card_style_for_content())
                        _render_current_interactive_image()

                    _render_current_interactive_image()
                    view.renderer._word_dialog_refresh_key = split_key
                    view.renderer._word_dialog_refresh_callback = (
                        _refresh_open_dialog_content
                    )
                    ui.toggle(
                        options={1: "1x", 2: "2x", 5: "5x"},
                        value=2,
                        on_change=lambda event: _set_current_zoom(event.value),
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

                    style_options = {
                        style_label: str(style_label).title()
                        for style_label in view.word_operations.supported_styles
                    }
                    scope_options = {
                        "": "--",
                        "whole": "Whole",
                        "part": "Part",
                    }
                    component_options = {
                        component_label: {
                            "footnote marker": "Footnote Marker",
                            "drop cap": "Drop Cap",
                            "subscript": "Subscript",
                            "superscript": "Superscript",
                        }.get(component_label, str(component_label).title())
                        for component_label in view.word_operations.supported_components
                    }
                    selected_style_value = next(iter(style_options), None)
                    selected_scope_value = ""
                    selected_component_value = next(iter(component_options), None)

                    scope_select = None

                    def _scope_value_for_style(style_value: str | None) -> str:
                        if not style_value:
                            return ""
                        render_word_match = _current_word_match_for_render()
                        word_object = getattr(render_word_match, "word_object", None)
                        if word_object is None:
                            return ""
                        try:
                            style_scopes = dict(
                                getattr(word_object, "text_style_label_scopes", {})
                                or {}
                            )
                        except Exception:
                            return ""

                        scope_value = style_scopes.get(str(style_value).strip().lower())
                        if scope_value is None:
                            return ""
                        normalized_scope = str(scope_value).strip().lower()
                        return (
                            normalized_scope
                            if normalized_scope in {"whole", "part"}
                            else ""
                        )

                    def _sync_scope_value_for_selected_style() -> None:
                        nonlocal selected_scope_value
                        selected_scope_value = _scope_value_for_style(
                            selected_style_value
                        )
                        if scope_select is not None:
                            scope_select.value = selected_scope_value

                    def _set_selected_style(event) -> None:
                        nonlocal selected_style_value
                        selected_style_value = str(event.value) if event.value else None
                        _sync_scope_value_for_selected_style()

                    def _set_selected_component(event) -> None:
                        nonlocal selected_component_value
                        selected_component_value = (
                            str(event.value) if event.value else None
                        )

                    def _apply_selected_style_from_dialog() -> None:
                        if split_word_index < 0:
                            view._safe_notify(
                                "Select a valid OCR word to apply style",
                                type_="warning",
                            )
                            return
                        if not selected_style_value:
                            view._safe_notify(
                                "Select a style to apply", type_="warning"
                            )
                            return
                        result = view.word_operations.apply_style_to_word(
                            line_index,
                            split_word_index,
                            selected_style_value,
                        )
                        view._safe_notify(result.message, type_=result.severity)
                        if result.updated_count > 0:
                            _refresh_open_dialog_content()
                            _sync_scope_value_for_selected_style()
                            _render_tag_chips()

                    def _apply_scope_for_selected_style(scope_value: str) -> None:
                        if split_word_index < 0:
                            view._safe_notify(
                                "Select a valid OCR word to apply scope",
                                type_="warning",
                            )
                            return
                        if not selected_style_value:
                            view._safe_notify(
                                "Select a style before setting scope",
                                type_="warning",
                            )
                            return

                        if scope_value in {"whole", "part"}:
                            result = view.word_operations.apply_scope_to_word_style(
                                line_index,
                                split_word_index,
                                selected_style_value,
                                scope_value,
                            )
                        else:
                            result = view.word_operations.clear_scope_on_word_style(
                                line_index,
                                split_word_index,
                                selected_style_value,
                            )

                        view._safe_notify(result.message, type_=result.severity)
                        if result.updated_count > 0:
                            _refresh_open_dialog_content()
                            _sync_scope_value_for_selected_style()
                            _render_tag_chips()

                    def _apply_selected_component_from_dialog(*, enabled: bool) -> None:
                        if split_word_index < 0:
                            view._safe_notify(
                                "Select a valid OCR word to apply component",
                                type_="warning",
                            )
                            return
                        if not selected_component_value:
                            view._safe_notify(
                                "Select a component to update",
                                type_="warning",
                            )
                            return
                        result = view.word_operations.apply_component_to_word(
                            line_index,
                            split_word_index,
                            selected_component_value,
                            enabled=enabled,
                        )
                        view._safe_notify(result.message, type_=result.severity)
                        if result.updated_count > 0:
                            _refresh_open_dialog_content()
                            _render_tag_chips()

                    _sync_scope_value_for_selected_style()

                _render_word_preview(
                    "Next",
                    split_word_index + 1,
                    next_word_match,
                )

            ui.separator()
            with (
                ui.row()
                .classes("items-end justify-start gap-1 full-width")
                .style("flex-wrap: wrap;")
            ):
                style_select = ui.select(
                    options=style_options,
                    value=selected_style_value,
                    label="Style",
                ).props("dense outlined options-dense")
                style_select.classes("text-caption")
                style_select.style(
                    "min-width: 122px; max-width: 140px; font-size: 0.72rem;"
                )
                style_select.on_value_change(_set_selected_style)
                style_select.enabled = split_word_index >= 0

                scope_select = ui.select(
                    options=scope_options,
                    value=selected_scope_value,
                    label="Scope",
                ).props("dense outlined options-dense")
                scope_select.classes("text-caption")
                scope_select.style(
                    "min-width: 96px; max-width: 108px; font-size: 0.72rem;"
                )
                scope_select.on_value_change(
                    lambda event: _apply_scope_for_selected_style(
                        str(event.value or "")
                    )
                )
                scope_select.enabled = split_word_index >= 0

                apply_style_button = ui.button(
                    "Apply Style",
                    on_click=_apply_selected_style_from_dialog,
                ).props("dense no-caps size=sm")
                style_word_text_button(apply_style_button, compact=True)
                apply_style_button.style(
                    "min-width: 80px; padding-left: 6px; padding-right: 6px; "
                    "font-size: 0.72rem;"
                )
                apply_style_button.props('data-testid="dialog-apply-style-button"')

                component_select = ui.select(
                    options=component_options,
                    value=selected_component_value,
                    label="Component",
                ).props("dense outlined options-dense")
                component_select.classes("text-caption")
                component_select.style(
                    "min-width: 138px; max-width: 162px; font-size: 0.72rem;"
                )
                component_select.on_value_change(_set_selected_component)
                component_select.enabled = split_word_index >= 0
                apply_component_button = ui.button(
                    "Apply Component",
                    on_click=lambda: _apply_selected_component_from_dialog(
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
                    on_click=lambda: _apply_selected_component_from_dialog(
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

            _render_tag_chips()

            ui.separator()
            ui.label("Merge / Split").classes("text-caption text-grey-7")
            with ui.row().classes("items-center gap-2"):
                merge_previous_button = ui.button(
                    "Merge Prev",
                    icon="call_merge",
                    on_click=lambda event: view.actions._handle_merge_word_left(
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
                    on_click=lambda event: view.actions._handle_merge_word_right(
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

                split_button = ui.button(
                    "H",
                    icon="call_split",
                    on_click=lambda event: (
                        _rerender_dialog()
                        if view.actions._handle_split_word(
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

            ui.separator()
            ui.label("Bounding Box").classes("text-caption text-grey-7")

            def _set_bbox_nudge_step(value: object) -> None:
                nonlocal bbox_nudge_step_px
                try:
                    step = int(float(value))
                except Exception:
                    return
                if step <= 0:
                    return
                bbox_nudge_step_px = step

            def _accumulate_bbox_nudge(
                *,
                left_units: float,
                right_units: float,
                top_units: float,
                bottom_units: float,
            ) -> None:
                nonlocal pending_bbox_deltas
                left_delta = float(left_units) * float(bbox_nudge_step_px)
                right_delta = float(right_units) * float(bbox_nudge_step_px)
                top_delta = float(top_units) * float(bbox_nudge_step_px)
                bottom_delta = float(bottom_units) * float(bbox_nudge_step_px)
                pending_left, pending_right, pending_top, pending_bottom = (
                    pending_bbox_deltas
                )
                pending_bbox_deltas = (
                    pending_left + left_delta,
                    pending_right + right_delta,
                    pending_top + top_delta,
                    pending_bottom + bottom_delta,
                )
                _refresh_open_dialog_content()

            def _stage_crop_to_marker(direction: str) -> None:
                nonlocal pending_bbox_deltas

                if view.nudge_word_bbox_callback is None:
                    view._safe_notify(
                        "Edit bbox function not available", type_="warning"
                    )
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
                page_image = (
                    getattr(line_match, "page_image", None) if line_match else None
                )
                if page_image is not None:
                    try:
                        preview_bbox = view.bbox.preview_bbox_for_word(
                            line_word_match,
                            page_image,
                            line_index=line_index,
                            word_index=split_word_index,
                            bbox_preview_deltas=pending_bbox_deltas,
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

                pending_left, pending_right, pending_top, pending_bottom = (
                    pending_bbox_deltas
                )
                pending_bbox_deltas = (
                    pending_left + left_delta,
                    pending_right + right_delta,
                    pending_top + top_delta,
                    pending_bottom + bottom_delta,
                )
                _refresh_open_dialog_content()

            def _reset_pending_bbox_nudges() -> None:
                nonlocal pending_bbox_deltas
                pending_bbox_deltas = (0.0, 0.0, 0.0, 0.0)
                _refresh_open_dialog_content()

            def _apply_pending_bbox_nudges(*, refine_after: bool) -> None:
                nonlocal pending_bbox_deltas
                if view.nudge_word_bbox_callback is None:
                    view._safe_notify(
                        "Edit bbox function not available",
                        type_="warning",
                    )
                    return
                if split_word_index < 0:
                    view._safe_notify(
                        "Select a valid OCR word bbox to edit",
                        type_="warning",
                    )
                    return

                left_delta, right_delta, top_delta, bottom_delta = pending_bbox_deltas
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
                        line_index,
                        split_word_index,
                        left_delta,
                        right_delta,
                        top_delta,
                        bottom_delta,
                        refine_after,
                    )
                    if success:
                        pending_bbox_deltas = (0.0, 0.0, 0.0, 0.0)
                        view._refresh_local_line_match_from_line_object(line_index)
                        view._update_summary()
                        view.renderer.rerender_word_column(line_index, split_word_index)
                        _refresh_open_dialog_content()
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

            if view.nudge_word_bbox_callback is not None and split_word_index >= 0:
                pending_left, pending_right, pending_top, pending_bottom = (
                    pending_bbox_deltas
                )
                with ui.row().classes("items-center gap-2"):
                    crop_above_button = ui.button(
                        "Crop Above",
                        on_click=lambda _event: _stage_crop_to_marker("above"),
                    ).tooltip("Stage removal above horizontal marker")
                    style_word_text_button(crop_above_button, compact=True)
                    crop_below_button = ui.button(
                        "Crop Below",
                        on_click=lambda _event: _stage_crop_to_marker("below"),
                    ).tooltip("Stage removal below horizontal marker")
                    style_word_text_button(crop_below_button, compact=True)
                    crop_left_button = ui.button(
                        "Crop Left",
                        on_click=lambda _event: _stage_crop_to_marker("left"),
                    ).tooltip("Stage removal left of vertical marker")
                    style_word_text_button(crop_left_button, compact=True)
                    crop_right_button = ui.button(
                        "Crop Right",
                        on_click=lambda _event: _stage_crop_to_marker("right"),
                    ).tooltip("Stage removal right of vertical marker")
                    style_word_text_button(crop_right_button, compact=True)

                def _stage_refine_preview(*, expand: bool) -> None:
                    nonlocal pending_bbox_deltas
                    deltas = view.bbox.compute_refine_preview_deltas(
                        line_index,
                        split_word_index,
                        expand=expand,
                        pending_deltas=pending_bbox_deltas,
                    )
                    if deltas is None:
                        view._safe_notify(
                            "Could not compute refine preview",
                            type_="warning",
                        )
                        return
                    pending_bbox_deltas = deltas
                    _refresh_open_dialog_content()

                with ui.row().classes("items-center gap-2"):
                    refine_preview_button = ui.button(
                        "Refine",
                        icon="auto_fix_high",
                        on_click=lambda _event: _stage_refine_preview(expand=False),
                    ).tooltip("Preview refine (stage without applying)")
                    style_word_text_button(refine_preview_button, compact=True)
                    refine_preview_button.disabled = (
                        view.refine_words_callback is None or split_word_index < 0
                    )
                    expand_refine_preview_button = ui.button(
                        "Expand + Refine",
                        icon="unfold_more",
                        on_click=lambda _event: _stage_refine_preview(expand=True),
                    ).tooltip("Preview expand then refine (stage without applying)")
                    style_word_text_button(expand_refine_preview_button, compact=True)
                    expand_refine_preview_button.disabled = (
                        view.expand_then_refine_words_callback is None
                        or split_word_index < 0
                    )

                with ui.row().classes("items-center gap-1"):
                    ui.label("Fine tune")
                    ui.radio(
                        options={1: "1px", 5: "5px", 10: "10px"},
                        value=bbox_nudge_step_px,
                        on_change=lambda event: _set_bbox_nudge_step(event.value),
                    ).props("inline dense")
                with ui.row().classes("items-center gap-1"):
                    ui.label("Left")
                    left_minus_button = ui.button(
                        "X-",
                        on_click=lambda _event: _accumulate_bbox_nudge(
                            left_units=-1.0,
                            right_units=0.0,
                            top_units=0.0,
                            bottom_units=0.0,
                        ),
                    )
                    style_word_text_button(left_minus_button, compact=True)
                    left_plus_button = ui.button(
                        "X+",
                        on_click=lambda _event: _accumulate_bbox_nudge(
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
                        on_click=lambda _event: _accumulate_bbox_nudge(
                            left_units=0.0,
                            right_units=-1.0,
                            top_units=0.0,
                            bottom_units=0.0,
                        ),
                    )
                    style_word_text_button(right_minus_button, compact=True)
                    right_plus_button = ui.button(
                        "X+",
                        on_click=lambda _event: _accumulate_bbox_nudge(
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
                        on_click=lambda _event: _accumulate_bbox_nudge(
                            left_units=0.0,
                            right_units=0.0,
                            top_units=-1.0,
                            bottom_units=0.0,
                        ),
                    )
                    style_word_text_button(top_minus_button, compact=True)
                    top_plus_button = ui.button(
                        "Y+",
                        on_click=lambda _event: _accumulate_bbox_nudge(
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
                        on_click=lambda _event: _accumulate_bbox_nudge(
                            left_units=0.0,
                            right_units=0.0,
                            top_units=0.0,
                            bottom_units=-1.0,
                        ),
                    )
                    style_word_text_button(bottom_minus_button, compact=True)
                    bottom_plus_button = ui.button(
                        "Y+",
                        on_click=lambda _event: _accumulate_bbox_nudge(
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
                        on_click=lambda _event: _reset_pending_bbox_nudges(),
                    ).tooltip("Reset pending bbox edits")
                    style_word_text_button(reset_button, compact=True)
                    apply_button = ui.button(
                        "Apply",
                        on_click=lambda _event: _apply_pending_bbox_nudges(
                            refine_after=False
                        ),
                    ).tooltip("Apply pending bbox edits")
                    style_word_text_button(apply_button, compact=True)
                    apply_refine_button = ui.button(
                        "Apply + Refine",
                        on_click=lambda _event: _apply_pending_bbox_nudges(
                            refine_after=True
                        ),
                    ).tooltip("Apply pending bbox edits and refine")
                    style_word_text_button(apply_refine_button, compact=True)

    def _cleanup() -> None:
        view._word_split_button_refs.pop(split_key, None)
        view._word_vertical_split_button_refs.pop(split_key, None)
        # Restore the main table's image ref/sizes so hover dashes keep
        # working after the dialog closes.
        if _saved_image_ref is not None:
            view._word_split_image_refs[split_key] = _saved_image_ref
        else:
            view._word_split_image_refs.pop(split_key, None)
        if _saved_image_size is not None:
            view._word_split_image_sizes[split_key] = _saved_image_size
        else:
            view._word_split_image_sizes.pop(split_key, None)
        view._word_split_hover_positions.pop(split_key, None)
        view._word_split_hover_keys.discard(split_key)
        view._word_split_y_fractions.pop(split_key, None)
        if view.renderer._word_dialog_refresh_key == split_key:
            view.renderer._word_dialog_refresh_key = None
            view.renderer._word_dialog_refresh_callback = None
        if split_word_index >= 0:
            view.gt_editing._word_style_button_refs.pop(split_key, None)

    if split_word_index >= 0:
        view._word_split_button_refs[split_key] = split_button
        view._word_vertical_split_button_refs[split_key] = vertical_split_button
    dialog.on("hide", lambda _event: _cleanup())
    dialog.open()
