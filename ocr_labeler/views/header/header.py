from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ..shared.base_view import BaseView
from .project_load_controls import ProjectLoadControls

if TYPE_CHECKING:
    from ...viewmodels.main_view_model import MainViewModel


class HeaderBar(BaseView["MainViewModel"]):
    """Top header containing project load controls only."""

    def __init__(self, viewmodel: MainViewModel):
        """Initialize the header bar with its view model.

        Args:
            viewmodel: The main view model containing app and project state.
        """
        super().__init__(viewmodel)
        self.project_controls = ProjectLoadControls(
            viewmodel.app_state_view_model, viewmodel.project_state_view_model
        )

    def build(self):
        """Build the header UI components."""
        with ui.header().classes("p-2 flex flex-col gap-2") as self._root:
            self.project_controls.build()
        self.mark_as_built()
        return self._root

    def refresh(self):
        """Refresh the header based on current view model state."""
        # Header content is mostly static, but we could refresh controls if needed
        pass
