from __future__ import annotations
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_EXTS = (".png", ".jpg", ".jpeg")


def _normalize_entries(data: dict) -> dict[str, str]:
    norm: dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(k, str):
            continue
        text_val: str | None = v if isinstance(v, str) else (str(v) if v is not None else None)
        if text_val is None:
            continue
        norm[k] = text_val
        lower_k = k.lower()
        norm.setdefault(lower_k, text_val)
        if '.' not in k:
            for ext in IMAGE_EXTS:
                norm.setdefault(f"{k}{ext}", text_val)
                norm.setdefault(f"{k}{ext}".lower(), text_val)
    return norm


def load_ground_truth_map(directory: Path) -> dict[str, str]:
    pages_json = directory / "pages.json"
    if not pages_json.exists():
        logger.info("No pages.json found in %s", directory)
        return {}
    try:
        raw_text = pages_json.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        if isinstance(data, dict):
            norm = _normalize_entries(data)
            logger.info("Loaded %d ground truth entries from %s", len(norm), pages_json)
            return norm
        logger.warning("pages.json root is not an object (dict): %s", pages_json)
    except Exception as exc:  # pragma: no cover - robustness
        logger.warning("Failed to load pages.json (%s): %s", pages_json, exc)
    return {}


def reload_ground_truth_into_project(state):  # type: ignore[override]
    """Re-read pages.json and update ground truth on already-loaded pages."""
    pages_json = state.project_root / "pages.json"
    if not pages_json.exists():
        logger.info("reload_ground_truth: no pages.json at %s", pages_json)
        return
    try:
        data = json.loads(pages_json.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("reload_ground_truth: root not dict")
            return
        norm_map = _normalize_entries(data)
        state.project.ground_truth_map = norm_map
        updated = 0
        for page in state.project.pages:
            if page is None:
                continue
            key_variants = [
                getattr(page, 'name', ''),
                getattr(page, 'name', '').lower(),
            ]
            for kv in list(key_variants):
                if '.' in kv:
                    base = kv.rsplit('.', 1)[0]
                    key_variants.append(base)
                    key_variants.append(base.lower())
            for kv in key_variants:
                if kv in norm_map:
                    try:
                        page.ground_truth_text = norm_map[kv]  # type: ignore[attr-defined]
                        updated += 1
                        break
                    except Exception:
                        pass
        logger.info("reload_ground_truth: updated ground truth on %d pages", updated)
        state.notify()
    except Exception as exc:  # pragma: no cover
        logger.warning("reload_ground_truth failed: %s", exc)


def find_ground_truth_text(name: str, ground_truth_map: dict[str, str]) -> str | None:
    """Return ground truth text for a given page *name* using variant lookup.

    The normalization process adds multiple keys (with/without extension, lowercase).
    However, some initial lookups (e.g. during first page load) previously only tried
    the exact filename. This helper attempts a list of variants in priority order.

    Parameters
    ----------
    name: str
        The image filename (e.g. ``001.png``) or bare page identifier.
    ground_truth_map: dict[str, str]
        Normalized mapping produced by ``load_ground_truth_map``.
    """
    if not name:
        return None
    candidates: list[str] = []
    # Original provided name
    candidates.append(name)
    # Lowercase variant
    candidates.append(name.lower())
    # If name has extension, add base name variants; else add ext variants (handled by normalization)
    if "." in name:
        base = name.rsplit(".", 1)[0]
        candidates.extend([base, base.lower()])
    # Deduplicate while preserving order
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if c in ground_truth_map:
            return ground_truth_map[c]
    return None
