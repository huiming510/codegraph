"""Registry for template engine plugins."""

from pathlib import Path
from typing import Optional, Type

from .base import TemplatePlugin, TemplateParseResult


# Registry: name -> plugin class
_TEMPLATE_REGISTRY: dict[str, type[TemplatePlugin]] = {}

# Global priority map: pattern -> plugin_name (for priority-based resolution)
_PATTERN_PRIORITY: dict[str, int] = {}


def _get_plugin_attrs(plugin_cls: Type[TemplatePlugin]) -> dict:
    """Get plugin attributes, instantiating if necessary for @property access."""
    try:
        instance = plugin_cls()
        return {
            "name": instance.name,
            "patterns": instance.file_patterns,
            "priority": instance.priority,
            "supported_langs": instance.supported_langs,
        }
    except Exception as e:
        raise ValueError(f"Failed to instantiate plugin {plugin_cls.__name__}: {e}")


def register(plugin_cls: type[TemplatePlugin]) -> None:
    """Register a template plugin class.

    Called automatically when the plugin module is imported.
    """
    attrs = _get_plugin_attrs(plugin_cls)
    plugin_name = attrs["name"]
    patterns = attrs["patterns"]
    priority = attrs["priority"]

    _TEMPLATE_REGISTRY[plugin_name] = plugin_cls

    # Build pattern priority map
    for pattern in patterns:
        current_priority = _PATTERN_PRIORITY.get(pattern, 0)
        if priority > current_priority:
            _PATTERN_PRIORITY[pattern] = priority


class TemplateRegistry:
    """Registry for template engine plugins."""

    @classmethod
    def get(cls, name: str) -> Optional[TemplatePlugin]:
        """Get an instance of the plugin by name."""
        _ensure_loaded()
        if name not in _TEMPLATE_REGISTRY:
            return None
        return _TEMPLATE_REGISTRY[name]()

    @classmethod
    def get_for_lang(cls, lang: str) -> list[TemplatePlugin]:
        """Get all plugins that support the given language."""
        _ensure_loaded()
        plugins = []
        for plugin_cls in _TEMPLATE_REGISTRY.values():
            attrs = _get_plugin_attrs(plugin_cls)
            if lang in attrs["supported_langs"]:
                plugins.append(plugin_cls())
        return plugins

    @classmethod
    def get_for_file(cls, file_path: Path) -> Optional[TemplatePlugin]:
        """Get the best matching plugin for a file based on patterns and priority."""
        _ensure_loaded()
        candidates: list[tuple[int, TemplatePlugin]] = []

        for plugin_cls in _TEMPLATE_REGISTRY.values():
            instance = plugin_cls()
            if instance.supports_file(file_path):
                candidates.append((instance.priority, instance))

        if not candidates:
            return None

        # Sort by priority (descending), return highest priority plugin
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    @classmethod
    def get_all_matching(cls, file_path: Path) -> list[TemplatePlugin]:
        """Get all plugins that match the given file."""
        _ensure_loaded()
        plugins = []
        for plugin_cls in _TEMPLATE_REGISTRY.values():
            instance = plugin_cls()
            if instance.supports_file(file_path):
                plugins.append(instance)
        return plugins

    @classmethod
    def all_plugins(cls) -> list[TemplatePlugin]:
        """Get instances of all registered plugins."""
        _ensure_loaded()
        return [plugin_cls() for plugin_cls in _TEMPLATE_REGISTRY.values()]

    @classmethod
    def available_templates(cls) -> list[str]:
        """Get names of all available template plugins."""
        _ensure_loaded()
        return sorted(_TEMPLATE_REGISTRY.keys())

    @classmethod
    def register(cls, plugin_cls: type[TemplatePlugin]) -> None:
        """Explicitly register a plugin class."""
        register(plugin_cls)

    @classmethod
    def parse_file(cls, file_path: Path) -> Optional[TemplateParseResult]:
        """Parse a file using matching plugins.

        Tries plugins in priority order (highest first).
        Returns None if no suitable plugin is found or if all plugins
        return None (e.g., file doesn't contain template syntax).
        """
        # First check if any plugin claims this file by pattern
        plugin = cls.get_for_file(file_path)
        if plugin is None:
            return None

        # Try the best matching plugin first
        result = plugin.parse(file_path)
        if result is not None:
            return result

        # If the plugin returned None (e.g., no Jinja2 syntax in .html file),
        # try other matching plugins as fallback
        for other_plugin in cls.get_all_matching(file_path):
            if other_plugin.name == plugin.name:
                continue  # already tried
            result = other_plugin.parse(file_path)
            if result is not None:
                return result

        return None


# ── Auto-discovery loader ────────────────────────────────────────────────────

def _load_builtin_templates():
    """Load all built-in template plugins."""
    try:
        from . import jsp  # noqa: F401
        from . import jinja2  # noqa: F401
        from . import react  # noqa: F401
        from . import vue  # noqa: F401
        from . import go_template  # noqa: F401
        from . import html_template_checker  # noqa: F401
    except ImportError as e:
        import warnings
        warnings.warn(f"Failed to load some template plugins: {e}")


def _ensure_loaded():
    """Ensure all plugins are loaded (lazy loading)."""
    if not _TEMPLATE_REGISTRY:
        _load_builtin_templates()


# Convenience functions

def get_for_lang(lang: str) -> list[TemplatePlugin]:
    """Get template plugins for a language."""
    _ensure_loaded()
    return TemplateRegistry.get_for_lang(lang)


def get_for_file(file_path: Path) -> Optional[TemplatePlugin]:
    """Get the best matching plugin for a file."""
    _ensure_loaded()
    return TemplateRegistry.get_for_file(file_path)


def available_templates() -> list[str]:
    """List available template plugins."""
    _ensure_loaded()
    return TemplateRegistry.available_templates()


def parse_file(file_path: Path) -> Optional[TemplateParseResult]:
    """Parse a file using the best matching plugin."""
    _ensure_loaded()
    return TemplateRegistry.parse_file(file_path)
