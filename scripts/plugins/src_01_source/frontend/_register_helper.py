"""Plugin registration helper — shared between __init__.py and plugin modules."""

_REGISTRY: dict[str, "LanguagePlugin"] = {}


def register(plugin_cls: "LanguagePlugin") -> None:
    """Register a plugin class."""
    _REGISTRY[plugin_cls.lang_id] = plugin_cls
