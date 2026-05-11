"""Pytest configuration for NiceGUI testing fixtures."""

import contextlib
import logging
import os
from pathlib import Path

import pytest

pytest_plugins = ["nicegui.testing.user_plugin"]


@pytest.fixture(scope="session", autouse=True)
def isolate_persistence_xdg_dirs(tmp_path_factory):
    """Redirect persistence-layer writes off the real user home for the suite.

    The persistence layer (``ConfigOperations``, ``SessionStateOperations``,
    ``PersistencePathsOperations``) resolves its destination on every call from
    ``XDG_CONFIG_HOME`` / ``XDG_DATA_HOME`` / ``XDG_CACHE_HOME``. Tests that
    drive code which writes through those classes — directly or transitively
    via ``AppState.load_project`` — would otherwise mutate the developer's real
    ``~/.config/pd-ocr-labeler/`` and ``~/.local/share/pd-ocr-labeler/``.

    Setting all three env vars at session start to a tmp tree closes both
    historical leak paths at once. Per-test fixtures that monkeypatch
    ``HOME`` / ``XDG_*`` / ``CONFIG_PATH`` continue to work — their
    function-scoped patches naturally win over this session-scoped baseline
    and revert at function teardown back to the safe tmp tree.

    Playwright browser location: Playwright resolves its installed browser
    directory from ``PLAYWRIGHT_BROWSERS_PATH`` (if set) or falls back to
    ``$XDG_CACHE_HOME/ms-playwright``. Because we redirect ``XDG_CACHE_HOME``
    to an empty tmp tree, we must preserve the real browser path in
    ``PLAYWRIGHT_BROWSERS_PATH`` so that browser tests can still launch
    Chromium even after this fixture runs.
    """
    xdg_root = tmp_path_factory.mktemp("xdg-isolation")
    config_home = xdg_root / "config"
    data_home = xdg_root / "data"
    cache_home = xdg_root / "cache"
    for d in (config_home, data_home, cache_home):
        d.mkdir(parents=True, exist_ok=True)

    # Preserve the real Playwright browser path before overriding XDG_CACHE_HOME.
    # Playwright checks PLAYWRIGHT_BROWSERS_PATH first; if unset it falls back
    # to $XDG_CACHE_HOME/ms-playwright. We pin it to the real location so that
    # browser tests continue to find installed Chromium after the redirect.
    real_xdg_cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    real_playwright_path = os.environ.get(
        "PLAYWRIGHT_BROWSERS_PATH", str(Path(real_xdg_cache) / "ms-playwright")
    )

    mp = pytest.MonkeyPatch()
    mp.setenv("XDG_CONFIG_HOME", str(config_home))
    mp.setenv("XDG_DATA_HOME", str(data_home))
    mp.setenv("XDG_CACHE_HOME", str(cache_home))
    mp.setenv("PLAYWRIGHT_BROWSERS_PATH", real_playwright_path)
    try:
        yield xdg_root
    finally:
        mp.undo()


@pytest.fixture(autouse=True)
def isolate_captured_logs(caplog):
    """Ensure each test has isolated log capture and logger handlers.

    This prevents dynamic handlers (for example per-session file handlers)
    from leaking into subsequent tests when suites run in parallel workers.
    """
    root_logger = logging.getLogger()
    initial_root_handlers = list(root_logger.handlers)

    caplog.clear()
    yield

    # Remove any handlers added during this test and close them.
    for handler in list(root_logger.handlers):
        if handler in initial_root_handlers:
            continue
        root_logger.removeHandler(handler)
        with contextlib.suppress(Exception):
            handler.close()

    caplog.clear()
