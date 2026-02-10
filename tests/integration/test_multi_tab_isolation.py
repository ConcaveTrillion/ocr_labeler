"""Integration tests for multi-tab session isolation."""

from pathlib import Path

import pytest

from ocr_labeler.app import NiceGuiLabeler
from ocr_labeler.state.app_state import AppState


class TestMultiTabIsolation:
    """Test that multiple tabs/sessions maintain independent state."""

    @pytest.fixture
    def test_projects_root(self) -> Path:
        """Return the path to the test projects directory."""
        return Path(__file__).parent.parent / "test-data" / "pgdp-projects"

    def test_multiple_app_state_instances_are_independent(
        self, test_projects_root: Path
    ):
        """Test that creating multiple AppState instances maintains independence."""
        # Simulate two browser tabs creating their own states
        state1 = AppState(base_projects_root=test_projects_root)
        state2 = AppState(base_projects_root=test_projects_root)

        # They should be different instances
        assert state1 is not state2

        # Modifying one should not affect the other
        state1.selected_project_key = "project1"
        state2.selected_project_key = "project2"

        assert state1.selected_project_key == "project1"
        assert state2.selected_project_key == "project2"

    def test_loading_projects_in_separate_states_maintains_isolation(
        self, test_projects_root: Path
    ):
        """Test that loading projects in separate states doesn't cause interference."""
        state1 = AppState(base_projects_root=test_projects_root)
        state2 = AppState(base_projects_root=test_projects_root)

        # Each state should have its own projects dict
        assert state1.projects is not state2.projects
        assert len(state1.projects) == 0
        assert len(state2.projects) == 0

        # Set different loading states
        state1.is_project_loading = True
        state2.is_project_loading = False

        assert state1.is_project_loading is True
        assert state2.is_project_loading is False

    def test_app_creates_isolated_instances_per_route_call(
        self, test_projects_root: Path
    ):
        """Test that the app's route handler creates isolated instances.

        This simulates what happens when multiple browser tabs open the app.
        Each call to the @ui.page("/") decorated function should create
        fresh state instances.
        """
        # Create the app (simulates server startup)
        app = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )

        # The app itself should not have state/viewmodel/view attributes
        # (they're created per-session in the route handler)
        assert not hasattr(app, "state") or app.__dict__.get("state") is None
        assert not hasattr(app, "viewmodel") or app.__dict__.get("viewmodel") is None
        assert not hasattr(app, "view") or app.__dict__.get("view") is None

        # The app should only have configuration
        assert app.project_root == test_projects_root
        assert app.projects_root == test_projects_root

    def test_default_project_state_isolation(self, test_projects_root: Path):
        """Test that _default_project_state is not shared across AppState instances."""
        state1 = AppState(base_projects_root=test_projects_root)
        state2 = AppState(base_projects_root=test_projects_root)

        # Access project_state on both (triggers lazy initialization)
        ps1 = state1.project_state
        ps2 = state2.project_state

        # They should be different instances
        assert ps1 is not ps2

        # Modifying one should not affect the other
        ps1.current_page_index = 5
        ps2.current_page_index = 10

        assert state1.project_state.current_page_index == 5
        assert state2.project_state.current_page_index == 10
