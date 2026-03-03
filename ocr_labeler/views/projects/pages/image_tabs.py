import logging
from typing import Callable

from nicegui import events, ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel

logger = logging.getLogger(__name__)


class ImageTabs:
    """Left side image tabs showing progressively processed page imagery."""

    def __init__(
        self,
        page_state_view_model: PageStateViewModel,
        on_words_selected: Callable[[set[tuple[int, int]]], None] | None = None,
        on_paragraphs_selected: Callable[[set[int]], None] | None = None,
    ):
        self._tab_ids = ["Original", "Paragraphs", "Lines", "Words", "Mismatches"]
        logger.debug("Initializing ImageTabs with tab IDs: %s", self._tab_ids)
        self.images: dict[str, ui.image] = {}
        self.page_state_view_model = page_state_view_model
        self._on_words_selected = on_words_selected
        self._on_paragraphs_selected = on_paragraphs_selected
        self._drag_start: tuple[float, float] | None = None
        self._drag_current: tuple[float, float] | None = None
        self._drag_target_tab: str | None = None
        self._drag_remove_mode = False
        self._drag_add_mode = False
        self._selected_word_indices: set[tuple[int, int]] = set()
        self._selected_paragraph_indices: set[int] = set()
        self._selected_word_boxes: list[tuple[float, float, float, float]] = []
        self._selected_line_boxes: list[tuple[float, float, float, float]] = []
        self._selected_paragraph_boxes: list[tuple[float, float, float, float]] = []
        # Register callback for direct image updates (bypasses data binding)
        self.page_state_view_model.set_image_update_callback(self._on_images_updated)
        logger.debug("ImageTabs initialization complete with callback registered")

    def build(self):
        logger.debug("Building ImageTabs UI components")
        # Root column uses Quasar full-height/width utility classes.
        with ui.column().classes("full-width full-height") as col:
            with ui.tabs().props("dense no-caps shrink") as tabs:
                for name in self._tab_ids:
                    ui.tab(name).props("ripple")
                tabs.on("update:model-value", lambda _e: self._clear_drag_state())
            # Tab panels fill available space; each panel centers its image.
            with ui.tab_panels(tabs, value="Original").classes(
                "full-width full-height"
            ):
                for name in self._tab_ids:
                    with ui.tab_panel(name).classes("column full-width full-height"):
                        with ui.column().classes(
                            "items-center justify-center full-width full-height"
                        ):
                            if name == "Words":
                                img = (
                                    ui.interactive_image(
                                        events=["mousedown", "mousemove", "mouseup"],
                                        on_mouse=self._handle_words_mouse,
                                        sanitize=False,
                                    )
                                    .classes("self-center full-height")
                                    .style(
                                        "height: 100%; width: auto; max-width: 100%;"
                                    )
                                )
                            elif name == "Lines":
                                img = (
                                    ui.interactive_image(
                                        events=["mousedown", "mousemove", "mouseup"],
                                        on_mouse=self._handle_lines_mouse,
                                        sanitize=False,
                                    )
                                    .classes("self-center full-height")
                                    .style(
                                        "height: 100%; width: auto; max-width: 100%;"
                                    )
                                )
                            elif name == "Paragraphs":
                                img = (
                                    ui.interactive_image(
                                        events=["mousedown", "mousemove", "mouseup"],
                                        on_mouse=self._handle_paragraphs_mouse,
                                        sanitize=False,
                                    )
                                    .classes("self-center full-height")
                                    .style(
                                        "height: 100%; width: auto; max-width: 100%;"
                                    )
                                )
                            else:
                                img = (
                                    ui.image()
                                    .props(
                                        "fit=contain"
                                    )  # rely on intrinsic container sizing
                                    .classes("full-width full-height")
                                )
                            # Store image reference (no binding - using callback instead)
                            self.images[name] = img
        self.container = col
        logger.debug(
            "ImageTabs UI build complete with %d image components", len(self.images)
        )
        return col

    def _handle_words_mouse(self, event: events.MouseEventArguments) -> None:
        """Handle drag selection gestures on the Words image tab."""
        self._handle_drag_mouse("Words", event)

    def _handle_lines_mouse(self, event: events.MouseEventArguments) -> None:
        """Handle drag selection gestures on the Lines image tab."""
        self._handle_drag_mouse("Lines", event)

    def _handle_paragraphs_mouse(self, event: events.MouseEventArguments) -> None:
        """Handle drag selection gestures on the Paragraphs image tab."""
        self._handle_drag_mouse("Paragraphs", event)

    def _handle_drag_mouse(
        self, tab_name: str, event: events.MouseEventArguments
    ) -> None:
        """Handle drag selection gestures on an interactive image tab."""
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
            self._apply_box_selection(tab_name)
            self._drag_start = None
            self._drag_current = None
            self._drag_target_tab = None
            self._drag_remove_mode = False
            self._drag_add_mode = False
            self._render_selection_overlay(tab_name)

    def _render_drag_overlay(self, tab_name: str) -> None:
        """Render selection overlay while drag is in progress."""
        self._render_selection_overlay(tab_name)

    def _render_selection_overlay(self, tab_name: str = "Words") -> None:
        """Render selected boxes and optional drag rectangle overlay for a tab."""
        interactive_image = self.images.get(tab_name)
        if interactive_image is None:
            return
        overlay_parts: list[str] = []

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

        if self._drag_start is not None and self._drag_current is not None:
            x1, y1, x2, y2 = self._normalized_rect(
                *self._drag_start, *self._drag_current
            )
            overlay_parts.append(
                f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{(x2 - x1):.2f}" '
                f'height="{(y2 - y1):.2f}" fill="none" stroke="#2563eb" '
                'stroke-width="2" stroke-dasharray="4 2" pointer-events="none" />'
            )

        try:
            interactive_image.content = "".join(overlay_parts)
        except Exception:
            logger.debug("Failed to render drag overlay", exc_info=True)

    def _clear_drag_overlay(self, tab_name: str = "Words") -> None:
        """Remove drag rectangle overlay."""
        interactive_image = self.images.get(tab_name)
        if interactive_image is None:
            return
        try:
            interactive_image.content = ""
        except Exception:
            logger.debug("Failed to clear drag overlay", exc_info=True)

    def _clear_drag_state(self) -> None:
        """Clear in-progress drag state and remove dashed drag overlays."""
        self._drag_start = None
        self._drag_current = None
        self._drag_target_tab = None
        self._drag_remove_mode = False
        self._drag_add_mode = False
        self._clear_drag_overlay("Words")
        self._clear_drag_overlay("Lines")
        self._clear_drag_overlay("Paragraphs")
        self._render_selection_overlay("Words")
        self._render_selection_overlay("Lines")
        self._render_selection_overlay("Paragraphs")

    def _apply_box_selection(self, tab_name: str = "Words") -> None:
        """Apply box selection for the given interactive image tab."""
        if self._drag_start is None or self._drag_current is None:
            return
        if tab_name == "Paragraphs":
            if self._on_paragraphs_selected is None:
                return
        elif self._on_words_selected is None:
            return

        page_state = getattr(self.page_state_view_model, "_page_state", None)
        page = getattr(page_state, "current_page", None) if page_state else None
        if page is None:
            return

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
            return

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
        """Return tab-specific source image used for encoded display."""
        if tab_name == "Lines":
            source_image = getattr(page, "cv2_numpy_page_image_line_with_bboxes", None)
        elif tab_name == "Paragraphs":
            source_image = getattr(
                page,
                "cv2_numpy_page_image_paragraph_with_bboxes",
                None,
            )
        elif tab_name == "Words":
            source_image = getattr(page, "cv2_numpy_page_image_word_with_bboxes", None)
        else:
            source_image = None

        if getattr(source_image, "shape", None) is None:
            source_image = getattr(page, "cv2_numpy_page_image", None)
        return source_image

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
        interactive_image = self.images.get(tab_name)
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

    def _on_images_updated(self, image_dict: dict[str, str]):
        """Callback invoked when viewmodel has new images ready.

        Updates all image sources directly in one operation to avoid
        multiple websocket updates that could cause disconnection.

        Args:
            image_dict: Dictionary mapping property names to image data URLs
        """
        logger.debug("_on_images_updated called with %d images", len(image_dict))

        prop_to_tab_map = {
            "original_image_source": "Original",
            "paragraphs_image_source": "Paragraphs",
            "lines_image_source": "Lines",
            "words_image_source": "Words",
            "mismatches_image_source": "Mismatches",
        }

        # Deduplicate identical images to minimize websocket traffic
        # For blank pages, all overlay images are often identical
        unique_images = {}
        image_to_tabs = {}

        for prop_name, image_data in image_dict.items():
            tab_name = prop_to_tab_map.get(prop_name)
            if tab_name and tab_name in self.images:
                if image_data not in image_to_tabs:
                    image_to_tabs[image_data] = []
                    unique_images[image_data] = tab_name
                image_to_tabs[image_data].append(tab_name)

        logger.info(
            "Dedup: %d unique images for %d tabs",
            len(unique_images),
            len(image_dict),
        )

        # Track which images actually changed
        updates_made = 0

        # Update images - for duplicates, set all tabs to the same source
        for image_data, tabs in image_to_tabs.items():
            for tab_name in tabs:
                img_element = self.images[tab_name]
                # Update source robustly for both image and interactive_image
                if hasattr(img_element, "set_source"):
                    img_element.set_source(image_data)
                else:
                    img_element.source = image_data
                updates_made += 1
                logger.debug(
                    "Updated %s image (length: %d, shared with %d tabs)",
                    tab_name,
                    len(image_data) if image_data else 0,
                    len(tabs),
                )

                self._update_interactive_image_geometry("Words")
                self._update_interactive_image_geometry("Lines")
                self._update_interactive_image_geometry("Paragraphs")
        self.set_selected_words(self._selected_word_indices)
        self.set_selected_paragraphs(self._selected_paragraph_indices)
        logger.debug("Image update complete: %d images updated", updates_made)

    def _bind_image_source(self, img: ui.image, tab_name: str):
        """DEPRECATED: Data binding removed to prevent websocket issues."""
        prop_map = {
            "Original": "original_image_source",
            "Paragraphs": "paragraphs_image_source",
            "Lines": "lines_image_source",
            "Words": "words_image_source",
            "Mismatches": "mismatches_image_source",
        }

        prop_name = prop_map.get(tab_name)
        if prop_name:
            logger.warning(
                "_bind_image_source called but binding is deprecated; using callback instead"
            )
        else:
            logger.warning(f"No property mapping found for tab: {tab_name}")

    def update_images(self):
        """Manually refresh images from viewmodel (for backward compatibility).

        Note: This is now automatic via callback, but kept for compatibility.
        """
        logger.debug("update_images called - images update automatically via callback")
