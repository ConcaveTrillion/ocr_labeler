from __future__ import annotations
from pathlib import Path
import hashlib
import asyncio
from nicegui import ui

try:  # pragma: no cover
    from cv2 import imencode as cv2_imencode  # type: ignore
except Exception:  # pragma: no cover
    cv2_imencode = None  # type: ignore

from ..state import AppState
from ..state.ground_truth import find_ground_truth_text
from .header import HeaderBar
from .content import ContentArea


class LabelerView:  # pragma: no cover - heavy UI wiring
    """Composite main view orchestrating header + content areas."""

    def __init__(self, state: AppState):
        self.state = state
        self.state.on_change = self.refresh
        self.header_bar: HeaderBar | None = None
        self.content: ContentArea | None = None
        self._no_project_placeholder = None
        self._global_loading = None

    # ------------------------------------------------------------ mount
    def mount(self):
        self.header_bar = HeaderBar(self.state)
        self.header_bar.build()

        callbacks = {
            'open_directory': self._open_project_from_path,  # kept for backward compatibility
            'prev': self._prev_async,
            'next': self._next_async,
            'goto': self._goto_async,
        }
        self.content = ContentArea(self.state, callbacks)
        self.content.build()

        # Placeholder shown before any project has been loaded
        self._no_project_placeholder = (
            ui.column()
            .classes("w-full h-[calc(100vh-160px)] items-center justify-center text-gray-500 gap-2 hidden")
        )
        with self._no_project_placeholder:  # type: ignore
            ui.icon('folder_open').classes('text-4xl opacity-40')
            ui.label('No Project Loaded').classes('text-lg font-medium')
            ui.label('Select a project above and click LOAD to begin.')

        # Global project-loading spinner (centered overlay)
        self._global_loading = (
            ui.spinner(size="xl")
            .props("color=primary")
            .classes("fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-40 pointer-events-none hidden")
        )

        self.refresh()

    # ------------------------------------------------------------ actions
    def _open_project_from_path(self, path: Path):
        try:
            self.state.load_project(path)
            if self.header_bar:
                self.header_bar.project_controls.update_path_label()
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Open failed: {exc}", type="negative")

    def _goto_page(self, raw_value):
        try:
            n = int(raw_value)
        except Exception:  # noqa: BLE001
            n = 1
        if n < 1:
            n = 1
        self.state.goto_page_number(n)

    # ------------------------------------------------------------ async navigation helpers
    def _prep_image_spinners(self):
        if self.content:
            for name, img in self.content.image_tabs.images.items():  # noqa: F841
                if img:
                    img.set_visibility(False)

    async def _prev_async(self):  # pragma: no cover - UI side effects
        if getattr(self.state, 'is_loading', False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.state.prev_page()

    async def _next_async(self):  # pragma: no cover - UI side effects
        if getattr(self.state, 'is_loading', False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self.state.next_page()

    async def _goto_async(self, value):  # pragma: no cover - UI side effects
        if getattr(self.state, 'is_loading', False):
            return
        self._prep_image_spinners()
        await asyncio.sleep(0)
        self._goto_page(value)

    # ------------------------------------------------------------ refresh
    def refresh(self):
        loading = getattr(self.state, 'is_loading', False)
        project_loading = getattr(self.state, 'is_project_loading', False)
        # Avoid calling current_page() while loading; it would synchronously create the page
        # and block the UI, defeating async navigation. We'll treat page as None until
        # background thread populates current_page_native and loading flips False.
        # Always compute current index & image name immediately for navigation feedback.
        # Only fetch full page object (with OCR) when not loading to avoid blocking.
        current_index = getattr(self.state.project, 'current_page_index', -1)
        image_name = ''
        if 0 <= current_index < len(self.state.project.image_paths):
            image_name = self.state.project.image_paths[current_index].name
        page = None if loading else self.state.current_page()
        total = len(self.state.project.pages)


        # Update project path label (keep header visible even while loading)
        if self.header_bar:
            self.header_bar.project_controls.update_path_label()

        # Toggle global spinner
        if self._global_loading:
            if project_loading:
                self._global_loading.classes(remove='hidden')
            else:
                self._global_loading.classes(add='hidden')

        # Content & placeholder visibility
        no_project = not getattr(self.state.project, 'image_paths', [])
        if self.content and self.content.root:
            # Keep overall root visible once a project is loaded; hide entirely only if no project.
            if no_project:
                self.content.root.classes(add='hidden')
            else:
                self.content.root.classes(remove='hidden')
            # Toggle splitter vs spinners
            if self.content.splitter and self.content.page_spinner:
                if project_loading:
                    self.content.splitter.classes(add='hidden')
                    self.content.page_spinner.classes(add='hidden')
                elif loading:  # page-level
                    self.content.splitter.classes(add='hidden')
                    self.content.page_spinner.classes(remove='hidden')
                else:
                    self.content.splitter.classes(remove='hidden')
                    self.content.page_spinner.classes(add='hidden')
        if self._no_project_placeholder:
            if no_project and not loading:
                self._no_project_placeholder.classes(remove='hidden')
            else:
                self._no_project_placeholder.classes(add='hidden')

        # Page meta
        if self.content and self.content.page_controls:
            if total:
                # Use immediate index+1 and image filename while OCR loads
                display_index = current_index + 1 if current_index >= 0 else 1
                display_name = image_name or (page.name if page else '(no page)')
                self.content.page_controls.set_page(display_index, display_name, total)
            else:
                self.content.page_controls.set_page(1, '(no page)', 0)

        # Images and text
        if not loading:
            self._update_images()
            self._update_text()

    # ------------------------------------------------------------ helpers
    def _encode_np(self, np_img):  # pragma: no cover
        if np_img is None:
            return None
        if cv2_imencode is not None:
            try:
                ok, buf = cv2_imencode(".png", np_img)
                if ok:
                    import base64
                    return f"data:image/png;base64,{base64.b64encode(buf.tobytes()).decode('ascii')}"
            except Exception:  # noqa: BLE001
                pass
        try:
            cache_root = Path(self.state.project_root).resolve() / "_overlay_cache"
            cache_root.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256(np_img.tobytes()[:1024]).hexdigest()
            fp = cache_root / f"{h}.png"
            if not fp.exists() and cv2_imencode is not None:
                ok, buf = cv2_imencode(".png", np_img)
                if ok:
                    fp.write_bytes(buf.tobytes())
            return fp.as_posix()
        except Exception:  # noqa: BLE001
            return None

    def _update_images(self):
        if not self.content:
            return
        native = self.state.current_page_native
        targets = [
            ("Original", "cv2_numpy_page_image"),
            ("Paragraphs", "cv2_numpy_page_image_paragraph_with_bboxes"),
            ("Lines", "cv2_numpy_page_image_line_with_bboxes"),
            ("Words", "cv2_numpy_page_image_word_with_bboxes"),
            ("Mismatches", "cv2_numpy_page_image_matched_word_with_colors"),
        ]
        if not native:
            for tab_name, _ in targets:
                img = self.content.image_tabs.images.get(tab_name)
                if img:
                    img.set_source(None)
                    img.set_visibility(False)
            return
        if hasattr(native, "refresh_page_images"):
            try:
                native.refresh_page_images()
            except Exception:  # noqa: BLE001
                pass
        for tab_name, attr in targets:
            img = self.content.image_tabs.images.get(tab_name)
            if not img:
                continue
            np_img = getattr(native, attr, None)
            src = self._encode_np(np_img)
            img.set_source(src)
            img.set_visibility(True if src else False)

    def _update_text(self):
        if not self.content:
            return
        page = self.state.current_page()
        if not page:
            if self.content.text_tabs.ocr_text:
                self.content.text_tabs.set_ocr_text("")
            if self.content.text_tabs.gt_text:
                self.content.text_tabs.set_ground_truth_text("")
            return
        if self.content.text_tabs.ocr_text:
            self.content.text_tabs.set_ocr_text(getattr(page, 'text', '') or '')
        if hasattr(page, 'ground_truth_text'):
            gt = (getattr(page, 'ground_truth_text', '') or '')
            if not gt.strip():  # attempt lookup if not already populated
                try:
                    name = getattr(page, 'name', '')
                    gt_lookup = find_ground_truth_text(name, self.state.project.ground_truth_map)
                    if gt_lookup:
                        gt = gt_lookup
                        page.ground_truth_text = gt_lookup  # cache on page
                except Exception:  # noqa: BLE001
                    # TODO Log this
                    pass
            self.content.text_tabs.set_ground_truth_text(gt if gt.strip() else '')
