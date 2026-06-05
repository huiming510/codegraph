"""Base classes for build system plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .._common import Symbol


DependencyScope = Literal["compile", "runtime", "test", "provided", "system"]


@dataclass
class Dependency:
    """Represents an external dependency from a build file."""

    group_id: str  # Maven: groupId, Gradle: group, npm: scope
    artifact_id: str  # Maven: artifactId, Gradle: name, npm: package name
    version: Optional[str] = None
    scope: DependencyScope = "compile"
    optional: bool = False
    exclusions: list["Dependency"] = field(default_factory=list)
    file: str = ""
    classifier: Optional[str] = None
    line: int = 0
    metadata: dict = field(default_factory=dict)  # Plugin-specific extra data

    @property
    def maven_coord(self) -> str:
        """Return Maven-style coordinate: groupId:artifactId[:classifier]:version"""
        coord = f"{self.group_id}:{self.artifact_id}"
        if self.classifier:
            coord += f":{self.classifier}"
        if self.version:
            coord += f":{self.version}"
        return coord

    @property
    def npm_coord(self) -> str:
        """Return npm-style coordinate: @scope/package@version"""
        if self.group_id:
            return f"@{self.group_id}/{self.artifact_id}@{self.version or 'latest'}"
        return f"{self.artifact_id}@{self.version or 'latest'}"

    @property
    def pip_coord(self) -> str:
        """Return pip-style coordinate: package==version"""
        if self.version:
            return f"{self.artifact_id}=={self.version}"
        return self.artifact_id

    @property
    def go_mod_coord(self) -> str:
        """Return Go module coordinate: module/path@version"""
        return f"{self.group_id}/{self.artifact_id}@{self.version or 'latest'}"

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "scope": self.scope,
            "optional": self.optional,
            "classifier": self.classifier,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class BuildDependencyEdge:
    """An edge representing a build dependency relationship.

    This creates edges between local modules/packages and external dependencies,
    which can be used to track which parts of the codebase depend on which libraries.
    """

    kind: str  # maven.dep | gradle.dep | npm.dep | pip.dep | go.dep
    from_qname: str  # Local module/package that depends on the dependency
    to_coord: str  # Dependency coordinate (maven/ npm/ pip style)
    file: str  # Build file path
    line: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "kind": self.kind,
            "from_qname": self.from_qname,
            "to_coord": self.to_coord,
            "file": self.file,
            "line": self.line,
        }
        d.update(self.metadata)
        return d


@dataclass
class TransitiveDependency:
    """Represents a transitive dependency discovered through resolution."""

    dependency: Dependency
    via: list[Dependency] = field(default_factory=list)  # Path through which this was discovered
    depth: int = 0


class BuildPlugin(ABC):
    """Abstract base class for build system plugins.

    Each plugin handles parsing of build configuration files (pom.xml, build.gradle,
    package.json, requirements.txt, go.mod) and extracts dependency information.

    Plugins contribute:
    - Dependency parsing: Extract external dependencies from build files
    - Local module edges: Link local packages to their declared dependencies
    - Scope inference: Infer which parts of code use which dependency scopes
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier, e.g., 'maven', 'gradle', 'npm', 'pip', 'go'."""

    @property
    def description(self) -> str:
        """Human-readable description of what this plugin handles."""
        return ""

    @property
    @abstractmethod
    def supported_langs(self) -> list[str]:
        """List of language IDs this plugin supports.

        Examples:
            - maven/gradle: ["java", "kotlin"]
            - npm: ["javascript", "typescript"]
            - pip: ["python"]
            - go: ["go"]
        """

    @abstractmethod
    def get_build_file_patterns(self) -> list[str]:
        """Return glob patterns for build files this plugin handles.

        Examples:
            - Maven: ["pom.xml", "**/pom.xml"]
            - Gradle: ["build.gradle", "build.gradle.kts", "**/build.gradle", "**/build.gradle.kts"]
            - npm: ["package.json", "**/package.json"]
            - pip: ["requirements.txt", "**/requirements*.txt", "pyproject.toml"]
            - Go: ["go.mod", "**/go.mod"]
        """

    @abstractmethod
    def parse_build_file(self, file_path: Path, content: str) -> list[Dependency]:
        """Parse a build file and extract dependencies.

        Args:
            file_path: Path to the build file
            content: Raw file content

        Returns:
            List of Dependency objects found in this file
        """

    def resolve_dependency_edges(
        self,
        dependencies: list[Dependency],
        symbols: list[dict],
        build_file: str,
    ) -> list[BuildDependencyEdge]:
        """Generate edges from dependencies to local modules.

        By default, creates edges from the root module to all dependencies.
        Subclasses can override to create more granular edges based on
        import statements, annotations, or other signals.

        Args:
            dependencies: List of dependencies from this build file
            symbols: Symbol table for resolving local module references
            build_file: Path to the build file

        Returns:
            List of BuildDependencyEdge instances
        """
        return []

    def get_root_module(self, build_file: Path, content: str) -> Optional[str]:
        """Extract the root module/package name from the build file.

        Args:
            build_file: Path to the build file
            content: Raw file content

        Returns:
            Root module name (e.g., groupId:artifactId for Maven, package name for npm)
        """
        return None

    def get_local_modules(self, build_file: Path, content: str) -> list[str]:
        """Extract local module names from multi-module build files.

        Args:
            build_file: Path to the build file
            content: Raw file content

        Returns:
            List of local module names (for multi-project builds)
        """
        return []

    # ── Lifecycle Hooks ────────────────────────────────────────────────────

    def on_build_init(self, build_file: Path) -> None:
        """Called when this plugin starts processing a build file.

        Use for one-time setup, config loading, etc.
        """
        pass

    def on_pipeline_complete(self, graph: dict) -> None:
        """Called after the full pipeline completes.

        Use for post-processing, validation, or logging.
        """
        pass
