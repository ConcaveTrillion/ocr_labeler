"""Page operations for OCR labeling tasks.

This module contains operations that can be performed on pages, such as saving,
loading, exporting, and other persistence-related functionality. These operations
are separated from state management to maintain clear architectural boundaries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Optional

from pd_book_tools.ocr.page import Page  # type: ignore

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Constants for ground truth operations
IMAGE_EXTS = (".png", ".jpg", ".jpeg")


class PageLoadInfo(NamedTuple):
    """Information about a page's load availability and file paths."""

    can_load: bool
    json_filename: str
    json_path: Path
    file_prefix: str


class PageOperations:
    """Handle page-level operations like save, load, export, and reset.

    This class provides functionality for:
    - Saving pages to disk with metadata
    - Loading pages from saved files
    - Exporting pages in various formats
    - Resetting OCR data for pages

    Operations are designed to be stateless and work with dependency injection
    to avoid tight coupling with state management classes.
    """

    def __init__(self, docTR_predictor=None):
        """Initialize PageOperations with its own page parser.

        Args:
            docTR_predictor: Optional predictor for OCR processing
        """
        # Store the predictor at instance level to avoid recreating it per-page
        self._docTR_predictor = docTR_predictor
        self._predictor_initialized = False
        self.page_parser = self.build_initial_page_parser()

    def _get_or_create_predictor(self):
        """Get or create the DocTR predictor instance.

        Lazy initialization to avoid loading models until actually needed.
        Ensures each PageOperations instance has its own predictor for thread safety.
        """
        if not self._predictor_initialized:
            if self._docTR_predictor is None:
                from pd_book_tools.ocr.doctr_support import get_default_doctr_predictor

                self._docTR_predictor = get_default_doctr_predictor()
            self._predictor_initialized = True
        return self._docTR_predictor

    def build_initial_page_parser(self):
        """Return an initial page parser that performs OCR via DocTR when invoked.

        This creates a parser for the initial OCR processing of pages from images.
        This is distinct from loading/saving work done on already processed pages.

        The returned parser supports force refresh semantics - when called, it
        always runs OCR on the image regardless of any cached state. Higher-level
        code controls whether to use saved results or force fresh OCR processing.

        Separated for easier testing & potential alternative implementations (e.g.,
        different OCR engines or caching strategies).

        Returns:
            Callable that takes (path, index, ground_truth_string) and returns
            a Page object with OCR results.
        """

        def _parse_page(
            path: Path,
            index: int,
            ground_truth_string: str,
        ) -> Page:
            from pd_book_tools.ocr.document import Document

            predictor = self._get_or_create_predictor()
            doc = Document.from_image_ocr_via_doctr(
                path,
                source_identifier=path.name,
                predictor=predictor,
            )
            page_obj: Page = doc.pages[0]

            if ground_truth_string:
                page_obj.add_ground_truth(ground_truth_string)

            from cv2 import imread as cv2_imread

            img = cv2_imread(str(path))
            if img is not None:
                page_obj.cv2_numpy_page_image = img
                logger.debug("attached cv2 image for index %s", index)
            return page_obj

        return _parse_page

    def save_page(
        self,
        page: Page,
        project_root: Path,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
        source_lib: str = "doctr-pgdp-labeled",
    ) -> bool:
        """Save a single page object to a file with both image copy and JSON metadata.

        Creates two files in the save directory:
        - <project_id>_<page_number>.png (or .jpg): Copy of original image
        - <project_id>_<page_number>.json: Metadata with serialized Page object

        Args:
            page: Page object to save (required).
            project_root: Root directory of the project for relative path calculation.
            save_directory: Directory to save files (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project_root name.
            source_lib: Source library identifier (default: "doctr-pgdp-labeled").

        Returns:
            bool: True if save was successful, False otherwise.

        Example:
            # Save page with default settings
            operations = PageOperations()
            success = operations.save_page(
                page=my_page,
                project_root=Path("/path/to/project")
            )

            # Save with custom directory and project ID
            success = operations.save_page(
                page=my_page,
                project_root=Path("/path/to/project"),
                save_directory="my-output/labeled-data",
                project_id="book_chapter_1"
            )
        """
        try:
            # Generate project ID if not provided
            if project_id is None:
                project_id = project_root.name

            # Create save directory
            save_dir = Path(save_directory)
            save_dir.mkdir(parents=True, exist_ok=True)

            # Get page number (1-based for filenames)
            page_number = getattr(page, "index", 0) + 1

            # Get original image path
            image_path = getattr(page, "image_path", None)
            if image_path is None:
                logger.error("Page has no associated image_path")
                return False

            # Determine file extensions
            image_suffix = Path(image_path).suffix.lower()
            if image_suffix not in {".png", ".jpg", ".jpeg"}:
                image_suffix = ".png"  # Default fallback

            # Create file names
            file_prefix = f"{project_id}_{page_number:03d}"
            image_filename = f"{file_prefix}{image_suffix}"
            json_filename = f"{file_prefix}.json"

            # Copy image file
            image_dest = save_dir / image_filename
            shutil.copy2(image_path, image_dest)
            logger.info(f"Copied image to: {image_dest}")

            # Create JSON metadata with relative path (fallback to filename if not relative)
            try:
                relative_path = str(Path(image_path).relative_to(project_root))
            except ValueError:
                # If image_path is not relative to project_root, use just the filename
                relative_path = Path(image_path).name

            json_data = {
                "source_lib": source_lib,
                "source_path": relative_path,
                "pages": [page.to_dict()],
            }

            # Save JSON file
            json_dest = save_dir / json_filename
            with open(json_dest, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON metadata to: {json_dest}")

            return True

        except Exception as e:
            logger.exception(f"Failed to save page: {e}")
            return False

    def load_page(
        self,
        page_number: int,
        project_root: Path,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> Optional[Page]:
        """Load a previously saved page from disk with metadata and image.

        Looks for saved files in the save directory:
        - <project_id>_<page_number>.json: Metadata with serialized Page object
        - <project_id>_<page_number>.png (or .jpg): Image file (not directly loaded into Page)

        Args:
            page_number: Page number to load (1-based indexing to match save_page).
            project_root: Root directory of the project.
            save_directory: Directory where files were saved (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project_root name.

        Returns:
            Page: Loaded Page object if found and valid, None otherwise.

        Example:
            # Load page with default settings
            operations = PageOperations()
            page = operations.load_page(
                page_number=1,
                project_root=Path("/path/to/project")
            )

            # Load with custom directory and project ID
            page = operations.load_page(
                page_number=5,
                project_root=Path("/path/to/project"),
                save_directory="my-output/labeled-data",
                project_id="book_chapter_1"
            )
        """
        try:
            if project_id is None:
                project_id = project_root.name

            save_dir = Path(save_directory)
            if not save_dir.exists():
                logger.info(f"Save directory does not exist: {save_dir}")
                return None

            file_prefix = f"{project_id}_{page_number:03d}"
            json_filename = f"{file_prefix}.json"
            json_path = save_dir / json_filename

            if not json_path.exists():
                logger.info(f"Saved page not found: {json_path}")
                return None

            # Load JSON metadata
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # Validate JSON structure
            if not isinstance(json_data, dict):
                logger.error(f"Invalid JSON structure in {json_path}")
                return None

            pages_data = json_data.get("pages", [])
            if not pages_data or not isinstance(pages_data, list):
                logger.error(f"No pages data found in {json_path}")
                return None

            # Load the first (and should be only) page from the list
            page_dict = pages_data[0]
            if not isinstance(page_dict, dict):
                logger.error(f"Invalid page data structure in {json_path}")
                return None

            # Reconstruct Page object from dictionary
            page = Page.from_dict(page_dict)
            logger.info(f"Successfully loaded page from: {json_path}")

            # Restore the original image path from source_path
            source_path = json_data.get("source_path")
            if source_path:
                page.image_path = project_root / source_path  # type: ignore[attr-defined]
                logger.debug(f"Restored image_path: {page.image_path}")
            else:
                logger.warning(
                    f"No source_path found in {json_path}, checking for saved image"
                )

            # Load the corresponding image file and attach it to the page
            # Try to find the image file (could be .png, .jpg, or .jpeg)
            image_path = None
            for ext in IMAGE_EXTS:
                candidate_path = save_dir / f"{file_prefix}{ext}"
                if candidate_path.exists():
                    image_path = candidate_path
                    break

            # If we don't have image_path from source_path, use the saved image as fallback
            if not hasattr(page, "image_path") or page.image_path is None:
                if image_path:
                    page.image_path = image_path  # type: ignore[attr-defined]
                    logger.debug(f"Using saved image as image_path: {image_path}")
                else:
                    logger.warning(
                        f"No image_path available for loaded page from {json_path}"
                    )

            if image_path:
                try:
                    from cv2 import imread as cv2_imread

                    img = cv2_imread(str(image_path))
                    if img is not None:
                        page.cv2_numpy_page_image = img
                        logger.debug(
                            f"Attached cv2 image for loaded page: {image_path}"
                        )
                    else:
                        logger.warning(f"Failed to load image from: {image_path}")
                except Exception as e:
                    logger.warning(f"Error loading image {image_path}: {e}")
            else:
                logger.warning(f"No image file found for prefix: {file_prefix}")

            return page

        except Exception as e:
            logger.exception(f"Failed to load page {page_number}: {e}")
            return None

    def refine_all_bboxes(self, page: Page, padding_px: int = 2) -> bool:
        """Refine all bounding boxes in a page with specified padding.

        Calls page.refine_bounding_boxes(padding_px) and refreshes page images.

        Args:
            page: Page object to refine bboxes for.
            padding_px: Padding in pixels to use for refinement (default: 2).

        Returns:
            bool: True if refinement was successful, False otherwise.
        """
        try:
            logger.debug(f"Refining bboxes for page with padding_px={padding_px}")
            page.refine_bounding_boxes(padding_px=padding_px)

            # Refresh page images after bbox changes
            if hasattr(page, "refresh_page_images"):
                page.refresh_page_images()
                logger.debug("Refreshed page images after bbox refinement")

            logger.info("Successfully refined bboxes for page")
            return True
        except Exception as e:
            logger.exception(f"Failed to refine bboxes for page: {e}")
            return False

    def expand_and_refine_all_bboxes(self, page: Page, padding_px: int = 2) -> bool:
        """Expand and refine all bounding boxes in a page.

        Iterates through all words in the page, calling crop_bottom() and expand_to_content()
        on each word, then calls page.refine_bounding_boxes(padding_px) and refreshes page images.

        Args:
            page: Page object to expand and refine bboxes for.
            padding_px: Padding in pixels to use for refinement (default: 2).

        Returns:
            bool: True if operation was successful, False otherwise.
        """
        try:
            logger.debug(
                f"Expanding and refining bboxes for page with padding_px={padding_px}"
            )

            # Iterate through all words and apply crop_bottom + expand_to_content
            word_blocks = None
            if hasattr(page, "blocks"):
                word_blocks = page.blocks
            elif hasattr(page, "lines"):
                word_blocks = page.lines

            if word_blocks is None:
                logger.warning(
                    "Page has no blocks/lines; skipping expand/refine word pass"
                )
                return False

            page_image = None
            if hasattr(page, "cv2_numpy_page_image"):
                page_image = page.cv2_numpy_page_image

            for block in word_blocks:
                words = getattr(block, "words", None)
                if not words:
                    continue
                for word in words:
                    if hasattr(word, "crop_bottom"):
                        try:
                            word.crop_bottom()  # type: ignore[attr-defined]
                        except TypeError:
                            if page_image is not None:
                                word.crop_bottom(page_image)  # type: ignore[attr-defined]
                            else:
                                raise
                    if hasattr(word, "expand_to_content"):
                        try:
                            word.expand_to_content()  # type: ignore[attr-defined]
                        except TypeError:
                            if page_image is not None:
                                word.expand_to_content(page_image)  # type: ignore[attr-defined]
                            else:
                                raise

            # Then refine bboxes
            page.refine_bounding_boxes(padding_px=padding_px)

            # Refresh page images after bbox changes
            if hasattr(page, "refresh_page_images"):
                page.refresh_page_images()
                logger.debug("Refreshed page images after expand and refine")

            logger.info("Successfully expanded and refined bboxes for page")
            return True
        except Exception as e:
            logger.exception(f"Failed to expand and refine bboxes for page: {e}")
            return False

    async def can_load_page(
        self,
        page_number: int,
        project_root: Path,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> PageLoadInfo:
        """Check if a page can be loaded and return validation information.

        Validates that the required JSON file exists for the specified page and
        returns detailed information about the file paths and availability.

        Args:
            page_number: Page number to check (1-based indexing to match save_page).
            project_root: Root directory of the project.
            save_directory: Directory where files were saved (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project_root name.

        Returns:
            PageLoadInfo: Named tuple containing:
                - can_load (bool): Whether the page can be loaded
                - json_filename (str): Name of the JSON file
                - json_path (Path): Full path to the JSON file
                - file_prefix (str): File prefix used for naming

        Example:
            # Check if page can be loaded with default settings
            operations = PageOperations()
            load_info = await operations.can_load_page(
                page_number=1,
                project_root=Path("/path/to/project")
            )

            if load_info.can_load:
                print(f"Page can be loaded from: {load_info.json_path}")
            else:
                print(f"Page not available at: {load_info.json_path}")
        """
        try:
            # Generate project ID if not provided
            if project_id is None:
                project_id = project_root.name

            # Create save directory path
            save_dir = Path(save_directory)

            # Create file names (matching save_page format)
            file_prefix = f"{project_id}_{page_number:03d}"
            json_filename = f"{file_prefix}.json"
            json_path = save_dir / json_filename

            # Check if save directory and JSON file exist
            save_dir_exists = await asyncio.to_thread(save_dir.exists)
            json_path_exists = await asyncio.to_thread(json_path.exists)
            can_load = save_dir_exists and json_path_exists

            if can_load:
                # Additional validation: check if file is readable and has basic structure
                try:
                    raw_text = await asyncio.to_thread(
                        json_path.read_text, encoding="utf-8"
                    )
                    json_data = await asyncio.to_thread(json.loads, raw_text)

                    # Basic structure validation
                    if not isinstance(json_data, dict) or "pages" not in json_data:
                        can_load = False
                        logger.warning(f"Invalid JSON structure in {json_path}")
                except Exception as e:
                    can_load = False
                    logger.warning(f"Cannot read or parse JSON file {json_path}: {e}")

            return PageLoadInfo(
                can_load=can_load,
                json_filename=json_filename,
                json_path=json_path,
                file_prefix=file_prefix,
            )

        except Exception as e:
            logger.exception(f"Failed to check page {page_number} availability: {e}")
            # Return a safe default with the computed paths
            file_prefix = f"{project_id or project_root.name}_{page_number:03d}"
            json_filename = f"{file_prefix}.json"
            json_path = Path(save_directory) / json_filename

            return PageLoadInfo(
                can_load=False,
                json_filename=json_filename,
                json_path=json_path,
                file_prefix=file_prefix,
            )

    def create_fallback_page(
        self,
        index: int,
        img_path: Path,
        ground_truth_map: dict[str, str],
    ) -> Page:
        """Create a fallback page when OCR fails, attaching image and ground truth if available.

        Args:
            index: Zero-based page index.
            img_path: Path to the image file.
            ground_truth_map: Mapping of image names to ground truth text.

        Returns:
            Page: A basic fallback page object.
        """
        page = Page(width=0, height=0, page_index=index, items=[])
        page.image_path = img_path  # type: ignore[attr-defined]
        page.name = img_path.name  # type: ignore[attr-defined]
        page.index = index  # type: ignore[attr-defined]
        page.ocr_failed = True  # type: ignore[attr-defined]

        # Add ground truth if available
        gt_text = self.find_ground_truth_text(img_path.name, ground_truth_map)
        if gt_text:
            page.add_ground_truth(gt_text)  # type: ignore[attr-defined]
            logger.debug("Injected ground truth for fallback page: %s", img_path.name)

        # Best-effort load image
        try:
            from cv2 import imread as cv2_imread

            img = cv2_imread(str(img_path))
            if img is not None:
                page.cv2_numpy_page_image = img  # type: ignore[attr-defined]
                logger.debug("Attached cv2 image for fallback page: %s", img_path.name)
        except Exception:
            logger.debug("cv2 load failed for fallback page: %s", img_path.name)

        return page

    def refresh_page_images(self, page: Page) -> bool:
        """Refresh all generated images (overlays) for a page.

        Calls page.refresh_page_images() if available.

        Args:
            page: Page object to refresh images for.

        Returns:
            bool: True if refresh was successful, False otherwise.
        """
        try:
            if hasattr(page, "refresh_page_images"):
                page.refresh_page_images()
                logger.info("Successfully refreshed page images using native method")
                return True
            else:
                logger.warning("Page object has no native refresh_page_images method")
                return False
        except Exception as e:
            logger.exception(f"Failed to refresh page images: {e}")
            return False

    def reset_ocr(
        self,
        image_path: Path,
        index: int = 0,
        ground_truth_text: str = "",
    ) -> Optional[Page]:
        """Reset OCR processing for a page by re-running DocTR OCR.

        This method forces a fresh OCR run on the image, discarding any cached or
        saved results. It's useful when you want to reprocess an image with the
        current OCR engine settings.

        Args:
            image_path: Path to the image file to process.
            index: Page index (default: 0).
            ground_truth_text: Optional ground truth text to add (default: "").

        Returns:
            Page object with fresh OCR results, or None if processing failed.

        Example:
            operations = PageOperations()
            page = operations.reset_ocr(
                image_path=Path("page_001.png"),
                index=0,
                ground_truth_text="Sample GT text"
            )
        """
        try:
            logger.info(f"Resetting OCR for page: {image_path}")

            # Use the page parser to perform fresh OCR
            page = self.page_parser(
                path=image_path,
                index=index,
                ground_truth_string=ground_truth_text,
            )

            if page is None:
                logger.error(f"Failed to reset OCR for {image_path}")
                return None

            logger.info(f"Successfully reset OCR for {image_path}")
            return page

        except Exception as e:
            logger.exception(f"Error resetting OCR for {image_path}: {e}")
            return None

    def find_ground_truth_text(
        self, name: str, ground_truth_map: dict[str, str]
    ) -> str | None:
        """Find ground truth text for a given page name using variant lookup.

        The normalization process adds multiple keys (with/without extension, lowercase).
        This helper attempts a list of variants in priority order to find a match.

        Parameters
        ----------
        name : str
            The image filename (e.g. "001.png") or bare page identifier
        ground_truth_map : dict[str, str]
            Normalized mapping produced by ``load_ground_truth_map``

        Returns
        -------
        str | None
            Ground truth text if found, None otherwise
        """
        if not name:
            return None
        candidates: list[str] = []
        # Original provided name
        candidates.append(name)
        # Lowercase variant
        candidates.append(name.lower())
        # If name has extension, add base name variants; else add ext variants (handled by normalization)
        if "." in name:
            base = name.rsplit(".", 1)[0]
            candidates.extend([base, base.lower()])
        # Deduplicate while preserving order
        seen = set()
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            if c in ground_truth_map:
                return ground_truth_map[c]
        return None
