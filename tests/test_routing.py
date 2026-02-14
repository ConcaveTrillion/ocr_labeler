"""Tests for URL routing utilities and route initialization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ocr_labeler.routing import (
    build_project_url,
    resolve_project_path,
    sync_url_from_project_state,
    sync_url_to_state,
)


class TestBuildProjectUrl:
    """Tests for build_project_url."""

    def test_project_only_default_page(self):
        """When page_index is 0 (default), returns /project/{key}/page/1."""
        url = build_project_url("my_project")
        assert url == "/project/my_project/page/1"

    def test_project_with_page_zero_explicit(self):
        """When page_index is explicitly 0, returns /project/{key}/page/1."""
        url = build_project_url("my_project", page_index=0)
        assert url == "/project/my_project/page/1"

    def test_project_with_page_nonzero(self):
        """When page_index > 0, returns /project/{key}/page/{index+1} (1-based)."""
        url = build_project_url("my_project", page_index=5)
        assert url == "/project/my_project/page/6"

    def test_project_with_page_one(self):
        """Page index 1 includes the page component with 1-based number."""
        url = build_project_url("proj", page_index=1)
        assert url == "/project/proj/page/2"

    def test_special_characters_in_project_key(self):
        """Project keys with special chars are included as-is."""
        url = build_project_url("projectID629292e7559a8", page_index=3)
        assert url == "/project/projectID629292e7559a8/page/4"


class TestResolveProjectPath:
    """Tests for resolve_project_path."""

    def test_resolve_under_base_projects_root(self, tmp_path: Path):
        """Should find a project directory under base_projects_root."""
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()

        result = resolve_project_path("my_project", base_projects_root=tmp_path)
        assert result is not None
        assert result.resolve() == project_dir.resolve()

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Should resolve an absolute path directly."""
        project_dir = tmp_path / "abs_project"
        project_dir.mkdir()

        result = resolve_project_path(str(project_dir), base_projects_root=None)
        assert result is not None
        assert result.resolve() == project_dir.resolve()

    def test_resolve_nonexistent_returns_none(self, tmp_path: Path):
        """Should return None when project doesn't exist anywhere."""
        result = resolve_project_path(
            "nonexistent_project_xyz", base_projects_root=tmp_path
        )
        assert result is None

    def test_resolve_relative_to_cwd(self, tmp_path: Path, monkeypatch):
        """Should resolve relative to CWD."""
        project_dir = tmp_path / "cwd_project"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        result = resolve_project_path("cwd_project", base_projects_root=None)
        assert result is not None
        assert result.resolve() == project_dir.resolve()

    def test_resolve_file_not_dir_returns_none(self, tmp_path: Path):
        """Should not resolve a file (only directories)."""
        file_path = tmp_path / "not_a_dir"
        file_path.touch()

        result = resolve_project_path("not_a_dir", base_projects_root=tmp_path)
        assert result is None

    def test_resolve_prefers_absolute_over_base(self, tmp_path: Path):
        """Absolute paths should be preferred over base_projects_root."""
        abs_dir = tmp_path / "abs"
        abs_dir.mkdir()
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        (base_dir / "abs").mkdir()

        result = resolve_project_path(str(abs_dir), base_projects_root=base_dir)
        assert result is not None
        assert result.resolve() == abs_dir.resolve()

    def test_resolve_with_none_base_projects_root(self, tmp_path: Path, monkeypatch):
        """When base_projects_root is None, still tries CWD."""
        project_dir = tmp_path / "no_base"
        project_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        result = resolve_project_path("no_base", base_projects_root=None)
        assert result is not None
        assert result.resolve() == project_dir.resolve()

    def test_resolve_from_available_projects(self, tmp_path: Path):
        """Should resolve from available_projects dict first."""
        project_dir = tmp_path / "discovered_project"
        project_dir.mkdir()
        available = {"discovered_project": project_dir}

        result = resolve_project_path(
            "discovered_project",
            base_projects_root=None,
            available_projects=available,
        )
        assert result is not None
        assert result.resolve() == project_dir.resolve()

    def test_resolve_available_projects_preferred_over_cwd(
        self, tmp_path: Path, monkeypatch
    ):
        """available_projects should be checked before CWD."""
        # Create project in both CWD and available_projects with different paths
        cwd_dir = tmp_path / "cwd_root"
        cwd_dir.mkdir()
        (cwd_dir / "my_proj").mkdir()

        other_dir = tmp_path / "other_root" / "my_proj"
        other_dir.mkdir(parents=True)

        monkeypatch.chdir(cwd_dir)
        available = {"my_proj": other_dir}

        result = resolve_project_path(
            "my_proj", base_projects_root=None, available_projects=available
        )
        assert result is not None
        assert result.resolve() == other_dir.resolve()


