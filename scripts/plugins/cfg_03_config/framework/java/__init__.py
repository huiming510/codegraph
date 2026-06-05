"""Java framework config plugins — Struts, TLD, Web XML, Dicon."""

from .base import JavaConfigEntry, JavaConfigPlugin, JavaConfigResult
from .registry import (
    Registry as JavaConfigRegistry,
    register,
    available_configs as available_java_configs,
    get_for_file as get_java_config_for_file,
)

__all__ = [
    "JavaConfigPlugin",
    "JavaConfigEntry",
    "JavaConfigResult",
    "JavaConfigRegistry",
    "get_java_config_for_file",
    "available_java_configs",
    "register",
]
