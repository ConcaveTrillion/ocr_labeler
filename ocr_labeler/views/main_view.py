from __future__ import annotations

import logging

from nicegui import ui

from ..viewmodels.main_view_model import MainViewModel
from .header.header import HeaderBar
from .projects.project_view import ProjectView
from .shared.base_view import BaseView

logger = logging.getLogger(__name__)


class LabelerView(BaseView[MainViewModel]):  # pragma: no cover - heavy UI wiring
    """High-level app view orchestrating header and conditional project view."""

    def __init__(self, viewmodel: MainViewModel):
        """Initialize the labeler view with its view model.

        Args:
            viewmodel: The main view model for the application.
        """
        logger.debug("Initializing LabelerView with MainViewModel")
        super().__init__(viewmodel)

        self.header_bar: HeaderBar | None = None
        self.project_view: ProjectView | None = None
        self._main_container = None
        self._content_container = None
        self._no_project_placeholder = None
        self._global_loading = None
        logger.debug("LabelerView initialization complete")

    def build(self):
        """Build the main application UI components."""
        logger.debug("Building LabelerView components")

        # Header must be a top-level layout element (direct child of page)
        self.header_bar = HeaderBar(self.viewmodel)
        self.header_bar.build()
        logger.debug("Header bar built")

        # Main content container (below header)
        self._main_container = ui.column().classes("w-full flex-1 flex flex-col")

        with self._main_container:
            # Content area container (where project view or placeholder goes)
            self._content_container = ui.column().classes("w-full flex-1 flex flex-col")

            with self._content_container:
                # Placeholder shown before any project has been loaded
                self._no_project_placeholder = ui.column().classes(
                    "w-full h-[calc(100vh-160px)] items-center justify-center text-gray-500 gap-2"
                )
                with self._no_project_placeholder:  # type: ignore
                    ui.icon("folder_open").classes("text-4xl opacity-40")
                    ui.label("No Project Loaded").classes("text-lg font-medium")
                    ui.label("Select a project above and click LOAD to begin.")

        logger.debug("Content containers and placeholder built")

        # Global project-loading spinner (centered overlay)
        self._global_loading = (
            ui.spinner(size="xl")
            .props("color=primary")
            .classes(
                "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-40 pointer-events-none hidden"
            )
        )

        # Set up data bindings
        if self.viewmodel.app_state_viewmodel:
            self._no_project_placeholder.bind_visibility_from(
                target_object=self.viewmodel.app_state_viewmodel,
                target_name="selected_project_key",
                value="",
            )

            self._global_loading.bind_visibility_from(
                target_object=self.viewmodel.app_state_viewmodel,
                target_name="is_project_loading",
                value=True,
            )

        logger.debug("Data bindings configured")
        self.mark_as_built()
        self.refresh()
        logger.debug("LabelerView building complete")

        return self._main_container

    def refresh(self):
        """Refresh the view based on current view model state."""
        logger.debug("Refreshing LabelerView")

        if not self.is_built:
            logger.warning("Cannot refresh LabelerView before it is built")
            return

        # Show/hide project view vs placeholder based on view model state
        show_project_view = self.viewmodel.show_project_view
        logger.debug(
            f"Show project view: {show_project_view}, ProjectView exists: {self.project_view is not None}"
        )

        if show_project_view and not self.project_view and self._content_container:
            # Create project view if needed
            logger.debug("Creating ProjectView for loaded project")
            with self._content_container:
                self.project_view = ProjectView(self.viewmodel.project_state_viewmodel)
                self.project_view.build()
            logger.debug("ProjectView created and built during refresh")
        elif self.project_view and not show_project_view:
            # Hide project view if no project
            logger.debug(
                "Project unloaded, keeping ProjectView instance for potential reuse"
            )
            pass

        # Refresh project view if it exists and not loading
        if (
            self.project_view
            and self.viewmodel.app_state_viewmodel
            and not self.viewmodel.app_state_viewmodel.is_project_loading
        ):
            logger.debug("Refreshing existing ProjectView")
            self.project_view.refresh()

        logger.debug("LabelerView refresh complete")

    def _on_viewmodel_property_changed(self, property_name: str, value):
        """Handle view model property changes."""
        logger.debug(
            f"LabelerView handling viewmodel property change: {property_name} = {value}"
        )

        # Refresh when relevant properties change
        if property_name in ["show_project_view", "show_placeholder", "has_project"]:
            self.refresh()
