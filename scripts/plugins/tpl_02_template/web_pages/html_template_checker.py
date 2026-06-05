"""HTML template syntax checker plugin.

Checks HTML files for server-side template syntax from various frameworks:
- Jinja2: {{ }}, {% %}, {# #}
- Django: {{ }}, {% %}, {# #}
- Handlebars: {{ }}, {{# }}, {{/ }}
- Mustache: {{ }}
- Blade: @{{ }}, @{{{{ }}}}
- PHP: <?php ?>, <?= ?>
- ASP/JSP: <% %>, <%= %>
- ERB: <% %>, <%= %>
- Thymeleaf: th:*
- Freemarker: ${ }, <# >
- Vue: {{ }}, v-*
- React/JSX: { }, {/*
- EJS: <% %>, <%= %>

Extracts:
- Template variable references
- Template conditionals and loops
- Template includes and extends
- Server-side directives
- Frontend framework bindings
"""

import re
from pathlib import Path
from typing import Optional

from .base import TemplateElement, TemplatePlugin, TemplateParseResult
from .registry import register


# Server-side template syntax patterns
_TEMPLATE_PATTERNS = {
    # Jinja2 / Django / Nunjucks
    "jinja2_var": (
        re.compile(r'\{\{\s*([^}]+?)\s*\}\}'),
        "jinja2"
    ),
    "jinja2_tag": (
        re.compile(r'\{%\s*(?:end)?(\w+)(?:\s+[^%]+)?\s*%\}'),
        "jinja2"
    ),
    "jinja2_comment": (
        re.compile(r'\{#\s*([^#]+?)\s*#\}'),
        "jinja2"
    ),

    # Handlebars / Mustache
    "handlebars_block": (
        re.compile(r'\{\{#(\w+)(?:\s+[^}]+)?\}\}'),
        "handlebars"
    ),
    "handlebars_var": (
        re.compile(r'\{\{\{?\s*([^}]+?)\s*\}?\}\}'),
        "handlebars"
    ),

    # Blade (Laravel)
    "blade_directive": (
        re.compile(r'@(\w+)(?:\([^)]*\))?(?:\s+(?!@)[\s\S]*?)?(?=\s*@|\s*<|\s*$)'),
        "blade"
    ),
    "blade_verbatim": (
        re.compile(r'@verbatim\s*([\s\S]*?)@endverbatim'),
        "blade"
    ),

    # PHP
    "php_tag": (
        re.compile(r'<\?(?:php)?[\s\S]*?\?>'),
        "php"
    ),
    "php_echo": (
        re.compile(r'<\?=\s*([^?]+)\s*\?>'),
        "php"
    ),

    # ASP / JSP
    "asp_scriptlet": (
        re.compile(r'<%\s*([^%]+)%\>'),
        "asp"
    ),
    "asp_expression": (
        re.compile(r'<%=\s*([^%]+)%\>'),
        "asp"
    ),
    "asp_directive": (
        re.compile(r'<%@\s*(\w+)(?:\s+[^%]+)?%>'),
        "asp"
    ),

    # ERB (Ruby)
    "erb_tag": (
        re.compile(r'<%[=#]?\s*([^%]+)\s*%>'),
        "erb"
    ),

    # Thymeleaf
    "thymeleaf_attr": (
        re.compile(r'th:(\w+)(?:="([^"]*)")?'),
        "thymeleaf"
    ),

    # Freemarker
    "freemarker_var": (
        re.compile(r'\$\{([^}]+)\}'),
        "freemarker"
    ),
    "freemarker_directive": (
        re.compile(r'<#(\w+)(?:\s+[^>]+)?>'),
        "freemarker"
    ),

    # Vue.js
    "vue_directive": (
        re.compile(r'v-(\w+)(?::(\w+))?(?:="([^"]*)")?'),
        "vue"
    ),
    "vue_interpolation": (
        re.compile(r'\{\{\s*([^}]+?)\s*\}\}'),
        "vue"
    ),

    # React / JSX
    "jsx_expr": (
        re.compile(r'\{/\*[\s\S]*?\*/\}|\{[^}]+\}'),
        "jsx"
    ),

    # EJS
    "ejs_tag": (
        re.compile(r'<%[=#]?\s*([^%]+)\s*%>'),
        "ejs"
    ),

    # Smarty
    "smarty_var": (
        re.compile(r'\{\$([^}]+)\}'),
        "smarty"
    ),
    "smarty_tag": (
        re.compile(r'\{(\w+)(?:\s+[^}]+)?\}'),
        "smarty"
    ),
}


