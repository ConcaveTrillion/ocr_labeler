from __future__ import annotations

from types import SimpleNamespace

import ocr_labeler.app as app_module
from ocr_labeler.app import NiceGuiLabeler
from ocr_labeler.routing import resolve_project_route_from_path
from ocr_labeler.state.app_state import AppState


async def test_initialize_from_url_toggles_project_loading_state(
    monkeypatch,
    tmp_path,
):
    labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=False)
    state = AppState(base_projects_root=tmp_path)

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module.run, "io_bound", fake_io_bound)
    monkeypatch.setattr(
        app_module,
        "resolve_project_path",
        lambda project_id, base_projects_root, available_projects: tmp_path,
    )
    monkeypatch.setattr(app_module, "sync_url_to_state", lambda _state: None)
    monkeypatch.setattr(app_module.ui, "notify", lambda *args, **kwargs: None)

    project_state = SimpleNamespace(
        project=SimpleNamespace(pages=[object(), object(), object()]),
        current_page_index=1,
        goto_page_index=lambda index: setattr(project_state, "goto_index", index),
        goto_index=None,
    )

    captured: dict[str, int | None] = {"initial_page_index": None}

    async def fake_load_project(_directory, initial_page_index=None):
        captured["initial_page_index"] = initial_page_index
        state.current_project_key = "fake_project"
        state.projects["fake_project"] = project_state

    monkeypatch.setattr(state, "load_project", fake_load_project)

    await labeler._initialize_from_url(
        state=state,
        project_id="fake_project",
        page_id="2",
        session_id="session-test",
    )

    assert captured["initial_page_index"] == 1
    assert state.is_project_loading is False
    assert project_state.goto_index == 1


async def test_initialize_from_url_ignores_notify_runtime_error(
    monkeypatch,
    tmp_path,
):
    labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=False)
    state = AppState(base_projects_root=tmp_path)

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module.run, "io_bound", fake_io_bound)
    monkeypatch.setattr(
        app_module,
        "resolve_project_path",
        lambda project_id, base_projects_root, available_projects: tmp_path,
    )
    monkeypatch.setattr(app_module, "sync_url_to_state", lambda _state: None)

    def raising_notify(*_args, **_kwargs):
        raise RuntimeError("slot stack is empty")

    monkeypatch.setattr(app_module.ui, "notify", raising_notify)

    project_state = SimpleNamespace(
        project=SimpleNamespace(pages=[object(), object(), object()]),
        current_page_index=1,
        goto_page_index=lambda index: setattr(project_state, "goto_index", index),
        goto_index=None,
    )

    async def fake_load_project(_directory, initial_page_index=None):
        assert initial_page_index == 1
        state.current_project_key = "fake_project"
        state.projects["fake_project"] = project_state

    monkeypatch.setattr(state, "load_project", fake_load_project)

    await labeler._initialize_from_url(
        state=state,
        project_id="fake_project",
        page_id="2",
        session_id="session-test",
    )

    assert state.is_project_loading is False
    assert project_state.goto_index == 1


async def test_initialize_from_url_missing_project_shows_not_found(
    monkeypatch,
    tmp_path,
):
    labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=False)
    state = AppState(base_projects_root=tmp_path)

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module.run, "io_bound", fake_io_bound)
    monkeypatch.setattr(
        app_module,
        "resolve_project_path",
        lambda project_id, base_projects_root, available_projects: None,
    )
    notify_calls: list[tuple[str, str]] = []

    def fake_notify(message, type="info", **_kwargs):
        notify_calls.append((message, type))

    monkeypatch.setattr(app_module.ui, "notify", fake_notify)

    await labeler._initialize_from_url(
        state=state,
        project_id="missing_project",
        page_id="1",
        session_id="session-test",
    )

    assert any(
        message == "Project not found: missing_project" and level == "warning"
        for message, level in notify_calls
    )
    assert state.is_project_loading is False


async def test_initialize_from_url_missing_page_shows_not_found(
    monkeypatch,
    tmp_path,
):
    labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=False)
    state = AppState(base_projects_root=tmp_path)

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module.run, "io_bound", fake_io_bound)
    monkeypatch.setattr(
        app_module,
        "resolve_project_path",
        lambda project_id, base_projects_root, available_projects: tmp_path,
    )
    monkeypatch.setattr(app_module, "sync_url_to_state", lambda _state: None)

    notify_calls: list[tuple[str, str]] = []

    def fake_notify(message, type="info", **_kwargs):
        notify_calls.append((message, type))

    monkeypatch.setattr(app_module.ui, "notify", fake_notify)

    project_state = SimpleNamespace(
        project=SimpleNamespace(pages=[object(), object()]),
        goto_page_index=lambda index: setattr(project_state, "goto_index", index),
        goto_index=None,
    )

    async def fake_load_project(_directory, initial_page_index=None):
        assert initial_page_index == 98
        state.current_project_key = "fake_project"
        state.projects["fake_project"] = project_state

    monkeypatch.setattr(state, "load_project", fake_load_project)

    await labeler._initialize_from_url(
        state=state,
        project_id="fake_project",
        page_id="99",
        session_id="session-test",
    )

    assert any(
        message == "Page not found: 99" and level == "warning"
        for message, level in notify_calls
    )


async def test_initialize_from_url_reuses_already_loaded_project(
    monkeypatch,
    tmp_path,
):
    labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=False)
    state = AppState(base_projects_root=tmp_path)

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module.run, "io_bound", fake_io_bound)
    monkeypatch.setattr(
        app_module,
        "resolve_project_path",
        lambda project_id, base_projects_root, available_projects: tmp_path,
    )
    monkeypatch.setattr(app_module, "sync_url_to_state", lambda _state: None)
    monkeypatch.setattr(app_module.ui, "notify", lambda *args, **kwargs: None)

    existing_project_state = SimpleNamespace(
        project=SimpleNamespace(pages=[object(), object(), object()]),
        project_root=tmp_path,
        current_page_index=0,
        goto_page_index=lambda index: setattr(
            existing_project_state, "goto_index", index
        ),
        goto_index=None,
    )

    state.current_project_key = tmp_path.resolve().name
    state.projects[state.current_project_key] = existing_project_state

    called = {"load_project": 0}

    async def fake_load_project(_directory, initial_page_index=None):
        called["load_project"] += 1

    monkeypatch.setattr(state, "load_project", fake_load_project)

    await labeler._initialize_from_url(
        state=state,
        project_id=tmp_path.name,
        page_id="2",
        session_id="session-test",
    )

    assert called["load_project"] == 0
    assert existing_project_state.goto_index == 1


def test_resolve_project_route_from_path_project_only():
    project_id, page_id = resolve_project_route_from_path("/project/my_proj")

    assert project_id == "my_proj"
    assert page_id == "1"


def test_resolve_project_route_from_path_project_and_page():
    project_id, page_id = resolve_project_route_from_path("/project/my_proj/page/7")

    assert project_id == "my_proj"
    assert page_id == "7"


def test_resolve_project_route_from_path_invalid():
    project_id, page_id = resolve_project_route_from_path("/")

    assert project_id is None
    assert page_id is None


def test_get_request_path_uses_referer_when_request_path_is_root(monkeypatch, tmp_path):
    labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=False)

    request = SimpleNamespace(
        url=SimpleNamespace(path="/"),
        headers={"referer": "http://localhost:8080/project/proj_a/page/7"},
    )
    client = SimpleNamespace(request=request)
    context = SimpleNamespace(client=client)

    monkeypatch.setattr(app_module.ui, "context", context)

    assert labeler._get_request_path() == "/project/proj_a/page/7"
