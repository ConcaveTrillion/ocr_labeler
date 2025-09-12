from __future__ import annotations
from dataclasses import dataclass, field
import asyncio
from pathlib import Path
from typing import Optional, Callable
import logging

from ..models.project import Project
from pd_book_tools.ocr.page import Page  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class ProjectState:
    """Project-specific state management.

    Responsibilities:
    - Manage the current project and its pages
    - Handle navigation within the project
    - Coordinate individual OCR page loading
    - Provide ground truth reload capability for the current project
    """

    project: Project = field(default_factory=Project)
    current_page_native: object | None = None  # native pd_book_tools Page object after OCR
    project_root: Path = Path("../data/source-pgdp-data/output")
    is_loading: bool = False
    on_change: Optional[Callable[[], None]] = None

    def notify(self):
        """Notify listeners of state changes."""
        if self.on_change:
            self.on_change()

    def load_project(self, directory: Path):
        """Load images; lazily OCR each page via DocTR on first access.

        Reads pages.json (if present) mapping image filename -> ground truth text.
        """
        from .ground_truth import load_ground_truth_map  # local import to avoid cycles
        from .page_loader import build_page_loader

        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(directory)
        
        self.is_loading = True
        self.notify()
        try:
            self.project_root = directory
            images = sorted([p for p in directory.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])

            ground_truth_map = load_ground_truth_map(directory)
            page_loader = build_page_loader()

            placeholders: list[Page | None] = [None] * len(images)
            self.project = Project(
                pages=placeholders,
                image_paths=images,  # type: ignore[arg-type]
                current_page_index=0 if images else -1,
                page_loader=page_loader,
                ground_truth_map=ground_truth_map,
            )
            self.current_page_native = self.project.current_page() if images else None
        finally:
            self.is_loading = False
            self.notify()

    def reload_ground_truth(self):
        """Reload ground truth for the current project."""
        # Import inside method to allow test monkeypatching of module attribute
        try:
            from .ground_truth import reload_ground_truth_into_project as _reload
        except Exception:  # pragma: no cover - defensive
            return
        _reload(self)

    def next_page(self):
        """Navigate to the next page."""
        self._navigate(self.project.next_page)

    def prev_page(self):
        """Navigate to the previous page."""
        self._navigate(self.project.prev_page)

    def goto_page_number(self, number: int):
        """Navigate to a specific page number."""
        def action():
            self.project.goto_page_number(number)
        self._navigate(action)

    def current_page(self) -> Page | None:
        """Get the current page."""
        return self.project.current_page()

    def _navigate(self, nav_callable: Callable[[], None]):
        """Internal navigation helper with loading state."""
        nav_callable()  # quick index change first
        self.is_loading = True
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
            """Schedule background load if an event loop is running.

            Option A with extra handling for test mocks: if create_task returns a non-Task
            (e.g., a test stub that just records the call and returns None), close the
            coroutine to avoid an un-awaited coroutine warning while still leaving the
            loading flag True (as real async completion would later clear it).
            """
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # no running loop at all
                logger.info("No running event loop; falling back to synchronous page load")
                # Fallback synchronous load
                try:
                    page = self.project.current_page()
                    self.current_page_native = page
                finally:
                    self.is_loading = False
                    self.notify()
                return

            logger.info("_schedule_async_load: got running loop %s", loop)
            coro = _background_load()
            try:
                task = loop.create_task(coro)
                # If a test replaced create_task with a stub that returns None or non-Task, close coro
                if not isinstance(task, asyncio.Task):  # pragma: no cover - exercised in tests via mock
                    try:
                        coro.close()
                    except Exception:  # pragma: no cover - defensive
                        pass
                return
            except Exception:  # scheduling failed (closed loop, etc.)
                try:
                    coro.close()  # prevent 'never awaited' warning
                except Exception:  # pragma: no cover - defensive
                    pass
                # Fallback synchronous load
                try:
                    page = self.project.current_page()
                    self.current_page_native = page
                finally:
                    self.is_loading = False
                    self.notify()

        _schedule_async_load()
