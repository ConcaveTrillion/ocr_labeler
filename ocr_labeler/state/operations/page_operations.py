"""Page operations for OCR labeling tasks.

This module contains operations that can be performed on pages, such as saving,
loading, exporting, and other persistence-related functionality. These operations
are separated from state management to maintain clear architectural boundaries.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import NamedTuple, Optional

from pd_book_tools.ocr.page import Page  # type: ignore

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

            return page

        except Exception as e:
            logger.exception(f"Failed to load page {page_number}: {e}")
            return None

    def can_load_page(
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
            load_info = operations.can_load_page(
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
            can_load = save_dir.exists() and json_path.exists()

            if can_load:
                # Additional validation: check if file is readable and has basic structure
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

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

    def _normalize_ground_truth_entries(self, data: dict) -> dict[str, str]:
        """Normalize ground truth entries for flexible filename lookup.

        Creates multiple lookup keys for each entry:
        - Original key
        - Lowercase variant
        - With/without file extensions

        Parameters
        ----------
        data : dict
            Raw ground truth data from JSON

        Returns
        -------
        dict[str, str]
            Normalized lookup dictionary with multiple keys per entry
        """
        norm: dict[str, str] = {}
        for k, v in data.items():
            if not isinstance(k, str):
                continue
            text_val: str | None = (
                v if isinstance(v, str) else (str(v) if v is not None else None)
            )
            if text_val is None:
                continue
            norm[k] = text_val
            lower_k = k.lower()
            norm.setdefault(lower_k, text_val)
            if "." not in k:
                for ext in IMAGE_EXTS:
                    norm.setdefault(f"{k}{ext}", text_val)
                    norm.setdefault(f"{k}{ext}".lower(), text_val)
        return norm

    def load_ground_truth_map(self, directory: Path) -> dict[str, str]:
        """Load and normalize ground truth data from pages.json file.

        Parameters
        ----------
        directory : Path
            Directory containing pages.json file

        Returns
        -------
        dict[str, str]
            Normalized ground truth mapping, empty dict if file not found or invalid
        """
        pages_json = directory / "pages.json"
        if not pages_json.exists():
            logger.info("No pages.json found in %s", directory)
            return {}
        try:
            raw_text = pages_json.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            if isinstance(data, dict):
                norm = self._normalize_ground_truth_entries(data)
                logger.info(
                    "Loaded %d ground truth entries from %s", len(norm), pages_json
                )
                return norm
            logger.warning("pages.json root is not an object (dict): %s", pages_json)
        except Exception as exc:  # pragma: no cover - robustness
            logger.warning("Failed to load pages.json (%s): %s", pages_json, exc)
        return {}

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
