import logging
from typing import Callable, Literal

from nicegui import events, ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel

logger = logging.getLogger(__name__)

_DRAG_JS_HANDLER = """
(e) => {
    const wrap = e.currentTarget.closest('.ocr-drag-wrap');
    if (!wrap) return;
    const rect = wrap.querySelector('.ocr-drag-rect');
    if (!rect) return;

    const t = e.type;
    if (t === 'mousedown') {
        const b = wrap.getBoundingClientRect();
        const x = e.clientX - b.left;
        const y = e.clientY - b.top;
        wrap.dataset.dragging = '1';
        wrap.dataset.sx = String(x);
        wrap.dataset.sy = String(y);
        rect.style.left = `${x}px`;
        rect.style.top = `${y}px`;
        rect.style.width = '0px';
        rect.style.height = '0px';
        rect.classList.remove('hidden');
        return;
    }

    if (t === 'mousemove') {
        if (wrap.dataset.dragging !== '1') return;
        const b = wrap.getBoundingClientRect();
        const x = e.clientX - b.left;
        const y = e.clientY - b.top;
        const sx = parseFloat(wrap.dataset.sx || '0');
        const sy = parseFloat(wrap.dataset.sy || '0');
        const left = Math.min(sx, x);
        const top = Math.min(sy, y);
        const width = Math.abs(x - sx);
        const height = Math.abs(y - sy);
        rect.style.left = `${left}px`;
        rect.style.top = `${top}px`;
        rect.style.width = `${width}px`;
        rect.style.height = `${height}px`;
        return;
    }

    if (t === 'mouseup' || t === 'mouseleave') {
        wrap.dataset.dragging = '0';
        rect.classList.add('hidden');
    }
}
"""


