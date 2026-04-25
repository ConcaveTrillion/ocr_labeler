"""Project operations for OCR labeling tasks.

This module contains operations that can be performed on projects, such as saving,
loading, exporting, and other project-level persistence functionality. These operations
are separated from state management to maintain clear architectural boundaries.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from pd_book_tools.pgdp.pgdp_results import PGDPResults

from pd_ocr_labeler.constants import IMAGE_EXTS

from .persistence_paths_operations import PersistencePathsOperations

if TYPE_CHECKING:
    from ...models.project_model import Project

logger = logging.getLogger(__name__)


class ProjectOperations:
    """Handle project-level operations like save, load, export, and backup.

    This class provides functionality for:
    - Saving entire projects to disk with metadata
    - Loading projects from saved files
    - Exporting projects in various formats
    - Creating project backups
    - Managing project configurations

    Operations are designed to be stateless and work with dependency injection
    to avoid tight coupling with state management classes.
    """

    @staticmethod
    def scan_project_directory(directory: Path) -> list[Path]:
        """Scan a directory for image files and return sorted paths.

        Args:
            directory: Directory to scan for image files.

        Returns:
            List of sorted image file paths.

        Raises:
            FileNotFoundError: If directory does not exist.
            ValueError: If directory is not a directory.
        """
        directory = Path(directory)

        # Check if directory exists and is a directory
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Find all image files with supported extensions
        image_extensions = {".png", ".jpg", ".jpeg"}

        # Get directory contents
        images = [
            p
            for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in image_extensions
        ]

        # Return sorted by name for consistent ordering
        return sorted(images)

    @staticmethod
    def validate_project_directory(directory: Path) -> bool:
        """Validate that a directory can be used as a project directory.

        Args:
            directory: Directory path to validate.

        Returns:
            bool: True if directory is valid for project loading.
        """
        try:
            directory = Path(directory)
            if not directory.exists() or not directory.is_dir():
                return False

            # Check if directory has at least one image file
            images = ProjectOperations.scan_project_directory(directory)
            return len(images) > 0

        except Exception:
            return False

    @staticmethod
    def create_project(
        directory: Path,
        images: list[Path],
        ground_truth_map: dict[str, str] | None = None,
    ) -> "Project":
        """Create a Project object from directory and image paths.

        This method handles all the project creation logic including:
        - Building page loader
        - Creating Project object with proper initialization

        Note: ground_truth_map should be provided by caller. If not provided,
        an empty mapping will be used.

        Args:
            directory: Project root directory.
            images: List of image file paths.
            ground_truth_map: Optional pre-loaded ground truth mapping.

        Returns:
            Project: Initialized Project object.
        """
        if ground_truth_map is None:
            ground_truth_map = {}
            logger.info("No ground truth mapping provided, using empty mapping")
        else:
            logger.info(
                "Using provided ground truth mapping with %s entries",
                len(ground_truth_map),
            )

        # Create placeholder pages (will be lazily loaded)
        placeholders = [None] * len(images)

        # Import Project here to avoid circular imports
        from ...models.project_model import Project

        # Create and return Project object
        project = Project(
            pages=placeholders,
            image_paths=images,
            ground_truth_map=ground_truth_map,
            source_path=str(directory),
            total_pages=len(images),
        )

        logger.info("Created project with %s images", len(images))
        return project

    @staticmethod
    def load_project_metadata(project_directory: Path) -> dict | None:
        """Load project metadata from a saved project directory.

        Args:
            project_directory: Path to saved project directory.

        Returns:
            Dict with project metadata, or None if loading failed.
        """
        try:
            project_json_path = project_directory / "project.json"
            if not project_json_path.exists():
                logger.error("Project metadata not found: %s", project_json_path)
                return None

            with open(project_json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Validate metadata structure using Project model
            try:
                from ...models.project_model import Project

                # This will raise an exception if metadata is invalid
                Project.from_dict(metadata)
            except Exception as e:
                logger.warning("Invalid project metadata structure: %s", e)
                # Continue anyway, as we don't want to break existing projects

            logger.info(
                "Loaded project metadata for: %s", metadata.get("project_id", "unknown")
            )
            return metadata

        except Exception:
            logger.exception("Failed to load project metadata")
            return None

    @staticmethod
    def backup_project(
        source_directory: Path,
        backup_directory: str | Path | None = None,
        backup_name: str | None = None,
    ) -> bool:
        """Create a backup copy of a project directory.

        Args:
            source_directory: Source project directory to backup.
            backup_directory: Directory to store backups.
            backup_name: Custom backup name. If None, uses timestamp.

        Returns:
            bool: True if backup was successful, False otherwise.
        """
        try:
            import datetime

            if backup_name is None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{source_directory.name}_{timestamp}"

            # Sanitize backup_name: strip any directory separators so it cannot
            # escape the backup_directory.
            backup_name = Path(backup_name).name
            if not backup_name:
                raise ValueError(
                    "backup_name must be a non-empty single path component"
                )

            backup_dir = (
                Path(backup_directory)
                if backup_directory is not None
                else PersistencePathsOperations.get_project_backups_root()
            )
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_path = backup_dir / backup_name

            # Copy entire directory tree
            shutil.copytree(source_directory, backup_path, dirs_exist_ok=False)

            logger.info("Created project backup: %s", backup_path)
            return True

        except Exception:
            logger.exception("Failed to backup project")
            return False

    @staticmethod
    def list_saved_projects(save_directory: str | Path | None = None) -> list[dict]:
        """List all saved projects with their metadata.

        Args:
            save_directory: Directory containing saved projects.

        Returns:
            List of dictionaries containing project metadata.
        """
        saved_projects = []

        try:
            save_dir = (
                Path(save_directory)
                if save_directory is not None
                else PersistencePathsOperations.get_saved_projects_root()
            )
            if not save_dir.exists():
                return saved_projects

            for project_dir in save_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                metadata = ProjectOperations.load_project_metadata(project_dir)
                if metadata:
                    metadata["directory_path"] = str(project_dir)
                    saved_projects.append(metadata)

        except Exception:
            logger.exception("Failed to list saved projects")

        return saved_projects

    @staticmethod
    def _normalize_ground_truth_entries(data: dict) -> dict[str, str]:
        """Normalize pages.json entries for flexible filename lookup.

        Raw PGDP text values are preprocessed via ``PGDPResults`` to convert
        diacritic markup, footnote brackets, ASCII dashes, straight quotes,
        and proofer notes into OCR-comparable Unicode.
        """
        normalized: dict[str, str] = {}

        for key, value in data.items():
            if not isinstance(key, str):
                continue

            text_value: str | None = (
                value
                if isinstance(value, str)
                else (str(value) if value is not None else None)
            )
            if text_value is None:
                continue

            text_value = PGDPResults(key, text_value).processed_page_text
            normalized[key] = text_value
            lower_key = key.lower()
            normalized.setdefault(lower_key, text_value)

            if "." not in key:
                for ext in IMAGE_EXTS:
                    normalized.setdefault(f"{key}{ext}", text_value)
                    normalized.setdefault(f"{key}{ext}".lower(), text_value)

        return normalized

    @classmethod
    def reload_ground_truth_into_project(cls, state):  # type: ignore[misc]
        """Reload ground truth data into an existing project.

        Parameters
        ----------
        state : AppState
            Application state containing the project to update
        """
        project = getattr(state, "project", None)
        project_root = getattr(state, "project_root", None)

        if project is None or project_root is None:
            logger.debug(
                "reload_ground_truth_into_project: missing project or project_root"
            )
            return

        new_map = cls.load_ground_truth_from_directory(Path(project_root))
        project.ground_truth_map = new_map

        invalidate_cache = getattr(state, "_invalidate_text_cache", None)
        if callable(invalidate_cache):
            invalidate_cache()

        notify = getattr(state, "notify", None)
        if callable(notify):
            notify()

    # ------------------------------------------------------------------
    # Multi-JSON ground truth merge
    # ------------------------------------------------------------------

    PAGES_MANIFEST_FILENAME = "pages_manifest.json"

    @classmethod
    def load_ground_truth_from_directory(cls, directory: Path) -> dict[str, str]:
        """Load and merge ground truth data from a project directory.

        Checks for a ``pages_manifest.json`` first.  If found, loads and
        merges each listed source file with its declared page index offset.
        Falls back to a single ``pages.json`` when no manifest is present.

        Parameters
        ----------
        directory : Path
            Project root directory.

        Returns
        -------
        dict[str, str]
            Normalized and merged ground truth mapping.
        """
        manifest_path = directory / cls.PAGES_MANIFEST_FILENAME
        if manifest_path.exists():
            try:
                merged = cls._load_ground_truth_from_manifest(manifest_path)
                logger.info(
                    "Loaded %d ground truth entries from manifest %s",
                    len(merged),
                    manifest_path,
                )
                return merged
            except Exception as exc:
                logger.warning(
                    "Failed to load pages_manifest.json (%s); falling back to pages.json: %s",
                    manifest_path,
                    exc,
                )

        # Single pages.json fallback
        pages_json = directory / "pages.json"
        if not pages_json.exists():
            logger.info("No pages.json found in %s", directory)
            return {}
        try:
            raw_data = json.loads(pages_json.read_text(encoding="utf-8"))
            if isinstance(raw_data, dict):
                norm = cls._normalize_ground_truth_entries(raw_data)
                logger.info(
                    "Loaded %d ground truth entries from %s", len(norm), pages_json
                )
                return norm
            logger.warning("pages.json root is not an object (dict): %s", pages_json)
        except Exception as exc:
            logger.warning("Failed to load pages.json (%s): %s", pages_json, exc)
        return {}

    @classmethod
    def _load_ground_truth_from_manifest(cls, manifest_path: Path) -> dict[str, str]:
        """Parse ``pages_manifest.json`` and merge source files with offsets.

        Manifest schema::

            {
                "schema": "pd_ocr_labeler.pages_manifest",
                "version": "1.0",
                "sources": [
                    {"file": "pages_r1.json", "offset": 0},
                    {"file": "pages_r2.json", "offset": 100}
                ]
            }

        The ``offset`` value is added to the numeric prefix extracted from each
        key in the source file.  For example, key ``"042.png"`` with offset 100
        becomes ``"142.png"``.  If the key does not have a numeric prefix, it is
        included verbatim (no offset applied).

        Parameters
        ----------
        manifest_path : Path
            Path to the manifest JSON file.

        Returns
        -------
        dict[str, str]
            Merged normalized ground truth mapping.
        """
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("pages_manifest.json must be a JSON object")

        sources = raw.get("sources")
        if not isinstance(sources, list):
            raise ValueError("pages_manifest.json must have a 'sources' list")

        base_dir = manifest_path.parent
        merged: dict[str, str] = {}

        for entry in sources:
            if not isinstance(entry, dict):
                logger.warning("Skipping invalid manifest entry: %r", entry)
                continue

            file_name = entry.get("file")
            if not isinstance(file_name, str) or not file_name:
                logger.warning("Skipping manifest entry with missing 'file': %r", entry)
                continue

            offset = int(entry.get("offset", 0))

            source_path = base_dir / file_name
            if not source_path.exists():
                logger.warning("Manifest source file not found: %s", source_path)
                continue

            try:
                source_data = json.loads(source_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning(
                    "Failed to read manifest source %s: %s", source_path, exc
                )
                continue

            if not isinstance(source_data, dict):
                logger.warning(
                    "Manifest source %s is not a JSON object; skipping", source_path
                )
                continue

            # If offset > 0, remap numeric keys before normalizing
            if offset != 0:
                source_data = cls._apply_page_index_offset(source_data, offset)

            partial = cls._normalize_ground_truth_entries(source_data)
            merged.update(partial)
            logger.debug(
                "Merged %d entries from %s (offset=%d)",
                len(partial),
                source_path.name,
                offset,
            )

        return merged

    _NUMERIC_STEM_RE = re.compile(r"^(\d+)(\.\w+)?$")

    @classmethod
    def _apply_page_index_offset(cls, data: dict, offset: int) -> dict:
        """Return a copy of *data* with numeric stems in keys shifted by *offset*.

        Keys whose stems are not purely numeric are passed through unchanged.
        For example, ``"042.png"`` with offset 100 → ``"142.png"``.

        Parameters
        ----------
        data : dict
            Raw key→text mapping from a pages JSON file.
        offset : int
            Integer to add to each numeric stem.

        Returns
        -------
        dict
            New mapping with shifted keys.
        """
        result: dict = {}
        for key, value in data.items():
            if not isinstance(key, str):
                result[key] = value
                continue
            m = cls._NUMERIC_STEM_RE.match(key)
            if m:
                new_num = int(m.group(1)) + offset
                ext = m.group(2) or ""
                new_key = f"{new_num:03d}{ext}"
                result[new_key] = value
            else:
                result[key] = value
        return result
