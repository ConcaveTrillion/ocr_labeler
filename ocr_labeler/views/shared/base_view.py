"""Base view class providing common functionality for all views."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ...viewmodels.shared.base_viewmodel import BaseViewModel

logger = __import__("logging").getLogger(__name__)

TViewModel = TypeVar("TViewModel", bound=BaseViewModel)


class BaseView(ABC, Generic[TViewModel]):
    """Base class for all views providing common functionality.

    This class provides:
    - View model integration
    - Abstract methods for building and refreshing UI
    - Common patterns for UI component management
    - Property change listener management
    """

    def __init__(self, viewmodel: TViewModel):
        """Initialize the view with its view model.

        Args:
            viewmodel: The view model this view will bind to.
        """
        self.viewmodel: TViewModel = viewmodel
        self._root: Any = None
        self._is_built = False

        # Set up property change listening
        self.viewmodel.add_property_changed_listener(
            self._on_viewmodel_property_changed
        )

    @abstractmethod
    def build(self) -> Any:
        """Build and return the root UI component.

        This method should create all UI components and set up initial bindings.
        It should be called once during the view's lifecycle.

        Returns:
            The root UI component of this view.
        """
        pass

    @abstractmethod
    def refresh(self):
        """Refresh the view based on current view model state.

        This method should update the UI to reflect current view model state.
        It may be called multiple times during the view's lifecycle.
        """
        pass

    def _on_viewmodel_property_changed(self, property_name: str, value: Any):
        """Handle view model property changes.

        This method is called whenever a property in the view model changes.
        Subclasses should override this to handle specific property changes.

        Args:
            property_name: Name of the property that changed.
            value: New value of the property.
        """
        logger.debug(f"View model property changed: {property_name} = {value}")
        # Default implementation does nothing - subclasses should override
        pass

    def dispose(self):
        """Clean up the view and remove listeners.

        This method should be called when the view is no longer needed
        to prevent memory leaks and remove event listeners.
        """
        if hasattr(self.viewmodel, "remove_property_changed_listener"):
            self.viewmodel.remove_property_changed_listener(
                self._on_viewmodel_property_changed
            )
        self._is_built = False
        logger.debug(f"View {self.__class__.__name__} disposed")

    @property
    def is_built(self) -> bool:
        """Check if the view has been built.

        Returns:
            True if build() has been called, False otherwise.
        """
        return self._is_built

    def mark_as_built(self):
        """Mark the view as built.

        This should be called at the end of the build() method.
        """
        self._is_built = True
