"""OCR service for text recognition operations."""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional

from pd_book_tools.ocr.page import Page  # type: ignore

logger = logging.getLogger(__name__)


class OCREngine(Enum):
    """Supported OCR engines."""

    DOCTR = "doctr"
    TESSERACT = "tesseract"


class OCRService:
    """Service for OCR operations.

    This service provides a high-level interface for OCR operations,
    abstracting away the details of page processing and text recognition.
    """

    def __init__(self, docTR_predictor=None, ocr_engine: OCREngine = OCREngine.DOCTR):
        """Initialize the OCR service.

        Args:
            docTR_predictor: Optional predictor for DocTR processing
            ocr_engine: OCR engine to use (defaults to DocTR)
        """
        self.docTR_predictor = docTR_predictor
        self.ocr_engine = ocr_engine
        self._predictor = None
        logger.debug("OCRService initialized with engine: %s", ocr_engine.value)

    def _get_predictor(self):
        """Get or create the DocTR predictor."""
        if self._predictor is None:
            if self.docTR_predictor is not None:
                self._predictor = self.docTR_predictor
            else:
                from pd_book_tools.ocr.doctr_support import get_default_doctr_predictor

                self._predictor = get_default_doctr_predictor()
        return self._predictor

    async def _process_page_with_doctr(
        self, image_path: Path, source_identifier: str
    ) -> Page:
        """Process a page using DocTR OCR engine.

        Args:
            image_path: Path to the image file
            source_identifier: Identifier for the page source

        Returns:
            Processed page object
        """
        from pd_book_tools.ocr.document import Document

        predictor = self._get_predictor()
        doc = Document.from_image_ocr_via_doctr(
            image_path,
            source_identifier=source_identifier,
            predictor=predictor,
        )
        return doc.pages[0]

    async def _process_page_with_tesseract(
        self, image_path: Path, source_identifier: str
    ) -> Page:
        """Process a page using Tesseract OCR engine.

        Args:
            image_path: Path to the image file
            source_identifier: Identifier for the page source

        Returns:
            Processed page object
        """
        from pd_book_tools.ocr.document import Document

        # Use Tesseract via pd_book_tools
        doc = Document.from_image_ocr_via_tesseract(
            image_path,
            source_identifier=source_identifier,
        )
        return doc.pages[0]

    async def process_page(self, image_path: Path) -> Optional[Page]:
        """Process a page with OCR.

        Args:
            image_path: Path to the image file to process.

        Returns:
            The processed page object, or None if processing failed.
        """
        try:
            logger.debug(f"Processing page: {image_path}")

            # Process the image with the selected OCR engine
            if self.ocr_engine == OCREngine.DOCTR:
                page_obj = await self._process_page_with_doctr(
                    image_path, image_path.name
                )
            elif self.ocr_engine == OCREngine.TESSERACT:
                page_obj = await self._process_page_with_tesseract(
                    image_path, image_path.name
                )
            else:
                raise ValueError(f"Unsupported OCR engine: {self.ocr_engine}")

            # Attach convenience attributes
            page_obj.image_path = image_path  # type: ignore[attr-defined]
            page_obj.name = image_path.name  # type: ignore[attr-defined]
            page_obj.index = 0  # type: ignore[attr-defined]
            page_obj.page_source = self.ocr_engine.value  # type: ignore[attr-defined]

            # Load and attach the image
            try:
                from cv2 import imread as cv2_imread

                img = cv2_imread(str(image_path))
                if img is not None:
                    page_obj.cv2_numpy_page_image = img  # type: ignore[attr-defined]
                    logger.debug("Attached cv2 image for OCR page: %s", image_path.name)
            except Exception:
                logger.debug("cv2 load failed for OCR page: %s", image_path.name)

            logger.info(f"Successfully processed page: {image_path}")
            return page_obj

        except Exception as e:
            logger.exception(f"Error processing page {image_path}: {e}")
            return None

    async def process_pages_batch(
        self, image_paths: list[Path]
    ) -> list[Optional[Page]]:
        """Process multiple pages with OCR.

        Args:
            image_paths: List of paths to image files to process.

        Returns:
            List of processed page objects, with None for failed pages.
        """
        results = []
        for image_path in image_paths:
            page = await self.process_page(image_path)
            results.append(page)

        successful = sum(1 for r in results if r is not None)
        logger.info(
            f"Batch processing complete: {successful}/{len(image_paths)} pages successful"
        )
        return results

    def get_supported_formats(self) -> list[str]:
        """Get list of supported image formats.

        Returns:
            List of supported file extensions (without dots).
        """
        # This would typically query the underlying OCR engine
        return ["png", "jpg", "jpeg", "tiff", "bmp"]

    def is_format_supported(self, image_path: Path) -> bool:
        """Check if an image format is supported.

        Args:
            image_path: Path to the image file.

        Returns:
            True if the format is supported, False otherwise.
        """
        suffix = image_path.suffix.lower().lstrip(".")
        return suffix in self.get_supported_formats()

    def validate_image(self, image_path: Path) -> tuple[bool, Optional[str]]:
        """Validate an image file for OCR processing.

        Args:
            image_path: Path to the image file.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is None.
        """
        if not image_path.exists():
            return False, f"Image file does not exist: {image_path}"

        if not image_path.is_file():
            return False, f"Path is not a file: {image_path}"

        if not self.is_format_supported(image_path):
            supported = ", ".join(self.get_supported_formats())
            return False, f"Unsupported format. Supported: {supported}"

        # Could add more validation here (file size, dimensions, etc.)
        return True, None
