"""Image caching operations for page images.

Pure functions for encoding, hashing, and caching page images to disk.
Extracted from PageStateViewModel to keep viewmodel focused on UI state.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Maximum longest dimension for cached images.
_MAX_CACHED_DIMENSION = 1200

# Supported on-disk extensions.
_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def compute_image_hash(np_img: np.ndarray | None) -> str:
    """Compute a content hash of a numpy image for caching purposes."""
    if np_img is None:
        return "none"
    try:
        contiguous = np.ascontiguousarray(np_img)
        shape_data = repr(contiguous.shape).encode("utf-8")
        dtype_data = str(contiguous.dtype).encode("utf-8")
        image_data = memoryview(contiguous).tobytes()
        return hashlib.md5(
            shape_data + b"|" + dtype_data + b"|" + image_data
        ).hexdigest()
    except Exception:
        import time

        return f"fallback_{time.time()}"


def normalize_cache_extension(suffix: str | None) -> str:
    """Normalize a file extension to a supported cache format."""
    value = str(suffix or "").strip().lower()
    if not value:
        return ".jpg"
    if not value.startswith("."):
        value = f".{value}"
    if value in _SUPPORTED_EXTENSIONS:
        return value
    return ".jpg"


def resolve_cache_image_extension(
    current_page: object,
    project: object | None,
    page_index: int,
) -> str:
    """Resolve image extension from page/project metadata; fallback to .jpg."""
    candidates: list[object] = []
    candidates.append(getattr(current_page, "image_path", None))
    candidates.append(getattr(current_page, "name", None))

    image_paths = getattr(project, "image_paths", None) if project else None
    if isinstance(image_paths, list) and 0 <= page_index < len(image_paths):
        candidates.append(image_paths[page_index])

    for candidate in candidates:
        try:
            suffix = Path(str(candidate)).suffix.lower()
        except Exception:
            continue
        normalized = normalize_cache_extension(suffix)
        if normalized:
            return normalized

    return ".jpg"


def normalize_cached_filenames(cached_filenames: object) -> dict[str, str]:
    """Return cached filenames only when they are stored as a plain mapping."""
    if isinstance(cached_filenames, dict):
        return cached_filenames
    return {}


def url_from_cached_filename(filename: str) -> str:
    """Reconstruct a /_word_image_cache/ static URL from a bare filename.

    The filename format is ``{project}_{page:03d}_{type}_{hash}{ext}``.
    The hash embedded in the stem is reused as the cache-busting query param.
    """
    stem = Path(filename).stem
    hash_part = stem.rsplit("_", 1)[-1]
    return f"/_word_image_cache/{filename}?v={hash_part[:8]}"


def cache_image_to_disk(
    np_img: np.ndarray | None,
    image_type: str,
    page_index: int,
    project_id: str,
    image_extension: str,
    cache_dir: Path,
) -> str:
    """Write a processed page image to the shared on-disk cache and return its static URL.

    The cache is keyed by project, page, image type, and a content hash.
    Returns a /_word_image_cache/ static URL, or "" on failure.
    """
    if np_img is None:
        return ""

    shape = getattr(np_img, "shape", None)
    if not isinstance(shape, tuple):
        return ""

    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        import cv2

        # Normalise colour space so all cached files are consistent.
        if len(shape) == 2:
            np_img = cv2.cvtColor(np_img, cv2.COLOR_GRAY2RGB)
        elif len(shape) > 2 and shape[2] == 4:
            np_img = cv2.cvtColor(np_img, cv2.COLOR_RGBA2RGB)

        height, width = np_img.shape[:2]
        if width > _MAX_CACHED_DIMENSION or height > _MAX_CACHED_DIMENSION:
            if width > height:
                new_width = _MAX_CACHED_DIMENSION
                new_height = max(1, int(height * _MAX_CACHED_DIMENSION / width))
            else:
                new_height = _MAX_CACHED_DIMENSION
                new_width = max(1, int(width * _MAX_CACHED_DIMENSION / height))
            np_img = cv2.resize(
                np_img, (new_width, new_height), interpolation=cv2.INTER_AREA
            )

        img_hash = compute_image_hash(np_img)
        safe_page_index = max(-1, int(page_index))
        safe_project_id = (project_id or "project").strip() or "project"
        safe_image_type = (image_type or "image").strip() or "image"
        page_number = max(1, safe_page_index + 1)
        normalized_extension = normalize_cache_extension(image_extension)
        file_name = f"{safe_project_id}_{page_number:03d}_{safe_image_type}_{img_hash}{normalized_extension}"
        output_path = cache_dir / file_name

        if not output_path.exists():
            encode_options: list[int] = []
            if normalized_extension in {".jpg", ".jpeg"}:
                encode_options = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            success, buffer = cv2.imencode(normalized_extension, np_img, encode_options)
            if not success:
                return ""
            output_path.write_bytes(buffer.tobytes())

        return f"/_word_image_cache/{file_name}?v={img_hash[:8]}"
    except Exception:
        logger.debug("Failed caching image to disk", exc_info=True)
        return ""
