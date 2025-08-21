from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging
from nicegui import ui

from .model import AppState
from .view import LabelerView


class NiceGuiLabeler:
    """Minimal OCR labeler: open project directory, navigate pages, auto OCR per page."""

    def __init__(
        self,
        project_root: Path,
        monospace_font_name: str = "monospace",
        monospace_font_path: Optional[Path] = None,
    ) -> None:
        self.state = AppState(
            project_root=project_root,
            monospace_font_name=monospace_font_name,
            monospace_font_path=monospace_font_path,
        )
        self.view = LabelerView(self.state)

    def create_routes(self):
        @ui.page("/")
        def index():  # noqa: D401
            self.view.mount()

    def run(self, host: str = "127.0.0.1", port: int = 8080):
        self._inject_font()
        self.create_routes()
        ui.run(host=host, port=port, reload=False)

    def _inject_font(self):  # pragma: no cover (UI side effect)
        """Inject DPSansMono font (hardcoded) if available.

        Looks for packaged font at fonts/DPSansMono.ttf relative to this file. If present,
        embeds as a data URL and sets a CSS variable + body monospace fallback.
        """
        try:
            logger = logging.getLogger(__name__)
            pkg_dir = Path(__file__).resolve().parent
            font_path = pkg_dir / "fonts" / "DPSansMono.ttf"
            if not font_path.exists():
                logger.info("DPSansMono.ttf not found at %s", font_path)
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
            logging.getLogger(__name__).debug("Font static serve/injection failed", exc_info=True)
