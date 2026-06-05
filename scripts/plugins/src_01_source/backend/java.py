"""Java language plugin — refactored from stage1_syntax / stage2_symbols / stage4_refs."""

from pathlib import Path
from typing import Optional

from tree_sitter import Parser
from tqdm import tqdm

import tree_sitter_java as tsjava
from tree_sitter import Language

from ._register_helper import register
from ...common.base import Edge, LanguagePlugin, Symbol


# ── module-level parser (shared across all parse operations) ──────────────────

_JAVA_LANGUAGE = Language(tsjava.language())
_JAVA_PARSER = Parser(_JAVA_LANGUAGE)

# ── external package detection (duplicated from cross_file.constants to avoid import) ──

_EXTERNAL_PACKAGES = (
    "java.", "javax.", "org.apache.", "org.springframework.",
    "org.springframework.", "org.seasar.", "org.hibernate.",
    "javax.persistence.", "org.junit.", "org.mockito.", "org.hamcrest.",
    "org.slf4j.", "ch.qos.", "com.sun.", "sun.", "org.omg.",
    "org.w3c.", "org.xml.", "junit.",
)


def _is_external_package(package_or_class: str) -> bool:
    return any(package_or_class.startswith(p) for p in _EXTERNAL_PACKAGES)


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


def _children_of_type(node: dict, *types) -> list[dict]:
    return [c for c in node.get("children", []) if c["type"] in types]


def _find_nodes(node: dict, node_type: str) -> list[dict]:
    found = []
    if node.get("type") == node_type:
        found.append(node)
    for c in node.get("children", []):
        found.extend(_find_nodes(c, node_type))
    return found


def _collect_method_calls(method_node: dict, results: list) -> None:
    """Recursively collect method_invocation nodes from a method AST."""
    if method_node.get("type") == "method_invocation":
        results.append(method_node)
    for c in method_node.get("children", []):
        _collect_method_calls(c, results)


def _collect_field_accesses(method_node: dict, results: list) -> None:
    if method_node.get("type") == "field_access":
        results.append(method_node)
    for c in method_node.get("children", []):
        _collect_field_accesses(c, results)


def _collect_identifier_refs(method_node: dict, results: list) -> None:
    """Collect bare identifier nodes that are not part of a field_access or method_invocation."""
    t = method_node.get("type", "")
    if t == "field_access":
        return
    if t == "method_invocation":
        children = method_node.get("children", [])
        for i, child in enumerate(children):
            if child["type"] == "argument_list" and i >= 3 and children[i - 2]["type"] == ".":
                receiver = children[i - 3]
                if receiver["type"] == "identifier":
                    results.append(receiver)
        return
    if t == "identifier":
        results.append(method_node)
        return
    for c in method_node.get("children", []):
        _collect_identifier_refs(c, results)


def _emit_inheritance_edges(
    edges: list,
    from_sym: Symbol,
    name: str,
    kind: str,
    candidates: list[Symbol],
    file: str,
    line: int,
) -> None:
    """Append one or more inheritance edges for a class/interface."""
    if candidates:
        for cand in candidates:
            edges.append(Edge(
                kind=kind,
                from_qname=from_sym.qualified_name,
                to_qname=cand.qualified_name,
                file=file,
                line=line,
            ))
    else:
        # Generate edges for external/unresolved base types as well.
        # These use ext:: prefix so downstream can filter if needed,
        # but at least the inheritance relationship is captured.
        edges.append(Edge(
            kind=kind,
            from_qname=from_sym.qualified_name,
            to_qname=f"ext::{name}",
            file=file,
            line=line,
        ))
    # External base classes (like java.lang.Object) should not produce edges anyway.


def _find_class_node_for_inheritance(ast: dict, sym: Symbol) -> Optional[dict]:
    """Find the class/interface/enum AST node matching the given symbol."""
    for n in (_find_nodes(ast, "class_declaration") +
              _find_nodes(ast, "interface_declaration") +
              _find_nodes(ast, "enum_declaration")):
        id_node = _first_child(n, "identifier")
        if id_node and _get_text(id_node) == sym.name \
                and n["start"][0] == sym.start[0]:
            return n
    return None


# ── symbol table builder ──────────────────────────────────────────────────────

