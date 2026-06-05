"""
Rule AST (Abstract Syntax Tree) for v1 rule format.
===================================================
Provides the runtime AST structure and the RuleASTBuilder that converts
a Pydantic Rule model into an executable AST.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from ..schema import Rule, MatchTarget, Condition, EmitEdge


# ---------------------------------------------------------------------------
# AST Node Classes
# ---------------------------------------------------------------------------


@dataclass
class BindingPathSpec:
    """
    Describes how to extract a binding value from a matched node.

    The spec string supports these formats:
        "text"           - Node's full text content
        "attr=X"         - XML/HTML attribute value
        "key=X"          - Annotation key=value pair value
        "parent.X"       - Parent node's attribute X
        "parent.parent.X" - Multi-level parent traversal
    """

    spec: str

    @property
    def path_type(self) -> str:
        if self.spec == "text":
            return "text"
        if self.spec.startswith("attr="):
            return "attr"
        if self.spec.startswith("key="):
            return "key"
        if self.spec.startswith("parent."):
            return "parent"
        return "literal"

    @property
    def path_value(self) -> str:
        if self.path_type == "text":
            return ""
        if self.path_type in ("attr", "key"):
            return self.spec.split("=", 1)[1]
        if self.path_type == "parent":
            return self.spec[len("parent."):]
        return self.spec

    @property
    def parent_depth(self) -> int:
        """Return how many 'parent.' segments are in the path."""
        if not self.spec.startswith("parent."):
            return 0
        return self.spec.count("parent.") + (1 if self.spec.endswith(".parent") else 0)

    @classmethod
    def parse(cls, spec: str) -> "BindingPathSpec":
        return cls(spec=spec)


@dataclass
class ConditionAST:
    """
    Runtime AST node for a single Condition.

    Fields:
        type           - ConditionType string
        query          - Compiled or raw query string
        annotation     - Annotation name
        pattern        - Compiled regex pattern
        relates_to     - Rule ID reference for RELATION type
        bindings       - Binding name -> BindingPathSpec mapping
        target         - "source" or "target" (which file to query)
        combinator     - Logical combinator ("and", "or", "not")
        sub_asts       - Child ConditionAST nodes for combinator groups
    """

    type: str
    query: Optional[str] = None
    annotation: Optional[str] = None
    pattern: Optional[re.Pattern] = None
    relates_to: Optional[str] = None
    bindings: dict[str, BindingPathSpec] = field(default_factory=dict)
    target: str = "source"
    combinator: Optional[str] = None
    sub_asts: list["ConditionAST"] = field(default_factory=list)


@dataclass
class EmitEdgeAST:
    """
    Runtime AST node for an EmitEdge spec.

    Fields:
        name         - Edge name
        from_ref     - Source reference template
        to_ref       - Target reference template
        kind         - Edge kind
        properties   - Rendered property templates
        line_ref     - Binding name for line number
    """

    name: str
    from_ref: str
    to_ref: str
    kind: str
    properties: dict[str, str] = field(default_factory=dict)
    line_ref: Optional[str] = None


@dataclass
class MatchTargetAST:
    """
    Runtime AST node for a MatchTarget.

    Fields:
        language        - Target language
        file_pattern    - Glob pattern
        annotation      - Annotation name (with @)
        class_annotation - Class-level annotation (with @)
        method_pattern  - Compiled regex for method names
        return_type     - Return type pattern
        kind            - Symbol kind
        paired_with     - Cross-file constraint AST
    """

    language: Optional[str] = None
    file_pattern: Optional[str] = None
    annotation: Optional[str] = None
    class_annotation: Optional[str] = None
    method_pattern: Optional[re.Pattern] = None
    return_type: Optional[str] = None
    kind: Optional[str] = None
    paired_with: Optional["MatchTargetAST"] = None


@dataclass
class RuleAST:
    """
    Complete runtime AST for a rule.

    Fields:
        rule_id           - Rule identifier
        source            - Source MatchTargetAST
        target            - Target MatchTargetAST
        conditions        - List of ConditionAST nodes
        edges             - List of EmitEdgeAST nodes
        priority          - Execution priority
        enabled           - Whether the rule is active
        depends_on        - Rule IDs this rule depends on
        binding_names     - All binding variable names
        from_ref_bindings - Binding names referenced in from_ref templates
        to_ref_bindings   - Binding names referenced in to_ref templates
    """

    rule_id: str
    source: MatchTargetAST
    target: MatchTargetAST
    conditions: list[ConditionAST] = field(default_factory=list)
    edges: list[EmitEdgeAST] = field(default_factory=list)
    priority: int = 100
    enabled: bool = True
    depends_on: list[str] = field(default_factory=list)
    binding_names: set[str] = field(default_factory=set)
    from_ref_bindings: set[str] = field(default_factory=set)
    to_ref_bindings: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# RuleASTBuilder
# ---------------------------------------------------------------------------


class RuleASTBuilder:
    """
    Converts a Pydantic Rule model into a runtime RuleAST.

    This builder:
        1. Converts MatchTarget dicts to MatchTargetAST objects
        2. Compiles regex patterns and parses binding path specs
        3. Extracts binding names from edge templates
        4. Validates internal consistency
    """

    def __init__(self, rule: Rule):
        self._rule = rule

    def build(self) -> RuleAST:
        """Build and return a RuleAST from the source Rule."""
        source = self._build_match_target(self._rule.match.get("source"))
        target = self._build_match_target(self._rule.match.get("target"))

        conditions = [self._build_condition(c) for c in self._rule.conditions]
        edges = [self._build_edge(e) for e in self._rule.edges]

        all_bindings = self._rule.get_binding_names()
        from_refs = self._collect_ref_bindings(lambda e: e.from_ref)
        to_refs = self._collect_ref_bindings(lambda e: e.to_ref)

        return RuleAST(
            rule_id=self._rule.id,
            source=source,
            target=target,
            conditions=conditions,
            edges=edges,
            priority=self._rule.priority,
            enabled=self._rule.enabled,
            depends_on=self._rule.depends_on,
            binding_names=all_bindings,
            from_ref_bindings=from_refs,
            to_ref_bindings=to_refs,
        )

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_match_target(self, mt: MatchTarget | None) -> MatchTargetAST:
        """Convert a MatchTarget Pydantic model to MatchTargetAST."""
        if mt is None:
            mt = MatchTarget()

        compiled_pattern: re.Pattern | None = None
        if mt.method_pattern:
            try:
                compiled_pattern = re.compile(mt.method_pattern)
            except re.error as e:
                import warnings
                warnings.warn(f"Invalid regex in method_pattern '{mt.method_pattern}': {e}")
                compiled_pattern = None

        paired_ast: MatchTargetAST | None = None
        if mt.paired_with:
            paired_ast = self._build_match_target(mt.paired_with)

        return MatchTargetAST(
            language=mt.language,
            file_pattern=mt.file_pattern,
            annotation=mt.annotation,
            class_annotation=mt.class_annotation,
            method_pattern=compiled_pattern,
            return_type=mt.return_type,
            kind=mt.kind,
            paired_with=paired_ast,
        )

    def _build_condition(self, cond: Condition) -> ConditionAST:
        """Convert a Condition Pydantic model to ConditionAST."""
        compiled_pattern: re.Pattern | None = None
        if cond.pattern:
            try:
                compiled_pattern = re.compile(cond.pattern)
            except re.error as e:
                import warnings
                warnings.warn(f"Invalid regex in condition pattern '{cond.pattern}': {e}")
                compiled_pattern = None

        binding_specs: dict[str, BindingPathSpec] = {}
        for name, path_spec in cond.bindings.items():
            binding_specs[name] = BindingPathSpec.parse(path_spec)

        sub_asts = [self._build_condition(sub) for sub in cond.sub_conditions]

        return ConditionAST(
            type=cond.type,
            query=cond.query,
            annotation=cond.annotation,
            pattern=compiled_pattern,
            relates_to=cond.relates_to,
            bindings=binding_specs,
            target=cond.target or "source",
            combinator=cond.combinator,
            sub_asts=sub_asts,
        )

    def _build_edge(self, edge: EmitEdge) -> EmitEdgeAST:
        """Convert an EmitEdge Pydantic model to EmitEdgeAST."""
        return EmitEdgeAST(
            name=edge.name,
            from_ref=edge.from_ref,
            to_ref=edge.to_ref,
            kind=edge.kind,
            properties=dict(edge.properties),
            line_ref=edge.line_ref,
        )

    def _collect_ref_bindings(self, accessor) -> set[str]:
        """Extract all {binding} placeholders from edge templates."""
        refs: set[str] = set()
        for edge in self._rule.edges:
            template = accessor(edge)
            refs.update(re.findall(r"\{([^}]+)\}", template))
        return refs
