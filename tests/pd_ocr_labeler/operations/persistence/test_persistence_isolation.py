"""Regression tests proving the test suite never writes to real user dirs.

Two known leak vectors live in this codebase:

1. ``ConfigOperations.set_source_projects_root`` writes a YAML file under the
   OS-aware config root (``~/.config/pd-ocr-labeler/config.yaml`` on Linux).
2. ``SessionStateOperations.save_session_state`` writes JSON under the OS-aware
   data root (``~/.local/share/pd-ocr-labeler/session_state.json`` on Linux).

Both resolve their destination on every call from ``XDG_CONFIG_HOME`` /
``XDG_DATA_HOME`` env vars. A session-scoped autouse fixture in
``tests/conftest.py`` redirects those env vars to a tmp tree so neither call
can leak into the real user home. This test asserts that protection is
actually in place by:

- Capturing the *real* user home (via ``pwd.getpwuid``, NOT ``$HOME``, so the
  capture is unaffected by the autouse fixture's monkeypatching).
- Snapshotting both real user files (sha256 + existence) before exercising
  each leak vector with sentinel values.
- Asserting both real user files are byte-identical (or still nonexistent)
  after.
- Asserting the writes *did* land somewhere under the redirected XDG tree
  (proves redirection happened, not that the calls silently no-op'd).
"""

from __future__ import annotations

import hashlib
import os
import pwd
from pathlib import Path

from pd_ocr_labeler.operations.persistence.config_operations import ConfigOperations
from pd_ocr_labeler.operations.persistence.session_state_operations import (
    SessionStateOperations,
)


def _real_user_home() -> Path:
    """Return the real user's home directory, ignoring ``$HOME``.

    ``pwd.getpwuid(os.getuid()).pw_dir`` reads from the password database, so
    it is unaffected by env-var monkeypatching in the autouse fixture.
    """
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def _file_fingerprint(path: Path) -> tuple[bool, str | None]:
    """Return (exists, sha256_hex_or_None) for a stable before/after compare."""
    if not path.exists():
        return False, None
    return True, hashlib.sha256(path.read_bytes()).hexdigest()


REAL_HOME = _real_user_home()
REAL_CONFIG_PATH = REAL_HOME / ".config" / "pd-ocr-labeler" / "config.yaml"
REAL_SESSION_STATE_PATH = (
    REAL_HOME / ".local" / "share" / "pd-ocr-labeler" / "session_state.json"
)


def test_config_write_does_not_leak_to_real_user_home(tmp_path):
    """``ConfigOperations.set_source_projects_root`` must redirect under XDG."""
    real_before = _file_fingerprint(REAL_CONFIG_PATH)

    sentinel = tmp_path / "sentinel-projects-root"
    ConfigOperations.set_source_projects_root(sentinel)

    real_after = _file_fingerprint(REAL_CONFIG_PATH)
    assert real_after == real_before, (
        f"ConfigOperations.set_source_projects_root leaked into real user "
        f"config at {REAL_CONFIG_PATH}: before={real_before} after={real_after}"
    )

    # Prove the write actually happened — somewhere under the XDG tmp tree —
    # rather than silently no-op'ing.
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    assert xdg_config_home, "XDG_CONFIG_HOME must be set by the autouse fixture"
    redirected_path = Path(xdg_config_home) / "pd-ocr-labeler" / "config.yaml"
    assert redirected_path.exists(), (
        f"Expected redirected config write at {redirected_path}, but file is "
        f"missing — write may have gone elsewhere."
    )
    assert sentinel.as_posix() in redirected_path.read_text(encoding="utf-8")


def test_session_state_write_does_not_leak_to_real_user_home(tmp_path):
    """``SessionStateOperations.save_session_state`` must redirect under XDG."""
    real_before = _file_fingerprint(REAL_SESSION_STATE_PATH)

    sentinel_project = tmp_path / "sentinel-project"
    ok = SessionStateOperations.save_session_state(sentinel_project, page_index=7)
    assert ok, "save_session_state should report success on the redirected path"

    real_after = _file_fingerprint(REAL_SESSION_STATE_PATH)
    assert real_after == real_before, (
        f"SessionStateOperations.save_session_state leaked into real user data "
        f"at {REAL_SESSION_STATE_PATH}: before={real_before} after={real_after}"
    )

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    assert xdg_data_home, "XDG_DATA_HOME must be set by the autouse fixture"
    redirected_path = Path(xdg_data_home) / "pd-ocr-labeler" / "session_state.json"
    assert redirected_path.exists(), (
        f"Expected redirected session-state write at {redirected_path}, but "
        f"file is missing — write may have gone elsewhere."
    )
    assert sentinel_project.as_posix() in redirected_path.read_text(encoding="utf-8")
