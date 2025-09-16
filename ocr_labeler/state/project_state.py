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
    current_page_native: object | None = (
        None  # native pd_book_tools Page object after OCR
    )
    project_root: Path = Path("../data/source-pgdp-data/output")
    is_loading: bool = False
    on_change: Optional[Callable[[], None]] = None

    def notify(self):
        """Notify listeners of state changes."""
        if self.on_change:
            self.on_change()

    def load_project(self, directory: Path):
        """Load images; lazily OCR each page via DocTR on first access.

        Reads pages.json (if present) mapping image filename -> ground truth text.
        """
        # Use ProjectOperations for I/O operations
        operations = ProjectOperations()

        # Validate directory and scan for images using operations
        directory = Path(directory)
        images = operations.scan_project_directory(
            directory
        )  # This will raise FileNotFoundError if needed

        self.is_loading = True
        self.notify()
        try:
            self.project_root = directory

            # Use ProjectOperations to create the project
            self.project = operations.create_project(directory, images)
            self.current_page_native = self.project.current_page() if images else None
        finally:
            self.is_loading = False
            self.notify()

    def reload_ground_truth(self):
        """Reload ground truth for the current project."""
        # Import inside method to allow test monkeypatching of module attribute
        try:
            from .ground_truth import reload_ground_truth_into_project as _reload
        except Exception:  # pragma: no cover - defensive
            return
        _reload(self)

    def next_page(self):
        """Navigate to the next page."""
        self._navigate(self.project.next_page)

    def prev_page(self):
        """Navigate to the previous page."""
        self._navigate(self.project.prev_page)

    def goto_page_number(self, number: int):
        """Navigate to a specific page number."""

        def action():
            self.project.goto_page_number(number)

        self._navigate(action)

    def current_page(self) -> Page | None:
        """Get the current page."""
        return self.project.current_page()

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

        try:
            lines = getattr(page, "lines", [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    f"Line index {line_index} out of range (0-{len(lines) - 1})"
                )
                return False

            line = lines[line_index]
            words = getattr(line, "words", [])
            if not words:
                logger.info(f"No words found in line {line_index}")
                return False

            modified_count = 0
            for word_idx, word in enumerate(words):
                gt_text = getattr(word, "ground_truth_text", "")
                if gt_text:
                    # Copy ground truth to OCR text
                    word.text = gt_text
                    modified_count += 1
                    logger.debug(
                        f"Copied GT→OCR for word {word_idx} in line {line_index}: '{gt_text}'"
                    )

            if modified_count > 0:
                logger.info(
                    f"Copied GT→OCR for {modified_count} words in line {line_index}"
                )
                # Trigger UI refresh to show updated matches
                self.notify()
                return True
            else:
                logger.info(f"No ground truth text found to copy in line {line_index}")
                return False

        except Exception as e:
            logger.exception(f"Error copying GT→OCR for line {line_index}: {e}")
            return False

    def _navigate(self, nav_callable: Callable[[], None]):
        """Internal navigation helper with loading state."""
        nav_callable()  # quick index change first
        self.is_loading = True
        self.current_page_native = None
        self.notify()

        async def _background_load():
            try:
                page = await asyncio.to_thread(self.project.current_page)
                self.current_page_native = page
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
                    page = self.project.current_page()
                    self.current_page_native = page
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
                    page = self.project.current_page()
                    self.current_page_native = page
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
