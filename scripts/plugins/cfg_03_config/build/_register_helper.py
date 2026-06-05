"""Plugin registration helper — shared between __init__.py and plugin modules."""

_REGISTRY: dict[str, "BuildPlugin"] = {}


def register(plugin_cls: "BuildPlugin") -> None:
    """Register a build plugin class."""
    _REGISTRY[plugin_cls.name] = plugin_cls
