"""JSP (JavaServer Pages) template plugin.

Parses JSP files for:
- Taglib directives
- Include directives
- Form bindings (r2:form, html:form)
- Custom tag usage
- Struts action references
- Bean expressions
"""

import re
from pathlib import Path

from .base import TemplatePlugin, TemplateElement, TemplateParseResult
from .registry import register


# Regex patterns for JSP content
_JSP_TAGLIB_PAT = re.compile(
    r'<%@\s*taglib\s+uri=["\']([^"\']+)["\']\s+prefix=["\']([^"\']+)["\']\s*%>',
    re.IGNORECASE
)
_JSP_INCLUDE_PAT = re.compile(
    r'<%@\s*include\s+file=["\']([^"\']+)["\']\s*%>',
    re.IGNORECASE
)
_JSP_R2_FORM_PAT = re.compile(
    r'<r2:form\s+[^>]*property=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_R2_FORM_ACT_PAT = re.compile(
    r'<r2:form\s+[^>]*action=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_R2_SELECT_PAT = re.compile(
    r'<r2:select\s+[^>]*property=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_HTML_FORM_PAT = re.compile(
    r'<html:form\s+[^>]*action=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_LOGIC_ITER_PAT = re.compile(
    r'<logic:iterate\s+[^>]*name=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_BEAN_WRITE_PAT = re.compile(
    r'<bean:write\s+[^>]*name=["\']([^"\']+)["\'][^>]*property=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_INCLUDE_TAG_PAT = re.compile(
    r'<(?:jj|jjn|jfn):include\s+[^>]*(?:href|page)=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_JSP_FN_URL_PAT = re.compile(
    r'\$\{f:url\(["\']([^"\']+)["\']\)\}',
    re.IGNORECASE
)
_JSP_CUSTOM_TAG_PAT = re.compile(
    r'<([a-z][a-z0-9_]*:[a-zA-Z][a-zA-Z0-9_-]*)\b',
    re.IGNORECASE
)

# Taglib prefix → URI mappings for standard tags
_TAGLIB_URI_MAP = {
    "html": "http://struts.apache.org/tags-html",
    "bean": "http://struts.apache.org/tags-bean",
    "logic": "http://struts.apache.org/tags-logic",
    "nested": "http://struts.apache.org/tags-nested",
    "tiles": "http://struts.apache.org/tags-tiles",
    "f": "http://java.sun.com/jsp/jstl/functions",
    "fmt": "http://java.sun.com/jsp/jstl/fmt",
    "c": "http://java.sun.com/jsp/jstl/core",
    "r2": "http://r2framework.rui",
    "jj": "http://r2framework.jp/jj",
    "r2fn": "http://r2framework/functions",
}

_STRUTS_URIS = {
    "http://struts.apache.org/tags-html",
    "http://struts.apache.org/tags-bean",
    "http://struts.apache.org/tags-logic",
    "http://struts.apache.org/tags-nested",
    "http://struts.apache.org/tags-tiles",
}


