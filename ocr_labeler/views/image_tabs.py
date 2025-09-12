from pathlib import Path
import hashlib

from nicegui import ui


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
        native = state.project_state.current_page_native
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
            cache_root = Path(state.project_state.project_root).resolve() / "_overlay_cache"
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
