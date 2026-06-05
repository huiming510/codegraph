"""
Schema definitions for rule files.
=================================
Defines Pydantic models for validating YAML rule files and rule bundles.

Usage:
    from scripts.plugins.rules_engine.schema import validate_rule, validate_bundle, Rule, RuleBundle
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RuleVersion(str):
    """Rule format version identifier."""

    V1 = "1"

    @classmethod
    def values(cls) -> list[str]:
        return [getattr(cls, a) for a in dir(cls) if not a.startswith("_") and not callable(getattr(cls, a))]


class ConditionType(str):
    """Condition type: determines how to query the match target."""

    AST_QUERY = "ast_query"
    XPATH = "xpath"
    REGEX = "regex"
    ANNOTATION = "annotation"
    NAMING = "naming"
    RELATION = "relation"

    @classmethod
    def values(cls) -> list[str]:
        return [getattr(cls, a) for a in dir(cls) if not a.startswith("_") and not callable(getattr(cls, a))]


class BindingSource(str):
    """Binding value source type."""

    ATTR = "attr"
    TEXT = "text"
    NODE = "node"

    @classmethod
    def values(cls) -> list[str]:
        return [getattr(cls, a) for a in dir(cls) if not a.startswith("_") and not callable(getattr(cls, a))]


# ---------------------------------------------------------------------------
# Field Models
# ---------------------------------------------------------------------------


class MatchTarget(BaseModel):
    """
    Match target: describes file / symbol filter conditions.

    Fields:
        language      - Target programming language (e.g. "java", "xml")
        file_pattern  - Glob pattern for file names (e.g. "**/*.jsp")
        annotation    - Annotation name with @ (e.g. "@Mapper")
        class_annotation - Class-level annotation (e.g. "@Entity")
        method_pattern - Method name regex (e.g. "findBy|get|load")
        return_type   - Return type pattern (e.g. "List<*>")
        kind          - Symbol kind ("class", "method", "field")
        paired_with   - Cross-file constraint for the counterpart target
    """

    language: Optional[str] = None
    file_pattern: Optional[str] = None
    annotation: Optional[str] = None
    class_annotation: Optional[str] = None
    method_pattern: Optional[str] = None
    return_type: Optional[str] = None
    kind: Optional[str] = None
    paired_with: Optional[MatchTarget] = None


class BindingSpec(BaseModel):
    """
    Binding specification: extracts a named capture from AST query results.

    Fields:
        name      - Capture name (binding variable name)
        source    - Source type ("attr" | "text" | "node")
        transform - Optional transform ("camel_to_snake", "snake_to_camel", "trim")
    """

    name: str
    source: str = "attr"
    transform: Optional[str] = None

    @field_validator("source")
    def _validate_source(cls, v: str) -> str:
        allowed = BindingSource.values()
        if v not in allowed:
            raise ValueError(f"Invalid binding source '{v}', must be one of: {allowed}")
        return v

    @field_validator("transform")
    def _validate_transform(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"camel_to_snake", "snake_to_camel", "trim"}
        if v not in allowed:
            raise ValueError(f"Invalid transform '{v}', must be one of: {allowed}")
        return v


class Condition(BaseModel):
    """
    Single match condition: describes what query to run against a match target.

    Fields:
        type            - ConditionType enum value
        query           - Tree-sitter query or XPath expression
        annotation      - Annotation name to match (for ANNOTATION type)
        pattern         - Regex pattern (for REGEX / NAMING types)
        relates_to      - Rule ID reference (for RELATION type)
        bindings        - Binding name -> path spec mapping
        combinator      - Logical combinator ("and" | "or" | "not")
        sub_conditions  - Nested conditions for combinator logic
    """

    type: str
    query: Optional[str] = None
    annotation: Optional[str] = None
    pattern: Optional[str] = None
    relates_to: Optional[str] = None
    bindings: dict[str, str] = Field(default_factory=dict)
    combinator: Optional[str] = None
    sub_conditions: list["Condition"] = Field(default_factory=list)
    target: Optional[str] = None  # "source" or "target", which file to query

    @field_validator("type")
    def _validate_type(cls, v: str) -> str:
        allowed = ConditionType.values()
        if v not in allowed:
            raise ValueError(f"Invalid condition type '{v}', must be one of: {allowed}")
        return v

    @field_validator("combinator")
    def _validate_combinator(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("and", "or", "not"):
            raise ValueError(f"Invalid combinator '{v}', must be 'and', 'or', or 'not'")
        return v

    @model_validator(mode="after")
    def _validate_condition_fields(self) -> "Condition":
        """Ensure required fields are present for each condition type."""
        if self.type == ConditionType.RELATION and not self.relates_to:
            raise ValueError(f"Condition type '{self.type}' requires 'relates_to' field")
        return self


class EmitEdge(BaseModel):
    """
    Edge emission spec: describes what kind of edge to generate from match results.

    Fields:
        name        - Edge identifier (used for logging / debug)
        from_ref    - Edge source reference (supports {binding} template)
        to_ref      - Edge target reference (supports {binding} template)
        kind        - Edge type (e.g. "sql_mapping", "jsp_java_render")
        properties  - Edge attribute dictionary (supports {binding} template)
        line_ref    - Binding name whose value provides the line number
    """

    name: str
    from_ref: str
    to_ref: str
    kind: str
    properties: dict[str, str] = Field(default_factory=dict)
    line_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level Models
# ---------------------------------------------------------------------------


class Rule(BaseModel):
    """
    Complete model for a single rule YAML file.

    Top-level fields:
        id          - Unique rule identifier (snake_case), e.g. "mybatis-orm"
        name        - Multi-language display name: {zh: ..., en: ...}
        description  - Rule description text
        rule_version - Semantic version of the rule itself (default "1.0.0")
        author      - Rule author name
        tags        - Classification tags for search / filtering
        match       - Source and target MatchTarget definitions
        conditions  - List of conditions to evaluate
        edges       - List of EmitEdge specs
        priority    - Execution priority, lower = earlier (default 100)
        enabled     - Whether this rule is active (default True)
        depends_on  - IDs of rules this rule depends on
    """

    # Format version (always "1" for v1 schema)
    version: str = "1"

    # Metadata
    id: str = Field(description="Unique rule identifier (snake_case)")
    name: dict[str, str] = Field(default_factory=dict, description="Multi-language name: {zh: ..., en: ...}")
    description: Optional[str] = None
    rule_version: str = "1.0.0"  # semantic version, separate from format version
    author: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    # Match scope
    match: dict[str, MatchTarget] = Field(
        description="Defines source and target match targets"
    )

    # Conditions
    conditions: list[Condition] = Field(default_factory=list)

    # Edge emission
    edges: list[EmitEdge] = Field(default_factory=list)

    # Execution control
    priority: int = Field(default=100, description="Lower number = higher priority")
    enabled: bool = Field(default=True)
    depends_on: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }

    @field_validator("id")
    def _validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][-a-z0-9_]*$", v):
            raise ValueError(
                f"Rule id '{v}' must be lowercase alphanumeric with hyphens/underscores, "
                "starting with a letter or digit"
            )
        return v

    @model_validator(mode="after")
    def _validate_match_keys(self) -> "Rule":
        """Ensure match contains 'source' and 'target' keys."""
        if "source" not in self.match:
            raise ValueError("Rule.match must contain 'source' key")
        if "target" not in self.match:
            raise ValueError("Rule.match must contain 'target' key")
        return self

    @model_validator(mode="after")
    def _validate_version_field(self) -> "Rule":
        """Ensure format version is '1'."""
        if self.version != "1":
            raise ValueError(f"Rule format version must be '1', got '{self.version}'")
        return self

    def get_source_language(self) -> Optional[str]:
        return self.match.get("source", MatchTarget()).language

    def get_target_language(self) -> Optional[str]:
        return self.match.get("target", MatchTarget()).language

    def get_binding_names(self) -> set[str]:
        """Return all binding variable names defined in all conditions."""
        names: set[str] = set()
        for cond in self.conditions:
            names.update(cond.bindings.keys())
        return names


class TargetEntry(BaseModel):
    """A single rule entry in a rule bundle's metadata."""

    file: str
    id: Optional[str] = None


