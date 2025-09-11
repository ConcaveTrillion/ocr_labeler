from __future__ import annotations
from dataclasses import dataclass, field
import asyncio
from pathlib import Path
from typing import Optional, Callable
import logging

from ..models.project import Project
try:  # Lazy import; NiceGUI only needed at runtime in UI context
    from nicegui import ui  # type: ignore
except Exception:  # pragma: no cover
    ui = None  # type: ignore
from pd_book_tools.ocr.page import Page  # type: ignore


logger = logging.getLogger(__name__)

@dataclass
class AppState:
    """Application State

    Responsibilities:
    - Manage project load & associated lazy-loaded pages (via Project)
    - Coordinate navigation and individual OCR page loading
    - Provide ground truth reload capability
    - Expose bindings for the view layer
    - Loads done via async
    """

    project_root: Path = "../data/source-pgdp-data/output"
    # Optional override for the root under which project subdirectories are discovered.
    # If None, falls back to the original fixed path (~/ocr/data/source-pgdp-data/output).
    base_projects_root: Path | None = None
    monospace_font_name: str = "monospace"
    monospace_font_path: Optional[Path] = None

    project: Project = field(default_factory=Project)
    current_page_native: object | None = None  # native pd_book_tools Page object after OCR
    on_change: Optional[Callable[[], None]] = None
    is_loading: bool = False
    is_project_loading: bool = False  # True only during full project load
    # Reactive project selection data for UI bindings
    available_projects: dict[str, Path] = field(default_factory=dict)
    project_keys: list[str] = field(default_factory=list)  # sorted keys for select options
    selected_project_key: str | None = None  # currently selected project key (folder name)

    # --------------- Initialization Hook ---------------
    def __post_init__(self):  # pragma: no cover - simple initialization
        """Populate available_projects immediately upon creation.

        Ensures that any UI building against this state instance has an
        initial project list without needing an explicit manual call.
        """
        try:
            self.available_projects = self.list_available_projects()
        except Exception:  # noqa: BLE001 - defensive
            logger.exception("__post_init__: failed to list available projects")
            self.available_projects = {}
        # Directly derive keys and set default selection to first project (if any)
        # without attempting to match current project_root or loading anything.
        try:
            self.project_keys = sorted(self.available_projects.keys())
            if self.project_keys:
                self.selected_project_key = self.project_keys[0]
        except Exception:  # pragma: no cover - defensive
            logger.debug("__post_init__: deriving initial project keys failed", exc_info=True)

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
            # Keep selection in sync (used by bindings)
            try:  # pragma: no cover - UI selection sync (not exercised in tests)
                self.selected_project_key = directory.resolve().name
            except Exception:  # pragma: no cover - defensive
                self.selected_project_key = directory.name  # pragma: no cover
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
            # Clear project-level loading state (page-level loading continues via navigation spinner logic)
            self.is_loading = False
            self.is_project_loading = False
            self.notify()

    # --------------- Ground Truth Reload ---------------
    def reload_ground_truth(self):
        # Import inside method to allow test monkeypatching of module attribute
        try:
            from .ground_truth import reload_ground_truth_into_project as _reload
        except Exception:  # pragma: no cover - defensive
            return
        _reload(self)

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

    # --------------- Project Discovery ---------------
    def list_available_projects(self) -> dict[str, Path]:
        """Return mapping of project name -> path under the canonical data root.

        The dropdown in the view should be populated from the fixed directory:
            ~/ocr/data/source-pgdp-data/output

        A "project" is any immediate subdirectory containing at least one image file
        (*.png|*.jpg|*.jpeg). If the root doesn't exist, returns an empty dict.
        """
        # Determine discovery base: explicit override -> legacy fixed path.
        discovery_root: Path
        if self.base_projects_root is not None:
            try:
                discovery_root = Path(self.base_projects_root).expanduser().resolve()
            except Exception:  # pragma: no cover - resolution error
                logger.critical("Failed to resolve custom projects root %s", self.base_projects_root, exc_info=True)
                return {}
        else:
            try:
                discovery_root = Path("~/ocr/data/source-pgdp-data/output").expanduser().resolve()
            except Exception:  # pragma: no cover - path resolution errors
                logger.critical("Project root path resolution failed", exc_info=True)
                return {}
        try:
            base_root = discovery_root
        except Exception:  # pragma: no cover - path resolution errors
            logger.critical("Project root path resolution failed", exc_info=True)
            return {}
        if not base_root.exists():  # pragma: no cover - environment dependent
            logger.critical("No project root found", exc_info=True)
            return {}
        projects: dict[str, Path] = {}
        try:
            for d in sorted(p for p in base_root.iterdir() if p.is_dir()):
                try:
                    if any(f.suffix.lower() in {'.png', '.jpg', '.jpeg'} for f in d.iterdir() if f.is_file()):
                        projects[d.name] = d
                except Exception:  # noqa: BLE001 - skip unreadable child
                    logger.critical("Failed to read project directory %s", d, exc_info=True)
                    continue
        except Exception:  # pragma: no cover - defensive
            logger.critical("Project discovery failed", exc_info=True)
            return {}
        return projects

    # --------------- Project Discovery (reactive helper) ---------------
    def refresh_projects(self):  # pragma: no cover - UI driven
        """Populate reactive project lists for UI bindings.

        Updates available_projects, project_keys, and selected_project_key (if current root present).
        """
        try:
            # Only derive reactive lists from the existing available_projects mapping.
            # Caller is now responsible for populating/updating self.available_projects.
            projects = self.available_projects or {}
            logger.debug(
                "refresh_projects: building keys from available_projects (count=%d, names=%s)",
                len(projects), sorted(projects.keys()),
            )
            self.project_keys = sorted(projects.keys())

            # Only assign a default if none chosen yet or existing choice no longer valid.
            if not self.selected_project_key or self.selected_project_key not in projects:
                self.selected_project_key = self.project_keys[0] if self.project_keys else None
        except Exception:  # pragma: no cover - defensive
            logger.exception("refresh_projects: failed while preparing reactive project lists")
            self.project_keys = []
            self.selected_project_key = None
        finally:
            self.notify()

    # --------------- Convenience ---------------
    def selected_project_path(self) -> Path | None:  # pragma: no cover - UI helper
        if not self.selected_project_key:
            return None
        return self.available_projects.get(self.selected_project_key)
