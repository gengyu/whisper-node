"""Engine registry for managing speech recognition engines."""

import logging
from typing import Dict, List, Optional, Type
from .base import BaseEngine

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Registry for managing speech recognition engines."""
    
    def __init__(self):
        self._engines: Dict[str, Type[BaseEngine]] = {}
        self._instances: Dict[str, BaseEngine] = {}
    
    def register(self, name: str, engine_class: Type[BaseEngine]) -> None:
        """Register an engine class.
        
        Args:
            name: Engine name
            engine_class: Engine class
        """
        if not issubclass(engine_class, BaseEngine):
            raise ValueError(f"Engine class must inherit from BaseEngine")
        
        self._engines[name] = engine_class
        logger.info(f"Registered engine: {name}")
    
    def get_engine(self, name: str, config: Optional[Dict] = None) -> Optional[BaseEngine]:
        """Get an engine instance.
        
        Args:
            name: Engine name
            config: Engine configuration
            
        Returns:
            Engine instance or None if not found
        """
        if name not in self._engines:
            logger.warning(f"Engine not found: {name}")
            return None
        
        # Return cached instance if available and no new config
        if name in self._instances and config is None:
            return self._instances[name]
        
        # Create new instance
        try:
            engine_class = self._engines[name]
            instance = engine_class(config or {})
            self._instances[name] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to create engine {name}: {e}")
            return None
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engine names.
        
        Returns:
            List of engine names that are ready to use
        """
        available = []
        for name in self._engines:
            engine = self.get_engine(name)
            if engine and engine.is_available():
                available.append(name)
        return available
    
    def get_all_engines(self) -> List[str]:
        """Get list of all registered engine names.
        
        Returns:
            List of all registered engine names
        """
        return list(self._engines.keys())
    
    def is_engine_available(self, name: str) -> bool:
        """Check if an engine is available.
        
        Args:
            name: Engine name
            
        Returns:
            True if engine is available, False otherwise
        """
        engine = self.get_engine(name)
        return engine is not None and engine.is_available()
    
    def get_engine_info(self, name: str) -> Optional[Dict]:
        """Get engine information.
        
        Args:
            name: Engine name
            
        Returns:
            Engine information dict or None if not found
        """
        engine = self.get_engine(name)
        return engine.get_info() if engine else None
    
    def get_all_engines_info(self) -> Dict[str, Dict]:
        """Get information for all engines.

        Returns:
            Dict mapping engine names to their info
        """
        info = {}
        for name in self._engines:
            engine_info = self.get_engine_info(name)
            if engine_info:
                info[name] = engine_info
        return info
    
    def list_engines(self) -> List[str]:
        """List all registered engines.
        
        Returns:
            List of all registered engine names
        """
        return self.get_all_engines()


# Global registry instance
registry = EngineRegistry()


def register_engine(name: str, engine_class: Type[BaseEngine]) -> None:
    """Register an engine in the global registry.
    
    Args:
        name: Engine name
        engine_class: Engine class
    """
    registry.register(name, engine_class)


def get_engine(name: str, config: Optional[Dict] = None) -> Optional[BaseEngine]:
    """Get an engine from the global registry.
    
    Args:
        name: Engine name
        config: Engine configuration
        
    Returns:
        Engine instance or None if not found
    """
    return registry.get_engine(name, config)


def get_available_engines() -> List[str]:
    """Get list of available engines from the global registry.
    
    Returns:
        List of available engine names
    """
    return registry.get_available_engines()