"""Project operations for OCR labeling tasks.

This module contains operations that can be performed on projects, such as saving,
loading, exporting, and other project-level persistence functionality. These operations
are separated from state management to maintain clear architectural boundaries.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from ...models.project import Project

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
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Find all image files with supported extensions
        image_extensions = {".png", ".jpg", ".jpeg"}
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

    def create_project(self, directory: Path, images: List[Path]) -> "Project":
        """Create a Project object from directory and image paths.

        This method handles all the project creation logic including:
        - Loading ground truth mapping
        - Building page loader
        - Creating Project object with proper initialization

        Args:
            directory: Project root directory.
            images: List of image file paths.

        Returns:
            Project: Initialized Project object.
        """
        # Import here to avoid circular imports and allow for test monkeypatching
        try:
            from ..page_loader import build_page_loader
            from .page_operations import PageOperations
        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}")
            raise

        # Load ground truth mapping if available
        page_ops = PageOperations()
        ground_truth_map = page_ops.load_ground_truth_map(directory)
        logger.info(f"Loaded ground truth mapping with {len(ground_truth_map)} entries")

        # Build page loader for OCR processing
        page_loader = build_page_loader()
        logger.info("Built page loader for OCR processing")

        # Create placeholder pages (will be lazily loaded)
        placeholders = [None] * len(images)

        # Import Project here to avoid circular imports
        from ...models.project import Project

        # Create and return Project object
        project = Project(
            pages=placeholders,
            image_paths=images,
            current_page_index=0 if images else -1,
            page_loader=page_loader,
            ground_truth_map=ground_truth_map,
        )

        logger.info(
            f"Created project with {len(images)} images, current index: {project.current_page_index}"
        )
        return project

    def save_project(
        self,
        project: "Project",
        project_root: Path,
        save_directory: str = "local-data/labeled-projects",
        project_id: Optional[str] = None,
        include_images: bool = True,
    ) -> bool:
        """Save an entire project to disk with all pages and metadata.

        Creates a project directory structure:
        - <project_id>/
          - images/          (if include_images=True)
          - pages/           (JSON files for each page)
          - project.json     (Project metadata)
          - pages.json       (Ground truth mapping, if present)

        Args:
            project: Project object to save (required).
            project_root: Root directory of the source project.
            save_directory: Base directory for saved projects.
            project_id: Project identifier. If None, derives from project_root name.
            include_images: Whether to copy image files (default: True).

        Returns:
            bool: True if save was successful, False otherwise.
        """
        try:
            # Generate project ID if not provided
            if project_id is None:
                project_id = project_root.name

            # Create project directory structure
            project_dir = Path(save_directory) / project_id
            project_dir.mkdir(parents=True, exist_ok=True)

            pages_dir = project_dir / "pages"
            pages_dir.mkdir(exist_ok=True)

            if include_images:
                images_dir = project_dir / "images"
                images_dir.mkdir(exist_ok=True)

            # Save individual pages
            saved_pages = 0
            for idx, page in enumerate(project.pages):
                if page is None:
                    continue

                page_filename = f"page_{idx + 1:03d}.json"
                page_path = pages_dir / page_filename

                try:
                    page_data = page.to_dict()
                    with open(page_path, "w", encoding="utf-8") as f:
                        json.dump(page_data, f, indent=2, ensure_ascii=False)
                    saved_pages += 1
                except Exception as e:
                    logger.warning(f"Failed to save page {idx + 1}: {e}")

            # Copy images if requested
            copied_images = 0
            if include_images:
                for idx, image_path in enumerate(project.image_paths):
                    if not Path(image_path).exists():
                        logger.warning(f"Source image not found: {image_path}")
                        continue

                    image_suffix = Path(image_path).suffix.lower()
                    image_filename = f"page_{idx + 1:03d}{image_suffix}"
                    image_dest = images_dir / image_filename

                    try:
                        shutil.copy2(image_path, image_dest)
                        copied_images += 1
                    except Exception as e:
                        logger.warning(f"Failed to copy image {image_path}: {e}")

            # Save project metadata
            project_metadata = {
                "version": "1.0",
                "source_lib": "ocr-labeler",
                "project_id": project_id,
                "source_path": str(project_root),
                "total_pages": len(project.image_paths),
                "saved_pages": saved_pages,
                "current_page_index": project.current_page_index,
                "include_images": include_images,
            }

            if include_images:
                project_metadata["copied_images"] = copied_images

            project_json_path = project_dir / "project.json"
            with open(project_json_path, "w", encoding="utf-8") as f:
                json.dump(project_metadata, f, indent=2, ensure_ascii=False)

            # Copy ground truth file if it exists
            ground_truth_source = project_root / "pages.json"
            if ground_truth_source.exists():
                ground_truth_dest = project_dir / "pages.json"
                shutil.copy2(ground_truth_source, ground_truth_dest)
                logger.info(f"Copied ground truth file: {ground_truth_dest}")

            logger.info(
                f"Saved project '{project_id}' to {project_dir} "
                f"({saved_pages} pages, {copied_images if include_images else 0} images)"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to save project: {e}")
            return False

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

            logger.info(
                f"Loaded project metadata for: {metadata.get('project_id', 'unknown')}"
            )
            return metadata

        except Exception as e:
            logger.exception(f"Failed to load project metadata: {e}")
            return None

    def export_project(
        self,
        project: "Project",
        project_root: Path,
        export_path: Path,
        format_type: str = "json",
        include_ground_truth: bool = True,
    ) -> bool:
        """Export project data in various formats for training or analysis.

        Args:
            project: Project object to export.
            project_root: Root directory of the source project.
            export_path: Output file path for the export.
            format_type: Export format ("json", "csv", "jsonl").
            include_ground_truth: Whether to include ground truth data.

        Returns:
            bool: True if export was successful, False otherwise.
        """
        try:
            export_data = []

            for idx, page in enumerate(project.pages):
                if page is None:
                    continue

                page_data = {
                    "page_index": idx,
                    "image_path": str(project.image_paths[idx]),
                    "page_data": page.to_dict(),
                }

                if include_ground_truth and hasattr(page, "ground_truth_text"):
                    page_data["ground_truth"] = getattr(page, "ground_truth_text", None)

                export_data.append(page_data)

            # Create export directory
            export_path.parent.mkdir(parents=True, exist_ok=True)

            if format_type == "json":
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "project_metadata": {
                                "source_path": str(project_root),
                                "total_pages": len(project.pages),
                                "exported_pages": len(export_data),
                            },
                            "pages": export_data,
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

            elif format_type == "jsonl":
                with open(export_path, "w", encoding="utf-8") as f:
                    for page_data in export_data:
                        f.write(json.dumps(page_data, ensure_ascii=False) + "\n")

            elif format_type == "csv":
                # For CSV, we'll need to flatten the data structure
                # This is a simplified version - could be extended based on needs
                import csv

                with open(export_path, "w", newline="", encoding="utf-8") as f:
                    if export_data:
                        fieldnames = ["page_index", "image_path", "page_json"]
                        if include_ground_truth:
                            fieldnames.append("ground_truth")

                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()

                        for page_data in export_data:
                            row = {
                                "page_index": page_data["page_index"],
                                "image_path": page_data["image_path"],
                                "page_json": json.dumps(page_data["page_data"]),
                            }
                            if include_ground_truth and "ground_truth" in page_data:
                                row["ground_truth"] = page_data.get("ground_truth", "")
                            writer.writerow(row)
            else:
                logger.error(f"Unsupported export format: {format_type}")
                return False

            logger.info(
                f"Exported project to {export_path} in {format_type} format ({len(export_data)} pages)"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to export project: {e}")
            return False

    def backup_project(
        self,
        source_directory: Path,
        backup_directory: str = "local-data/project-backups",
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

            backup_dir = Path(backup_directory)
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
        self, save_directory: str = "local-data/labeled-projects"
    ) -> List[Dict]:
        """List all saved projects with their metadata.

        Args:
            save_directory: Directory containing saved projects.

        Returns:
            List of dictionaries containing project metadata.
        """
        saved_projects = []

        try:
            save_dir = Path(save_directory)
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

    def reload_ground_truth_into_project(self, state):  # type: ignore[misc]
        """Reload ground truth data into an existing project.

        Currently a placeholder for future implementation.

        Parameters
        ----------
        state : AppState
            Application state containing the project to update
        """
        pass
        # TODO: this should instead allow remapping of ground truth to OCR
