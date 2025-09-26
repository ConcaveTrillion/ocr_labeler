"""Tests for OCR service."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ocr_labeler.operations.ocr.ocr_service import OCREngine, OCRService


class TestOCRService:
    """Test OCRService class methods."""

    @pytest.fixture
    def service(self):
        """Create OCRService instance."""
        return OCRService()

    @pytest.fixture
    def temp_image(self):
        """Create a temporary image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_init_default(self):
        """Test initializing service with default parameters."""
        service = OCRService()
        assert service.docTR_predictor is None
        assert service._predictor is None
        assert service.ocr_engine == OCREngine.DOCTR

    def test_init_with_predictor(self):
        """Test initializing service with custom predictor."""
        mock_predictor = MagicMock()
        service = OCRService(docTR_predictor=mock_predictor)
        assert service.docTR_predictor == mock_predictor
        assert service.ocr_engine == OCREngine.DOCTR

    def test_init_with_engine(self):
        """Test initializing service with different OCR engine."""
        service = OCRService(ocr_engine=OCREngine.TESSERACT)
        assert service.ocr_engine == OCREngine.TESSERACT

    @pytest.mark.asyncio
    async def test_process_page_success(self, service, temp_image):
        """Test successful page processing."""
        # Mock the OCR processing
        with patch.object(service, "_get_predictor") as mock_get_predictor:
            mock_predictor = MagicMock()
            mock_get_predictor.return_value = mock_predictor

            # Mock the Document.from_image_ocr_via_doctr
            with patch("pd_book_tools.ocr.document.Document") as mock_document:
                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_doc.pages = [mock_page]
                mock_document.from_image_ocr_via_doctr.return_value = mock_doc

                # Mock cv2.imread
                with patch("cv2.imread", return_value=MagicMock()):
                    result = await service.process_page(temp_image)

                    assert result == mock_page
                    mock_document.from_image_ocr_via_doctr.assert_called_once_with(
                        temp_image,
                        source_identifier=temp_image.name,
                        predictor=mock_predictor,
                    )

    @pytest.mark.asyncio
    async def test_process_page_failure(self, service, temp_image):
        """Test page processing failure."""
        # Mock the OCR processing to raise an exception
        with patch.object(service, "_get_predictor") as mock_get_predictor:
            mock_predictor = MagicMock()
            mock_get_predictor.return_value = mock_predictor

            # Mock the Document.from_image_ocr_via_doctr to raise exception
            with patch("pd_book_tools.ocr.document.Document") as mock_document:
                mock_document.from_image_ocr_via_doctr.side_effect = Exception(
                    "OCR failed"
                )

                result = await service.process_page(temp_image)

                assert result is None

    @pytest.mark.asyncio
    async def test_process_page_with_tesseract_engine(self, temp_image):
        """Test page processing with Tesseract engine."""
        service = OCRService(ocr_engine=OCREngine.TESSERACT)

        # Mock the Tesseract processing
        with patch("pd_book_tools.ocr.document.Document") as mock_document:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_doc.pages = [mock_page]
            mock_document.from_image_ocr_via_tesseract.return_value = mock_doc

            # Mock cv2.imread
            with patch("cv2.imread", return_value=MagicMock()):
                result = await service.process_page(temp_image)

                assert result == mock_page
                mock_document.from_image_ocr_via_tesseract.assert_called_once_with(
                    temp_image,
                    source_identifier=temp_image.name,
                )
                assert result.page_source == "tesseract"  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_process_page_unsupported_engine(self, temp_image):
        """Test page processing with unsupported OCR engine."""
        # Create a mock engine that's not supported
        from unittest.mock import MagicMock

        mock_engine = MagicMock()
        mock_engine.value = "unsupported"

        service = OCRService(ocr_engine=mock_engine)

        result = await service.process_page(temp_image)

        assert result is None

    @pytest.mark.asyncio
    async def test_process_pages_batch(self, service):
        """Test batch processing of multiple pages."""
        image_paths = [Path("/tmp/image1.png"), Path("/tmp/image2.png")]

        # Mock process_page to return different results
        with patch.object(
            service, "process_page", new_callable=AsyncMock
        ) as mock_process_page:
            mock_process_page.side_effect = [
                MagicMock(),
                None,
            ]  # One success, one failure

            results = await service.process_pages_batch(image_paths)

            assert len(results) == 2
            assert results[0] is not None
            assert results[1] is None

            # Verify process_page was called for each image
            assert mock_process_page.call_count == 2

    @pytest.mark.asyncio
    async def test_process_pages_batch_empty_list(self, service):
        """Test batch processing with empty image list."""
        results = await service.process_pages_batch([])

        assert results == []

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
