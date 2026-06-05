"""Shared registry for Java framework configuration plugins.

This module holds the registry dict and register function to break
circular imports between base.py and registry.py.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import JavaConfigPlugin


_REGISTRY: dict[str, type["JavaConfigPlugin"]] = {}


def register(plugin_cls: type["JavaConfigPlugin"]) -> None:
    """Register a Java config plugin class. Called automatically when the plugin module is imported."""
    instance = plugin_cls()
    _REGISTRY[instance.name] = plugin_cls
