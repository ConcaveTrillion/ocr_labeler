from __future__ import annotations

import base64
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from nicegui import background_tasks, core, run, ui

from .operations.persistence.project_discovery_operations import (
    ProjectDiscoveryOperations,
)
from .routing import (
    resolve_project_path,
    resolve_project_route_from_path,
    sync_url_to_state,
)
from .state.app_state import AppState
from .viewmodels.main_view_model import MainViewModel
from .views.main_view import LabelerView

logger = logging.getLogger(__name__)


class _NiceGuiBenignErrorFilter(logging.Filter):
    """Filter known benign NiceGUI teardown race errors."""

    _blocked_fragments = (
        "the client this element belongs to has been deleted",
        "object has no attribute 'reconnect_timeout'",
        "dictionary changed size during iteration",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.ERROR:
            return True
        message = record.getMessage().lower()
        return not any(fragment in message for fragment in self._blocked_fragments)


class NiceGuiLabeler:
    """Minimal OCR labeler: open project directory, navigate pages, auto OCR per page.

    This class implements per-session state isolation to ensure each browser tab
    operates independently. State, viewmodels, and views are created inside the
    @ui.page handler rather than in __init__, so each tab/session gets its own
    isolated instance.
    """

    def __init__(
        self,
        project_root: Path | str,
        projects_root: Path | str | None = None,
        monospace_font_name: str = "monospace",
        monospace_font_path: Path | str | None = None,
        enable_session_logging: bool = True,
    ) -> None:
        # Store configuration parameters as Path objects
        self.project_root = Path(project_root) if project_root else None
        self.projects_root = Path(projects_root) if projects_root else None
        self.monospace_font_name = monospace_font_name
        self.monospace_font_path = (
            Path(monospace_font_path) if monospace_font_path else None
        )
        self.enable_session_logging = enable_session_logging

        logger.debug(
            "Initializing NiceGuiLabeler with project_root=%s, projects_root=%s, monospace_font_name=%s, monospace_font_path=%s",
            self.project_root,
            self.projects_root,
            self.monospace_font_name,
            self.monospace_font_path,
        )

        # Prepare font CSS once (shared across all sessions)
        self.font_css = self._prepare_font_css()

        # Ensure logs directory exists if session logging is enabled
        if self.enable_session_logging:
            self.logs_dir = Path.cwd() / "logs"
            self.logs_dir.mkdir(exist_ok=True)
        else:
            self.logs_dir = None

        logger.debug("NiceGuiLabeler initialization complete")

        try:
            nicegui_logger = logging.getLogger("nicegui")
            if not any(
                isinstance(existing_filter, _NiceGuiBenignErrorFilter)
                for existing_filter in nicegui_logger.filters
            ):
                nicegui_logger.addFilter(_NiceGuiBenignErrorFilter())

            if os.getenv("PYTEST_CURRENT_TEST"):
                nicegui_logger.setLevel(logging.CRITICAL)
        except Exception:
            logger.debug("Failed to install NiceGUI benign-error filter", exc_info=True)

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
        file_handler.setLevel(logging.NOTSET)

        # Create detailed formatter for file logs
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        # Add handler to root logger so new loggers inherit it
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # Also add to all existing loggers since CLI may have disabled propagation
        # This ensures session logs capture records from loggers with propagate=False.
        # Do not modify logger levels here; verbosity is controlled by CLI logging config.
        for logger_name in list(logging.root.manager.loggerDict):
            existing_logger = logging.getLogger(logger_name)
            if not existing_logger.propagate:  # Only add if propagation is disabled
                existing_logger.addHandler(file_handler)

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

    def _create_session(
        self,
        *,
        page_title: str,
        log_label: str,
        project_id: str | None = None,
        page_id: str | None = None,
        auto_load_cli_project: bool = False,
    ):
        """Create an isolated per-session app instance with logging, UI, and cleanup.

        This is the common core for all route handlers. Each browser tab gets
        its own AppState, MainViewModel, and LabelerView to prevent state
        conflicts when multiple tabs are open.

        Args:
            page_title: Title for the browser tab.
            log_label: Label for session log messages (e.g. "ROOT", "PROJECT").
            project_id: Optional project to load from URL path parameter.
            page_id: Optional page index to navigate to from URL path parameter.
            auto_load_cli_project: If True and self.project_root is set, auto-load it.
        """
        # Set up per-session logging
        session_handler, session_id = self._setup_session_logging()
        logger.info("=" * 80)
        logger.info(f"NEW {log_label} TAB SESSION STARTED - ID: {session_id}")
        logger.info("=" * 80)

        ui.page_title(page_title)

        # Keep toast notifications visible above loading overlays so users can
        # see progress messages during long OCR operations.
        ui.add_head_html(
            """
            <style>
            .q-notifications {
                z-index: 100000 !important;
            }
            </style>
            """
        )

        # Ensure reconnect timeout is defined on the page itself. In test
        # contexts where ui.run() is not called, app-level reconnect timeout
        # may be unavailable; page-level value avoids outbox teardown errors.
        try:
            client = getattr(ui.context, "client", None)
            page = getattr(client, "page", None)
            if page is not None and getattr(page, "reconnect_timeout", None) is None:
                page.reconnect_timeout = 30.0
        except Exception:
            logger.debug("Failed setting page reconnect_timeout", exc_info=True)

        try:
            logger.debug(f"Creating {log_label.lower()} session instance")

            # Create fresh state for this session/tab
            state = AppState(
                base_projects_root=self.projects_root,
                monospace_font_name=self.monospace_font_name,
                monospace_font_path=self.monospace_font_path,
            )

            # For URL-based project/page routes, set loading state immediately
            # so the initial render shows the loading overlay instead of the
            # "No Project Loaded" placeholder while background init starts.
            if project_id:
                state.is_project_loading = True
                state.notify()

            # Create view model and view for this session
            viewmodel = MainViewModel(state)
            view = LabelerView(viewmodel)

            # Inject font CSS in page context
            if self.font_css:
                ui.add_head_html(f"<style>{self.font_css}</style>")
                logger.debug("Font CSS injected into page")

            # Build the UI for this session
            view.build()

            # Determine what to load
            if project_id:
                # Start URL initialization on the first UI timer tick so the
                # page context/client is active and progress notifications can
                # render during loading (especially on reconnect).
                url_init_started = False

                def _enqueue_notify(message: str, type_: str = "info") -> None:
                    """Queue URL-init notifications for UI-thread timer delivery."""
                    try:
                        state.queue_notification(message, type_)
                    except Exception:
                        logger.debug("Falling back to direct notify", exc_info=True)
                        self._notify_safe(message, type_)

                def start_url_initialization() -> None:
                    nonlocal url_init_started
                    if url_init_started:
                        return
                    url_init_started = True
                    background_tasks.create(
                        self._initialize_from_url(
                            state,
                            project_id,
                            page_id or "1",
                            session_id,
                            notify_fn=_enqueue_notify,
                        )
                    )

                ui.timer(0.05, start_url_initialization)
            elif auto_load_cli_project and self.project_root:
                # Auto-load CLI project if valid
                if ProjectDiscoveryOperations.validate_project_directory(
                    self.project_root
                ):
                    logger.info(f"Auto-loading CLI project: {self.project_root}")
                    background_tasks.create(state.load_project(self.project_root))

            logger.info(
                f"{log_label} tab session initialized successfully: {session_id}"
            )

            # Set up cleanup on disconnect
            def on_disconnect():
                logger.info(f"{log_label} tab session disconnecting: {session_id}")

                # Stop periodic UI work for this session.
                try:
                    notification_timer = getattr(view, "_notification_timer", None)
                    if notification_timer is not None:
                        notification_timer.active = False
                except Exception:
                    logger.debug("Failed to deactivate session notification timer")

                # Detach listener chains to avoid late async callbacks trying to
                # update elements after the client has been deleted.
                try:
                    state.on_change.clear()
                    for project_state in state.projects.values():
                        project_state.notification_sink = None
                        project_state.on_change.clear()
                        for page_state in project_state.page_states.values():
                            page_state.on_change.clear()
                except Exception:
                    logger.debug("Failed to clear session listeners", exc_info=True)

                self._cleanup_session_logging(session_handler, session_id)

            try:
                ui.on("disconnect", on_disconnect)
            except Exception:
                logger.warning(
                    "ui.on('disconnect') registration failed; cleanup will rely on process exit",
                    exc_info=True,
                )

        except Exception as e:
            logger.exception(
                f"Error during {log_label.lower()} tab session initialization: {e}"
            )
            self._cleanup_session_logging(session_handler, session_id)
            raise

    def create_routes(self):
        logger.debug("Creating UI routes")

        # In test contexts, ui.run() is often not invoked, and older NiceGUI
        # app_config instances may lack reconnect_timeout. Outbox teardown then
        # raises AttributeError when resolving reconnect timeout.
        try:
            from nicegui.app.app_config import AppConfig

            if not hasattr(AppConfig, "reconnect_timeout"):
                AppConfig.reconnect_timeout = 30.0

            if not hasattr(core.app.config, "reconnect_timeout"):
                core.app.config.reconnect_timeout = 30.0
        except Exception:
            logger.debug(
                "Unable to initialize NiceGUI reconnect_timeout on app config",
                exc_info=True,
            )

        @ui.page("/")
        def root_index():  # noqa: D401
            """Root index page - shows project selection or auto-loads CLI project."""
            request_path = self._get_request_path()
            project_id, page_id = resolve_project_route_from_path(request_path)
            self._create_session(
                page_title="OCR Labeler",
                log_label="ROOT",
                project_id=project_id,
                page_id=page_id,
                auto_load_cli_project=project_id is None,
            )

        @ui.page("/project/{project_id}")
        def project_index(project_id: str):  # noqa: D401
            """Project-specific page - loads the given project at page 0."""
            self._create_session(
                page_title=f"OCR Labeler - {project_id}",
                log_label="PROJECT",
                project_id=project_id,
            )

        @ui.page("/project/{project_id}/page/{page_id}")
        def project_page_index(project_id: str, page_id: str):  # noqa: D401
            """Project + page page - loads the given project at the specified page."""
            self._create_session(
                page_title=f"OCR Labeler - {project_id} (Page {page_id})",
                log_label="PROJECT PAGE",
                project_id=project_id,
                page_id=page_id,
            )

        logger.debug("Routes creation complete")

    def _get_request_path(self) -> str | None:
        """Safely retrieve the current request path from NiceGUI context."""
        try:
            client = getattr(ui.context, "client", None)
            request = getattr(client, "request", None)

            # Primary path from current request URL
            url = getattr(request, "url", None)
            path = getattr(url, "path", None)
            if isinstance(path, str) and path not in {"", "/"}:
                return path

            # Fallback for proxied environments
            headers = getattr(request, "headers", None)
            if headers is not None:
                for header_name in ("x-original-uri", "x-forwarded-uri"):
                    forwarded_path = headers.get(header_name)
                    if isinstance(forwarded_path, str) and forwarded_path.startswith(
                        "/"
                    ):
                        return forwarded_path

                # NiceGUI reconnect can hit '/' while Referer still has '/project/...'
                referer = headers.get("referer") or headers.get("referrer")
                if isinstance(referer, str) and referer:
                    referer_path = urlparse(referer).path
                    if referer_path:
                        return referer_path

            # Last resort: use root path if present
            if isinstance(path, str):
                return path
        except Exception:
            logger.debug(
                "Failed to read request path from NiceGUI context", exc_info=True
            )
        return None

    def _notify_safe(self, message: str, type: str = "info") -> None:
        """Best-effort notification that does not fail URL initialization.

        URL initialization runs in a background task where NiceGUI's slot
        context may be unavailable. In that case, notifying should be skipped
        rather than crashing the load flow.
        """
        try:
            ui.notify(message, type=type)
        except RuntimeError:
            logger.debug("Skipping ui.notify without active NiceGUI slot context")
        except Exception:
            logger.debug("Failed to send ui.notify", exc_info=True)

    async def _initialize_from_url(
        self,
        state: AppState,
        project_id: str,
        page_id: str,
        session_id: str,
        notify_fn: Callable[[str, str], None] | None = None,
    ):
        """Initialize the application state from URL parameters.

        Resolves a project_id to a filesystem directory path by trying:
        1. Absolute path or relative to CWD
        2. Under base_projects_root (standard discovery location)
        3. Fallback common locations

        Then loads the project and navigates to page_id (1-based page number
        from the URL, converted to 0-based index internally).
        After loading, updates the browser URL to reflect the current state.
        """
        notify = notify_fn or self._notify_safe

        try:
            logger.info(
                f"Initializing from URL: project_id={project_id}, page_id={page_id}"
            )

            # Find the project directory
            project_path = await run.io_bound(
                resolve_project_path,
                project_id,
                state.base_projects_root,
                state.available_projects,
            )

            if not project_path:
                logger.warning(
                    "Project '%s' not found",
                    project_id,
                )
                notify(f"Project not found: {project_id}", "warning")
                return

            requested_page_index: int | None = None
            requested_page_number: int | None = None
            page_id_parse_error = False

            try:
                requested_page_number = int(page_id)
                requested_page_index = requested_page_number - 1
                if requested_page_index < 0:
                    page_id_parse_error = True
                    requested_page_index = None
            except ValueError:
                page_id_parse_error = True

            logger.info(
                "URL init page selection: page_id=%s, requested_page_number=%s, requested_page_index=%s, parse_error=%s",
                page_id,
                requested_page_number,
                requested_page_index,
                page_id_parse_error,
            )

            project_key = project_path.resolve().name
            already_loaded = False
            if (
                state.current_project_key == project_key
                and project_key in state.projects
            ):
                existing_project_state = state.projects[project_key]
                existing_project_root = getattr(
                    existing_project_state, "project_root", None
                )
                if existing_project_root is not None:
                    try:
                        already_loaded = (
                            Path(existing_project_root).resolve()
                            == project_path.resolve()
                        )
                    except Exception:
                        already_loaded = False

            if already_loaded:
                logger.info(
                    "URL init: project '%s' already loaded, skipping reload",
                    project_key,
                )
            else:
                # Use the shared AppState project loading path so URL and in-app
                # project loading follow the same lifecycle and notifications.
                await state.load_project(
                    project_path,
                    initial_page_index=requested_page_index,
                )

            # Set the page if specified and valid
            # page_id is 1-based in the URL; convert to 0-based index
            if page_id_parse_error:
                logger.warning(
                    "Invalid page id '%s' for project '%s'",
                    page_id,
                    project_id,
                )
                notify(f"Page not found: {page_id}", "warning")
            elif (
                state.current_project_key
                and state.current_project_key in state.projects
                and requested_page_index is not None
                and requested_page_number is not None
            ):
                project_state = state.projects[state.current_project_key]
                # Ensure project state has some pages before attempting navigation
                if project_state.project and project_state.project.pages:
                    if not (
                        0 <= requested_page_index < len(project_state.project.pages)
                    ):
                        logger.warning(
                            "Page '%s' not found in project '%s'",
                            page_id,
                            project_id,
                        )
                        notify(f"Page not found: {page_id}", "warning")
                    elif hasattr(project_state, "goto_page_index"):
                        current_index = getattr(
                            project_state, "current_page_index", None
                        )
                        page_already_loaded = False
                        try:
                            page_already_loaded = (
                                project_state.project.pages[requested_page_index]
                                is not None
                            )
                        except Exception:
                            page_already_loaded = False

                        # Route URL-driven page selection through async navigation
                        # only when needed (different index or missing page object).
                        if (
                            current_index != requested_page_index
                            or not page_already_loaded
                        ):
                            project_state.goto_page_index(requested_page_index)
                else:
                    logger.warning(
                        "Project '%s' loaded but contains no pages", project_id
                    )
                    notify(f"Page not found: {page_id}", "warning")

            # Update browser URL to reflect the resolved state
            sync_url_to_state(state)

            logger.info(f"URL initialization complete for session {session_id}")

        except Exception as e:
            logger.exception(f"Error initializing from URL: {e}")
            notify(f"Error loading project: {e}", "negative")

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
            # Increase reconnect_timeout to give more headroom for long-running
            # operations like OCR. Default is 3.0s which can cause "connection lost"
            # during async image processing. 30s is more tolerant while still
            # detecting actual disconnections.
            ui.run(
                host=host,
                port=port,
                reload=False,
                reconnect_timeout=30.0,
                **uvicorn_kwargs,
            )
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
