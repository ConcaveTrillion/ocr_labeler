from __future__ import annotations

import asyncio  # noqa: F401 - used in monkeypatch
from pathlib import Path

import pytest

from ocr_labeler.state.app_state import AppState

# ocr_labeler/state/test_app_state.py


# Relative import of the code under test

# ------------------------
# Test doubles / utilities
# ------------------------


class DummyProject:
    def __init__(
        self, pages, image_paths, current_page_index, page_loader, ground_truth_map
    ):
        self.pages = pages
        self.image_paths = image_paths
        self.ground_truth_map = ground_truth_map

    # Methods expected by new Project API
    def get_page(self, index: int):
        if not self.image_paths or index < 0 or index >= len(self.image_paths):
            return None
        return f"page-{index}"

    def page_count(self) -> int:
        return len(self.image_paths) if self.image_paths else 0


def _ensure_dummy_support_modules(monkeypatch):
    """
    Ensure page_operations modules exist and patch their functions.
    This accommodates either real modules (patched) or absence (dummy injected).
    """
    # Import the operations classes for patching
    from ocr_labeler.operations.ocr.page_operations import PageOperations
    from ocr_labeler.operations.persistence.project_operations import ProjectOperations

    def fake_load_ground_truth_map(self, directory: Path):
        # Return simple mapping for deterministic behavior
        return {}

    # Placeholder; will be overridden in specific test where needed
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

    # page_operations module - mock build_initial_page_parser method
    def fake_build_initial_page_parser(self, docTR_predictor=None):
        return object()

    monkeypatch.setattr(
        PageOperations,
        "build_initial_page_parser",
        fake_build_initial_page_parser,
        raising=False,
    )


def _patch_project_vm(monkeypatch):
    """Mock ProjectOperations to return DummyProject instead of real Project"""
    import ocr_labeler.state.project_state as proj_state_mod

    # Create a mock ProjectOperations class
    class MockProjectOperations:
        async def create_project(self, project_dir, image_paths, ground_truth_map=None):
            return DummyProject(
                pages=[None]
                * len(image_paths),  # Create pages list to match image_paths
                image_paths=image_paths,
                current_page_index=0,
                page_loader=object(),  # Mock page loader
                ground_truth_map=ground_truth_map or {},
            )

        async def scan_project_directory(self, project_dir):
            # Return the image files from the directory
            from pathlib import Path

            project_path = Path(project_dir)
            image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
            return [
                str(p)
                for p in project_path.iterdir()
                if p.is_file() and p.suffix.lower() in image_extensions
            ]

    # Patch the import in project_state module
    monkeypatch.setattr(proj_state_mod, "ProjectOperations", MockProjectOperations)


# ------------- Tests --------------


@pytest.mark.asyncio
async def test_load_project_success_sets_state_and_clears_loading(
    monkeypatch, tmp_path
):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Add specific ground truth mapping (override for this test)
    # Since ground truth is now in PageOperations, mock it there
    from ocr_labeler.operations.ocr.page_operations import PageOperations

    def mock_load_ground_truth_map(self, directory):
        return {"img0.png": "GT0"}

    monkeypatch.setattr(
        PageOperations,
        "load_ground_truth_map",
        mock_load_ground_truth_map,
        raising=False,
    )

    # Create image files
    (tmp_path / "img0.png").write_bytes(b"")
    (tmp_path / "img1.jpg").write_bytes(b"")

    # Track notifications
    notifications = []

    state = AppState()
    state.on_change.append(
        lambda: notifications.append((state.is_loading, state.is_project_loading))
    )

    # Mock ProjectState.get_page to return expected string format
    def mock_get_page(index):
        if 0 <= index < len(state.project_state.project.image_paths):
            return f"page-{index}"
        return None

    await state.load_project(tmp_path)

    # Apply the mock after load_project creates the project_state
    monkeypatch.setattr(state.project_state, "get_page", mock_get_page)

    assert state.project_state.project_root == tmp_path
    # DummyProject attributes
    assert isinstance(state.project_state.project, DummyProject)
    assert len(state.project_state.project.image_paths) == 2
    assert state.project_state.current_page() == "page-0"
    assert state.is_loading is False
    assert state.is_project_loading is False
    # Expect at least two notifications: entering & leaving loading phase
    # (may have more due to project state notifications)
    assert len(notifications) >= 2
    assert notifications[0] == (True, True)  # start project load
    assert notifications[-1] == (False, False)  # end project load


@pytest.mark.asyncio
async def test_load_project_nonexistent_directory_raises(tmp_path):
    state = AppState()
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        await state.load_project(missing)
    # Flags should remain default
    assert state.is_loading is False
    assert state.is_project_loading is False


