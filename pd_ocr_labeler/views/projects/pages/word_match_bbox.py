"""Bounding box editing and image slicing for the word match view."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Callable

from nicegui import events, ui

if TYPE_CHECKING:
    from ....models.line_match_model import LineMatch
    from .word_match import WordMatchView

logger = logging.getLogger(__name__)

WordKey = tuple[int, int]
ClickEvent = events.ClickEventArguments | None
ReboxRequestCallback = Callable[[int, int], None]


class WordMatchBbox:
    """Manages bounding box editing, nudging, reboxing, and word image slicing."""

    _WORD_SLICE_CSS_REGISTERED = False

    def __init__(self, view: WordMatchView) -> None:
        self._view = view
        self._bbox_editor_open_keys: set[WordKey] = set()
        self._bbox_pending_deltas: dict[WordKey, tuple[float, float, float, float]] = {}
        self._bbox_nudge_step_px: int = 5
        self._pending_rebox_word_key: WordKey | None = None
        self._rebox_request_callback: ReboxRequestCallback | None = None
        self._add_word_request_callback: Callable[[], None] | None = None
        self._original_image_source_provider: Callable[[], str] | None = None
        self._last_word_view_source: str = ""

    # ------------------------------------------------------------------
    # Word image slice helpers
    # ------------------------------------------------------------------

    def get_word_image_slice(
        self,
        word_match,
        *,
        line_index: int,
        word_index: int,
        bbox_preview_deltas: tuple[float, float, float, float] | None = None,
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
            if not self._view.view_model.line_matches:
                logger.debug("No line matches in view model, cannot get word image")
                return None

            # Find the line match that contains this word match
            # Use identity comparison instead of equality to avoid numpy array issues
            line_match = None
            for lm in self._view.view_model.line_matches:
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
            preview_bbox = self.preview_bbox_for_word(
                word_match,
                page_image,
                line_index=line_index,
                word_index=word_index,
                bbox_preview_deltas=bbox_preview_deltas,
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

            encoded_width, encoded_height = self.compute_encoded_dimensions(
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
            logger.debug("Error creating word image: %s", e)
            return None

    def preview_bbox_for_word(
        self,
        word_match,
        page_image,
        *,
        line_index: int,
        word_index: int,
        bbox_preview_deltas: tuple[float, float, float, float] | None = None,
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
            bbox_preview_deltas
            if bbox_preview_deltas is not None
            else (0.0, 0.0, 0.0, 0.0)
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

    def compute_refine_preview_deltas(
        self,
        line_index: int,
        word_index: int,
        *,
        expand: bool,
        pending_deltas: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    ) -> tuple[float, float, float, float] | None:
        """Compute bbox deltas that a refine operation would produce, without applying.

        When *pending_deltas* are supplied (e.g. from a prior crop), the bbox is
        first adjusted by those deltas so that ``refine`` sees the cropped image
        region.  The returned deltas are expressed relative to the **original**
        bbox so they fully replace ``pending_deltas``.

        Returns (left_delta, right_delta, top_delta, bottom_delta) in pixel space,
        using the same sign convention as ``preview_bbox_for_word``:
        positive left_delta = expand left, positive right_delta = expand right, etc.
        """
        line_match = self._view._line_match_by_index(line_index)
        if line_match is None:
            return None

        page_image = getattr(line_match, "page_image", None)
        if page_image is None:
            return None

        shape = getattr(page_image, "shape", None)
        if shape is None or len(shape) < 2:
            return None
        page_height = int(shape[0])
        page_width = int(shape[1])
        if page_width <= 0 or page_height <= 0:
            return None

        word_match = self._view._line_word_match_by_ocr_index(line_index, word_index)
        if word_match is None:
            return None
        word_object = getattr(word_match, "word_object", None)
        if word_object is None:
            return None
        bbox = getattr(word_object, "bounding_box", None)
        if bbox is None:
            return None

        # Resolve original bbox pixel coords.
        is_normalized = bool(getattr(bbox, "is_normalized", False))
        if is_normalized:
            old_x1 = float(getattr(bbox, "minX", 0.0) or 0.0) * page_width
            old_y1 = float(getattr(bbox, "minY", 0.0) or 0.0) * page_height
            old_x2 = float(getattr(bbox, "maxX", 0.0) or 0.0) * page_width
            old_y2 = float(getattr(bbox, "maxY", 0.0) or 0.0) * page_height
        else:
            old_x1 = float(getattr(bbox, "minX", 0.0) or 0.0)
            old_y1 = float(getattr(bbox, "minY", 0.0) or 0.0)
            old_x2 = float(getattr(bbox, "maxX", 0.0) or 0.0)
            old_y2 = float(getattr(bbox, "maxY", 0.0) or 0.0)

        # Apply pending deltas to get the effective (e.g. cropped) bbox.
        pd_left, pd_right, pd_top, pd_bottom = pending_deltas
        eff_x1 = old_x1 - pd_left
        eff_y1 = old_y1 - pd_top
        eff_x2 = old_x2 + pd_right
        eff_y2 = old_y2 + pd_bottom

        # Build a temporary BoundingBox from the effective coords so refine
        # operates on the cropped region.
        bbox_from_dict = getattr(type(bbox), "from_dict", None)
        if bbox_from_dict is None:
            return None

        has_pending = (pd_left, pd_right, pd_top, pd_bottom) != (0.0, 0.0, 0.0, 0.0)
        if has_pending:
            # Clamp to image bounds and round to integer pixel coordinates so
            # that downstream refine routines (which slice the page image with
            # these values) get integer indices.  Without rounding, deltas
            # derived from normalized bboxes can yield float coords like
            # ``60.0000000000001`` and trigger ``TypeError: slice indices must
            # be integers`` inside ``BoundingBox._extract_roi``, which would
            # otherwise be swallowed and surface as
            # "Could not compute refine preview".
            eff_x1_i = max(0, min(int(round(eff_x1)), page_width - 1))
            eff_y1_i = max(0, min(int(round(eff_y1)), page_height - 1))
            eff_x2_i = max(eff_x1_i + 1, min(int(round(eff_x2)), page_width))
            eff_y2_i = max(eff_y1_i + 1, min(int(round(eff_y2)), page_height))
            try:
                eff_bbox = bbox_from_dict(
                    {
                        "top_left": {"x": eff_x1_i, "y": eff_y1_i},
                        "bottom_right": {"x": eff_x2_i, "y": eff_y2_i},
                        "is_normalized": False,
                    }
                )
            except Exception:
                return None
            refine_fn = getattr(eff_bbox, "refine", None)
        else:
            refine_fn = getattr(bbox, "refine", None)

        if not callable(refine_fn):
            return None

        try:
            padding_px = 0 if expand else 1
            refined_bbox = refine_fn(
                page_image,
                padding_px=padding_px,
                expand_beyond_original=expand,
            )
        except Exception:
            return None

        if refined_bbox is None:
            return None

        # Read refined coords in pixel space.
        ref_normalized = bool(getattr(refined_bbox, "is_normalized", False))
        if ref_normalized:
            new_x1 = float(getattr(refined_bbox, "minX", 0.0) or 0.0) * page_width
            new_y1 = float(getattr(refined_bbox, "minY", 0.0) or 0.0) * page_height
            new_x2 = float(getattr(refined_bbox, "maxX", 0.0) or 0.0) * page_width
            new_y2 = float(getattr(refined_bbox, "maxY", 0.0) or 0.0) * page_height
        else:
            new_x1 = float(getattr(refined_bbox, "minX", 0.0) or 0.0)
            new_y1 = float(getattr(refined_bbox, "minY", 0.0) or 0.0)
            new_x2 = float(getattr(refined_bbox, "maxX", 0.0) or 0.0)
            new_y2 = float(getattr(refined_bbox, "maxY", 0.0) or 0.0)

        # Deltas relative to the *original* bbox so they fully replace pending.
        left_delta = old_x1 - new_x1
        right_delta = new_x2 - old_x2
        top_delta = old_y1 - new_y1
        bottom_delta = new_y2 - old_y2

        return left_delta, right_delta, top_delta, bottom_delta

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

    def compute_encoded_dimensions(
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

    def ensure_word_slice_css_registered(self) -> None:
        """Inject shared CSS for word-slice interactive image rendering once."""
        if WordMatchBbox._WORD_SLICE_CSS_REGISTERED:
            return

        ui.add_head_html(
            """
            <style>
            .word-slice-image {
                overflow: hidden;
                background-color: transparent;
                cursor: col-resize;
            }
            .word-slice-image img {
                opacity: 0 !important;
            }
            .copy-icon-flip .q-icon {
                transform: scaleX(-1);
            }
            </style>
            """
        )
        WordMatchBbox._WORD_SLICE_CSS_REGISTERED = True

    def refresh_word_slice_source(self) -> None:
        """Publish original image source once on the lines container as a CSS variable."""
        if self._view.lines_container is None:
            return

        source = self._get_original_image_source()
        if not source:
            self._view.lines_container.style("--wm-page-src: none;")
            return

        safe_source = source.replace("\\", "\\\\").replace("'", "\\'")
        self._view.lines_container.style(f"--wm-page-src: url('{safe_source}');")

    def on_image_sources_updated(self, image_dict: dict[str, str]) -> None:
        """React to state image updates and rerender if word-view source changed."""
        source = str(image_dict.get("word_view_original_image_source", "") or "")
        if source == self._last_word_view_source:
            return

        self._last_word_view_source = source
        if not source:
            return
        if not self._view._has_active_ui_context(self._view.lines_container):
            return

        self._view.renderer._last_display_signature = None
        self._view.renderer.update_lines_display()

        # Keep an open word-edit dialog in sync with the latest page image.
        dialog_key = self._view.renderer._word_dialog_refresh_key
        if dialog_key is None:
            return
        try:
            line_index, word_index = dialog_key
        except Exception:
            return
        self._view.renderer.refresh_open_word_dialog_for(line_index, word_index)

    # ------------------------------------------------------------------
    # Rebox / start-rebox
    # ------------------------------------------------------------------

    def set_rebox_request_callback(
        self,
        callback: ReboxRequestCallback | None,
    ) -> None:
        """Register callback invoked when user starts a word rebox request."""
        self._rebox_request_callback = callback

    def set_add_word_request_callback(
        self,
        callback: Callable[[], None] | None,
    ) -> None:
        """Register callback invoked when user requests to start an add-word draw."""
        self._add_word_request_callback = callback

    def handle_start_rebox_word(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Start rebox mode for a selected word."""
        if self._view.rebox_word_callback is None:
            self._view._safe_notify(
                "Rebox word function not available", type_="warning"
            )
            return
        if word_index < 0:
            self._view._safe_notify("Select a valid OCR word to rebox", type_="warning")
            return

        self._pending_rebox_word_key = (line_index, word_index)
        if self._rebox_request_callback is not None:
            try:
                self._rebox_request_callback(line_index, word_index)
            except Exception:
                logger.debug("Rebox request callback failed", exc_info=True)
        self._view._safe_notify(
            (
                f"Rebox word {word_index + 1} on line {line_index + 1}: "
                "draw a new rectangle on the Words image"
            ),
            type_="info",
        )

    def apply_rebox_bbox(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Apply a drawn bbox to the currently pending rebox word target."""
        if self._view.rebox_word_callback is None:
            self._view._safe_notify(
                "Rebox word function not available", type_="warning"
            )
            return

        target_key = self._pending_rebox_word_key
        if target_key is None:
            self._view._safe_notify("No active word rebox request", type_="warning")
            return

        line_index, word_index = target_key
        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()

        try:
            success = self._view.rebox_word_callback(
                line_index,
                word_index,
                x1,
                y1,
                x2,
                y2,
            )
            if success:
                self._pending_rebox_word_key = None
                self._view.renderer.rerender_word_column(line_index, word_index)
                self._view.renderer.refresh_open_word_dialog_for(line_index, word_index)
                self._view._safe_notify(
                    f"Reboxed word {word_index + 1} on line {line_index + 1}",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify("Failed to rebox word", type_="warning")
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error reboxing word (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(f"Error reboxing word: {e}", type_="negative")

    # ------------------------------------------------------------------
    # Add-word
    # ------------------------------------------------------------------

    def handle_start_add_word(self, _event=None) -> None:
        """Enter add-word draw mode: user will draw a bbox on the image."""
        if self._view.add_word_callback is None:
            self._view._safe_notify("Add-word function not available", type_="warning")
            return
        if self._add_word_request_callback is not None:
            try:
                self._add_word_request_callback()
            except Exception:
                logger.debug("Add-word request callback failed", exc_info=True)
        self._view._safe_notify(
            "Add word: draw a rectangle around the new word on the Words image",
            type_="info",
        )

    def apply_add_word_bbox(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Apply a drawn bbox as a new word insertion."""
        if self._view.add_word_callback is None:
            self._view._safe_notify("Add-word function not available", type_="warning")
            return
        try:
            success = self._view.add_word_callback(x1, y1, x2, y2)
            if success:
                self._view._safe_notify("Word added", type_="positive")
            else:
                self._view._safe_notify("Failed to add word", type_="warning")
        except Exception as e:
            logger.exception("Error applying add-word bbox: %s", e)
            self._view._safe_notify(f"Error adding word: {e}", type_="negative")

    # ------------------------------------------------------------------
    # Fine-tune / nudge
    # ------------------------------------------------------------------

    def toggle_bbox_fine_tune(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Toggle fine-tune controls for a single word bbox."""
        if self._view.nudge_word_bbox_callback is None:
            self._view._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word bbox to edit", type_="warning"
            )
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
            self._view.renderer.rerender_word_column(line_index, word_index)
        except Exception as e:
            logger.exception("Error toggling bbox fine-tune controls for key=%s", key)
            self._view._safe_notify(
                f"Error opening fine-tune controls: {e}", type_="negative"
            )
            raise

    def set_bbox_nudge_step(self, value: object) -> None:
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
                self._view.renderer.rerender_word_column(line_index, word_index)
        except Exception as e:
            logger.exception("Error updating bbox nudge step from value=%s", value)
            self._view._safe_notify(f"Error updating nudge step: {e}", type_="negative")
            raise

    def handle_nudge_single_word_bbox(
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
        if self._view.nudge_word_bbox_callback is None:
            self._view._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word bbox to edit", type_="warning"
            )
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
            self._view.renderer.rerender_word_column(line_index, word_index)
        except Exception as e:
            logger.exception(
                "Error accumulating nudge for word bbox (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(
                f"Error updating pending bbox edit: {e}", type_="negative"
            )
            raise

    def reset_pending_single_word_bbox_nudge(
        self,
        line_index: int,
        word_index: int,
        _event: ClickEvent = None,
    ) -> None:
        """Reset pending bbox deltas for a single word."""
        key = (line_index, word_index)
        self._bbox_pending_deltas.pop(key, None)
        self._view.renderer.rerender_word_column(line_index, word_index)

    def apply_pending_single_word_bbox_nudge(
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
        if self._view.nudge_word_bbox_callback is None:
            self._view._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word bbox to edit", type_="warning"
            )
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
            self._view._safe_notify("No pending bbox edits to apply", type_="warning")
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()

        try:
            success = self._view.nudge_word_bbox_callback(
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
                self._view.renderer.rerender_word_column(line_index, word_index)
                self._view.renderer.refresh_open_word_dialog_for(line_index, word_index)
                if refine_after:
                    self._view._safe_notify(
                        "Applied bbox fine-tune edits and refined",
                        type_="positive",
                    )
                else:
                    self._view._safe_notify(
                        "Applied bbox fine-tune edits", type_="positive"
                    )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify("Failed to apply bbox edits", type_="warning")
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error applying pending bbox nudge (%s, %s): %s",
                line_index,
                word_index,
                e,
            )
            self._view._safe_notify(f"Error applying bbox edits: {e}", type_="negative")
            raise

    # ------------------------------------------------------------------
    # Crop word to marker
    # ------------------------------------------------------------------

    def handle_crop_word_to_marker(
        self,
        line_index: int,
        word_index: int,
        direction: str,
        _event: ClickEvent = None,
    ) -> None:
        """Trim current word bbox on the named side using marker-based fraction."""
        if self._view.nudge_word_bbox_callback is None:
            self._view._safe_notify("Edit bbox function not available", type_="warning")
            return
        if word_index < 0:
            self._view._safe_notify(
                "Select a valid OCR word bbox to edit", type_="warning"
            )
            return

        split_key = (line_index, word_index)
        split_x_fraction = self._view._word_split_fractions.get(split_key)
        split_y_fraction = self._view._word_split_y_fractions.get(split_key)
        split_y_px = self._view._word_split_marker_y.get(split_key)
        image_size = self._view._word_split_image_sizes.get(split_key)
        if image_size is None:
            self._view._safe_notify(
                "Click inside the word image to place a marker first",
                type_="warning",
            )
            return

        line_word_match = self._view._line_word_match_by_ocr_index(
            line_index, word_index
        )
        if line_word_match is None:
            self._view._safe_notify(
                "Selected word is no longer available", type_="warning"
            )
            return

        bbox_width = 0.0
        bbox_height = 0.0
        line_match = self._view._line_match_by_index(line_index)
        page_image = getattr(line_match, "page_image", None) if line_match else None
        if page_image is not None:
            try:
                preview_bbox = self.preview_bbox_for_word(
                    line_word_match,
                    page_image,
                    line_index=line_index,
                    word_index=word_index,
                )
            except Exception:
                preview_bbox = None
            if preview_bbox is not None:
                px1, py1, px2, py2 = preview_bbox
                bbox_width = max(0.0, float(px2) - float(px1))
                bbox_height = max(0.0, float(py2) - float(py1))

        if bbox_width <= 0.0 or bbox_height <= 0.0:
            # Fallback for contexts where preview bbox cannot be resolved.
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
            self._view._safe_notify(
                "Cannot crop: invalid word bounding box", type_="warning"
            )
            return

        left_delta = 0.0
        right_delta = 0.0
        top_delta = 0.0
        bottom_delta = 0.0

        if direction == "above":
            if split_y_fraction is None:
                if split_y_px is None:
                    self._view._safe_notify(
                        "Click inside the word image to place a marker first",
                        type_="warning",
                    )
                    return
                split_y_fraction = float(split_y_px) / float(image_height)
            else:
                split_y_fraction = float(split_y_fraction)
            if split_y_fraction <= 0.0 or split_y_fraction >= 1.0:
                self._view._safe_notify("Marker is out of bounds", type_="warning")
                return
            top_delta = -bbox_height * split_y_fraction
        elif direction == "below":
            if split_y_fraction is None:
                if split_y_px is None:
                    self._view._safe_notify(
                        "Click inside the word image to place a marker first",
                        type_="warning",
                    )
                    return
                split_y_fraction = float(split_y_px) / float(image_height)
            else:
                split_y_fraction = float(split_y_fraction)
            if split_y_fraction <= 0.0 or split_y_fraction >= 1.0:
                self._view._safe_notify("Marker is out of bounds", type_="warning")
                return
            bottom_delta = -bbox_height * (1.0 - split_y_fraction)
        elif direction == "left":
            if split_x_fraction is None:
                self._view._safe_notify(
                    "Click inside the word image to place a marker first",
                    type_="warning",
                )
                return
            split_x_fraction = float(split_x_fraction)
            if split_x_fraction <= 0.0 or split_x_fraction >= 1.0:
                self._view._safe_notify("Marker is out of bounds", type_="warning")
                return
            left_delta = -bbox_width * split_x_fraction
        elif direction == "right":
            if split_x_fraction is None:
                self._view._safe_notify(
                    "Click inside the word image to place a marker first",
                    type_="warning",
                )
                return
            split_x_fraction = float(split_x_fraction)
            if split_x_fraction <= 0.0 or split_x_fraction >= 1.0:
                self._view._safe_notify("Marker is out of bounds", type_="warning")
                return
            right_delta = -bbox_width * (1.0 - split_x_fraction)
        else:
            self._view._safe_notify("Unsupported crop direction", type_="warning")
            return

        previous_line_selection = set(self._view.selection.selected_line_indices)
        previous_word_selection = set(self._view.selection.selected_word_indices)
        self._view.selection.selected_line_indices.clear()
        self._view.selection.selected_word_indices.clear()
        self._view.toolbar.update_button_state()
        self._view.selection.emit_selection_changed()

        try:
            success = self._view.nudge_word_bbox_callback(
                line_index,
                word_index,
                left_delta,
                right_delta,
                top_delta,
                bottom_delta,
                False,
            )
            if success:
                self._view.renderer.refresh_local_line_match_from_line_object(
                    line_index
                )
                self._view._update_summary()
                self._view.renderer.rerender_line_card(line_index)
                self._view.renderer.refresh_open_word_dialog_for(line_index, word_index)
                self._view._safe_notify(
                    f"Cropped word {word_index + 1} ({direction})",
                    type_="positive",
                )
            else:
                self._view.selection.selected_line_indices = previous_line_selection
                self._view.selection.selected_word_indices = previous_word_selection
                self._view.toolbar.update_button_state()
                self._view.selection.emit_selection_changed()
                self._view._safe_notify("Failed to crop word bbox", type_="warning")
        except Exception as e:
            self._view.selection.selected_line_indices = previous_line_selection
            self._view.selection.selected_word_indices = previous_word_selection
            self._view.toolbar.update_button_state()
            self._view.selection.emit_selection_changed()
            logger.exception(
                "Error cropping word bbox (%s, %s, %s): %s",
                line_index,
                word_index,
                direction,
                e,
            )
            self._view._safe_notify(f"Error cropping word bbox: {e}", type_="negative")

    # ------------------------------------------------------------------
    # Line image helper
    # ------------------------------------------------------------------

    def get_line_image(self, line_match: "LineMatch") -> str | None:
        """Get cropped line image as base64 data URL.

        Args:
            line_match: The LineMatch object containing the line to crop.

        Returns:
            Base64 data URL string for the cropped line image, or None if unavailable.
        """
        logger.debug("Getting line image for line %s", line_match.line_index)
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
                logger.debug("Error cropping line image: %s", e)
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
            logger.debug("Error creating line image: %s", e)
            return None

    # ------------------------------------------------------------------
    # State cleanup
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset all bbox-related state."""
        self._bbox_editor_open_keys.clear()
        self._bbox_pending_deltas.clear()
        self._pending_rebox_word_key = None
