from __future__ import annotations
import sys
import types
from pathlib import Path
import pytest
from ocr_labeler.state.app_state import AppState
import ocr_labeler.state.ground_truth
import ocr_labeler.state.page_loader

# ocr_labeler/state/test_app_state.py


# Relative import of the code under test

# ------------------------
# Test doubles / utilities
# ------------------------

class DummyProject:
    def __init__(self, pages, image_paths, current_page_index, page_loader, ground_truth_map):
        self.pages = pages
        self.image_paths = image_paths
        self.index = current_page_index
        self.page_loader = page_loader
        self.ground_truth_map = ground_truth_map

    # Methods expected by AppState
    def current_page(self):
        if not self.image_paths or self.index < 0:
            return None
        return f"page-{self.index}"

    def next_page(self):
        if self.index < len(self.image_paths) - 1:
            self.index += 1

    def prev_page(self):
        if self.index > 0:
            self.index -= 1

    def goto_page_number(self, number: int):
        if 0 <= number < len(self.image_paths):
            self.index = number


def _ensure_dummy_support_modules(monkeypatch):
    """
    Ensure ground_truth and page_loader modules exist and patch their functions.
    This accommodates either real modules (patched) or absence (dummy injected).
    """
    # ground_truth module
    gt_mod_name = "ocr_labeler.state.ground_truth"
    if gt_mod_name in sys.modules:
        gt_mod = sys.modules[gt_mod_name]
    else:
        gt_mod = types.ModuleType(gt_mod_name)
        sys.modules[gt_mod_name] = gt_mod

    def fake_load_ground_truth_map(directory: Path):
        # Return simple mapping for deterministic behavior
        return {}

    # Placeholder; will be overridden in specific test where needed
    def fake_reload_ground_truth_into_project(app_state: AppState):
        pass

    monkeypatch.setattr(gt_mod, "load_ground_truth_map", fake_load_ground_truth_map, raising=False)
    monkeypatch.setattr(gt_mod, "reload_ground_truth_into_project", fake_reload_ground_truth_into_project, raising=False)

    # page_loader module
    pl_mod_name = "ocr_labeler.state.page_loader"
    if pl_mod_name in sys.modules:
        pl_mod = sys.modules[pl_mod_name]
    else:
        pl_mod = types.ModuleType(pl_mod_name)
        sys.modules[pl_mod_name] = pl_mod

    def fake_build_page_loader():
        return object()

    monkeypatch.setattr(pl_mod, "build_page_loader", fake_build_page_loader, raising=False)


def _patch_project_vm(monkeypatch):
    import ocr_labeler.state.app_state as app_state_module
    monkeypatch.setattr(app_state_module, "Project", DummyProject, raising=True)


# ------------- Tests --------------

