"""Registry for build system plugins."""

from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Dependency

from .._common import BuildPlugin


_BUILD_REGISTRY: dict[str, type[BuildPlugin]] = {}


def register(plugin_cls: type[BuildPlugin]) -> None:
    """Register a build plugin class.

    Called automatically when the plugin module is imported.
    """
    _BUILD_REGISTRY[plugin_cls.name] = plugin_cls


class BuildRegistry:
    """Registry for build system plugins."""

    @classmethod
    def get(cls, name: str) -> Optional[BuildPlugin]:
        """Get an instance of the plugin by name."""
        _ensure_loaded()
        if name not in _BUILD_REGISTRY:
            return None
        return _BUILD_REGISTRY[name]()

    @classmethod
    def get_for_lang(cls, lang: str) -> list[BuildPlugin]:
        """Get all plugins that support the given language.

        Args:
            lang: Language ID (e.g., 'java', 'python', 'javascript', 'go')

        Returns:
            List of plugin instances supporting this language
        """
        _ensure_loaded()
        plugins = []
        for name, plugin_cls in _BUILD_REGISTRY.items():
            # supported_langs is a property, so we need to instantiate to check
            instance = plugin_cls()
            if lang in instance.supported_langs:
                plugins.append(instance)
        return plugins

    @classmethod
    def get_for_file(cls, file_path: Path) -> list[BuildPlugin]:
        """Get all plugins that handle the given file path.

        Args:
            file_path: Path to a build file

        Returns:
            List of plugin instances that match the file patterns
        """
        _ensure_loaded()
        from fnmatch import fnmatch

        matching_plugins = []
        for name, plugin_cls in _BUILD_REGISTRY.items():
            instance = plugin_cls()
            patterns = instance.get_build_file_patterns()
            for pattern in patterns:
                if fnmatch(str(file_path.name), pattern) or fnmatch(str(file_path), pattern):
                    matching_plugins.append(instance)
                    break
        return matching_plugins

    @classmethod
    def all_plugins(cls) -> list[BuildPlugin]:
        """Get instances of all registered plugins."""
        _ensure_loaded()
        return [plugin_cls() for plugin_cls in _BUILD_REGISTRY.values()]

    @classmethod
    def available_builders(cls) -> list[str]:
        """Get names of all available build plugins."""
        _ensure_loaded()
        return sorted(_BUILD_REGISTRY.keys())

    @classmethod
    def register(cls, plugin_cls: type[BuildPlugin]) -> None:
        """Explicitly register a plugin class."""
        register(plugin_cls)

    @classmethod
    def parse_file(cls, file_path: Path) -> Optional[list["Dependency"]]:
        """Parse a build file using the best matching plugin.

        Args:
            file_path: Path to the build file

        Returns:
            List of Dependency objects if a plugin handles this file, None otherwise
        """
        plugins = cls.get_for_file(file_path)
        if not plugins:
            return None
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            content = ""
        return plugins[0].parse_build_file(file_path, content)


# ── Auto-discovery loader ────────────────────────────────────────────────────

def _load_builtin_builders():
    """Load all built-in build plugins using importlib."""
    import importlib
    import warnings

    _plugins: list[str] = []
    for name in _plugins:
        try:
            # Try relative import first
            importlib.import_module(f".{name}", package="plugins.cfg_03_config.build")
        except (ImportError, ModuleNotFoundError):
            try:
                # Fall back to absolute import
                importlib.import_module(f"plugins.cfg_03_config.build.{name}")
            except (ImportError, ModuleNotFoundError):
                pass


def _ensure_loaded():
    """Ensure all plugins are loaded (lazy loading)."""
    if not _BUILD_REGISTRY:
        _load_builtin_builders()


def get_for_lang(lang: str) -> list[BuildPlugin]:
    """Convenience function: get plugins for a language."""
    _ensure_loaded()
    return BuildRegistry.get_for_lang(lang)


def available_builders() -> list[str]:
    """Convenience function: list available build plugins."""
    _ensure_loaded()
    return BuildRegistry.available_builders()


def get_for_file(file_path: Path) -> list[BuildPlugin]:
    """Convenience function: get plugins for a file."""
    _ensure_loaded()
    return BuildRegistry.get_for_file(file_path)
