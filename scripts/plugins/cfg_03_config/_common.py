"""Shared base classes for cfg_03_config subpackages (app_config, build, framework).

Provides shared dataclasses for build plugins (Dependency, BuildDependencyEdge),
abstract base classes: ConfigPlugin, BuildPlugin, and shared constants.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ConfigEntry:
    """A parsed configuration entry from a config file."""
    key: str
    value: Optional[str] = None
    entry_type: str = "string"
    path: str = ""
    line: int = 0
    file: str = ""
    raw_value: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "key": self.key, "value": self.value, "entry_type": self.entry_type,
            "path": self.path, "line": self.line, "file": self.file,
            "raw_value": self.raw_value, "metadata": self.metadata,
        }


@dataclass
class ConfigRef:
    """A reference from a config entry to a code symbol."""
    config_path: str
    target: str
    target_type: str
    file: str
    line: int
    confidence: str = "medium"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "config_path": self.config_path, "target": self.target,
            "target_type": self.target_type, "file": self.file, "line": self.line,
            "confidence": self.confidence, "metadata": self.metadata,
        }


@dataclass
class ConfigSchema:
    """Represents the schema/structure of a parsed config file."""
    file: str
    format: str
    entries: list = field(default_factory=list)
    refs: list = field(default_factory=list)
    parse_error: bool = False
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "file": self.file, "format": self.format,
            "entries": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.entries],
            "refs": [r.to_dict() if hasattr(r, "to_dict") else r for r in self.refs],
            "parse_error": self.parse_error, "error_msg": self.error_msg,
        }


@dataclass
class ConfigEdge:
    """An edge representing a configuration-to-code relationship."""
    kind: str
    from_qname: str
    to_qname: str
    file: str = ""
    line: int = 0

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "from_qname": self.from_qname,
            "to_qname": self.to_qname, "file": self.file, "line": self.line,
        }


class ConfigPlugin(ABC):
    """Abstract base class for config file plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier."""

    @property
    @abstractmethod
    def file_patterns(self) -> list[str]:
        """Glob patterns for files this plugin handles."""

    @abstractmethod
    def parse(self, file_path: Path) -> "ConfigParseResult":
        """Parse a config file and extract entries."""

    def get_config_file_patterns(self) -> list[str]:
        """Alias for file_patterns for compatibility."""
        return self.file_patterns


@dataclass
class ConfigParseResult:
    """Result of parsing a config file."""
    file: str
    entries: list = field(default_factory=list)
    parse_error: bool = False
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        entries_list = []
        for e in self.entries:
            if hasattr(e, "to_dict"):
                entries_list.append(e.to_dict())
            elif isinstance(e, dict):
                entries_list.append(e)
            else:
                entries_list.append(str(e))
        return {
            "file": self.file,
            "entries": entries_list,
            "parse_error": self.parse_error,
            "error_msg": self.error_msg,
        }


# Build base classes
DependencyScope = str  # "compile", "runtime", etc.


@dataclass
class Dependency:
    """Represents an external dependency."""
    group_id: str
    artifact_id: str
    version: Optional[str] = None
    scope: DependencyScope = "compile"
    optional: bool = False
    file: str = ""
    classifier: Optional[str] = None
    line: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class BuildDependencyEdge:
    """An edge from a build dependency to a code element."""
    kind: str
    from_qname: str
    to_qname: str
    file: str = ""
    line: int = 0
    dependency: Optional[Dependency] = None

    def to_dict(self) -> dict:
        d = {
            "kind": self.kind, "from_qname": self.from_qname,
            "to_qname": self.to_qname, "file": self.file, "line": self.line,
        }
        if self.dependency:
            d["dependency"] = {
                "group_id": self.dependency.group_id,
                "artifact_id": self.dependency.artifact_id,
                "version": self.dependency.version,
            }
        return d


class BuildPlugin(ABC):
    """Abstract base class for build system plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier."""

    @property
    def build_file_patterns(self) -> list[str]:
        """Glob patterns for build files this plugin handles.

        Falls back to get_build_file_patterns() for compatibility.
        """
        if hasattr(self, "get_build_file_patterns"):
            return self.get_build_file_patterns()
        return []

    def parse(self, file_path: Path) -> "BuildParseResult":
        """Parse a build file and extract dependencies.

        Falls back to parse_build() for compatibility.
        """
        if hasattr(self, "parse_build"):
            return self.parse_build(file_path)
        return BuildParseResult(file=str(file_path), parse_error=True, error_msg="No parse method available")


@dataclass
class BuildParseResult:
    """Result of parsing a build file."""
    file: str
    dependencies: list[Dependency] = field(default_factory=list)
    parse_error: bool = False
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "dependencies": [
                {"group_id": d.group_id, "artifact_id": d.artifact_id, "version": d.version}
                for d in self.dependencies
            ],
            "parse_error": self.parse_error,
            "error_msg": self.error_msg,
        }
