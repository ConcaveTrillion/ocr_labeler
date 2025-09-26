"""Tests for OCR service."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from ocr_labeler.operations.ocr.ocr_service import OCRService
from ocr_labeler.operations.ocr.page_operations import PageOperations


class TestOCRService:
    """Test OCRService class methods."""

    @pytest.fixture
    def mock_page_operations(self):
        """Create a mock page operations instance."""
        return MagicMock(spec=PageOperations)

    @pytest.fixture
    def service(self, mock_page_operations):
        """Create OCRService instance with mocked dependencies."""
        return OCRService(page_operations=mock_page_operations)

    @pytest.fixture
    def temp_image(self):
        """Create a temporary image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_init_with_page_operations(self, mock_page_operations):
        """Test initializing service with provided page operations."""
        service = OCRService(page_operations=mock_page_operations)
        assert service.page_operations == mock_page_operations

    def test_init_without_page_operations(self):
        """Test initializing service without page operations (creates default)."""
        service = OCRService()
        assert isinstance(service.page_operations, PageOperations)

    @pytest.mark.asyncio
    async def test_process_page_success(
        self, service, mock_page_operations, temp_image
    ):
        """Test successful page processing."""
        # Setup mock
        mock_page = MagicMock()
        mock_page_operations.ensure_page = AsyncMock(return_value=mock_page)

        result = await service.process_page(temp_image)

        assert result == mock_page
        mock_page_operations.ensure_page.assert_called_once_with(temp_image, None)

    @pytest.mark.asyncio
    async def test_process_page_failure(
        self, service, mock_page_operations, temp_image
    ):
        """Test page processing failure."""
        # Setup mock to return None
        mock_page_operations.ensure_page = AsyncMock(return_value=None)

        result = await service.process_page(temp_image)

        assert result is None
        mock_page_operations.ensure_page.assert_called_once_with(temp_image, None)

    @pytest.mark.asyncio
    async def test_process_page_with_project(
        self, service, mock_page_operations, temp_image
    ):
        """Test page processing with project context."""
        mock_project = MagicMock()
        mock_page = MagicMock()
        mock_page_operations.ensure_page = AsyncMock(return_value=mock_page)

        result = await service.process_page(temp_image, mock_project)

        assert result == mock_page
        mock_page_operations.ensure_page.assert_called_once_with(
            temp_image, mock_project
        )

    @pytest.mark.asyncio
    async def test_process_pages_batch(self, service, mock_page_operations):
        """Test batch processing of multiple pages."""
        image_paths = [Path("/tmp/image1.png"), Path("/tmp/image2.png")]
        mock_pages = [MagicMock(), None]  # One success, one failure

        mock_page_operations.ensure_page = AsyncMock(side_effect=mock_pages)

        results = await service.process_pages_batch(image_paths)

        assert len(results) == 2
        assert results[0] == mock_pages[0]
        assert results[1] == mock_pages[1]

        # Verify ensure_page was called for each image
        assert mock_page_operations.ensure_page.call_count == 2

    @pytest.mark.asyncio
    async def test_process_pages_batch_empty_list(self, service, mock_page_operations):
        """Test batch processing with empty image list."""
        results = await service.process_pages_batch([])

        assert results == []
        mock_page_operations.ensure_page.assert_not_called()

    def test_get_supported_formats(self, service):
        """Test getting supported image formats."""
        formats = service.get_supported_formats()

        expected_formats = ["png", "jpg", "jpeg", "tiff", "bmp"]
        assert formats == expected_formats

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("image.png", True),
            ("image.PNG", True),
            ("image.jpg", True),
            ("image.jpeg", True),
            ("image.tiff", True),
            ("image.bmp", True),
            ("image.gif", False),
            ("image.webp", False),
            ("image.txt", False),
        ],
    )
    def test_is_format_supported(self, service, filename, expected):
        """Test checking if image format is supported."""
        image_path = Path(filename)
        result = service.is_format_supported(image_path)
        assert result is expected

    def test_validate_image_valid_png(self, service, temp_image):
        """Test validating a valid PNG image."""
        is_valid, error = service.validate_image(temp_image)

        assert is_valid is True
        assert error is None

    def test_validate_image_nonexistent(self, service):
        """Test validating a non-existent image."""
        nonexistent_path = Path("/tmp/nonexistent.png")
        is_valid, error = service.validate_image(nonexistent_path)

        assert is_valid is False
        assert "does not exist" in error

    def test_validate_image_directory(self, service, tmp_path):
        """Test validating a directory instead of a file."""
        is_valid, error = service.validate_image(tmp_path)

        assert is_valid is False
        assert "not a file" in error

    def test_validate_image_unsupported_format(self, service):
        """Test validating an unsupported image format."""
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            unsupported_path = Path(f.name)

        try:
            is_valid, error = service.validate_image(unsupported_path)

            assert is_valid is False
            assert "Unsupported format" in error
            assert "png, jpg, jpeg, tiff, bmp" in error
        finally:
            unsupported_path.unlink(missing_ok=True)
