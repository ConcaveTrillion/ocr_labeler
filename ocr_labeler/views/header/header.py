from nicegui import ui

from ...state import AppState
from .project_load_controls import ProjectLoadControls


class HeaderBar:
    """Top header containing project load controls only."""

    def __init__(self, state: AppState):
        self.state = state
        self.project_controls = ProjectLoadControls(state)
        self.header = None

    def build(self):
        with ui.header().classes("p-2 flex flex-col gap-2") as header:
            self.header = header
            self.project_controls.build()
        # Populate after construction
        self.project_controls.populate()
        return header
