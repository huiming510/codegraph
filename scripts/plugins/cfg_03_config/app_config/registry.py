"""Registry for config file plugins."""

from pathlib import Path
from typing import Optional

from .._common import ConfigPlugin


_CONFIG_REGISTRY: dict[str, type[ConfigPlugin]] = {}


def register(plugin_cls: type[ConfigPlugin]) -> None:
    """Register a config plugin class.

    Called automatically when the plugin module is imported.
    """
    _CONFIG_REGISTRY[plugin_cls.name] = plugin_cls


class ConfigRegistry:
    """Registry for config file plugins."""

    @classmethod
    def get(cls, name: str) -> Optional[ConfigPlugin]:
        """Get an instance of the plugin by name."""
        _ensure_loaded()
        if name not in _CONFIG_REGISTRY:
            return None
        return _CONFIG_REGISTRY[name]()

    @classmethod
    def get_for_lang(cls, lang: str) -> list[ConfigPlugin]:
        """Get all plugins that support the given language.

        Args:
            lang: Language ID (e.g., 'java', 'python', 'javascript', 'go')

        Returns:
            List of plugin instances supporting this language
        """
        _ensure_loaded()
        plugins = []
        for name, plugin_cls in _CONFIG_REGISTRY.items():
            instance = plugin_cls()
            if lang in instance.supported_langs or not instance.supported_langs:
                plugins.append(instance)
        return plugins

    @classmethod
    def get_for_file(cls, file_path: Path) -> list[ConfigPlugin]:
        """Get all plugins that handle the given file path.

        Args:
            file_path: Path to a config file

        Returns:
            List of plugin instances that match the file patterns
        """
        _ensure_loaded()
        from fnmatch import fnmatch

        matching_plugins = []
        for name, plugin_cls in _CONFIG_REGISTRY.items():
            instance = plugin_cls()
            patterns = instance.get_config_file_patterns()
            for pattern in patterns:
                if fnmatch(str(file_path.name), pattern) or fnmatch(str(file_path), pattern):
                    if instance not in matching_plugins:
                        matching_plugins.append(instance)
                    break
        return matching_plugins

    @classmethod
    def all_plugins(cls) -> list[ConfigPlugin]:
        """Get instances of all registered plugins."""
        _ensure_loaded()
        return [plugin_cls() for plugin_cls in _CONFIG_REGISTRY.values()]

    @classmethod
    def available_formats(cls) -> list[str]:
        """Get names of all available config plugins."""
        _ensure_loaded()
        return sorted(_CONFIG_REGISTRY.keys())

    @classmethod
    def register(cls, plugin_cls: type[ConfigPlugin]) -> None:
        """Explicitly register a plugin class."""
        register(plugin_cls)

    @classmethod
    def parse_file(cls, file_path: Path) -> Optional[dict]:
        """Parse a config file using the best matching plugin.

        Args:
            file_path: Path to the config file

        Returns:
            dict with keys: file, entries, parse_error if a plugin handles this file, None otherwise
        """
        plugins = cls.get_for_file(file_path)
        if not plugins:
            return None
        result = plugins[0].parse(file_path)
        if hasattr(result, "to_dict"):
            return result.to_dict()
        return result


# ── Auto-discovery loader ────────────────────────────────────────────────────

def _load_builtin_configs():
    """Load all built-in config plugins."""
    try:
        from . import yaml_config  # noqa: F401
        from . import properties_config  # noqa: F401
        from . import json_config  # noqa: F401
        from . import env_config  # noqa: F401
    except ImportError as e:
        import warnings
        warnings.warn(f"Failed to load some config plugins: {e}")


def _ensure_loaded():
    """Ensure all plugins are loaded (lazy loading)."""
    if not _CONFIG_REGISTRY:
        _load_builtin_configs()


def get_for_lang(lang: str) -> list[ConfigPlugin]:
    """Convenience function: get plugins for a language."""
    _ensure_loaded()
    return ConfigRegistry.get_for_lang(lang)


def available_formats() -> list[str]:
    """Convenience function: list available config plugins."""
    _ensure_loaded()
    return ConfigRegistry.available_formats()


def get_for_file(file_path: Path) -> list[ConfigPlugin]:
    """Convenience function: get plugins for a file."""
    _ensure_loaded()
    return ConfigRegistry.get_for_file(file_path)
