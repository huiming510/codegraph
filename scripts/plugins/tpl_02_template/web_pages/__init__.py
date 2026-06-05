"""Web page template plugins — JSP, React, Vue, Jinja2, Go template, HTML."""

from .base import TemplatePlugin, TemplateElement, TemplateParseResult
from .registry import (
    TemplateRegistry,
    get_for_lang,
    get_for_file,
    available_templates,
    parse_file,
)

__all__ = [
    # Base classes
    "TemplatePlugin",
    "TemplateElement",
    "TemplateParseResult",
    # Registry
    "TemplateRegistry",
    # Convenience functions
    "get_for_lang",
    "get_for_file",
    "available_templates",
    "parse_file",
]
