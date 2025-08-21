from __future__ import annotations
import argparse
import logging
from pathlib import Path
from .app import NiceGuiLabeler

logger = logging.getLogger(__name__)

def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(
        description="Launch the OCR Labeler NiceGUI UI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--dir", "-d", default=".", help="Directory containing page images (png/jpg/jpeg) and optional pages.json")
    p.add_argument("--host", default="127.0.0.1", help="Host/interface to bind the web server")
    p.add_argument("--port", type=int, default=8080, help="Port for the web server")
    p.add_argument("--font-name", default="monospace", help="Custom monospace font name (future use)")
    p.add_argument("--font-path", type=Path, default=None, help="Path to custom monospace font file (future use)")
    p.add_argument("--verbose", "-v", action="count", default=0, help="Increase logging verbosity (-v, -vv)")
    return p.parse_args(argv)

def configure_logging(verbosity: int):
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="[%(levelname)s] %(name)s: %(message)s")

def main(argv: list[str] | None = None):  # pragma: no cover (thin wrapper)
    args = parse_args(argv)
    configure_logging(args.verbose)

    app = NiceGuiLabeler(
        project_root=args.dir,
        monospace_font_name=args.font_name,
        monospace_font_path=args.font_path,
    )
    logger.info("Starting UI on %s:%s for project %s", args.host, args.port, args.dir)
    app.run(host=args.host, port=args.port)

if __name__ == "__main__":  # pragma: no cover
    main()
