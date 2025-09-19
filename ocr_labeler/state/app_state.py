from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .project_state import ProjectState

try:  # Lazy import; NiceGUI only needed at runtime in UI context
    from nicegui import ui  # type: ignore
except Exception:  # pragma: no cover
    ui = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Application State

    Responsibilities:
    - Manage application-level UI state and settings
    - Handle project discovery and selection
    - Coordinate between project state and UI
    - Provide application-wide notification system
    """

    # Application-level settings
    # Optional override for the root under which project subdirectories are discovered.
    # If None, falls back to the original fixed path (~/ocr/data/source-pgdp-data/output).
    base_projects_root: Path | None = None
    monospace_font_name: str = "monospace"
    monospace_font_path: Optional[Path] = None

    # Project state management
    projects: dict[str, ProjectState] = field(default_factory=dict)
    current_project_key: str | None = None
    on_change: Optional[Callable[[], None]] = None
    is_project_loading: bool = False  # True only during full project load

    # Reactive project selection data for UI bindings
    available_projects: dict[str, Path] = field(default_factory=dict)
    project_keys: list[str] = field(
        default_factory=list
    )  # sorted keys for select options
    selected_project_key: str | None = (
        None  # currently selected project key (folder name)
    )

    # --------------- Initialization Hook ---------------
    def __post_init__(self):  # pragma: no cover - simple initialization
        """Initialize application state and set up project state notifications.

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
            logger.debug(
                "__post_init__: deriving initial project keys failed", exc_info=True
            )

    # --------------- Notification ---------------
    def notify(self):
        if self.on_change:
            self.on_change()

    # --------------- Project Loading ---------------
    async def load_project(self, directory: Path):
        """Load a project by delegating to project state.

        Manages application-level loading state and project selection synchronization.
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(directory)

        project_key = directory.resolve().name

        # Indicate a project-level loading phase so the UI can hide content & show spinner
        self.is_project_loading = True
        self.notify()

        try:
            # Keep selection in sync (used by bindings)
            self.selected_project_key = project_key
            self.current_project_key = project_key

            # Get or create project state
            if project_key not in self.projects:
                self.projects[project_key] = ProjectState()
                # Set up notifications for the new project state
                self.projects[project_key].on_change = self.notify

            # Delegate actual project loading to project state
            await self.projects[project_key].load_project(directory)
        finally:
            # Clear project-level loading state (page-level loading continues via navigation spinner logic)
            self.is_project_loading = False
            self.notify()

    @property
    def is_loading(self) -> bool:
        """Get loading state from current project state or app level."""
        if self.current_project_key and self.current_project_key in self.projects:
            return (
                self.projects[self.current_project_key].is_loading
                or self.is_project_loading
            )
        # Check default project state if no current project
        if hasattr(self, "_default_project_state"):
            return self._default_project_state.is_loading or self.is_project_loading
        return self.is_project_loading

    @is_loading.setter
    def is_loading(self, value: bool):
        """Set loading state on current project state."""
        if self.current_project_key and self.current_project_key in self.projects:
            self.projects[self.current_project_key].is_loading = value
        else:
            # Set on default project state if no current project
            if not hasattr(self, "_default_project_state"):
                self._default_project_state = ProjectState()
                self._default_project_state.on_change = self.notify
            self._default_project_state.is_loading = value

    @property
    def project_state(self) -> ProjectState:
        """Get the current project state for backward compatibility."""
        if self.current_project_key and self.current_project_key in self.projects:
            return self.projects[self.current_project_key]
        # Return a default empty project state if no current project
        if not hasattr(self, "_default_project_state"):
            self._default_project_state = ProjectState()
            self._default_project_state.on_change = self.notify
        return self._default_project_state

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
                logger.critical(
                    "Failed to resolve custom projects root %s",
                    self.base_projects_root,
                    exc_info=True,
                )
                return {}
        else:
            try:
                discovery_root = (
                    Path("~/ocr/data/source-pgdp-data/output").expanduser().resolve()
                )
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
                    if any(
                        f.suffix.lower() in {".png", ".jpg", ".jpeg"}
                        for f in d.iterdir()
                        if f.is_file()
                    ):
                        projects[d.name] = d
                except Exception:  # noqa: BLE001 - skip unreadable child
                    logger.critical(
                        "Failed to read project directory %s", d, exc_info=True
                    )
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
            # Re-scan for available projects
            self.available_projects = self.list_available_projects()
            projects = self.available_projects or {}
            logger.debug(
                "refresh_projects: building keys from available_projects (count=%d, names=%s)",
                len(projects),
                sorted(projects.keys()),
            )
            self.project_keys = sorted(projects.keys())

            # Only assign a default if none chosen yet or existing choice no longer valid.
            if (
                not self.selected_project_key
                or self.selected_project_key not in projects
            ):
                self.selected_project_key = (
                    self.project_keys[0] if self.project_keys else None
                )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "refresh_projects: failed while preparing reactive project lists"
            )
            self.project_keys = []
            self.selected_project_key = None
        finally:
            self.notify()

    # --------------- Convenience ---------------
    def selected_project_path(self) -> Path | None:  # pragma: no cover - UI helper
        if not self.selected_project_key:
            return None
        return self.available_projects.get(self.selected_project_key)
