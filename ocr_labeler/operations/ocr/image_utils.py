"""Shared image cropping utilities for OCR element bounding boxes."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def crop_image_to_bbox(
    element: object,
    page_image: np.ndarray | None,
    label: str = "element",
) -> np.ndarray | None:
    """Crop a region from *page_image* using the bounding box of *element*.

    Parameters
    ----------
    element:
        Any object with a ``bounding_box`` attribute (Word, Line, etc.).
    page_image:
        The full page image as a NumPy array (H×W or H×W×C).
    label:
        A human-readable label used in debug log messages.

    Returns
    -------
    numpy.ndarray | None
        The cropped sub-image, or ``None`` when cropping is impossible.
    """
    if element is None or page_image is None:
        logger.debug("No element or page_image for %s", label)
        return None

    bbox = getattr(element, "bounding_box", None)
    if not bbox:
        logger.debug("No bounding_box found for %s", label)
        return None

    try:
        height, width = page_image.shape[:2]

        if bbox.is_normalized:
            pixel_bbox = bbox.scale(width, height)
        else:
            pixel_bbox = bbox

        x1 = int(pixel_bbox.minX)
        y1 = int(pixel_bbox.minY)
        x2 = int(pixel_bbox.maxX)
        y2 = int(pixel_bbox.maxY)

        if x1 >= x2 or y1 >= y2:
            logger.debug(
                "Invalid bbox coordinates for %s: (%s, %s, %s, %s)",
                label,
                x1,
                y1,
                x2,
                y2,
            )
            return None

        # Clamp to image bounds
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(x1 + 1, min(x2, width))
        y2 = max(y1 + 1, min(y2, height))

        cropped = page_image[y1:y2, x1:x2]

        if cropped.size == 0:
            logger.debug("Empty crop for %s at (%s, %s, %s, %s)", label, x1, y1, x2, y2)
            return None

        return cropped

    except Exception as e:
        logger.debug("Error cropping image for %s: %s", label, e)
        return None


def is_geometry_normalization_error(error: Exception) -> bool:
    """Return True for known malformed-bbox normalization failures."""
    message = str(error)
    return "NoneType" in message and "is_normalized" in message
