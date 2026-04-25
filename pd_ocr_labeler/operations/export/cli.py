"""CLI entry point for DocTR training-data export.

Usage examples::

    # Standard export (detection + recognition) — all validated pages
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output

    # Include all pages (skip validation check)
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --all-pages

    # Include pages that have ground truth (even if not word-validated)
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --require-gt

    # Export only italic words
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --style italics

    # Export only small-caps words
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --style "small caps"

    # Export multivariate classification dataset
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --classification

    # Detection only (no recognition crops)
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --detection-only

    # Recognition only (no detection polygons)
    pd-ocr-labeler-export /path/to/labeled-ocr /path/to/output --recognition-only
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def build_parser(
    prog: str | None = None,
) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description="Export DocTR training datasets from labeled OCR pages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "labeled_dir",
        type=Path,
        help="Directory containing labeled JSON+image pairs",
    )
    p.add_argument(
        "output_dir",
        type=Path,
        help="Root output directory for exported datasets",
    )
    p.add_argument(
        "--prefix",
        default="",
        help="Filename prefix for exported images (default: none)",
    )

    # --- Validation mode ---
    val_group = p.add_mutually_exclusive_group()
    val_group.add_argument(
        "--all-pages",
        action="store_true",
        help="Export all pages regardless of validation state",
    )
    val_group.add_argument(
        "--require-gt",
        action="store_true",
        help="Export pages that have ground truth text (even if not word-validated)",
    )

    # --- Export type ---
    type_group = p.add_mutually_exclusive_group()
    type_group.add_argument(
        "--style",
        action="append",
        dest="styles",
        metavar="LABEL",
        help="Export only words matching this text style label (can be repeated). "
        'E.g. --style italics --style "small caps"',
    )
    type_group.add_argument(
        "--component",
        action="append",
        dest="components",
        metavar="LABEL",
        help="Export only words matching this word component (can be repeated). "
        'E.g. --component "footnote marker"',
    )
    type_group.add_argument(
        "--classification",
        action="store_true",
        help="Export multivariate classification dataset (recognition labels include "
        "all style/component flags as a dict)",
    )

    # --- Dataset selection ---
    ds_group = p.add_mutually_exclusive_group()
    ds_group.add_argument(
        "--detection-only",
        action="store_true",
        help="Export detection data only (skip recognition crops)",
    )
    ds_group.add_argument(
        "--recognition-only",
        action="store_true",
        help="Export recognition data only (skip detection polygons)",
    )

    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    level = logging.WARNING
    if args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose >= 1:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Validate inputs
    if not args.labeled_dir.is_dir():
        parser.error(f"Labeled directory does not exist: {args.labeled_dir}")

    # Select validation predicate
    from pd_ocr_labeler.operations.export.doctr_export import (
        DocTRExportOperations,
        page_always_valid,
        page_has_ground_truth,
        page_is_validated,
    )

    if args.all_pages:
        validation_predicate = page_always_valid
    elif args.require_gt:
        validation_predicate = page_has_ground_truth
    else:
        validation_predicate = page_is_validated

    detection = not args.recognition_only
    recognition = not args.detection_only

    exporter = DocTRExportOperations(
        labeled_data_dir=args.labeled_dir,
        output_dir=args.output_dir,
        validation_predicate=validation_predicate,
    )

    # Dispatch to the right export mode
    if args.classification:
        logger.info("Exporting multivariate classification dataset")
        stats = exporter.export_classification(prefix=args.prefix)
    elif args.styles:
        logger.info("Exporting labeled dataset (styles: %s)", args.styles)
        stats = exporter.export_labeled(
            style_labels=args.styles,
            prefix=args.prefix,
            detection=detection,
            recognition=recognition,
        )
    elif args.components:
        logger.info("Exporting labeled dataset (components: %s)", args.components)
        stats = exporter.export_labeled(
            word_components=args.components,
            prefix=args.prefix,
            detection=detection,
            recognition=recognition,
        )
    else:
        logger.info("Exporting standard dataset")
        stats = exporter.export_standard(
            prefix=args.prefix,
            detection=detection,
            recognition=recognition,
        )

    print(stats.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
