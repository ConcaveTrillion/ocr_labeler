"""Base view model class providing common functionality for all view models."""

import logging
from abc import ABC
from dataclasses import field
from typing import Any, Callable

from nicegui import binding

logger = logging.getLogger(__name__)

_BENIGN_CALLBACK_ERROR_FRAGMENTS = (
    "the client this element belongs to has been deleted",
    "cannot enqueue javascript commands",
)


@binding.bindable_dataclass
class BaseViewModel(ABC):
    """Base class for all view models providing common functionality.

    This class provides:
    - Property change notification system
    - Command pattern support for UI actions
    - Common initialization and cleanup patterns
    """

    _property_changed_callbacks: list[Callable[[str, Any], None]] = field(
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
                message = str(e).lower()
                if any(
                    fragment in message for fragment in _BENIGN_CALLBACK_ERROR_FRAGMENTS
                ):
                    logger.debug(
                        "Ignoring benign property change callback error for %s: %s",
                        property_name,
                        e,
                    )
                    continue
                logger.exception(
                    f"Error in property change callback for {property_name}: {e}"
                )