# Server-side template detection patterns
_SERVER_SCRIPT_PATTERNS = {
    "php": re.compile(r'<\?(?:php)?', re.IGNORECASE),
    "asp": re.compile(r'<%|<!--\s*asp', re.IGNORECASE),
    "jsp": re.compile(r'<%@\s*page|<jsp:', re.IGNORECASE),
    "erb": re.compile(r'<%\s*ruby|<%%', re.IGNORECASE),
    "blade": re.compile(r'@if|@foreach|@section|@yield|@php', re.IGNORECASE),
    "django": re.compile(r'\{%\s*(?:if|for|block|include|extends|with)', re.IGNORECASE),
    "jinja2": re.compile(r'\{%|\{\{|\{#', re.IGNORECASE),
    "handlebars": re.compile(r'\{\{#', re.IGNORECASE),
    "mustache": re.compile(r'\{\{[^#]', re.IGNORECASE),
    "thymeleaf": re.compile(r'th:', re.IGNORECASE),
    "freemarker": re.compile(r'\$\{|<\#', re.IGNORECASE),
    "smarty": re.compile(r'\{\$', re.IGNORECASE),
}


class HtmlTemplateCheckerPlugin(TemplatePlugin):
    """Plugin for checking HTML files for server-side template syntax.

    This plugin detects and parses various server-side template syntaxes
    in HTML files to understand which template engine is being used
    and extract template elements.

    Supported template engines:
    - Jinja2, Django, Nunjucks
    - Handlebars, Mustache
    - Blade (Laravel)
    - PHP
    - ASP/JSP
    - ERB (Ruby)
    - Thymeleaf
    - Freemarker
    - Vue.js
    - React/JSX
    - EJS
    - Smarty
    """

    @property
    def name(self) -> str:
        return "html_template_checker"

    @property
    def description(self) -> str:
        return "HTML file server-side template syntax detection and parsing"

    @property
    def legacy_result_key(self) -> str:
        return "html_template"

    @property
    def supported_langs(self) -> list[str]:
        return ["python", "javascript", "typescript", "java", "go", "php"]

    @property
    def file_patterns(self) -> list[str]:
        return ["*.html", "*.htm", "*.blade.php", "*.vue", "*.jsx", "*.tsx"]

    @property
    def priority(self) -> int:
        return 60  # High priority — processes all HTML files first so that plain
                  # HTML (no server-side syntax) is labeled as html_template_checker
                  # rather than falling through to jinja2 (priority 50). Actual Jinja2
                  # files still get their Jinja2 elements extracted by the detector.

    def parse(self, file_path: Path) -> TemplateParseResult:
        """Parse an HTML file and extract server-side template syntax elements."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TemplateParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e)
            )

        elements: list[TemplateElement] = []
        file_str = str(file_path)

        # Detect template engine
        detected_engines = self._detect_template_engines(content)
        if detected_engines:
            elements.append(TemplateElement(
                kind="template_engine_detected",
                tag_name="html",
                attrs={"engines": detected_engines},
                line=1,
                file=file_str
            ))

        # Extract template elements based on detected engines
        if "php" in detected_engines:
            elements.extend(self._extract_php(content, file_str))
        if any(e in detected_engines for e in ["jinja2", "django", "nunjucks"]):
            elements.extend(self._extract_jinja2(content, file_str))
        if any(e in detected_engines for e in ["handlebars", "mustache"]):
            elements.extend(self._extract_handlebars(content, file_str))
        if "blade" in detected_engines:
            elements.extend(self._extract_blade(content, file_str))
        if any(e in detected_engines for e in ["asp", "jsp"]):
            elements.extend(self._extract_asp_jsp(content, file_str))
        if "thymeleaf" in detected_engines:
            elements.extend(self._extract_thymeleaf(content, file_str))
        if "freemarker" in detected_engines:
            elements.extend(self._extract_freemarker(content, file_str))
        if "vue" in detected_engines:
            elements.extend(self._extract_vue(content, file_str))
        if "jsx" in detected_engines:
            elements.extend(self._extract_jsx(content, file_str))
        if "smarty" in detected_engines:
            elements.extend(self._extract_smarty(content, file_str))
        if "erb" in detected_engines:
            elements.extend(self._extract_erb(content, file_str))

        return TemplateParseResult(
            file=file_str,
            elements=elements,
            parse_error=False
        )

    def _detect_template_engines(self, content: str) -> list[str]:
        """Detect which server-side template engines are used in the content."""
        detected = []

        for engine, pattern in _SERVER_SCRIPT_PATTERNS.items():
            if pattern.search(content):
                detected.append(engine)

        return detected

    def _extract_php(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract PHP script elements."""
        elements = []

        # PHP tags
        php_tag_pat = re.compile(r'(<\?php[\s\S]*?\?>)', re.MULTILINE)
        for match in php_tag_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="php_script",
                tag_name="php",
                attrs={"code": match.group(1)[:100]},
                line=line_num,
                file=file_str
            ))

        return elements

    def _extract_jinja2(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract Jinja2 template elements."""
        elements = []

        # Variables: {{ var }}
        var_pat = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
        for match in var_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            var_expr = match.group(1).strip()
            elements.append(TemplateElement(
                kind="jinja2_variable",
                tag_name="variable",
                attrs={"expression": var_expr},
                line=line_num,
                file=file_str,
                target=var_expr
            ))

        # Tags: {% if %}, {% for %}, {% block %}, etc.
        tag_pat = re.compile(r'\{%\s*(end)?(\w+)(?:\s+([^%]+))?\s*%\}')
        for match in tag_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            is_end = match.group(1) == "end"
            tag_name = match.group(2)
            tag_content = match.group(3) or ""

            elements.append(TemplateElement(
                kind=f"jinja2_{'end' if is_end else tag_name}",
                tag_name=tag_name,
                attrs={"content": tag_content.strip(), "is_end": is_end},
                line=line_num,
                file=file_str
            ))

        # Comments: {# comment #}
        comment_pat = re.compile(r'\{#\s*([^#]+)\s*#\}')
        for match in comment_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="jinja2_comment",
                tag_name="comment",
                attrs={"text": match.group(1).strip()},
                line=line_num,
                file=file_str
            ))

        return elements

    def _extract_handlebars(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract Handlebars/Mustache template elements."""
        elements = []

        # Block helpers: {{#each}}, {{#if}}, etc.
        block_pat = re.compile(r'\{\{#(\w+)(?:\s+([^}]+))?\}\}')
        for match in block_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="handlebars_block",
                tag_name=match.group(1),
                attrs={"expression": match.group(2) or ""},
                line=line_num,
                file=file_str
            ))

        # Variables: {{var}}, {{{var}}}
        var_pat = re.compile(r'\{\{\{?\s*([^}]+?)\s*\}?\}\}')
        for match in var_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            var_expr = match.group(1).strip()
            if not var_expr.startswith("#") and not var_expr.startswith("/"):
                elements.append(TemplateElement(
                    kind="handlebars_variable",
                    tag_name="variable",
                    attrs={"expression": var_expr},
                    line=line_num,
                    file=file_str,
                    target=var_expr
                ))

        return elements

    def _extract_blade(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract Laravel Blade template elements."""
        elements = []

        # Blade directives: @if, @foreach, @section, etc.
        directive_pat = re.compile(r'@(\w+)(?:\(([^)]*)\))?(?:\s+([\s\S]*?))?(?=@|\s*</|\s*$)')
        for match in directive_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            directive = match.group(1)
            args = match.group(2) or ""
            content_attr = match.group(3) or ""

            elements.append(TemplateElement(
                kind=f"blade_{directive}",
                tag_name=directive,
                attrs={"args": args, "content": content_attr[:100]},
                line=line_num,
                file=file_str
            ))

        # {{ }} interpolation in Blade
        blade_var_pat = re.compile(r'\{\{\{\{\s*(.+?)\s*\}\}\}\}')  # {{{ }}}
        for match in blade_var_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="blade_unescaped_var",
                tag_name="variable",
                attrs={"expression": match.group(1).strip()},
                line=line_num,
                file=file_str
            ))

        return elements

    def _extract_asp_jsp(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract ASP/JSP scriptlet elements."""
        elements = []

        # Scriptlets: <% code %>
        scriptlet_pat = re.compile(r'<%\s*([^%]+)\%>')
        for match in scriptlet_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="asp_scriptlet",
                tag_name="scriptlet",
                attrs={"code": match.group(1).strip()[:100]},
                line=line_num,
                file=file_str
            ))

        # Expressions: <%= expression %>
        expr_pat = re.compile(r'<%=\s*([^%]+)\%>')
        for match in expr_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="asp_expression",
                tag_name="expression",
                attrs={"expression": match.group(1).strip()},
                line=line_num,
                file=file_str,
                target=match.group(1).strip()
            ))

        # Directives: <%@ page %>
        directive_pat = re.compile(r'<%@\s*(\w+)(?:\s+([^%]+))?%>')
        for match in directive_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="asp_directive",
                tag_name=match.group(1),
                attrs={"attrs": match.group(2) or ""},
                line=line_num,
                file=file_str
            ))

        return elements

    def _extract_thymeleaf(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract Thymeleaf attributes."""
        elements = []

        # th: attributes
        th_attr_pat = re.compile(r'th:(\w+)(?:="([^"]*)")?')
        for match in th_attr_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="thymeleaf_attribute",
                tag_name=match.group(1),
                attrs={"value": match.group(2) or ""},
                line=line_num,
                file=file_str
            ))

        return elements

    def _extract_freemarker(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract FreeMarker template elements."""
        elements = []

        # Variables: ${var}
        var_pat = re.compile(r'\$\{([^}]+)\}')
        for match in var_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="freemarker_variable",
                tag_name="variable",
                attrs={"expression": match.group(1).strip()},
                line=line_num,
                file=file_str,
                target=match.group(1).strip()
            ))

        # Directives: <#if>, <#list>, etc.
        directive_pat = re.compile(r'<#(\w+)(?:\s+([^>]+))?>')
        for match in directive_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="freemarker_directive",
                tag_name=match.group(1),
                attrs={"args": match.group(2) or ""},
                line=line_num,
                file=file_str
            ))

        return elements

    def _extract_vue(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract Vue.js directives and interpolation."""
        elements = []

        # Vue directives: v-if, v-for, v-bind:, v-on:, etc.
        vue_dir_pat = re.compile(r'v-(\w+)(?::(\w+))?(?:="([^"]*)")?')
        for match in vue_dir_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            directive = match.group(1)
            arg = match.group(2) or ""
            value = match.group(3) or ""

            elements.append(TemplateElement(
                kind=f"vue_{directive}",
                tag_name=f"v-{directive}",
                attrs={"arg": arg, "value": value},
                line=line_num,
                file=file_str
            ))

        # {{ }} interpolation
        vue_interp_pat = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
        for match in vue_interp_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            expr = match.group(1).strip()
            elements.append(TemplateElement(
                kind="vue_interpolation",
                tag_name="interpolation",
                attrs={"expression": expr},
                line=line_num,
                file=file_str,
                target=expr
            ))

        return elements

    def _extract_jsx(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract JSX expressions."""
        elements = []

        # JSX expressions: {expression}
        jsx_expr_pat = re.compile(r'\{([^{}][\s\S]*?)\}(?!\})')
        for match in jsx_expr_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            expr = match.group(1).strip()
            if expr and not expr.startswith("/*"):  # Skip comments
                elements.append(TemplateElement(
                    kind="jsx_expression",
                    tag_name="expression",
                    attrs={"expression": expr[:100]},
                    line=line_num,
                    file=file_str,
                    target=expr
                ))

        return elements

    def _extract_smarty(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract Smarty template elements."""
        elements = []

        # Variables: {$var}
        var_pat = re.compile(r'\{\$([^}]+)\}')
        for match in var_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            elements.append(TemplateElement(
                kind="smarty_variable",
                tag_name="variable",
                attrs={"name": match.group(1).strip()},
                line=line_num,
                file=file_str,
                target=match.group(1).strip()
            ))

        # Tags: {if}, {foreach}, {block}, etc.
        tag_pat = re.compile(r'\{(\w+)(?:\s+[^}]+)?\}')
        for match in tag_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            tag_name = match.group(1)
            if tag_name not in ("ldelim", "rdelim"):  # Skip delimiters
                elements.append(TemplateElement(
                    kind=f"smarty_{tag_name}",
                    tag_name=tag_name,
                    attrs={"raw": match.group(0)},
                    line=line_num,
                    file=file_str
                ))

        return elements

    def _extract_erb(self, content: str, file_str: str) -> list[TemplateElement]:
        """Extract ERB (Ruby) template elements."""
        elements = []

        # ERB tags: <% %>, <%= %>
        erb_pat = re.compile(r'<%[=#]?\s*([^%]+)\s*%>')
        for match in erb_pat.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            is_output = match.group(0).startswith("<%=")
            code = match.group(1).strip()

            elements.append(TemplateElement(
                kind="erb_scriptlet" if not is_output else "erb_output",
                tag_name="erb",
                attrs={"code": code, "output": is_output},
                line=line_num,
                file=file_str,
                target=code if is_output else None
            ))

        return elements

    def resolve_template_edges(
        self,
        elements: list[TemplateElement],
        context: "GraphContext",
        lang: Optional[str] = None,
    ) -> list["TemplateEdge"]:
        """Generate edges from template elements to code symbols.

        Quality gates:
        - Only edges where `to_qname` is a known symbol are kept.
        - Template files that reference no known symbols produce no edges.
        - Edges are deduplicated by (from, to, kind) to avoid duplicates.
        """
        from .base import TemplateEdge

        edges: list[TemplateEdge] = []
        seen: set[tuple[str, str, str]] = set()  # (from, to, kind)

        # Build a set of known symbol qnames for fast O(1) membership testing
        known_symbols: set[str] = set()
        for sym in context.symbols:
            qn = sym.get("qualified_name", "")
            if qn:
                known_symbols.add(qn)

        # Group elements by file
        elements_by_file: dict[str, list[TemplateElement]] = {}
        for elem in elements:
            f = elem.file or ""
            elements_by_file.setdefault(f, []).append(elem)

        for file_str, file_elements in elements_by_file.items():
            for elem in file_elements:
                if not elem.target:
                    continue

                # Only process meaningful template reference kinds
                if not (elem.kind.endswith("_variable")
                        or elem.kind.endswith("_interpolation")
                        or elem.kind in ("asp_expression", "erb_output")):
                    continue

                target = elem.target
                # Skip bare template expressions that don't look like code identifiers
                if not target or len(target) < 2 or target in ("true", "false", "null", "nil", "undefined"):
                    continue

                # Try to resolve template variable to code symbols
                for sym in context.symbols:
                    sym_name = sym.get("name", "")
                    qname = sym.get("qualified_name", "")

                    if sym_name != target and not qname.endswith(f".{target}"):
                        continue

                    key = (f"template::{file_str}", qname, "template_to_symbol")
                    if key in seen:
                        continue
                    seen.add(key)

                    edges.append(TemplateEdge(
                        kind="template_to_symbol",
                        from_qname=f"template::{file_str}",
                        to_qname=qname,
                        file=file_str,
                        line=elem.line,
                        metadata={
                            "template_expr": target,
                            "element_kind": elem.kind,
                        },
                    ))

                # Handle template includes/extends
                if elem.kind in ("jinja2_include", "jinja2_extends"):
                    if elem.attrs.get("template"):
                        key = (f"template::{file_str}", f"file::{elem.attrs['template']}", "template_include")
                        if key not in seen:
                            seen.add(key)
                            edges.append(TemplateEdge(
                                kind="template_include",
                                from_qname=f"template::{file_str}",
                                to_qname=f"file::{elem.attrs['template']}",
                                file=file_str,
                                line=elem.line,
                                metadata={"template": elem.attrs["template"]},
                            ))

        # Cap edges per file to prevent noise from large templates
        MAX_EDGES_PER_FILE = 10
        by_file: dict[str, list[TemplateEdge]] = {}
        for e in edges:
            by_file.setdefault(e.file or "", []).append(e)
        capped: list[TemplateEdge] = []
        for f, file_edges in by_file.items():
            capped.extend(file_edges[:MAX_EDGES_PER_FILE])
        return capped


# Register the plugin
register(HtmlTemplateCheckerPlugin)
