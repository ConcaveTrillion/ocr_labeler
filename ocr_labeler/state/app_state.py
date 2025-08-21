from __future__ import annotations
from dataclasses import dataclass, field
import asyncio
from pathlib import Path
from typing import Optional, Callable
import logging

from ..models.project import ProjectVM
try:  # Lazy import; NiceGUI only needed at runtime in UI context
    from nicegui import ui  # type: ignore
except Exception:  # pragma: no cover
    ui = None  # type: ignore
from pd_book_tools.ocr.page import Page  # type: ignore

logger = logging.getLogger(__name__)

# NOTE: This file was extracted from the original monolithic model.py to improve
# maintainability. Logic is split further into helpers in helpers/*.py.

@dataclass
class AppState:
    """Minimal application state: project pages + current OCR page images.

    Responsibilities:
    - Manage project root & associated lazy-loaded pages (via ProjectVM)
    - Coordinate navigation and background OCR page loading
    - Provide ground truth reload capability
    - Expose change notifications for the view layer
    """

    project_root: Path
    monospace_font_name: str = "monospace"
    monospace_font_path: Optional[Path] = None

    project: ProjectVM = field(default_factory=ProjectVM)
    current_page_native: object | None = None  # native pd_book_tools Page object after OCR
    on_change: Optional[Callable[[], None]] = None
    is_loading: bool = False
    is_project_loading: bool = False  # True only during full project load

    # --------------- Notification ---------------
    def notify(self):
        if self.on_change:
            self.on_change()

    # --------------- Project Loading ---------------
    def load_project(self, directory: Path):
        """Load images; lazily OCR each page via DocTR on first access.

        Reads pages.json (if present) mapping image filename -> ground truth text.
        """
        from .ground_truth import load_ground_truth_map  # local import to avoid cycles
        from .page_loader import build_page_loader

        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(directory)
        # Indicate a project-level loading phase so the UI can hide content & show spinner
        self.is_loading = True
        self.is_project_loading = True
        self.notify()
        try:
            self.project_root = directory
            images = sorted([p for p in directory.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])

            ground_truth_map = load_ground_truth_map(directory)
            page_loader = build_page_loader()

            placeholders: list[Page | None] = [None] * len(images)
            self.project = ProjectVM(
                pages=placeholders,
                image_paths=images,  # type: ignore[arg-type]
                current_page_index=0 if images else -1,
                page_loader=page_loader,
                ground_truth_map=ground_truth_map,
            )
            self.current_page_native = self.project.current_page() if images else None
        finally:
            # Clear project-level loading state (page-level loading continues via navigation spinner logic)
            self.is_loading = False
            self.is_project_loading = False
            self.notify()

    # --------------- Ground Truth Reload ---------------
    def reload_ground_truth(self):
        from .ground_truth import reload_ground_truth_into_project
        reload_ground_truth_into_project(self)

    # --------------- Navigation ---------------
    def next_page(self):
        self._navigate(self.project.next_page)

    def prev_page(self):
        self._navigate(self.project.prev_page)

    def goto_page_number(self, number: int):
        def action():
            self.project.goto_page_number(number)
        self._navigate(action)

    def current_page(self) -> Page | None:
        return self.project.current_page()

    # Backwards compatibility if elsewhere still calls it
    def _ocr_current_page(self):  # pragma: no cover
        self.current_page_native = self.project.current_page()

    # --------------- Internal navigation helper with loading state ---------------
    def _navigate(self, nav_callable: Callable[[], None]):
        nav_callable()  # quick index change first
        self.is_loading = True
        self.is_project_loading = False  # navigation only
        self.current_page_native = None
        self.notify()

        async def _background_load():
            try:
                page = await asyncio.to_thread(self.project.current_page)
                self.current_page_native = page
            finally:
                self.is_loading = False
                self.notify()

        def _schedule_async_load():
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_background_load())
            except RuntimeError:  # no loop present
                try:
                    page = self.project.current_page()
                    self.current_page_native = page
                finally:
                    self.is_loading = False
                    self.notify()

        if ui is not None:
            ui.timer(0.05, _schedule_async_load, once=True)  # type: ignore[arg-type]
        else:  # Non-UI fallback
            _schedule_async_load()

    # --------------- Project Discovery ---------------
    def list_available_projects(self) -> dict[str, Path]:
        """Return mapping of project name -> path under the canonical data root.

        The dropdown in the view should be populated from the fixed directory:
            ~/ocr/data/source-pgdp-data/output

        A "project" is any immediate subdirectory containing at least one image file
        (*.png|*.jpg|*.jpeg). If the root doesn't exist, returns an empty dict.
        """
        try:
            base_root = Path("~/ocr/data/source-pgdp-data/output").expanduser().resolve()
        except Exception:  # pragma: no cover - path resolution errors
            return {}
        if not base_root.exists():  # pragma: no cover - environment dependent
            return {}
        projects: dict[str, Path] = {}
        try:
            for d in sorted(p for p in base_root.iterdir() if p.is_dir()):
                try:
                    if any(f.suffix.lower() in {'.png', '.jpg', '.jpeg'} for f in d.iterdir() if f.is_file()):
                        projects[d.name] = d
                except Exception:  # noqa: BLE001 - skip unreadable child
                    continue
        except Exception:  # pragma: no cover - defensive
            logging.getLogger(__name__).debug("Project discovery failed", exc_info=True)
            return {}
        return projects
