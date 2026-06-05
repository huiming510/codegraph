"""Registry for cross-file edge generation plugins."""

from typing import Optional, Type, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CrossFilePlugin


# Global registry - initialized once
_REGISTRY: dict[str, type] = {}
_REGISTER_HOOKS: list[Callable[[], None]] = []


def on_load(callback: Callable[[], None]) -> None:
    """Register a callback to be called when plugins are loaded."""
    _REGISTER_HOOKS.append(callback)


def _run_hooks():
    """Run all registered load hooks."""
    for hook in _REGISTER_HOOKS:
        try:
            hook()
        except Exception as e:
            import warnings
            warnings.warn(f"Plugin load hook failed: {e}")


def register(plugin_cls: Type["CrossFilePlugin"]) -> None:
    """Register a cross-file plugin class."""
    global _REGISTRY
    instance = plugin_cls()
    _REGISTRY[instance.name] = plugin_cls


class Registry:
    """Registry for cross-file edge generation plugins."""

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Ensure all plugins are loaded (lazy loading)."""
        if not _REGISTRY:
            _load_builtin_plugins()

    @classmethod
    def get(cls, name: str) -> Optional["CrossFilePlugin"]:
        """Get an instance of the plugin by name."""
        cls._ensure_loaded()
        if name not in _REGISTRY:
            return None
        return _REGISTRY[name]()

    @classmethod
    def get_applicable(cls, context, lang: str = None) -> list["CrossFilePlugin"]:
        """Get all plugins that can produce cross-file edges for the given context."""
        cls._ensure_loaded()
        plugins = []
        for plugin_cls in _REGISTRY.values():
            instance = plugin_cls()
            if instance.can_produce(context, lang):
                plugins.append(instance)
        return plugins

    @classmethod
    def produce_all(cls, context, lang: str = None, elements: dict = None) -> list[dict]:
        """Run all applicable cross-file plugins and collect their edges."""
        cls._ensure_loaded()
        all_edges = []
        for plugin in cls.get_applicable(context, lang):
            edges = plugin.produce(context, lang, elements)
            all_edges.extend(edges)
        return all_edges

    @classmethod
    def available_plugins(cls) -> list[str]:
        """Get names of all registered cross-file plugins."""
        cls._ensure_loaded()
        return sorted(_REGISTRY.keys())


# ── Auto-discovery loader ────────────────────────────────────────────────────

def _load_builtin_plugins():
    """Load all built-in cross-file plugins using importlib."""
    import importlib
    import warnings

    _plugins = [
        "plugins.cross_file.plugins.jsp_java",
        "plugins.cross_file.plugins.web_xml_servlet",
        "plugins.cross_file.plugins.tld_handler",
        "plugins.cross_file.plugins.dicon_component",
        "plugins.cross_file.plugins.template_code",
        "plugins.cross_file.plugins.mybatis_orm",
    ]
    for name in _plugins:
        try:
            importlib.import_module(name)
        except ImportError as e:
            warnings.warn(f"Failed to load cross-file plugin {name}: {e}")


def _ensure_loaded():
    """Ensure all plugins are loaded (lazy loading)."""
    if not _REGISTRY:
        _load_builtin_plugins()


# Convenience functions

def available_plugins() -> list[str]:
    """Get names of all registered cross-file plugins."""
    _ensure_loaded()
    return Registry.available_plugins()


def get_applicable(context, lang: str = None) -> list["CrossFilePlugin"]:
    """Get all applicable cross-file plugins."""
    _ensure_loaded()
    return Registry.get_applicable(context, lang)


def produce_all(context, lang: str = None, elements: dict = None) -> list[dict]:
    """Run all applicable cross-file plugins."""
    _ensure_loaded()
    return Registry.produce_all(context, lang, elements)
