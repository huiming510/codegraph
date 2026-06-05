"""Core data models and base classes shared across all plugin types.

This module contains:
- Symbol: unified symbol model
- Edge: directed edge between qualified names
- GraphContext: shared context for cross-domain operations
- PluginContributionLimits: per-plugin edge contribution caps
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class PluginContributionLimits:
    """Per-plugin contribution caps to prevent noise explosions.

    These limits are enforced at the plugin call site (stage4_refs.py) so
    plugins cannot unilaterally bloat the graph with low-quality edges.
    """
    max_edges: int = 200           # per plugin call / per file
    max_edges_global: int = 2000   # total across all calls
    require_cluster_link: bool = True  # drop edges with no cluster connectivity


@dataclass
class Symbol:
    """Unified symbol model used by all language plugins."""

    name: str
    kind: str  # class | interface | struct | enum | function | method | field | property | parameter | variable | module | import
    qualified_name: str
    file: str
    start: tuple[int, int]  # (line, col), 1-indexed
    end: tuple[int, int]
    scope: str  # qualified name of enclosing scope (e.g. "pkg.Class")
    type_hint: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)  # public, static, async, etc.
    annotations: list[str] = field(default_factory=list)  # @Decorator, //go:build, etc.
    docstring: Optional[str] = None
    lang: str = "java"  # language identifier

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "qualified_name": self.qualified_name,
            "file": self.file,
            "start": list(self.start),
            "end": list(self.end),
            "scope": self.scope,
            "type_hint": self.type_hint,
            "modifiers": self.modifiers,
            "annotations": self.annotations,
            "docstring": self.docstring,
            "lang": self.lang,
        }


@dataclass
class Edge:
    """Directed edge between two qualified names."""

    kind: str  # call | contains | extends | implements | reads | writes | instantiates | typed_as | defined_in | imports | defined_in | template_include | template_url_for
    from_qname: str
    to_qname: str
    file: str
    line: int
    receiver: Optional[str] = None  # for external/ambiguous method calls: the object on which the method is called
    receiver_type: Optional[str] = None  # the declared/resolved type of the receiver object

    def to_dict(self) -> dict:
        d = {
            "kind": self.kind,
            "from_qname": self.from_qname,
            "to_qname": self.to_qname,
            "file": self.file,
            "line": self.line,
        }
        if self.receiver:
            d["receiver"] = self.receiver
        if self.receiver_type is not None:
            d["receiver_type"] = self.receiver_type
        return d


# ── GraphContext: Shared context for all plugins ────────────────────────────────


@dataclass
class GraphContext:
    """Context containing all data available for cross-domain edge generation.

    This is the "shared context" that all plugins can access to produce
    cross-domain edges. It is passed to plugin methods that need to
    resolve references across multiple files or domains.
    """

    # Raw data from pipeline stages
    symbols: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    ui_data: dict = field(default_factory=dict)
    ast_data: list[dict] = field(default_factory=list)
    config_data: list[dict] = field(default_factory=list)

    # Computed indexes for efficient lookup
    _symbol_by_qname: dict = field(default_factory=dict, repr=False)
    _symbols_by_kind: dict = field(default_factory=dict, repr=False)
    _symbols_by_name: dict = field(default_factory=dict, repr=False)
    _nodes_by_file: dict = field(default_factory=dict, repr=False)
    _edges_by_kind: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Build indexes for efficient lookup."""
        # Index symbols by qualified name
        for s in self.symbols:
            qname = s.get("qualified_name", "")
            if qname:
                self._symbol_by_qname[qname] = s

        # Index symbols by kind
        for s in self.symbols:
            kind = s.get("kind", "unknown")
            self._symbols_by_kind.setdefault(kind, []).append(s)

        # Index symbols by simple name
        for s in self.symbols:
            name = s.get("name", "")
            if name:
                self._symbols_by_name.setdefault(name, []).append(s)

        # Index nodes by file
        for s in self.symbols:
            f = s.get("file", "")
            if f:
                self._nodes_by_file.setdefault(f, []).append(s)

        # Index edges by kind
        for e in self.edges:
            kind = e.get("kind", "unknown")
            self._edges_by_kind.setdefault(kind, []).append(e)

    def get_symbol(self, qname: str) -> Optional[dict]:
        """Get symbol by qualified name."""
        return self._symbol_by_qname.get(qname)

    def get_symbols_by_kind(self, kind: str) -> list[dict]:
        """Get all symbols of a specific kind."""
        return self._symbols_by_kind.get(kind, [])

    def get_symbols_by_name(self, name: str) -> list[dict]:
        """Get all symbols with a specific simple name."""
        return self._symbols_by_name.get(name, [])

    def get_symbols_in_file(self, file: str) -> list[dict]:
        """Get all symbols defined in a file."""
        return self._nodes_by_file.get(file, [])

    def get_edges_by_kind(self, kind: str) -> list[dict]:
        """Get all edges of a specific kind."""
        return self._edges_by_kind.get(kind, [])