@pytest.mark.asyncio
async def test_navigation_updates_current_page_and_flags(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Three images
    for i in range(3):
        (tmp_path / f"p{i}.png").write_bytes(b"")

    state = AppState()
    await state.load_project(tmp_path)

    # Mock ProjectState.get_page to return expected string format
    def mock_get_page(index):
        if 0 <= index < len(state.project_state.project.image_paths):
            return f"page-{index}"
        return None

    monkeypatch.setattr(state.project_state, "get_page", mock_get_page)

    # Initial
    assert state.project_state.current_page() == "page-0"

    # Mock asyncio to force synchronous behavior for this test
    def mock_get_running_loop():
        raise RuntimeError("no loop")  # Force synchronous fallback

    monkeypatch.setattr("asyncio.get_running_loop", mock_get_running_loop)

    state.project_state.next_page()
    assert state.project_state.current_page() == "page-1"
    assert state.is_loading is False  # synchronous fallback path

    state.project_state.next_page()
    state.project_state.next_page()  # attempt to move beyond end
    assert state.project_state.current_page() == "page-2"

    state.project_state.prev_page()
    assert state.project_state.current_page() == "page-1"

    state.project_state.goto_page_number(1)  # 1-based page number -> index 0
    assert state.project_state.current_page() == "page-0"

    # Out-of-range should not change index
    state.project_state.goto_page_number(99)
    assert state.project_state.current_page() == "page-0"


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
    # Redirect HOME so that the function's fixed path resolves under tmp_path
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
    # Do NOT create the base path
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
    """
    Verify that is_loading is set True inside navigation and ends False after synchronous load.
    """
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    (tmp_path / "only.png").write_bytes(b"")
    state = AppState()
    await state.load_project(tmp_path)

    observed = []

    def on_change():
        observed.append(state.is_loading)

    state.on_change.append(on_change)

    # Mock asyncio to force synchronous behavior for this test
    def mock_get_running_loop():
        raise RuntimeError("no loop")  # Force synchronous fallback

    monkeypatch.setattr("asyncio.get_running_loop", mock_get_running_loop)

    state.project_state.next_page()  # Will attempt to go beyond end; index unchanged but navigation path runs
    # Expect at least two observations: loading True then False
    assert True in observed
    assert observed[-1] is False


def test_navigate_sync_fallback_sets_flags_and_loads_page(monkeypatch, tmp_path):
    """Test _navigate in sync fallback path (no event loop): sets loading flags, calls nav_callable, loads page synchronously, clears flags."""
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Mock nav_callable
    nav_called = False
    nav_has_run = False

    def mock_nav():
        nonlocal nav_called, nav_has_run
        nav_called = True
        nav_has_run = True

    state = AppState()

    # Mock ProjectState.get_page to return a sentinel after first notification
    sentinel_page = object()
    notification_count = 0

    def mock_get_page(index):
        # First call (during first notification) return None
        # After first notification, return sentinel (simulating loaded page)
        if notification_count > 1:
            return sentinel_page
        return None  # Empty project should return None initially

    monkeypatch.setattr(state.project_state, "get_page", mock_get_page)

    notifications = []

    def capture_notification():
        nonlocal notification_count
        notification_count += 1
        notifications.append(
            (
                state.is_loading,
                state.is_project_loading,
                state.project_state.current_page(),
            )
        )

    state.on_change.append(capture_notification)

    # Mock asyncio.get_running_loop to raise RuntimeError (no loop)
    monkeypatch.setattr(
        "asyncio.get_running_loop",
        lambda: (_ for _ in ()).throw(RuntimeError("no loop")),
    )

    # Call _navigate directly on project_state
    state.project_state._navigate()

    # Assertions
    assert len(notifications) == 2  # Two notifications: start and end
    assert notifications[0] == (
        True,
        False,
        None,
    )  # Start: loading=True, project_loading=False, page=None
    assert notifications[1] == (
        False,
        False,
        sentinel_page,
    )  # End: loading=False, project_loading=False, page=sentinel
    assert state.is_loading is False
    assert state.is_project_loading is False
    assert state.project_state.current_page() is sentinel_page


def test_navigate_async_path_schedules_task(monkeypatch, tmp_path):
    """Test _navigate in async path (with event loop): sets flags, calls nav_callable, schedules async task, does not load synchronously."""
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Mock nav_callable
    nav_called = False
    nav_has_run = False

    def mock_nav():
        nonlocal nav_called, nav_has_run
        nav_called = True
        nav_has_run = True

    state = AppState()

    # Mock ProjectState.get_page to return a sentinel after first notification
    sentinel_page = object()
    notification_count = 0

    def mock_get_page(index):
        # First call (during first notification) return None
        # Subsequent calls return sentinel (simulating loaded page)
        if notification_count > 1:
            return sentinel_page
        return None  # Empty project should return None initially

    monkeypatch.setattr(state.project_state, "get_page", mock_get_page)

    notifications = []

    def capture_notification():
        nonlocal notification_count
        notification_count += 1
        notifications.append(
            (
                state.is_loading,
                state.is_project_loading,
                state.project_state.current_page(),
            )
        )

    state.on_change.append(capture_notification)

    # Mock event loop
    mock_loop = type("MockLoop", (), {"create_task": lambda self, coro: None})()
    monkeypatch.setattr("asyncio.get_running_loop", lambda: mock_loop)

    # Track if create_task was called
    task_created = False

    def mock_create_task(coro):
        nonlocal task_created
        task_created = True
        # Don't call original to avoid unawaited coroutine warning

    mock_loop.create_task = mock_create_task

    # Call _navigate directly on project_state
    state.project_state._navigate()

    # Assertions
    assert task_created  # Async task was scheduled
    assert (
        len(notifications) == 1
    )  # Only start notification; end happens in async task (not in this sync test)
    assert notifications[0] == (
        True,
        False,
        None,
    )  # Start: loading=True, project_loading=False, page=None
    assert state.is_loading is True  # Still loading since async task hasn't completed
    assert state.is_project_loading is False
    assert state.project_state.current_page() is None  # Not yet loaded (mock behavior)
