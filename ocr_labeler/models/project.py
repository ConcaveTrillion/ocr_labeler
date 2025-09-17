from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from pd_book_tools.ocr.page import Page

from ..state.operations.page_operations import PageOperations

logger = logging.getLogger(__name__)

# Create a module-level PageOperations instance for use in Project methods
_page_operations = PageOperations()


@dataclass
class Project:
    """Project view model with lazy page instantiation.

    Instead of constructing a ``Page`` object for every image up-front, we keep the
    list of image paths and only create the corresponding ``Page`` instance when it
    is first accessed (current page navigation). This keeps initial project load
    fast for large collections.
    """

    # Parallel arrays: pages holds either a loaded Page or None placeholder.
    pages: list[Page | None] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)

    # Ground Truth mapping loaded from a project-level pages.json file: {"001.png": "Ground truth text"}
    ground_truth_map: dict[str, str] = field(default_factory=dict)

    # Optional callable to lazily construct a full OCR Page from an image path.
    # Signature: (image_path: Path, index: int) -> Page
    page_parser: Optional[Callable[[Path, int, str, Optional[bool]], Page]] = None

    def _ensure_page(self, index: int) -> Optional[Page]:
        """Ensure that the Page at *index* is loaded, loading it if necessary."""
        if not self.pages:
            logger.info("_ensure_page: no pages loaded yet")
            return None
        if not (0 <= index < len(self.pages)):
            logger.warning(
                "_ensure_page: index %s out of range (0..%s)",
                index,
                len(self.pages) - 1,
            )
            return None
        if self.pages[index] is None:
            img_path = self.image_paths[index]
            logger.debug(
                "_ensure_page: cache miss for index=%s path=%s (loader=%s)",
                index,
                img_path,
                bool(self.page_parser),
            )
            if self.page_parser:
                try:
                    gt_text = (
                        _page_operations.find_ground_truth_text(
                            img_path.name, self.ground_truth_map
                        )
                        or ""
                    )
                    page_obj = self.page_parser(img_path, index, gt_text)
                    logger.debug(
                        "_ensure_page: loader created page index=%s name=%s",
                        index,
                        getattr(page_obj, "name", img_path.name),
                    )
                    # Attach a couple of convenience attrs expected elsewhere
                    if not hasattr(page_obj, "image_path"):
                        page_obj.image_path = img_path  # type: ignore[attr-defined]
                    if not hasattr(page_obj, "name"):
                        page_obj.name = img_path.name  # type: ignore[attr-defined]
                    if not hasattr(page_obj, "index"):
                        page_obj.index = index  # type: ignore[attr-defined]
                    self.pages[index] = page_obj
                except Exception:  # pragma: no cover - defensive
                    logger.exception(
                        "_ensure_page: loader failed for index=%s path=%s; using fallback page",
                        index,
                        img_path,
                    )
                    # Fallback: still display original image even if OCR failed
                    page = Page(width=0, height=0, page_index=index, items=[])
                    page.image_path = img_path  # type: ignore[attr-defined]
                    page.name = img_path.name  # type: ignore[attr-defined]
                    page.index = index  # type: ignore[attr-defined]
                    # Add ground truth if available even for fallback page
                    try:
                        gt_text = _page_operations.find_ground_truth_text(
                            img_path.name, self.ground_truth_map
                        )
                        if gt_text is not None:
                            page.add_ground_truth(gt_text)  # type: ignore[attr-defined]
                            logger.debug(
                                "_ensure_page: injected ground truth (fallback) for %s",
                                img_path.name,
                            )
                    except Exception:
                        logger.exception(
                            "_ensure_page: ground truth injection failed (fallback) for %s",
                            img_path.name,
                        )
                        pass
                    try:  # best-effort load image
                        from cv2 import imread as cv2_imread  # type: ignore

                        img = cv2_imread(str(img_path))
                        if img is not None:
                            page.cv2_numpy_page_image = img  # type: ignore[attr-defined]
                            logger.debug(
                                "_ensure_page: attached cv2 image for %s", img_path.name
                            )
                    except Exception:
                        logger.debug(
                            "_ensure_page: cv2 load failed for %s", img_path.name
                        )
                        pass
                    self.pages[index] = page
            else:
                # No loader provided: keep legacy minimal placeholder behavior
                logger.debug(
                    "_ensure_page: no loader provided, creating placeholder page for index=%s",
                    index,
                )
                page = Page(width=0, height=0, page_index=index, items=[])
                page.image_path = img_path  # type: ignore[attr-defined]
                page.name = img_path.name  # type: ignore[attr-defined]
                page.index = index  # type: ignore[attr-defined]
                try:
                    gt_text = _page_operations.find_ground_truth_text(
                        img_path.name, self.ground_truth_map
                    )
                    if gt_text is not None:
                        page.add_ground_truth(gt_text)  # type: ignore[attr-defined]
                        logger.debug(
                            "_ensure_page: injected ground truth (no-loader) for %s",
                            img_path.name,
                        )
                except Exception:
                    logger.exception(
                        "_ensure_page: ground truth injection failed (no-loader) for %s",
                        img_path.name,
                    )
                    pass
                self.pages[index] = page
        else:
            logger.debug("_ensure_page: cache hit for index=%s", index)
        return self.pages[index]

    def get_page(self, index: int) -> Optional[Page]:
        """Get page at the specified index, loading it if necessary."""
        logger.debug("get_page: index=%s", index)
        return self._ensure_page(index)

    def page_count(self) -> int:
        """Return the number of pages in this project."""
        return len(self.pages)
