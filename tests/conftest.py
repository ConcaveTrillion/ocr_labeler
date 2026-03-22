"""Pytest configuration for NiceGUI testing fixtures."""

import logging

import pytest

pytest_plugins = ["nicegui.testing.user_plugin"]


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
        try:
            handler.close()
        except Exception:
            pass

    caplog.clear()
