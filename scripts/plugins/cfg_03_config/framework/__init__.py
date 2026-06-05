"""Framework config plugins — Python framework (Flask, Django) and Java framework (Struts, etc.)."""

from .java import (
    JavaConfigPlugin,
    JavaConfigEntry,
    JavaConfigResult,
    JavaConfigRegistry,
    get_java_config_for_file,
    available_java_configs,
)

__all__ = [
    "JavaConfigPlugin",
    "JavaConfigEntry",
    "JavaConfigResult",
    "JavaConfigRegistry",
    "get_java_config_for_file",
    "available_java_configs",
]
