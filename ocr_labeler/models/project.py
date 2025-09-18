from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


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

    def page_count(self) -> int:
        """Return the number of pages in this project."""
        return len(self.pages)
