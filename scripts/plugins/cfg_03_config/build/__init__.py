"""Build system plugins."""

from .._common import BuildPlugin, Dependency, BuildDependencyEdge
from .registry import BuildRegistry

__all__ = [
    "BuildPlugin",
    "Dependency",
    "BuildDependencyEdge",
    "BuildRegistry",
]
