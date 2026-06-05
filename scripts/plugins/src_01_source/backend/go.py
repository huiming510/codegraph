"""Go language plugin — supports Go source files via tree-sitter-go."""

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser
from tqdm import tqdm

import tree_sitter_go as tsgo

from ._register_helper import register
from ...common.base import Edge, LanguagePlugin, Symbol


_GO_LANGUAGE = Language(tsgo.language())
_GO_PARSER = Parser(_GO_LANGUAGE)


# ── tree helpers ────────────────────────────────────────────────────────────────

def _get_text(node: dict, default: str = "") -> str:
    if "text" in node:
        return node["text"]
    parts = []
    for c in node.get("children", []):
        parts.append(_get_text(c))
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


# ── module path resolution ─────────────────────────────────────────────────────

def _infer_package(file_path: str, src_root: str) -> str:
    """Infer package path from a Go file.

    e.g.  src_root="project/src", file="project/src/net/http/server.go"
          → "net/http"
    """
    try:
        abs_root = Path(src_root).resolve()
        abs_file = Path(file_path).resolve()
        rel = abs_file.relative_to(abs_root)
        parts = list(rel.parts)
        if parts[-1].startswith("doc.go"):
            parts = parts[:-1]
        elif parts[-1].endswith(".go"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)
    except (ValueError, OSError):
        return Path(file_path).stem


# ── symbol builder ─────────────────────────────────────────────────────────────

class _GoSymbolBuilder:
    """Builds Symbol list from a Go AST entry."""

    def __init__(self, ast_entry: dict, src_root: str = ""):
        self.entry = ast_entry
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._package: str = ""
        self._file: str = ast_entry["file"]
        self._src_root = src_root
        self._pkg_path = _infer_package(self._file, src_root)

    def _current_scope(self) -> str:
        return ".".join(self._scope_stack) if self._scope_stack else self._pkg_path

    def _qualified(self, name: str) -> str:
        parts = [p for p in [self._pkg_path, *self._scope_stack, name] if p]
        return ".".join(parts)

    def _push(self, name: str) -> None:
        self._scope_stack.append(name)

    def _pop(self) -> None:
        if self._scope_stack:
            self._scope_stack.pop()

    def _collect_line_comments(self, node: dict) -> Optional[str]:
        for c in node.get("children", []):
            if c.get("type") in ("comment", "line_comment"):
                return _get_text(c).lstrip("//").strip()
        return None

    def _visit(self, node: dict) -> None:
        t = node.get("type", "")

        if t == "package_clause":
            pkg_node = _first_child(node, "package_identifier")
            self._package = _get_text(pkg_node) if pkg_node else ""
            return

        # type_declaration covers structs, interfaces, and type aliases
        if t == "type_declaration":
            for child in node.get("children", []):
                if child.get("type") == "type_spec":
                    self._visit_type_spec(child)
            return

        if t == "function_declaration":
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            result_node = _first_child(node, "result")
            ret_type = None
            if result_node:
                type_node = _first_child(result_node, "pointer_type", "slice_type",
                                          "array_type", "type_identifier",
                                          "struct_type", "interface_type",
                                          "func_type", "map_type", "channel_type")
                if type_node:
                    ret_type = _get_text(type_node)
            doc = self._collect_line_comments(node)
            sym = Symbol(
                name=name,
                kind="function",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=ret_type,
                docstring=doc,
                lang="go",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c)
            self._pop()
            return

        if t == "method_declaration":
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            result_node = _first_child(node, "result")
            ret_type = None
            if result_node:
                type_node = _first_child(result_node, "pointer_type", "slice_type",
                                          "array_type", "type_identifier",
                                          "struct_type", "interface_type",
                                          "func_type", "map_type", "channel_type")
                if type_node:
                    ret_type = _get_text(type_node)
            doc = self._collect_line_comments(node)
            sym = Symbol(
                name=name,
                kind="method",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=ret_type,
                docstring=doc,
                lang="go",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c)
            self._pop()
            return

        if t == "field_declaration":
            type_node = _first_child(node, "pointer_type", "slice_type",
                                     "array_type", "type_identifier",
                                     "struct_type", "interface_type",
                                     "func_type", "map_type", "channel_type")
            for child in node.get("children", []):
                if child.get("type") == "field_identifier":
                    fname = _get_text(child)
                    self.symbols.append(Symbol(
                        name=fname,
                        kind="field",
                        qualified_name=self._qualified(fname),
                        file=self._file,
                        start=tuple(node["start"]),
                        end=tuple(node["end"]),
                        scope=self._current_scope(),
                        type_hint=_get_text(type_node) if type_node else None,
                        lang="go",
                    ))
            return

        if t == "parameter_declaration":
            type_node = _first_child(node, "pointer_type", "slice_type",
                                     "array_type", "type_identifier",
                                     "struct_type", "interface_type",
                                     "func_type", "map_type", "channel_type")
            for child in node.get("children", []):
                tn = child.get("type", "")
                if tn in ("identifier", "field_identifier"):
                    pname = _get_text(child)
                    if pname:
                        self.symbols.append(Symbol(
                            name=pname,
                            kind="parameter",
                            qualified_name=self._qualified(pname),
                            file=self._file,
                            start=tuple(node["start"]),
                            end=tuple(node["end"]),
                            scope=self._current_scope(),
                            type_hint=_get_text(type_node) if type_node else None,
                            lang="go",
                        ))
            return

        if t == "var_declaration":
            type_node = _first_child(node, "pointer_type", "slice_type",
                                     "array_type", "type_identifier",
                                     "struct_type", "interface_type",
                                     "func_type", "map_type", "channel_type")
            for child in node.get("children", []):
                tn = child.get("type", "")
                if tn in ("identifier_list", "identifier", "field_identifier"):
                    vname = _get_text(child)
                    if vname and vname != "_":
                        self.symbols.append(Symbol(
                            name=vname,
                            kind="variable",
                            qualified_name=self._qualified(vname),
                            file=self._file,
                            start=tuple(node["start"]),
                            end=tuple(node["end"]),
                            scope=self._current_scope(),
                            type_hint=_get_text(type_node) if type_node else None,
                            lang="go",
                        ))
            return

        for c in node.get("children", []):
            self._visit(c)

    def _visit_type_spec(self, node: dict) -> None:
        name_node = _first_child(node, "type_identifier")
        name = _get_text(name_node) if name_node else "<anon>"
        doc = self._collect_line_comments(node)

        for child in node.get("children", []):
            ct = child.get("type", "")
            if ct == "struct_type":
                sym = Symbol(
                    name=name,
                    kind="struct",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    docstring=doc,
                    lang="go",
                )
                if self._scope_stack:
                    sym.modifiers = ["inner"]
                self.symbols.append(sym)
                self._push(name)
                for c in child.get("children", []):
                    self._visit(c)
                self._pop()
                return
            if ct == "interface_type":
                sym = Symbol(
                    name=name,
                    kind="interface",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    docstring=doc,
                    lang="go",
                )
                if self._scope_stack:
                    sym.modifiers = ["inner"]
                self.symbols.append(sym)
                self._push(name)
                for c in child.get("children", []):
                    self._visit(c)
                self._pop()
                return
            # type alias: type Foo = Bar
            if ct not in ("type_identifier", "comment", "line_comment"):
                sym = Symbol(
                    name=name,
                    kind="class",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    docstring=doc,
                    lang="go",
                )
                if self._scope_stack:
                    sym.modifiers = ["inner"]
                self.symbols.append(sym)

    def build(self) -> list[Symbol]:
        if self.entry.get("parse_error") or self.entry.get("ast") is None:
            return []
        self._visit(self.entry["ast"])
        return self.symbols


