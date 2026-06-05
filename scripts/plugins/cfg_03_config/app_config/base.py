"""Base classes and data models for config file plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .._common import Symbol, GraphContext


@dataclass
class ConfigEntry:
    """A parsed configuration entry from a config file.

    Represents a key-value pair, array, or nested structure in a config file.
    """

    key: str
    value: Optional[str] = None
    entry_type: str = "string"  # string | number | boolean | array | object | null
    path: str = ""  # Dot-notation path: "database.connection.host"
    line: int = 0
    file: str = ""
    raw_value: Optional[str] = None  # Original raw value before any processing
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "type": self.entry_type,
            "path": self.path,
            "line": self.line,
            "file": self.file,
            "raw_value": self.raw_value,
            "metadata": self.metadata,
        }


@dataclass
class ConfigRef:
    """A reference from a config entry to a code symbol.

    For example:
    - Spring YAML: spring.datasource.bean: "myDataSource"
      → references symbol: com.example.MyDataSource
    - Properties: server.port → references constant: 8080
    """

    config_path: str  # Dot-notation path in config file
    target: str  # What the config points to (class name, URL, path, etc.)
    target_type: str  # class | url | path | constant | env_var | service
    file: str
    line: int
    confidence: str = "medium"  # high | medium | low
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "config_path": self.config_path,
            "target": self.target,
            "target_type": self.target_type,
            "file": self.file,
            "line": self.line,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class ConfigEdge:
    """An edge representing a configuration-to-code relationship.

    This creates edges between config entries and the code they control,
    enabling queries like "show me all configs that reference this class".
    """

    kind: str  # config.ref | config.env | config.bean | config.route | config.url
    from_qname: str  # Config path (e.g., "app.database.url")
    to_qname: str  # Target (class name, URL, env var, etc.)
    file: str  # Config file path
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


@dataclass
class ConfigSchema:
    """Represents the schema/structure of a parsed config file."""

    file: str
    format: str  # yaml | properties | json | toml | env | xml | ini
    entries: list[ConfigEntry] = field(default_factory=list)
    refs: list[ConfigRef] = field(default_factory=list)
    parse_error: bool = False
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "format": self.format,
            "entries": [e.to_dict() for e in self.entries],
            "refs": [r.to_dict() for r in self.refs],
            "parse_error": self.parse_error,
            "error_msg": self.error_msg,
        }


class ConfigPlugin(ABC):
    """Abstract base class for configuration file plugins.

    Each plugin handles parsing of configuration files (YAML, JSON, properties,
    TOML, .env, XML, INI, etc.) and extracts:

    - Config entries: Key-value pairs with dot-notation paths
    - Config references: Points to classes, URLs, services, or other code elements
    - Config edges: Relationships between config and code

    Plugins contribute:
    - Schema extraction: Parse config structure into unified format
    - Reference detection: Identify config values that reference code elements
    - Type inference: Infer types for config values
    - Validation hints: Schema validation patterns (e.g., Spring Boot conventions)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier, e.g., 'yaml', 'properties', 'json', 'toml', 'env'."""

    @property
    def description(self) -> str:
        """Human-readable description of what this plugin handles."""
        return ""

    @property
    def supported_langs(self) -> list[str]:
        """List of language IDs this plugin is typically used with.

        Config plugins are usually language-agnostic, but some configs
        are specific to certain ecosystems:
        - properties: Java, Android
        - .env: Any (Node.js, Python, etc.)
        - Spring YAML: Java
        - Django settings: Python
        """
        return []

    @property
    def priority(self) -> int:
        """Plugin priority when multiple plugins match the same file.

        Higher values are tried first. Default is 0.
        """
        return 0

    @abstractmethod
    def get_config_file_patterns(self) -> list[str]:
        """Return glob patterns for config files this plugin handles.

        Examples:
            - YAML: ["*.yaml", "*.yml", "**/*.yaml", "**/*.yml"]
            - Properties: ["*.properties", "**/*.properties"]
            - TOML: ["*.toml", "**/pyproject.toml", "**/Cargo.toml"]
            - JSON: ["*.json", "**/package.json", "**/tsconfig.json"]
            - ENV: [".env", ".env.*", "**/.env*"]
            - XML: ["*.xml", "**/applicationContext.xml"]
            - INI: ["*.ini", "**/*.cfg"]
        """

    def supports_file(self, file_path: Path) -> bool:
        """Check if this plugin supports the given file."""
        for pattern in self.get_config_file_patterns():
            if file_path.match(pattern):
                return True
        return False

    @abstractmethod
    def parse_config(self, file_path: Path, content: str) -> ConfigSchema:
        """Parse a config file and extract entries and references.

        Args:
            file_path: Path to the config file
            content: Raw file content

        Returns:
            ConfigSchema with parsed entries and optional references
        """

    def detect_references(
        self,
        schema: ConfigSchema,
        symbols: list[dict],
    ) -> list[ConfigRef]:
        """Detect references from config entries to code symbols.

        This method analyzes config values and attempts to link them to:
        - Class names (e.g., @Bean method names in Spring)
        - Package paths (e.g., main class in Spring Boot)
        - Environment variable names
        - Service names
        - URLs and paths

        Args:
            schema: Parsed config schema from parse_config()
            symbols: Symbol table from stage 2/3

        Returns:
            List of ConfigRef objects detected in the config
        """
        return schema.refs

    def resolve_config_edges(
        self,
        schema: ConfigSchema,
        symbols: list[dict],
    ) -> list[ConfigEdge]:
        """Generate edges from config entries to code symbols.

        This creates graph edges that represent the relationships
        between configuration and code elements.

        Args:
            schema: Parsed config schema
            symbols: Symbol table from stage 2/3

        Returns:
            List of ConfigEdge instances
        """
        edges = []

        # Add edges for detected references
        for ref in schema.refs:
            edges.append(ConfigEdge(
                kind=f"config.{ref.target_type}",
                from_qname=ref.config_path,
                to_qname=ref.target,
                file=ref.file,
                line=ref.line,
                metadata={
                    "target_type": ref.target_type,
                    "confidence": ref.confidence,
                },
            ))

        return edges

    def resolve_symbols_to_config(
        self,
        symbols: list[dict],
        schema: ConfigSchema,
    ) -> list[ConfigEdge]:
        """Generate edges from code symbols to config entries.

        This reverse direction is useful for queries like:
        "Find all beans that are configured in YAML"

        Args:
            symbols: Symbol table from stage 2/3
            schema: Parsed config schema

        Returns:
            List of ConfigEdge instances (reversed direction)
        """
        edges = []

        for ref in schema.refs:
            # Find matching symbol
            for sym in symbols:
                if self._symbol_matches_ref(sym, ref):
                    edges.append(ConfigEdge(
                        kind=f"config.{ref.target_type}",
                        from_qname=sym.get("qualified_name", sym.get("name", "")),
                        to_qname=ref.config_path,
                        file=ref.file,
                        line=ref.line,
                        metadata={
                            "direction": "code_to_config",
                            "target_type": ref.target_type,
                        },
                    ))

        return edges

    # ── Unified Edge Production with GraphContext ──────────────────────────────────

    def produce_edges(
        self,
        context: "GraphContext",
        schema: Optional[ConfigSchema] = None,
    ) -> list[dict]:
        """Produce all edges from config using the shared graph context.

        This is the primary method for generating edges. It handles:
        - Config → code edges (e.g., spring.main-class → Java class)
        - Config → URL edges (e.g., datasource.url → JDBC URL)
        - Config → env_var edges (e.g., DATABASE_URL)
        - Code → config edges (reverse direction)

        Args:
            context: Shared graph context with all pipeline data
            schema: Parsed config schema (optional, can be parsed from context)

        Returns:
            List of edge dicts with keys: kind, from_qname, to_qname, file, line
        """
        edges = []

        # Parse config if not provided
        if schema is None:
            # Subclasses should override to provide default config parsing
            return edges

        # Config → code edges
        edges.extend(self.resolve_config_edges(schema, context.symbols))

        # Code → config edges (reverse direction)
        edges.extend(self.resolve_symbols_to_config(context.symbols, schema))

        return edges

    def _symbol_matches_ref(self, symbol: dict, ref: ConfigRef) -> bool:
        """Check if a symbol matches a config reference.

        Override this in plugins for more sophisticated matching logic.
        """
        sym_name = symbol.get("qualified_name", symbol.get("name", ""))

        # Exact match
        if ref.target == sym_name:
            return True

        # Simple class name match (last part of qualified name)
        if ref.target == symbol.get("name", ""):
            return True

        return False

    def get_config_schema_hints(self) -> dict[str, str]:
        """Return config path → expected value type hints.

        This provides schema hints that can help other plugins or
        validation tools understand the config structure.

        Examples:
            {
                "server.port": "integer",
                "spring.datasource.url": "string",
                "logging.level": "string",
            }
        """
        return {}

    def produce_nodes(self, schema: "ConfigSchema") -> list[dict]:
        """Generate additional graph nodes from this config file.

        Override this method to add format-specific nodes (e.g., env_var nodes for .env files).
        Each node should have at least: id, kind, file, domain_tags.

        Args:
            schema: Parsed config schema

        Returns:
            List of node dicts to add to the graph
        """
        return []

    # ── Lifecycle Hooks ────────────────────────────────────────────────────

    def on_config_init(self, config_file: Path) -> None:
        """Called when this plugin starts processing a config file.

        Use for one-time setup, config loading, etc.
        """
        pass

    def on_pipeline_complete(self, graph: dict) -> None:
        """Called after the full pipeline completes.

        Use for post-processing, validation, or logging.
        """
        pass
