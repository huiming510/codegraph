"""JavaScript / TypeScript language plugin — supports JS/TS/JSX/TSX via tree-sitter-javascript."""

import os
from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser
from tqdm import tqdm

import tree_sitter_javascript as tsjs

from ._register_helper import register
from ...common.base import Edge, LanguagePlugin, Symbol


_JS_LANGUAGE = Language(tsjs.language())
_JS_PARSER = Parser(_JS_LANGUAGE)


# ── tree helpers ────────────────────────────────────────────────────────────────

def _get_text(node: dict, default: str = "") -> str:
    if "text" in node:
        return node["text"]
    parts = []
    for c in node.get("children", []):
        t = _get_text(c)
        if t:
            parts.append(t)
    return "".join(parts) or default


def _first_child(node: dict, *types) -> Optional[dict]:
    for c in node.get("children", []):
        if c["type"] in types:
            return c
    return None


def _find_nodes(node: dict, node_type: str) -> list[dict]:
    found = []
    if node.get("type") == node_type:
        found.append(node)
    for c in node.get("children", []):
        found.extend(_find_nodes(c, node_type))
    return found


def _collect_calls(node: dict, results: list) -> None:
    if node.get("type") == "call_expression":
        results.append(node)
    for c in node.get("children", []):
        _collect_calls(c, results)


def _is_nested(node: dict) -> bool:
    """Return True if this node is nested inside a class or function body."""
    parent = node.get("_parent")
    while parent:
        t = parent.get("type", "")
        if t in ("class_declaration", "function_declaration",
                 "function_expression", "arrow_function",
                 "method_definition", "class_expression"):
            return True
        parent = parent.get("_parent")
    return False


# ── symbol builder ──────────────────────────────────────────────────────────────

def _infer_module_name(file_path: str) -> str:
    """Infer a module/namespace name from a file path.

    e.g.  src/components/Button.tsx → src/components/Button.tsx
    JS doesn't have packages, so we use the full relative path as namespace.
    """
    try:
        p = Path(file_path)
        stem = p.stem  # "Button" from "Button.tsx"
        parent = p.parent
        # use relative path from nearest src/node_modules boundary
        return str(parent / stem)
    except (ValueError, OSError):
        return file_path


def _strip_type_annotation(text: str) -> str:
    """Remove TypeScript type annotation suffix like ': Type' from a name."""
    if ":" in text:
        return text.split(":")[0].strip()
    return text


