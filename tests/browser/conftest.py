"""Shared fixtures for Playwright browser tests.

These fixtures provide a running app instance and browser pages for tests
that need a real browser context with pre-saved OCR data (no ML models needed).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def browser_test_fixtures_dir() -> Path:
    """Return the path to the browser test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def browser_projects_root(tmp_path_factory, browser_test_fixtures_dir) -> Path:
    """Create a temporary projects root containing the browser-test-project."""
    root = tmp_path_factory.mktemp("projects")
    src = browser_test_fixtures_dir / "browser-test-project"
    dst = root / "browser-test-project"
    shutil.copytree(src, dst)
    return root


@pytest.fixture(scope="session")
def browser_app_url(browser_projects_root, tmp_path_factory) -> str:
    """Start the app as a subprocess with pre-saved OCR data and yield the URL.

    Sets XDG_DATA_HOME so that the app finds pre-saved page JSON files
    instead of attempting live OCR (which requires ML models).

    Under pytest-xdist, each worker is a separate process and gets its own
    session-scoped fixture instance (including a unique random free port).
    """
    # Set up XDG directories for the subprocess
    xdg_base = tmp_path_factory.mktemp("xdg")
    xdg_data_home = xdg_base / "data"
    xdg_cache_home = xdg_base / "cache"

    # Copy pre-saved page JSONs into the expected location
    labeled_dir = xdg_data_home / "pd-ocr-labeler" / "labeled-projects"
    labeled_dir.mkdir(parents=True)
    saved_pages_src = FIXTURES_DIR / "saved-pages"
    for f in saved_pages_src.iterdir():
        shutil.copy2(f, labeled_dir / f.name)

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    cmd = [
        sys.executable,
        "-m",
        "pd_ocr_labeler.cli",
        str(REPO_ROOT),
        "--projects-root",
        str(browser_projects_root),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)

    process = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url = f"http://127.0.0.1:{port}/"

    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if process.poll() is not None:
                startup_output = process.stdout.read() if process.stdout else ""
                raise RuntimeError(
                    "App process exited before becoming ready. Output:\n"
                    f"{startup_output}"
                )
            try:
                with urlopen(url, timeout=1):
                    break
            except URLError:
                time.sleep(0.25)
        else:
            raise TimeoutError("Timed out waiting for app to start")

        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="session")
def _browser_instance():
    """Session-scoped Playwright + Chromium browser (shared across all tests)."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    try:
        try:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-animations",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-features=TranslateUI",
                    "--disable-extensions",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )
        except Exception:
            raise RuntimeError(
                "Playwright Chromium is required but could not be launched. "
                "Run: make install"
            )
        yield browser
        try:
            browser.close()
        except RuntimeError:
            # Playwright sync API may fail if the event loop was already
            # torn down by pytest-asyncio at session end.  The process is
            # exiting anyway, so swallowing the error is safe.
            pass
    finally:
        playwright.stop()


@pytest.fixture
def browser_page(_browser_instance):
    """Provide a fresh Playwright page in an isolated context per test."""
    context = _browser_instance.new_context(reduced_motion="reduce")
    # Containers can be slower; 60 s gives headroom at the end of long runs.
    context.set_default_navigation_timeout(60_000)
    context.set_default_timeout(30_000)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def browser_context(_browser_instance):
    """Provide a Playwright browser context for multi-tab tests."""
    context = _browser_instance.new_context(reduced_motion="reduce")
    context.set_default_navigation_timeout(60_000)
    yield context
    context.close()
