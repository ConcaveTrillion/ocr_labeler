"""Integration test fixtures — event-loop isolation for pytest-xdist workers.

Under ``pytest-xdist -n auto`` with ``pytest-asyncio`` in *auto* mode the
NiceGUI ``user`` fixture (an async-generator) occasionally finds a stale
"running" event loop left over from a previous test's ``Runner`` teardown on
the same worker.  ``Runner.run()`` then raises
``RuntimeError: Runner.run() cannot be called from a running event loop``.

The autouse fixture below detects that situation and force-clears the
thread-local running-loop flag so that the next ``Runner.run()`` call can
proceed normally.  This is a targeted workaround; the root cause lives in
the interaction between ``pytest-asyncio``, ``asyncio.Runner``, and
``pytest-xdist``'s ``execnet`` gateway.
"""

from __future__ import annotations

import asyncio.events as _aio_events

import pytest


@pytest.fixture(autouse=True)
def _clear_stale_running_loop() -> None:
    """Force-clear a leaked running-loop flag before each integration test."""
    _running = _aio_events._get_running_loop()
    if _running is not None:
        _aio_events._set_running_loop(None)