class _JSSymbolBuilder:
    """Builds Symbol list from a JavaScript/TypeScript AST entry."""

    def __init__(self, ast_entry: dict, src_root: str = ""):
        self.entry = ast_entry
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._file: str = ast_entry["file"]
        self._src_root = src_root
        self._module_name = _infer_module_name(self._file)
        self._is_ts: bool = Path(self._file).suffix in (".ts", ".tsx")

    def _current_scope(self) -> str:
        return ".".join(self._scope_stack) if self._scope_stack else self._module_name

    def _qualified(self, name: str) -> str:
        parts = [p for p in [self._module_name, *self._scope_stack, name] if p]
        return ".".join(parts)

    def _push(self, name: str) -> None:
        self._scope_stack.append(name)

    def _pop(self) -> None:
        if self._scope_stack:
            self._scope_stack.pop()

    def _decorators_of(self, node: dict) -> list[str]:
        anns = []
        for c in node.get("children", []):
            if c.get("type") == "decorator":
                anns.append("@" + _get_text(c).lstrip("@"))
        return anns

    def _type_from_node(self, node: dict) -> Optional[str]:
        """Extract type name from a type_annotation node."""
        if node is None:
            return None
        t = node.get("type", "")
        if t == "type_annotation":
            return _get_text(node).lstrip(":").strip()
        if t == "builtin_type":
            return _get_text(node)
        return None

    def _visit(self, node: dict, parent: Optional[dict] = None) -> None:
        node["_parent"] = parent
        t = node.get("type", "")

        # class declaration
        if t == "class_declaration":
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            anns = self._decorators_of(node)
            heritage: list[str] = []
            for c in node.get("children", []):
                if c.get("type") in ("extends_clause", "implements_clause"):
                    heritage.append(_get_text(c))
            sym = Symbol(
                name=name,
                kind="class",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                annotations=anns,
                lang="javascript",
            )
            if _is_nested(node):
                sym.modifiers = ["inner"]
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        # interface declaration (TypeScript)
        if t == "interface_declaration":
            name_node = _first_child(node, "type_identifier", "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            anns = self._decorators_of(node)
            sym = Symbol(
                name=name,
                kind="interface",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                annotations=anns,
                lang="javascript",
            )
            if _is_nested(node):
                sym.modifiers = ["inner"]
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        # enum declaration
        if t == "enum_declaration":
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            anns = self._decorators_of(node)
            sym = Symbol(
                name=name,
                kind="enum",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                annotations=anns,
                lang="javascript",
            )
            if _is_nested(node):
                sym.modifiers = ["inner"]
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        # type alias (TypeScript)
        if t == "type_alias_declaration":
            name_node = _first_child(node, "type_identifier", "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            anns = self._decorators_of(node)
            type_node = _first_child(node, "type_annotation")
            sym = Symbol(
                name=name,
                kind="class",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=self._type_from_node(type_node),
                annotations=anns,
                lang="javascript",
            )
            self.symbols.append(sym)
            return

        # function declaration
        if t == "function_declaration":
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            anns = self._decorators_of(node)
            type_node = _first_child(node, "type_annotation")
            sym = Symbol(
                name=name,
                kind="function",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=self._type_from_node(type_node),
                annotations=anns,
                lang="javascript",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        # method definition (inside class)
        if t == "method_definition":
            name_node = _first_child(
                node, "property_identifier", "identifier",
                "computed_property_name", "string",
            )
            raw_name = _get_text(name_node) if name_node else "<anon>"
            name = _strip_type_annotation(raw_name)
            anns = self._decorators_of(node)
            type_node = _first_child(node, "type_annotation")
            mods: list[str] = []
            for c in node.get("children", []):
                if c.get("type") in ("static", "async"):
                    mods.append(c.get("type"))
            is_constructor = name == "constructor"
            kind = "method"
            if is_constructor:
                kind = "method"
            sym = Symbol(
                name=name,
                kind=kind,
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=self._type_from_node(type_node),
                modifiers=mods,
                annotations=anns,
                lang="javascript",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        # field_definition (class property, TypeScript)
        if t == "field_definition":
            name_node = _first_child(
                node, "property_identifier", "identifier",
                "computed_property_name", "string",
            )
            raw_name = _get_text(name_node) if name_node else "<anon>"
            name = _strip_type_annotation(raw_name)
            type_node = _first_child(node, "type_annotation")
            mods: list[str] = []
            for c in node.get("children", []):
                if c.get("type") in ("static", "readonly"):
                    mods.append(c.get("type"))
            self.symbols.append(Symbol(
                name=name,
                kind="field",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=self._type_from_node(type_node),
                modifiers=mods,
                lang="javascript",
            ))
            return

        # arrow function assigned to identifier (const foo = () => {})
        if t == "variable_declarator":
            name_node = _first_child(node, "identifier", "array_pattern", "object_pattern")
            if name_node:
                name = _get_text(name_node)
                # look for arrow function in declarator
                init_node = _first_child(node, "arrow_function")
                if init_node is not None:
                    is_method = bool(self._scope_stack)
                    kind = "method" if is_method else "function"
                    self.symbols.append(Symbol(
                        name=name,
                        kind=kind,
                        qualified_name=self._qualified(name),
                        file=self._file,
                        start=tuple(node["start"]),
                        end=tuple(node["end"]),
                        scope=self._current_scope(),
                        lang="javascript",
                    ))
                    # Visit arrow function body so call edges can be found inside it.
                    self._push(name)
                    for c in init_node.get("children", []):
                        self._visit(c, init_node)
                    self._pop()
                    return
            return

        # formal_parameters (function parameters)
        if t == "formal_parameters":
            for child in node.get("children", []):
                tn = child.get("type", "")
                if tn in ("required_parameter", "optional_parameter",
                          "rest_parameter", "typed_parameter"):
                    name_node = _first_child(
                        child, "identifier", "property_identifier",
                        "assignment_pattern",
                    )
                    raw_name = _get_text(name_node) if name_node else ""
                    name = _strip_type_annotation(raw_name).split("=")[0].strip()
                    if name and name not in ("this",):
                        type_node = _first_child(child, "type_annotation")
                        self.symbols.append(Symbol(
                            name=name,
                            kind="parameter",
                            qualified_name=self._qualified(name),
                            file=self._file,
                            start=tuple(node["start"]),
                            end=tuple(node["end"]),
                            scope=self._current_scope(),
                            type_hint=self._type_from_node(type_node),
                            lang="javascript",
                        ))
            return

        for c in node.get("children", []):
            self._visit(c, node)

    def build(self) -> list[Symbol]:
        if self.entry.get("parse_error") or self.entry.get("ast") is None:
            return []
        self._visit(self.entry["ast"], None)
        return self.symbols


# ── call edge resolver ──────────────────────────────────────────────────────────

class _JSCallResolver:
    """Resolves function/method call edges for JavaScript/TypeScript."""

    def __init__(self, symbols: list[Symbol], ast_data: list[dict]):
        self.symbols = symbols
        self.ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
        self._by_simple: dict[str, list[Symbol]] = {}
        self._by_qname: dict[str, Symbol] = {}
        for s in symbols:
            self._by_qname[s.qualified_name] = s
            self._by_simple.setdefault(s.name, []).append(s)

    def _get_call_target_name(self, call_node: dict) -> tuple[Optional[str], Optional[str]]:
        """Return (callee_name, receiver_name) from a call_expression node.

        Examples:
            foo()        → ("foo", None)
            obj.foo()    → ("foo", "obj")
            a.b.foo()    → ("foo", "a.b")
            React.useState() → ("useState", "React")
            import('foo') → (None, None)
        """
        children = call_node.get("children", [])
        # tree-sitter-javascript uses 'arguments'; older versions used 'argument_list'
        arg_types = ("arguments", "argument_list")

        def _extract_parts(target_node: dict) -> tuple[Optional[str], Optional[str]]:
            tn = target_node.get("type", "")
            if tn == "identifier":
                name = target_node.get("text") or _get_text(target_node)
                return name, None
            if tn == "member_expression":
                parts = []
                for part in target_node.get("children", []):
                    pt = part.get("type", "")
                    if pt in ("identifier", "property_identifier"):
                        t = part.get("text") if part.get("text") else _get_text(part)
                        if t:
                            parts.append(t)
                if len(parts) >= 2:
                    return parts[-1], ".".join(parts[:-1])
                elif len(parts) == 1:
                    return parts[0], None
                return None, None
            if tn == "call_expression":
                return None, None  # dynamic import
            return None, None

        for i, child in enumerate(children):
            if child.get("type") in arg_types and i > 0:
                target = children[i - 1]
                return _extract_parts(target)
        return None, None

    def resolve(self) -> list[Edge]:
        edges: list[Edge] = []
        seen_calls: set[tuple] = set()

        func_syms = [s for s in self.symbols if s.kind in ("function", "method")]
        for sym in tqdm(func_syms, desc="  Stage 4a calls", unit="func", ncols=80, leave=False):
            ast = self.ast_by_file.get(sym.file)
            if ast is None:
                continue
            method_node = self._find_node_at_line(ast, sym.name, sym.start[0])
            if method_node is None:
                continue

            call_nodes: list[dict] = []
            _collect_calls(method_node, call_nodes)

            for call in call_nodes:
                callee, receiver = self._get_call_target_name(call)
                if not callee:
                    continue

                candidates = self._by_simple.get(callee, [])
                if candidates:
                    same_scope = [c for c in candidates if c.scope == sym.scope]
                    resolved = same_scope[0] if same_scope else candidates[0]
                    key = (sym.qualified_name, resolved.qualified_name)
                    if key not in seen_calls:
                        seen_calls.add(key)
                        edges.append(Edge(
                            kind="call",
                            from_qname=sym.qualified_name,
                            to_qname=resolved.qualified_name,
                            file=sym.file,
                            line=call["start"][0],
                            receiver=receiver,
                        ))
                else:
                    # external call — still add as edge
                    edges.append(Edge(
                        kind="call",
                        from_qname=sym.qualified_name,
                        to_qname=f"ext::{callee}",
                        file=sym.file,
                        line=call["start"][0],
                        receiver=receiver,
                    ))

        return edges

    def _find_node_at_line(self, ast: dict, name: str, line: int) -> Optional[dict]:
        for node in (_find_nodes(ast, "function_declaration") +
                     _find_nodes(ast, "method_definition") +
                     _find_nodes(ast, "arrow_function")):
            for child in node.get("children", []):
                tn = child.get("type", "")
                if tn in ("identifier", "property_identifier") and _get_text(child) == name:
                    if node["start"][0] == line:
                        return node
        return None


# ── plugin class ──────────────────────────────────────────────────────────────

class JavaScriptPlugin(LanguagePlugin):
    lang_id = "javascript"
    display_name = "JavaScript/TypeScript"

    def get_file_patterns(self) -> list[str]:
        return ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs"]

    def get_tree_sitter_package(self) -> str:
        return "tree_sitter_javascript"

    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        return _JSSymbolBuilder(ast_entry, src_root).build()

    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        resolver = _JSCallResolver(symbols, ast_data)
        return resolver.resolve()

    def get_framework_annotations(self) -> dict[str, str]:
        return {
            "@RestController": "spring.controller",
            "@Controller": "spring.controller",
            "@GetMapping": "web.route",
            "@PostMapping": "web.route",
            "@PutMapping": "web.route",
            "@DeleteMapping": "web.route",
            "@RequestMapping": "spring.mapping",
            "@Injectable": "di.inject",
            "@Component": "di.component",
            "@Service": "spring.service",
            "@Module": "di.module",
            "@NgModule": "angular.module",
            "@Inject": "di.inject",
            "@Input": "react.prop",
            "@Output": "react.event",
            "@Prop": "react.prop",
            "@State": "react.state",
            "@Watch": "react.hook",
            "@Route": "web.route",
            "@Routes": "web.routes",
            "@beforeEnter": "web.route",
            "@Get": "web.route",
            "@Post": "web.route",
            "@app.get": "web.route",
            "@app.post": "web.route",
        }

    def infer_constructors(self) -> dict[str, str]:
        return {}

    def build_inner_class_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate inner_class edges for JavaScript/TypeScript nested classes."""
        edges: list[Edge] = []
        by_qname: dict[str, Symbol] = {s.qualified_name: s for s in symbols}

        for sym in symbols:
            if sym.kind not in ("class", "interface", "enum"):
                continue
            if "inner" not in (sym.modifiers or []):
                continue

            qname = sym.qualified_name
            if "." not in qname:
                continue

            outer_qname = qname.rsplit(".", 1)[0]
            if outer_qname in by_qname:
                edges.append(Edge(
                    kind="inner_class",
                    from_qname=outer_qname,
                    to_qname=qname,
                    file=sym.file,
                    line=sym.start[0] if sym.start else 1,
                ))

        return edges

    def get_entry_point_names(self) -> list[str]:
        """JavaScript/TypeScript entry points: main, init."""
        return ["main", "init"]

    def build_import_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate import edges for JavaScript/TypeScript.

        Handles:
        - import "module"         → string_import (external/named module import)
        - import x from "module"  → ts_import / js_import (named import)
        - import * as x from ... → namespace_import
        - export from "..."      → re-export
        - require("module")       → commonjs_require

        Unlike backend languages, JS has no 'import' kind symbols — we scan all
        AST files directly rather than filtering by symbol kind.
        """
        edges: list[Edge] = []
        seen: set[tuple] = set()

        ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

        for file_path, ast in tqdm(ast_by_file.items(), desc="  Stage 4b imports", unit="file", ncols=80, leave=False):
            import_nodes = _find_nodes(ast, "import_statement")
            import_nodes += _find_nodes(ast, "call_expression")

            for node in import_nodes:
                self._process_import_node(
                    node, ast, file_path, edges, seen
                )

        return edges

    def _process_import_node(
        self, node: dict, ast: dict, file_path: str,
        edges: list[Edge], seen: set
    ) -> None:
        ntype = node.get("type", "")

        if ntype == "import_statement":
            self._handle_import_statement(node, file_path, edges, seen)
            return

        if ntype == "call_expression":
            self._handle_require_call(node, file_path, edges, seen)
            return

    def _handle_import_statement(
        self, node: dict, from_file: str,
        edges: list[Edge], seen: set
    ) -> None:
        """Process an ES module import statement."""
        children = node.get("children", [])
        module_name = ""
        import_kinds = []
        import_specs = []

        for i, child in enumerate(children):
            ct = child.get("type", "")
            if ct in ("string", "string_fragment", "template_string"):
                raw = child.get("text", "")
                if not raw:
                    raw = _get_text(child)
                module_name = raw.strip('"\'')
            elif ct == "import_clause":
                import_specs = self._extract_import_specifiers(child)
            elif ct == "asterisk" or ct == "*":
                import_kinds.append("namespace")
            elif ct == "identifier" and not module_name:
                pass

        if not module_name:
            return

        edge_kind = self._classify_import(module_name, import_specs, import_kinds)
        if edge_kind is None:
            return

        from_module = self._infer_module_name(from_file)
        to_module = self._resolve_module_path(module_name, from_file)

        if not to_module:
            return

        key = (from_file, to_module)
        if key in seen:
            return
        seen.add(key)

        edges.append(Edge(
            kind=edge_kind,
            from_qname=from_module,
            to_qname=to_module,
            file=from_file,
            line=node["start"][0],
        ))

    def _handle_require_call(
        self, node: dict, from_file: str,
        edges: list[Edge], seen: set
    ) -> None:
        """Process a CommonJS require() call."""
        children = node.get("children", [])
        require_arg = None
        for i, child in enumerate(children):
            if child.get("type") == "call_expression":
                continue
            if child.get("type") == "identifier":
                if _get_text(child) == "require":
                    if i + 1 < len(children) and children[i + 1].get("type") == "argument_list":
                        args = children[i + 1].get("children", [])
                        for arg in args:
                            if arg.get("type") in ("string", "string_fragment"):
                                require_arg = (arg.get("text") or "").strip('"\'')
                                break

        if not require_arg:
            return

        from_module = self._infer_module_name(from_file)
        to_module = self._resolve_module_path(require_arg, from_file)

        if not to_module:
            return

        key = (from_file, to_module)
        if key in seen:
            return
        seen.add(key)

        edges.append(Edge(
            kind="js_import",
            from_qname=from_module,
            to_qname=to_module,
            file=from_file,
            line=node["start"][0],
        ))

    def _extract_import_specifiers(self, node: dict) -> list[str]:
        """Extract import specifier names from an import_clause node."""
        specs = []
        children = node.get("children", [])
        for child in children:
            ct = child.get("type", "")
            if ct == "identifier":
                specs.append(_get_text(child))
            elif ct == "import_specifier":
                for sub in child.get("children", []):
                    if sub.get("type") == "identifier":
                        specs.append(_get_text(sub))
            elif ct == "namespace_import":
                for sub in child.get("children", []):
                    if sub.get("type") == "identifier":
                        specs.append(_get_text(sub))
        return specs

    def _classify_import(
        self, module_name: str, specs: list[str], kinds: list[str]
    ) -> Optional[str]:
        """Classify the import kind based on module name and specifiers."""
        if "namespace" in kinds:
            return "js_import"
        if specs:
            return "ts_import" if self._is_ts_import(module_name, specs) else "js_import"
        return "js_import"

    def _is_external_module(self, module_name: str) -> bool:
        """Check if a module is external (node_modules or URL)."""
        if module_name.startswith("./") or module_name.startswith("../"):
            return False
        if module_name.startswith("/"):
            return False
        if "://" in module_name:
            return True
        return True

    def _is_ts_import(self, module_name: str, specs: list[str]) -> bool:
        """Heuristic: .ts/.tsx files or interfaces in specifiers suggest TypeScript."""
        if module_name.endswith((".ts", ".tsx", ".d.ts")):
            return True
        for spec in specs:
            if spec[0].isupper():
                return True
        return False

    def _infer_module_name(self, file_path: str) -> str:
        """Infer the module name from a file path."""
        return _infer_module_name(file_path)

    def _resolve_module_path(self, module_name: str, from_file: str) -> str:
        """Resolve a module path relative to a file.

        Handles:
        - Relative imports: ./foo, ../bar, ../../baz
        - Absolute/package imports: lodash, @scope/pkg
        """
        if module_name.startswith("."):
            return self._resolve_relative_path(module_name, from_file)

        return f"module:{module_name}"

    def _resolve_relative_path(self, rel_path: str, from_file: str) -> str:
        """Resolve a relative import path to a module qname."""
        try:
            from_path = Path(from_file).resolve()
            if rel_path.startswith("./") or rel_path.startswith("../"):
                base_dir = from_path.parent
            else:
                base_dir = from_path.parent
            resolved = (base_dir / rel_path).resolve()

            stem = resolved.stem
            parent = resolved.parent
            return str(parent / stem)
        except (ValueError, OSError):
            return rel_path


# ── self-register ─────────────────────────────────────────────────────────────

register(JavaScriptPlugin)
