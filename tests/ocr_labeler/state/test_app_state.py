"""
Consolidated tests for AppState.

Includes both basic initialization/property checks and operational/navigation
behavior that was previously split across multiple files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ocr_labeler.state.app_state import AppState


class TestAppState:
    """Basic tests for AppState functionality."""

    def test_app_state_initialization(self):
        """Test that AppState can be instantiated with default values."""
        state = AppState()

        assert state.base_projects_root is None
        assert state.monospace_font_name == "monospace"
        assert state.monospace_font_path is None
        assert state.is_project_loading is False
        assert state.on_change == []
        assert state.project_state is not None

        assert isinstance(state.available_projects, dict)
        assert isinstance(state.project_keys, list)
        assert state.selected_project_key is None or isinstance(
            state.selected_project_key, str
        )

    def test_notify_method(self):
        """Test that notify method works without callback."""
        state = AppState()

        state.notify()

        called = []
        state.on_change.append(lambda: called.append(True))
        state.notify()

        assert len(called) == 1

    def test_is_loading_property(self):
        """Test that is_loading property delegates to project_state."""
        state = AppState()

        assert state.is_loading is False

        state.is_loading = True
        assert state.project_state.is_project_loading is True
        assert state.is_loading is True

    @pytest.mark.asyncio
    async def test_load_project_nonexistent_path(self):
        """Test that loading a nonexistent project raises FileNotFoundError."""
        state = AppState()
        nonexistent_path = Path("/nonexistent/path/to/project")

        with pytest.raises(FileNotFoundError):
            await state.load_project(nonexistent_path)


class DummyProject:
    def __init__(
        self, pages, image_paths, current_page_index, page_loader, ground_truth_map
    ):
        self.pages = pages
        self.image_paths = image_paths
        self.ground_truth_map = ground_truth_map

    def get_page(self, index: int):
        if not self.image_paths or index < 0 or index >= len(self.image_paths):
            return None
        return f"page-{index}"

    def page_count(self) -> int:
        return len(self.image_paths) if self.image_paths else 0


def _ensure_dummy_support_modules(monkeypatch):
    from ocr_labeler.operations.ocr.page_operations import PageOperations
    from ocr_labeler.operations.persistence.project_operations import ProjectOperations

    def fake_load_ground_truth_map(self, directory: Path):
        return {}

    def fake_reload_ground_truth_into_project(self, app_state: AppState):
        pass

    monkeypatch.setattr(
        PageOperations,
        "load_ground_truth_map",
        fake_load_ground_truth_map,
        raising=False,
    )
    monkeypatch.setattr(
        ProjectOperations,
        "reload_ground_truth_into_project",
        fake_reload_ground_truth_into_project,
        raising=False,
    )

    def fake_build_initial_page_parser(self, docTR_predictor=None):
        return object()

    monkeypatch.setattr(
        PageOperations,
        "build_initial_page_parser",
        fake_build_initial_page_parser,
        raising=False,
    )


def _patch_project_vm(monkeypatch):
    import ocr_labeler.state.project_state as proj_state_mod

    class MockProjectOperations:
        def create_project(self, project_dir, image_paths, ground_truth_map=None):
            return DummyProject(
                pages=[None] * len(image_paths),
                image_paths=image_paths,
                current_page_index=0,
                page_loader=object(),
                ground_truth_map=ground_truth_map or {},
            )

        def scan_project_directory(self, project_dir):
            project_path = Path(project_dir)
            image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
            return [
                str(p)
                for p in project_path.iterdir()
                if p.is_file() and p.suffix.lower() in image_extensions
            ]

    monkeypatch.setattr(proj_state_mod, "ProjectOperations", MockProjectOperations)


@pytest.mark.asyncio
async def test_load_project_success_sets_state_and_clears_loading(
    monkeypatch, tmp_path
):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    from ocr_labeler.operations.ocr.page_operations import PageOperations

    def mock_load_ground_truth_map(self, directory):
        return {"img0.png": "GT0"}

    monkeypatch.setattr(
        PageOperations,
        "load_ground_truth_map",
        mock_load_ground_truth_map,
        raising=False,
    )

    (tmp_path / "img0.png").write_bytes(b"")
    (tmp_path / "img1.jpg").write_bytes(b"")

    notifications = []

    state = AppState()
    state.on_change.append(
        lambda: notifications.append((state.is_loading, state.is_project_loading))
    )

    def mock_get_page(index):
        if 0 <= index < len(state.project_state.project.image_paths):
            return f"page-{index}"
        return None

    await state.load_project(tmp_path)

    monkeypatch.setattr(state.project_state, "get_or_load_page_model", mock_get_page)

    assert state.project_state.project_root == tmp_path
    assert isinstance(state.project_state.project, DummyProject)
    assert len(state.project_state.project.image_paths) == 2
    assert state.project_state.current_page_model() == "page-0"
    assert state.is_loading is False
    assert state.is_project_loading is False
    assert len(notifications) >= 2
    assert notifications[0] == (True, True)
    assert notifications[-1] == (False, False)


@pytest.mark.asyncio
async def test_navigation_updates_current_page_and_flags(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    for i in range(3):
        (tmp_path / f"p{i}.png").write_bytes(b"")

    state = AppState()
    await state.load_project(tmp_path)

    def mock_get_page(index):
        if 0 <= index < len(state.project_state.project.image_paths):
            return f"page-{index}"
        return None

    monkeypatch.setattr(state.project_state, "get_or_load_page_model", mock_get_page)

    assert state.project_state.current_page_model() == "page-0"

    def mock_get_running_loop():
        raise RuntimeError("no loop")

    monkeypatch.setattr("asyncio.get_running_loop", mock_get_running_loop)

    state.project_state.next_page()
    assert state.project_state.current_page_model() == "page-1"
    assert state.is_loading is False

    state.project_state.next_page()
    state.project_state.next_page()
    assert state.project_state.current_page_model() == "page-2"

    state.project_state.prev_page()
    assert state.project_state.current_page_model() == "page-1"

    state.project_state.goto_page_number(1)
    assert state.project_state.current_page_model() == "page-0"

    state.project_state.goto_page_number(99)
    assert state.project_state.current_page_model() == "page-0"


def test_reload_ground_truth_invokes_helper(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    from ocr_labeler.operations.persistence.project_operations import ProjectOperations

    called = {}

    def fake_reload(self, app_state):
        called["app_state"] = app_state

    monkeypatch.setattr(
        ProjectOperations,
        "reload_ground_truth_into_project",
        fake_reload,
        raising=False,
    )

    state = AppState()
    state.project_state.reload_ground_truth()
    assert called.get("app_state") is state.project_state


def test_list_available_projects_filters_image_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    base = tmp_path / "ocr" / "data" / "source-pgdp-data" / "output"
    base.mkdir(parents=True)

    projA = base / "projA"
    projA.mkdir()
    (projA / "a.png").write_bytes(b"")

    projB = base / "projB"
    projB.mkdir()
    (projB / "notes.txt").write_text("not an image")

    projC = base / "projC"
    projC.mkdir()
    (projC / "scan.JPG").write_bytes(b"")

    state = AppState()
    result = state.list_available_projects()
    assert set(result.keys()) == {"projA", "projC"}
    assert result["projA"] == projA.resolve()
    assert result["projC"] == projC.resolve()


def test_list_available_projects_missing_base_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    state = AppState()
    assert state.list_available_projects() == {}


def test_notify_invokes_on_change_callback(tmp_path):
    state = AppState()
    calls = []
    state.on_change.append(lambda: calls.append("notified"))
    state.notify()
    assert calls == ["notified"]


@pytest.mark.asyncio
async def test_navigation_triggers_loading_flag_transient(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    (tmp_path / "only.png").write_bytes(b"")
    state = AppState()
    await state.load_project(tmp_path)

    observed = []

    def on_change():
        observed.append(state.is_loading)

    state.on_change.append(on_change)

    def mock_get_running_loop():
        raise RuntimeError("no loop")

    monkeypatch.setattr("asyncio.get_running_loop", mock_get_running_loop)

    state.project_state.next_page()
    assert True in observed
    assert observed[-1] is False


def test_navigate_sync_fallback_sets_flags_and_loads_page(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    state = AppState()

    sentinel_page = object()
    notification_count = 0

    def mock_get_page(index):
        if notification_count > 1:
            return sentinel_page
        return None

    monkeypatch.setattr(state.project_state, "get_or_load_page_model", mock_get_page)

    notifications = []

    def capture_notification():
        nonlocal notification_count
        notification_count += 1
        notifications.append(
            (
                state.is_loading,
                state.is_project_loading,
                state.project_state.current_page_model(),
            )
        )

    state.on_change.append(capture_notification)

    monkeypatch.setattr(
        "asyncio.get_running_loop",
        lambda: (_ for _ in ()).throw(RuntimeError("no loop")),
    )

    state.project_state._navigate()

    assert len(notifications) == 2
    assert notifications[0] == (True, False, None)
    assert notifications[1] == (False, False, sentinel_page)
    assert state.is_loading is False
    assert state.is_project_loading is False
    assert state.project_state.current_page_model() is sentinel_page


def test_navigate_async_path_schedules_task(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    state = AppState()

    sentinel_page = object()
    notification_count = 0

    def mock_get_page(index):
        if notification_count > 1:
            return sentinel_page
        return None

    monkeypatch.setattr(state.project_state, "get_or_load_page_model", mock_get_page)

    notifications = []

    def capture_notification():
        nonlocal notification_count
        notification_count += 1
        notifications.append(
            (
                state.is_loading,
                state.is_project_loading,
                state.project_state.current_page_model(),
            )
        )

    state.on_change.append(capture_notification)

    task_created = False

    def mock_background_create(coro):
        nonlocal task_created
        task_created = True
        try:
            coro.close()
        except Exception:
            pass

    monkeypatch.setattr("nicegui.background_tasks.create", mock_background_create)

    state.project_state._navigate()

    assert task_created
    assert len(notifications) == 1
    assert notifications[0] == (True, False, None)
    assert state.is_loading is True
    assert state.is_project_loading is False
    assert state.project_state.current_page_model() is None
