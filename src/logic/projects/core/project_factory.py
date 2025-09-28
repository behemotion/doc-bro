"""ProjectFactory for creating type-specific project handlers."""

import logging
from typing import Any

from ...contracts.service_interfaces import ProjectHandlerContract
from ..models.project import ProjectType

logger = logging.getLogger(__name__)


class ProjectFactory:
    """
    Factory for creating type-specific project handlers.

    Provides centralized creation and management of project type handlers,
    enabling easy extension and testing of new project types.
    """

    def __init__(self):
        """Initialize ProjectFactory with handler registry."""
        self._handlers: dict[ProjectType, type[ProjectHandlerContract]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default project type handlers."""
        try:
            # Import handlers dynamically to avoid circular imports
            from ..types.crawling_project import CrawlingProject
            from ..types.data_project import DataProject
            from ..types.storage_project import StorageProject

            self._handlers[ProjectType.CRAWLING] = CrawlingProject
            self._handlers[ProjectType.DATA] = DataProject
            self._handlers[ProjectType.STORAGE] = StorageProject

            logger.debug("Registered default project handlers")

        except ImportError as e:
            logger.error(f"Failed to import project handlers: {e}")
            # Continue with empty registry - handlers can be registered manually

    def create_project_handler(self, project_type: ProjectType) -> ProjectHandlerContract:
        """
        Create appropriate handler for project type.

        Args:
            project_type: Type of project handler to create

        Returns:
            ProjectHandlerContract instance for the specified type

        Raises:
            ValueError: If project type is not supported
            RuntimeError: If handler creation fails
        """
        if project_type not in self._handlers:
            available_types = list(self._handlers.keys())
            raise ValueError(
                f"Unsupported project type '{project_type.value}'. "
                f"Available types: {[t.value for t in available_types]}"
            )

        handler_class = self._handlers[project_type]

        try:
            handler = handler_class()
            logger.debug(f"Created {project_type.value} project handler")
            return handler

        except Exception as e:
            logger.error(f"Failed to create {project_type.value} handler: {e}")
            raise RuntimeError(f"Handler creation failed for {project_type.value}: {e}")

    def register_handler(self, project_type: ProjectType, handler_class: type[ProjectHandlerContract]) -> None:
        """
        Register a custom project handler.

        Args:
            project_type: Project type to associate with handler
            handler_class: Handler class implementing ProjectHandlerContract

        Raises:
            ValueError: If handler class is invalid
        """
        # Validate handler class
        if not issubclass(handler_class, ProjectHandlerContract):
            raise ValueError("Handler class must implement ProjectHandlerContract")

        self._handlers[project_type] = handler_class
        logger.info(f"Registered custom handler for {project_type.value}")

    def unregister_handler(self, project_type: ProjectType) -> None:
        """
        Unregister a project handler.

        Args:
            project_type: Project type to unregister

        Raises:
            ValueError: If project type is not registered
        """
        if project_type not in self._handlers:
            raise ValueError(f"No handler registered for {project_type.value}")

        del self._handlers[project_type]
        logger.info(f"Unregistered handler for {project_type.value}")

    def get_supported_types(self) -> list[ProjectType]:
        """
        Get list of supported project types.

        Returns:
            List of ProjectType values that have registered handlers
        """
        return list(self._handlers.keys())

    def is_type_supported(self, project_type: ProjectType) -> bool:
        """
        Check if project type is supported.

        Args:
            project_type: Project type to check

        Returns:
            True if type is supported, False otherwise
        """
        return project_type in self._handlers

    def get_handler_class(self, project_type: ProjectType) -> type[ProjectHandlerContract]:
        """
        Get handler class for project type.

        Args:
            project_type: Project type

        Returns:
            Handler class for the project type

        Raises:
            ValueError: If project type is not supported
        """
        if project_type not in self._handlers:
            raise ValueError(f"No handler registered for {project_type.value}")

        return self._handlers[project_type]

    def get_handler_info(self, project_type: ProjectType) -> dict[str, str]:
        """
        Get information about a project handler.

        Args:
            project_type: Project type

        Returns:
            Dictionary containing handler information

        Raises:
            ValueError: If project type is not supported
        """
        if project_type not in self._handlers:
            raise ValueError(f"No handler registered for {project_type.value}")

        handler_class = self._handlers[project_type]

        return {
            'type': project_type.value,
            'class_name': handler_class.__name__,
            'module': handler_class.__module__,
            'description': getattr(handler_class, '__doc__', 'No description available').strip().split('\n')[0] if handler_class.__doc__ else 'No description available'
        }

    def get_all_handler_info(self) -> list[dict[str, str]]:
        """
        Get information about all registered handlers.

        Returns:
            List of handler information dictionaries
        """
        return [self.get_handler_info(project_type) for project_type in self._handlers.keys()]

    def validate_handler_compatibility(self, project_type: ProjectType) -> list[str]:
        """
        Validate that a handler is properly implemented and compatible.

        Args:
            project_type: Project type to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if project_type not in self._handlers:
            errors.append(f"No handler registered for {project_type.value}")
            return errors

        handler_class = self._handlers[project_type]

        # Check that class implements required interface
        if not issubclass(handler_class, ProjectHandlerContract):
            errors.append(f"Handler {handler_class.__name__} does not implement ProjectHandlerContract")

        # Check required methods
        required_methods = [
            'initialize_project',
            'cleanup_project',
            'validate_settings',
            'get_default_settings'
        ]

        for method_name in required_methods:
            if not hasattr(handler_class, method_name):
                errors.append(f"Handler {handler_class.__name__} missing required method: {method_name}")
            else:
                method = getattr(handler_class, method_name)
                if not callable(method):
                    errors.append(f"Handler {handler_class.__name__} method {method_name} is not callable")

        # Try to instantiate handler
        try:
            handler = handler_class()
            # Basic functionality test
            if hasattr(handler, 'get_default_settings'):
                try:
                    import asyncio
                    # Test if method can be called (don't check result)
                    asyncio.create_task(handler.get_default_settings())
                except Exception as e:
                    errors.append(f"Handler {handler_class.__name__} get_default_settings failed: {e}")

        except Exception as e:
            errors.append(f"Cannot instantiate handler {handler_class.__name__}: {e}")

        return errors

    def validate_all_handlers(self) -> dict[ProjectType, list[str]]:
        """
        Validate all registered handlers.

        Returns:
            Dictionary mapping project types to their validation errors
        """
        results = {}

        for project_type in self._handlers.keys():
            results[project_type] = self.validate_handler_compatibility(project_type)

        return results

    def get_factory_status(self) -> dict[str, Any]:
        """
        Get current status of the factory.

        Returns:
            Dictionary containing factory status information
        """
        validation_results = self.validate_all_handlers()

        return {
            'registered_handlers': len(self._handlers),
            'supported_types': [t.value for t in self.get_supported_types()],
            'handler_info': self.get_all_handler_info(),
            'validation_status': {
                'valid_handlers': len([errs for errs in validation_results.values() if not errs]),
                'invalid_handlers': len([errs for errs in validation_results.values() if errs]),
                'validation_errors': {
                    pt.value: errors for pt, errors in validation_results.items() if errors
                }
            }
        }

    def reset_to_defaults(self) -> None:
        """Reset factory to default handlers only."""
        self._handlers.clear()
        self._register_default_handlers()
        logger.info("Reset ProjectFactory to default handlers")

    def __str__(self) -> str:
        """String representation of ProjectFactory."""
        return f"ProjectFactory({len(self._handlers)} handlers registered)"

    def __repr__(self) -> str:
        """Detailed string representation."""
        handler_types = [t.value for t in self._handlers.keys()]
        return f"ProjectFactory(handlers={handler_types})"


# Singleton instance for global use
_factory_instance: ProjectFactory | None = None


def get_project_factory() -> ProjectFactory:
    """
    Get singleton ProjectFactory instance.

    Returns:
        Global ProjectFactory instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = ProjectFactory()

    return _factory_instance


def reset_project_factory() -> None:
    """Reset global ProjectFactory instance (mainly for testing)."""
    global _factory_instance
    _factory_instance = None


# Type imports for factory validation
from typing import Any
