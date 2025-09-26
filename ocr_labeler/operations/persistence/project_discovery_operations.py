"""Project discovery operations for finding and managing available projects."""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ProjectDiscoveryOperations:
    """Operations for discovering and managing available projects.

    Handles scanning directories for project subdirectories containing images,
    validating project structure, and providing project listings.
    """

    @staticmethod
    def list_available_projects(
        base_projects_root: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """Return mapping of project name -> path under the canonical data root.

        The dropdown in the view should be populated from the fixed directory:
            ~/ocr/data/source-pgdp-data/output

        A "project" is any immediate subdirectory containing at least one image file
        (*.png|*.jpg|*.jpeg). If the root doesn't exist, returns an empty dict.

        Args:
            base_projects_root: Override for the projects root directory.
                              If None, uses default path.

        Returns:
            Dictionary mapping project names to their paths.
        """
        # Determine discovery base: explicit override -> legacy fixed path.
        discovery_root: Path
        if base_projects_root is not None:
            try:
                discovery_root = Path(base_projects_root).expanduser().resolve()
            except Exception:  # pragma: no cover - resolution error
                logger.critical(
                    "Failed to resolve custom projects root %s",
                    base_projects_root,
                    exc_info=True,
                )
                return {}
        else:
            try:
                discovery_root = (
                    Path("~/ocr/data/source-pgdp-data/output").expanduser().resolve()
                )
            except Exception:  # pragma: no cover - path resolution errors
                logger.critical("Project root path resolution failed", exc_info=True)
                return {}
        try:
            base_root = discovery_root
        except Exception:  # pragma: no cover - path resolution errors
            logger.critical("Project root path resolution failed", exc_info=True)
            return {}
        if not base_root.exists():  # pragma: no cover - environment dependent
            logger.critical("No project root found", exc_info=True)
            return {}
        projects: Dict[str, Path] = {}
        try:
            for d in sorted(p for p in base_root.iterdir() if p.is_dir()):
                try:
                    if any(
                        f.suffix.lower() in {".png", ".jpg", ".jpeg"}
                        for f in d.iterdir()
                        if f.is_file()
                    ):
                        projects[d.name] = d
                except Exception:  # noqa: BLE001 - skip unreadable child
                    logger.critical(
                        "Failed to read project directory %s", d, exc_info=True
                    )
                    continue
        except Exception:  # pragma: no cover - defensive
            logger.critical("Project discovery failed", exc_info=True)
            return {}
        return projects

    @staticmethod
    def validate_project_directory(directory: Path) -> bool:
        """Validate that a directory contains valid project structure.

        Args:
            directory: Path to the project directory to validate.

        Returns:
            True if directory contains image files and is valid, False otherwise.
        """
        if not directory.exists() or not directory.is_dir():
            return False

        try:
            return any(
                f.suffix.lower() in {".png", ".jpg", ".jpeg"}
                for f in directory.iterdir()
                if f.is_file()
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to validate project directory %s", directory)
            return False

    @staticmethod
    def get_project_keys(projects: Dict[str, Path]) -> list[str]:
        """Get sorted list of project keys from projects dictionary.

        Args:
            projects: Dictionary mapping project names to paths.

        Returns:
            Sorted list of project keys.
        """
        return sorted(projects.keys())

    @staticmethod
    def get_default_project_key(project_keys: list[str]) -> Optional[str]:
        """Get the default project key from a list of keys.

        Args:
            project_keys: List of available project keys.

        Returns:
            First project key if available, None otherwise.
        """
        return project_keys[0] if project_keys else None
