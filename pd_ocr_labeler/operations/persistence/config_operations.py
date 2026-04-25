"""Configuration file operations used by persistence layer."""

from __future__ import annotations

import logging
from pathlib import Path

from .persistence_paths_operations import PersistencePathsOperations

logger = logging.getLogger(__name__)


class ConfigOperations:
    """Read application configuration from user config directories."""

    DISCOVERY_CONFIG_KEY = "source_projects_root"
    # Optional override path used by tests or embedding contexts.
    CONFIG_PATH: Path | None = None

    @staticmethod
    def get_default_config_path() -> Path:
        """Return OS-aware default location for config.yaml."""
        return PersistencePathsOperations.get_default_config_path()

    @staticmethod
    def get_default_source_projects_root() -> Path:
        """Return OS-aware default source projects root."""
        return PersistencePathsOperations.get_default_source_projects_root()

    @staticmethod
    def _default_config_contents() -> str:
        default_root = ConfigOperations.get_default_source_projects_root().as_posix()
        return (
            "# Root directory containing OCR project subdirectories.\n"
            "# Each child directory is treated as a project when it contains image files.\n"
            f'{ConfigOperations.DISCOVERY_CONFIG_KEY}: "{default_root}"\n'
        )

    @staticmethod
    def _ensure_config_file(path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                ConfigOperations._default_config_contents(), encoding="utf-8"
            )
            logger.info("Created default config file at %s", path)
        except Exception:
            logger.warning(
                "Failed to create default config file at %s", path, exc_info=True
            )

    @staticmethod
    def set_source_projects_root(path: Path) -> None:
        """Persist a new source projects root to the config file."""
        config_path = (
            ConfigOperations.CONFIG_PATH or ConfigOperations.get_default_config_path()
        )
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                "# Root directory containing OCR project subdirectories.\n"
                "# Each child directory is treated as a project when it contains image files.\n"
                f'{ConfigOperations.DISCOVERY_CONFIG_KEY}: "{path.as_posix()}"\n',
                encoding="utf-8",
            )
            logger.info("Updated source_projects_root to %s in %s", path, config_path)
        except Exception:
            logger.warning(
                "Failed to write source_projects_root to %s", config_path, exc_info=True
            )

    @staticmethod
    def get_source_projects_root(config_path: Path | None = None) -> Path:
        """Return source projects root from config with fallback default.

        Expected YAML shape:
            source_projects_root: ~/path/to/projects
        """
        path = (
            config_path
            or ConfigOperations.CONFIG_PATH
            or ConfigOperations.get_default_config_path()
        )

        if not path.exists():
            logger.debug("Config file not found at %s", path)
            ConfigOperations._ensure_config_file(path)
            return ConfigOperations.get_default_source_projects_root()

        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue

                key, value = line.split(":", 1)
                if key.strip() != ConfigOperations.DISCOVERY_CONFIG_KEY:
                    continue

                configured_root = value.strip().strip('"').strip("'")
                if configured_root:
                    return Path(configured_root)

                logger.warning(
                    "Config key '%s' is empty in %s",
                    ConfigOperations.DISCOVERY_CONFIG_KEY,
                    path,
                )
                return ConfigOperations.get_default_source_projects_root()
        except Exception:
            logger.warning(
                "Failed to parse config file at %s",
                path,
                exc_info=True,
            )
            return ConfigOperations.get_default_source_projects_root()

        logger.warning(
            "Config key '%s' not found in %s",
            ConfigOperations.DISCOVERY_CONFIG_KEY,
            path,
        )
        return ConfigOperations.get_default_source_projects_root()
