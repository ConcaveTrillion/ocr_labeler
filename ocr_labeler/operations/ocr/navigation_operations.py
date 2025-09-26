"""Navigation operations for managing page navigation within projects."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class NavigationResult:
    """Result of a navigation attempt."""

    class NavigationStatus(Enum):
        SUCCESS = "success"
        FAILURE = "failure"
        NO_OP = "no_op"

    success: bool
    message: str = ""

    def __bool__(self) -> bool:
        return self.success


class NavigationOperations:
    """Operations for handling page navigation within projects.

    Provides methods for navigating between pages, validating page indices,
    and managing navigation state.
    """

    @staticmethod
    def next_page(current_index: int, max_index: int) -> NavigationResult:
        """Navigate to the next page.

        Args:
            current_index: Current page index (0-based)
            max_index: Maximum valid page index (0-based)

        Returns:
            NavigationResult indicating success or failure
        """
        logger.debug(
            "next_page: called, current_index=%s, max_index=%s",
            current_index,
            max_index,
        )

        if current_index < max_index:
            logger.debug("next_page: moving to index=%s", current_index + 1)
            return NavigationResult(True)
        else:
            logger.warning("next_page: already at last page, no change")
            return NavigationResult(False, "Already at last page")

    @staticmethod
    def prev_page(current_index: int) -> NavigationResult:
        """Navigate to the previous page.

        Args:
            current_index: Current page index (0-based)

        Returns:
            NavigationResult indicating success or failure
        """
        logger.debug("prev_page: called, current_index=%s", current_index)

        if current_index > 0:
            logger.debug("prev_page: moving to index=%s", current_index - 1)
            return NavigationResult(True)
        else:
            logger.warning("prev_page: already at first page, no change")
            return NavigationResult(False, "Already at first page")

    @staticmethod
    def goto_page_number(
        page_number: int, max_pages: int
    ) -> tuple[NavigationResult, int]:
        """Navigate to a specific page number (1-based).

        Args:
            page_number: Page number to navigate to (1-based)
            max_pages: Total number of pages

        Returns:
            Tuple of (NavigationResult, target_index) where target_index is 0-based
        """
        logger.debug(
            "goto_page_number: called with page_number=%s, max_pages=%s",
            page_number,
            max_pages,
        )

        # Validate page number is in valid range (1-based)
        if page_number < 1 or page_number > max_pages:
            logger.warning(
                "goto_page_number: invalid page number %s (valid range: 1-%s)",
                page_number,
                max_pages,
            )
            return NavigationResult(False, f"Invalid page number {page_number}"), -1

        target_index = page_number - 1
        logger.debug("goto_page_number: navigating to index=%s", target_index)
        return NavigationResult(True), target_index

    @staticmethod
    def goto_page_index(
        target_index: int, max_index: int
    ) -> tuple[NavigationResult, int]:
        """Jump to a page by zero-based index, clamping to valid range.

        Args:
            target_index: Target page index (0-based)
            max_index: Maximum valid page index (0-based)

        Returns:
            Tuple of (NavigationResult, clamped_index)
        """
        logger.debug(
            "goto_page_index: called with target_index=%s, max_index=%s",
            target_index,
            max_index,
        )

        if max_index < 0:
            logger.warning("goto_page_index: no pages available")
            return NavigationResult(False, "No pages available"), -1

        # Clamp to valid range
        if target_index < 0:
            logger.warning("goto_page_index: clamping %s -> 0", target_index)
            clamped_index = 0
        elif target_index > max_index:
            logger.warning(
                "goto_page_index: clamping %s -> %s", target_index, max_index
            )
            clamped_index = max_index
        else:
            clamped_index = target_index

        logger.debug("goto_page_index: clamped to index=%s", clamped_index)
        return NavigationResult(True), clamped_index

    @staticmethod
    def validate_page_index(page_index: int, max_index: int) -> bool:
        """Validate that a page index is within valid range.

        Args:
            page_index: Page index to validate (0-based)
            max_index: Maximum valid page index (0-based)

        Returns:
            True if index is valid, False otherwise
        """
        return 0 <= page_index <= max_index

    @staticmethod
    async def schedule_async_navigation(
        nav_action: Callable[[], None],
        background_load: Callable[[], None],
        is_navigating_callback: Callable[[bool], None],
    ) -> None:
        """Schedule asynchronous navigation with background loading.

        Args:
            nav_action: Action to perform for navigation
            background_load: Background loading action
            is_navigating_callback: Callback to set navigation state
        """
        logger.debug("schedule_async_navigation: called")

        # Quick index change first
        nav_action()
        is_navigating_callback(True)

        try:
            # Pre-load the page at the new index
            await asyncio.to_thread(background_load)
        finally:
            is_navigating_callback(False)

        logger.debug("schedule_async_navigation: completed")
