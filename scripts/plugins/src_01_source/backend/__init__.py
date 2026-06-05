"""Backend source plugins — Java, Python, Go, C++, C."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....common.base import LanguagePlugin

# Shared registry with _register_helper to avoid circular imports
from ._register_helper import _REGISTRY, register

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
    """Check if backend is imported as a subpackage."""
    import sys
    m = sys.modules.get("plugins.src_01_source.backend")
    if m is not None:
        pkg = getattr(m, "__package__", None)
        if pkg and "." in pkg:
            return True
    return False


def _load_plugins():
    """Lazily import and register all available plugins."""
    if _REGISTRY:
        return
    import importlib
    import warnings
    is_subpkg = _is_subpackage()
    _plugin_modules = ["java", "python", "go", "cpp", "c"]
    _loaded = False
    for plugin_name in _plugin_modules:
        try:
            if is_subpkg:
                importlib.import_module(f".{plugin_name}", package="plugins.src_01_source.backend")
            else:
                importlib.import_module(f"plugins.src_01_source.backend.{plugin_name}")
            _loaded = True
        except (ImportError, ModuleNotFoundError):
            try:
                importlib.import_module(f"plugins.languages.{plugin_name}")
                _loaded = True
            except (ImportError, ModuleNotFoundError):
                pass
    if not _loaded and not _REGISTRY:
        warnings.warn(f"Failed to load language plugins: registry may be empty")


class LanguageRegistry:
    """Registry for backend language plugins."""

    @classmethod
    def get(cls, lang_id: str) -> "LanguagePlugin":
        """Get an instance of the plugin for the given language ID.

        Checks both backend plugins and frontend plugins (e.g. javascript).
        """
        _load_plugins()
        if lang_id in _REGISTRY:
            return _REGISTRY[lang_id]()

        # Try frontend registry (e.g. javascript from src_01_source.frontend)
        try:
            import importlib
            import sys
            # Always use absolute path to avoid relative-import complexity
            frontend_mod = importlib.import_module("plugins.src_01_source.frontend")
            fe_registry = getattr(frontend_mod, "_REGISTRY", {})
            if lang_id in fe_registry:
                return fe_registry[lang_id]()
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass

        available = sorted(_REGISTRY.keys())
        raise ValueError(
            f"Unknown language: {lang_id!r}. "
            f"Available languages: {available}"
        )

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
        _load_plugins()
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
        _load_plugins()
        return sorted(_REGISTRY.keys())

    @classmethod
    def all_plugins(cls) -> list["LanguagePlugin"]:
        """Return instances of all registered plugins."""
        _load_plugins()
        return [cls.get(lang_id) for lang_id in sorted(_REGISTRY.keys())]


__all__ = [
    "LanguageRegistry",
    "register",
    "available_languages",
]
