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
    """Page-specific state management. Oversees page loading, caching, and operations.

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
    page_sources: dict[int, str] = field(
        default_factory=dict
    )  # Track source of each page: 'ocr' or 'filesystem'
    current_page: Optional[Page] = field(default=None, init=False)

    # Cached text values for current page
    _cached_page_index: int = field(default=-1, init=False)
    _cached_ocr_text: str = field(default="", init=False)
    _cached_gt_text: str = field(default="", init=False)

    def notify(self):
        """Notify listeners of state changes."""
        if self.on_change:
            self.on_change()

    def set_project_context(self, project: Project, project_root: Path):
        """Set the project context for page operations."""
        self._project = project
        self._project_root = project_root

    def get_page(self, index: int, force_ocr: bool = False) -> Optional[Page]:
        """Get page at the specified index, loading it if necessary."""
        if not self._project:
            logger.warning("PageState.get_page: no project context set")
            return None

        logger.debug("PageState.get_page: index=%s, force_ocr=%s", index, force_ocr)

        # Use PageOperations directly for state concerns
        page = self.page_ops.ensure_page(
            index=index,
            pages=self._project.pages,
            image_paths=self._project.image_paths,
            ground_truth_map=self._project.ground_truth_map,
            project_root=self._project_root,
            force_ocr=force_ocr,
        )

        # Update page_sources dictionary based on the page's source
        if page is not None and hasattr(page, "page_source"):
            self.page_sources[index] = page.page_source

        return page

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
                self._invalidate_text_cache()
                self.notify()

            return result
        except Exception as e:
            logger.exception(f"Error in GT→OCR copy for line {line_index}: {e}")
            return False

    def persist_page_to_file(
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

    def load_page_from_file(
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

        # Inject ground truth text if available
        if hasattr(loaded_page, "name") and self._project.ground_truth_map:
            page_name = getattr(loaded_page, "name", None)
            if isinstance(page_name, str) and page_name:
                gt_text = self.find_ground_truth_text(
                    page_name, self._project.ground_truth_map
                )
                if gt_text:
                    try:
                        loaded_page.add_ground_truth(gt_text)
                        logger.debug(
                            f"Injected ground truth for loaded page {page_index}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to add ground truth to loaded page {page_index}: {e}"
                        )

        # Replace the page in the project
        if 0 <= page_index < len(self._project.pages):
            self._project.pages[page_index] = loaded_page
            self.page_sources[page_index] = (
                "filesystem"  # Mark as loaded from filesystem
            )
            logger.info(f"Successfully loaded page at index {page_index}")
            # Invalidate cache since page content changed
            self._invalidate_text_cache()
            return True
        else:
            logger.error(f"Page index {page_index} out of range for project pages")
            return False

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

    def get_page_source_text(self, page_index: int, is_loading: bool) -> str:
        """Get the source text for a specific page.

        Args:
            page_index: Zero-based page index
            is_loading: Whether OCR is currently loading

        Returns:
            Source text string
        """
        if is_loading:
            return "LOADING..."
        elif not self._project:
            return "(NO PROJECT)"
        else:
            page_source = self.page_sources.get(
                page_index,
                "ocr",  # Default to OCR if unknown
            )
            if page_source == "filesystem":
                return "LABELED"
            else:
                return "RAW OCR"

    def reload_page_with_ocr(self, page_index: int) -> None:
        """Reload a specific page with OCR processing, bypassing any saved version.

        Args:
            page_index: Zero-based page index to reload
        """
        if not self._project:
            logger.warning("PageState.reload_page_with_ocr: no project context set")
            return

        if 0 <= page_index < len(self._project.pages):
            # Clear the cached page to force reload
            self._project.pages[page_index] = None
            # Reload with force_ocr=True
            page = self.get_page(page_index, force_ocr=True)
            # Ensure the page source is set to "ocr" since we forced OCR processing
            if page is not None:
                self.page_sources[page_index] = "ocr"
                # Invalidate cache since page content changed
                self._invalidate_text_cache()
            self.notify()
        else:
            logger.warning(
                "PageState.reload_page_with_ocr: page_index %s out of range", page_index
            )

    def reload_current_page_with_ocr(self, current_page_index: int) -> None:
        """Reload the current page with OCR processing, bypassing any saved version.

        Args:
            current_page_index: Zero-based index of the current page
        """
        self.reload_page_with_ocr(current_page_index)

    def save_current_page(
        self,
        current_page_index: int,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Save the current page.

        Args:
            current_page_index: Zero-based index of the current page
            save_directory: Directory to save files (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        return self.persist_page_to_file(
            page_index=current_page_index,
            save_directory=save_directory,
            project_id=project_id,
        )

    def load_current_page(
        self,
        current_page_index: int,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Load the current page from saved files.

        Args:
            current_page_index: Zero-based index of the current page
            save_directory: Directory where files were saved (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if load was successful, False otherwise.
        """
        return self.load_page_from_file(
            page_index=current_page_index,
            save_directory=save_directory,
            project_id=project_id,
        )

    def copy_ground_truth_to_ocr_for_current_page(
        self, current_page_index: int, line_index: int
    ) -> bool:
        """Copy ground truth text to OCR text for all words in the specified line on the current page.

        Args:
            current_page_index: Zero-based index of the current page
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        return self.copy_ground_truth_to_ocr(current_page_index, line_index)

    def get_page_texts(self, page_index: int) -> tuple[str, str]:
        """Get OCR and ground truth text for a page.

        Args:
            page_index: Zero-based page index

        Returns:
            Tuple of (ocr_text, ground_truth_text) where each is a string
        """
        if not self._project:
            return "", ""

        page = self.get_page(page_index)
        if not page:
            return "", ""

        # Get OCR text from page
        ocr_text = getattr(page, "text", "") or ""
        if isinstance(ocr_text, str):
            ocr_text = ocr_text if ocr_text.strip() else ""
        else:
            ocr_text = ""

        # Get ground truth text from state mapping
        gt_text = ""
        if hasattr(page, "name") and self._project:
            gt_text = (
                self.find_ground_truth_text(page.name, self._project.ground_truth_map)
                or ""
            )

        if isinstance(gt_text, str):
            gt_text = gt_text if gt_text.strip() else ""
        else:
            gt_text = ""

        return ocr_text, gt_text

    @property
    def current_ocr_text(self) -> str:
        """Get the OCR text for the current page (cached for performance)."""
        self._update_text_cache()
        return self._cached_ocr_text

    @property
    def current_gt_text(self) -> str:
        """Get the ground truth text for the current page (cached for performance)."""
        self._update_text_cache()
        return self._cached_gt_text

    def _invalidate_text_cache(self):
        """Invalidate the cached text values when page content changes."""
        self._cached_page_index = -1
        self._cached_ocr_text = ""
        self._cached_gt_text = ""

    def _update_text_cache(self, force: bool = False):
        """Update cached text values for the current page."""
        if force or self._cached_page_index != self._current_page_index:
            # Only update cache if page is already loaded to avoid triggering OCR
            if (
                0 <= self._current_page_index < len(self._project.pages)
                and self._project.pages[self._current_page_index] is not None
            ):
                self._cached_ocr_text, self._cached_gt_text = self.get_page_texts(
                    self._current_page_index
                )
                self._cached_page_index = self._current_page_index
            else:
                # Page not loaded yet, keep old cache or set to loading
                if self._cached_page_index == -1 or force:
                    self._cached_ocr_text = "Loading..."
                    self._cached_gt_text = "Loading..."
                    self._cached_page_index = self._current_page_index

    @property
    def _current_page_index(self) -> int:
        """Get the current page index (this would need to be set by the caller)."""
        # For now, return 0 as a default - this should be set by the component using page_state
        return getattr(self, "_page_index", 0)

    @_current_page_index.setter
    def _current_page_index(self, value: int):
        """Set the current page index."""
        if getattr(self, "_page_index", None) != value:
            self._invalidate_text_cache()
        self._page_index = value
