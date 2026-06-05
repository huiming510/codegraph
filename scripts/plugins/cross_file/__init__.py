"""Cross-file edge plugins — generates edges across file boundaries.

Each plugin in cross_file/plugins/ identifies one specific type of cross-file relationship
(e.g., JSP → Java, template → code, config → component).
"""

from .base import CrossFileEdge, CrossFilePlugin
from .constants import (
    CrossFileEdgeCategory,
    CROSS_FILE_EDGE_TYPES,
    EXTERNAL_PACKAGES,
    FRAMEWORK_PACKAGES,
    is_external_package,
)
from .registry import (
    Registry,
    available_plugins,
    get_applicable,
    on_load,
    produce_all,
    register,
)
from ..common.base import GraphContext


__all__ = [
    # Base classes
    "CrossFileEdge",
    "CrossFilePlugin",
    # GraphContext from common.base
    "GraphContext",
    # Constants
    "CrossFileEdgeCategory",
    "CROSS_FILE_EDGE_TYPES",
    "EXTERNAL_PACKAGES",
    "FRAMEWORK_PACKAGES",
    "is_external_package",
    # Registry
    "Registry",
    "register",
    "available_plugins",
    "get_applicable",
    "produce_all",
    "on_load",
]

# Alias for backward compatibility
CrossFileRegistry = Registry
