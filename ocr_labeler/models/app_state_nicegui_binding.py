import logging
from dataclasses import field

from nicegui import binding

from ..state import AppState

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class AppStateNiceGuiBinding:
    _app_state: AppState

    is_loading: bool = False
    is_project_loading: bool = False
    project_keys: list[str] = field(default_factory=list)
    selected_project_key: str = ""
    selected_project_path: str = ""

    def __init__(self, app_state: AppState):
        logger.debug(
            f"Initializing AppStateNiceGuiBinding with app_state: {app_state is not None}"
        )

        if app_state is not None and isinstance(app_state, AppState):
            self._app_state = app_state
            logger.debug("Registering app state change listener")
            self._app_state.on_change.append(self._on_app_state_change)
            logger.debug("Registered app state change listener")
        else:
            logger.error(
                "App state of type AppState not provided to AppStateNiceGuiBinding!"
            )
            raise ValueError(
                "App state of type AppState not provided to AppStateNiceGuiBinding!"
            )
        self.update()

    # Only propagate one-way from AppState to model, not vice versa
    def update(self):
        """Sync model from AppState via state change listener."""
        logger.debug("Updating AppStateNiceGuiBinding from AppState")
        if self._app_state:
            self.is_loading = self._app_state.is_loading
            self.is_project_loading = self._app_state.is_project_loading
            self.project_keys = (
                self._app_state.project_keys.copy()
                if self._app_state.project_keys
                else []
            )
            self.selected_project_key = self._app_state.selected_project_key or ""
            self.selected_project_path = (
                str(self._app_state.available_projects.get(self.selected_project_key))
                if self.selected_project_key
                and self.selected_project_key in self._app_state.available_projects
                else ""
            )

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Is Loading: {self.is_loading}")
                logger.debug(f"Is Project Loading: {self.is_project_loading}")
                logger.debug(f"Project Keys: {self.project_keys}")
                logger.debug(f"Selected Project Key: {self.selected_project_key}")
                logger.debug(f"Selected Project Path: {self.selected_project_path}")
                logger.debug("AppStateNiceGuiBinding update complete")

        else:
            logger.error("No app state available when updating AppStateNiceGuiBinding!")
            raise ValueError(
                "No app state available when updating AppStateNiceGuiBinding!"
            )

    def update_selected_project(self, key: str):
        """Update the selected project key in the underlying AppState."""
        if self._app_state:
            if key in self._app_state.available_projects:
                self._app_state.selected_project_key = key
                logger.debug(f"Updated selected project key to: {key}")
                self._app_state.notify()
            else:
                logger.error(f"Project key '{key}' not found in available projects!")
                raise ValueError(
                    f"Project key '{key}' not found in available projects!"
                )
        else:
            logger.error("No app state available when updating selected project key!")
            raise ValueError(
                "No app state available when updating selected project key!"
            )

    def _on_app_state_change(self):
        """Listener for AppState changes; update model properties."""
        logger.debug("App State change detected, updating model")
        self.update()
