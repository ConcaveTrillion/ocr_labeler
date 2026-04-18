"""Session state persistence for restoring last project and page on startup."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .persistence_paths_operations import PersistencePathsOperations

logger = logging.getLogger(__name__)

SESSION_STATE_FILENAME = "session_state.json"
SESSION_STATE_SCHEMA_VERSION = "1.0"


@dataclass
class SessionState:
    """Lightweight snapshot of the last user session."""

    schema_version: str = SESSION_STATE_SCHEMA_VERSION
    last_project_path: Optional[str] = None
    last_page_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        return cls(
            schema_version=str(
                data.get("schema_version", SESSION_STATE_SCHEMA_VERSION)
            ),
            last_project_path=data.get("last_project_path") or None,
            last_page_index=int(data.get("last_page_index", 0)),
        )


class SessionStateOperations:
    """Read and write session state to a local JSON file.

    The session snapshot is stored under the app's data root so it persists
    across browser reloads and process restarts without user intervention.

    Design:
    - Writes are best-effort; failures are logged but never re-raised.
    - Reads fail gracefully and return ``None`` so callers can fall back to
      the default project-picker view.
    - The snapshot is intentionally minimal: only the last project path and
      page index are stored.
    """

    @staticmethod
    def _session_state_path() -> Path:
        return PersistencePathsOperations.get_data_root() / SESSION_STATE_FILENAME

    @classmethod
    def save_session_state(
        cls,
        project_path: str | Path | None,
        page_index: int = 0,
    ) -> bool:
        """Persist the current session snapshot to disk.

        Args:
            project_path: Absolute path to the loaded project directory.
            page_index: Zero-based page index of the current page.

        Returns:
            bool: True if the write succeeded, False otherwise.
        """
        state = SessionState(
            last_project_path=str(project_path) if project_path else None,
            last_page_index=max(0, int(page_index)),
        )
        dest = cls._session_state_path()
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(
                "Saved session state: project=%s page_index=%s",
                state.last_project_path,
                state.last_page_index,
            )
            return True
        except Exception:
            logger.debug("Failed to save session state", exc_info=True)
            return False

    @classmethod
    def load_session_state(cls) -> Optional[SessionState]:
        """Load the last session snapshot from disk.

        Returns:
            SessionState if a valid snapshot exists, None otherwise.
        """
        dest = cls._session_state_path()
        try:
            if not dest.exists():
                logger.debug("No session state file found at %s", dest)
                return None
            raw = dest.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.debug("Session state file has unexpected format; ignoring")
                return None
            state = SessionState.from_dict(data)
            logger.debug(
                "Loaded session state: project=%s page_index=%s",
                state.last_project_path,
                state.last_page_index,
            )
            return state
        except Exception:
            logger.debug("Failed to load session state", exc_info=True)
            return None

    @classmethod
    def clear_session_state(cls) -> bool:
        """Delete the stored session snapshot.

        Returns:
            bool: True if deleted or file did not exist, False on error.
        """
        dest = cls._session_state_path()
        try:
            dest.unlink(missing_ok=True)
            return True
        except Exception:
            logger.debug("Failed to clear session state", exc_info=True)
            return False
