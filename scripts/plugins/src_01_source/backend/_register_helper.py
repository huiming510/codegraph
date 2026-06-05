"""Plugin registration helper — shared between __init__.py and plugin modules.

This module defines register() and _REGISTRY in one place so that:
- __init__.py can use them directly
- plugin modules (java.py, etc.) can import them without creating a circular import

Circular import problem solved:
- __init__.py imports plugins (java.py, etc.)
- plugins need to call register() which is defined in __init__.py
- but __init__.py hasn't finished loading yet when plugins run

Solution: both __init__.py and plugins import from this shared helper.
"""

_REGISTRY: dict[str, "LanguagePlugin"] = {}


def register(plugin_cls: "LanguagePlugin") -> None:
    """Register a plugin class. Called by each plugin module on import."""
    _REGISTRY[plugin_cls.lang_id] = plugin_cls
