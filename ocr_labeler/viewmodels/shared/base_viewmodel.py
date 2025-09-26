"""Base view model class providing common functionality for all view models."""

from abc import ABC
from dataclasses import field
from typing import Any, Callable, List

from nicegui import binding

logger = __import__("logging").getLogger(__name__)


@binding.bindable_dataclass
class BaseViewModel(ABC):
    """Base class for all view models providing common functionality.

    This class provides:
    - Property change notification system
    - Command pattern support for UI actions
    - Common initialization and cleanup patterns
    """

    _property_changed_callbacks: List[Callable[[str, Any], None]] = field(
        default_factory=list
    )

    def __post_init__(self):
        """Initialize the view model after dataclass construction."""
        pass

    def add_property_changed_listener(self, callback: Callable[[str, Any], None]):
        """Add a listener for property changes.

        Args:
            callback: Function to call when a property changes. Receives (property_name, new_value).
        """
        self._property_changed_callbacks.append(callback)

    def remove_property_changed_listener(self, callback: Callable[[str, Any], None]):
        """Remove a property change listener.

        Args:
            callback: The callback function to remove.
        """
        if callback in self._property_changed_callbacks:
            self._property_changed_callbacks.remove(callback)

    def notify_property_changed(self, property_name: str, value: Any):
        """Notify listeners of property changes.

        Args:
            property_name: Name of the property that changed.
            value: New value of the property.
        """
        for callback in self._property_changed_callbacks:
            try:
                callback(property_name, value)
            except Exception as e:
                logger.exception(
                    f"Error in property change callback for {property_name}: {e}"
                )

    def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """Execute a command by name.

        This provides a way for views to trigger view model actions through a command pattern.

        Args:
            command_name: Name of the command to execute.
            *args: Positional arguments for the command.
            **kwargs: Keyword arguments for the command.

        Returns:
            Result of the command execution.

        Raises:
            AttributeError: If the command method doesn't exist.
            Exception: If the command execution fails.
        """
        command_method = getattr(self, f"command_{command_name}", None)
        if command_method is None:
            raise AttributeError(
                f"Command '{command_name}' not found in {self.__class__.__name__}"
            )

        if not callable(command_method):
            raise AttributeError(
                f"Command '{command_name}' is not callable in {self.__class__.__name__}"
            )

        try:
            return command_method(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error executing command '{command_name}': {e}")
            raise
