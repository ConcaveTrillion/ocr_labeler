"""Utilities and CLI for cleaning local runtime state.

This module removes local logs and rendered image cache files from both:
1) Current OS-aware persistence roots, and
2) Legacy workspace-local paths used by older setups.
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from pd_ocr_labeler.operations.persistence.persistence_paths_operations import (
    PersistencePathsOperations,
)


@dataclass(slots=True)
class CleanupResult:
    """Aggregate counts for a cleanup operation."""

    files_removed: int = 0
    dirs_removed: int = 0
    failures: int = 0


def _remove_tree_contents(directory: Path) -> CleanupResult:
    """Remove all children under a directory while keeping the directory itself."""
    result = CleanupResult()
    if not directory.exists():
        return result

    for child in directory.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
                result.dirs_removed += 1
            else:
                child.unlink()
                result.files_removed += 1
        except OSError:
            result.failures += 1

    return result


def _remove_log_files(directory: Path) -> CleanupResult:
    """Remove *.log files recursively in a directory tree."""
    result = CleanupResult()
    if not directory.exists():
        return result

    for log_file in directory.rglob("*.log"):
        try:
            if log_file.is_file():
                log_file.unlink()
                result.files_removed += 1
        except OSError:
            result.failures += 1

    return result


def _merge(base: CleanupResult, update: CleanupResult) -> CleanupResult:
    base.files_removed += update.files_removed
    base.dirs_removed += update.dirs_removed
    base.failures += update.failures
    return base


def cleanup_logs(workspace_root: Path) -> CleanupResult:
    """Clean session logs from modern and legacy locations."""
    targets = {
        PersistencePathsOperations.get_logs_root(),
        workspace_root / "logs",
    }

    result = CleanupResult()
    for target in targets:
        _merge(result, _remove_log_files(target))
    return result


def cleanup_image_cache(workspace_root: Path) -> CleanupResult:
    """Clean rendered page image cache from modern and legacy locations."""
    targets = {
        PersistencePathsOperations.get_page_image_cache_root(),
        workspace_root / "local-data" / "labeled-ocr" / "cache",
    }

    result = CleanupResult()
    for target in targets:
        _merge(result, _remove_tree_contents(target))
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean OCR Labeler local runtime state."
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root used for legacy local-data/logs paths (default: current directory).",
    )
    parser.add_argument("--logs", action="store_true", help="Clean session log files.")
    parser.add_argument(
        "--cache", action="store_true", help="Clean rendered image cache."
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    clean_logs = args.logs
    clean_cache = args.cache
    if not clean_logs and not clean_cache:
        clean_logs = True
        clean_cache = True

    workspace_root = args.workspace_root.resolve()
    overall = CleanupResult()

    if clean_logs:
        logs_result = cleanup_logs(workspace_root)
        _merge(overall, logs_result)
        print(
            "Logs cleaned: files_removed="
            f"{logs_result.files_removed}, failures={logs_result.failures}"
        )

    if clean_cache:
        cache_result = cleanup_image_cache(workspace_root)
        _merge(overall, cache_result)
        print(
            "Image cache cleaned: files_removed="
            f"{cache_result.files_removed}, dirs_removed={cache_result.dirs_removed}, failures={cache_result.failures}"
        )

    if overall.failures > 0:
        print(f"Cleanup completed with {overall.failures} failure(s).")
        return 1

    print("Cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