class LanguagePlugin(ABC):
    """Abstract base class for language plugins.

    Each plugin handles parsing, symbol extraction, and reference resolution
    for a specific programming language (or language family).
    """

    lang_id: str  # "java" | "python" | "javascript" | "go"
    display_name: str  # "Java" | "Python" | "JavaScript/TypeScript" | "Go"

    def get_contribution_limits(self) -> "PluginContributionLimits":
        """Return contribution limits for this plugin's edge output.

        These limits prevent a single plugin from bloating the graph with
        low-quality edges. The actual enforcement happens in stage4_refs.py
        via the _filter_edges_by_quality gate.

        Override in subclasses to adjust limits for specific plugins.
        """
        return PluginContributionLimits(
            max_edges=200,
            require_cluster_link=True,
        )

    @abstractmethod
    def get_file_patterns(self) -> list[str]:
        """Return glob patterns for source files this plugin handles.

        Example: ['*.java'] or ['*.py', '*.pyi']
        """

    @abstractmethod
    def get_tree_sitter_package(self) -> str:
        """Return the tree-sitter package name.

        Example: 'tree_sitter_java' or 'tree_sitter_python'
        """

    @abstractmethod
    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        """Traverse AST and extract symbol table.

        Args:
            ast_entry: A dict with keys 'file', 'ast', 'parse_error'
            src_root: The root source directory path, used by some languages
                      (Python, JS, Go) to infer module/package paths.

        Returns:
            List of Symbol objects found in this file.
        """

    @abstractmethod
    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        """Extract method/function call edges from AST.

        This handles language-specific call syntax (method_invocation,
        call_expression, etc.). Contains/extends/implements edges are
        handled generically in stage4_refs.py.
        """

    @abstractmethod
    def get_framework_annotations(self) -> dict[str, str]:
        """Return framework annotation → domain tag mappings.

        Example:
            {"@Execute": "struts.action", "@app.route": "web.route"}
        """

    @abstractmethod
    def infer_constructors(self) -> dict[str, str]:
        """Return a mapping of class qualified names to constructor names.

        Used by stage3_types.py to infer return types of constructor-like methods.
        Example:
            {"pkg.MyClass": "MyClass"}  # constructor MyClass() returns pkg.MyClass
        """

    def get_entry_point_names(self) -> list[str]:
        """Return names that indicate entry points in this language.

        Used by semantic enrichment to identify entry point functions.
        Override to provide language-specific entry point names.
        """
        return ["main"]

    def build_inner_class_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate inner_class edges for nested class relationships.

        For each inner class (modifier includes "inner"), creates an edge:
            outer_class → inner_class (kind="inner_class")

        By default returns an empty list. Override in language plugins
        that support nested class declarations (Java, Python, JavaScript, Go).
        """
        return []

    def build_import_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate module-level import edges.

        Creates 'imports' edges from the importing file/module to the
        imported module/class. This is the primary mechanism for connecting
        files across modules into a coherent graph.

        By default returns an empty list. Override in language plugins
        that support module import systems (Python, JS, Go).
        """
        return []

    def build_extends_implements_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate extends/implements edges for class declarations.

        Creates 'extends' / 'implements' / 'java_extends' / 'java_implements' edges
        from a class/interface to its parent types. This feeds the Intra-Type
        classification in Stage 6 for languages with explicit inheritance syntax.

        By default returns an empty list. Override in language plugins
        that support class inheritance declarations (Java, TypeScript, C++, Python).
        """
        return []

    def get_control_flow_hints(self, sym: dict) -> Optional[str]:
        """Determine control flow summary for a symbol.

        Args:
            sym: Symbol dict with 'name', 'kind', 'annotations', etc.

        Returns:
            Control flow type string or None (e.g., "entry_point", "web_action")
        """
        return None
