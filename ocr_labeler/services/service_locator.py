"""Service locator for dependency injection."""

import logging
from typing import Any, Dict, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLocator:
    """Service locator for dependency injection.

    This class provides a centralized registry for services that can be
    injected into other components. It follows the service locator pattern
    to decouple service creation from service usage.
    """

    _services: Dict[Type[Any], Any] = {}
    _service_factories: Dict[Type[Any], callable] = {}

    @classmethod
    def register(cls, service_type: Type[T], service_instance: T):
        """Register a service instance.

        Args:
            service_type: The type/class of the service.
            service_instance: The service instance to register.
        """
        cls._services[service_type] = service_instance
        logger.debug(f"Registered service instance: {service_type.__name__}")

    @classmethod
    def register_factory(cls, service_type: Type[T], factory: callable):
        """Register a service factory function.

        Args:
            service_type: The type/class of the service.
            factory: A callable that creates the service instance.
        """
        cls._service_factories[service_type] = factory
        logger.debug(f"Registered service factory: {service_type.__name__}")

    @classmethod
    def get(cls, service_type: Type[T]) -> T:
        """Get a service instance.

        Args:
            service_type: The type/class of the service to retrieve.

        Returns:
            The service instance.

        Raises:
            KeyError: If the service is not registered.
        """
        # First check if we have a direct instance
        if service_type in cls._services:
            return cls._services[service_type]

        # Then check if we have a factory
        if service_type in cls._service_factories:
            instance = cls._service_factories[service_type]()
            # Cache the created instance
            cls._services[service_type] = instance
            return instance

        raise KeyError(f"Service not registered: {service_type.__name__}")

    @classmethod
    def has_service(cls, service_type: Type[T]) -> bool:
        """Check if a service is registered.

        Args:
            service_type: The type/class of the service to check.

        Returns:
            True if the service is registered, False otherwise.
        """
        return service_type in cls._services or service_type in cls._service_factories

    @classmethod
    def unregister(cls, service_type: Type[T]):
        """Unregister a service.

        Args:
            service_type: The type/class of the service to unregister.
        """
        if service_type in cls._services:
            del cls._services[service_type]
            logger.debug(f"Unregistered service instance: {service_type.__name__}")

        if service_type in cls._service_factories:
            del cls._service_factories[service_type]
            logger.debug(f"Unregistered service factory: {service_type.__name__}")

    @classmethod
    def clear(cls):
        """Clear all registered services and factories."""
        cls._services.clear()
        cls._service_factories.clear()
        logger.debug("Cleared all services")

    @classmethod
    def list_services(cls) -> Dict[str, str]:
        """List all registered services.

        Returns:
            Dictionary mapping service type names to their registration type.
        """
        services = {}
        for service_type in cls._services:
            services[service_type.__name__] = "instance"
        for service_type in cls._service_factories:
            if service_type not in services:  # Don't overwrite if both exist
                services[service_type.__name__] = "factory"
        return services
