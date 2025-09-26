import logging
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import binding

from ..state import ProjectState

if TYPE_CHECKING:
    from .app_state_view_model import AppStateViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class ProjectStateViewModel:
    _project_state: ProjectState
    _app_state_model: "AppStateViewModel | None" = (
        None  # Forward reference to avoid circular import
    )

    is_navigating: bool = False
    page_total: int = 0
    current_page_index: int = 0
    is_project_loading: bool = False
    project_root: str = ""
    project_root_resolved: str = ""
    is_busy: bool = False
    can_navigate: bool = False
    can_navigate_override: bool = False
    can_navigate_prev: bool = False
    can_navigate_next: bool = False
    is_controls_disabled: bool = False

    def __init__(
        self,
        project_state: ProjectState,
        app_state_model: "AppStateViewModel | None" = None,
    ):
        logger.debug(
            f"Initializing ProjectStateViewModel with project_state: {project_state.project.project_id is not None}"
        )

        if project_state is not None and isinstance(project_state, ProjectState):
            self._project_state = project_state
            logger.debug("Registering project state change listener")
            self._project_state.on_change.append(self._on_project_state_change)
            logger.debug("Registered project state change listener")
        else:
            logger.error(
                "Project state of type ProjectState not provided to ProjectStateViewModel!"
            )
            raise ValueError(
                "Project state of type ProjectState not provided to ProjectStateViewModel!"
            )

        self._app_state_model = app_state_model
        if self._app_state_model:
            logger.debug("Registering app state model change listener")
            self._app_state_model._app_state.on_change.append(self._on_app_state_change)
            logger.debug("Registered app state model change listener")
        self.update()

    def override_can_navigate(self, can_navigate_override: bool):
        """Override can_navigate property, e.g. to disable navigation during modal dialogs and requests."""
        logger.debug(f"Setting can_navigate_override to {can_navigate_override}")
        self.can_navigate_override = can_navigate_override

    # Only propagate one-way from ProjectState to model, not vice versa
    def update(self):
        """Sync model from ProjectState via state change listener."""
        logger.debug("Updating ProjectStateViewModel from ProjectState")
        if self._project_state:
            self.page_total = self._project_state.project.page_count()
            self.current_page_index = self._project_state.current_page_index
            self.is_navigating = self._project_state.is_navigating
            self.is_project_loading = self._project_state.is_project_loading
            self.is_busy = (
                self._project_state.is_project_loading
                or self._project_state.is_navigating
            )
            self.project_root = str(self._project_state.project_root)
            # Resolve project root path if possible for display
            self.project_root_resolved = (
                str(
                    self._project_state.project_root.resolve()
                    if isinstance(self._project_state.project_root, Path)
                    else ""
                )
                if self._project_state.project_root
                else ""
            )
            self.can_navigate = (
                self.page_total > 0 and not self.is_busy and not self.is_navigating
            )
            self.can_navigate_prev = self.current_page_index > 0 and self.can_navigate
            self.can_navigate_next = (
                self.current_page_index < self.page_total - 1 and self.can_navigate
            )

            # Update combined disabled state
            app_loading = (
                self._app_state_model.is_project_loading
                if self._app_state_model
                else False
            )
            self.is_controls_disabled = self.is_busy or app_loading

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Project page total: {self.page_total}")
                logger.debug(f"Current page index: {self.current_page_index}")
                logger.debug(f"Is navigating: {self.is_navigating}")
                logger.debug(f"Is project loading: {self.is_project_loading}")
                logger.debug(f"Is busy: {self.is_busy}")
                logger.debug(f"Project root: {self.project_root}")
                logger.debug(f"Project root resolved: {self.project_root_resolved}")
                logger.debug(f"Can navigate: {self.can_navigate}")
                logger.debug(f"Can navigate prev: {self.can_navigate_prev}")
                logger.debug(f"Can navigate next: {self.can_navigate_next}")
                logger.debug("ProjectStateViewModel update complete")
        else:
            logger.error(
                "No project state available when updating ProjectStateViewModel!"
            )
            raise ValueError(
                "No project state available when updating ProjectStateViewModel!"
            )

    def _on_project_state_change(self):
        """Listener for ProjectState changes; update model properties."""
        logger.debug("Project State change detected, updating model")
        self.update()

    def _on_app_state_change(self):
        """Listener for AppState changes; update computed properties."""
        logger.debug("App State change detected, updating computed properties")
        app_loading = (
            self._app_state_model.is_project_loading if self._app_state_model else False
        )
        old_value = self.is_controls_disabled
        self.is_controls_disabled = self.is_busy or app_loading
        if old_value != self.is_controls_disabled:
            # Notify listeners that the computed property changed
            self._project_state.notify()
