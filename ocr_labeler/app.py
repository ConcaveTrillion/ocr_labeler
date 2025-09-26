from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

from nicegui import ui

from .state.app_state import AppState
from .viewmodels.main_view_model import MainViewModel
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
        logger.debug(
            "Initializing NiceGuiLabeler with project_root=%s, projects_root=%s, monospace_font_name=%s, monospace_font_path=%s",
            project_root,
            projects_root,
            monospace_font_name,
            monospace_font_path,
        )
        self.state = AppState(
            base_projects_root=projects_root,
            monospace_font_name=monospace_font_name,
            monospace_font_path=monospace_font_path,
        )
        # Set the initial project root in the project state
        self.state.project_state.project_root = project_root

        # Create view model and view
        self.viewmodel = MainViewModel(self.state)
        self.view = LabelerView(self.viewmodel)
        logger.debug("NiceGuiLabeler initialization complete")

    def create_routes(self):
        logger.debug("Creating UI routes")

        @ui.page("/")
        def index():  # noqa: D401
            self.view.build()

        logger.debug("Routes creation complete")

    def run(self, host: str = "127.0.0.1", port: int = 8080, **uvicorn_kwargs):
        logger.debug(
            "Starting NiceGuiLabeler application with host=%s, port=%d, uvicorn_kwargs=%s",
            host,
            port,
            uvicorn_kwargs,
        )
        self._inject_font()
        self.create_routes()

        # Forward extra kwargs (e.g., uvicorn_logging_level) to NiceGUI/uvicorn if supported
        # Ensure uvicorn doesn't override our logging: let records propagate to root handlers
        uvicorn_kwargs.setdefault("log_config", None)
        logger.debug("Configured uvicorn_kwargs: %s", uvicorn_kwargs)
        try:
            ui.run(host=host, port=port, reload=False, **uvicorn_kwargs)
        except TypeError:
            # Older NiceGUI versions may not accept forwarded kwargs
            logger.warning(
                "Falling back to basic ui.run call due to TypeError with kwargs"
            )
            ui.run(host=host, port=port, reload=False)

    def _inject_font(self):  # pragma: no cover (UI side effect)
        """Inject DPSansMono font (hardcoded) if available.

        Looks for packaged font at fonts/DPSansMono.ttf relative to this file. If present,
        embeds as a data URL and sets a CSS variable + body monospace fallback.
        """
        logger.debug("Attempting to inject DPSansMono font")
        try:
            pkg_dir = Path(__file__).resolve().parent
            font_path = pkg_dir / "fonts" / "DPSansMono.ttf"
            logger.debug("Looking for font at path: %s", font_path)
            if not font_path.exists():
                logger.warning("DPSansMono.ttf not found at %s", font_path)
                return
            logger.debug("Font file found, reading and encoding")
            with open(font_path, "rb") as f:
                font_data = base64.b64encode(f.read()).decode("utf-8")
            logger.debug("Font encoded successfully, size: %d bytes", len(font_data))
            css = f"""
            @font-face {{
                font-family: 'DPSansMono';
                src: url('data:font/truetype;base64,{font_data}') format('truetype');
                font-weight: normal;
                font-style: normal;
                font-display: swap;
            }}
            body, .monospace, textarea {{
                font-family: 'DPSansMono', {self.state.monospace_font_name}, monospace !important;
            }}
            """
            ui.add_head_html(f"<style>{css}</style>")
            logger.debug("Font CSS injected into UI head")
        except Exception:  # noqa: BLE001
            logger.warning("Font static serve/injection failed", exc_info=True)
