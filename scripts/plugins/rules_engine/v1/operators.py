"""
Operator definitions for rule conditions.
=========================================
Defines supported operators for each condition type used in rule AST evaluation.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Operator Registry
# ---------------------------------------------------------------------------


class OperatorRegistry:
    """
    Registry of operators indexed by condition type.
    Each operator is a dict with:
        name        - Human-readable operator name
        symbol      - Symbolic representation
        description - What this operator does
    """

    _operators: dict[str, list[dict]] = {
        "ast_query": [
            {
                "name": "matches",
                "symbol": "~",
                "description": "Tree-sitter query matches at least one node",
            },
            {
                "name": "not_matches",
                "symbol": "!~",
                "description": "Tree-sitter query matches no nodes",
            },
        ],
        "regex": [
            {
                "name": "equals",
                "symbol": "==",
                "description": "Exact string match",
            },
            {
                "name": "not_equals",
                "symbol": "!=",
                "description": "String does not match",
            },
            {
                "name": "matches",
                "symbol": "~",
                "description": "Regex matches",
            },
            {
                "name": "contains",
                "symbol": "⊃",
                "description": "String contains substring",
            },
        ],
        "naming": [
            {
                "name": "matches",
                "symbol": "~",
                "description": "Name matches regex pattern",
            },
            {
                "name": "not_matches",
                "symbol": "!~",
                "description": "Name does not match regex pattern",
            },
            {
                "name": "equals",
                "symbol": "==",
                "description": "Name equals exact string",
            },
        ],
        "annotation": [
            {
                "name": "present",
                "symbol": "?",
                "description": "Annotation is present on the symbol",
            },
            {
                "name": "absent",
                "symbol": "!",
                "description": "Annotation is not present",
            },
            {
                "name": "has_attr",
                "symbol": "@",
                "description": "Annotation has the specified attribute",
            },
        ],
        "xpath": [
            {
                "name": "matches",
                "symbol": "~",
                "description": "XPath expression matches at least one node",
            },
            {
                "name": "not_matches",
                "symbol": "!~",
                "description": "XPath expression matches no nodes",
            },
            {
                "name": "count_eq",
                "symbol": "=",
                "description": "XPath result count equals expected value",
            },
        ],
        "relation": [
            {
                "name": "depends_on",
                "symbol": "->",
                "description": "Symbol depends on target rule's result",
            },
        ],
    }

    @classmethod
    def get_operators(cls, condition_type: str) -> list[dict]:
        """Return all operators for a given condition type."""
        return cls._operators.get(condition_type, [])

    @classmethod
    def get_all_types(cls) -> list[str]:
        """Return all registered condition types."""
        return list(cls._operators.keys())

    @classmethod
    def register(cls, condition_type: str, operators: list[dict]) -> None:
        """Register operators for a new condition type."""
        cls._operators[condition_type] = operators


# ---------------------------------------------------------------------------
# Transform Functions
# ---------------------------------------------------------------------------

_TRANSFORM_FUNCS: dict[str, callable[[str], str]] = {
    "camel_to_snake": lambda s: _camel_to_snake(s),
    "snake_to_camel": lambda s: _snake_to_camel(s),
    "trim": lambda s: s.strip(),
}


def apply_transform(value: str, transform_name: str) -> str:
    """
    Apply a named transform to a string value.

    Supported transforms:
        camel_to_snake - Converts camelCase to snake_case
        snake_to_camel - Converts snake_case to camelCase
        trim           - Removes leading/trailing whitespace
    """
    func = _TRANSFORM_FUNCS.get(transform_name)
    if func is None:
        raise ValueError(f"Unknown transform '{transform_name}'")
    return func(value)


def _camel_to_snake(s: str) -> str:
    """Convert camelCase string to snake_case."""
    import re
    s = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def _snake_to_camel(s: str) -> str:
    """Convert snake_case string to camelCase."""
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# ---------------------------------------------------------------------------
# Reference Templates
# ---------------------------------------------------------------------------

_REF_PREFIXES = {
    "target:": "target",
    "source:": "source",
    "db::": "db",
    "symbol:": "symbol",
    "meta:source": "meta_source",
    "meta:target": "meta_target",
}


def parse_ref_template(template: str) -> tuple[str, str, list[str]]:
    """
    Parse a from_ref / to_ref template string.

    Args:
        template: e.g. "target:{class}.{property}" or "db::{column}"

    Returns:
        (prefix, base, binding_names)
        prefix       - "target" | "source" | "db" | "symbol" | "meta"
        base         - The literal base part after prefix, e.g. "{class}.{property}"
        binding_names - List of {binding} placeholders found, e.g. ["class", "property"]
    """
    import re

    # Find prefix
    prefix = "literal"
    base = template
    for pfx, name in _REF_PREFIXES.items():
        if template.startswith(pfx):
            prefix = name
            base = template[len(pfx):]
            break

    # Extract {binding} placeholders
    binding_names = re.findall(r"\{([^}]+)\}", base)

    return prefix, base, binding_names


def render_ref_template(template: str, bindings: dict[str, str]) -> str:
    """
    Render a from_ref / to_ref template with actual binding values.

    Args:
        template: e.g. "target:{class}.{property}"
        bindings: {"class": "UserMapper", "property": "id"}

    Returns:
        Rendered string, e.g. "target:UserMapper.id"
    """
    import re

    def replacer(m: re.Match) -> str:
        key = m.group(1)
        return bindings.get(key, f"{{{key}}}")

    return re.sub(r"\{([^}]+)\}", replacer, template)
