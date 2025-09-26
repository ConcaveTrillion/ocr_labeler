"""State persistence operations for serializing and deserializing application state."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StatePersistenceOperations:
    """Operations for persisting and restoring application state.

    Handles serialization/deserialization of state objects to/from JSON files,
    with validation and migration support.
    """

    @staticmethod
    def save_state_to_file(state: Any, file_path: Path, indent: int = 2) -> bool:
        """Save state object to a JSON file.

        Args:
            state: State object to serialize (must be JSON serializable)
            file_path: Path to save the state file
            indent: JSON indentation level

        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize state to JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=indent, ensure_ascii=False)

            logger.debug("State saved to %s", file_path)
            return True

        except Exception as e:
            logger.exception("Failed to save state to %s: %s", file_path, e)
            return False

    @staticmethod
    def load_state_from_file(file_path: Path, default_state: Any = None) -> Any:
        """Load state object from a JSON file.

        Args:
            file_path: Path to the state file
            default_state: Default state to return if file doesn't exist or is invalid

        Returns:
            Loaded state object, or default_state if loading fails
        """
        if not file_path.exists():
            logger.debug("State file %s does not exist, returning default", file_path)
            return default_state

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            logger.debug("State loaded from %s", file_path)
            return state

        except Exception as e:
            logger.exception("Failed to load state from %s: %s", file_path, e)
            return default_state

    @staticmethod
    def validate_state_structure(state: Any, required_keys: list[str]) -> bool:
        """Validate that state has required structure.

        Args:
            state: State object to validate
            required_keys: List of required top-level keys

        Returns:
            True if state is valid, False otherwise
        """
        if not isinstance(state, dict):
            logger.error("State must be a dictionary")
            return False

        missing_keys = [key for key in required_keys if key not in state]
        if missing_keys:
            logger.error("State missing required keys: %s", missing_keys)
            return False

        return True

    @staticmethod
    def migrate_state(state: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        """Migrate state to a target version.

        Args:
            state: Current state dictionary
            target_version: Target version string

        Returns:
            Migrated state dictionary
        """
        # For now, just add version if missing
        if "version" not in state:
            state["version"] = target_version
            logger.info("Added version %s to state", target_version)

        # Future migrations can be added here based on version
        current_version = state.get("version", "unknown")
        if current_version != target_version:
            logger.warning(
                "State version %s does not match target %s, migration may be needed",
                current_version,
                target_version,
            )

        return state

    @staticmethod
    def get_state_file_path(base_dir: Path, state_name: str) -> Path:
        """Get the standard file path for a state file.

        Args:
            base_dir: Base directory for state files
            state_name: Name of the state (e.g., "app_state", "project_state")

        Returns:
            Path to the state file
        """
        return base_dir / f"{state_name}.json"

    @staticmethod
    def backup_state_file(file_path: Path) -> Optional[Path]:
        """Create a backup of a state file.

        Args:
            file_path: Path to the state file to backup

        Returns:
            Path to the backup file, or None if backup failed
        """
        if not file_path.exists():
            return None

        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        try:
            import shutil

            shutil.copy2(file_path, backup_path)
            logger.debug("State backup created: %s", backup_path)
            return backup_path
        except Exception as e:
            logger.exception("Failed to create state backup: %s", e)
            return None
