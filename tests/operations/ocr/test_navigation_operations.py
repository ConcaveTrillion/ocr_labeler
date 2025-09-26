"""Tests for navigation operations."""

import logging
from unittest.mock import MagicMock

import pytest

from ocr_labeler.operations.ocr.navigation_operations import (
    NavigationOperations,
    NavigationResult,
)


class TestNavigationResult:
    """Test NavigationResult dataclass."""

    def test_success_result(self):
        """Test successful navigation result."""
        result = NavigationResult(True, "Success message")
        assert result.success is True
        assert result.message == "Success message"
        assert bool(result) is True

    def test_failure_result(self):
        """Test failed navigation result."""
        result = NavigationResult(False, "Error message")
        assert result.success is False
        assert result.message == "Error message"
        assert bool(result) is False

    def test_result_without_message(self):
        """Test navigation result without message."""
        result = NavigationResult(True)
        assert result.success is True
        assert result.message == ""
        assert bool(result) is True


class TestNavigationOperations:
    """Test NavigationOperations static methods."""

    def test_next_page_success(self, caplog):
        """Test successful next page navigation."""
        with caplog.at_level(logging.DEBUG):
            result = NavigationOperations.next_page(0, 5)

        assert result.success is True
        assert result.message == ""
        assert bool(result) is True
        assert "next_page: called, current_index=0, max_index=5" in caplog.text
        assert "next_page: moving to index=1" in caplog.text

    def test_next_page_at_last_page(self, caplog):
        """Test next page navigation when already at last page."""
        with caplog.at_level(logging.WARNING):
            result = NavigationOperations.next_page(5, 5)

        assert result.success is False
        assert result.message == "Already at last page"
        assert bool(result) is False
        assert "next_page: already at last page, no change" in caplog.text

    def test_prev_page_success(self, caplog):
        """Test successful previous page navigation."""
        with caplog.at_level(logging.DEBUG):
            result = NavigationOperations.prev_page(3)

        assert result.success is True
        assert result.message == ""
        assert bool(result) is True
        assert "prev_page: called, current_index=3" in caplog.text
        assert "prev_page: moving to index=2" in caplog.text

    def test_prev_page_at_first_page(self, caplog):
        """Test previous page navigation when already at first page."""
        with caplog.at_level(logging.WARNING):
            result = NavigationOperations.prev_page(0)

        assert result.success is False
        assert result.message == "Already at first page"
        assert bool(result) is False
        assert "prev_page: already at first page, no change" in caplog.text

    def test_goto_page_number_valid(self, caplog):
        """Test navigation to valid page number."""
        with caplog.at_level(logging.DEBUG):
            result, target_index = NavigationOperations.goto_page_number(3, 10)

        assert result.success is True
        assert result.message == ""
        assert target_index == 2  # 0-based index
        assert (
            "goto_page_number: called with page_number=3, max_pages=10" in caplog.text
        )
        assert "goto_page_number: navigating to index=2" in caplog.text

    def test_goto_page_number_too_low(self, caplog):
        """Test navigation to page number below minimum."""
        with caplog.at_level(logging.WARNING):
            result, target_index = NavigationOperations.goto_page_number(0, 10)

        assert result.success is False
        assert result.message == "Invalid page number 0"
        assert target_index == -1
        assert (
            "goto_page_number: invalid page number 0 (valid range: 1-10)" in caplog.text
        )

    def test_goto_page_number_too_high(self, caplog):
        """Test navigation to page number above maximum."""
        with caplog.at_level(logging.WARNING):
            result, target_index = NavigationOperations.goto_page_number(15, 10)

        assert result.success is False
        assert result.message == "Invalid page number 15"
        assert target_index == -1
        assert (
            "goto_page_number: invalid page number 15 (valid range: 1-10)"
            in caplog.text
        )

    def test_goto_page_index_valid(self, caplog):
        """Test navigation to valid page index."""
        with caplog.at_level(logging.DEBUG):
            result, clamped_index = NavigationOperations.goto_page_index(3, 10)

        assert result.success is True
        assert clamped_index == 3
        assert (
            "goto_page_index: called with target_index=3, max_index=10" in caplog.text
        )
        assert "goto_page_index: clamped to index=3" in caplog.text

    def test_goto_page_index_clamp_low(self, caplog):
        """Test clamping of page index below minimum."""
        with caplog.at_level(logging.WARNING):
            result, clamped_index = NavigationOperations.goto_page_index(-5, 10)

        assert result.success is True
        assert clamped_index == 0
        assert "goto_page_index: clamping -5 -> 0" in caplog.text

    def test_goto_page_index_clamp_high(self, caplog):
        """Test clamping of page index above maximum."""
        with caplog.at_level(logging.WARNING):
            result, clamped_index = NavigationOperations.goto_page_index(15, 10)

        assert result.success is True
        assert clamped_index == 10
        assert "goto_page_index: clamping 15 -> 10" in caplog.text

    def test_goto_page_index_no_pages(self, caplog):
        """Test navigation when no pages are available."""
        with caplog.at_level(logging.WARNING):
            result, clamped_index = NavigationOperations.goto_page_index(0, -1)

        assert result.success is False
        assert result.message == "No pages available"
        assert clamped_index == -1
        assert "goto_page_index: no pages available" in caplog.text

    @pytest.mark.parametrize(
        "page_index,max_index,expected",
        [
            (0, 5, True),  # Valid first page
            (5, 5, True),  # Valid last page
            (3, 5, True),  # Valid middle page
            (-1, 5, False),  # Below minimum
            (6, 5, False),  # Above maximum
        ],
    )
    def test_validate_page_index(self, page_index, max_index, expected):
        """Test page index validation with various inputs."""
        result = NavigationOperations.validate_page_index(page_index, max_index)
        assert result is expected

    @pytest.mark.asyncio
    async def test_schedule_async_navigation(self, caplog):
        """Test asynchronous navigation scheduling."""
        nav_action = MagicMock()
        background_load = MagicMock()
        is_navigating_callback = MagicMock()

        with caplog.at_level(logging.DEBUG):
            await NavigationOperations.schedule_async_navigation(
                nav_action, background_load, is_navigating_callback
            )

        # Verify navigation action was called immediately
        nav_action.assert_called_once()

        # Verify navigation state callbacks
        assert is_navigating_callback.call_count == 2
        is_navigating_callback.assert_any_call(True)
        is_navigating_callback.assert_any_call(False)

        # Verify background load was called
        background_load.assert_called_once()

        assert "schedule_async_navigation: called" in caplog.text
        assert "schedule_async_navigation: completed" in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_async_navigation_with_exception(self, caplog):
        """Test asynchronous navigation with background load exception."""
        nav_action = MagicMock()
        background_load = MagicMock(side_effect=Exception("Load failed"))
        is_navigating_callback = MagicMock()

        # The method does not catch exceptions from background_load
        with pytest.raises(Exception, match="Load failed"):
            await NavigationOperations.schedule_async_navigation(
                nav_action, background_load, is_navigating_callback
            )

        # Verify navigation action was called
        nav_action.assert_called_once()

        # Verify navigation state callbacks - should still call False even on exception
        assert is_navigating_callback.call_count == 2
        is_navigating_callback.assert_any_call(True)
        is_navigating_callback.assert_any_call(False)

        # Verify background load was attempted
        background_load.assert_called_once()
