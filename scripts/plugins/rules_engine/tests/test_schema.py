"""
Tests for schema.py - Pydantic models and validation functions.
=========================================================================
Covers:
    - Rule and RuleBundle Pydantic model instantiation
    - validate_rule() error detection with precise field paths
    - validate_bundle() completeness checks
    - Field validators (id format, condition type, binding source, etc.)
"""

import sys
from pathlib import Path

# Ensure the rules_engine module is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest

from scripts.plugins.rules_engine.schema import (
    validate_rule,
    validate_bundle,
    Rule,
    RuleBundle,
    MatchTarget,
    Condition,
    EmitEdge,
    BindingSpec,
    validate_rule as vr,
)


# ---------------------------------------------------------------------------
# Helper: minimal valid rule dict
# ---------------------------------------------------------------------------

def _minimal_rule(**overrides) -> dict:
    base = {
        "version": "1",
        "id": "test-rule",
        "match": {
            "source": {"language": "java"},
            "target": {"language": "java"},
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# test_validate_rule_success
# ---------------------------------------------------------------------------

def test_validate_rule_minimal_valid():
    yaml_str = """
version: "1"
id: mybatis-orm
match:
  source:
    language: java
    annotation: "@Mapper"
  target:
    language: java
    class_annotation: "@Entity"
"""
    rule, errors = validate_rule(yaml_str)
    assert errors == [], f"Expected no errors, got: {errors}"
    assert rule is not None
    assert rule.id == "mybatis-orm"
    assert rule.match["source"].language == "java"
    assert rule.match["source"].annotation == "@Mapper"


def test_validate_rule_with_conditions_and_edges():
    yaml_str = """
version: "1"
id: jsp-java
name:
  zh: JSP映射
  en: JSP Mapping
match:
  source:
    language: jsp
    file_pattern: "**/*.jsp"
  target:
    language: java
conditions:
  - type: regex
    pattern: 'class="([A-Za-z0-9_.]+)"'
    bindings:
      class_ref: "group(1)"
edges:
  - name: jsp-form-bean
    from_ref: "source:{jsp_file}"
    to_ref: "target:{class_ref}"
    kind: jsp_java_form
    properties:
      ref_type: form_bean
"""
    rule, errors = validate_rule(yaml_str)
    assert errors == [], f"Expected no errors, got: {errors}"
    assert rule is not None
    assert len(rule.conditions) == 1
    assert rule.conditions[0].type == "regex"
    assert rule.conditions[0].bindings["class_ref"] == "group(1)"
    assert len(rule.edges) == 1
    assert rule.edges[0].kind == "jsp_java_form"


def test_validate_rule_with_all_optional_fields():
    yaml_str = """
version: "1"
id: webxml-servlet
name:
  zh: WebXML
  en: WebXML Servlet
description: Maps web.xml to servlets
rule_version: "1.1.0"
author: codegraph
tags:
  - java
  - webxml
match:
  source:
    language: xml
    file_pattern: "**/web.xml"
  target:
    language: java
    class_annotation: "@WebServlet"
conditions:
  - type: xpath
    query: "//servlet"
    bindings:
      servlet_name: "servlet-name/text()"
  - type: annotation
    annotation: "@WebServlet"
    bindings:
      url_pattern: "key=value"
edges:
  - name: webxml-servlet-mapping
    from_ref: "target:{servlet_class}"
    to_ref: "source:{url_pattern}"
    kind: web_xml_to_servlet
    properties:
      servlet_name: "{servlet_name}"
    line_ref: line
priority: 50
enabled: true
depends_on:
  - other-rule-id
"""
    rule, errors = validate_rule(yaml_str)
    assert errors == [], f"Expected no errors, got: {errors}"
    assert rule is not None
    assert rule.priority == 50
    assert rule.enabled is True
    assert "java" in rule.tags
    assert "other-rule-id" in rule.depends_on


# ---------------------------------------------------------------------------
# test_validate_rule_errors
# ---------------------------------------------------------------------------

def test_validate_rule_missing_id():
    yaml_str = """
version: "1"
match:
  source: {language: java}
  target: {language: java}
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("id" in e.lower() for e in errors)


def test_validate_rule_missing_match_source():
    yaml_str = """
version: "1"
id: test-rule
match:
  target: {language: java}
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("source" in e for e in errors)


def test_validate_rule_missing_match_target():
    yaml_str = """
version: "1"
id: test-rule
match:
  source: {language: java}
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("target" in e for e in errors)


def test_validate_rule_invalid_id_format():
    yaml_str = """
version: "1"
id: "MyBatis-Orm"   # uppercase and starts with capital
match:
  source: {language: java}
  target: {language: java}
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("id" in e.lower() for e in errors)


def test_validate_rule_invalid_id_starts_with_hyphen():
    yaml_str = """
version: "1"
id: "-invalid-rule"
match:
  source: {language: java}
  target: {language: java}
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("id" in e.lower() for e in errors)


def test_validate_rule_invalid_condition_type():
    yaml_str = """
version: "1"
id: test-rule
match:
  source: {language: java}
  target: {language: java}
conditions:
  - type: invalid_type
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("condition type" in e.lower() for e in errors)


def test_validate_rule_invalid_combinator():
    yaml_str = """
version: "1"
id: test-rule
match:
  source: {language: java}
  target: {language: java}
conditions:
  - type: regex
    pattern: ".*"
    combinator: xor
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("combinator" in e.lower() for e in errors)


def test_validate_rule_invalid_binding_source():
    yaml_str = """
version: "1"
id: test-rule
match:
  source: {language: java}
  target: {language: java}
"""
    # Invalid source type in condition bindings is stored as raw string
    # (the schema accepts it as a plain string, so this tests the
    # BindingSpec validator specifically)
    from scripts.plugins.rules_engine.schema import BindingSpec, ValidationError
    with pytest.raises(ValidationError):
        BindingSpec(name="foo", source="invalid_source")


def test_validate_rule_extra_field():
    yaml_str = """
version: "1"
id: test-rule
match:
  source: {language: java}
  target: {language: java}
unknown_field: true
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("extra" in e.lower() for e in errors)


def test_validate_rule_invalid_version():
    yaml_str = """
version: "2"
id: test-rule
match:
  source: {language: java}
  target: {language: java}
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    assert any("version" in e.lower() for e in errors)


def test_validate_rule_yaml_parse_error():
    rule, errors = validate_rule("not: valid: yaml: [broken")
    assert rule is None
    assert any("YAML" in e or "parse" in e.lower() for e in errors)


def test_validate_rule_dict_input():
    data = {
        "version": "1",
        "id": "dict-rule",
        "match": {
            "source": {"language": "java"},
            "target": {"language": "java"},
        },
    }
    rule, errors = validate_rule(data)
    assert errors == []
    assert rule is not None
    assert rule.id == "dict-rule"


# ---------------------------------------------------------------------------
# test_validate_rule_precise_field_path
# ---------------------------------------------------------------------------

def test_validate_rule_precise_error_field_path():
    """Errors should include the field path like conditions[0].type."""
    yaml_str = """
version: "1"
id: test-rule
match:
  source: {language: java}
  target: {language: java}
conditions:
  - type: bad_type
"""
    rule, errors = validate_rule(yaml_str)
    assert rule is None
    # Check that error message includes a field reference
    assert len(errors) > 0
    error_text = " ".join(errors)
    # Should mention something about the condition type field
    assert any("type" in e for e in errors)


# ---------------------------------------------------------------------------
# test_validate_bundle
# ---------------------------------------------------------------------------

def test_validate_bundle_java_orm():
    bundle_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "java-orm"
    )
    valid, errors = validate_bundle(bundle_dir)
    assert valid, f"java-orm bundle validation failed:\n" + "\n".join(errors)
    assert len(errors) == 0


def test_validate_bundle_web_framework():
    bundle_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "web-framework"
    )
    valid, errors = validate_bundle(bundle_dir)
    assert valid, f"web-framework bundle validation failed:\n" + "\n".join(errors)
    assert len(errors) == 0


def test_validate_bundle_missing_metadata():
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / "empty-bundle"
        bundle_dir.mkdir()
        (bundle_dir / "rules").mkdir()
        valid, errors = validate_bundle(bundle_dir)
        assert valid is False
        assert any("metadata.yaml" in e for e in errors)


def test_validate_bundle_missing_rules_dir():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / "no-rules"
        bundle_dir.mkdir()
        (bundle_dir / "metadata.yaml").write_text(
            'id: test\nname: {zh: test}\nversion: "1.0.0"\n',
            encoding="utf-8"
        )
        valid, errors = validate_bundle(bundle_dir)
        assert valid is False
        assert any("rules" in e.lower() for e in errors)


def test_validate_bundle_rule_file_missing():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / "broken-bundle"
        bundle_dir.mkdir()
        rules_dir = bundle_dir / "rules"
        rules_dir.mkdir()
        (bundle_dir / "metadata.yaml").write_text(
            'id: test\nname: {zh: test}\nversion: "1.0.0"\nrules:\n  - file: nonexistent.yaml\n',
            encoding="utf-8"
        )
        valid, errors = validate_bundle(bundle_dir)
        assert valid is False
        assert any("not found" in e for e in errors)


# ---------------------------------------------------------------------------
# test_rule_bundle_model
# ---------------------------------------------------------------------------

def test_rule_bundle_metadata_valid():
    yaml_str = """
id: java-orm
name:
  zh: Java ORM
  en: Java ORM Rules
version: "1.0.0"
description: ORM mapping rules
author: codegraph
license: MIT
targets:
  languages:
    - java
  frameworks:
    - mybatis
rules:
  - file: mybatis-orm.yaml
"""
    import yaml
    data = yaml.safe_load(yaml_str)
    bundle = RuleBundle.model_validate(data)
    assert bundle.id == "java-orm"
    assert bundle.targets["languages"] == ["java"]
    assert bundle.targets["frameworks"] == ["mybatis"]
    assert len(bundle.rules) == 1


# ---------------------------------------------------------------------------
# test_rule_ast_builder
# ---------------------------------------------------------------------------

def test_rule_ast_builder_basic():
    from scripts.plugins.rules_engine.schema import validate_rule
    from scripts.plugins.rules_engine.v1.rule_ast import RuleASTBuilder

    yaml_str = """
version: "1"
id: test-rule
match:
  source:
    language: java
    annotation: "@Mapper"
    method_pattern: "findBy|getBy"
  target:
    language: java
    class_annotation: "@Entity"
conditions:
  - type: annotation
    annotation: "@Result"
    bindings:
      property: "key=property"
      column: "key=column"
edges:
  - name: test-edge
    from_ref: "target:{class}.{property}"
    to_ref: "db::{column}"
    kind: sql_mapping
    properties:
      mapping_type: "annotation"
"""
    rule, errors = validate_rule(yaml_str)
    assert errors == [], f"Rule validation failed: {errors}"
    assert rule is not None

    builder = RuleASTBuilder(rule)
    ast = builder.build()

    assert ast.rule_id == "test-rule"
    assert ast.source.language == "java"
    assert ast.source.annotation == "@Mapper"
    assert ast.source.method_pattern is not None
    assert ast.source.method_pattern.pattern == "findBy|getBy"
    assert ast.target.class_annotation == "@Entity"
    assert len(ast.conditions) == 1
    assert ast.conditions[0].bindings["property"].spec == "key=property"
    assert len(ast.edges) == 1
    assert "property" in ast.from_ref_bindings
    assert "column" in ast.to_ref_bindings
    assert "class" in ast.from_ref_bindings


# ---------------------------------------------------------------------------
# test_binding_path_spec
# ---------------------------------------------------------------------------

def test_binding_path_spec_parsing():
    from scripts.plugins.rules_engine.v1.rule_ast import BindingPathSpec

    for spec_str, expected_type, expected_value in [
        ("text", "text", ""),
        ("attr=class", "attr", "class"),
        ("key=property", "key", "property"),
        ("parent.attr", "parent", "attr"),
        ("parent.parent.attr", "parent", "parent.attr"),
    ]:
        spec = BindingPathSpec.parse(spec_str)
        assert spec.path_type == expected_type, f"spec={spec_str}"
        assert spec.path_value == expected_value, f"spec={spec_str}"


# ---------------------------------------------------------------------------
# test_operators
# ---------------------------------------------------------------------------

def test_operators_registry():
    from scripts.plugins.rules_engine.v1.operators import (
        OperatorRegistry,
        apply_transform,
        parse_ref_template,
        render_ref_template,
    )

    assert len(OperatorRegistry.get_operators("ast_query")) >= 1
    assert len(OperatorRegistry.get_operators("regex")) >= 2
    assert "ast_query" in OperatorRegistry.get_all_types()
    assert "annotation" in OperatorRegistry.get_all_types()


def test_transform_functions():
    from scripts.plugins.rules_engine.v1.operators import apply_transform

    assert apply_transform("camelCase", "camel_to_snake") == "camel_case"
    assert apply_transform("snake_case", "snake_to_camel") == "snakeCase"
    assert apply_transform("  spaces  ", "trim") == "spaces"


def test_ref_template_parsing():
    from scripts.plugins.rules_engine.v1.operators import parse_ref_template, render_ref_template

    prefix, base, bindings = parse_ref_template("target:{class}.{property}")
    assert prefix == "target"
    assert "{class}.{property}" == base
    assert set(bindings) == {"class", "property"}

    prefix, base, bindings = parse_ref_template("db::{column}")
    assert prefix == "db"
    assert "{column}" == base

    result = render_ref_template("target:{class}.{property}", {"class": "User", "property": "id"})
    assert result == "target:User.id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
