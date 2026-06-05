"""Registry for framework/project pattern plugins."""

from typing import Optional

from .base import FrameworkPlugin


# Registry: name -> plugin class
_FRAMEWORK_REGISTRY: dict[str, type[FrameworkPlugin]] = {}


def register(plugin_cls: type[FrameworkPlugin]) -> None:
    """Register a framework plugin class.

    Called automatically when the plugin module is imported.
    """
    _FRAMEWORK_REGISTRY[plugin_cls.name] = plugin_cls


class FrameworkRegistry:
    """Registry for framework plugins."""

    @classmethod
    def get(cls, name: str) -> Optional[FrameworkPlugin]:
        """Get an instance of the plugin by name."""
        _ensure_loaded()
        if name not in _FRAMEWORK_REGISTRY:
            return None
        return _FRAMEWORK_REGISTRY[name]()

    @classmethod
    def get_for_lang(cls, lang: str) -> list[FrameworkPlugin]:
        """Get all plugins that support the given language.

        Args:
            lang: Language ID (e.g., 'java', 'python')

        Returns:
            List of plugin instances supporting this language
        """
        _ensure_loaded()
        plugins = []
        for name, plugin_cls in _FRAMEWORK_REGISTRY.items():
            if lang in plugin_cls.supported_langs:
                plugins.append(plugin_cls())
        return plugins

    @classmethod
    def all_plugins(cls) -> list[FrameworkPlugin]:
        """Get instances of all registered plugins."""
        _ensure_loaded()
        return [plugin_cls() for plugin_cls in _FRAMEWORK_REGISTRY.values()]

    @classmethod
    def available_frameworks(cls) -> list[str]:
        """Get names of all available framework plugins."""
        _ensure_loaded()
        return sorted(_FRAMEWORK_REGISTRY.keys())

    @classmethod
    def register(cls, plugin_cls: type[FrameworkPlugin]) -> None:
        """Explicitly register a plugin class."""
        register(plugin_cls)


# ── Auto-discovery loader ────────────────────────────────────────────────────

def _load_builtin_frameworks():
    """Load all built-in Python framework plugins."""
    pass


def _ensure_loaded():
    """Ensure all plugins are loaded (lazy loading)."""
    if not _FRAMEWORK_REGISTRY:
        _load_builtin_frameworks()


def get_for_lang(lang: str) -> list[FrameworkPlugin]:
    """Convenience function: get plugins for a language."""
    _ensure_loaded()
    return FrameworkRegistry.get_for_lang(lang)


def available_frameworks() -> list[str]:
    """Convenience function: list available frameworks."""
    _ensure_loaded()
    return FrameworkRegistry.available_frameworks()
