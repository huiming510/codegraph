"""Python framework config plugins."""

from .base import FrameworkPlugin, PatternEdge
from .registry import (
    FrameworkRegistry,
    get_for_lang,
    available_frameworks,
)

__all__ = [
    "FrameworkPlugin",
    "PatternEdge",
    "FrameworkRegistry",
    "get_for_lang",
    "available_frameworks",
]
