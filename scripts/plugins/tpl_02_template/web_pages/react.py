"""React JSX/TSX component plugin.

Parses React component files for:
- Import statements
- JSX component usage
- Hook usage (useState, useEffect, etc.)
- Component exports
"""

import re
from pathlib import Path

from .base import TemplatePlugin, TemplateElement, TemplateParseResult
from .registry import register


# Regex patterns for React/JSX
_REACT_IMPORT_PAT = re.compile(
    r'import\s+(?:{\s*([^}]+)\s*}|(\w+))\s+from\s+["\']([^"\']+)["\']'
)
_REACT_JSX_TAG_PAT = re.compile(r'<([A-Z][a-zA-Z0-9_]*)\s', re.MULTILINE)
_REACT_HOOK_PAT = re.compile(
    r'(?:const|let|var)\s+\[([^\]]+)\]\s*=\s*(use\w+)\('
)
_REACT_EXPORT_DEFAULT_PAT = re.compile(
    r'export\s+default\s+(?:function|const|class)?\s*(\w+)'
)
_REACT_EXPORT_PAT = re.compile(
    r'export\s+(?:function|const|class)\s+(\w+)'
)


class ReactTemplatePlugin(TemplatePlugin):
    """Plugin for parsing React JSX/TSX component files."""

    @property
    def name(self) -> str:
        return "jsx"

    @property
    def description(self) -> str:
        return "React JSX/TSX component files"

    @property
    def legacy_result_key(self) -> str:
        return "react"

    @property
    def supported_langs(self) -> list[str]:
        return ["javascript"]

    @property
    def file_patterns(self) -> list[str]:
        return ["*.jsx", "*.tsx"]

    @property
    def priority(self) -> int:
        return 80  # High priority for JSX files

    def parse(self, file_path: Path) -> TemplateParseResult:
        """Parse a React JSX/TSX file and extract elements."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TemplateParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e)
            )

        elements: list[TemplateElement] = []
        elements.extend(self._parse_imports(content, file_path))
        elements.extend(self._parse_jsx_tags(content, file_path))
        elements.extend(self._parse_hooks(content, file_path))
        elements.extend(self._parse_exports(content, file_path))

        return TemplateParseResult(
            file=str(file_path),
            elements=elements,
            parse_error=False
        )

    def _parse_imports(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract import statements."""
        elements = []

        for m in _REACT_IMPORT_PAT.finditer(content):
            names = m.group(1) or m.group(2) or ""
            source = m.group(3)

            for name in names.replace(" ", "").split(","):
                name = name.strip()
                if name:
                    elements.append(TemplateElement(
                        kind="js_import",
                        tag_name="import",
                        attrs={"name": name, "source": source},
                        target=source,
                        line=content[:m.start()].count("\n") + 1,
                        file=str(file_path)
                    ))

        return elements

    def _parse_jsx_tags(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract JSX component tags."""
        elements = []

        for m in _REACT_JSX_TAG_PAT.finditer(content):
            tag = m.group(1)
            elements.append(TemplateElement(
                kind="jsx_component",
                tag_name=tag,
                attrs={},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def _parse_hooks(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract React hook usage."""
        elements = []

        for m in _REACT_HOOK_PAT.finditer(content):
            vars_, hook = m.group(1), m.group(2)
            elements.append(TemplateElement(
                kind="react_hook",
                tag_name=hook,
                attrs={"variables": vars_},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def _parse_exports(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract export statements."""
        elements = []

        for m in _REACT_EXPORT_DEFAULT_PAT.finditer(content):
            name = m.group(1)
            elements.append(TemplateElement(
                kind="react_export_default",
                tag_name="export",
                attrs={"name": name, "type": "default"},
                target=name,
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        for m in _REACT_EXPORT_PAT.finditer(content):
            name = m.group(1)
            elements.append(TemplateElement(
                kind="react_export",
                tag_name="export",
                attrs={"name": name, "type": "named"},
                target=name,
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def resolve_template_edges(
        self,
        elements: list[TemplateElement],
        symbols: list[dict],
    ) -> list[dict]:
        """Generate edges from React elements to code symbols."""
        edges = []
        by_simple: dict[str, list[dict]] = {}

        for s in symbols:
            by_simple.setdefault(s["name"], []).append(s)

        for elem in elements:
            if elem.kind == "js_import":
                # Import → imported symbol
                name = elem.attrs.get("name", "")
                source = elem.attrs.get("source", "")
                if name:
                    edges.append({
                        "kind": "imports",
                        "from_qname": f"jsx::{elem.file}",
                        "to_qname": name,
                        "file": elem.file or "",
                        "line": elem.line,
                    })

            elif elem.kind == "jsx_component":
                # JSX tag → component symbol
                tag = elem.tag_name
                candidates = by_simple.get(tag, [])
                for cand in candidates:
                    if cand.get("kind") in ("class", "function", "method"):
                        edges.append({
                            "kind": "uses_component",
                            "from_qname": f"jsx::{elem.file}",
                            "to_qname": cand["qualified_name"],
                            "file": elem.file or "",
                            "line": elem.line,
                        })
                        break

        return edges


# Register the plugin
register(ReactTemplatePlugin)
