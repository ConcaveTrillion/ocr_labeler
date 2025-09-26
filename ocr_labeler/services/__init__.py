"""Services layer for cross-cutting concerns and dependency injection."""

from .notification_service import NotificationService
from .service_locator import ServiceLocator

__all__ = [
    "NotificationService",
    "ServiceLocator",
]
