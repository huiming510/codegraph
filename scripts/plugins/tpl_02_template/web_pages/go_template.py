"""Go html/template plugin.

Parses Go template files for:
- Template defines
- Template usages
- Template variables
- Action blocks
"""

import re
from pathlib import Path

from .base import TemplatePlugin, TemplateElement, TemplateParseResult
from .registry import register


# Regex patterns for Go templates
_GO_TEMPLATE_DEFINE_PAT = re.compile(r'{{define\s+"([^"]+)"}}')
_GO_TEMPLATE_USE_PAT = re.compile(r'{{template\s+"([^"]+)"}}')
_GO_TEMPLATE_VAR_PAT = re.compile(r'{{\$\.([A-Z][a-zA-Z0-9_]*)}}')
_GO_TEMPLATE_ACTION_PAT = re.compile(r'{{(\w+)')
_GO_TEMPLATE_WITH_PAT = re.compile(r'{{with\s+([^}]+)}}')


class GoTemplatePlugin(TemplatePlugin):
    """Plugin for parsing Go html/template files."""

    @property
    def name(self) -> str:
        return "go_template"

    @property
    def description(self) -> str:
        return "Go html/template and text/template"

    @property
    def legacy_result_key(self) -> str:
        return "go_templates"

    @property
    def supported_langs(self) -> list[str]:
        return ["go"]

    @property
    def file_patterns(self) -> list[str]:
        return ["*.tmpl", "*.gohtml"]

    @property
    def priority(self) -> int:
        return 70

    def parse(self, file_path: Path) -> TemplateParseResult:
        """Parse a Go template file and extract elements."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TemplateParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e)
            )

        elements: list[TemplateElement] = []
        elements.extend(self._parse_defines(content, file_path))
        elements.extend(self._parse_uses(content, file_path))
        elements.extend(self._parse_actions(content, file_path))

        return TemplateParseResult(
            file=str(file_path),
            elements=elements,
            parse_error=False
        )

    def _parse_defines(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract template definitions."""
        elements = []

        for m in _GO_TEMPLATE_DEFINE_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_block",
                tag_name="define",
                attrs={"name": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def _parse_uses(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract template usages."""
        elements = []

        for m in _GO_TEMPLATE_USE_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_include",
                tag_name="template",
                attrs={"name": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def _parse_actions(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract template actions and variables."""
        elements = []

        # Template variables
        for m in _GO_TEMPLATE_VAR_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_variable",
                tag_name="variable",
                attrs={"name": m.group(1)},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # Action blocks
        for m in _GO_TEMPLATE_ACTION_PAT.finditer(content):
            action = m.group(1)
            # Skip common actions that aren't meaningful for graph
            if action.lower() in ("if", "else", "end", "range", "with", "template", "define", "block"):
                continue
            elements.append(TemplateElement(
                kind="template_action",
                tag_name=action,
                attrs={},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def resolve_template_edges(
        self,
        elements: list[TemplateElement],
        symbols: list[dict],
    ) -> list[dict]:
        """Generate edges from Go template elements."""
        edges = []

        for elem in elements:
            if elem.kind == "template_include":
                target = elem.target
                if target:
                    edges.append({
                        "kind": "template_include",
                        "from_qname": f"go_template::{elem.file}",
                        "to_qname": f"file::{target}",
                        "file": elem.file or "",
                        "line": elem.line,
                    })

            elif elem.kind == "template_block":
                target = elem.target
                if target:
                    edges.append({
                        "kind": "template_defines",
                        "from_qname": f"go_template::{elem.file}",
                        "to_qname": f"template::{target}",
                        "file": elem.file or "",
                        "line": elem.line,
                    })

        return edges


# Register the plugin
register(GoTemplatePlugin)
