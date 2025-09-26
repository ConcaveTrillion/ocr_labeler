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
            self.has_project = (
                bool(self.app_state_viewmodel.selected_project_key)
                and self.app_state_viewmodel.is_project_loaded
                and self.project_state_viewmodel.page_total > 0
            )

            # Update view visibility
            self.show_project_view = self.has_project
            self.show_placeholder = not self.has_project

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
