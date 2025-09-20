import hashlib
import logging
from pathlib import Path

from nicegui import ui

from ....state import PageState

logger = logging.getLogger(__name__)


class ImageTabs:
    """Left side image tabs showing progressively processed page imagery."""

    def __init__(self, page_state: PageState | None = None):
        self._tab_ids = ["Original", "Paragraphs", "Lines", "Words", "Mismatches"]
        logger.debug("Initializing ImageTabs with tab IDs: %s", self._tab_ids)
        self.images: dict[str, ui.image] = {}
        self.container = None
        self.page_state = page_state
        logger.debug("ImageTabs initialization complete")

    def build(self):
        logger.debug("Building ImageTabs UI components")
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
        logger.debug(
            "ImageTabs UI build complete with %d image components", len(self.images)
        )
        return col

    def update_images(self, state):
        logger.debug("Updating images for ImageTabs")
        native = state.project_state.current_page()
        targets = [
            ("Original", "cv2_numpy_page_image"),
            ("Paragraphs", "cv2_numpy_page_image_paragraph_with_bboxes"),
            ("Lines", "cv2_numpy_page_image_line_with_bboxes"),
            ("Words", "cv2_numpy_page_image_word_with_bboxes"),
            ("Mismatches", "cv2_numpy_page_image_matched_word_with_colors"),
        ]
        if not native:
            logger.debug("No current page available, clearing all images")
            for tab_name, _ in targets:
                img = self.images.get(tab_name)
                if img:
                    img.set_source(None)
                    img.set_visibility(False)
            return
        logger.debug("Processing page: %s", getattr(native, "page_number", "unknown"))
        if hasattr(native, "refresh_page_images"):
            try:
                logger.debug("Refreshing page images")
                native.refresh_page_images()
            except Exception as e:
                logger.warning("Failed to refresh page images: %s", e)
        for tab_name, attr in targets:
            img = self.images.get(tab_name)
            if not img:
                logger.debug("No image component found for tab: %s", tab_name)
                continue
            np_img = getattr(native, attr, None)
            if np_img is None:
                logger.debug("No numpy image available for %s (%s)", tab_name, attr)
                img.set_source(None)
                img.set_visibility(False)
                continue
            logger.debug("Encoding image for %s (%s)", tab_name, attr)
            src = self._encode_np(np_img, state)
            img.set_source(src)
            img.set_visibility(True if src else False)
            logger.debug(
                "Set %s image source: %s", tab_name, "success" if src else "failed"
            )

    def _encode_np(self, np_img, state):
        if np_img is None:
            logger.debug("No numpy image provided for encoding")
            return None
        logger.debug(
            "Attempting to encode numpy image with shape: %s",
            getattr(np_img, "shape", "unknown"),
        )
        try:
            from cv2 import imencode as cv2_imencode

            logger.debug("cv2.imencode available, attempting direct encoding")
        except Exception as e:
            logger.debug("cv2.imencode not available: %s", e)
            cv2_imencode = None
        if cv2_imencode is not None:
            try:
                ok, buf = cv2_imencode(".png", np_img)
                if ok:
                    import base64

                    encoded = f"data:image/png;base64,{base64.b64encode(buf.tobytes()).decode('ascii')}"
                    logger.debug("Successfully encoded image as base64 data URL")
                    return encoded
                else:
                    logger.debug("cv2.imencode failed to encode image")
            except Exception as e:
                logger.debug("cv2.imencode encoding failed: %s", e)
        try:
            cache_root = (
                Path(state.project_state.project_root).resolve() / "_overlay_cache"
            )
            logger.debug("Attempting file-based caching to: %s", cache_root)
            cache_root.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256(np_img.tobytes()[:1024]).hexdigest()
            fp = cache_root / f"{h}.png"
            logger.debug("Cache file path: %s", fp)
            if not fp.exists() and cv2_imencode is not None:
                ok, buf = cv2_imencode(".png", np_img)
                if ok:
                    fp.write_bytes(buf.tobytes())
                    logger.debug("Successfully cached image to file")
                else:
                    logger.debug("Failed to encode image for caching")
            elif fp.exists():
                logger.debug("Using existing cached image file")
            return fp.as_posix()
        except Exception as e:
            logger.debug("File-based encoding/caching failed: %s", e)
            return None
