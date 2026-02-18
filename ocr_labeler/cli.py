from __future__ import annotations

import argparse
import logging
import logging.config
from pathlib import Path

from .app import NiceGuiLabeler

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(
        description="Launch the OCR Labeler NiceGUI UI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Directory containing page images (png/jpg/jpeg) and optional pages.json",
    )
    p.add_argument(
        "--projects-root",
        type=Path,
        default=None,
        help="Root directory whose immediate subdirectories are treated as selectable projects",
    )
    p.add_argument(
        "--host", default="127.0.0.1", help="Host/interface to bind the web server"
    )
    p.add_argument("--port", type=int, default=8080, help="Port for the web server")
    p.add_argument(
        "--font-name",
        default="monospace",
        help="Custom monospace font name (future use)",
    )
    p.add_argument(
        "--font-path",
        type=Path,
        default=None,
        help="Path to custom monospace font file (future use)",
    )
    p.add_argument(
        "--debugpy",
        action="store_true",
        help="Enable debugpy listener on 5678 for remote debugging/REPL",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase logging verbosity (-v: DEBUG app logs, -vv: DEBUG + pd-book-tools, -vvv: DEBUG all dependencies; default: INFO)",
    )
    p.add_argument(
        "--page-timing",
        action="store_true",
        help="Enable isolated page-load timing logs on the CLI (logger: ocr_labeler.page_timing)",
    )
    return p.parse_args(argv)


def get_logging_configuration(verbose: int, page_timing: bool = False) -> dict:
    """Return logging DictConfig.

    Verbosity mapping:
    - default: INFO
    - -v: DEBUG (app logs)
    - -vv: DEBUG (app + pd-book-tools)
    - -vvv: DEBUG (app + all dependent libraries)
    """
    # Keep global logging silent; per-session handlers in app.py write runtime
    # records into session log files.
    handler_names: list[str] = ["null"]

    if verbose >= 1:
        app_level = "DEBUG"
    else:
        app_level = "INFO"

    # Important dependency gets debug at -vv and above.
    important_dependency_level = "DEBUG" if verbose >= 2 else "WARNING"

    # All dependent libraries become verbose at -vvv.
    dependency_level = "DEBUG" if verbose >= 3 else "WARNING"

    # Keep root strict until -vvv to avoid noisy third-party logs
    root_level = "DEBUG" if verbose >= 3 else "WARNING"

    log_formatters = {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        }
    }

    log_handlers = {
        "null": {
            "class": "logging.NullHandler",
        },
        "page_timing_console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
        },
    }

    log_loggers = {
        "ocr_labeler": {
            "level": app_level,
            "handlers": handler_names,
            "propagate": False,
        },
        "ocr_labeler.page_timing": {
            "level": "INFO" if page_timing else "WARNING",
            "handlers": ["page_timing_console"] if page_timing else [],
            "propagate": False,
        },
        "pd_book_tools": {
            "level": important_dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "nicegui": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "uvicorn": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "uvicorn.error": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "uvicorn.access": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "engineio": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "socketio": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
        "urllib3": {
            "level": dependency_level,
            "handlers": [],
            "propagate": True,
        },
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": log_formatters,
        "handlers": log_handlers,
        "root": {"level": root_level, "handlers": handler_names},
        "loggers": log_loggers,
    }


def main(argv: list[str] | None = None):  # pragma: no cover (thin wrapper)
    args = parse_args(argv)
    logger.info("Parsed args: %s", args)

    # Configure base logging immediately; session files are attached per-tab in app.py
    log_cfg = get_logging_configuration(args.verbose, page_timing=args.page_timing)

    logging.config.dictConfig(log_cfg)

    if args.debugpy:
        try:
            import debugpy  # type: ignore

            debugpy.listen(("0.0.0.0", 5678))
            logger.info("debugpy listening on 0.0.0.0:5678 (attach for REPL/debug)")
        except Exception:  # pragma: no cover - defensive
            logger.error("Failed to start debugpy listener", exc_info=True)

    app = NiceGuiLabeler(
        project_root=args.project_dir,
        projects_root=args.projects_root,
        monospace_font_name=args.font_name,
        monospace_font_path=args.font_path,
    )

    # Keep uvicorn/nicegui quiet unless -vvv enables dependency debug logs.
    if args.verbose >= 3:
        uvicorn_logging_level = "debug"
    else:
        uvicorn_logging_level = "warning"
    logger.info(
        "Starting UI on %s:%s for project %s (projects root: %s), uvicorn log level %s",
        args.host,
        args.port,
        args.project_dir,
        args.projects_root or "<default>",
        uvicorn_logging_level,
    )
    try:
        app.run(
            host=args.host,
            port=args.port,
            uvicorn_logging_level=uvicorn_logging_level,
        )
    except TypeError:
        logger.critical("Failed to start application")
        raise  # re-raise


if __name__ == "__main__":  # pragma: no cover
    main()
