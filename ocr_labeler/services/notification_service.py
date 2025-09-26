"""Notification service for centralized user feedback."""

import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Centralized notification service for user feedback.

    This service provides a consistent interface for showing notifications
    to users, abstracting away the specific UI framework implementation.
    """

    def __init__(self, ui_framework=None):
        """Initialize the notification service.

        Args:
            ui_framework: Optional UI framework module (e.g., nicegui.ui).
                          If not provided, will import nicegui.ui when needed.
        """
        self._ui_framework = ui_framework
        self._notifications_enabled = True

    @property
    def ui(self):
        """Get the UI framework module, importing if necessary."""
        if self._ui_framework is None:
            try:
                from nicegui import ui

                self._ui_framework = ui
            except ImportError as e:
                logger.warning(f"Could not import nicegui.ui: {e}")
                # Create a mock UI for testing or when UI is not available
                self._ui_framework = self._create_mock_ui()
        return self._ui_framework

    def _create_mock_ui(self):
        """Create a mock UI object for testing or when UI is not available."""

        class MockUI:
            def notify(self, message, type="info", **kwargs):
                logger.info(f"Mock notification [{type}]: {message}")

        return MockUI()

    def success(self, message: str, **kwargs):
        """Show success notification.

        Args:
            message: The message to display.
            **kwargs: Additional arguments passed to the UI notification.
        """
        if self._notifications_enabled:
            self.ui.notify(message, type="positive", **kwargs)
            logger.debug(f"Success notification: {message}")

    def error(self, message: str, **kwargs):
        """Show error notification.

        Args:
            message: The message to display.
            **kwargs: Additional arguments passed to the UI notification.
        """
        if self._notifications_enabled:
            self.ui.notify(message, type="negative", **kwargs)
            logger.error(f"Error notification: {message}")

    def warning(self, message: str, **kwargs):
        """Show warning notification.

        Args:
            message: The message to display.
            **kwargs: Additional arguments passed to the UI notification.
        """
        if self._notifications_enabled:
            self.ui.notify(message, type="warning", **kwargs)
            logger.warning(f"Warning notification: {message}")

    def info(self, message: str, **kwargs):
        """Show info notification.

        Args:
            message: The message to display.
            **kwargs: Additional arguments passed to the UI notification.
        """
        if self._notifications_enabled:
            self.ui.notify(message, **kwargs)
            logger.info(f"Info notification: {message}")

    def disable_notifications(self):
        """Disable all notifications."""
        self._notifications_enabled = False
        logger.debug("Notifications disabled")

    def enable_notifications(self):
        """Enable all notifications."""
        self._notifications_enabled = True
        logger.debug("Notifications enabled")

    def is_enabled(self) -> bool:
        """Check if notifications are enabled.

        Returns:
            True if notifications are enabled, False otherwise.
        """
        return self._notifications_enabled