class _JavaSymbolBuilder:
    """Builds Symbol list from a Java AST entry (used by JavaPlugin.build_symbols)."""

    def __init__(self, ast_entry: dict):
        self.entry = ast_entry
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._package: str = ""
        self._file: str = ast_entry["file"]

    def _current_scope(self) -> str:
        parts = [p for p in [self._package, *self._scope_stack] if p]
        return ".".join(parts) if parts else "<global>"

    def _qualified(self, name: str) -> str:
        parts = [p for p in [self._package, *self._scope_stack, name] if p]
        return ".".join(parts)

    def _push(self, name: str) -> None:
        self._scope_stack.append(name)

    def _pop(self) -> None:
        if self._scope_stack:
            self._scope_stack.pop()

    def _collect_modifiers(self, node: dict) -> tuple[list[str], list[str]]:
        mods, anns = [], []
        for c in node.get("children", []):
            if c["type"] == "modifiers":
                for m in c.get("children", []):
                    if m["type"] in ("marker_annotation", "annotation"):
                        ann = _get_text(_first_child(m, "identifier") or m)
                        anns.append("@" + ann)
                    elif m["type"] in (
                        "public", "private", "protected", "static",
                        "final", "abstract", "synchronized",
                    ):
                        mods.append(m["type"])
        return mods, anns

    def _type_text(self, node: dict) -> str:
        if node is None:
            return ""
        t = node.get("type", "")
        if t in (
            "type_identifier", "void_type", "integral_type",
            "floating_point_type", "boolean_type",
        ):
            return _get_text(node)
        if t == "array_type":
            return self._type_text(node["children"][0]) + "[]"
        if t in ("generic_type",):
            return _get_text(node)
        return _get_text(node)

    def _visit(self, node: dict) -> None:
        t = node.get("type", "")

        if t == "package_declaration":
            name_node = _first_child(node, "scoped_identifier", "identifier")
            self._package = _get_text(name_node) if name_node else ""
            return

        if t in ("class_declaration", "interface_declaration", "enum_declaration"):
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            mods, anns = self._collect_modifiers(node)
            kind = "interface" if t == "interface_declaration" else (
                "enum" if t == "enum_declaration" else "class"
            )
            if self._scope_stack:
                mods = list(mods) + ["inner"]
            sym = Symbol(
                name=name,
                kind=kind,
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                modifiers=mods,
                annotations=anns,
                lang="java",
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
            mods, anns = self._collect_modifiers(node)
            ret_node = _first_child(
                node,
                "void_type", "type_identifier", "array_type", "generic_type",
                "integral_type", "floating_point_type", "boolean_type",
            )
            sym = Symbol(
                name=name,
                kind="method",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=self._type_text(ret_node),
                modifiers=mods,
                annotations=anns,
                lang="java",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c)
            self._pop()
            return

        if t == "field_declaration":
            mods, anns = self._collect_modifiers(node)
            type_node = _first_child(
                node,
                "type_identifier", "array_type", "generic_type",
                "integral_type", "floating_point_type", "boolean_type", "void_type",
            )
            for declarator in _children_of_type(node, "variable_declarator"):
                name_node = _first_child(declarator, "identifier")
                name = _get_text(name_node) if name_node else "<anon>"
                sym = Symbol(
                    name=name,
                    kind="field",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(declarator["start"]),
                    end=tuple(declarator["end"]),
                    scope=self._current_scope(),
                    type_hint=self._type_text(type_node),
                    modifiers=mods,
                    annotations=anns,
                    lang="java",
                )
                self.symbols.append(sym)
            return

        if t == "formal_parameter":
            type_node = _first_child(
                node,
                "type_identifier", "array_type", "generic_type",
                "integral_type", "floating_point_type", "boolean_type", "void_type",
            )
            name_node = _first_child(node, "identifier")
            if name_node:
                name = _get_text(name_node)
                sym = Symbol(
                    name=name,
                    kind="parameter",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    type_hint=self._type_text(type_node),
                    lang="java",
                )
                self.symbols.append(sym)
            return

        for c in node.get("children", []):
            self._visit(c)

    def build(self) -> list[Symbol]:
        if self.entry.get("parse_error") or self.entry.get("ast") is None:
            return []
        self._visit(self.entry["ast"])
        return self.symbols


# ── reference resolver ─────────────────────────────────────────────────────────

_COLLECTION_TYPES = frozenset((
    "List", "ArrayList", "LinkedList", "Set", "HashSet", "LinkedHashSet",
    "TreeSet", "Map", "HashMap", "LinkedHashMap", "TreeMap",
    "Collection", "Iterable", "Iterator", "Enumeration",
    "Stream", "Optional", "OptionalInt", "OptionalLong",
))
_PROJECT_PKG_PREFIXES = ("jp.",)


def _simple_name(qname: str) -> str:
    return qname.split(".")[-1]


def _pkg(qname: str) -> str:
    return qname.rsplit(".", 1)[0] if "." in qname else ""


def _best_candidates(simple_name: str, ref_qname: str, by_simple: dict, by_qname: dict) -> list[dict]:
    """Return candidates for simple_name, preferring same-package; skip if ambiguous cross-package."""
    candidates = [c for c in by_simple.get(simple_name, [])
                  if c.qualified_name != ref_qname]
    ref_p = _pkg(ref_qname)
    same_pkg = [c for c in candidates if _pkg(c.qualified_name) == ref_p]
    if same_pkg:
        return same_pkg
    return candidates if len(candidates) == 1 else []


class _JavaCallResolver:
    """Resolves method call edges for Java (used by JavaPlugin.build_call_edges)."""

    def __init__(self, symbols: list[Symbol], ast_data: list[dict]):
        self.symbols = symbols
        self.ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
        self._by_simple: dict[str, list[Symbol]] = {}
        self._by_qname: dict[str, Symbol] = {}
        for s in symbols:
            self._by_qname[s.qualified_name] = s
            sn = _simple_name(s.qualified_name)
            self._by_simple.setdefault(sn, []).append(s)

    def _normalize_type(self, type_hint: str) -> str:
        return type_hint.rstrip("[]").split("<")[0]

    def _get_receiver_type(self, call_node: dict, caller_file: str) -> Optional[str]:
        """Extract receiver type for a method_invocation node."""
        children = call_node.get("children", [])
        receiver_name = None
        dot_seen = False
        for c in reversed(children):
            ct = c["type"]
            if ct == "argument_list":
                continue
            if ct == "identifier":
                if dot_seen:
                    receiver_name = _get_text(c)
                    break
                continue
            if ct == ".":
                dot_seen = True
                continue
            break

        for sym in self._by_simple.get(receiver_name, []):
            if sym.type_hint and sym.file == caller_file:
                return self._normalize_type(sym.type_hint)
        for sym in self._by_simple.get(receiver_name, []):
            if sym.type_hint:
                return self._normalize_type(sym.type_hint)
        if receiver_name and receiver_name[0].isupper():
            return receiver_name
        return None

    def _find_method_node(self, ast: dict, sym: Symbol) -> Optional[dict]:
        for n in _find_nodes(ast, "method_declaration"):
            id_node = _first_child(n, "identifier")
            if id_node and _get_text(id_node) == sym.name:
                if n["start"][0] == sym.start[0]:
                    return n
        return None

    def _find_class_node(self, ast: dict, sym: Symbol) -> Optional[dict]:
        for n in (_find_nodes(ast, "class_declaration") +
                  _find_nodes(ast, "interface_declaration") +
                  _find_nodes(ast, "enum_declaration")):
            id_node = _first_child(n, "identifier")
            if id_node and _get_text(id_node) == sym.name \
                    and n["start"][0] == sym.start[0]:
                return n
        return None

    def _last_identifier_before_args(self, call_node: dict) -> Optional[str]:
        children = call_node.get("children", [])
        last_ident = None
        for c in children:
            if c["type"] == "argument_list":
                break
            if c["type"] == "identifier":
                last_ident = _get_text(c)
        return last_ident

    def _receiver_node(self, call_node: dict) -> Optional[dict]:
        children = call_node.get("children", [])
        for i, c in enumerate(children):
            if c["type"] == "argument_list" and i >= 3 and children[i - 2]["type"] == ".":
                receiver = children[i - 3]
                if receiver["type"] == "identifier":
                    return receiver
        return None

    def resolve(self) -> list[Edge]:
        edges: list[Edge] = []

        method_syms = [s for s in self.symbols if s.kind == "method"]
        for sym in tqdm(method_syms, desc="  Stage 4a calls", unit="func", ncols=80, leave=False):
            ast = self.ast_by_file.get(sym.file)
            if ast is None:
                continue
            method_node = self._find_method_node(ast, sym)
            if method_node is None:
                continue
            call_nodes: list[dict] = []
            _collect_method_calls(method_node, call_nodes)
            caller_class = sym.scope
            for call in call_nodes:
                callee_name = self._last_identifier_before_args(call)
                if callee_name is None:
                    continue

                receiver_node = self._receiver_node(call)
                receiver_text = _get_text(receiver_node) if receiver_node else None
                receiver_type = None
                if receiver_text:
                    receiver_type = self._get_receiver_type(call, sym.file)

                candidates = self._by_simple.get(callee_name, [])
                method_candidates = [c for c in candidates if c.kind == "method"]
                same_class = [c for c in method_candidates if c.scope == caller_class]
                if same_class:
                    resolved = same_class[0]
                elif len(method_candidates) == 1:
                    candidate = method_candidates[0]
                    cand_pkg = _pkg(candidate.qualified_name)
                    is_project_candidate = any(cand_pkg.startswith(p) for p in _PROJECT_PKG_PREFIXES)

                    if receiver_text is None:
                        resolved = candidate
                    elif is_project_candidate and receiver_type:
                        recv_pkg = _pkg(receiver_type)
                        recv_simple = receiver_type.rstrip("[]").split("<")[0].split(".")[-1]
                        if recv_simple in _COLLECTION_TYPES:
                            resolved = None
                        else:
                            recv_class_name = receiver_type.rstrip("[]").split("<")[0].split(".")[-1]
                            cand_class_name = candidate.scope.split(".")[-1]
                            if recv_class_name == cand_class_name:
                                resolved = candidate
                            else:
                                resolved = None
                    elif is_project_candidate:
                        resolved = None
                    else:
                        resolved = None
                else:
                    resolved = None

                if resolved:
                    edges.append(Edge(
                        kind="call",
                        from_qname=sym.qualified_name,
                        to_qname=resolved.qualified_name,
                        file=sym.file,
                        line=call["start"][0],
                    ))
                else:
                    if receiver_text is None and receiver_node:
                        receiver_text = _get_text(receiver_node)
                    ext_qname = (
                        f"ext::{callee_name}@{receiver_type}" if receiver_type
                        else f"ext::{callee_name}"
                    )
                    edges.append(Edge(
                        kind="call",
                        from_qname=sym.qualified_name,
                        to_qname=ext_qname,
                        file=sym.file,
                        line=call["start"][0],
                        receiver=receiver_text,
                        receiver_type=receiver_type,
                    ))
                    if receiver_type:
                        ext_type = f"ext::{receiver_type}"
                        edges.append(Edge(
                            kind="contains",
                            from_qname=ext_type,
                            to_qname=ext_qname,
                            file=sym.file,
                            line=call["start"][0],
                        ))

        return edges


# ── plugin class ──────────────────────────────────────────────────────────────

class JavaPlugin(LanguagePlugin):
    lang_id = "java"
    display_name = "Java"
    _symbols: list[Symbol] = []  # class-level cache populated by build_symbols

    def get_file_patterns(self) -> list[str]:
        return ["*.java"]

    def get_tree_sitter_package(self) -> str:
        return "tree_sitter_java"

    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        syms = _JavaSymbolBuilder(ast_entry).build()
        JavaPlugin._symbols.extend(syms)
        return syms

    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        resolver = _JavaCallResolver(symbols, ast_data)
        return resolver.resolve()

    def build_field_access_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        """Extract field read/write edges from Java AST."""
        edges: list[Edge] = []
        ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
        by_simple: dict[str, list[Symbol]] = {}
        for s in symbols:
            by_simple.setdefault(s.name, []).append(s)

        method_types = ("method_declaration",)
        class_types = ("class_declaration", "interface_declaration", "enum_declaration")

        def find_method_node(ast: dict, sym: Symbol) -> Optional[dict]:
            for n in _find_nodes(ast, "method_declaration"):
                id_node = _first_child(n, "identifier")
                if id_node and _get_text(id_node) == sym.name and n["start"][0] == sym.start[0]:
                    return n
            return None

        def find_class_node(ast: dict, sym: Symbol) -> Optional[dict]:
            for n in (_find_nodes(ast, "class_declaration") +
                      _find_nodes(ast, "interface_declaration") +
                      _find_nodes(ast, "enum_declaration")):
                id_node = _first_child(n, "identifier")
                if id_node and _get_text(id_node) == sym.name and n["start"][0] == sym.start[0]:
                    return n
            return None

        def last_child(node: dict, *types) -> Optional[dict]:
            result = None
            for c in node.get("children", []):
                if c["type"] in types:
                    result = c
            return result

        def receiver_node(call_node: dict) -> Optional[dict]:
            children = call_node.get("children", [])
            for i, c in enumerate(children):
                if c["type"] == "argument_list" and i >= 3 and children[i - 2]["type"] == ".":
                    receiver = children[i - 3]
                    if receiver["type"] == "identifier":
                        return receiver
            return None

        for sym in symbols:
            if sym.kind != "method":
                continue
            ast = ast_by_file.get(sym.file)
            if ast is None:
                continue
            method_node = find_method_node(ast, sym)
            if method_node is None:
                continue

            write_node_ids: set[int] = set()
            for assign in _find_nodes(method_node, "assignment_expression"):
                children = assign.get("children", [])
                lhs = children[0] if children else None
                if lhs and lhs["type"] in ("field_access", "identifier"):
                    write_node_ids.add(id(lhs))

            write_receiver_ids: set[int] = set()
            for call in _find_nodes(method_node, "method_invocation"):
                if receiver_node(call) is not None:
                    write_receiver_ids.add(id(call))

            caller_class = sym.scope

            field_access_ids: set[int] = set()
            for fa in _find_nodes(method_node, "field_access"):
                field_access_ids.add(id(fa))

            for fa in _find_nodes(method_node, "field_access"):
                field_ident = last_child(fa, "identifier")
                if field_ident is None:
                    continue
                field_name = _get_text(field_ident)
                is_write = id(fa) in write_node_ids
                for cand in by_simple.get(field_name, []):
                    if cand.kind != "field" or cand.scope != caller_class:
                        continue
                    edges.append(Edge(
                        kind="writes" if is_write else "reads",
                        from_qname=sym.qualified_name,
                        to_qname=cand.qualified_name,
                        file=sym.file,
                        line=fa["start"][0],
                    ))

            for ident in _find_nodes(method_node, "identifier"):
                if ident.get("type") != "identifier" or id(ident) in field_access_ids:
                    continue
                field_name = _get_text(ident)
                is_write = id(ident) in write_node_ids or id(ident) in write_receiver_ids
                for cand in by_simple.get(field_name, []):
                    if cand.kind != "field" or cand.scope != caller_class:
                        continue
                    edges.append(Edge(
                        kind="writes" if is_write else "reads",
                        from_qname=sym.qualified_name,
                        to_qname=cand.qualified_name,
                        file=sym.file,
                        line=ident["start"][0],
                    ))

        return edges

    def build_instantiation_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        """Extract instantiation edges (new Foo()) from Java AST."""
        edges: list[Edge] = []
        ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
        by_simple: dict[str, list[Symbol]] = {}
        for s in symbols:
            by_simple.setdefault(s.name, []).append(s)

        def find_method_node(ast: dict, sym: Symbol) -> Optional[dict]:
            for n in _find_nodes(ast, "method_declaration"):
                id_node = _first_child(n, "identifier")
                if id_node and _get_text(id_node) == sym.name and n["start"][0] == sym.start[0]:
                    return n
            return None

        def best_candidates(simple_name: str, ref_qname: str) -> list[Symbol]:
            candidates = [c for c in by_simple.get(simple_name, []) if c.qualified_name != ref_qname]
            ref_p = _pkg(ref_qname)
            same_pkg = [c for c in candidates if _pkg(c.qualified_name) == ref_p]
            if same_pkg:
                return same_pkg
            return candidates if len(candidates) == 1 else []

        for sym in symbols:
            if sym.kind != "method":
                continue
            ast = ast_by_file.get(sym.file)
            if ast is None:
                continue
            method_node = find_method_node(ast, sym)
            if method_node is None:
                continue
            for new_node in _find_nodes(method_node, "object_creation_expression"):
                type_node = _first_child(new_node, "type_identifier", "generic_type")
                if type_node is None:
                    continue
                type_name = _get_text(type_node).split("<")[0]
                candidates = [c for c in best_candidates(type_name, sym.qualified_name)
                             if c.kind in ("class", "enum")]
                if candidates:
                    for cand in candidates:
                        edges.append(Edge(
                            kind="instantiates",
                            from_qname=sym.qualified_name,
                            to_qname=cand.qualified_name,
                            file=sym.file,
                            line=new_node["start"][0],
                        ))
                else:
                    edges.append(Edge(
                        kind="instantiates",
                        from_qname=sym.qualified_name,
                        to_qname=f"ext::{type_name}",
                        file=sym.file,
                        line=new_node["start"][0],
                    ))

        return edges

    def build_import_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        """Generate import edges for Java files.

        Parses import_declaration nodes from each Java AST and generates
        'imports' edges from the importing file's package to the imported type.

        This feeds the Intra-Type classification in Stage 6, which requires
        'imports' kind edges to connect Java files into the cross-file graph.

        NOTE: from_qname uses the top-level class qualified_name instead of
        'file::{path}' because file nodes are excluded from nodes.jsonl in
        filtered mode, which causes the BFS prune to drop all these edges.
        """
        edges: list[Edge] = []

        # Build symbol index for resolving imported types
        by_simple: dict[str, list[Symbol]] = {}
        by_file: dict[str, list[Symbol]] = {}
        for s in symbols:
            by_simple.setdefault(s.name, []).append(s)
            by_file.setdefault(s.file, []).append(s)

        ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

        def _get_package(ast: dict) -> str:
            """Extract package name from the AST."""
            for node in (ast.get("children", []) if ast else []):
                if node.get("type") == "package_declaration":
                    name_node = None
                    for c in node.get("children", []):
                        ct = c.get("type", "")
                        if ct in ("scoped_identifier", "identifier"):
                            name_node = c
                            break
                    if name_node:
                        return _get_text(name_node)
            return ""

        for file_path, ast in ast_by_file.items():
            # Determine the package that "owns" this file for the import edge from_qname
            pkg = _get_package(ast)
            if not pkg:
                # Fallback: derive from file path for src/main/java layout
                parts = file_path.replace("\\", "/").split("/")
                pkg_parts = []
                seen_src = False
                for p in parts:
                    if p in ("src", "main", "java", "kotlin"):
                        seen_src = True
                        continue
                    if seen_src and p and p[0].islower():
                        pkg_parts.append(p)
                pkg = ".".join(pkg_parts)

            file_symbols = by_file.get(file_path, [])
            # Prefer the top-level public class as the from_qname (more specific than package)
            top_class = None
            for sym in file_symbols:
                if sym.kind in ("class", "interface", "enum") and "inner" not in (sym.modifiers or []):
                    top_class = sym
                    break

            # Determine the from_qname: use top-level class if available, else package
            if top_class:
                from_qname = top_class.qualified_name
            elif pkg:
                from_qname = pkg
            else:
                from_qname = f"file::{file_path}"

            for imp_node in _find_nodes(ast, "import_declaration"):
                children = imp_node.get("children", [])
                # import_declaration: ['import', 'scoped_identifier'/'identifier', ';']
                # The actual imported path is the identifier part (skip 'import' keyword)
                ident_node = None
                for c in children:
                    ct = c.get("type", "")
                    if ct in ("scoped_identifier", "identifier"):
                        ident_node = c
                        break
                if ident_node is None:
                    continue

                imported_qname = _get_text(ident_node)
                if not imported_qname:
                    continue

                # Check if it's a static import (.* or .member)
                is_static = any(c.get("type") == "static" for c in children)
                is_wildcard = any(c.get("type") == "*" for c in children)

                # Normalize: strip trailing .* for wildcard imports
                if is_wildcard and imported_qname.endswith(".*"):
                    imported_qname = imported_qname[:-2]

                line = imp_node["start"][0]

                # Try to resolve to a project symbol first
                simple_name = imported_qname.split(".")[-1]
                candidates = by_simple.get(simple_name, [])

                # Filter: prefer same-package imports, skip external packages
                project_candidates = [c for c in candidates if not _is_external_package(c.qualified_name)]
                if project_candidates:
                    resolved = project_candidates[0]
                    edges.append(Edge(
                        kind="imports",
                        from_qname=from_qname,
                        to_qname=resolved.qualified_name,
                        file=file_path,
                        line=line,
                    ))
                # NOTE: We intentionally do NOT generate an edge for unresolved
                # project-internal imports (the "elif" branch). The ext:: prefix
                # causes these edges to be stripped by downstream filters, so
                # they never reach Stage 6. Skipping them entirely is cleaner.
                # External package imports are already skipped above.

        return edges

    def build_extends_implements_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate extends/implements edges for Java class declarations.

        Parses class/interface declarations to find superclass and implemented
        interfaces, generating 'java_extends' / 'java_implements' edges.
        These feed the Intra-Type classification in Stage 6.
        """
        edges: list[Edge] = []

        by_simple: dict[str, list[Symbol]] = {}
        by_qname: dict[str, Symbol] = {}
        for s in symbols:
            by_qname[s.qualified_name] = s
            by_simple.setdefault(s.name, []).append(s)

        ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

        def best_candidates(simple_name: str, ref_qname: str) -> list[Symbol]:
            candidates = [c for c in by_simple.get(simple_name, [])
                         if c.qualified_name != ref_qname]
            ref_pkg = _pkg(ref_qname)
            same_pkg = [c for c in candidates if _pkg(c.qualified_name) == ref_pkg]
            if same_pkg:
                return same_pkg
            return candidates if len(candidates) == 1 else []

        for sym in symbols:
            if sym.kind not in ("class", "interface", "enum"):
                continue
            ast = ast_by_file.get(sym.file)
            if ast is None:
                continue
            cls_node = _find_class_node_for_inheritance(ast, sym)
            if cls_node is None:
                continue

            line = cls_node["start"][0]

            for child in cls_node.get("children", []):
                ct = child.get("type", "")

                # superclass: class Foo extends Bar
                if ct == "superclass":
                    for c in child.get("children", []):
                        if c.get("type") in ("type_identifier", "generic_type",
                                             "scoped_identifier", "identifier"):
                            name = _get_text(c).split("<")[0]
                            if not name:
                                continue
                            candidates = best_candidates(name, sym.qualified_name)
                            _emit_inheritance_edges(
                                edges, sym, name, "java_extends", candidates, sym.file, line
                            )
                            break
                    continue

                # super_interfaces: class Foo implements Bar1, Bar2
                if ct == "super_interfaces":
                    type_list_node = None
                    for c in child.get("children", []):
                        if c.get("type") == "type_list":
                            type_list_node = c
                            break
                        if c.get("type") in ("type_identifier", "generic_type",
                                            "scoped_identifier", "identifier"):
                            name = _get_text(c).split("<")[0]
                            if name:
                                candidates = best_candidates(name, sym.qualified_name)
                                _emit_inheritance_edges(
                                    edges, sym, name, "java_implements", candidates, sym.file, line
                                )
                    if type_list_node:
                        for iface in type_list_node.get("children", []):
                            iface_name = None
                            if iface.get("type") in ("type_identifier", "identifier",
                                                     "scoped_identifier", "generic_type"):
                                iface_name = _get_text(iface).split("<")[0]
                            else:
                                for c in iface.get("children", []):
                                    if c.get("type") in ("type_identifier", "identifier",
                                                        "scoped_identifier", "generic_type"):
                                        iface_name = _get_text(c).split("<")[0]
                                        break
                            if iface_name:
                                candidates = best_candidates(iface_name, sym.qualified_name)
                                _emit_inheritance_edges(
                                    edges, sym, iface_name, "java_implements",
                                    candidates, sym.file, line
                                )

        return edges

    def build_inner_class_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate inner_class edges for Java nested classes."""
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

    def get_framework_annotations(self) -> dict[str, str]:
        return {
            "@Execute": "struts.action",
            "@ActionForm": "struts.form",
            "@Resource": "di.inject",
            "@Autowired": "spring.inject",
            "@Service": "spring.service",
            "@Repository": "spring.repository",
            "@Controller": "spring.controller",
            "@RestController": "spring.rest_controller",
            "@RequestMapping": "spring.mapping",
            "@GetMapping": "spring.get_mapping",
            "@PostMapping": "spring.post_mapping",
            "@Entity": "jpa.entity",
            "@Table": "jpa.table",
            "@Column": "jpa.column",
            "@Id": "jpa.id",
            "@Test": "test.case",
            "@BeforeEach": "test.setup",
            "@AfterEach": "test.teardown",
        }

    def infer_constructors(self) -> dict[str, str]:
        result = {}
        for sym in JavaPlugin._symbols:
            if sym.kind == "class":
                result[sym.qualified_name] = sym.name
        return result

    def get_entry_point_names(self) -> list[str]:
        return ["main"]

    def get_control_flow_hints(self, sym: dict) -> Optional[str]:
        name = sym.get("name", "")
        if name == "<clinit>":
            return "startup_init"
        return None


# ── self-register ─────────────────────────────────────────────────────────────

register(JavaPlugin)
