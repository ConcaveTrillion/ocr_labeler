import logging
from dataclasses import field

from nicegui import binding, run

from ...operations.persistence.config_operations import ConfigOperations
from ...state import AppState
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class AppStateViewModel(BaseViewModel):
    """View model for application-level state and UI interactions."""

    _app_state: AppState | None = None

    # UI-bound properties
    is_loading: bool = False
    is_project_loading: bool = False
    project_keys: list[str] = field(default_factory=list)
    selected_project_key: str | None = None
    selected_project_path: str = ""
    is_project_loaded: bool = False
    ocr_model_options: dict[str, str] = field(default_factory=dict)
    selected_ocr_model_key: str = "default"
    ocr_detection_model_options: dict[str, str] = field(default_factory=dict)
    ocr_recognition_model_options: dict[str, str] = field(default_factory=dict)
    selected_ocr_detection_model_key: str = "default"
    selected_ocr_recognition_model_key: str = "default"

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
            "ocr_model_options",
            "selected_ocr_model_key",
            "ocr_detection_model_options",
            "ocr_recognition_model_options",
            "selected_ocr_detection_model_key",
            "selected_ocr_recognition_model_key",
        ]:
            self.notify_property_changed(name, value)

    def __init__(self, app_state: AppState):
        logger.debug(
            "Initializing AppStateViewModel with app_state: %s", app_state is not None
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
            self.selected_project_key = self._app_state.selected_project_key
            self.selected_project_path = (
                str(self._app_state.available_projects.get(self.selected_project_key))
                if self.selected_project_key
                and self.selected_project_key in self._app_state.available_projects
                else ""
            )
            self.is_project_loaded = bool(self._app_state.current_project_key)
            self.ocr_model_options = dict(self._app_state.ocr_model_options)
            self.selected_ocr_model_key = self._app_state.selected_ocr_model_key
            self.ocr_detection_model_options = dict(
                self._app_state.ocr_detection_model_options
            )
            self.ocr_recognition_model_options = dict(
                self._app_state.ocr_recognition_model_options
            )
            self.selected_ocr_detection_model_key = (
                self._app_state.selected_ocr_detection_model_key
            )
            self.selected_ocr_recognition_model_key = (
                self._app_state.selected_ocr_recognition_model_key
            )

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Is Loading: %s", self.is_loading)
                logger.debug("Is Project Loading: %s", self.is_project_loading)
                logger.debug("Project Keys: %s", self.project_keys)
                logger.debug("Selected Project Key: %s", self.selected_project_key)
                logger.debug("Selected Project Path: %s", self.selected_project_path)
                logger.debug("Is Project Loaded: %s", self.is_project_loaded)
                logger.debug("OCR model options count: %s", len(self.ocr_model_options))
                logger.debug("Selected OCR model key: %s", self.selected_ocr_model_key)
                logger.debug(
                    "Selected OCR detection key: %s",
                    self.selected_ocr_detection_model_key,
                )
                logger.debug(
                    "Selected OCR recognition key: %s",
                    self.selected_ocr_recognition_model_key,
                )
                logger.debug("AppStateViewModel update complete")

        else:
            logger.error("No app state available when updating AppStateViewModel!")
            raise ValueError("No app state available when updating AppStateViewModel!")

    def _on_app_state_change(self):
        """Listener for AppState changes; update model properties."""
        logger.debug("App State change detected, updating model")
        self.update()

    # Command methods for UI actions

    @property
    def source_projects_root_str(self) -> str:
        """Return the currently effective source projects root path as a string."""
        if not self._app_state:
            return ""
        if self._app_state.base_projects_root is not None:
            return str(self._app_state.base_projects_root)
        return str(ConfigOperations.get_source_projects_root())

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
                    "Selected project key changed from '%s' to '%s'", old_key, key
                )
                self._app_state.notify()
                return True
            else:
                logger.warning("Project key '%s' not found in available projects", key)
                return False
        except Exception:
            logger.exception("Error selecting project '%s'", key)
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

            # Ensure underlying AppState reflects the currently selected key from the UI
            try:
                self._app_state.selected_project_key = self.selected_project_key
            except Exception:
                logger.debug(
                    "Failed to sync selected_project_key to AppState", exc_info=True
                )

            await self._app_state.load_selected_project()
            return True
        except Exception:
            logger.exception("Error loading selected project")
            return False

    async def command_set_source_projects_root(self, path_str: str) -> bool:
        """Update the source projects root, persist to config, and rescan projects.

        Args:
            path_str: Absolute or user-expandable path string for the new root.

        Returns:
            True if the root was updated successfully, False otherwise.
        """
        from pathlib import Path

        path_str = path_str.strip()
        if not path_str:
            return False
        try:
            path = Path(path_str).expanduser().resolve()
            await run.io_bound(self._app_state.set_source_projects_root, path)
            logger.debug("Source projects root updated to %s", path)
            return True
        except Exception:
            logger.exception(
                "command_set_source_projects_root failed for path '%s'", path_str
            )
            return False

    def command_get_project_display_name(self, key: str | None = None) -> str:
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
        except Exception:
            logger.exception("Error getting display name for project '%s'", project_key)
            return project_key

    def command_refresh_ocr_models(self) -> bool:
        """Rescan OCR model outputs and refresh selectable options."""
        try:
            self._app_state.refresh_ocr_models()
            return True
        except Exception:
            logger.exception("Error refreshing OCR model options")
            return False

    def command_set_selected_ocr_model(self, model_key: str) -> bool:
        """Set the active OCR model key."""
        try:
            return self._app_state.set_selected_ocr_model(model_key)
        except Exception:
            logger.exception("Error selecting OCR model '%s'", model_key)
            return False

    def command_set_selected_ocr_models(
        self, detection_model_key: str, recognition_model_key: str
    ) -> bool:
        """Set active OCR detection/recognition model keys."""
        try:
            return self._app_state.set_selected_ocr_models(
                detection_model_key,
                recognition_model_key,
            )
        except Exception:
            logger.exception(
                "Error selecting OCR models detection='%s' recognition='%s'",
                detection_model_key,
                recognition_model_key,
            )
            return False

    def command_is_project_available(self, key: str) -> bool:
        """Command to check if a project is available.

        Args:
            key: Project key to check.

        Returns:
            True if project is available, False otherwise.
        """
        return key in self._app_state.available_projects

    def queue_notification(self, message: str, kind: str = "info") -> None:
        """Queue a user-facing notification through the underlying AppState."""
        if self._app_state:
            self._app_state.queue_notification(message, kind)

    def pop_notification(self) -> tuple[str, str] | None:
        """Pop one queued notification for paced UI delivery."""
        if self._app_state:
            return self._app_state.pop_notification()
        return None
