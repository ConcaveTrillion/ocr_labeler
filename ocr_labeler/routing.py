"""URL routing utilities for the OCR labeler application.

Provides functions for building and synchronizing project URLs. These are kept in
a separate module to avoid circular imports between app.py and view components.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from nicegui import ui

if TYPE_CHECKING:
    from .state.app_state import AppState

logger = logging.getLogger(__name__)


def resolve_project_route_from_path(path: str | None) -> tuple[str | None, str | None]:
    """Parse project and page identifiers from an incoming request path.

    Supports:
    - /project/{project_id}
    - /project/{project_id}/page/{page_id}
    """
    if not path:
        return None, None

    normalized_path = path.rstrip("/")
    if not normalized_path:
        return None, None

    parts = normalized_path.split("/")
    if len(parts) == 3 and parts[1] == "project" and parts[2]:
        return unquote(parts[2]), "1"

    if (
        len(parts) == 5
        and parts[1] == "project"
        and parts[2]
        and parts[3] == "page"
        and parts[4]
    ):
        return unquote(parts[2]), unquote(parts[4])

    return None, None


def build_project_url(project_key: str, page_index: int = 0) -> str:
    """Build a URL path for a given project and page.

    The URL uses 1-based page numbers for user-friendliness,
    even though the internal page_index is 0-based.

    Args:
        project_key: The project identifier (directory name).
        page_index: Zero-based page index (default 0).

    Returns:
        URL path string like '/project/{project_key}/page/{page_number}'
        where page_number is 1-based (page_index + 1).
    """
    page_number = page_index + 1
    return f"/project/{project_key}/page/{page_number}"


def sync_url_to_state(state: "AppState") -> None:
    """Update the browser URL to reflect the current project/page state.

    Uses ui.navigate.history.replace() to update the URL bar without
    triggering a page reload or adding a browser history entry.

    Args:
        state: The current AppState to read project/page info from.
    """
    try:
        if not state.current_project_key:
            return

        project_key = state.current_project_key
        page_index = 0

        if project_key in state.projects:
            project_state = state.projects[project_key]
            page_index = project_state.current_page_index

        url = build_project_url(project_key, page_index)
        ui.navigate.history.replace(url)
        logger.debug(f"Browser URL synced to: {url}")
    except Exception:
        logger.debug("Failed to sync browser URL", exc_info=True)


def sync_url_from_project_state(
    project_root: Path | None, current_page_index: int
) -> None:
    """Update browser URL from project state fields directly.

    This variant avoids needing a full AppState reference, making it
    suitable for use from views that only have a ProjectState.

    Args:
        project_root: The project root directory (used for project key).
        current_page_index: The current 0-based page index (converted to
            1-based page number in the URL).
    """
    try:
        if not project_root:
            return

        project_key = project_root.resolve().name
        url = build_project_url(project_key, current_page_index)
        ui.navigate.history.replace(url)
        logger.debug(f"Browser URL synced to: {url}")
    except Exception:
        logger.debug("Failed to sync browser URL", exc_info=True)


def resolve_project_path(
    project_id: str,
    base_projects_root: Path | None,
    available_projects: dict[str, Path] | None = None,
) -> Path | None:
    """Resolve a project_id string to a filesystem directory path.

    Tries multiple strategies in order:
    1. Lookup in available_projects dict (already discovered projects)
    2. Absolute path
    3. Relative to CWD
    4. Under base_projects_root
    5. Under default discovery root (~/ocr/data/source-pgdp-data/output)
    6. Fallback common locations

    This is a synchronous method suitable for run.io_bound().

    Args:
        project_id: The project identifier from the URL.
        base_projects_root: Optional root directory for project discovery.
        available_projects: Optional mapping of project name -> path from
            project discovery. Checked first for quick resolution.

    Returns:
        Resolved Path if found, else None.
    """
    # 1. Check already-discovered projects
    if available_projects and project_id in available_projects:
        path = available_projects[project_id]
        if path.exists() and path.is_dir():
            return path

    # 2. Try as an absolute path
    p = Path(project_id)
    if p.is_absolute() and p.exists() and p.is_dir():
        return p

    # 3. Try relative to CWD
    potential = Path.cwd() / project_id
    if potential.exists() and potential.is_dir():
        return potential

    # 4. Try under base_projects_root
    if base_projects_root:
        potential = base_projects_root / project_id
        if potential.exists() and potential.is_dir():
            return potential

    # 5. Try default discovery root (same as ProjectDiscoveryOperations)
    try:
        default_root = Path("~/ocr/data/source-pgdp-data/output").expanduser().resolve()
        potential = default_root / project_id
        if potential.exists() and potential.is_dir():
            return potential
    except Exception:
        logger.debug("Failed to check default discovery root", exc_info=True)

    # 6. Fallback common locations
    fallback_paths = [
        Path.cwd().parent / "data" / "source-pgdp-data" / "output" / project_id,
    ]
    for path in fallback_paths:
        if path.exists() and path.is_dir():
            return path

    return None
