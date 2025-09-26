"""OCR service for text recognition operations."""

import logging
from pathlib import Path
from typing import Optional

from ...models.project import Project
from .page_operations import PageOperations

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR operations.

    This service provides a high-level interface for OCR operations,
    abstracting away the details of page processing and text recognition.
    """

    def __init__(self, page_operations: Optional[PageOperations] = None):
        """Initialize the OCR service.

        Args:
            page_operations: Page operations instance. If not provided,
                           a new instance will be created.
        """
        self.page_operations = page_operations or PageOperations()
        logger.debug("OCRService initialized")

    async def process_page(
        self, image_path: Path, project: Optional[Project] = None
    ) -> Optional[object]:
        """Process a page with OCR.

        Args:
            image_path: Path to the image file to process.
            project: Optional project context for processing.

        Returns:
            The processed page object, or None if processing failed.
        """
        try:
            logger.debug(f"Processing page: {image_path}")

            # Use page operations to process the image
            # Note: This is a simplified interface - the actual implementation
            # would depend on the specific page operations API
            page = await self.page_operations.ensure_page(image_path, project)

            if page:
                logger.info(f"Successfully processed page: {image_path}")
                return page
            else:
                logger.warning(f"Failed to process page: {image_path}")
                return None

        except Exception as e:
            logger.exception(f"Error processing page {image_path}: {e}")
            return None

    async def process_pages_batch(
        self, image_paths: list[Path], project: Optional[Project] = None
    ) -> list[Optional[object]]:
        """Process multiple pages with OCR.

        Args:
            image_paths: List of paths to image files to process.
            project: Optional project context for processing.

        Returns:
            List of processed page objects, with None for failed pages.
        """
        results = []
        for image_path in image_paths:
            page = await self.process_page(image_path, project)
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
