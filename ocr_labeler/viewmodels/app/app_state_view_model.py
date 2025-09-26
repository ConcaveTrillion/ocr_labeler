import logging
from dataclasses import field
from typing import Optional

from nicegui import binding

from ...state import AppState
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class AppStateViewModel(BaseViewModel):
    """View model for application-level state and UI interactions."""

    _app_state: Optional[AppState] = None

    # UI-bound properties
    is_loading: bool = False
    is_project_loading: bool = False
    project_keys: list[str] = field(default_factory=list)
    selected_project_key: str = ""
    selected_project_path: str = ""
    is_project_loaded: bool = False

    def __setattr__(self, name, value):
        """Override to ensure both NiceGUI binding and custom listeners work."""
        super().__setattr__(name, value)  # Calls NiceGUI's bindable __setattr__
        # Notify custom listeners for properties that have them
        if hasattr(self, "_property_changed_callbacks") and name in [
            "is_loading",
            "is_project_loading",
            "project_keys",
            "selected_project_key",
            "selected_project_path",
            "is_project_loaded",
        ]:
            self.notify_property_changed(name, value)

    def __init__(self, app_state: AppState):
        logger.debug(
            f"Initializing AppStateViewModel with app_state: {app_state is not None}"
        )

        if app_state is not None and isinstance(app_state, AppState):
            self._app_state = app_state
            logger.debug("Registering app state change listener")
            self._app_state.on_change.append(self._on_app_state_change)
            logger.debug("Registered app state change listener")
        else:
            logger.error(
                "App state of type AppState not provided to AppStateViewModel!"
            )
            raise ValueError(
                "App state of type AppState not provided to AppStateViewModel!"
            )

        # Initialize base class
        super().__init__()
        self.update()

    def update(self):
        """Sync model from AppState via state change listener."""
        logger.debug("Updating AppStateViewModel from AppState")
        if self._app_state:
            # Update properties
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
            self.is_project_loaded = bool(self._app_state.current_project_key)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Is Loading: {self.is_loading}")
                logger.debug(f"Is Project Loading: {self.is_project_loading}")
                logger.debug(f"Project Keys: {self.project_keys}")
                logger.debug(f"Selected Project Key: {self.selected_project_key}")
                logger.debug(f"Selected Project Path: {self.selected_project_path}")
                logger.debug(f"Is Project Loaded: {self.is_project_loaded}")
                logger.debug("AppStateViewModel update complete")

        else:
            logger.error("No app state available when updating AppStateViewModel!")
            raise ValueError("No app state available when updating AppStateViewModel!")

    def _on_app_state_change(self):
        """Listener for AppState changes; update model properties."""
        logger.debug("App State change detected, updating model")
        self.update()

    # Command methods for UI actions

    def command_select_project(self, key: str) -> bool:
        """Command to select a project.

        Args:
            key: The project key to select.

        Returns:
            True if selection was successful, False otherwise.
        """
        try:
            if key in self._app_state.available_projects:
                old_key = self.selected_project_key
                self._app_state.selected_project_key = key
                logger.debug(
                    f"Selected project key changed from '{old_key}' to '{key}'"
                )
                self._app_state.notify()
                return True
            else:
                logger.warning(f"Project key '{key}' not found in available projects")
                return False
        except Exception as e:
            logger.exception(f"Error selecting project '{key}': {e}")
            return False

    async def command_load_selected_project(self) -> bool:
        """Command to load the currently selected project.

        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            if not self.selected_project_key:
                logger.warning("No project selected to load")
                return False

            await self._app_state.load_selected_project()
            return True
        except Exception as e:
            logger.exception(f"Error loading selected project: {e}")
            return False

    def command_get_project_display_name(self, key: Optional[str] = None) -> str:
        """Command to get display name for a project.

        Args:
            key: Project key to get display name for. If None, uses selected project.

        Returns:
            Display name for the project.
        """
        project_key = key or self.selected_project_key
        if not project_key:
            return ""

        try:
            project_path = self._app_state.available_projects.get(project_key)
            if project_path:
                return project_path.name
            return project_key
        except Exception as e:
            logger.exception(
                f"Error getting display name for project '{project_key}': {e}"
            )
            return project_key

    def command_is_project_available(self, key: str) -> bool:
        """Command to check if a project is available.

        Args:
            key: Project key to check.

        Returns:
            True if project is available, False otherwise.
        """
        return key in self._app_state.available_projects

    # Legacy methods for backward compatibility (deprecated)
    def update_selected_project(self, key: str):
        """Update the selected project key in the underlying AppState."""
        logger.warning(
            "update_selected_project is deprecated, use command_select_project instead"
        )
        self.command_select_project(key)

    async def load_selected_project(self):
        """Load the currently selected project."""
        import traceback

        logger.warning(
            "load_selected_project is deprecated, use command_load_selected_project instead"
        )
        logger.warning("Call stack: %s", traceback.format_stack())
        await self.command_load_selected_project()
