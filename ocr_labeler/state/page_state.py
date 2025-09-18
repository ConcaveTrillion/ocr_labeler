from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from pd_book_tools.ocr.page import Page  # type: ignore

from .operations import PageOperations

if TYPE_CHECKING:
    from ..models.project import Project

logger = logging.getLogger(__name__)


@dataclass
class PageState:
    """Page-specific state management.

    Responsibilities:
    - Handle page loading and caching
    - Manage page-specific operations (save/load, copy ground truth to OCR)
    - Provide access to current page data
    """

    page_ops: PageOperations = field(default_factory=PageOperations)
    on_change: Optional[Callable[[], None]] = None

    # Reference to project for accessing pages (set by ProjectState)
    _project: Optional[Project] = field(default=None, init=False)
    _project_root: Optional[Path] = field(default=None, init=False)

    def notify(self):
        """Notify listeners of state changes."""
        if self.on_change:
            self.on_change()

    def set_project_context(self, project: Project, project_root: Path):
        """Set the project context for page operations."""
        self._project = project
        self._project_root = project_root

    def get_page(self, index: int) -> Optional[Page]:
        """Get page at the specified index, loading it if necessary."""
        if not self._project:
            logger.warning("PageState.get_page: no project context set")
            return None

        logger.debug("PageState.get_page: index=%s", index)

        # Use PageOperations directly for state concerns
        return self.page_ops.ensure_page(
            index=index,
            pages=self._project.pages,
            image_paths=self._project.image_paths,
            ground_truth_map=self._project.ground_truth_map,
        )

    def copy_ground_truth_to_ocr(self, page_index: int, line_index: int) -> bool:
        """Copy ground truth text to OCR text for all words in the specified line.

        Args:
            page_index: Zero-based page index
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        page = self.get_page(page_index)
        if not page:
            logger.warning("No page available at index %s for GT→OCR copy", page_index)
            return False

        # Import inside method to allow test monkeypatching
        try:
            from .operations.line_operations import LineOperations

            line_ops = LineOperations()
            result = line_ops.copy_ground_truth_to_ocr(page, line_index)

            if result:
                # Trigger UI refresh to show updated matches
                self.notify()

            return result
        except Exception as e:
            logger.exception(f"Error in GT→OCR copy for line {line_index}: {e}")
            return False

    def save_page(
        self,
        page_index: int,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Save a specific page using PageOperations.

        Args:
            page_index: Zero-based page index to save
            save_directory: Directory to save files (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        if not self._project_root:
            logger.error("PageState.save_page: no project root set")
            return False

        page = self.get_page(page_index)
        if page is None:
            logger.error("No page available at index %s to save", page_index)
            return False

        return self.page_ops.save_page(
            page=page,
            project_root=self._project_root,
            save_directory=save_directory,
            project_id=project_id,
        )

    def load_page(
        self,
        page_index: int,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Load a specific page from saved files.

        Args:
            page_index: Zero-based page index to load
            save_directory: Directory where files were saved (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if load was successful, False otherwise.
        """
        if not self._project or not self._project_root:
            logger.error("PageState.load_page: project context not set")
            return False

        loaded_page = self.page_ops.load_page(
            page_number=page_index + 1,  # Convert to 1-based
            project_root=self._project_root,
            save_directory=save_directory,
            project_id=project_id,
        )

        if loaded_page is None:
            logger.warning("No saved page found for index %s", page_index)
            return False

        # Replace the page in the project

    def find_ground_truth_text(
        self, page_name: str, ground_truth_map: dict
    ) -> Optional[str]:
        """Find ground truth text for a page from the ground truth mapping.

        Args:
            page_name: Name of the page file
            ground_truth_map: Mapping of page names to ground truth text

        Returns:
            Ground truth text if found, None otherwise
        """
        return self.page_ops.find_ground_truth_text(page_name, ground_truth_map)