class ImageTabs:
    """Left side image tabs showing progressively processed page imagery."""

    def __init__(
        self,
        page_state_view_model: PageStateViewModel,
        on_words_selected: Callable[[set[tuple[int, int]]], None] | None = None,
        on_paragraphs_selected: Callable[[set[int]], None] | None = None,
        on_word_rebox_drawn: Callable[[float, float, float, float], None] | None = None,
        on_word_add_drawn: Callable[[float, float, float, float], None] | None = None,
    ):
        logger.debug("Initializing ImageTabs unified viewport")
        self.images: dict[str, ui.image] = {}
        self.visible_layers: dict[str, bool] = {
            "paragraphs": True,
            "lines": True,
            "words": True,
        }
        self.selection_mode: Literal["paragraph", "line", "word"] = "word"
        self.page_state_view_model = page_state_view_model
        self._on_words_selected = on_words_selected
        self._on_paragraphs_selected = on_paragraphs_selected
        self._on_word_rebox_drawn = on_word_rebox_drawn
        self._on_word_add_drawn = on_word_add_drawn
        self._drag_start: tuple[float, float] | None = None
        self._drag_current: tuple[float, float] | None = None
        self._drag_target_tab: str | None = None
        self._drag_remove_mode = False
        self._drag_add_mode = False
        self._word_rebox_mode = False
        self._word_add_mode = False
        self._selected_word_indices: set[tuple[int, int]] = set()
        self._selected_paragraph_indices: set[int] = set()
        self._selected_word_boxes: list[tuple[float, float, float, float]] = []
        self._selected_line_boxes: list[tuple[float, float, float, float]] = []
        self._selected_paragraph_boxes: list[tuple[float, float, float, float]] = []
        self._viewport_layer_overlay_cache: str = ""
        self._viewport_layer_overlay_cache_key: (
            tuple[object, bool, bool, bool] | None
        ) = None
        self._suspend_overlay_render: bool = False
        self._notified_error_keys: set[str] = set()
        # Register callback for direct image updates (bypasses data binding)
        self.page_state_view_model.set_image_update_callback(self._on_images_updated)
        logger.debug("ImageTabs initialization complete with callback registered")

    def _notify(self, message: str, type_: str = "warning") -> None:
        """Send UI notification through app-state queue with direct UI fallback."""
        project_state = getattr(self.page_state_view_model, "_project_state", None)
        app_state_model = getattr(project_state, "_app_state_model", None)
        app_state = getattr(app_state_model, "_app_state", None)
        if app_state is not None:
            app_state.queue_notification(message, type_)
            return
        ui.notify(message, type=type_)

    def _notify_once(self, key: str, message: str, type_: str = "warning") -> None:
        """Emit a notification once per key to avoid repeated toasts."""
        if key in self._notified_error_keys:
            return
        self._notified_error_keys.add(key)
        self._notify(message, type_)

    def build(self):
        logger.debug("Building ImageTabs UI components")
        with ui.column().classes("full-width full-height overflow-hidden") as col:
            with ui.column().classes("full-width shrink-0 sticky top-0 z-10 bg-white"):
                with ui.row().classes("items-center gap-4 wrap"):
                    ui.label("Layers").classes("text-sm text-gray-600")
                    ui.checkbox(
                        "Show Paragraphs",
                        value=self.visible_layers["paragraphs"],
                        on_change=lambda e: self._set_layer_visibility(
                            "paragraphs", bool(e.value)
                        ),
                    )
                    ui.checkbox(
                        "Show Lines",
                        value=self.visible_layers["lines"],
                        on_change=lambda e: self._set_layer_visibility(
                            "lines", bool(e.value)
                        ),
                    )
                    ui.checkbox(
                        "Show Words",
                        value=self.visible_layers["words"],
                        on_change=lambda e: self._set_layer_visibility(
                            "words", bool(e.value)
                        ),
                    )

                with ui.row().classes("items-center gap-4"):
                    ui.label("Selection Mode").classes("text-sm text-gray-600")
                    ui.radio(
                        options={
                            "paragraph": "Select Paragraphs",
                            "line": "Select Lines",
                            "word": "Select Words",
                        },
                        value=self.selection_mode,
                        on_change=lambda e: self._set_selection_mode(str(e.value)),
                    ).props("inline")

                with ui.row().classes("items-center gap-2 text-xs text-gray-600"):
                    ui.label("Legend").classes("text-xs text-gray-500")
                    ui.badge("Paragraphs").style(
                        "background: rgba(34,197,94,0.20); color: #166534; border: 1px solid rgba(22,163,74,0.65);"
                    )
                    ui.badge("Lines").style(
                        "background: rgba(236,72,153,0.20); color: #9d174d; border: 1px solid rgba(190,24,93,0.65);"
                    )
                    ui.badge("Words").style(
                        "background: rgba(59,130,246,0.18); color: #1e3a8a; border: 1px solid rgba(29,78,216,0.65);"
                    )

            with ui.column().classes(
                "items-start justify-start full-width grow min-h-0 overflow-auto"
            ):
                with ui.element("div").classes("relative inline-block ocr-drag-wrap"):
                    img = (
                        ui.interactive_image(
                            events=["mousedown", "mouseup", "mouseleave"],
                            on_mouse=self._handle_viewport_mouse,
                            sanitize=False,
                        )
                        .classes("self-start ocr-viewport-img")
                        .style("height: auto; width: auto; max-width: none;")
                    )
                    ui.element("div").classes(
                        "ocr-drag-rect absolute pointer-events-none hidden z-30"
                    ).style("border: 2px dashed #2563eb; background: transparent;")
                    self.images["Viewport"] = img

                    for event_name in (
                        "mousedown",
                        "mousemove",
                        "mouseup",
                        "mouseleave",
                    ):
                        img.on(event_name, js_handler=_DRAG_JS_HANDLER)

                    # If image sources were prepared before the viewport was built,
                    # apply the current source immediately to avoid a blank first render.
                    existing_source = str(
                        getattr(self.page_state_view_model, "original_image_source", "")
                        or ""
                    )
                    if existing_source:
                        if hasattr(img, "set_source"):
                            img.set_source(existing_source)
                        else:
                            img.source = existing_source
        self.container = col
        logger.debug("ImageTabs UI build complete with single viewport")
        return col

    def _set_layer_visibility(self, layer: str, visible: bool) -> None:
        if layer not in self.visible_layers:
            return
        self.visible_layers[layer] = visible
        self._viewport_layer_overlay_cache_key = None
        self._render_selection_overlay(self._selection_mode_tab())

    def _set_selection_mode(self, mode: str) -> None:
        if mode not in {"paragraph", "line", "word"}:
            return
        self.selection_mode = mode
        self._clear_drag_state()
        self._render_selection_overlay(self._selection_mode_tab())

    def _selection_mode_tab(self) -> str:
        if self.selection_mode == "paragraph":
            return "Paragraphs"
        if self.selection_mode == "line":
            return "Lines"
        return "Words"

    def _overlay_image(self, tab_name: str = "Words") -> ui.image | None:
        if "Viewport" in self.images:
            return self.images.get("Viewport")
        return self.images.get(tab_name)

    def _handle_viewport_mouse(self, event: events.MouseEventArguments) -> None:
        target = (
            "Words"
            if (self._word_rebox_mode or self._word_add_mode)
            else self._selection_mode_tab()
        )
        self._handle_drag_mouse(target, event)

    def _handle_drag_mouse(
        self, tab_name: str, event: events.MouseEventArguments
    ) -> None:
        """Handle drag selection gestures on an interactive image tab."""
        if tab_name == "Words" and (self._word_rebox_mode or self._word_add_mode):
            self._handle_word_rebox_drag(event)
            return

        event_type = getattr(event, "type", "")
        x = float(getattr(event, "image_x", 0.0))
        y = float(getattr(event, "image_y", 0.0))

        if event_type == "mousedown":
            self._drag_target_tab = tab_name
            self._drag_start = (x, y)
            self._drag_current = (x, y)
            self._drag_remove_mode = bool(getattr(event, "shift", False))
            self._drag_add_mode = bool(getattr(event, "ctrl", False))
            self._render_drag_overlay(tab_name)
            return

        if self._drag_start is None or self._drag_target_tab != tab_name:
            return

        if event_type == "mousemove":
            self._drag_current = (x, y)
            self._render_drag_overlay(tab_name)
            return

        if event_type == "mouseup":
            self._drag_current = (x, y)
            applied = self._apply_box_selection(tab_name)
            self._drag_start = None
            self._drag_current = None
            self._drag_target_tab = None
            self._drag_remove_mode = False
            self._drag_add_mode = False
            if not applied:
                self._render_selection_overlay(tab_name)
            return

        if event_type == "mouseleave":
            self._clear_drag_state()

    def _handle_word_rebox_drag(self, event: events.MouseEventArguments) -> None:
        """Handle drag gesture when word rebox mode is active."""
        event_type = getattr(event, "type", "")
        x = float(getattr(event, "image_x", 0.0))
        y = float(getattr(event, "image_y", 0.0))

        if event_type == "mousedown":
            self._drag_target_tab = "Words"
            self._drag_start = (x, y)
            self._drag_current = (x, y)
            self._drag_remove_mode = False
            self._drag_add_mode = False
            self._render_drag_overlay("Words")
            return

        if self._drag_start is None or self._drag_target_tab != "Words":
            return

        if event_type == "mousemove":
            self._drag_current = (x, y)
            self._render_drag_overlay("Words")
            return

        if event_type == "mouseup":
            self._drag_current = (x, y)
            if self._word_add_mode:
                self._emit_word_add_bbox()
            else:
                self._emit_word_rebox_bbox()
            self._drag_start = None
            self._drag_current = None
            self._drag_target_tab = None
            self._drag_remove_mode = False
            self._drag_add_mode = False
            self._word_rebox_mode = False
            self._word_add_mode = False
            self._render_selection_overlay("Words")
            return

        if event_type == "mouseleave":
            self._clear_drag_state()

    def _emit_word_rebox_bbox(self) -> None:
        """Emit a drawn rebox rectangle in source image coordinates."""
        if self._on_word_rebox_drawn is None:
            return
        if self._drag_start is None or self._drag_current is None:
            return

        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None
        if page is None:
            return

        x1, y1, x2, y2 = self._normalized_rect(*self._drag_start, *self._drag_current)
        scale_x, scale_y = self._get_display_scale(page, tab_name="Words")
        if scale_x <= 0.0 or scale_y <= 0.0:
            return

        source_rect = (
            x1 / scale_x,
            y1 / scale_y,
            x2 / scale_x,
            y2 / scale_y,
        )
        sx1, sy1, sx2, sy2 = source_rect
        if sx2 <= sx1 or sy2 <= sy1:
            return

        self._on_word_rebox_drawn(sx1, sy1, sx2, sy2)

    def enable_word_rebox_mode(self) -> None:
        """Enable drag-to-rebox mode on the Words image tab."""
        self._word_rebox_mode = True

    def enable_word_add_mode(self) -> None:
        """Enable drag-to-add-word mode on the Words image tab."""
        self._word_add_mode = True

    def _emit_word_add_bbox(self) -> None:
        """Emit a drawn add-word rectangle in source image coordinates."""
        if self._on_word_add_drawn is None:
            return
        if self._drag_start is None or self._drag_current is None:
            return

        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None
        if page is None:
            return

        x1, y1, x2, y2 = self._normalized_rect(*self._drag_start, *self._drag_current)
        scale_x, scale_y = self._get_display_scale(page, tab_name="Words")
        if scale_x <= 0.0 or scale_y <= 0.0:
            return

        sx1 = x1 / scale_x
        sy1 = y1 / scale_y
        sx2 = x2 / scale_x
        sy2 = y2 / scale_y
        if sx2 <= sx1 or sy2 <= sy1:
            return

        self._on_word_add_drawn(sx1, sy1, sx2, sy2)

    def _render_drag_overlay(self, tab_name: str) -> None:
        """Render selection overlay while drag is in progress."""
        if "Viewport" in self.images:
            # Client-side JS handlers render the drag rectangle for the viewport.
            return

        interactive_image = self._overlay_image(tab_name)
        if interactive_image is None:
            return

        if self._drag_start is None or self._drag_current is None:
            self._render_selection_overlay(tab_name)
            return

        drag_rect = self._build_drag_rect_overlay()
        self._render_selection_overlay(tab_name)
        current = getattr(interactive_image, "content", "") or ""
        overlay_content = f"{current}{drag_rect}"

        try:
            interactive_image.content = overlay_content
        except Exception:
            logger.debug("Failed to render drag overlay", exc_info=True)
            self._notify_once(
                "image-tabs-drag-overlay-render",
                "Failed to render selection overlay",
                type_="warning",
            )

    def _render_selection_overlay(self, tab_name: str = "Words") -> None:
        """Render selected boxes and optional drag rectangle overlay for a tab."""
        interactive_image = self._overlay_image(tab_name)
        if interactive_image is None:
            return
        overlay_parts: list[str] = []

        if "Viewport" in self.images:
            page_state = getattr(self.page_state_view_model, "_page_state", None)
            page = getattr(page_state, "current_page", None) if page_state else None
            if page is not None:
                overlay_parts.append(self._get_viewport_layer_overlay(page))
                self._append_viewport_selected_overlays(overlay_parts)
        else:
            selected_boxes = (
                self._selected_word_boxes
                if tab_name == "Words"
                else (
                    self._selected_line_boxes
                    if tab_name == "Lines"
                    else self._selected_paragraph_boxes
                )
            )

            for x1, y1, x2, y2 in selected_boxes:
                overlay_parts.append(
                    f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2 - x1):.2f}" '
                    f'height="{(y2 - y1):.2f}" fill="rgba(37,99,235,0.20)" '
                    'stroke="#1d4ed8" stroke-width="1" pointer-events="none" />'
                )

        try:
            content = "".join(overlay_parts)
            interactive_image.content = content
        except Exception:
            logger.debug("Failed to render drag overlay", exc_info=True)
            self._notify_once(
                "image-tabs-drag-overlay-render",
                "Failed to render selection overlay",
                type_="warning",
            )

    def _build_drag_rect_overlay(self) -> str:
        """Build SVG fragment for the active drag rectangle."""
        if self._drag_start is None or self._drag_current is None:
            return ""

        x1, y1, x2, y2 = self._normalized_rect(*self._drag_start, *self._drag_current)
        return (
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2 - x1):.2f}" '
            f'height="{(y2 - y1):.2f}" fill="none" stroke="#2563eb" '
            'stroke-width="2" stroke-dasharray="4 2" pointer-events="none" />'
        )

    def _append_viewport_layer_overlays(
        self, page: object, overlay_parts: list[str]
    ) -> None:
        """Render passive layer overlays for unified viewport mode."""
        if self.visible_layers.get("paragraphs", False):
            scale_x, scale_y = self._get_display_scale(page, tab_name="Paragraphs")
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            for paragraph in paragraphs:
                bbox = self._paragraph_bbox(paragraph, page)
                if bbox is None:
                    continue
                x1, y1, x2, y2 = bbox
                overlay_parts.append(
                    f'<rect x="{(x1 * scale_x):.2f}" y="{(y1 * scale_y):.2f}" '
                    f'width="{((x2 - x1) * scale_x):.2f}" '
                    f'height="{((y2 - y1) * scale_y):.2f}" fill="rgba(34,197,94,0.12)" '
                    'stroke="rgba(22,163,74,0.70)" stroke-width="2" style="mix-blend-mode:multiply" pointer-events="none" />'
                )

        if self.visible_layers.get("lines", False):
            scale_x, scale_y = self._get_display_scale(page, tab_name="Lines")
            for line in self._get_page_lines(page):
                bbox = self._line_bbox(line, page)
                if bbox is None:
                    continue
                x1, y1, x2, y2 = bbox
                overlay_parts.append(
                    f'<rect x="{(x1 * scale_x):.2f}" y="{(y1 * scale_y):.2f}" '
                    f'width="{((x2 - x1) * scale_x):.2f}" '
                    f'height="{((y2 - y1) * scale_y):.2f}" fill="rgba(236,72,153,0.12)" '
                    'stroke="rgba(236,72,153,0.70)" stroke-width="2" style="mix-blend-mode:multiply" pointer-events="none" />'
                )

        if self.visible_layers.get("words", False):
            scale_x, scale_y = self._get_display_scale(page, tab_name="Words")
            word_rects: list[tuple[float, float, float, float]] = []
            for line in self._get_page_lines(page):
                words = getattr(line, "words", None) or []
                for word in words:
                    bbox = self._word_bbox(word, page)
                    if bbox is None:
                        continue
                    x1, y1, x2, y2 = bbox
                    word_rects.append(
                        (
                            x1 * scale_x,
                            y1 * scale_y,
                            (x2 - x1) * scale_x,
                            (y2 - y1) * scale_y,
                        )
                    )

            if word_rects:
                dense_words = len(word_rects) > 1500
                word_fill = "none" if dense_words else "rgba(59,130,246,0.10)"
                word_style = "" if dense_words else ' style="mix-blend-mode:multiply"'
                overlay_parts.append(
                    f'<path d="{self._rects_to_path(word_rects)}" '
                    f'fill="{word_fill}" '
                    'stroke="rgba(59,130,246,0.60)" stroke-width="2" '
                    f'{word_style} pointer-events="none" />'
                )

    def _get_viewport_layer_overlay(self, page: object) -> str:
        """Return cached passive viewport layer SVG for current page/layer visibility."""
        cache_key = (
            page,
            bool(self.visible_layers.get("paragraphs", False)),
            bool(self.visible_layers.get("lines", False)),
            bool(self.visible_layers.get("words", False)),
        )
        if self._viewport_layer_overlay_cache_key == cache_key:
            return self._viewport_layer_overlay_cache

        parts: list[str] = []
        self._append_viewport_layer_overlays(page, parts)
        overlay = "".join(parts)
        self._viewport_layer_overlay_cache_key = cache_key
        self._viewport_layer_overlay_cache = overlay
        return overlay

    def _append_viewport_selected_overlays(self, overlay_parts: list[str]) -> None:
        """Render selected boxes for layers enabled in unified viewport mode."""
        if self.visible_layers.get("paragraphs", False):
            for x1, y1, x2, y2 in self._selected_paragraph_boxes:
                overlay_parts.append(
                    f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2 - x1):.2f}" '
                    f'height="{(y2 - y1):.2f}" fill="rgba(34,197,94,0.20)" '
                    'stroke="#166534" stroke-width="3" style="mix-blend-mode:multiply" pointer-events="none" />'
                )

        if self.visible_layers.get("lines", False):
            for x1, y1, x2, y2 in self._selected_line_boxes:
                overlay_parts.append(
                    f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2 - x1):.2f}" '
                    f'height="{(y2 - y1):.2f}" fill="rgba(236,72,153,0.20)" '
                    'stroke="#be185d" stroke-width="3" style="mix-blend-mode:multiply" pointer-events="none" />'
                )

        if self.visible_layers.get("words", False):
            for x1, y1, x2, y2 in self._selected_word_boxes:
                overlay_parts.append(
                    f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2 - x1):.2f}" '
                    f'height="{(y2 - y1):.2f}" fill="rgba(37,99,235,0.20)" '
                    'stroke="#1d4ed8" stroke-width="3" style="mix-blend-mode:multiply" pointer-events="none" />'
                )

    def _clear_drag_overlay(self, tab_name: str = "Words") -> None:
        """Remove drag rectangle overlay."""
        interactive_image = self._overlay_image(tab_name)
        if interactive_image is None:
            return
        try:
            interactive_image.content = ""
        except Exception:
            logger.debug("Failed to clear drag overlay", exc_info=True)
            self._notify_once(
                "image-tabs-drag-overlay-clear",
                "Failed to clear selection overlay",
                type_="warning",
            )

    def _clear_drag_state(self) -> None:
        """Clear in-progress drag state and remove dashed drag overlays."""
        self._drag_start = None
        self._drag_current = None
        self._drag_target_tab = None
        self._drag_remove_mode = False
        self._drag_add_mode = False
        self._word_rebox_mode = False
        self._word_add_mode = False
        if "Viewport" not in self.images:
            self._clear_drag_overlay(self._selection_mode_tab())
        self._render_selection_overlay(self._selection_mode_tab())

    def _apply_box_selection(self, tab_name: str = "Words") -> bool:
        """Apply box selection for the given interactive image tab."""
        if self._drag_start is None or self._drag_current is None:
            return False
        if tab_name == "Paragraphs":
            if self._on_paragraphs_selected is None:
                return False
        elif self._on_words_selected is None:
            return False

        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None
        if page is None:
            return False

        x1, y1, x2, y2 = self._normalized_rect(*self._drag_start, *self._drag_current)
        if tab_name == "Paragraphs":
            selected_in_box = self._select_paragraphs_in_rect(page, x1, y1, x2, y2)
            if self._drag_remove_mode:
                selected_paragraphs = set(self._selected_paragraph_indices)
                selected_paragraphs.difference_update(selected_in_box)
            elif self._drag_add_mode:
                selected_paragraphs = set(self._selected_paragraph_indices)
                selected_paragraphs.update(selected_in_box)
            else:
                selected_paragraphs = selected_in_box

            self.set_selected_paragraphs(selected_paragraphs)
            self._on_paragraphs_selected(selected_paragraphs)
            return True

        if tab_name == "Lines":
            selected_line_indices = self._select_lines_in_rect(page, x1, y1, x2, y2)
            current_line_indices = self._line_indices_from_selected_words()

            if self._drag_remove_mode:
                line_selection = set(current_line_indices)
                line_selection.difference_update(selected_line_indices)
            elif self._drag_add_mode:
                line_selection = set(current_line_indices)
                line_selection.update(selected_line_indices)
            else:
                line_selection = selected_line_indices

            selected = self._word_keys_for_lines(page, line_selection)
        else:
            selected_in_box = self._select_words_in_rect(page, x1, y1, x2, y2)

            if self._drag_remove_mode:
                selected = set(self._selected_word_indices)
                selected.difference_update(selected_in_box)
            elif self._drag_add_mode:
                selected = set(self._selected_word_indices)
                selected.update(selected_in_box)
            else:
                selected = selected_in_box

        self.set_selected_words(selected)
        self._on_words_selected(selected)
        return True

    def _select_paragraphs_in_rect(
        self, page: object, x1: float, y1: float, x2: float, y2: float
    ) -> set[int]:
        """Return paragraph indices for paragraphs intersecting a rectangle."""
        selection: set[int] = set()
        scale_x, scale_y = self._get_display_scale(page, tab_name="Paragraphs")
        paragraphs = list(getattr(page, "paragraphs", []) or [])
        for paragraph_index, paragraph in enumerate(paragraphs):
            bbox = self._paragraph_bbox(paragraph, page)
            if bbox is None:
                continue
            px1, py1, px2, py2 = bbox
            px1 *= scale_x
            px2 *= scale_x
            py1 *= scale_y
            py2 *= scale_y
            if self._rects_intersect((x1, y1, x2, y2), (px1, py1, px2, py2)):
                selection.add(paragraph_index)

        logger.debug("Box selection resolved %d paragraphs", len(selection))
        return selection

    def _select_words_in_rect(
        self, page: object, x1: float, y1: float, x2: float, y2: float
    ) -> set[tuple[int, int]]:
        """Return (line_index, word_index) tuples for words intersecting a rectangle."""
        selection: set[tuple[int, int]] = set()
        scale_x, scale_y = self._get_display_scale(page)
        lines = self._get_page_lines(page)
        for line_index, line in enumerate(lines):
            words = getattr(line, "words", None) or []
            for word_index, word in enumerate(words):
                bbox = self._word_bbox(word, page)
                if bbox is None:
                    continue
                wx1, wy1, wx2, wy2 = bbox
                wx1 *= scale_x
                wx2 *= scale_x
                wy1 *= scale_y
                wy2 *= scale_y
                if self._rects_intersect((x1, y1, x2, y2), (wx1, wy1, wx2, wy2)):
                    selection.add((line_index, word_index))

        logger.debug("Box selection resolved %d words", len(selection))
        return selection

    def _select_lines_in_rect(
        self, page: object, x1: float, y1: float, x2: float, y2: float
    ) -> set[int]:
        """Return line indices for lines intersecting a rectangle."""
        selection: set[int] = set()
        scale_x, scale_y = self._get_display_scale(page, tab_name="Lines")
        lines = self._get_page_lines(page)
        for line_index, line in enumerate(lines):
            bbox = self._line_bbox(line, page)
            if bbox is None:
                continue
            lx1, ly1, lx2, ly2 = bbox
            lx1 *= scale_x
            lx2 *= scale_x
            ly1 *= scale_y
            ly2 *= scale_y
            if self._rects_intersect((x1, y1, x2, y2), (lx1, ly1, lx2, ly2)):
                selection.add(line_index)

        logger.debug("Box selection resolved %d lines", len(selection))
        return selection

    def _word_bbox(
        self, word: object, page: object
    ) -> tuple[float, float, float, float] | None:
        """Extract pixel bbox for a word as (x1, y1, x2, y2)."""
        bbox = getattr(word, "bounding_box", None)
        if bbox is None:
            return None
        try:
            if bool(getattr(bbox, "is_normalized", False)):
                width = float(getattr(page, "width", 0) or 0)
                height = float(getattr(page, "height", 0) or 0)
                if width <= 0 or height <= 0:
                    base_image = getattr(page, "cv2_numpy_page_image", None)
                    if getattr(base_image, "shape", None) is not None:
                        height, width = base_image.shape[:2]
                if width > 0 and height > 0 and hasattr(bbox, "scale"):
                    bbox = bbox.scale(width, height)
            return (
                float(getattr(bbox, "minX")),
                float(getattr(bbox, "minY")),
                float(getattr(bbox, "maxX")),
                float(getattr(bbox, "maxY")),
            )
        except Exception:
            return None

    def _line_bbox(
        self, line: object, page: object
    ) -> tuple[float, float, float, float] | None:
        """Extract pixel bbox for a line as (x1, y1, x2, y2)."""
        bbox = getattr(line, "bounding_box", None)
        if bbox is None:
            return None
        try:
            if bool(getattr(bbox, "is_normalized", False)):
                width = float(getattr(page, "width", 0) or 0)
                height = float(getattr(page, "height", 0) or 0)
                if width <= 0 or height <= 0:
                    base_image = getattr(page, "cv2_numpy_page_image", None)
                    if getattr(base_image, "shape", None) is not None:
                        height, width = base_image.shape[:2]
                if width > 0 and height > 0 and hasattr(bbox, "scale"):
                    bbox = bbox.scale(width, height)
            return (
                float(getattr(bbox, "minX")),
                float(getattr(bbox, "minY")),
                float(getattr(bbox, "maxX")),
                float(getattr(bbox, "maxY")),
            )
        except Exception:
            return None

    def _paragraph_bbox(
        self, paragraph: object, page: object
    ) -> tuple[float, float, float, float] | None:
        """Extract pixel bbox for a paragraph as (x1, y1, x2, y2)."""
        bbox = getattr(paragraph, "bounding_box", None)
        if bbox is None:
            return None
        try:
            if bool(getattr(bbox, "is_normalized", False)):
                width = float(getattr(page, "width", 0) or 0)
                height = float(getattr(page, "height", 0) or 0)
                if width <= 0 or height <= 0:
                    base_image = getattr(page, "cv2_numpy_page_image", None)
                    if getattr(base_image, "shape", None) is not None:
                        height, width = base_image.shape[:2]
                if width > 0 and height > 0 and hasattr(bbox, "scale"):
                    bbox = bbox.scale(width, height)
            return (
                float(getattr(bbox, "minX")),
                float(getattr(bbox, "minY")),
                float(getattr(bbox, "maxX")),
                float(getattr(bbox, "maxY")),
            )
        except Exception:
            return None

    def _get_page_lines(self, page: object) -> list[object]:
        """Return page lines from `lines` or line-like blocks."""
        lines = getattr(page, "lines", None)
        if lines:
            return list(lines)

        blocks = getattr(page, "blocks", None) or []
        line_blocks = [block for block in blocks if getattr(block, "words", None)]
        return line_blocks

    def set_selected_words(self, selection: set[tuple[int, int]]) -> None:
        """Set selected words externally (e.g. from right-panel checkboxes)."""
        self._selected_word_indices = set(selection)
        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None

        self._selected_word_boxes = []
        self._selected_line_boxes = []
        if page is not None:
            word_scale_x, word_scale_y = self._get_display_scale(page, tab_name="Words")
            line_scale_x, line_scale_y = self._get_display_scale(page, tab_name="Lines")
            lines = self._get_page_lines(page)
            selected_line_indices = self._line_indices_from_selected_words()

            for line_index in selected_line_indices:
                if not (0 <= line_index < len(lines)):
                    continue
                line_bbox = self._line_bbox(lines[line_index], page)
                if line_bbox is not None:
                    lx1, ly1, lx2, ly2 = line_bbox
                    self._selected_line_boxes.append(
                        (
                            lx1 * line_scale_x,
                            ly1 * line_scale_y,
                            lx2 * line_scale_x,
                            ly2 * line_scale_y,
                        )
                    )

            for line_index, word_index in self._selected_word_indices:
                if not (0 <= line_index < len(lines)):
                    continue
                words = getattr(lines[line_index], "words", None) or []
                if not (0 <= word_index < len(words)):
                    continue
                bbox = self._word_bbox(words[word_index], page)
                if bbox is not None:
                    x1, y1, x2, y2 = bbox
                    self._selected_word_boxes.append(
                        (
                            x1 * word_scale_x,
                            y1 * word_scale_y,
                            x2 * word_scale_x,
                            y2 * word_scale_y,
                        )
                    )

        if self._suspend_overlay_render:
            return

        if "Viewport" in self.images:
            self._render_selection_overlay(self._selection_mode_tab())
        else:
            self._render_selection_overlay("Words")
            self._render_selection_overlay("Lines")

    def set_selected_paragraphs(self, selection: set[int]) -> None:
        """Set selected paragraphs externally (e.g. from right-panel checkboxes)."""
        self._selected_paragraph_indices = set(selection)
        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None

        self._selected_paragraph_boxes = []
        if page is not None:
            paragraph_scale_x, paragraph_scale_y = self._get_display_scale(
                page, tab_name="Paragraphs"
            )
            paragraphs = list(getattr(page, "paragraphs", []) or [])
            for paragraph_index in self._selected_paragraph_indices:
                if not (0 <= paragraph_index < len(paragraphs)):
                    continue
                bbox = self._paragraph_bbox(paragraphs[paragraph_index], page)
                if bbox is not None:
                    x1, y1, x2, y2 = bbox
                    self._selected_paragraph_boxes.append(
                        (
                            x1 * paragraph_scale_x,
                            y1 * paragraph_scale_y,
                            x2 * paragraph_scale_x,
                            y2 * paragraph_scale_y,
                        )
                    )

        if self._suspend_overlay_render:
            return

        if "Viewport" in self.images:
            self._render_selection_overlay(self._selection_mode_tab())
        else:
            self._render_selection_overlay("Paragraphs")

    def _get_display_scale(
        self, page: object, tab_name: str = "Words"
    ) -> tuple[float, float]:
        """Return scale from original image coordinates to encoded display coordinates."""
        source_image = self._get_source_image_for_tab(page, tab_name)
        if getattr(source_image, "shape", None) is None:
            return 1.0, 1.0

        source_height, source_width = source_image.shape[:2]
        display_width, display_height = self._compute_encoded_dimensions(
            source_width, source_height
        )
        return display_width / float(source_width), display_height / float(
            source_height
        )

    def _compute_encoded_dimensions(
        self, source_width: int, source_height: int
    ) -> tuple[int, int]:
        """Mirror page image encoder resizing (integer math) for exact display size."""
        max_dimension = 1200
        if source_width > max_dimension or source_height > max_dimension:
            if source_width > source_height:
                return max_dimension, int(source_height * max_dimension / source_width)
            return int(source_width * max_dimension / source_height), max_dimension
        return source_width, source_height

    def _get_source_image_for_tab(self, page: object, tab_name: str) -> object:
        """Return source image used for viewport geometry calculations."""
        _ = tab_name
        return getattr(page, "cv2_numpy_page_image", None)

    def _get_display_dimensions(
        self, page: object, tab_name: str = "Words"
    ) -> tuple[float, float] | None:
        """Return encoded display dimensions for a given interactive image tab."""
        source_image = self._get_source_image_for_tab(page, tab_name)
        if getattr(source_image, "shape", None) is None:
            return None

        source_height, source_width = source_image.shape[:2]
        if source_width <= 0 or source_height <= 0:
            return None

        display_width, display_height = self._compute_encoded_dimensions(
            source_width, source_height
        )
        return float(display_width), float(display_height)

    def _update_interactive_image_geometry(self, tab_name: str) -> None:
        """Keep interactive image geometry aligned with source image."""
        interactive_image = self._overlay_image(tab_name)
        if interactive_image is None:
            return

        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None
        if page is None:
            return

        display_dimensions = self._get_display_dimensions(page, tab_name=tab_name)
        if display_dimensions is None:
            return

        display_width, display_height = display_dimensions
        if display_width <= 0 or display_height <= 0:
            return

        try:
            interactive_image._props["size"] = (display_width, display_height)
        except Exception:
            logger.debug(
                "Failed to update interactive image geometry for %s",
                tab_name,
                exc_info=True,
            )
            self._notify_once(
                f"image-tabs-geometry-{tab_name.lower()}",
                "Failed to update image geometry",
                type_="warning",
            )

    def _line_indices_from_selected_words(self) -> set[int]:
        """Return currently selected line indices derived from selected words."""
        return {line_index for line_index, _ in self._selected_word_indices}

    def _word_keys_for_lines(
        self, page: object, line_indices: set[int]
    ) -> set[tuple[int, int]]:
        """Expand selected line indices to all word keys in those lines."""
        selection: set[tuple[int, int]] = set()
        lines = self._get_page_lines(page)
        for line_index in line_indices:
            if not (0 <= line_index < len(lines)):
                continue
            words = getattr(lines[line_index], "words", None) or []
            for word_index, _ in enumerate(words):
                selection.add((line_index, word_index))
        return selection

    def _rects_intersect(
        self,
        rect_a: tuple[float, float, float, float],
        rect_b: tuple[float, float, float, float],
    ) -> bool:
        """Return True if two rectangles intersect."""
        ax1, ay1, ax2, ay2 = rect_a
        bx1, by1, bx2, by2 = rect_b
        return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)

    def _normalized_rect(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> tuple[float, float, float, float]:
        """Normalize rectangle coordinates so min corner comes first."""
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def _rects_to_path(self, rects: list[tuple[float, float, float, float]]) -> str:
        """Encode rectangles as a single SVG path to reduce DOM node count."""
        commands: list[str] = []
        for x, y, width, height in rects:
            if width <= 0.0 or height <= 0.0:
                continue
            commands.append(f"M{x:.2f} {y:.2f}h{width:.2f}v{height:.2f}h{-width:.2f}Z")
        return " ".join(commands)

    def _on_images_updated(self, image_dict: dict[str, str]):
        """Callback invoked when viewmodel has new images ready.

        Updates all image sources directly in one operation to avoid
        multiple websocket updates that could cause disconnection.

        Args:
            image_dict: Dictionary mapping property names to image data URLs
        """
        logger.debug("_on_images_updated called with %d images", len(image_dict))

        source = image_dict.get("original_image_source")
        if not source:
            return

        img_element = self.images.get("Viewport")
        if img_element is None:
            return

        if hasattr(img_element, "set_source"):
            img_element.set_source(source)
        else:
            img_element.source = source

        self._viewport_layer_overlay_cache_key = None
        self._update_interactive_image_geometry(self._selection_mode_tab())
        self._suspend_overlay_render = True
        try:
            self.set_selected_words(self._selected_word_indices)
            self.set_selected_paragraphs(self._selected_paragraph_indices)
        finally:
            self._suspend_overlay_render = False
        self._render_selection_overlay(self._selection_mode_tab())
        logger.debug("Image update complete for unified viewport")