class JSPTemplatePlugin(TemplatePlugin):
    """Plugin for parsing JavaServer Pages (JSP) files."""

    @property
    def name(self) -> str:
        return "jsp"

    @property
    def description(self) -> str:
        return "JavaServer Pages (JSP) template engine"

    @property
    def legacy_result_key(self) -> str:
        return "jsp"

    @property
    def supported_langs(self) -> list[str]:
        return ["java"]

    @property
    def file_patterns(self) -> list[str]:
        return ["*.jsp", "*.jspf", "*.jspx"]

    @property
    def priority(self) -> int:
        return 100  # High priority for JSP-specific files

    def parse(self, file_path: Path) -> TemplateParseResult:
        """Parse a JSP file and extract elements."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TemplateParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e)
            )

        elements: list[TemplateElement] = []
        elements.extend(self._parse_taglib(content, file_path))
        elements.extend(self._parse_includes(content, file_path))
        elements.extend(self._parse_forms(content, file_path))
        elements.extend(self._parse_tags(content, file_path))

        return TemplateParseResult(
            file=str(file_path),
            elements=elements,
            parse_error=False
        )

    def _parse_taglib(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract taglib directives."""
        elements = []
        for m in _JSP_TAGLIB_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_taglib",
                tag_name=f"{m.group(2)}:*",
                attrs={"uri": m.group(1), "prefix": m.group(2)},
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))
        return elements

    def _parse_includes(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract include directives."""
        elements = []
        for m in _JSP_INCLUDE_PAT.finditer(content):
            target = m.group(1)
            if not target.startswith("/"):
                target = str(Path(file_path).parent / target)
            elements.append(TemplateElement(
                kind="jsp_include",
                tag_name="include",
                attrs={"file": target},
                target=target,
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))
        return elements

    def _parse_forms(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract form bindings and action references."""
        elements = []

        # r2:form property bindings
        for m in _JSP_R2_FORM_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_form",
                tag_name="r2:form",
                attrs={"property": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # r2:form action routing
        for m in _JSP_R2_FORM_ACT_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_struts_action",
                tag_name="r2:form",
                attrs={"action": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # r2:select (form field)
        for m in _JSP_R2_SELECT_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_form_field",
                tag_name="r2:select",
                attrs={"property": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # html:form action
        for m in _JSP_HTML_FORM_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_struts_action",
                tag_name="html:form",
                attrs={"action": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # logic:iterate name bindings
        for m in _JSP_LOGIC_ITER_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_logic",
                tag_name="logic:iterate",
                attrs={"name": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # bean:write
        for m in _JSP_BEAN_WRITE_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_bean",
                tag_name="bean:write",
                attrs={"name": m.group(1), "property": m.group(2)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # jj:include / jjn:navigate
        for m in _JSP_INCLUDE_TAG_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_include",
                tag_name="jj:include",
                attrs={"href": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        # ${f:url(...)} expressions
        for m in _JSP_FN_URL_PAT.finditer(content):
            elements.append(TemplateElement(
                kind="jsp_expression",
                tag_name="f:url",
                attrs={"url": m.group(1)},
                target=m.group(1),
                line=content[:m.start()].count("\n") + 1,
                file=str(file_path)
            ))

        return elements

    def _parse_tags(self, content: str, file_path: Path) -> list[TemplateElement]:
        """Extract custom tag usage."""
        elements = []
        seen_tags: set[str] = set()

        for m in _JSP_CUSTOM_TAG_PAT.finditer(content):
            tag_full = m.group(1)
            if tag_full in seen_tags:
                continue
            seen_tags.add(tag_full)

            # Skip standard taglib prefixes already handled
            prefix = tag_full.split(":")[0] if ":" in tag_full else ""
            is_struts = any(
                prefix == p for p, u in _TAGLIB_URI_MAP.items()
                if u in _STRUTS_URIS
            )

            elements.append(TemplateElement(
                kind="jsp_struts_tag" if is_struts else "jsp_custom_tag",
                tag_name=tag_full,
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
        """Generate edges from JSP elements to code symbols."""
        edges = []
        by_simple: dict[str, list[dict]] = {}

        for s in symbols:
            by_simple.setdefault(s["name"], []).append(s)

        for elem in elements:
            if elem.kind == "jsp_form":
                # Form binding → Form class
                # NOTE: form_bound edges are now generated by JspUiCrossEdgePlugin
                # which has more sophisticated matching logic. Template plugins
                # should only generate template-specific edges (includes, extends, etc.)
                pass

            elif elem.kind == "jsp_include":
                # Include → target file
                target = elem.attrs.get("file") or elem.target
                if target:
                    edges.append({
                        "kind": "includes",
                        "from_qname": f"jsp::{elem.file}",
                        "to_qname": f"file::{target}",
                        "file": elem.file or "",
                        "line": elem.line,
                    })

        return edges


# Register the plugin
register(JSPTemplatePlugin)
