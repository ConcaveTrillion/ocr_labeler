from nicegui import ui

from ...viewmodels.app.app_state_view_model import AppStateViewModel
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from .project_load_controls import ProjectLoadControls


class HeaderBar:
    """Top header containing project load controls only."""

    def __init__(
        self,
        app_state_model: AppStateViewModel,
        project_state_model: ProjectStateViewModel,
    ):
        self.app_state_model = app_state_model
        self.project_state_model = project_state_model
        self.project_controls = ProjectLoadControls(
            app_state_model, project_state_model
        )
        self.header = None

    def build(self):
        with ui.header().classes("p-2 flex flex-col gap-2") as header:
            self.header = header
            self.project_controls.build()
        return header
