from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from pd_book_tools.ocr.page import Page  # type: ignore

from ..models.project import Project
from .operations import PageOperations, ProjectOperations

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
    is_loading: bool = False
    on_change: Optional[Callable[[], None]] = None
    page_ops: PageOperations = field(default_factory=PageOperations)

    def notify(self):
        """Notify listeners of state changes."""
        if self.on_change:
            self.on_change()

    async def load_project(self, directory: Path):
        """Load images; lazily OCR each page via DocTR on first access.

        Reads pages.json (if present) mapping image filename -> ground truth text.
        """
        # Use ProjectOperations for I/O operations
        operations = ProjectOperations()

        # Validate directory and scan for images using operations
        directory = Path(directory)
        images = await operations.scan_project_directory(
            directory
        )  # This will raise FileNotFoundError if needed

        self.is_loading = True
        self.notify()
        try:
            self.project_root = directory

            # Use ProjectOperations to create the project
            self.project = await operations.create_project(directory, images)
            # Reset navigation to first page
            self.current_page_index = 0 if images else -1
        finally:
            self.is_loading = False
            self.notify()

    def reload_ground_truth(self):
        """Reload ground truth for the current project."""
        # Import inside method to allow test monkeypatching of module attribute
        try:
            from .operations.project_operations import ProjectOperations

            project_ops = ProjectOperations()
            project_ops.reload_ground_truth_into_project(self)
        except Exception:  # pragma: no cover - defensive
            return

    def next_page(self):
        """Navigate to the next page."""

        def action():
            if self.current_page_index < self.project.page_count() - 1:
                self.current_page_index += 1
                logger.debug("next_page: moved to index=%s", self.current_page_index)
            else:
                logger.debug("next_page: already at last page, no change")

        self._navigate(action)

    def prev_page(self):
        """Navigate to the previous page."""

        def action():
            if self.current_page_index > 0:
                self.current_page_index -= 1
                logger.debug("prev_page: moved to index=%s", self.current_page_index)
            else:
                logger.debug("prev_page: already at first page, no change")

        self._navigate(action)

    def goto_page_number(self, number: int):
        """Navigate to a specific page number."""
        # Validate page number is in valid range (1-based)
        if number < 1 or number > self.project.page_count():
            logger.warning(
                "goto_page_number: invalid page number %s (valid range: 1-%s)",
                number,
                self.project.page_count(),
            )
            return

        def action():
            self.goto_page_index(number - 1)

        self._navigate(action)

    def goto_page_index(self, index: int):
        """Jump to a page by zero-based index, clamping to valid range."""
        if not self.project.pages:
            self.current_page_index = -1
            logger.warning("goto_page_index: empty pages list; index set to -1")
            return
        if index < 0:
            logger.warning("goto_page_index: clamp %s -> 0", index)
            index = 0
        if index >= self.project.page_count():
            logger.warning(
                "goto_page_index: clamp %s -> %s", index, self.project.page_count() - 1
            )
            index = self.project.page_count() - 1
        self.current_page_index = index
        logger.debug("goto_page_index: now at index=%s", self.current_page_index)

    def get_page(self, index: int) -> Optional[Page]:
        """Get page at the specified index, loading it if necessary.

        This method handles page loading directly through PageOperations,
        bypassing the Project model's get_page method.
        """
        logger.debug("ProjectState.get_page: index=%s", index)

        # Use PageOperations directly for state concerns
        return self.page_ops.ensure_page(
            index=index,
            pages=self.project.pages,
            image_paths=self.project.image_paths,
            ground_truth_map=self.project.ground_truth_map,
        )

    def current_page(self) -> Page | None:
        """Get the current page."""
        return self.get_page(self.current_page_index)

    def copy_ground_truth_to_ocr(self, line_index: int) -> bool:
        """Copy ground truth text to OCR text for all words in the specified line.

        Args:
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        page = self.current_page()
        if not page:
            logger.warning("No current page available for GT→OCR copy")
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

    def _navigate(self, nav_callable: Callable[[], None]):
        """Internal navigation helper with loading state."""
        nav_callable()  # quick index change first
        self.is_loading = True
        self.notify()

        async def _background_load():
            try:
                # Pre-load the page at the new index
                await asyncio.to_thread(self.get_page, self.current_page_index)
            finally:
                self.is_loading = False
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
                    self.is_loading = False
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
                    self.is_loading = False
                    self.notify()

        _schedule_async_load()

    def save_current_page(
        self,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Save the current page using PageOperations.

        This is a convenience method that delegates to PageOperations.save_page
        using the current page from the project state.

        Args:
            save_directory: Directory to save files (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        page = self.current_page()
        if page is None:
            logger.error("No current page available to save")
            return False

        operations = PageOperations()
        return operations.save_page(
            page=page,
            project_root=self.project_root,
            save_directory=save_directory,
            project_id=project_id,
        )
