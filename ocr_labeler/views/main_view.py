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
        self._project_loading_overlay = None
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

        # Global project-loading overlay (blur + centered text/spinner)
        self._project_loading_overlay = (
            ui.column()
            .classes(
                "fixed inset-0 bg-black/30 backdrop-blur-sm z-40 items-center justify-center gap-3 hidden"
            )
            .mark("project-loading-overlay")
        )
        with self._project_loading_overlay:
            ui.spinner(size="xl", color="primary")
            self._project_loading_label = ui.label("Loading project...").classes(
                "text-white text-lg font-semibold"
            )

        # Set up data bindings
        if self.viewmodel.app_state_viewmodel:
            self._no_project_placeholder.bind_visibility_from(
                target_object=self.viewmodel,
                target_name="show_placeholder",
            )

            self._project_loading_overlay.bind_visibility_from(
                target_object=self.viewmodel.app_state_viewmodel,
                target_name="is_project_loading",
                value=True,
            )

            # Update loading label with selected project key/path
            try:
                self._project_loading_label.bind_text_from(
                    target_object=self.viewmodel.app_state_viewmodel,
                    target_name="loading_message",
                )
            except Exception:
                logger.debug("Failed to bind project loading label", exc_info=True)

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

        # If the loaded project's root changed, drop the existing ProjectView so it rebuilds cleanly
        if (
            self.project_view
            and hasattr(self.project_view, "project_root_snapshot")
            and self.project_view.project_root_snapshot
            != getattr(self.viewmodel.project_state_viewmodel, "project_root", None)
        ):
            try:
                if getattr(self.project_view, "_root", None):
                    self.project_view._root.delete()
            except Exception:
                logger.debug("Failed to delete old ProjectView root", exc_info=True)
            self.project_view = None
            logger.debug("Project root changed; rebuilding ProjectView")

        if show_project_view and not self.project_view and self._content_container:
            # Create project view if needed
            logger.debug("Creating ProjectView for loaded project")
            with self._content_container:
                self.project_view = ProjectView(self.viewmodel.project_state_viewmodel)
                self.project_view.build()
                # Bind project view visibility to show_project_view
                if hasattr(self.project_view, "_root") and self.project_view._root:
                    self.project_view._root.bind_visibility_from(
                        target_object=self.viewmodel,
                        target_name="show_project_view",
                    )
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
            and self.project_view.is_built
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
