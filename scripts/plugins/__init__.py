"""Language plugin registry and discovery.

Usage:
    from plugins import LanguageRegistry, get_plugin

    plugin = LanguageRegistry.get("python")
    plugin = LanguageRegistry.get_by_file(Path("foo/bar.py"))
    plugin = LanguageRegistry.get_by_glob_patterns(src_root)
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .common.base import LanguagePlugin


# Lazily populated registry: lang_id -> plugin class
_REGISTRY: dict[str, type["LanguagePlugin"]] = {}

# Language ID -> file extension -> language mapping
_EXT_MAP: dict[str, str] = {
    ".java": "java",
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
}


def _is_subpackage() -> bool:
    """Check if plugins is imported as a subpackage (has parent)."""
    import sys
    m = sys.modules.get("plugins")
    if m is not None:
        pkg = getattr(m, "__package__", None)
        if pkg and "." in pkg:
            return True
    return False


def _lazy_load():
    """Lazily import all subpackages."""
    import sys
    import importlib
    import warnings

    if _REGISTRY:
        return

    is_subpkg = _is_subpackage()
    _imported = set()

    if is_subpkg:
        _subpkgs = ["src_01_source", "tpl_02_template", "cfg_03_config", "cross_file", "common"]
        for name in _subpkgs:
            try:
                importlib.import_module(f".{name}", package="plugins")
                _imported.add(name)
            except ImportError:
                pass
    else:
        _subpkgs = ["src_01_source", "tpl_02_template", "cfg_03_config", "cross_file", "common"]
        for name in _subpkgs:
            try:
                importlib.import_module(f"plugins.{name}")
                _imported.add(name)
            except ImportError:
                pass

    _plugin_names = ["java", "python", "go", "cpp", "c"]
    _frontend_plugins = ["javascript"]

    for plugin_name in _plugin_names:
        for attempt in range(2):
            try:
                if is_subpkg:
                    importlib.import_module(f".src_01_source.backend.{plugin_name}", package="plugins")
                else:
                    importlib.import_module(f"plugins.src_01_source.backend.{plugin_name}")
            except (ImportError, ModuleNotFoundError):
                if attempt == 0:
                    try:
                        if is_subpkg:
                            importlib.import_module(f".languages.{plugin_name}", package="plugins")
                        else:
                            importlib.import_module(f"plugins.languages.{plugin_name}")
                    except (ImportError, ModuleNotFoundError):
                        pass
                else:
                    pass
            break

    for plugin_name in _frontend_plugins:
        for attempt in range(2):
            try:
                if is_subpkg:
                    importlib.import_module(f".src_01_source.frontend.{plugin_name}", package="plugins")
                else:
                    importlib.import_module(f"plugins.src_01_source.frontend.{plugin_name}")
            except (ImportError, ModuleNotFoundError):
                if attempt == 0:
                    try:
                        if is_subpkg:
                            importlib.import_module(f".languages.{plugin_name}", package="plugins")
                        else:
                            importlib.import_module(f"plugins.languages.{plugin_name}")
                    except (ImportError, ModuleNotFoundError):
                        pass
                else:
                    pass
            break

    # Note: _lazy_load uses absolute imports which may fail when plugins is a top-level
    # package. Plugins are actually loaded via subpackage registries. Don't warn here.


def register(plugin_cls: type["LanguagePlugin"]) -> None:
    """Register a plugin class. Called by each plugin module on import."""
    _REGISTRY[plugin_cls.lang_id] = plugin_cls


class LanguageRegistry:
    """Registry for language plugins — delegates to subpackage registries."""

    @classmethod
    def _get_subregistry(cls):
        """Get the actual registry from subpackages, merged from both backend and frontend."""
        import importlib
        merged: dict = {}
        for subpkg in ("plugins.src_01_source.backend", "plugins.src_01_source.frontend"):
            try:
                mod = importlib.import_module(subpkg)
                merged.update(mod._REGISTRY)
            except (ImportError, ModuleNotFoundError, AttributeError):
                pass
        return merged if merged else _REGISTRY

    @classmethod
    def get(cls, lang_id: str) -> "LanguagePlugin":
        """Get an instance of the plugin for the given language ID."""
        _lazy_load()
        reg = cls._get_subregistry()
        if lang_id not in reg:
            available = sorted(reg.keys())
            raise ValueError(
                f"Unknown language: {lang_id!r}. "
                f"Available languages: {available}"
            )
        return reg[lang_id]()

    @classmethod
    def get_by_file(cls, path: Path) -> "LanguagePlugin":
        """Detect language from a file path and return the matching plugin."""
        ext = path.suffix.lower()
        lang_id = _EXT_MAP.get(ext)
        if lang_id is None:
            raise ValueError(f"Unknown file extension: {ext!r}")
        return cls.get(lang_id)

    @classmethod
    def get_by_glob_patterns(cls, src_root: Path) -> list["LanguagePlugin"]:
        """Scan src_root for files and return plugins for languages that have matching files."""
        _lazy_load()
        found_langs: set[str] = set()
        seen_exts: set[str] = set()
        for f in src_root.rglob("*"):
            if f.is_file() and f.suffix.lower() in _EXT_MAP:
                ext = f.suffix.lower()
                if ext not in seen_exts:
                    seen_exts.add(ext)
                    lang_id = _EXT_MAP[ext]
                    if lang_id not in found_langs:
                        found_langs.add(lang_id)
        plugins = []
        for lang_id in sorted(found_langs):
            try:
                plugins.append(cls.get(lang_id))
            except Exception:
                pass
        return plugins

    @classmethod
    def available_languages(cls) -> list[str]:
        """Return list of available language IDs."""
        _lazy_load()
        return sorted(cls._get_subregistry().keys())

    @classmethod
    def all_plugins(cls) -> list["LanguagePlugin"]:
        """Return instances of all registered plugins."""
        _lazy_load()
        return [cls.get(lang_id) for lang_id in sorted(cls._get_subregistry().keys())]


# ── Re-export BuildRegistry for convenience ─────────────────────────────────────

def get_build_registry():
    """Get the build plugin registry."""
    import importlib
    try:
        # Try new location first (role-architecture path)
        mod = importlib.import_module("plugins.cfg_03_config.build")
        return mod.BuildRegistry
    except ImportError:
        from .build import BuildRegistry
        return BuildRegistry


# ── Re-export ConfigRegistry for convenience ─────────────────────────────────────

def get_config_registry():
    """Get the config plugin registry."""
    import importlib
    try:
        # Try new location first (role-architecture path)
        mod = importlib.import_module("plugins.cfg_03_config.app_config")
        return mod.ConfigRegistry
    except ImportError:
        from .config import ConfigRegistry
        return ConfigRegistry


# ── Re-export CrossFileRegistry for convenience ─────────────────────────────────────

def get_cross_file_registry():
    """Get the cross-file edge plugin registry."""
    try:
        from .cross_file import CrossFileRegistry
        return CrossFileRegistry
    except ImportError:
        return None

