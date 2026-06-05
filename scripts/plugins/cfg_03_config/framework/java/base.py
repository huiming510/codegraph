"""Base classes for Java framework configuration plugins.

This module provides the foundation for parsing Java-specific configuration files:
- TLD (Tag Library Descriptor) files
- struts-config.xml
- web.xml
- .dicon (S2Container DI configuration)

Architecture:
    JavaConfigPlugin handles parsing of framework-specific config files.
    The parsed data flows to CrossEdgePlugins for cross-domain edge generation.

Usage:
    from plugins.cfg_03_config.framework.java.base import JavaConfigPlugin

    class TldPlugin(JavaConfigPlugin):
        @property
        def name(self) -> str:
            return "tld"

        @property
        def config_type(self) -> str:
            return "tld"

        def parse(self, file_path: Path) -> JavaConfigResult:
            # ... parsing logic ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class JavaConfigEntry:
    """A parsed entry from a Java configuration file.

    This is a unified representation for entries from TLD, XML configs, and dicon files.
    """

    # Entry identification
    entry_type: str  # tld_tag | action_mapping | form_bean | global_forward | servlet_def | filter_def | dicon_component | dicon_include
    name: str  # Primary identifier (tag name, action path, component name, etc.)
    class_name: Optional[str] = None  # Handler class for tags/components
    file: str = ""
    line: int = 0

    # Type-specific attributes
    attrs: dict = field(default_factory=dict)  # All attributes as key-value pairs
    forwards: list[dict] = field(default_factory=list)  # For action mappings: list of forwards
    properties: dict = field(default_factory=dict)  # For dicon: property name-value pairs
    body_content: str = ""  # For TLD tags: body-content value

    # Metadata
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entry_type": self.entry_type,
            "name": self.name,
            "class_name": self.class_name,
            "file": self.file,
            "line": self.line,
            "attrs": self.attrs,
            "forwards": self.forwards,
            "properties": self.properties,
            "body_content": self.body_content,
            "metadata": self.metadata,
        }


@dataclass
class JavaConfigResult:
    """Result of parsing a Java configuration file.

    Contains a list of entries extracted from the file.
    """

    file: str
    config_type: str  # tld | struts_config | web_xml | dicon
    entries: list[JavaConfigEntry] = field(default_factory=list)
    parse_error: bool = False
    error_msg: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "config_type": self.config_type,
            "entries": [e.to_dict() for e in self.entries],
            "parse_error": self.parse_error,
            "error_msg": self.error_msg,
            "metadata": self.metadata,
        }


class JavaConfigPlugin(ABC):
    """Abstract base class for Java framework configuration plugins.

    Each plugin handles parsing of a specific type of Java configuration file:
    - TLD files define custom tag handlers
    - struts-config.xml defines action mappings and form beans
    - web.xml defines servlets and filters
    - .dicon files define dependency injection components

    Plugins contribute:
    - Config parsing: Convert framework-specific XML/text configs to unified format
    - Entry extraction: Extract meaningful entries (tags, actions, components)
    - Metadata enrichment: Add context-specific metadata for edge generation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier, e.g., 'tld', 'struts_config', 'web_xml', 'dicon'."""

    @property
    def description(self) -> str:
        """Human-readable description of what this plugin handles."""
        return ""

    @property
    @abstractmethod
    def config_type(self) -> str:
        """Config type identifier, e.g., 'tld', 'struts_config', 'web_xml', 'dicon'."""

    @property
    def file_patterns(self) -> list[str]:
        """Glob patterns for files this plugin handles."""
        return []

    @property
    def priority(self) -> int:
        """Plugin priority when multiple plugins match the same file."""
        return 0

    def supports_file(self, file_path: Path) -> bool:
        """Check if this plugin supports the given file."""
        for pattern in self.file_patterns:
            if file_path.match(pattern):
                return True
        return False

    @abstractmethod
    def parse(self, file_path: Path) -> JavaConfigResult:
        """Parse a configuration file and extract entries.

        Args:
            file_path: Path to the config file

        Returns:
            JavaConfigResult with parsed entries and metadata
        """

    def get_entries_by_type(
        self, results: list[JavaConfigResult], entry_type: str
    ) -> list[JavaConfigEntry]:
        """Filter entries by type across multiple result files."""
        entries = []
        for result in results:
            if result.parse_error:
                continue
            for entry in result.entries:
                if entry.entry_type == entry_type:
                    entries.append(entry)
        return entries
