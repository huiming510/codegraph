"""Registry for Java framework configuration plugins."""

from pathlib import Path
from typing import Optional

from .base import JavaConfigPlugin, JavaConfigResult
from ._register_helper import _REGISTRY, register


class Registry:
    """Registry for Java framework configuration plugins."""

    @classmethod
    def get(cls, name: str) -> Optional[JavaConfigPlugin]:
        """Get an instance of the plugin by name."""
        _ensure_loaded()
        if name not in _REGISTRY:
            return None
        return _REGISTRY[name]()

    @classmethod
    def get_for_file(cls, file_path: Path) -> Optional[JavaConfigPlugin]:
        """Get the best matching plugin for a file.

        Args:
            file_path: Path to a config file

        Returns:
            Plugin instance that handles this file, or None
        """
        _ensure_loaded()
        candidates: list[tuple[int, JavaConfigPlugin]] = []

        for plugin_cls in _REGISTRY.values():
            instance = plugin_cls()
            if instance.supports_file(file_path):
                candidates.append((instance.priority, instance))

        if not candidates:
            return None

        # Sort by priority (descending), return highest priority plugin
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    @classmethod
    def all_plugins(cls) -> list[JavaConfigPlugin]:
        """Get instances of all registered plugins."""
        _ensure_loaded()
        return [plugin_cls() for plugin_cls in _REGISTRY.values()]

    @classmethod
    def available_configs(cls) -> list[str]:
        """Get names of all available config plugins."""
        _ensure_loaded()
        return sorted(_REGISTRY.keys())

    @classmethod
    def parse_file(cls, file_path: Path) -> Optional[JavaConfigResult]:
        """Parse a file using the best matching plugin.

        Args:
            file_path: Path to the config file

        Returns:
            JavaConfigResult if a plugin handles this file, None otherwise
        """
        plugin = cls.get_for_file(file_path)
        if plugin is None:
            return None
        return plugin.parse(file_path)


# ── Auto-discovery loader ────────────────────────────────────────────────────

_BUILTIN_MODULES = [
    "tld",
    "struts",
    "web_xml",
    "dicon",
    "mybatis_xml_orm",
]


def _load_builtin_configs():
    """Load all built-in Java config plugins via importlib."""
    import importlib
    import warnings

    _pkg = "plugins.cfg_03_config.framework.java"
    for module_name in _BUILTIN_MODULES:
        try:
            importlib.import_module(f".{module_name}", package=_pkg)
        except (ImportError, ModuleNotFoundError) as ex:
            try:
                importlib.import_module(f"{_pkg}.{module_name}")
            except (ImportError, ModuleNotFoundError):
                warnings.warn(f"Failed to load Java config plugin '{module_name}': {ex}")


def _ensure_loaded():
    """Ensure all plugins are loaded (lazy loading)."""
    if not _REGISTRY:
        _load_builtin_configs()


# Convenience functions

def get_for_file(file_path: Path) -> Optional[JavaConfigPlugin]:
    """Get the best matching plugin for a file."""
    _ensure_loaded()
    return Registry.get_for_file(file_path)


def available_configs() -> list[str]:
    """List available Java config plugins."""
    _ensure_loaded()
    return Registry.available_configs()


def available_java_configs() -> list[str]:
    """Alias for available_configs() for backward compatibility."""
    return available_configs()


def parse_file(file_path: Path) -> Optional[JavaConfigResult]:
    """Parse a file using the best matching plugin."""
    _ensure_loaded()
    return Registry.parse_file(file_path)
