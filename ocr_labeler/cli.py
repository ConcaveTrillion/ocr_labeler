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
        help="Increase logging verbosity (-v: console DEBUG, -vv: +third‑party DEBUG)",
    )
    p.add_argument(
        "--log-file",
        type=Path,
        default=Path("ocr_labeler.log"),
        help="Path to log file (will be created/overwritten). Set to '-' to disable file logging.",
    )
    return p.parse_args(argv)


def get_logging_configuration(verbose, log_file: Path | None = None) -> dict:
    """Return logging DictConfig.

    Console: WARNING and above only.
    File: ALL
    """
    handler_names: list[str] = ["console"]
    if log_file is not None:
        handler_names.append("file")

    # Discover existing loggers and directly set log levels, then later we can attach handlers.
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for lg in loggers:
        # Noise reduction for known chatty loggers
        if "engineio" in lg.name or "socketio" in lg.name or "urllib3" in lg.name:
            lg.setLevel(logging.WARNING)
            lg.propagate = False
            # print(f"Discovered noisy logger: {lg.name} level={lg.level} propagate={lg.propagate}")
            continue
        if verbose >= 2:
            lg.setLevel(logging.DEBUG)
            lg.propagate = False
        elif verbose == 1:
            lg.setLevel(logging.INFO)
            lg.propagate = False
        elif verbose == 0:
            lg.setLevel(logging.WARNING)
            lg.propagate = False
        # print(f"Discovered logger: {lg.name} level={lg.level} propagate={lg.propagate}")
    loggers_dict = {lg.name: lg for lg in loggers}

    log_formatters = {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%H:%M:%S",
        }
    }

    log_handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    }
    if log_file is not None:
        log_handlers["file"] = {
            "class": "logging.FileHandler",
            "level": "NOTSET",  # capture everything to file now
            "formatter": "default",
            "filename": str(log_file),
            "mode": "w",
            "encoding": "utf-8",
        }

    log_loggers = {
        name: {"handlers": handler_names, "propagate": False}
        for name in loggers_dict.keys()
    }

    # Ensure uvicorn/nicegui loggers propagate; avoid attaching handlers directly so
    # if uvicorn later adjusts its own handlers we still capture records via root.
    for special in ["uvicorn", "uvicorn.error", "uvicorn.access", "nicegui"]:
        if verbose >= 2:
            special_level = "DEBUG"
        elif verbose == 1:
            special_level = "INFO"
        else:
            special_level = "WARNING"
        log_loggers.setdefault(
            special, {"level": special_level, "handlers": [], "propagate": True}
        )
        # Force propagate True & empty handlers
        log_loggers[special]["handlers"] = []
        log_loggers[special]["propagate"] = True

    if verbose >= 2:
        root_level = "DEBUG"
    elif verbose == 1:
        root_level = "INFO"
    else:
        root_level = "WARNING"

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

    # Configure logging immediately so early INFO logs go to file
    log_file = args.log_file if str(args.log_file) != "-" else None
    log_cfg = get_logging_configuration(
        args.verbose,
        log_file,
    )

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

    # Tell uvicorn/nicegui to emit DEBUG when -vvv is used.
    if args.verbose >= 3:
        uvicorn_logging_level = "debug"
    elif args.verbose >= 1:
        uvicorn_logging_level = "info"
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
