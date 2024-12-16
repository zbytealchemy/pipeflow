"""Plugin system for pipeflow."""
from pipeflow.plugins.plugins import register_sink, register_source, registry

__all__ = ["registry", "register_source", "register_sink"]