def test_load_project_success_sets_state_and_clears_loading(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Add specific ground truth mapping (override for this test)
    import ocr_labeler.state.ground_truth as gt_mod
    monkeypatch.setattr(gt_mod, "load_ground_truth_map",
                        lambda directory: {"img0.png": "GT0"}, raising=False)

    # Create image files
    (tmp_path / "img0.png").write_bytes(b"")
    (tmp_path / "img1.jpg").write_bytes(b"")

    # Track notifications
    notifications = []

    state = AppState(project_root=tmp_path)
    state.on_change = lambda: notifications.append(
        (state.is_loading, state.is_project_loading))

    state.load_project(tmp_path)

    assert state.project_root == tmp_path
    # DummyProject attributes
    assert isinstance(state.project, DummyProject)
    assert len(state.project.image_paths) == 2
    assert state.current_page_native == "page-0"
    assert state.is_loading is False
    assert state.is_project_loading is False
    # Expect two notifications: entering & leaving loading phase
    assert len(notifications) == 2
    assert notifications[0] == (True, True)   # start project load
    assert notifications[-1] == (False, False)  # end project load


def test_load_project_nonexistent_directory_raises(tmp_path):
    state = AppState(project_root=tmp_path)
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        state.load_project(missing)
    # Flags should remain default
    assert state.is_loading is False
    assert state.is_project_loading is False


def test_navigation_updates_current_page_and_flags(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Three images
    for i in range(3):
        (tmp_path / f"p{i}.png").write_bytes(b"")

    state = AppState(project_root=tmp_path)
    state.load_project(tmp_path)

    # Initial
    assert state.current_page_native == "page-0"

    state.next_page()
    assert state.current_page_native == "page-1"
    assert state.is_loading is False  # synchronous fallback path

    state.next_page()
    state.next_page()  # attempt to move beyond end
    assert state.current_page_native == "page-2"

    state.prev_page()
    assert state.current_page_native == "page-1"

    state.goto_page_number(0)
    assert state.current_page_native == "page-0"

    # Out-of-range should not change index
    state.goto_page_number(99)
    assert state.current_page_native == "page-0"


def test_reload_ground_truth_invokes_helper(monkeypatch, tmp_path):
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    import ocr_labeler.state.ground_truth as gt_mod

    called = {}

    def fake_reload(app_state):
        called["app_state"] = app_state

    monkeypatch.setattr(gt_mod, "reload_ground_truth_into_project", fake_reload, raising=False)

    state = AppState(project_root=tmp_path)
    state.reload_ground_truth()
    assert called.get("app_state") is state


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

    state = AppState(project_root=tmp_path)
    result = state.list_available_projects()
    assert set(result.keys()) == {"projA", "projC"}
    assert result["projA"] == projA.resolve()
    assert result["projC"] == projC.resolve()


def test_list_available_projects_missing_base_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Do NOT create the base path
    state = AppState(project_root=tmp_path)
    assert state.list_available_projects() == {}


def test_notify_invokes_on_change_callback(tmp_path):
    state = AppState(project_root=tmp_path)
    calls = []
    state.on_change = lambda: calls.append("notified")
    state.notify()
    assert calls == ["notified"]


def test_navigation_triggers_loading_flag_transient(monkeypatch, tmp_path):
    """
    Verify that is_loading is set True inside navigation and ends False after synchronous load.
    """
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    (tmp_path / "only.png").write_bytes(b"")
    state = AppState(project_root=tmp_path)
    state.load_project(tmp_path)

    observed = []

    def on_change():
        observed.append(state.is_loading)

    state.on_change = on_change
    state.next_page()  # Will attempt to go beyond end; index unchanged but navigation path runs
    # Expect at least two observations: loading True then False
    assert True in observed
    assert observed[-1] is False


def test_navigate_sync_fallback_sets_flags_and_loads_page(monkeypatch, tmp_path):
    """Test _navigate in sync fallback path (no event loop): sets loading flags, calls nav_callable, loads page synchronously, clears flags."""
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Mock nav_callable
    nav_called = False
    def mock_nav():
        nonlocal nav_called
        nav_called = True

    state = AppState(project_root=tmp_path)
    notifications = []
    state.on_change = lambda: notifications.append((state.is_loading, state.is_project_loading, state.current_page_native))

    # Mock project.current_page to return a sentinel
    sentinel_page = object()
    monkeypatch.setattr(state.project, "current_page", lambda: sentinel_page)

    # Mock asyncio.get_running_loop to raise RuntimeError (no loop)
    monkeypatch.setattr("asyncio.get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError("no loop")))

    # Call _navigate directly
    state._navigate(mock_nav)

    # Assertions
    assert nav_called  # nav_callable was called
    assert len(notifications) == 2  # Two notifications: start and end
    assert notifications[0] == (True, False, None)  # Start: loading=True, project_loading=False, page=None
    assert notifications[1] == (False, False, sentinel_page)  # End: loading=False, project_loading=False, page=sentinel
    assert state.is_loading is False
    assert state.is_project_loading is False
    assert state.current_page_native is sentinel_page


def test_navigate_async_path_schedules_task(monkeypatch, tmp_path):
    """Test _navigate in async path (with event loop): sets flags, calls nav_callable, schedules async task, does not load synchronously."""
    _ensure_dummy_support_modules(monkeypatch)
    _patch_project_vm(monkeypatch)

    # Mock nav_callable
    nav_called = False
    def mock_nav():
        nonlocal nav_called
        nav_called = True

    state = AppState(project_root=tmp_path)
    notifications = []
    state.on_change = lambda: notifications.append((state.is_loading, state.is_project_loading, state.current_page_native))

    # Mock project.current_page to return a sentinel
    sentinel_page = object()
    monkeypatch.setattr(state.project, "current_page", lambda: sentinel_page)

    # Mock event loop
    mock_loop = type('MockLoop', (), {'create_task': lambda self, coro: None})()
    monkeypatch.setattr("asyncio.get_running_loop", lambda: mock_loop)

    # Track if create_task was called
    task_created = False
    def mock_create_task(coro):
        nonlocal task_created
        task_created = True
        # Don't call original to avoid unawaited coroutine warning
    mock_loop.create_task = mock_create_task

    # Call _navigate directly
    state._navigate(mock_nav)

    # Assertions
    assert nav_called  # nav_callable was called
    assert task_created  # Async task was scheduled
    assert len(notifications) == 1  # Only start notification; end happens in async task (not in this sync test)
    assert notifications[0] == (True, False, None)  # Start: loading=True, project_loading=False, page=None
    assert state.is_loading is True  # Still loading since async task hasn't completed
    assert state.is_project_loading is False
    assert state.current_page_native is None  # Not yet loaded