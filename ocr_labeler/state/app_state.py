from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from nicegui import run

from ..operations.persistence.project_discovery_operations import (
    ProjectDiscoveryOperations,
)
from .project_state import ProjectState

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
    on_change: Optional[List[Callable[[], None]]] = field(default_factory=list)

    is_project_loading: bool = False  # True only during full project load

    # Reactive project selection data for UI bindings
    available_projects: dict[str, Path] = field(default_factory=dict)
    project_keys: list[str] = field(
        default_factory=list
    )  # sorted keys for select options
    _selected_project_key: str | None = None  # currently selected project key
    _notification_queue: deque[tuple[str, str]] = field(
        default_factory=deque, init=False, repr=False
    )
    _notification_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def queue_notification(self, message: str, kind: str = "info") -> None:
        """Queue a user notification for this browser-tab session."""
        if not message:
            return
        with self._notification_lock:
            self._notification_queue.append((message, kind))

    def pop_notification(self) -> tuple[str, str] | None:
        """Pop one queued notification for paced UI delivery."""
        with self._notification_lock:
            if not self._notification_queue:
                return None
            return self._notification_queue.popleft()

    @property
    def selected_project_key(self) -> str | None:
        """Get the currently selected project key."""
        return self._selected_project_key

    @selected_project_key.setter
    def selected_project_key(self, value: str | None):
        """Set the currently selected project key."""
        if value != self._selected_project_key:
            self._selected_project_key = value
            self.notify()

    # --------------- Initialization Hook ---------------
    def __post_init__(self):  # pragma: no cover - simple initialization
        """Initialize application state and set up project state notifications.

        Ensures that any UI building against this state instance has an
        initial project list without needing an explicit manual call.
        """
        try:
            self.available_projects = self.list_available_projects()
        except Exception:
            logger.exception("__post_init__: failed to list available projects")
            self.available_projects = {}

        # Directly derive keys and set default selection to first project (if any)
        # without attempting to match current project_root or loading anything.
        try:
            self.project_keys = sorted(self.available_projects.keys())
            if self.project_keys:
                self.selected_project_key = self.project_keys[0]
        except Exception:
            logger.exception(
                "__post_init__: deriving initial project keys failed", exc_info=True
            )

    # --------------- Notification ---------------
    def notify(self):
        """Notify listeners of state changes."""
        for listener in self.on_change:
            listener()

    # --------------- Project Loading ---------------
    async def load_project(
        self,
        directory: Path,
        initial_page_index: int | None = None,
        manage_loading_state: bool = True,
    ):
        """Load a project by delegating to project state.

        Manages application-level loading state and project selection synchronization.
        """
        logger.debug(f"Loading project from directory: {directory}")

        directory = Path(directory)
        if not await run.io_bound(directory.exists):
            raise FileNotFoundError(directory)

        project_key = directory.resolve().name

        # Indicate a project-level loading phase so the UI can hide content & show spinner
        if manage_loading_state:
            self.queue_notification(f"Loading {project_key}", "info")
            self.is_project_loading = True
            self.notify()

        try:
            # Keep selection in sync (used by bindings)
            self.selected_project_key = project_key
            self.current_project_key = project_key

            # Get or create project state
            if project_key not in self.projects:
                self.projects[project_key] = ProjectState(
                    notification_sink=self.queue_notification
                )
                # Set up notifications for the new project state
                self.projects[project_key].on_change.append(self.notify)
            else:
                self.projects[project_key].notification_sink = self.queue_notification

            # Delegate actual project loading to project state
            await self.projects[project_key].load_project(
                directory, initial_page_index=initial_page_index
            )

            if manage_loading_state:
                self.queue_notification(f"Loaded {project_key}", "positive")
        finally:
            # Clear project-level loading state (page-level loading continues via navigation spinner logic)
            if manage_loading_state:
                self.is_project_loading = False
                self.notify()

    @property
    def is_loading(self) -> bool:
        """Get loading state from current project state or app level."""
        if self.current_project_key and self.current_project_key in self.projects:
            return (
                self.projects[self.current_project_key].is_project_loading
                or self.projects[self.current_project_key].is_navigating
                or self.is_project_loading
            )
        # Check default project state if no current project
        if hasattr(self, "_default_project_state"):
            return (
                self._default_project_state.is_project_loading
                or self._default_project_state.is_navigating
                or self.is_project_loading
            )
        return self.is_project_loading

    @is_loading.setter
    def is_loading(self, value: bool):
        """Set loading state on current project state."""
        if self.current_project_key and self.current_project_key in self.projects:
            self.projects[self.current_project_key].is_project_loading = value
        else:
            # Set on default project state if no current project
            if not hasattr(self, "_default_project_state"):
                self._default_project_state = ProjectState()
                self._default_project_state.on_change.append(self.notify)
            self._default_project_state.is_project_loading = value

    @property
    def project_state(self) -> ProjectState:
        """Get the current project state for backward compatibility."""
        if self.current_project_key and self.current_project_key in self.projects:
            return self.projects[self.current_project_key]
        # Return a default empty project state if no current project
        if not hasattr(self, "_default_project_state"):
            self._default_project_state = ProjectState(
                notification_sink=self.queue_notification
            )
            self._default_project_state.on_change.append(self.notify)
        return self._default_project_state

    # --------------- Project Discovery ---------------
    def list_available_projects(self) -> dict[str, Path]:
        """Return mapping of project name -> path under the canonical data root.

        The dropdown in the view should be populated from the fixed directory:
            ~/ocr/data/source-pgdp-data/output

        A "project" is any immediate subdirectory containing at least one image file
        (*.png|*.jpg|*.jpeg). If the root doesn't exist, returns an empty dict.
        """
        return ProjectDiscoveryOperations.list_available_projects(
            self.base_projects_root
        )

    # --------------- Project Discovery (reactive helper) ---------------
    def refresh_projects(self):  # pragma: no cover - UI driven
        """Populate reactive project lists for UI bindings.

        Updates available_projects, project_keys, and selected_project_key (if current root present).
        """
        try:
            # Re-scan for available projects
            self.available_projects = (
                ProjectDiscoveryOperations.list_available_projects(
                    self.base_projects_root
                )
            )
            projects = self.available_projects or {}
            logger.debug(
                "refresh_projects: building keys from available_projects (count=%d, names=%s)",
                len(projects),
                sorted(projects.keys()),
            )
            self.project_keys = ProjectDiscoveryOperations.get_project_keys(projects)

            # Only assign a default if none chosen yet or existing choice no longer valid.
            if (
                not self.selected_project_key
                or self.selected_project_key not in projects
            ):
                self.selected_project_key = (
                    ProjectDiscoveryOperations.get_default_project_key(
                        self.project_keys
                    )
                )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "refresh_projects: failed while preparing reactive project lists"
            )
            self.project_keys = []
            self.selected_project_key = None
        finally:
            self.notify()

    async def load_selected_project(self):
        """Load the currently selected project.

        Handles validation, loading state, and notifications for the selected project.
        """
        if self.is_loading:
            return

        key = self.selected_project_key
        if not key:
            # This shouldn't happen if UI is properly bound, but defensive
            logger.warning("load_selected_project: no project selected")
            return

        # Ensure mapping is fresh
        if not self.available_projects:
            self.refresh_projects()

        path = self.available_projects.get(key)
        if not path:
            logger.error(
                "load_selected_project: selected project path missing for key %s", key
            )
            return

        # The load_project method already handles loading state and notifications
        await self.load_project(path)