class RuleBundle(BaseModel):
    """
    Rule bundle metadata model.

    A bundle is a directory containing:
        metadata.yaml - This file
        rules/        - Directory with .yaml rule files

    Fields:
        id            - Bundle identifier
        name          - Multi-language bundle name
        version       - Bundle semantic version
        description   - Bundle description
        author        - Bundle author
        license       - License identifier (default "MIT")
        homepage      - Bundle homepage URL
        dependencies  - Other bundles this bundle depends on
        targets       - Supported languages and frameworks
        rules         - List of rule entries in this bundle
    """

    id: str
    name: dict[str, str]
    version: str
    description: Optional[str | dict] = None
    author: Optional[str] = None
    license: str = "MIT"
    homepage: Optional[str] = None
    dependencies: list[dict] = Field(default_factory=list)
    targets: dict[str, list[str]] = Field(
        default_factory=lambda: {"languages": [], "frameworks": []}
    )
    rules: list[dict] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @field_validator("id")
    def _validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][-a-z0-9_]*$", v):
            raise ValueError(
                f"Bundle id '{v}' must be lowercase alphanumeric with hyphens/underscores"
            )
        return v


# ---------------------------------------------------------------------------
# Validation Functions
# ---------------------------------------------------------------------------


def validate_rule(yaml_content: str | dict | Path) -> tuple[Optional[Rule], list[str]]:
    """
    Validate a rule YAML file.

    Args:
        yaml_content: YAML string, dict, or Path to a .yaml file.

    Returns:
        (Rule object, error list). Empty error list means validation passed.

    Example:
        content = '''
            id: mybatis-orm
            version: "1"
            match:
                source: {language: java, annotation: "@Mapper"}
                target: {language: java, class_annotation: "@Entity"}
        '''
        rule, errors = validate_rule(content)
        if errors:
            for e in errors:
                print(e)
    """
    errors: list[str] = []

    try:
        if isinstance(yaml_content, (str, Path)):
            if isinstance(yaml_content, Path):
                yaml_content = Path(yaml_content).read_text(encoding="utf-8")
            data: dict[str, Any] = yaml.safe_load(yaml_content) or {}
        else:
            data = yaml_content

        if data is None:
            return None, ["  YAML content is empty"]

        rule = Rule.model_validate(data)
        return rule, []

    except ValidationError as e:
        for err in e.errors():
            field_path = ".".join(str(l) for l in err["loc"])
            ctx = err.get("ctx", {})
            msg = err["msg"]
            inp = err.get("input", "")
            if ctx:
                msg = msg.format(**ctx)
            errors.append(f"  [{field_path}] {msg}: {inp!r}")
        return None, errors

    except yaml.YAMLError as e:
        return None, [f"  YAML parse error: {e}"]

    except Exception as e:
        return None, [f"  Unexpected error: {e}"]


