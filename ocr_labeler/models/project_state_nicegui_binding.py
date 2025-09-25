import logging
from pathlib import Path

from nicegui import binding

from ..state import ProjectState

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class ProjectStateNiceGuiBinding:
    _project_state: ProjectState

    is_navigating: bool = False
    page_total: int = 0
    current_page_index: int = 0
    is_project_loading: bool = False
    project_root: str = ""
    project_root_resolved: str = ""
    is_busy: bool = False

    def __init__(self, project_state: ProjectState):
        logger.debug(
            f"Initializing ProjectControlsModel with project_state: {project_state.project.project_id is not None}"
        )

        if project_state is not None and isinstance(project_state, ProjectState):
            self._project_state = project_state
            logger.debug("Registering project state change listener")
            self._project_state.on_change.append(self._on_project_state_change)
            logger.debug("Registered project state change listener")
        else:
            logger.error(
                "Project state of type ProjectState not provided to ProjectControlsModel!"
            )
            raise ValueError(
                "Project state of type ProjectState not provided to ProjectControlsModel!"
            )
        self.update()

    # Only propagate one-way from ProjectState to model, not vice versa
    def update(self):
        """Sync model from ProjectState via state change listener."""
        logger.debug("Updating ProjectControlsModel from ProjectState")
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

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Project page total: {self.page_total}")
                logger.debug(f"Current page index: {self.current_page_index}")
                logger.debug(f"Is navigating: {self.is_navigating}")
                logger.debug(f"Is project loading: {self.is_project_loading}")
                logger.debug(f"Is busy: {self.is_busy}")
                logger.debug(f"Project root: {self.project_root}")
                logger.debug(f"Project root resolved: {self.project_root_resolved}")
                logger.debug("ProjectStateNiceGuiBinding update complete")
        else:
            logger.error(
                "No project state available when updating ProjectStateNiceGuiBinding!"
            )
            raise ValueError(
                "No project state available when updating ProjectStateNiceGuiBinding!"
            )

    def _on_project_state_change(self):
        """Listener for ProjectState changes; update model properties."""
        logger.debug("Project State change detected, updating model")
        self.update()
