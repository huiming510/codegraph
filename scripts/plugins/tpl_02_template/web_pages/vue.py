"""Vue Single File Component (SFC) plugin.

Parses Vue .vue files for:
- Script setup imports
- Component usage in template
- Props, emits, computed properties
- Lifecycle hooks
"""

import re
from pathlib import Path

from .base import TemplatePlugin, TemplateElement, TemplateParseResult
from .registry import register


# Regex patterns for Vue SFC
_VUE_SCRIPT_SETUP_PAT = re.compile(r'<script\s+setup[^>]*>')
_VUE_IMPORT_PAT = re.compile(
    r'import\s+(?:{\s*([^}]+)\s*}|(\w+))\s+from\s+["\']([^"\']+)["\']'
)
_VUE_COMPONENT_PAT = re.compile(r'<([A-Z][a-zA-Z0-9_-]+)[\s>]')
_VUE_PROP_PAT = re.compile(
    r'(?:defineProps|props)\s*:\s*\{([^}]+)\}',
    re.MULTILINE
)
_VUE_EMIT_PAT = re.compile(
    r'(?:defineEmits|emits)\s*:\s*\[([^\]]+)\]',
    re.MULTILINE
)
_VUE_COMPUTED_PAT = re.compile(
    r'(?:const|let|var)\s+(\w+)\s*=\s*computed\(',
    re.MULTILINE
)
_VUE_WATCH_PAT = re.compile(
    r'watch\([^,]+,\s*\([^)]+\)\s*=>\s*\{',
    re.MULTILINE
)
_VUE_REF_PAT = re.compile(
    r'(?:const|let|var)\s+(\w+)\s*=\s*ref\(',
    re.MULTILINE
)


class VueTemplatePlugin(TemplatePlugin):
    """Plugin for parsing Vue Single File Component (.vue) files."""

    @property
    def name(self) -> str:
        return "vue"

    @property
    def description(self) -> str:
        return "Vue Single File Component (SFC)"

    @property
    def legacy_result_key(self) -> str:
        return "vue"

    @property
    def supported_langs(self) -> list[str]:
        return ["javascript"]

    @property
    def file_patterns(self) -> list[str]:
        return ["*.vue"]

    @property
    def priority(self) -> int:
        return 90  # High priority, .vue is specific to Vue

    def parse(self, file_path: Path) -> TemplateParseResult:
        """Parse a Vue SFC file and extract elements."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TemplateParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e)
            )

        elements: list[TemplateElement] = []
        elements.extend(self._parse_script_setup(content, file_path))
        elements.extend(self._parse_template(content, file_path))

        return TemplateParseResult(
            file=str(file_path),
            elements=elements,
            parse_error=False
        )

    def _parse_script_setup(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract script setup elements."""
        elements = []

        # Extract script setup block
        script_match = _VUE_SCRIPT_SETUP_PAT.search(content)
        if not script_match:
            return elements

        script_start = script_match.end()
        script_end = content.find("</script>", script_start)
        if script_end == -1:
            script_end = len(content)
        script_content = content[script_start:script_end]

        # Imports
        for m in _VUE_IMPORT_PAT.finditer(script_content):
            names = m.group(1) or m.group(2) or ""
            source = m.group(3)
            line_offset = content[:m.start()].count("\n")

            for name in names.replace(" ", "").split(","):
                name = name.strip()
                if name:
                    elements.append(TemplateElement(
                        kind="js_import",
                        tag_name="import",
                        attrs={"name": name, "source": source},
                        target=source,
                        line=line_offset + 1,
                        file=str(file_path)
                    ))

        # Props
        for m in _VUE_PROP_PAT.finditer(script_content):
            line_offset = content[:m.start()].count("\n")
            props_str = m.group(1)
            for prop in re.findall(r'(\w+)', props_str):
                elements.append(TemplateElement(
                    kind="vue_prop",
                    tag_name="prop",
                    attrs={"name": prop},
                    line=line_offset + 1,
                    file=str(file_path)
                ))

        # Emits
        for m in _VUE_EMIT_PAT.finditer(script_content):
            line_offset = content[:m.start()].count("\n")
            emits_str = m.group(1)
            for emit in re.findall(r'["\']?(\w+)["\']?', emits_str):
                if emit:
                    elements.append(TemplateElement(
                        kind="vue_emit",
                        tag_name="emit",
                        attrs={"name": emit},
                        line=line_offset + 1,
                        file=str(file_path)
                    ))

        # Computed
        for m in _VUE_COMPUTED_PAT.finditer(script_content):
            name = m.group(1)
            line_offset = content[:m.start()].count("\n")
            elements.append(TemplateElement(
                kind="vue_computed",
                tag_name="computed",
                attrs={"name": name},
                line=line_offset + 1,
                file=str(file_path)
            ))

        # Refs
        for m in _VUE_REF_PAT.finditer(script_content):
            name = m.group(1)
            line_offset = content[:m.start()].count("\n")
            elements.append(TemplateElement(
                kind="vue_ref",
                tag_name="ref",
                attrs={"name": name},
                line=line_offset + 1,
                file=str(file_path)
            ))

        return elements

    def _parse_template(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract template elements (component usage)."""
        elements = []

        # Find template block
        template_match = re.search(r'<template[^>]*>', content)
        if not template_match:
            return elements

        template_start = template_match.end()
        template_end = content.find("</template>", template_start)
        if template_end == -1:
            return elements
        template_content = content[template_start:template_end]

        # Component usage
        for m in _VUE_COMPONENT_PAT.finditer(template_content):
            tag = m.group(1)
            # Skip HTML elements (lowercase)
            if tag[0].islower():
                continue
            line_offset = content[:template_match.start() + m.start()].count("\n")
            elements.append(TemplateElement(
                kind="vue_component",
                tag_name=tag,
                attrs={},
                line=line_offset + 1,
                file=str(file_path)
            ))

        return elements

    def resolve_template_edges(
        self,
        elements: list[TemplateElement],
        symbols: list[dict],
    ) -> list[dict]:
        """Generate edges from Vue elements to code symbols."""
        edges = []
        by_simple: dict[str, list[dict]] = {}

        for s in symbols:
            by_simple.setdefault(s["name"], []).append(s)

        for elem in elements:
            if elem.kind == "js_import":
                name = elem.attrs.get("name", "")
                source = elem.attrs.get("source", "")
                if name:
                    edges.append({
                        "kind": "imports",
                        "from_qname": f"vue::{elem.file}",
                        "to_qname": name,
                        "file": elem.file or "",
                        "line": elem.line,
                    })

            elif elem.kind == "vue_component":
                tag = elem.tag_name
                candidates = by_simple.get(tag, [])
                for cand in candidates:
                    if cand.get("kind") in ("class", "function", "variable", "component"):
                        edges.append({
                            "kind": "uses_component",
                            "from_qname": f"vue::{elem.file}",
                            "to_qname": cand["qualified_name"],
                            "file": elem.file or "",
                            "line": elem.line,
                        })
                        break

        return edges


# Register the plugin
register(VueTemplatePlugin)
