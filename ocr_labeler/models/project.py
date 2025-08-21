from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable
from pd_book_tools.ocr.page import Page
from ..state.ground_truth import find_ground_truth_text

@dataclass
class ProjectVM:
    """Project view model with lazy page instantiation.

    Instead of constructing a ``Page`` object for every image up-front, we keep the
    list of image paths and only create the corresponding ``Page`` instance when it
    is first accessed (current page navigation). This keeps initial project load
    fast for large collections.
    """

    # Parallel arrays: pages holds either a loaded Page or None placeholder.
    pages: list[Page | None] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    current_page_index: int = 0
    # Optional mapping loaded from a project-level pages.json file: {"001.png": "Ground truth text"}
    ground_truth_map: dict[str, str] = field(default_factory=dict)
    # Optional callable to lazily construct a full OCR Page from an image path.
    # Signature: (image_path: Path, index: int) -> Page
    page_loader: Optional[Callable[[Path, int], Page]] = None

    def _ensure_page(self, index: int) -> Optional[Page]:
        if not (0 <= index < len(self.pages)):
            return None
        if self.pages[index] is None:
            img_path = self.image_paths[index]
            if self.page_loader:
                try:
                    page_obj = self.page_loader(img_path, index)
                    # Attach a couple of convenience attrs expected elsewhere
                    if not hasattr(page_obj, "image_path"):
                        page_obj.image_path = img_path  # type: ignore[attr-defined]
                    if not hasattr(page_obj, "name"):
                        page_obj.name = img_path.name  # type: ignore[attr-defined]
                    if not hasattr(page_obj, "index"):
                        page_obj.index = index  # type: ignore[attr-defined]
                    # Inject ground truth text if available (keyed by image filename)
                    try:
                        gt_text = find_ground_truth_text(img_path.name, self.ground_truth_map)
                        if gt_text is not None:
                            page_obj.ground_truth_text = gt_text  # type: ignore[attr-defined]
                    except Exception:  # pragma: no cover - best effort
                        pass
                    self.pages[index] = page_obj
                except Exception:  # pragma: no cover - defensive
                    # Fallback: still display original image even if OCR failed
                    page = Page(width=0, height=0, page_index=index, items=[])
                    page.image_path = img_path  # type: ignore[attr-defined]
                    page.name = img_path.name  # type: ignore[attr-defined]
                    page.index = index  # type: ignore[attr-defined]
                    # Add ground truth if available even for fallback page
                    try:
                        gt_text = find_ground_truth_text(img_path.name, self.ground_truth_map)
                        if gt_text is not None:
                            page.ground_truth_text = gt_text  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    try:  # best-effort load image
                        from cv2 import imread as cv2_imread  # type: ignore
                        img = cv2_imread(str(img_path))
                        if img is not None:
                            page.cv2_numpy_page_image = img  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    self.pages[index] = page
            else:
                # No loader provided: keep legacy minimal placeholder behavior
                page = Page(width=0, height=0, page_index=index, items=[])
                page.image_path = img_path  # type: ignore[attr-defined]
                page.name = img_path.name  # type: ignore[attr-defined]
                page.index = index  # type: ignore[attr-defined]
                try:
                    gt_text = find_ground_truth_text(img_path.name, self.ground_truth_map)
                    if gt_text is not None:
                        page.ground_truth_text = gt_text  # type: ignore[attr-defined]
                except Exception:
                    pass
                self.pages[index] = page
        return self.pages[index]

    def current_page(self) -> Optional[Page]:
        return self._ensure_page(self.current_page_index)

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1

    def next_page(self):
        if self.current_page_index < len(self.pages) - 1:
            self.current_page_index += 1

    def goto_page_index(self, index: int):
        """Jump to a page by zero-based index, clamping to valid range."""
        if not self.pages:
            self.current_page_index = -1
            return
        if index < 0:
            index = 0
        if index >= len(self.pages):
            index = len(self.pages) - 1
        self.current_page_index = index

    def goto_page_number(self, number: int):
        """Jump to a page by 1-based page number (user facing)."""
        self.goto_page_index(number - 1)
