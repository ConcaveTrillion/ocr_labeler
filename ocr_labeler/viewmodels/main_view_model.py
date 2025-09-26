"""Main view model for the application orchestrating app and project view models."""

import logging
from typing import Optional

from nicegui import binding

from ..state import AppState
from .app.app_state_view_model import AppStateViewModel
from .project.project_state_view_model import ProjectStateViewModel
from .shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class MainViewModel(BaseViewModel):
    """Main view model that orchestrates the entire application UI state."""

    # Child view models
    app_state_viewmodel: Optional[AppStateViewModel] = None
    project_state_viewmodel: Optional[ProjectStateViewModel] = None

    # UI-bound properties for main view
    has_project: bool = False
    show_project_view: bool = False
    show_placeholder: bool = True

    def __init__(self, app_state: AppState):
        """Initialize the main view model.

        Args:
            app_state: The application state.
        """
        logger.debug("Initializing MainViewModel")

        # Create child view models
        self.app_state_viewmodel = AppStateViewModel(app_state)
        self.project_state_viewmodel = ProjectStateViewModel(
            app_state.project_state, self.app_state_viewmodel
        )

        # Initialize base class
        super().__init__()

        # Update child view models to ensure they have initial state
        self.app_state_viewmodel.update()
        self.project_state_viewmodel.update()

        # Set up listeners for child view model changes
        self.app_state_viewmodel.add_property_changed_listener(
            self._on_app_state_changed
        )
        self.project_state_viewmodel.add_property_changed_listener(
            self._on_project_state_changed
        )

        # Initial update of derived properties
        self._update_derived_properties()

        logger.debug("MainViewModel initialized")

    def _on_app_state_changed(self, property_name: str, value):
        """Handle app state view model property changes."""
        logger.debug(f"App state changed: {property_name} = {value}")

        # Update derived properties when relevant app state changes
        if property_name in [
            "selected_project_key",
            "is_project_loaded",
            "is_project_loading",
        ]:
            self._update_derived_properties()

        # Update project state view model when current project changes
        if property_name == "is_project_loaded" and value and self.app_state_viewmodel:
            # When a project is loaded, update the project state view model to point to the current project state
            current_project_state = self.app_state_viewmodel._app_state.project_state
            if current_project_state != self.project_state_viewmodel._project_state:
                logger.debug(
                    "Updating project state view model to point to loaded project"
                )
                # Update the underlying project state reference
                self.project_state_viewmodel._project_state = current_project_state
                # Re-register the change listener
                current_project_state.on_change.append(
                    self.project_state_viewmodel._on_project_state_change
                )
                # Update the view model
                self.project_state_viewmodel.update()
                # Update derived properties again now that project state view model is updated
                self._update_derived_properties()

    def _on_project_state_changed(self, property_name: str, value):
        """Handle project state view model property changes."""
        logger.debug(f"Project state changed: {property_name} = {value}")

        # Update derived properties when relevant project state changes
        if property_name in ["page_total", "current_page_index"]:
            self._update_derived_properties()

    def _update_derived_properties(self):
        """Update properties derived from child view models."""
        if self.app_state_viewmodel and self.project_state_viewmodel:
            # Check if we have a project loaded
            new_has_project = (
                bool(self.app_state_viewmodel.selected_project_key)
                and self.app_state_viewmodel.is_project_loaded
                and self.project_state_viewmodel.page_total > 0
            )

            # Update view visibility
            new_show_project_view = new_has_project
            new_show_placeholder = not new_has_project

            # Track old values safely (avoid accessing bindable properties during init)
            try:
                old_has_project = self.has_project
                old_show_project_view = self.show_project_view
                old_show_placeholder = self.show_placeholder
            except AttributeError:
                # During initialization, properties might not be accessible yet
                old_has_project = None
                old_show_project_view = None
                old_show_placeholder = None

            # Update properties
            self.has_project = new_has_project
            self.show_project_view = new_show_project_view
            self.show_placeholder = new_show_placeholder

            # Notify listeners of property changes only if values actually changed
            if old_has_project is not None and old_has_project != self.has_project:
                self.notify_property_changed("has_project", self.has_project)
            if (
                old_show_project_view is not None
                and old_show_project_view != self.show_project_view
            ):
                self.notify_property_changed(
                    "show_project_view", self.show_project_view
                )
            if (
                old_show_placeholder is not None
                and old_show_placeholder != self.show_placeholder
            ):
                self.notify_property_changed("show_placeholder", self.show_placeholder)

            logger.debug(
                f"Updated derived properties: has_project={self.has_project}, "
                f"show_project_view={self.show_project_view}, "
                f"show_placeholder={self.show_placeholder}"
            )

    # Delegate commands to appropriate child view models

    def command_select_project(self, key: str) -> bool:
        """Delegate project selection to app state view model."""
        if self.app_state_viewmodel:
            return self.app_state_viewmodel.command_select_project(key)
        return False

    async def command_load_selected_project(self) -> bool:
        """Delegate project loading to app state view model."""
        if self.app_state_viewmodel:
            return await self.app_state_viewmodel.command_load_selected_project()
        return False

    def command_navigate_to_page(self, page_index: int) -> bool:
        """Delegate page navigation to project state view model."""
        if self.project_state_viewmodel:
            return self.project_state_viewmodel.command_navigate_to_page(page_index)
        return False

    def command_navigate_next(self) -> bool:
        """Delegate next navigation to project state view model."""
        if self.project_state_viewmodel:
            return self.project_state_viewmodel.command_navigate_next()
        return False

    def command_navigate_prev(self) -> bool:
        """Delegate previous navigation to project state view model."""
        if self.project_state_viewmodel:
            return self.project_state_viewmodel.command_navigate_prev()
        return False

    def command_get_project_display_name(self, key: Optional[str] = None) -> str:
        """Delegate project display name to app state view model."""
        if self.app_state_viewmodel:
            return self.app_state_viewmodel.command_get_project_display_name(key)
        return ""

    def command_is_project_available(self, key: str) -> bool:
        """Delegate project availability check to app state view model."""
        if self.app_state_viewmodel:
            return self.app_state_viewmodel.command_is_project_available(key)
        return False

    def command_get_page_display_info(self, page_index: Optional[int] = None) -> dict:
        """Delegate page display info to project state view model."""
        if self.project_state_viewmodel:
            return self.project_state_viewmodel.command_get_page_display_info(
                page_index
            )
        return {}

    def command_get_navigation_status(self) -> dict:
        """Delegate navigation status to project state view model."""
        if self.project_state_viewmodel:
            return self.project_state_viewmodel.command_get_navigation_status()
        return {}
