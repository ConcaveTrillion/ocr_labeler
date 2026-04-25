#!/usr/bin/env python3
"""One-time script to generate browser test fixtures.

This script creates a sample project with pre-saved OCR page JSON files
so that browser tests never need DocTR / ML models at runtime.

It can use EITHER:
  1. Pre-existing labeled-ocr data from ../data/labeled-ocr/ (preferred, no ML needed)
  2. Synthetic page data as a fallback (no external deps)

Usage:
    cd pd-ocr-labeler
    uv run python tests/browser/generate_test_fixtures.py              # uses labeled-ocr
    uv run python tests/browser/generate_test_fixtures.py --synthetic  # synthetic data

After running:
  - tests/browser/fixtures/browser-test-project/ will contain 3 page images + pages.json
  - tests/browser/fixtures/saved-pages/ will contain pre-saved OCR JSON + image copies

Commit the generated fixtures so tests don't need ML models.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # pd-ocr-labeler/
DATA_ROOT = REPO_ROOT.parent / "data"  # ../data/

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PROJECT_DIR = FIXTURES_DIR / "browser-test-project"
SAVED_PAGES_DIR = FIXTURES_DIR / "saved-pages"

SOURCE_PROJECT_ID = "projectID629292e7559a8"

# Source directories
SOURCE_IMAGES_DIR = DATA_ROOT / "source-pgdp-data" / "output" / SOURCE_PROJECT_ID
LABELED_OCR_DIR = DATA_ROOT / "labeled-ocr"
# Fallback source in tests/test-data
FALLBACK_SOURCE = (
    REPO_ROOT / "tests" / "test-data" / "pgdp-projects" / SOURCE_PROJECT_ID
)

# Selected pages: source_filename -> (dest_page_number, labeled_ocr_0based_index)
# Labeled-ocr uses 0-based index: _0 = 001.png, _3 = 004.png, _21 = 022.png
SELECTED_PAGES: dict[str, tuple[int, int]] = {
    "001.png": (1, 0),  # title page
    "004.png": (2, 3),  # frontispiece (has text)
    "022.png": (3, 21),  # text-heavy page
}

DEST_PROJECT_NAME = "browser-test-project"


def resolve_source_dir() -> Path:
    """Find the source images directory, preferring data/ over tests/test-data/."""
    if SOURCE_IMAGES_DIR.exists():
        return SOURCE_IMAGES_DIR
    if FALLBACK_SOURCE.exists():
        return FALLBACK_SOURCE
    print(
        f"ERROR: No source images found at:\n  {SOURCE_IMAGES_DIR}\n  {FALLBACK_SOURCE}"
    )
    sys.exit(1)


def copy_source_images(source_dir: Path) -> dict[str, str]:
    """Copy selected page images and build ground truth mapping."""
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    source_gt_path = source_dir / "pages.json"
    source_gt: dict[str, str] = {}
    if source_gt_path.exists():
        source_gt = json.loads(source_gt_path.read_text(encoding="utf-8"))

    ground_truth: dict[str, str] = {}

    for src_filename, (dest_num, _labeled_idx) in SELECTED_PAGES.items():
        src_path = source_dir / src_filename
        if not src_path.exists():
            print(f"  WARNING: {src_path} not found, skipping")
            continue

        dest_filename = f"{dest_num:03d}.png"
        shutil.copy2(src_path, PROJECT_DIR / dest_filename)
        print(f"  Copied {src_filename} -> {dest_filename}")

        if src_filename in source_gt:
            ground_truth[dest_filename] = source_gt[src_filename]
        else:
            ground_truth[dest_filename] = f"[Ground truth for {src_filename}]"

    return ground_truth


def copy_labeled_ocr_fixtures() -> bool:
    """Copy pre-existing labeled-ocr JSON + images as the saved-pages fixtures.

    Returns True if all pages were found and copied.
    """
    SAVED_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True

    for _src_filename, (dest_num, labeled_idx) in SELECTED_PAGES.items():
        src_json = LABELED_OCR_DIR / f"{SOURCE_PROJECT_ID}_{labeled_idx}.json"
        src_png = LABELED_OCR_DIR / f"{SOURCE_PROJECT_ID}_{labeled_idx}.png"

        dest_json = SAVED_PAGES_DIR / f"{DEST_PROJECT_NAME}_{dest_num:03d}.json"
        dest_png = SAVED_PAGES_DIR / f"{DEST_PROJECT_NAME}_{dest_num:03d}.png"

        if not src_json.exists():
            print(f"  WARNING: {src_json.name} not found in labeled-ocr")
            all_ok = False
            continue

        # Read, patch source_path, and write
        with open(src_json, encoding="utf-8") as f:
            ocr_data = json.load(f)
        ocr_data["source_path"] = f"{dest_num:03d}.png"
        with open(dest_json, "w", encoding="utf-8") as f:
            json.dump(ocr_data, f, indent=2, ensure_ascii=False)
        print(f"  Saved {dest_json.name}")

        if src_png.exists():
            shutil.copy2(src_png, dest_png)
            print(f"  Saved {dest_png.name}")
        else:
            # Copy from the project dir instead
            project_png = PROJECT_DIR / f"{dest_num:03d}.png"
            if project_png.exists():
                shutil.copy2(project_png, dest_png)
                print(f"  Saved {dest_png.name} (from project)")

    return all_ok


def generate_synthetic_fixtures(ground_truth: dict[str, str]) -> None:
    """Generate minimal synthetic page JSON fixtures (no external deps)."""
    SAVED_PAGES_DIR.mkdir(parents=True, exist_ok=True)

    for image_path in sorted(PROJECT_DIR.glob("*.png")):
        page_num = int(image_path.stem)
        gt_text = ground_truth.get(image_path.name, "Sample text")

        # Build synthetic words from ground truth text
        line_blocks = []
        for line_idx, line_text in enumerate(gt_text.strip().split("\n")[:10]):
            line_words = []
            for word_idx, word_text in enumerate(line_text.split()[:15]):
                if not word_text.strip():
                    continue
                x0 = 0.1 + (word_idx * 0.06)
                y0 = 0.05 + (line_idx * 0.05)
                line_words.append(
                    {
                        "type": "Word",
                        "text": word_text,
                        "bounding_box": {
                            "top_left": {"x": round(x0, 4), "y": round(y0, 4)},
                            "bottom_right": {
                                "x": round(min(x0 + 0.05, 0.9), 4),
                                "y": round(y0 + 0.03, 4),
                            },
                        },
                        "confidence": 0.95,
                        "ocr_labels": None,
                    }
                )
            if line_words:
                line_blocks.append(
                    {
                        "type": "Block",
                        "child_type": "WORDS",
                        "block_category": "LINE",
                        "bounding_box": {
                            "top_left": line_words[0]["bounding_box"]["top_left"],
                            "bottom_right": line_words[-1]["bounding_box"][
                                "bottom_right"
                            ],
                        },
                        "block_labels": None,
                        "items": line_words,
                    }
                )

        items = []
        if line_blocks:
            items = [
                {
                    "type": "Block",
                    "child_type": "BLOCKS",
                    "block_category": "BLOCK",
                    "bounding_box": {
                        "top_left": line_blocks[0]["bounding_box"]["top_left"],
                        "bottom_right": line_blocks[-1]["bounding_box"]["bottom_right"],
                    },
                    "block_labels": None,
                    "items": [
                        {
                            "type": "Block",
                            "child_type": "BLOCKS",
                            "block_category": "PARAGRAPH",
                            "bounding_box": {
                                "top_left": line_blocks[0]["bounding_box"]["top_left"],
                                "bottom_right": line_blocks[-1]["bounding_box"][
                                    "bottom_right"
                                ],
                            },
                            "block_labels": None,
                            "items": line_blocks,
                        }
                    ],
                }
            ]

        json_data = {
            "source_lib": "synthetic-test-fixture",
            "source_path": image_path.name,
            "pages": [
                {
                    "type": "Page",
                    "width": 800,
                    "height": 1000,
                    "page_index": 0,
                    "bounding_box": None,
                    "items": items,
                }
            ],
        }

        json_filename = f"{DEST_PROJECT_NAME}_{page_num:03d}.json"
        with open(SAVED_PAGES_DIR / json_filename, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"    Saved {json_filename}")

        image_dest = SAVED_PAGES_DIR / f"{DEST_PROJECT_NAME}_{page_num:03d}.png"
        shutil.copy2(image_path, image_dest)
        print(f"    Saved {image_dest.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source-project",
        type=Path,
        default=None,
        help="Override source project directory (default: auto-detect from data/)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate synthetic fixtures instead of using labeled-ocr data",
    )
    args = parser.parse_args()

    source_dir = args.source_project or resolve_source_dir()
    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        sys.exit(1)

    print(f"Source project: {source_dir}")
    print(f"Labeled OCR dir: {LABELED_OCR_DIR}")
    print(f"Target fixtures: {FIXTURES_DIR}")
    print()

    print("Step 1: Copying source images...")
    ground_truth = copy_source_images(source_dir)

    print("\nStep 2: Writing pages.json...")
    pages_json_path = PROJECT_DIR / "pages.json"
    with open(pages_json_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    print(f"  Saved {pages_json_path}")

    print("\nStep 3: Generating OCR fixtures...")
    if args.synthetic:
        generate_synthetic_fixtures(ground_truth)
    elif LABELED_OCR_DIR.exists():
        print("  Using pre-existing labeled-ocr data (no ML models needed)...")
        if not copy_labeled_ocr_fixtures():
            print("  Some labeled-ocr files missing, falling back to synthetic.")
            generate_synthetic_fixtures(ground_truth)
    else:
        print("  No labeled-ocr data found, generating synthetic fixtures.")
        generate_synthetic_fixtures(ground_truth)

    print("\nDone! Fixtures are ready at:")
    print(f"  Project: {PROJECT_DIR}")
    print(f"  Saved pages: {SAVED_PAGES_DIR}")
    print("\nCommit these fixtures so browser tests don't need ML models.")


if __name__ == "__main__":
    main()
