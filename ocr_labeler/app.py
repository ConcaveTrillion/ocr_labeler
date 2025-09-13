from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from nicegui import ui

from .state.app_state import AppState
from .views.main_view import LabelerView

logger = logging.getLogger(__name__)


class NiceGuiLabeler:
    """Minimal OCR labeler: open project directory, navigate pages, auto OCR per page."""

    def __init__(
        self,
        project_root: Path,
        projects_root: Path | None = None,
        monospace_font_name: str = "monospace",
        monospace_font_path: Optional[Path] = None,
    ) -> None:
        self.state = AppState(
            base_projects_root=projects_root,
            monospace_font_name=monospace_font_name,
            monospace_font_path=monospace_font_path,
        )
        # Set the initial project root in the project state
        self.state.project_state.project_root = project_root
        self.view = LabelerView(self.state)

    def create_routes(self):
        @ui.page("/")
        def index():  # noqa: D401
            self.view.mount()

    def run(self, host: str = "127.0.0.1", port: int = 8080, **uvicorn_kwargs):
        self._inject_font()
        self.create_routes()

        # Forward extra kwargs (e.g., uvicorn_logging_level) to NiceGUI/uvicorn if supported
        # Ensure uvicorn doesn't override our logging: let records propagate to root handlers
        uvicorn_kwargs.setdefault("log_config", None)
        try:
            ui.run(host=host, port=port, reload=False, **uvicorn_kwargs)
        except TypeError:
            # Older NiceGUI versions may not accept forwarded kwargs
            ui.run(host=host, port=port, reload=False)

    def _inject_font(self):  # pragma: no cover (UI side effect)
        """Inject DPSansMono font (hardcoded) if available.

        Looks for packaged font at fonts/DPSansMono.ttf relative to this file. If present,
        embeds as a data URL and sets a CSS variable + body monospace fallback.
        """
        try:
            pkg_dir = Path(__file__).resolve().parent
            font_path = pkg_dir / "fonts" / "DPSansMono.ttf"
            if not font_path.exists():
                logger.warning("DPSansMono.ttf not found at %s", font_path)
                return
            mount_path = "/_fonts"
            # Serve containing directory so additional fonts could be added later
            ui.add_static_files(mount_path, str(font_path.parent))  # type: ignore[arg-type]
            css = f"""
            @font-face {{
                font-family: 'DPSansMono';
                src: url('{mount_path}/DPSansMono.ttf') format('truetype');
                font-weight: normal;
                font-style: normal;
                font-display: swap;
            }}
            body, .monospace, textarea {{
                font-family: 'DPSansMono', {self.state.monospace_font_name}, monospace !important;
            }}
            """
            ui.add_head_html(f"<style>{css}</style>")
        except Exception:  # noqa: BLE001
            logger.warning("Font static serve/injection failed", exc_info=True)
