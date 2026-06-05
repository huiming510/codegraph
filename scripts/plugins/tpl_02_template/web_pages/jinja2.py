"""Jinja2 template plugin.

Parses Jinja2/Jinja template files for:
- Template extends
- Include statements
- url_for references
- Macro definitions
- Variable assignments
"""

import re
from pathlib import Path

from .base import TemplatePlugin, TemplateElement, TemplateParseResult
from .registry import register


# Jinja2 syntax detection patterns (must check one of these to confirm it's a Jinja2 template)
_JINJA2_SYNTAX_PATTERNS = [
    re.compile(r'\{%[-+]?\s*'),
    re.compile(r'\{\{[-+]?'),
    re.compile(r'\{#(?!#)'),
]

# Regex patterns for Jinja2 templates
_JINJA2_EXTENDS_PAT = re.compile(
    r'{%\s*extends\s+["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JINJA2_INCLUDE_PAT = re.compile(
    r'{%\s*include\s+["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JINJA2_URL_FOR_PAT = re.compile(
    r'{{\s*url_for\(["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JINJA2_IMPORT_PAT = re.compile(
    r'{%\s*import\s+["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JINJA2_MACRO_PAT = re.compile(
    r'{%\s*macro\s+(\w+)',
    re.IGNORECASE
)
_JINJA2_SET_PAT = re.compile(
    r'{%\s*set\s+(\w+)',
    re.IGNORECASE
)
_JINJA2_FOR_PAT = re.compile(
    r'{%\s*for\s+(\w+)',
    re.IGNORECASE
)
_JINJA2_BLOCK_PAT = re.compile(
    r'{%\s*block\s+(\w+)',
    re.IGNORECASE
)


class Jinja2TemplatePlugin(TemplatePlugin):
    """Plugin for parsing Jinja2 template files."""

    @property
    def name(self) -> str:
        return "jinja2"

    @property
    def description(self) -> str:
        return "Jinja2 template engine (Python)"

    @property
    def legacy_result_key(self) -> str:
        return "jinja2"

    @property
    def supported_langs(self) -> list[str]:
        return ["python"]

    @property
    def file_patterns(self) -> list[str]:
        return ["*.html", "*.jinja", "*.jinja2", "*.j2", "*.twig"]

    @property
    def priority(self) -> int:
        return 50  # Medium priority, can be overridden

    def _has_jinja2_syntax(self, content: str) -> bool:
        """Check if content contains any Jinja2 syntax markers."""
        for pattern in _JINJA2_SYNTAX_PATTERNS:
            if pattern.search(content):
                return True
        return False

    def parse(self, file_path: Path) -> TemplateParseResult | None:
        """Parse a Jinja2 template file and extract elements.

        Returns None if the file doesn't contain Jinja2 syntax
        (e.g., plain HTML files).
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TemplateParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e)
            )

        # Skip files that don't contain Jinja2 syntax (e.g., plain HTML)
        if not self._has_jinja2_syntax(content):
            return None

        elements: list[TemplateElement] = []
        elements.extend(self._parse_structure(content, file_path))

        return TemplateParseResult(
            file=str(file_path),
            elements=elements,
            parse_error=False
        )

    def _parse_structure(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract Jinja2 structural elements."""
        elements = []

        # extends
        for m in _JINJA2_EXTENDS_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_extends",
                tag_name="extends",
                attrs={"template": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # include
        for m in _JINJA2_INCLUDE_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_include",
                tag_name="include",
                attrs={"template": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # url_for
        for m in _JINJA2_URL_FOR_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_url_for",
                tag_name="url_for",
                attrs={"function": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # import
        for m in _JINJA2_IMPORT_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_import",
                tag_name="import",
                attrs={"module": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # macro
        for m in _JINJA2_MACRO_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_macro",
                tag_name="macro",
                attrs={"name": m.group(1)},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # block
        for m in _JINJA2_BLOCK_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="template_block",
                tag_name="block",
                attrs={"name": m.group(1)},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def resolve_template_edges(
        self,
        elements: list[TemplateElement],
        symbols: list[dict],
    ) -> list[dict]:
        """Generate edges from Jinja2 elements to code symbols."""
        edges = []

        for elem in elements:
            if elem.kind == "template_include":
                target = elem.target
                if target:
                    edges.append({
                        "kind": "template_include",
                        "from_qname": f"jinja2::{elem.file}",
                        "to_qname": f"file::{target}",
                        "file": elem.file or "",
                        "line": elem.line,
                    })

            elif elem.kind == "template_extends":
                target = elem.target
                if target:
                    edges.append({
                        "kind": "template_extends",
                        "from_qname": f"jinja2::{elem.file}",
                        "to_qname": f"file::{target}",
                        "file": elem.file or "",
                        "line": elem.line,
                    })

        return edges


# Register the plugin
register(Jinja2TemplatePlugin)
