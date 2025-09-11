from pathlib import Path
import hashlib

from nicegui import ui
from ..state.ground_truth import find_ground_truth_text


class ImageTabs:
    """Left side image tabs showing progressively processed page imagery."""

    def __init__(self):
        self._tab_ids = ["Original", "Paragraphs", "Lines", "Words", "Mismatches"]
        self.images: dict[str, ui.image] = {}
        self.container = None

    def build(self):
        # Root column uses Quasar full-height/width utility classes.
        with ui.column().classes("full-width full-height") as col:
            with ui.tabs().props("dense no-caps shrink") as tabs:
                for name in self._tab_ids:
                    ui.tab(name).props("ripple")
            # Tab panels fill available space; each panel centers its image.
            with ui.tab_panels(tabs, value="Original").classes(
                "full-width full-height"
            ):
                for name in self._tab_ids:
                    with ui.tab_panel(name).classes("column full-width full-height"):
                        with ui.column().classes(
                            "items-center justify-center full-width full-height"
                        ):
                            img = (
                                ui.image()
                                .props(
                                    "fit=contain no-spinner"
                                )  # rely on intrinsic container sizing
                                .classes("full-width full-height")
                            )
                            self.images[name] = img
        self.container = col
        return col

    def update_images(self, state):
        native = state.current_page_native
        targets = [
            ("Original", "cv2_numpy_page_image"),
            ("Paragraphs", "cv2_numpy_page_image_paragraph_with_bboxes"),
            ("Lines", "cv2_numpy_page_image_line_with_bboxes"),
            ("Words", "cv2_numpy_page_image_word_with_bboxes"),
            ("Mismatches", "cv2_numpy_page_image_matched_word_with_colors"),
        ]
        if not native:
            for tab_name, _ in targets:
                img = self.images.get(tab_name)
                if img:
                    img.set_source(None)
                    img.set_visibility(False)
            return
        if hasattr(native, "refresh_page_images"):
            try:
                native.refresh_page_images()
            except Exception:
                pass
        for tab_name, attr in targets:
            img = self.images.get(tab_name)
            if not img:
                continue
            np_img = getattr(native, attr, None)
            src = self._encode_np(np_img, state)
            img.set_source(src)
            img.set_visibility(True if src else False)

    def _encode_np(self, np_img, state):
        if np_img is None:
            return None
        try:
            from cv2 import imencode as cv2_imencode
        except Exception:
            cv2_imencode = None
        if cv2_imencode is not None:
            try:
                ok, buf = cv2_imencode(".png", np_img)
                if ok:
                    import base64
                    return f"data:image/png;base64,{base64.b64encode(buf.tobytes()).decode('ascii')}"
            except Exception:
                pass
        try:
            cache_root = Path(state.project_root).resolve() / "_overlay_cache"
            cache_root.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256(np_img.tobytes()[:1024]).hexdigest()
            fp = cache_root / f"{h}.png"
            if not fp.exists() and cv2_imencode is not None:
                ok, buf = cv2_imencode(".png", np_img)
                if ok:
                    fp.write_bytes(buf.tobytes())
            return fp.as_posix()
        except Exception:
            return None


class TextTabs:
    """Right side textual data tabs (Matches placeholder, Ground Truth, OCR)."""

    def __init__(self):
        # Keep attribute names for external references, but these will hold code_editor instances.
        self.gt_text = None  # type: ignore[assignment]
        self.ocr_text = None  # type: ignore[assignment]
        self.container = None
        self._tabs = None

    def build(self):
        # Root container uses Quasar growth classes; so flex children can shrink.
        # Root must be flex container with so nested 100% heights can resolve
        with ui.column().classes("full-width full-height") as col:
            with ui.tabs() as text_tabs:
                ui.tab("Matches")
                ui.tab("Ground Truth")
                ui.tab("OCR")
            # Panels area should expand to fill remaining height (col makes it flex already).
            with ui.tab_panels(text_tabs, value="Matches").classes(
                "full-width full-height column"
            ):
                # Matches placeholder
                with ui.tab_panel("Matches").classes("full-width full-height column"):
                    ui.label("(Not implemented yet)").classes("text-caption text-grey")
                # Ground Truth panel
                with ui.tab_panel("Ground Truth").classes(
                    "full-width full-height column"
                ):
                    with ui.column().classes("full-width full-height"):
                        self.gt_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
                # OCR panel
                with ui.tab_panel("OCR").classes("full-width full-height column"):
                    with ui.column().classes("full-width full-height"):
                        self.ocr_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height"
                        )
            self._tabs = text_tabs
        self.container = col
        return col

    # --- public helpers -------------------------------------------------
    def set_ocr_text(self, text: str):
        if self.ocr_text is not None:
            self.ocr_text.set_value(text or "")

    def set_ground_truth_text(self, text: str):
        if self.gt_text is not None:
            self.gt_text.set_value(text or "")

    def update_text(self, state):
        page = state.current_page()
        if not page:
            if hasattr(self, "ocr_text") and self.ocr_text:
                self.set_ocr_text("")
            if hasattr(self, "gt_text") and self.gt_text:
                self.set_ground_truth_text("")
            return
        if hasattr(self, "ocr_text") and self.ocr_text:
            self.set_ocr_text(getattr(page, 'text', '') or '')
        if hasattr(page, 'ground_truth_text'):
            gt = (getattr(page, 'ground_truth_text', '') or '')
            if not gt.strip():
                try:
                    name = getattr(page, 'name', '')
                    gt_lookup = find_ground_truth_text(name, state.project.ground_truth_map)
                    if gt_lookup:
                        gt = gt_lookup
                        page.add_ground_truth(gt_lookup)
                except Exception:
                    pass
            if hasattr(self, "set_ground_truth_text"):
                self.set_ground_truth_text(gt if gt.strip() else '')
