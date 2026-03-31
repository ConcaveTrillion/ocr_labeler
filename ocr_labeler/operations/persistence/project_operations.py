"""Project operations for OCR labeling tasks.

This module contains operations that can be performed on    async def create_project(
        self, directory: Path, images: list[Path], ground_truth_map: Optional[dict[str, str]] = None
    ) -> "Project":projects, such as saving,
loading, exporting, and other project-level persistence functionality. These operations
are separated from state management to maintain clear architectural boundaries.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from pd_book_tools.pgdp.pgdp_results import PGDPResults

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

    def scan_project_directory(self, directory: Path) -> List[Path]:
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

    def validate_project_directory(self, directory: Path) -> bool:
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
            images = self.scan_project_directory(directory)
            return len(images) > 0

        except Exception:
            return False

    def create_project(
        self,
        directory: Path,
        images: List[Path],
        ground_truth_map: Optional[dict[str, str]] = None,
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
                f"Using provided ground truth mapping with {len(ground_truth_map)} entries"
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

        logger.info(f"Created project with {len(images)} images")
        return project

    def load_project_metadata(self, project_directory: Path) -> Optional[Dict]:
        """Load project metadata from a saved project directory.

        Args:
            project_directory: Path to saved project directory.

        Returns:
            Dict with project metadata, or None if loading failed.
        """
        try:
            project_json_path = project_directory / "project.json"
            if not project_json_path.exists():
                logger.error(f"Project metadata not found: {project_json_path}")
                return None

            with open(project_json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # Validate metadata structure using Project model
            try:
                from ...models.project_model import Project

                # This will raise an exception if metadata is invalid
                Project.from_dict(metadata)
            except Exception as e:
                logger.warning(f"Invalid project metadata structure: {e}")
                # Continue anyway, as we don't want to break existing projects

            logger.info(
                f"Loaded project metadata for: {metadata.get('project_id', 'unknown')}"
            )
            return metadata

        except Exception as e:
            logger.exception(f"Failed to load project metadata: {e}")
            return None

    def backup_project(
        self,
        source_directory: Path,
        backup_directory: str | Path | None = None,
        backup_name: Optional[str] = None,
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

            logger.info(f"Created project backup: {backup_path}")
            return True

        except Exception as e:
            logger.exception(f"Failed to backup project: {e}")
            return False

    def list_saved_projects(
        self, save_directory: str | Path | None = None
    ) -> List[Dict]:
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

                metadata = self.load_project_metadata(project_dir)
                if metadata:
                    metadata["directory_path"] = str(project_dir)
                    saved_projects.append(metadata)

        except Exception as e:
            logger.exception(f"Failed to list saved projects: {e}")

        return saved_projects

    def _normalize_ground_truth_entries(self, data: dict) -> dict[str, str]:
        """Normalize pages.json entries for flexible filename lookup.

        Raw PGDP text values are preprocessed via ``PGDPResults`` to convert
        diacritic markup, footnote brackets, ASCII dashes, straight quotes,
        and proofer notes into OCR-comparable Unicode.
        """
        image_exts = (".png", ".jpg", ".jpeg")
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
                for ext in image_exts:
                    normalized.setdefault(f"{key}{ext}", text_value)
                    normalized.setdefault(f"{key}{ext}".lower(), text_value)

        return normalized

    def reload_ground_truth_into_project(self, state):  # type: ignore[misc]
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

        pages_json = Path(project_root) / "pages.json"
        new_map: dict[str, str] = {}

        if pages_json.exists():
            try:
                raw_data = json.loads(pages_json.read_text(encoding="utf-8"))
                if isinstance(raw_data, dict):
                    new_map = self._normalize_ground_truth_entries(raw_data)
                    logger.info(
                        "Reloaded %d ground truth entries from %s",
                        len(new_map),
                        pages_json,
                    )
                else:
                    logger.warning(
                        "pages.json root is not an object (dict): %s", pages_json
                    )
            except Exception as exc:
                logger.warning("Failed to reload pages.json (%s): %s", pages_json, exc)
        else:
            logger.info(
                "No pages.json found in %s; clearing ground truth map", project_root
            )

        project.ground_truth_map = new_map

        invalidate_cache = getattr(state, "_invalidate_text_cache", None)
        if callable(invalidate_cache):
            invalidate_cache()

        notify = getattr(state, "notify", None)
        if callable(notify):
            notify()