class TestSyncUrlToState:
    """Tests for sync_url_to_state."""

    @patch("ocr_labeler.routing.ui")
    def test_sync_with_project_and_page(self, mock_ui):
        """Should call history.replace with correct URL."""
        state = MagicMock()
        state.current_project_key = "test_project"
        mock_project_state = MagicMock()
        mock_project_state.current_page_index = 3
        state.projects = {"test_project": mock_project_state}

        sync_url_to_state(state)

        mock_ui.navigate.history.replace.assert_called_once_with(
            "/project/test_project/page/4"
        )

    @patch("ocr_labeler.routing.ui")
    def test_sync_with_project_page_zero(self, mock_ui):
        """When page index is 0, URL should include /page/1."""
        state = MagicMock()
        state.current_project_key = "proj"
        mock_project_state = MagicMock()
        mock_project_state.current_page_index = 0
        state.projects = {"proj": mock_project_state}

        sync_url_to_state(state)

        mock_ui.navigate.history.replace.assert_called_once_with("/project/proj/page/1")

    @patch("ocr_labeler.routing.ui")
    def test_sync_no_project_key_does_nothing(self, mock_ui):
        """When no project is loaded, should not update URL."""
        state = MagicMock()
        state.current_project_key = None

        sync_url_to_state(state)

        mock_ui.navigate.history.replace.assert_not_called()

    @patch("ocr_labeler.routing.ui")
    def test_sync_project_key_not_in_projects(self, mock_ui):
        """When project key exists but not in projects dict, page defaults to 0."""
        state = MagicMock()
        state.current_project_key = "orphan"
        state.projects = {}

        sync_url_to_state(state)

        mock_ui.navigate.history.replace.assert_called_once_with(
            "/project/orphan/page/1"
        )

    @patch("ocr_labeler.routing.ui")
    def test_sync_handles_exception_gracefully(self, mock_ui):
        """Should not raise on error; should log and continue."""
        mock_ui.navigate.history.replace.side_effect = RuntimeError("no websocket")
        state = MagicMock()
        state.current_project_key = "proj"
        state.projects = {}

        # Should not raise
        sync_url_to_state(state)


class TestSyncUrlFromProjectState:
    """Tests for sync_url_from_project_state."""

    @patch("ocr_labeler.routing.ui")
    def test_sync_with_root_and_index(self, mock_ui):
        """Should build URL from project root name and page index (1-based in URL)."""
        project_root = Path("/some/path/my_project")
        sync_url_from_project_state(project_root, 5)

        mock_ui.navigate.history.replace.assert_called_once_with(
            "/project/my_project/page/6"
        )

    @patch("ocr_labeler.routing.ui")
    def test_sync_with_none_root_does_nothing(self, mock_ui):
        """When project_root is None, should not update URL."""
        sync_url_from_project_state(None, 0)

        mock_ui.navigate.history.replace.assert_not_called()

    @patch("ocr_labeler.routing.ui")
    def test_sync_index_zero_no_page_component(self, mock_ui):
        """Page index 0 should produce /page/1."""
        project_root = Path("/home/user/projects/proj1")
        sync_url_from_project_state(project_root, 0)

        mock_ui.navigate.history.replace.assert_called_once_with(
            "/project/proj1/page/1"
        )

    @patch("ocr_labeler.routing.ui")
    def test_sync_handles_exception_gracefully(self, mock_ui):
        """Should not raise on error."""
        mock_ui.navigate.history.replace.side_effect = RuntimeError("boom")
        project_root = Path("/x/y")

        # Should not raise
        sync_url_from_project_state(project_root, 0)
