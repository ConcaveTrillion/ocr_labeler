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
        cropped = bbox.crop_image(page_image)
        if cropped is None:
            logger.debug("Empty crop for %s", label)
        return cropped
    except Exception as e:
        logger.debug("Error cropping image for %s: %s", label, e)
        return None


def is_geometry_normalization_error(error: Exception) -> bool:
    """Return True for known malformed-bbox normalization failures."""
    from pd_book_tools.geometry.bounding_box import BoundingBox

    return BoundingBox.is_geometry_normalization_error(error)
