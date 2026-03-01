from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ocr_labeler.operations.persistence.project_operations import ProjectOperations


def _make_state(project_root: Path):
    state = SimpleNamespace()
    state.project_root = project_root
    state.project = SimpleNamespace(ground_truth_map={})
    state.invalidated = False
    state.notified = False

    def _invalidate_text_cache() -> None:
        state.invalidated = True

    def notify() -> None:
        state.notified = True

    state._invalidate_text_cache = _invalidate_text_cache
    state.notify = notify
    return state


def test_reload_ground_truth_into_project_loads_and_normalizes_pages_json(tmp_path):
    pages_json = tmp_path / "pages.json"
    pages_json.write_text('{"001":"Line one","002.png":"Line two"}', encoding="utf-8")

    state = _make_state(tmp_path)
    ops = ProjectOperations()

    ops.reload_ground_truth_into_project(state)

    assert state.project.ground_truth_map["001"] == "Line one"
    assert state.project.ground_truth_map["001.png"] == "Line one"
    assert state.project.ground_truth_map["002.png"] == "Line two"
    assert state.invalidated is True
    assert state.notified is True


def test_reload_ground_truth_into_project_clears_map_when_pages_json_missing(tmp_path):
    state = _make_state(tmp_path)
    state.project.ground_truth_map = {"001.png": "stale value"}
    ops = ProjectOperations()

    ops.reload_ground_truth_into_project(state)

    assert state.project.ground_truth_map == {}
    assert state.invalidated is True
    assert state.notified is True


def test_reload_ground_truth_into_project_handles_invalid_json(tmp_path):
    pages_json = tmp_path / "pages.json"
    pages_json.write_text('{"001": ', encoding="utf-8")

    state = _make_state(tmp_path)
    state.project.ground_truth_map = {"001.png": "stale value"}
    ops = ProjectOperations()

    ops.reload_ground_truth_into_project(state)

    assert state.project.ground_truth_map == {}
    assert state.invalidated is True
    assert state.notified is True
