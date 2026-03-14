"""Shared persistence path operations for config, data, cache, and state."""

from __future__ import annotations

import os
import platform
from pathlib import Path


class PersistencePathsOperations:
    """Resolve OS-aware persistence locations for the application."""

    APP_NAME = "pgdp-ocr-labeler"

    @staticmethod
    def get_config_root() -> Path:
        """Return OS-aware config root directory for the app."""
        system_name = platform.system()

        if system_name == "Linux":
            config_home = os.getenv("XDG_CONFIG_HOME")
            base_dir = (
                Path(config_home).expanduser()
                if config_home
                else Path.home() / ".config"
            )
        elif system_name == "Darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        elif system_name == "Windows":
            appdata = os.getenv("APPDATA")
            base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        else:
            base_dir = Path.home() / ".config"

        return base_dir / PersistencePathsOperations.APP_NAME

    @staticmethod
    def get_data_root() -> Path:
        """Return OS-aware data root directory for the app."""
        system_name = platform.system()

        if system_name == "Linux":
            data_home = os.getenv("XDG_DATA_HOME")
            base_dir = (
                Path(data_home).expanduser()
                if data_home
                else Path.home() / ".local" / "share"
            )
        elif system_name == "Darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        elif system_name == "Windows":
            appdata = os.getenv("APPDATA")
            base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        else:
            base_dir = Path.home() / ".local" / "share"

        return base_dir / PersistencePathsOperations.APP_NAME

    @staticmethod
    def get_cache_root() -> Path:
        """Return OS-aware cache root directory for the app."""
        system_name = platform.system()

        if system_name == "Linux":
            cache_home = os.getenv("XDG_CACHE_HOME")
            base_dir = (
                Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
            )
        elif system_name == "Darwin":
            base_dir = Path.home() / "Library" / "Caches"
        elif system_name == "Windows":
            localappdata = os.getenv("LOCALAPPDATA")
            base_dir = (
                Path(localappdata)
                if localappdata
                else Path.home() / "AppData" / "Local"
            )
        else:
            base_dir = Path.home() / ".cache"

        return base_dir / PersistencePathsOperations.APP_NAME

    @staticmethod
    def get_default_config_path() -> Path:
        """Return default config file path."""
        return PersistencePathsOperations.get_config_root() / "config.yaml"

    @staticmethod
    def get_default_source_projects_root() -> Path:
        """Return default source projects root under app data root."""
        return (
            PersistencePathsOperations.get_data_root() / "source-pgdp-data" / "output"
        )

    @staticmethod
    def get_default_state_root() -> Path:
        """Return default directory for persisted state files."""
        return PersistencePathsOperations.get_data_root() / "state"

    @staticmethod
    def get_logs_root() -> Path:
        """Return default directory for application logs."""
        return PersistencePathsOperations.get_data_root() / "logs"

    @staticmethod
    def get_page_image_cache_root() -> Path:
        """Return default directory for rendered page image cache files."""
        return PersistencePathsOperations.get_cache_root() / "page-images"

    @staticmethod
    def get_saved_projects_root() -> Path:
        """Return default directory for persisted labeled projects."""
        return PersistencePathsOperations.get_data_root() / "labeled-projects"

    @staticmethod
    def get_project_backups_root() -> Path:
        """Return default directory for project backups."""
        return PersistencePathsOperations.get_data_root() / "project-backups"
