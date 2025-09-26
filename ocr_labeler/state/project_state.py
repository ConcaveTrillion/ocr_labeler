from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from pd_book_tools.ocr.page import Page

from ..models.project import Project
from ..operations.ocr.navigation_operations import NavigationOperations
from ..operations.ocr.page_operations import PageOperations
from ..operations.ocr.text_operations import TextOperations
from ..operations.persistence.project_operations import ProjectOperations
from .page_state import PageState

logger = logging.getLogger(__name__)


@dataclass
class ProjectState:
    """Project-specific state management.

    Responsibilities:
    - Manage the current project and its pages
    - Handle navigation within the project
    - Coordinate individual OCR page loading
    - Provide ground truth reload capability for the current project
    """

    project: Project = field(default_factory=Project)
    current_page_index: int = 0  # Navigation state managed here
    project_root: Path = Path("../data/source-pgdp-data/output")
    is_project_loading: bool = False
    is_navigating: bool = False
    on_change: Optional[List[Callable[[], None]]] = field(default_factory=list)
    page_states: dict[int, PageState] = field(
        default_factory=dict
    )  # Per-page state management
    page_ops: PageOperations = field(
        default_factory=PageOperations
    )  # For backward compatibility

    # Cached text values to avoid expensive recomputation during binding propagation
    _cached_ocr_text: str = field(default="", init=False)
    _cached_gt_text: str = field(default="", init=False)
    _cached_page_index: int = field(
        default=-1, init=False
    )  # Track which page the cache is for

    def notify(self):
        """Notify listeners of state changes."""
        for listener in self.on_change:
            listener()

    def get_page_state(self, page_index: int) -> PageState:
        """Get or create PageState for the specified page index.
        Each page gets its own state management instance.
        """
        logger.debug("get_page_state: called with page_index=%s", page_index)
        if page_index not in self.page_states:
            page_state = PageState()
            page_state.set_project_context(self.project, self.project_root)
            page_state.on_change.append(self.notify)
            self.page_states[page_index] = page_state
        logger.debug("get_page_state: returning page_state for index %s", page_index)
        return self.page_states[page_index]

    @property
    def current_page_state(self) -> PageState:
        """Get or create the PageState for the current page index."""
        logger.debug("current_page_state: called")
        result = self.get_page_state(self.current_page_index)
        logger.debug("current_page_state: returning page_state")
        return result

    async def load_project(self, directory: Path):
        """Load images; lazily OCR each page via DocTR on first access.

        Reads pages.json (if present) mapping image filename -> ground truth text.
        """
        logger.debug("load_project: called with directory=%s", directory)
        # Use ProjectOperations for I/O operations
        operations = ProjectOperations()

        # Validate directory and scan for images using operations
        directory = Path(directory)
        images = await operations.scan_project_directory(
            directory
        )  # This will raise FileNotFoundError if needed

        self.is_project_loading = True
        self.notify()
        try:
            self.project_root = directory

            logger.debug("load_project: creating project with %d images", len(images))
            # Use ProjectOperations to create the project
            self.project = await operations.create_project(directory, images)
            # Reset navigation to first page
            self.current_page_index = 0 if images else -1

            # Clear page states for the new project
            self.page_states.clear()
        finally:
            self.is_project_loading = False
            self.notify()
        logger.debug("load_project: completed, loaded %d images", len(images))

    def reload_ground_truth(self):
        """Reload ground truth for the current project."""
        logger.debug("reload_ground_truth: called")
        # Import inside method to allow test monkeypatching of module attribute
        try:
            from ..operations.persistence.project_operations import ProjectOperations

            project_ops = ProjectOperations()
            project_ops.reload_ground_truth_into_project(self)
        except Exception:  # pragma: no cover - defensive
            return
        logger.debug("reload_ground_truth: completed")

    def next_page(self):
        """Navigate to the next page."""
        logger.debug("next_page: called, current_index=%s", self.current_page_index)

        result = NavigationOperations.next_page(
            self.current_page_index, self.project.page_count() - 1
        )
        if result:
            self.current_page_index += 1
            logger.debug("next_page: moved to index=%s", self.current_page_index)
        else:
            logger.warning("next_page: already at last page, no change")

        self._navigate()
        logger.debug("next_page: completed")

    def prev_page(self):
        """Navigate to the previous page."""
        logger.debug("prev_page: called, current_index=%s", self.current_page_index)

        result = NavigationOperations.prev_page(self.current_page_index)
        if result:
            self.current_page_index -= 1
            logger.debug("prev_page: moved to index=%s", self.current_page_index)
        else:
            logger.warning("prev_page: already at first page, no change")

        self._navigate()
        logger.debug("prev_page: completed")

    def goto_page_number(self, number: int):
        """Navigate to a specific page number."""
        logger.debug("goto_page_number: called with number=%s", number)

        result, target_index = NavigationOperations.goto_page_number(
            number, self.project.page_count()
        )
        if result:
            self.goto_page_index(target_index)
        else:
            logger.warning("goto_page_number: invalid page number %s", number)

        logger.debug("goto_page_number: completed")

    def goto_page_index(self, index: int):
        """Jump to a page by zero-based index, clamping to valid range."""
        logger.debug("goto_page_index: called with index=%s", index)
        if not self.project.pages:
            self.current_page_index = -1
            logger.warning("goto_page_index: empty pages list; index set to -1")
            raise ValueError("No pages available to navigate")

        result, clamped_index = NavigationOperations.goto_page_index(
            index, self.project.page_count() - 1
        )
        if result:
            # Invalidate cache if page index actually changed
            if self.current_page_index != clamped_index:
                self._invalidate_text_cache()
            self.current_page_index = clamped_index
            logger.debug("goto_page_index: now at index=%s", self.current_page_index)
        else:
            logger.warning("goto_page_index: navigation failed for index %s", index)

    def get_page(self, index: int, force_ocr: bool = False) -> Optional[Page]:
        """Get page at the specified index, loading it if necessary.

        This method delegates to the PageState for the specific page.
        """
        logger.debug("get_page: called with index=%s, force_ocr=%s", index, force_ocr)
        page_state = self.get_page_state(index)
        result = page_state.get_page(index, force_ocr=force_ocr)
        logger.debug("get_page: returning page for index %s", index)
        return result

    def current_page(self) -> Page | None:
        """Get the current page."""
        logger.debug("current_page: called, current_index=%s", self.current_page_index)
        result = self.get_page(self.current_page_index)
        logger.debug("current_page: returning page")
        return result

    def reload_current_page_with_ocr(self):
        """Reload the current page with OCR processing, bypassing any saved version."""
        logger.debug(
            "reload_current_page_with_ocr: called, current_index=%s",
            self.current_page_index,
        )
        page_state = self.get_page_state(self.current_page_index)
        page_state.reload_page_with_ocr(self.current_page_index)
        # Invalidate cache since page content may have changed
        self._invalidate_text_cache()
        logger.debug("reload_current_page_with_ocr: completed")

    def _navigate(self):
        """Internal navigation helper with loading state."""
        logger.debug("_navigate: called")
        self.is_navigating = True
        self.notify()

        async def _background_load():
            try:
                # Pre-load the page at the new index
                await asyncio.to_thread(self.get_page, self.current_page_index)
                # Update text cache now that page is loaded
                self._update_text_cache(force=True)
            finally:
                self.is_navigating = False
                self.notify()

        def _schedule_async_load():
            """Schedule background load if an event loop is running.

            Option A with extra handling for test mocks: if create_task returns a non-Task
            (e.g., a test stub that just records the call and returns None), close the
            coroutine to avoid an un-awaited coroutine warning while still leaving the
            loading flag True (as real async completion would later clear it).
            """
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # no running loop at all
                logger.info(
                    "No running event loop; falling back to synchronous page load"
                )
                # Fallback synchronous load
                try:
                    self.get_page(self.current_page_index)
                finally:
                    self.is_project_loading = False
                    self.is_navigating = False
                    self.notify()
                return

            logger.info("_schedule_async_load: got running loop %s", loop)
            coro = _background_load()
            try:
                task = loop.create_task(coro)
                # If a test replaced create_task with a stub that returns None or non-Task, close coro
                if not isinstance(
                    task, asyncio.Task
                ):  # pragma: no cover - exercised in tests via mock
                    try:
                        coro.close()
                    except Exception:  # pragma: no cover - defensive
                        pass
                return
            except Exception:  # scheduling failed (closed loop, etc.)
                try:
                    coro.close()  # prevent 'never awaited' warning
                except Exception:  # pragma: no cover - defensive
                    pass
                # Fallback synchronous load
                try:
                    self.get_page(self.current_page_index)
                finally:
                    self.is_project_loading = False
                    self.is_navigating = False
                    self.notify()

        _schedule_async_load()
        logger.debug("_navigate: completed")

    def save_current_page(
        self,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Save the current page using its PageState.

        This is a convenience method that delegates to the PageState for the current page.

        Args:
            save_directory: Directory to save files (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        logger.debug(
            "save_current_page: called with save_directory=%s, project_id=%s",
            save_directory,
            project_id,
        )
        page_state = self.get_page_state(self.current_page_index)

        # Try PageState first if page is available
        if page_state.get_page(self.current_page_index) is not None:
            result = page_state.persist_page_to_file(
                page_index=self.current_page_index,
                save_directory=save_directory,
                project_id=project_id,
            )
        else:
            # Fall back to direct implementation for backward compatibility (tests)
            page = self.current_page()
            if page is None:
                logger.error("No current page available to save")
                result = False
            else:
                operations = PageOperations()
                result = operations.save_page(
                    page=page,
                    project_root=self.project_root,
                    save_directory=save_directory,
                    project_id=project_id,
                )
        logger.debug("save_current_page: completed, result=%s", result)
        return result

    def load_current_page(
        self,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Load the current page from saved files.

        This is a convenience method that delegates to the PageState for the current page.

        Args:
            save_directory: Directory where files were saved (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if load was successful, False otherwise.
        """
        logger.debug(
            "load_current_page: called with save_directory=%s, project_id=%s",
            save_directory,
            project_id,
        )
        page_state = self.get_page_state(self.current_page_index)
        success = page_state.load_page_from_file(
            page_index=self.current_page_index,
            save_directory=save_directory,
            project_id=project_id,
        )
        if success:
            # Invalidate cache since page content changed
            self._invalidate_text_cache()
        logger.debug("load_current_page: completed, success=%s", success)
        return success

    @property
    def current_page_source_text(self) -> str:
        """Get the source text for the current page."""
        logger.debug("current_page_source_text: called")
        page = self.current_page()
        result = TextOperations.get_page_source_text(page, self.is_project_loading)
        logger.debug("current_page_source_text: returning text")
        return result

    @property
    def current_ocr_text(self) -> str:
        """Get the OCR text for the current page (cached for performance)."""
        logger.debug("current_ocr_text: called")
        self._update_text_cache()
        logger.debug("current_ocr_text: returning cached text")
        return self._cached_ocr_text

    @property
    def current_gt_text(self) -> str:
        """Get the ground truth text for the current page (cached for performance)."""
        logger.debug("current_gt_text: called")
        self._update_text_cache()
        logger.debug("current_gt_text: returning cached text")
        return self._cached_gt_text

    def _invalidate_text_cache(self):
        """Invalidate the cached text values when page content changes."""
        logger.debug("_invalidate_text_cache: called")
        self._cached_page_index = -1
        self._cached_ocr_text = ""
        self._cached_gt_text = ""
        logger.debug("_invalidate_text_cache: completed")

    def _update_text_cache(self, force: bool = False):
        """Update cached text values for the current page."""
        logger.debug("_update_text_cache: called with force=%s", force)
        if TextOperations.should_update_text_cache(
            self.current_page_index, self._cached_page_index, force
        ):
            # Only update cache if page is already loaded to avoid triggering OCR
            if TextOperations.is_page_loaded_for_cache(
                self.project.pages, self.current_page_index
            ):
                page = self.project.pages[self.current_page_index]
                self._cached_ocr_text, self._cached_gt_text = (
                    TextOperations.get_page_texts(page, self.project.ground_truth_map)
                )
                self._cached_page_index = self.current_page_index
            else:
                # Page not loaded yet, keep old cache or set to loading
                if self._cached_page_index == -1 or force:
                    self._cached_ocr_text, self._cached_gt_text = (
                        TextOperations.get_loading_text()
                    )
                    self._cached_page_index = self.current_page_index
        logger.debug("_update_text_cache: completed")
