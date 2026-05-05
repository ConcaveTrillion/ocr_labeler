"""Pre-warm the HF Hub cache for the labeler's default OCR + layout models.

Used by ``make prefetch-models`` and called automatically at the end of
``make setup`` / ``make install`` so the first-page OCR isn't a 150 MB
surprise. Skippable with ``NO_PREFETCH=1``.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Prefetch the canonical OCR detection + recognition + layout models.

    Returns a process exit code: 0 on success, 0 (silent) when
    ``NO_PREFETCH`` is truthy, 1 on import / runtime failure.
    """
    if _env_truthy("NO_PREFETCH"):
        print("NO_PREFETCH set — skipping HF model prefetch.", flush=True)
        return 0

    try:
        from pd_book_tools.hf import (
            DEFAULT_DET_FILENAME,
            DEFAULT_HF_REPO,
            DEFAULT_RECO_FILENAME,
            OCR_MODEL_SIDECARS,
            hf_download,
            prefetch_layout_files,
            resolve_layout_source,
        )
    except ImportError as exc:
        print(
            f"ERROR: pd-book-tools is missing or out of date ({exc}). "
            "Run `make setup` to install/upgrade it.",
            file=sys.stderr,
        )
        return 1

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print(
        f"Prefetching OCR detection + recognition models from {DEFAULT_HF_REPO}...",
        flush=True,
    )
    try:
        hf_download(
            DEFAULT_HF_REPO,
            DEFAULT_DET_FILENAME,
            None,
            sidecars=OCR_MODEL_SIDECARS,
        )
        hf_download(
            DEFAULT_HF_REPO,
            DEFAULT_RECO_FILENAME,
            None,
            sidecars=OCR_MODEL_SIDECARS,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort prefetch
        print(f"WARNING: OCR model prefetch failed: {exc}", file=sys.stderr)
        return 1

    # Default layout backend for the labeler is pp-doclayout-plus-l, mirroring
    # cli + prep. The adapter knows the canonical repo + revision.
    print("Prefetching default layout model...", flush=True)
    try:
        repo, revision, descriptor = resolve_layout_source("pp-doclayout-plus-l")
        if repo:
            print(f"  layout source: {descriptor}", flush=True)
            prefetch_layout_files(repo, revision)
    except Exception as exc:  # noqa: BLE001 — layout deps may be optional
        print(f"WARNING: layout model prefetch failed: {exc}", file=sys.stderr)
        return 1

    print("✅ Prefetch complete.", flush=True)
    return 0


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
