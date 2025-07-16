"""Engine registry for backward compatibility."""

# Import from the actual registry location
from .engines.registry import EngineRegistry, registry, register_engine, get_engine, get_available_engines

__all__ = ['EngineRegistry', 'registry', 'register_engine', 'get_engine', 'get_available_engines']