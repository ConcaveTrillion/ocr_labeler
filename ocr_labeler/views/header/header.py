from nicegui import ui

from ...models.app_state_nicegui_binding import AppStateNiceGuiBinding
from ...models.project_state_nicegui_binding import ProjectStateNiceGuiBinding
from .project_load_controls import ProjectLoadControls


class HeaderBar:
    """Top header containing project load controls only."""

    def __init__(
        self,
        app_state_model: AppStateNiceGuiBinding,
        project_state_model: ProjectStateNiceGuiBinding,
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
