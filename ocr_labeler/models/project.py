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

    # Project metadata
    version: str = "1.0"
    source_lib: str = "doctr-pgdp-labeled"
    project_id: str = ""
    source_path: str = ""
    total_pages: int = 0
    saved_pages: int = 0
    current_page_index: int = 0
    include_images: bool = True
    copied_images: int = 0

    def page_count(self) -> int:
        """Return the number of pages in this project."""
        return len(self.pages)

    def to_dict(self) -> dict:
        """Convert project metadata to dictionary for serialization."""
        return {
            "version": self.version,
            "source_lib": self.source_lib,
            "project_id": self.project_id,
            "source_path": self.source_path,
            "total_pages": self.total_pages,
            "saved_pages": self.saved_pages,
            "current_page_index": self.current_page_index,
            "include_images": self.include_images,
            "copied_images": self.copied_images,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create Project instance from metadata dictionary."""
        # Create instance with metadata fields
        project = cls(
            version=data.get("version", "1.0"),
            source_lib=data.get("source_lib", "doctr-pgdp-labeled"),
            project_id=data.get("project_id", ""),
            source_path=data.get("source_path", ""),
            total_pages=data.get("total_pages", 0),
            saved_pages=data.get("saved_pages", 0),
            current_page_index=data.get("current_page_index", 0),
            include_images=data.get("include_images", True),
            copied_images=data.get("copied_images", 0),
        )
        return project
