"""Base classes and data models for template plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import GraphContext


@dataclass
class TemplateElement:
    """A parsed element from a template file.

    This is the unified representation for elements extracted from
    any template engine (JSP, Jinja2, React JSX, Vue SFC, etc.).
    """

    kind: str
    tag_name: str
    attrs: dict = field(default_factory=dict)
    line: int = 0
    target: Optional[str] = None
    file: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "kind": self.kind,
            "tag_name": self.tag_name,
            "attrs": self.attrs,
            "line": self.line,
        }
        if self.target:
            d["target"] = self.target
        if self.file:
            d["file"] = self.file
        return d


@dataclass
class TemplateParseResult:
    """Result of parsing a template file."""

    file: str
    elements: list[TemplateElement] = field(default_factory=list)
    parse_error: bool = False
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "file": self.file,
            "elements": [e.to_dict() for e in self.elements],
            "parse_error": self.parse_error,
        }
        if self.error_msg:
            d["error_msg"] = self.error_msg
        return d


@dataclass
class TemplateEdge:
    """An edge generated from template elements to code symbols."""

    kind: str
    from_qname: str
    to_qname: str
    file: str
    line: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "kind": self.kind,
            "from_qname": self.from_qname,
            "to_qname": self.to_qname,
            "file": self.file,
            "line": self.line,
        }
        d.update(self.metadata)
        return d


class TemplatePlugin(ABC):
    """Abstract base class for template engine plugins.

    Each plugin handles parsing and edge generation for a specific
    template engine (JSP, Jinja2, React JSX, Vue SFC, Go templates, etc.).

    Template plugins are language-agnostic but are typically associated
    with a specific language ecosystem. For example:
    - JSP/Thymeleaf/Freemarker → Java
    - Jinja2/Mako/Django templates → Python
    - JSX/Handlebars/EJS → JavaScript/TypeScript
    - Go html/template → Go
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier, e.g., 'jsp', 'jinja2', 'jsx', 'vue'."""

    @property
    def description(self) -> str:
        """Human-readable description."""
        return ""

    @property
    def legacy_result_key(self) -> Optional[str]:
        """Legacy key for backward-compatible results dict.

        If set, parsed results will also be stored under this key
        in the stage1b_ui results dict.
        Example: 'jsp' for JSPPlugin, 'jinja2' for Jinja2Plugin
        """
        return None

    @property
    def supported_langs(self) -> list[str]:
        """List of language IDs this plugin is typically used with.

        For example: ['java'] for JSP, ['python'] for Jinja2.
        """
        return []

    @property
    def file_patterns(self) -> list[str]:
        """Glob patterns for files this plugin handles.

        Examples:
            ["*.jsp", "*.jspf"]
            ["*.html", "*.jinja", "*.jinja2", "*.j2"]
            ["*.jsx", "*.tsx"]
            ["*.vue"]
            ["*.tmpl", "*.html"]
        """
        return []

    @property
    def priority(self) -> int:
        """Plugin priority when multiple plugins match the same file.

        Higher values are tried first. Default is 0.
        """
        return 0

    def supports_file(self, file_path: Path) -> bool:
        """Check if this plugin supports the given file."""
        for pattern in self.file_patterns:
            if file_path.match(pattern):
                return True
        return False

    @abstractmethod
    def parse(self, file_path: Path) -> TemplateParseResult:
        """Parse a template file and extract elements.

        Args:
            file_path: Path to the template file

        Returns:
            TemplateParseResult with parsed elements or error info
        """

    # ── Unified Edge Production ──────────────────────────────────────────────

    def produce_edges(
        self,
        context: "GraphContext",
        elements: list[TemplateElement],
        lang: Optional[str] = None,
    ) -> list[dict]:
        """Produce all edges from template elements using the shared graph context.

        This is the primary method for generating edges. It handles:
        - Template → code edges (e.g., template_url_for → view function)
        - Template → template edges (e.g., extends, includes)
        - Template → class edges (e.g., form binding)

        Args:
            context: Shared graph context with all pipeline data
            elements: Parsed template elements
            lang: Language ID (optional, for language-specific processing)

        Returns:
            List of edge dicts with keys: kind, from_qname, to_qname, file, line
        """
        edges = []

        # Template-specific edges
        edges.extend(self.resolve_template_edges(elements, context, lang))

        return [e.to_dict() if isinstance(e, TemplateEdge) else e for e in edges]

    def resolve_template_edges(
        self,
        elements: list[TemplateElement],
        context: "GraphContext",
        lang: Optional[str] = None,
    ) -> list[TemplateEdge]:
        """Generate edges from template elements to code symbols.

        This method resolves template references (e.g., JSP form bindings,
        Jinja2 includes, React component imports) to their corresponding
        code symbols.

        Uses GraphContext for efficient cross-file symbol lookup.

        Args:
            elements: Parsed template elements
            context: Shared graph context with all symbols
            lang: Language ID for language-specific processing

        Returns:
            List of TemplateEdge instances
        """
        return []

    # ── Legacy Method (deprecated) ──────────────────────────────────────────

    def resolve_template_edges_legacy(
        self,
        elements: list[TemplateElement],
        symbols: list[dict],
    ) -> list[dict]:
        """Legacy method for template edge resolution.

        Deprecated: Use resolve_template_edges(elements, context) instead.
        This method is kept for backward compatibility.
        """
        return []

    def get_symbol_kind_for_element(self, element: TemplateElement) -> Optional[str]:
        """Determine the symbol kind that this element represents.

        Override this in plugins where template elements map to specific
        symbol types (e.g., form → ActionForm class, component → React component).

        Args:
            element: Template element to classify

        Returns:
            Suggested symbol kind or None for file-level elements
        """
        return None
