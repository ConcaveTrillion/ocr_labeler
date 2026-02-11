from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from nicegui import ui

from .state.app_state import AppState
from .viewmodels.main_view_model import MainViewModel
from .views.main_view import LabelerView

logger = logging.getLogger(__name__)


class NiceGuiLabeler:
    """Minimal OCR labeler: open project directory, navigate pages, auto OCR per page.

    This class implements per-session state isolation to ensure each browser tab
    operates independently. State, viewmodels, and views are created inside the
    @ui.page handler rather than in __init__, so each tab/session gets its own
    isolated instance.
    """

    def __init__(
        self,
        project_root: Path,
        projects_root: Path | None = None,
        monospace_font_name: str = "monospace",
        monospace_font_path: Optional[Path] = None,
        enable_session_logging: bool = True,
    ) -> None:
        logger.debug(
            "Initializing NiceGuiLabeler with project_root=%s, projects_root=%s, monospace_font_name=%s, monospace_font_path=%s",
            project_root,
            projects_root,
            monospace_font_name,
            monospace_font_path,
        )
        # Store configuration parameters to use when creating per-session instances
        self.project_root = project_root
        self.projects_root = projects_root
        self.monospace_font_name = monospace_font_name
        self.monospace_font_path = monospace_font_path
        self.enable_session_logging = enable_session_logging

        # Prepare font CSS once (shared across all sessions)
        self.font_css = self._prepare_font_css()

        # Ensure logs directory exists if session logging is enabled
        if self.enable_session_logging:
            self.logs_dir = Path.cwd() / "logs"
            self.logs_dir.mkdir(exist_ok=True)
        else:
            self.logs_dir = None

        logger.debug("NiceGuiLabeler initialization complete")

    def _setup_session_logging(self) -> tuple[logging.FileHandler | None, str]:
        """Set up per-session logging to a timestamped file.

        Creates a unique log file for this browser tab/session with format:
        logs/session_YYYYMMDD_HHMMSS_mmm.log

        Returns:
            Tuple of (file_handler, session_id) for cleanup and identification.
            file_handler is None if session logging is disabled.
        """
        # Generate unique session ID with timestamp
        session_timestamp = datetime.now()
        session_id = session_timestamp.strftime("%Y%m%d_%H%M%S_%f")[
            :20
        ]  # Include microseconds

        if not self.enable_session_logging or self.logs_dir is None:
            logger.debug(f"Session logging disabled for session {session_id}")
            return None, session_id

        log_filename = self.logs_dir / f"session_{session_id}.log"

        # Create file handler for this session
        file_handler = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Create detailed formatter for file logs
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        # Add handler to root logger so new loggers inherit it
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # Set root logger to DEBUG so it doesn't filter messages before handlers see them
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)

        # Also add to all existing loggers since CLI may have disabled propagation
        # This ensures session logs capture everything even when propagate=False
        # AND set them to DEBUG level so they don't filter before handlers see messages
        for logger_name in list(logging.root.manager.loggerDict):
            existing_logger = logging.getLogger(logger_name)
            if not existing_logger.propagate:  # Only add if propagation is disabled
                existing_logger.addHandler(file_handler)
                # Set ocr_labeler loggers to DEBUG for session logging
                # Other libraries stay at their CLI-configured level
                if logger_name.startswith("ocr_labeler"):
                    existing_logger.setLevel(logging.DEBUG)

        logger.info(f"Session logging initialized: {log_filename}")
        logger.info(f"Session ID: {session_id}")

        return file_handler, session_id

    def _cleanup_session_logging(
        self, file_handler: logging.FileHandler | None, session_id: str
    ):
        """Clean up session-specific logging handler.

        Args:
            file_handler: The file handler to remove (None if logging was disabled)
            session_id: Session identifier for logging
        """
        if file_handler is None:
            return

        logger.info(f"Cleaning up session logging: {session_id}")

        # Remove from root logger
        root_logger = logging.getLogger()
        root_logger.removeHandler(file_handler)

        # Remove from all individual loggers where we added it
        for logger_name in list(logging.root.manager.loggerDict):
            existing_logger = logging.getLogger(logger_name)
            if file_handler in existing_logger.handlers:
                existing_logger.removeHandler(file_handler)

        file_handler.close()

    def create_routes(self):
        logger.debug("Creating UI routes")

        @ui.page("/")
        def index():  # noqa: D401
            """Create per-session instances for tab isolation.

            Each browser tab gets its own AppState, MainViewModel, and LabelerView
            to prevent state conflicts when multiple tabs are open.
            """
            # Set up per-session logging
            session_handler, session_id = self._setup_session_logging()
            logger.info("=" * 80)
            logger.info(f"NEW TAB SESSION STARTED - ID: {session_id}")
            logger.info("=" * 80)

            try:
                logger.debug("Creating new session instance for tab")

                # Create fresh state for this session/tab
                state = AppState(
                    base_projects_root=self.projects_root,
                    monospace_font_name=self.monospace_font_name,
                    monospace_font_path=self.monospace_font_path,
                )
                # Note: project_root is not set here. It will be set when a project
                # is actually loaded via AppState.load_project(), which creates a
                # proper ProjectState instance in the projects dict.

                # Create view model and view for this session
                viewmodel = MainViewModel(state)
                view = LabelerView(viewmodel)

                # Inject font CSS in page context
                if self.font_css:
                    ui.add_head_html(f"<style>{self.font_css}</style>")
                    logger.debug("Font CSS injected into page")

                # Build the UI for this session
                view.build()

                logger.info(f"Tab session initialized successfully: {session_id}")

                # Set up cleanup on disconnect (if available - not in testing)
                def on_disconnect():
                    logger.info(f"Tab session disconnecting: {session_id}")
                    self._cleanup_session_logging(session_handler, session_id)

                try:
                    # NiceGUI supports ui.on('disconnect', ...) on current versions.
                    ui.on("disconnect", on_disconnect)
                except Exception:
                    logger.warning(
                        "ui.on('disconnect') registration failed; cleanup will rely on process exit",
                        exc_info=True,
                    )

            except Exception as e:
                logger.exception(f"Error during tab session initialization: {e}")
                # Still clean up logging on error
                self._cleanup_session_logging(session_handler, session_id)
                raise

        logger.debug("Routes creation complete")

    def run(self, host: str = "127.0.0.1", port: int = 8080, **uvicorn_kwargs):
        logger.debug(
            "Starting NiceGuiLabeler application with host=%s, port=%d, uvicorn_kwargs=%s",
            host,
            port,
            uvicorn_kwargs,
        )
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

    def _prepare_font_css(self) -> str:  # pragma: no cover (UI side effect)
        """Prepare monospace font CSS.

        Priority:
        1. AppState.monospace_font_path (if provided)
        2. Packaged DPSansMono.ttf font at fonts/DPSansMono.ttf

        This is called once during __init__ since the font CSS is shared
        across all sessions/tabs.

        Returns:
            CSS string to inject, or empty string if no font available
        """
        logger.debug("Attempting to inject monospace font")
        try:
            # 1. Try custom font path from state
            font_path = self.monospace_font_path
            if font_path and font_path.exists():
                logger.debug("Using custom font path: %s", font_path)
            else:
                # 2. Fall back to packaged DPSansMono.ttf
                pkg_dir = Path(__file__).resolve().parent
                font_path = pkg_dir / "fonts" / "DPSansMono.ttf"
                logger.debug("Looking for bundled font at path: %s", font_path)

            if not font_path.exists():
                logger.warning("No monospace font found at %s", font_path)
                return ""

            logger.debug("Font file found, reading and encoding")
            with open(font_path, "rb") as f:
                font_data = base64.b64encode(f.read()).decode("utf-8")
            logger.debug("Font encoded successfully, size: %d bytes", len(font_data))

            # Use DPSansMono as the font name unless explicitly overridden
            font_family = self.monospace_font_name
            if font_family == "monospace":
                # Default was used, switch to DPSansMono
                font_family = "DPSansMono"

            css = f"""
            @font-face {{
                font-family: '{font_family}';
                src: url('data:font/truetype;base64,{font_data}') format('truetype');
                font-weight: normal;
                font-style: normal;
                font-display: swap;
            }}
            /* Apply to elements with .monospace class */
            .monospace {{
                font-family: '{font_family}', monospace !important;
            }}
            /* Apply to CodeMirror editor components */
            .CodeMirror,
            .CodeMirror-line,
            .CodeMirror pre,
            .cm-content {{
                font-family: '{font_family}', monospace !important;
            }}
            /* Apply to NiceGUI textarea and labels with monospace class */
            textarea.monospace,
            label.monospace {{
                font-family: '{font_family}', monospace !important;
            }}
            """
            logger.debug("Font CSS prepared with font-family: %s", font_family)
            return css
        except Exception:  # noqa: BLE001
            logger.warning("Font CSS preparation failed", exc_info=True)
            return ""
