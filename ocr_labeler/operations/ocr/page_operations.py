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
        self.page_parser = self.build_initial_page_parser(docTR_predictor)

    def build_initial_page_parser(self, docTR_predictor=None):
        """Return an initial page parser that performs OCR via DocTR when invoked.

        This creates a parser for the initial OCR processing of pages from images.
        This is distinct from loading/saving work done on already processed pages.

        Separated for easier testing & potential alternative implementations (e.g.,
        different OCR engines or caching strategies).
        """

        def _get_predictor():
            if docTR_predictor is None:
                from pd_book_tools.ocr.doctr_support import get_default_doctr_predictor

                predictor = get_default_doctr_predictor()
            return predictor

        def _parse_page(
            path: Path,
            index: int,
            ground_truth_string: str,
            rerun_ocr_and_match: bool = False,
        ) -> Page:
            from pd_book_tools.ocr.document import Document

            predictor = _get_predictor()
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
                "source_lib": "doctr-pgdp-labeled",
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

            # If the expected file doesn't exist, try to find any matching file
            if not json_path.exists():
                logger.debug(
                    f"Expected file {json_path} not found, searching for alternatives"
                )
                # Try broader patterns to find any file for this page number
                patterns = [
                    f"_{page_number:03d}.json",  # _001.json
                    f"*{page_number:03d}.json",  # *001.json (any prefix)
                    f"*_{page_number:03d}.json",  # *_001.json
                ]

                matching_files = []
                for pattern in patterns:
                    files = list(save_dir.glob(pattern))
                    if files:
                        matching_files.extend(files)
                        logger.debug(f"Pattern '{pattern}' found {len(files)} files")

                if matching_files:
                    # Use the first match
                    json_path = matching_files[0]
                    json_filename = json_path.name
                    # Extract project_id from the filename
                    file_prefix = json_filename.replace(".json", "")
                    logger.debug(f"Found alternative file: {json_path}")
                else:
                    logger.info(
                        f"No saved page files found for page {page_number} in {save_dir}"
                    )
                    # Log what files do exist for debugging
                    all_json_files = list(save_dir.glob("*.json"))
                    logger.info(
                        f"Available JSON files: {[f.name for f in all_json_files]}"
                    )
                    return None

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
