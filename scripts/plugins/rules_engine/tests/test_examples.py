"""
Tests for example rule files - ensures all bundled examples pass Schema validation.
===================================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest

from scripts.plugins.rules_engine.schema import validate_rule, validate_bundle


# ---------------------------------------------------------------------------
# Example bundle rules
# ---------------------------------------------------------------------------

def _list_example_yaml_files():
    examples_dir = (
        Path(__file__).parent.parent / "bundles" / "built-in" / "examples"
    )
    if not examples_dir.exists():
        pytest.skip("examples directory not found")
    return list(examples_dir.glob("*.yaml"))


@pytest.mark.parametrize("yaml_file", _list_example_yaml_files())
def test_example_rule_file_valid(yaml_file: Path):
    """Each example YAML file must pass schema validation without errors."""
    content = yaml_file.read_text(encoding="utf-8")
    rule, errors = validate_rule(content)
    assert rule is not None, (
        f"Example rule {yaml_file.name} failed validation:\n" + "\n".join(errors)
    )
    assert errors == [], f"Unexpected errors for {yaml_file.name}: {errors}"


def _list_all_bundle_rule_files():
    built_in_dir = (
        Path(__file__).parent.parent / "bundles" / "built-in"
    )
    if not built_in_dir.exists():
        pytest.skip("bundles/built-in directory not found")
    result = []
    for bundle_dir in built_in_dir.iterdir():
        if not bundle_dir.is_dir():
            continue
        rules_dir = bundle_dir / "rules"
        if not rules_dir.exists():
            continue
        for yaml_file in rules_dir.glob("*.yaml"):
            result.append((bundle_dir.name, yaml_file))
    return result


@pytest.mark.parametrize("bundle_name,yaml_file", _list_all_bundle_rule_files())
def test_bundle_rule_files_valid(bundle_name: str, yaml_file: Path):
    """All rule files in all built-in bundles must pass schema validation."""
    content = yaml_file.read_text(encoding="utf-8")
    rule, errors = validate_rule(content)
    assert rule is not None, (
        f"Bundle '{bundle_name}' rule {yaml_file.name} failed:\n" + "\n".join(errors)
    )
    assert errors == [], f"Unexpected errors for {bundle_name}/{yaml_file.name}: {errors}"


# ---------------------------------------------------------------------------
# Built-in bundle validation
# ---------------------------------------------------------------------------

def test_java_orm_bundle_valid():
    bundle_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "java-orm"
    )
    valid, errors = validate_bundle(bundle_dir)
    assert valid, f"java-orm bundle errors:\n" + "\n".join(errors)


def test_web_framework_bundle_valid():
    bundle_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "web-framework"
    )
    valid, errors = validate_bundle(bundle_dir)
    assert valid, f"web-framework bundle errors:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Rule content checks (semantic validation of example content)
# ---------------------------------------------------------------------------

def test_mybatis_orm_example_has_correct_structure():
    examples_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "examples"
    )
    file_path = examples_dir / "mybatis-orm.yaml"
    if not file_path.exists():
        pytest.skip("mybatis-orm.yaml not found")

    rule, errors = validate_rule(file_path)
    assert rule is not None, f"Validation errors: {errors}"

    # Must have all condition types used in the design example
    condition_types = {c.type for c in rule.conditions}
    assert "annotation" in condition_types
    assert "ast_query" in condition_types

    # Must have at least one edge
    assert len(rule.edges) >= 1
    assert rule.edges[0].kind == "sql_mapping"


def test_jsp_java_example_has_regex_condition():
    examples_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "examples"
    )
    file_path = examples_dir / "jsp-java.yaml"
    if not file_path.exists():
        pytest.skip("jsp-java.yaml not found")

    rule, errors = validate_rule(file_path)
    assert rule is not None, f"Validation errors: {errors}"

    condition_types = {c.type for c in rule.conditions}
    assert "regex" in condition_types


def test_webxml_servlet_example_has_xpath_condition():
    examples_dir = (
        Path(__file__).parent.parent
        / "bundles"
        / "built-in"
        / "examples"
    )
    file_path = examples_dir / "webxml-servlet.yaml"
    if not file_path.exists():
        pytest.skip("webxml-servlet.yaml not found")

    rule, errors = validate_rule(file_path)
    assert rule is not None, f"Validation errors: {errors}"

    condition_types = {c.type for c in rule.conditions}
    assert "xpath" in condition_types
    assert "annotation" in condition_types


def test_all_rules_have_unique_ids():
    """All rule files in bundles must have unique ids within their bundle."""
    built_in_dir = (
        Path(__file__).parent.parent / "bundles" / "built-in"
    )
    all_ids = {}
    for bundle_dir in built_in_dir.iterdir():
        if not bundle_dir.is_dir():
            continue
        rules_dir = bundle_dir / "rules"
        if not rules_dir.exists():
            continue
        for yaml_file in rules_dir.glob("*.yaml"):
            rule, errors = validate_rule(yaml_file)
            if rule is None:
                continue  # will be caught by other tests
            if rule.id in all_ids:
                pytest.fail(
                    f"Duplicate rule id '{rule.id}' in "
                    f"{all_ids[rule.id]} and {yaml_file}"
                )
            all_ids[rule.id] = str(yaml_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