# ── call edge resolver ──────────────────────────────────────────────────────────

class _GoCallResolver:
    """Resolves function/method call edges for Go."""

    def __init__(self, symbols: list[Symbol], ast_data: list[dict]):
        self.symbols = symbols
        self.ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
        self._by_simple: dict[str, list[Symbol]] = {}
        self._by_qname: dict[str, Symbol] = {}
        for s in symbols:
            self._by_qname[s.qualified_name] = s
            self._by_simple.setdefault(s.name, []).append(s)

    def _get_call_target_name(self, call_node: dict) -> tuple[Optional[str], Optional[str]]:
        """Return (callee_name, receiver_name) from a call_expression node."""
        children = call_node.get("children", [])
        for i, child in enumerate(children):
            if child.get("type") == "argument_list":
                if i > 0:
                    target = children[i - 1]
                    tn = target.get("type", "")
                    if tn == "identifier":
                        return _get_text(target), None
                    if tn == "selector_expression":
                        # pkg.Method() or obj.Method()
                        sel_children = target.get("children", [])
                        if len(sel_children) >= 2:
                            receiver = sel_children[0]
                            method = sel_children[-1]
                            recv_text = _get_text(receiver)
                            method_text = _get_text(method)
                            return method_text, recv_text
                    if tn == "call_expression":
                        return None, None
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
                    key = (sym.qualified_name, f"ext::{callee}", receiver)
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
                     _find_nodes(ast, "method_declaration")):
            id_node = _first_child(node, "identifier")
            if id_node and _get_text(id_node) == name and node["start"][0] == line:
                return node
        return None


# ── plugin class ──────────────────────────────────────────────────────────────

class GoPlugin(LanguagePlugin):
    lang_id = "go"
    display_name = "Go"

    def get_file_patterns(self) -> list[str]:
        return ["*.go"]

    def get_tree_sitter_package(self) -> str:
        return "tree_sitter_go"

    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        return _GoSymbolBuilder(ast_entry, src_root).build()

    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        resolver = _GoCallResolver(symbols, ast_data)
        return resolver.resolve()

    def build_inner_class_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate inner_class edges for Go nested types."""
        edges: list[Edge] = []
        by_qname: dict[str, Symbol] = {s.qualified_name: s for s in symbols}

        for sym in symbols:
            if sym.kind not in ("struct", "interface", "class"):
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

    def get_framework_annotations(self) -> dict[str, str]:
        return {
            "//go:generate": "codegen.generate",
            "//go:build": "build.tag",
            "+build": "build.tag",
            "// net/http.HandleFunc": "web.route",
            "// http.Handler": "web.handler",
            "json:": "data.serialization",
            "validate:": "data.validation",
            "yaml:": "data.serialization",
            "env:": "config.env",
            "mapstructure:": "data.mapping",
        }

    def infer_constructors(self) -> dict[str, str]:
        return {}

    def get_entry_point_names(self) -> list[str]:
        """Go entry points: main, init."""
        return ["main", "init"]

    def get_control_flow_hints(self, sym: dict) -> Optional[str]:
        """Detect control flow for Go symbols."""
        name = sym.get("name", "")

        # Go init functions are startup initializers
        if name == "init":
            return "startup_init"

        return None


# ── self-register ─────────────────────────────────────────────────────────────

register(GoPlugin)
