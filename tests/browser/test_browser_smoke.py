"""Browser-based regression smoke tests for the NiceGUI app."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT\x08\x1dc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def projects_root(tmp_path: Path) -> Path:
    """Create a minimal projects root with one synthetic project."""
    root = tmp_path / "projects"
    project = root / "project-browser-smoke"
    project.mkdir(parents=True)

    # A tiny valid PNG is enough for project discovery.
    (project / "001.png").write_bytes(TINY_PNG)
    (project / "pages.json").write_text('{"001.png": "sample ground truth"}\n')

    return root


@pytest.fixture
def app_url(projects_root: Path):
    """Start the app in a subprocess and yield a reachable local URL."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    repo_root = Path(__file__).resolve().parents[2]

    cmd = [
        sys.executable,
        "-m",
        "pd_ocr_labeler.cli",
        str(repo_root),
        "--projects-root",
        str(projects_root),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    process = subprocess.Popen(
        cmd,
        cwd=repo_root,
        env={k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"},
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


@pytest.fixture
def browser_page():
    """Provide a Playwright page; fail fast if browsers are unavailable."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    try:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Playwright Chromium is required but could not be launched. "
                "Run: make install"
            )

        context = browser.new_context()
        context.set_default_navigation_timeout(60_000)
        page = context.new_page()
        yield page
        context.close()
        browser.close()
    finally:
        playwright.stop()


@pytest.mark.browser
def test_home_page_renders_core_controls(app_url: str, browser_page) -> None:
    """Smoke-test key controls using a real browser context."""
    page = browser_page
    page.goto(app_url, wait_until="networkidle")

    page.get_by_text("No Project Loaded").first.wait_for(state="visible")
    page.get_by_role("button", name="LOAD").wait_for(state="visible")
    page.get_by_text("Project").first.wait_for(state="visible")