def validate_bundle(bundle_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate a rule bundle's completeness and all its rule files.

    Checks:
        - metadata.yaml exists and is valid
        - rules/ directory exists
        - Each rule file listed in metadata exists and passes Schema validation

    Args:
        bundle_dir: Path to the bundle directory (containing metadata.yaml).

    Returns:
        (True, []) if all checks pass.
        (False, [error, ...]) with detailed error messages on failure.
    """
    errors: list[str] = []

    metadata_file = bundle_dir / "metadata.yaml"
    if not metadata_file.exists():
        return False, [f"  metadata.yaml not found in {bundle_dir}"]

    try:
        metadata_data = yaml.safe_load(metadata_file.read_text(encoding="utf-8")) or {}
        bundle = RuleBundle.model_validate(metadata_data)
    except ValidationError as e:
        for err in e.errors():
            field_path = ".".join(str(l) for l in err["loc"])
            errors.append(f"  [metadata.{field_path}] {err['msg']}: {err.get('input', '')!r}")
        return False, errors
    except yaml.YAMLError as e:
        return False, [f"  metadata.yaml YAML parse error: {e}"]
    except Exception as e:
        return False, [f"  metadata.yaml unexpected error: {e}"]

    rules_dir = bundle_dir / "rules"
    if not rules_dir.exists():
        return False, [f"  rules/ directory not found in {bundle_dir}"]

    if not bundle.rules:
        errors.append(f"  Bundle '{bundle.id}' has no rules defined in metadata")

    for rule_entry in bundle.rules:
        rule_file_name = rule_entry.get("file")
        if not rule_file_name:
            errors.append(f"  Rule entry missing 'file' field: {rule_entry}")
            continue

        rule_file = rules_dir / rule_file_name
        if not rule_file.exists():
            errors.append(f"  Rule file not found: {rule_file}")
            continue

        _, rule_errors = validate_rule(rule_file)
        if rule_errors:
            errors.extend(rule_errors)

    return len(errors) == 0, errors
