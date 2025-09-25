from __future__ import annotations

import logging

from nicegui import ui

from ..models.app_state_nicegui_binding import AppStateNiceGuiBinding
from ..models.project_state_nicegui_binding import ProjectStateNiceGuiBinding
from ..state import AppState
from .header.header import HeaderBar
from .projects.project_view import ProjectView

logger = logging.getLogger(__name__)


class LabelerView:  # pragma: no cover - heavy UI wiring
    """High-level app view orchestrating header and conditional project view."""

    def __init__(self, state: AppState):
        logger.debug("Initializing LabelerView with AppState")
        self.state = state
        self.state_model: AppStateNiceGuiBinding = AppStateNiceGuiBinding(self.state)
        self.project_state_model: ProjectStateNiceGuiBinding = (
            ProjectStateNiceGuiBinding(self.state.project_state)
        )
        logger.debug("AppStateNiceGuiBinding created and linked to AppState")
        logger.debug("ProjectStateNiceGuiBinding created and linked to ProjectState")

        self.header_bar: HeaderBar | None = None
        self.project_view: ProjectView | None = None
        self._main_container = None
        self._content_container = None
        self._no_project_placeholder = None
        self._global_loading = None
        logger.debug("LabelerView initialization complete")

    # ------------------------------------------------------------ mount
    def mount(self):
        logger.debug("Mounting LabelerView components")
        # Header must be a top-level layout element (direct child of page)
        self.header_bar = HeaderBar(self.state_model, self.project_state_model)
        self.header_bar.build()
        logger.debug("Header bar mounted")

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

        logger.debug("Content containers and placeholder mounted")

        # Global project-loading spinner (centered overlay)
        self._global_loading = (
            ui.spinner(size="xl")
            .props("color=primary")
            .classes(
                "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-40 pointer-events-none hidden"
            )
        )

        self._no_project_placeholder.bind_visibility_from(
            target_object=self.state_model, target_name="selected_project_key", value=""
        )

        self._global_loading.bind_visibility_from(
            target_object=self.state_model, target_name="is_project_loading", value=True
        )

        logger.debug("Global loading spinner and bindings configured")
        self.refresh()
        logger.debug("LabelerView mounting complete")

    # ------------------------------------------------------------ refresh
    def refresh(self):
        logger.debug("Refreshing LabelerView")
        project_loading = self.state.is_project_loading
        logger.debug(f"Project loading state: {project_loading}")

        # Show/hide project view vs placeholder
        has_project = bool(getattr(self.state.project_state.project, "image_paths", []))
        logger.debug(
            f"Has project: {has_project}, ProjectView exists: {self.project_view is not None}"
        )

        if has_project and not self.project_view and self._content_container:
            # Create project view if project exists but view doesn't
            logger.debug("Creating ProjectView for loaded project")
            with self._content_container:
                self.project_view = ProjectView(self.state.project_state)
                self.project_view.build()
            logger.debug("ProjectView created and built during refresh")
        elif self.project_view and not has_project:
            # Hide project view if no project
            # Note: We keep the instance but let refresh handle visibility
            logger.debug(
                "Project unloaded, keeping ProjectView instance for potential reuse"
            )
            pass

        # Refresh project view if it exists
        if self.project_view:
            logger.debug("Refreshing existing ProjectView")
            self.project_view.refresh()

        # Placeholder visibility is now handled by binding to state_model.selected_project_key
        # No manual management needed here

        logger.debug("LabelerView refresh complete")
