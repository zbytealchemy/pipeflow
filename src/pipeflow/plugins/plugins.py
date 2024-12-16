"""Plugin system for pipeflow."""
from typing import Callable, Dict, Optional, Type, TypeVar

from pipeflow.core.pipe import BasePipe

T = TypeVar("T", bound=BasePipe)


class PluginRegistry:
    """Registry for pipeflow plugins."""

    def __init__(self) -> None:
        """Initialize plugin registry."""
        self._sources: Dict[str, Type[BasePipe]] = {}
        self._sinks: Dict[str, Type[BasePipe]] = {}

    def register_source(self, name: str) -> Callable[[Type[T]], Type[T]]:
        """Register a source pipe.

        Args:
            name: Name of the source pipe

        Returns:
            Decorator function
        """

        def decorator(cls: Type[T]) -> Type[T]:
            self._sources[name] = cls
            return cls

        return decorator

    def register_sink(self, name: str) -> Callable[[Type[T]], Type[T]]:
        """Register a sink pipe.

        Args:
            name: Name of the sink pipe

        Returns:
            Decorator function
        """

        def decorator(cls: Type[T]) -> Type[T]:
            self._sinks[name] = cls
            return cls

        return decorator

    def get_source(self, name: str) -> Optional[Type[BasePipe]]:
        """Get a source pipe by name."""
        return self._sources.get(name)

    def get_sink(self, name: str) -> Optional[Type[BasePipe]]:
        """Get a sink pipe by name."""
        return self._sinks.get(name)

    def list_sources(self) -> Dict[str, Type[BasePipe]]:
        """List all registered source pipes."""
        return self._sources.copy()

    def list_sinks(self) -> Dict[str, Type[BasePipe]]:
        """List all registered sink pipes."""
        return self._sinks.copy()


# Global registry instance
registry = PluginRegistry()

# Decorator exports
register_source = registry.register_source
register_sink = registry.register_sink
