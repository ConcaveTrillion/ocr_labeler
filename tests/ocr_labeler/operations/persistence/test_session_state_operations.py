"""Tests for SessionStateOperations."""

from __future__ import annotations

import json
from pathlib import Path

from ocr_labeler.operations.persistence.session_state_operations import (
    SESSION_STATE_FILENAME,
    SESSION_STATE_SCHEMA_VERSION,
    SessionState,
    SessionStateOperations,
)


class TestSessionState:
    def test_to_dict_roundtrip(self):
        state = SessionState(
            last_project_path="/some/project",
            last_page_index=3,
        )
        result = SessionState.from_dict(state.to_dict())
        assert result.last_project_path == "/some/project"
        assert result.last_page_index == 3
        assert result.schema_version == SESSION_STATE_SCHEMA_VERSION

    def test_from_dict_defaults(self):
        state = SessionState.from_dict({})
        assert state.last_project_path is None
        assert state.last_page_index == 0

    def test_from_dict_none_path_becomes_none(self):
        state = SessionState.from_dict({"last_project_path": None})
        assert state.last_project_path is None

    def test_from_dict_empty_string_path_becomes_none(self):
        state = SessionState.from_dict({"last_project_path": ""})
        assert state.last_project_path is None


class TestSessionStateOperations:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: tmp_path / SESSION_STATE_FILENAME),
        )
        SessionStateOperations.save_session_state(
            project_path="/my/project",
            page_index=5,
        )
        state = SessionStateOperations.load_session_state()
        assert state is not None
        assert state.last_project_path == "/my/project"
        assert state.last_page_index == 5

    def test_load_returns_none_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: tmp_path / "nonexistent.json"),
        )
        assert SessionStateOperations.load_session_state() is None

    def test_load_returns_none_on_corrupt_json(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        dest.write_text("not valid json", encoding="utf-8")
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        assert SessionStateOperations.load_session_state() is None

    def test_load_returns_none_on_non_dict_json(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        dest.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        assert SessionStateOperations.load_session_state() is None

    def test_save_creates_parent_directories(self, tmp_path, monkeypatch):
        nested = tmp_path / "a" / "b" / SESSION_STATE_FILENAME
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: nested),
        )
        result = SessionStateOperations.save_session_state("/proj", 0)
        assert result is True
        assert nested.exists()

    def test_clear_removes_file(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        dest.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        result = SessionStateOperations.clear_session_state()
        assert result is True
        assert not dest.exists()

    def test_clear_is_idempotent(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        # File doesn't exist — should return True without error
        result = SessionStateOperations.clear_session_state()
        assert result is True

    def test_save_clamps_negative_page_index(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        SessionStateOperations.save_session_state("/proj", -5)
        state = SessionStateOperations.load_session_state()
        assert state is not None
        assert state.last_page_index == 0

    def test_save_with_none_project_path(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        result = SessionStateOperations.save_session_state(None, 0)
        assert result is True
        state = SessionStateOperations.load_session_state()
        assert state is not None
        assert state.last_project_path is None

    def test_save_with_path_object(self, tmp_path, monkeypatch):
        dest = tmp_path / SESSION_STATE_FILENAME
        monkeypatch.setattr(
            "ocr_labeler.operations.persistence.session_state_operations."
            "SessionStateOperations._session_state_path",
            staticmethod(lambda: dest),
        )
        result = SessionStateOperations.save_session_state(Path("/my/project"), 2)
        assert result is True
        state = SessionStateOperations.load_session_state()
        assert state is not None
        assert state.last_project_path == "/my/project"
