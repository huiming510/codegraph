"""C++ language plugin — supports C++ source files via tree-sitter-cpp.

This plugin handles:
- C++ source files (.cpp, .cc, .cxx)
- C++ header files (.hpp, .hh, .hxx)

Pure C files (.c, .h) are handled by the separate CPlugin.

It extracts:
- Classes and structs
- Functions and methods
- Fields (member variables)
- Parameters
- Local/global variables
- Type aliases (typedef, using)
- Namespaces
- Template declarations
- Preprocessor macros (as annotations)

It generates:
- call edges for function/method invocations
- contains edges for members inside types
- extends edges for inheritance
- imports edges for #include directives
- template_include edges for #include with angle brackets
"""

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser
from tqdm import tqdm

import tree_sitter_cpp as tscpp

from ._register_helper import register
from ...common.base import Edge, LanguagePlugin, Symbol


_CPP_LANGUAGE = Language(tscpp.language())
_CPP_PARSER = Parser(_CPP_LANGUAGE)


# ── tree helpers ────────────────────────────────────────────────────────────────

def _get_text(node: dict, default: str = "") -> str:
    """Recursively extract text from a node, falling back to children."""
    if node.get("text") not in (None, ""):
        return node["text"]
    parts = []
    for c in node.get("children", []):
        parts.append(_get_text(c))
    result = "".join(parts)
    return result if result else default


def _first_child(node: dict, *types) -> Optional[dict]:
    """Return the first child matching one of the given types."""
    for c in node.get("children", []):
        if c["type"] in types:
            return c
    return None


def _children_of_type(node: dict, *types) -> list[dict]:
    """Return all direct children matching one of the given types."""
    return [c for c in node.get("children", []) if c["type"] in types]


def _find_nodes(node: dict, node_type: str) -> list[dict]:
    """Recursively find all descendant nodes of a given type."""
    found = []
    if node.get("type") == node_type:
        found.append(node)
    for c in node.get("children", []):
        found.extend(_find_nodes(c, node_type))
    return found


def _collect_calls(node: dict, results: list) -> None:
    """Recursively collect call_expression nodes."""
    if node.get("type") == "call_expression":
        results.append(node)
    for c in node.get("children", []):
        _collect_calls(c, results)


def _collect_field_accesses(node: dict, results: list) -> None:
    """Recursively collect field_access nodes."""
    if node.get("type") == "field_access":
        results.append(node)
    for c in node.get("children", []):
        _collect_field_accesses(c, results)


def _is_in_type(node: dict) -> bool:
    """Return True if this node is nested inside a struct_specifier or class_specifier body."""
    parent = node.get("_parent")
    while parent:
        t = parent.get("type", "")
        if t in ("struct_specifier", "class_specifier", "enum_specifier"):
            return True
        parent = parent.get("_parent")
    return False


def _is_cpp_header_file(file_path: str) -> bool:
    """Return True if this is a C++ header file (.hpp, .hh, .hxx)."""
    ext = Path(file_path).suffix.lower()
    return ext in (".hpp", ".hh", ".hxx")


# ── namespace / scope inference ─────────────────────────────────────────────────

def _infer_namespace(file_path: str, src_root: str) -> str:
    """Infer a dotted namespace from the file path.

    For header files, uses the parent directories to create a namespace-like path.
    For source files, uses the directory structure as the module path.

    e.g.  src_root="project/src", file="project/src/foo/bar.hpp"
          → "foo.bar"
    e.g.  src_root="project", file="project/utils.cpp"
          → "utils"
    """
    try:
        abs_root = Path(src_root).resolve()
        abs_file = Path(file_path).resolve()
        rel = abs_file.relative_to(abs_root)
        parts = list(rel.parts)
        ext = Path(file_path).suffix.lower()

        if ext in (".hpp", ".hh", ".hxx"):
            if parts[-1].startswith("pch.") or parts[-1].startswith("stdafx."):
                parts = parts[:-1]
        else:
            if parts[-1].endswith((".cpp", ".cc", ".cxx")):
                parts[-1] = parts[-1].rsplit(".", 1)[0]

        return ".".join(parts)
    except (ValueError, OSError):
        return Path(file_path).stem


# ── symbol builder ─────────────────────────────────────────────────────────────

class _CppSymbolBuilder:
    """Builds Symbol list from a C++ AST entry."""

    def __init__(self, ast_entry: dict, src_root: str = ""):
        self.entry = ast_entry
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._file: str = ast_entry["file"]
        self._src_root = src_root
        self._namespace = _infer_namespace(self._file, src_root)
        self._is_header = _is_cpp_header_file(self._file)
        self._is_in_class_body = False
        self._current_access: str = "private"

    def _current_scope(self) -> str:
        parts = [p for p in [self._namespace, *self._scope_stack] if p]
        return ".".join(parts) if parts else self._namespace

    def _qualified(self, name: str) -> str:
        parts = [p for p in [self._namespace, *self._scope_stack, name] if p]
        return ".".join(parts)

    def _push(self, name: str) -> None:
        self._scope_stack.append(name)

    def _pop(self) -> None:
        if self._scope_stack:
            self._scope_stack.pop()

    def _collect_line_comments(self, node: dict) -> Optional[str]:
        """Extract the first line comment preceding or inside a node."""
        for c in node.get("children", []):
            if c.get("type") in ("comment", "line_comment"):
                text = _get_text(c).lstrip("//").strip()
                if text:
                    return text
        return None

    def _collect_modifiers(self, node: dict) -> tuple[list[str], list[str]]:
        """Extract access modifiers and annotations from a node.

        Returns (modifiers, annotations).
        Modifiers include: public, private, protected, static, const, virtual,
                           override, final, inline, extern, constexpr, mutable, abstract.
        Annotations include: preprocessor macros on the preceding line.
        """
        modifiers: list[str] = []
        annotations: list[str] = []

        for c in node.get("children", []):
            t = c["type"]
            if t in (
                "public", "private", "protected",
                "static", "virtual", "inline", "extern",
                "constexpr", "mutable", "final", "override",
                "const", "volatile", "auto", "register", "thread_local",
            ):
                modifiers.append(t)
            elif t == "attribute":
                annotations.append("@" + _get_text(c).strip())
            elif t == "attribute_declaration":
                annotations.append("@attr:" + _get_text(c).strip())

        return modifiers, annotations

    def _extract_storage_class(self, node: dict) -> list[str]:
        """Extract storage class specifiers."""
        result = []
        for c in node.get("children", []):
            if c["type"] in ("static", "extern", "register", "thread_local", "constexpr"):
                result.append(c["type"])
        return result

    def _type_text(self, type_node: Optional[dict]) -> str:
        """Extract a readable type name from a type node."""
        if type_node is None:
            return ""
        return _get_text(type_node).strip()

    def _get_return_type(self, node: dict) -> Optional[str]:
        """Extract return type from a function/method definition node."""
        for c in node.get("children", []):
            t = c["type"]
            if t in (
                "primitive_type", "type_identifier", "sized_type_specifier",
                "type_descriptor", "qualified_identifier", "generic_type",
                "pointer_type", "reference_type", "const_type", "volatile_type",
            ):
                return self._type_text(c)
            if t == "function_declarator":
                declarator = _first_child(c, "function_declarator")
                if declarator:
                    return self._get_return_type(declarator)
        return None

    def _visit(self, node: dict, parent: Optional[dict] = None) -> None:
        node["_parent"] = parent
        t = node.get("type", "")

        if t == "linkage_specification":
            for c in node.get("children", []):
                self._visit(c, node)
            return

        if t == "namespace_definition":
            name_node = _first_child(node, "namespace_identifier", "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            if name == "<anon>":
                for c in node.get("children", []):
                    self._visit(c, node)
                return
            self.symbols.append(Symbol(
                name=name,
                kind="namespace",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                lang="cpp",
            ))
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        if t == "struct_specifier":
            self._visit_type(node, parent, "struct")
            return

        if t == "class_specifier":
            self._visit_type(node, parent, "class")
            return

        if t == "enum_specifier":
            name_node = _first_child(node, "type_identifier", "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            if name == "<anon>":
                for c in node.get("children", []):
                    self._visit(c, node)
                return

            underlying = None
            base = _first_child(node, "type_identifier")
            if base:
                underlying = _get_text(base)

            doc = self._collect_line_comments(node)
            sym = Symbol(
                name=name,
                kind="enum",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=underlying,
                docstring=doc,
                lang="cpp",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        if t == "type_alias_declaration":
            name_node = _first_child(node, "type_identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            aliased = None
            for c in node.get("children", []):
                if c["type"] not in ("using", "typedef", "type_identifier", "="):
                    aliased = self._type_text(c)
                    break
            self.symbols.append(Symbol(
                name=name,
                kind="typedef",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=aliased,
                lang="cpp",
            ))
            return

        if t == "alias_declaration":
            name_node = _first_child(node, "type_identifier", "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            aliased = None
            for c in node.get("children", []):
                if c["type"] not in ("using", "type_identifier", "=", "primitive_type", ";"):
                    aliased = self._type_text(c)
                    break
            self.symbols.append(Symbol(
                name=name,
                kind="typedef",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=aliased,
                lang="cpp",
            ))
            return

        if t == "function_definition":
            self._visit_function(node, parent)
            return

        if t == "declaration":
            self._visit_declaration(node, parent)
            return

        if t == "field_declaration":
            self._visit_declaration(node, parent)
            return

        if t == "template_declaration":
            for c in node.get("children", []):
                if c["type"] not in ("template",):
                    self._visit(c, node)
            return

        if t == "enumerator":
            name_node = _first_child(node, "identifier", "field_identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            if name and name != "<anon>":
                self.symbols.append(Symbol(
                    name=name,
                    kind="variable",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    type_hint=None,
                    lang="cpp",
                ))
            return

        # Generic fallback: recurse into children for unhandled node types.
        for c in node.get("children", []):
            self._visit(c, node)

    def _visit_type(self, node: dict, parent: Optional[dict], kind: str) -> None:
        """Handle struct_specifier or class_specifier nodes."""
        name_node = _first_child(node, "type_identifier")
        name = _get_text(name_node) if name_node else "<anon>"
        if name == "<anon>":
            for c in node.get("children", []):
                self._visit(c, node)
            return

        mods, anns = self._collect_modifiers(node)
        doc = self._collect_line_comments(node)

        is_template = False
        for c in node.get("children", []):
            if c["type"] == "base_class_clause":
                for bc in c.get("children", []):
                    bc_t = bc.get("type", "")
                    if bc_t == "type_identifier":
                        base_name = _get_text(bc)
                        self.symbols.append(Symbol(
                            name=name,
                            kind=kind,
                            qualified_name=self._qualified(name),
                            file=self._file,
                            start=tuple(node["start"]),
                            end=tuple(node["end"]),
                            scope=self._current_scope(),
                            annotations=["extends:" + base_name],
                            docstring=doc,
                            lang="cpp",
                        ))
                        break

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
            docstring=doc,
            lang="cpp",
        )
        self.symbols.append(sym)

        if self._scope_stack:
            sym.modifiers = list(sym.modifiers) + ["inner"]

        self._push(name)
        old_access = self._current_access
        self._current_access = "public" if kind == "struct" else "private"

        class_body_found = False
        for c in node.get("children", []):
            ct = c["type"]
            if ct in ("public_clause", "private_clause", "protected_clause"):
                self._current_access = ct.rsplit("_", 1)[0]
            elif ct in ("field_declaration", "function_definition",
                        "declaration", "friend_declaration", "template_declaration",
                        "type_alias_declaration", "constructor_initializer",
                        "qualified_identifier"):
                self._visit(c, node)
            elif ct == "base_class_clause":
                pass
            elif ct in ("comment", "line_comment"):
                pass
            elif ct == "type_identifier" and not class_body_found:
                class_body_found = True
            elif ct == "class_body":
                class_body_found = True
                for member in c.get("children", []):
                    self._visit(member, node)
            elif ct == "field_declaration_list":
                class_body_found = True
                for member in c.get("children", []):
                    self._visit(member, node)

        self._current_access = old_access
        self._pop()

    def _visit_function(self, node: dict, parent: Optional[dict]) -> None:
        """Handle function_definition nodes (both free functions and methods)."""
        decl = _first_child(node, "function_declarator", "pointer_declarator",
                            "reference_declarator")
        if decl is None:
            for c in node.get("children", []):
                self._visit(c, node)
            return

        while decl.get("type") in ("pointer_declarator", "reference_declarator", "parenthesized_declarator", "qualified_identifier"):
            inner = _first_child(decl, "function_declarator", "pointer_declarator",
                                 "reference_declarator", "identifier", "qualified_identifier")
            if inner:
                decl = inner
            else:
                break

        # Unwrap qualified_identifier (e.g. "PFinNormal::SetHappyHourItem")
        # so we can extract the real method name and its containing class.
        _qual_class_name: Optional[str] = None
        _qual_method_name: Optional[str] = None
        _unwrapped = decl
        while _unwrapped.get("type") == "qualified_identifier":
            children = _unwrapped.get("children", [])
            if len(children) >= 2:
                _qual_class_name = _get_text(children[0])
                _qual_method_name = _get_text(children[-1])
                # Re-fetch the declarator by finding the inner function_declarator
                _unwrapped = _first_child(decl, "function_declarator", "pointer_declarator",
                                          "reference_declarator") or decl
            else:
                break

        name_node = _first_child(_unwrapped, "identifier", "field_identifier",
                                 "pointer_declarator", "reference_declarator")
        if name_node and name_node.get("type") in ("pointer_declarator", "reference_declarator"):
            name_node = _first_child(name_node, "identifier", "field_identifier")

        name = _get_text(name_node) if name_node else "<anon>"

        # If we extracted method name from qualified_identifier, use it
        if _qual_method_name and _qual_method_name != "<anon>":
            name = _qual_method_name

        if name.startswith("operator") and name_node:
            raw = _get_text(name_node)
            name = raw.strip()

        if name == "<anon>":
            for c in node.get("children", []):
                self._visit(c, node)
            return

        # A qualified function (ClassName::method) is always a method.
        # If the qualifier matches our current scope, treat it as a method too.
        is_method = _is_in_type(node) or (
            _qual_class_name is not None
            and _qual_class_name == self._namespace.split(".")[-1]
        )
        kind = "method" if is_method else "function"

        ret_type = self._get_return_type(node)
        mods, anns = self._collect_modifiers(node)

        if name.startswith("~"):
            kind = "method"
            ret_type = None

        doc = self._collect_line_comments(node)

        # For out-of-class qualified definitions (ClassName::method),
        # set the scope to the qualifying class so the qname is correct.
        _effective_scope = self._current_scope()
        if _qual_class_name and is_method:
            _effective_scope = (
                self._namespace.rsplit(".", 1)[0] + "." + _qual_class_name
                if "." in self._namespace
                else _qual_class_name
            )

        sym = Symbol(
            name=name,
            kind=kind,
            qualified_name=".".join([p for p in [_effective_scope, name] if p]),
            file=self._file,
            start=tuple(node["start"]),
            end=tuple(node["end"]),
            scope=_effective_scope,
            type_hint=ret_type,
            modifiers=mods,
            annotations=anns,
            docstring=doc,
            lang="cpp",
        )
        self.symbols.append(sym)
        self._push(name)
        for c in node.get("children", []):
            if c["type"] == "parameter_list":
                self._visit_parameters(c)
            elif c["type"] == "compound_statement":
                for stmt in c.get("children", []):
                    self._visit(stmt, node)
            else:
                self._visit(c, node)
        self._pop()

    def _visit_declaration(self, node: dict, parent: Optional[dict]) -> None:
        """Handle declaration nodes (global variables, function prototypes, etc.)."""
        type_node: Optional[dict] = None
        declarators: list[dict] = []

        for c in node.get("children", []):
            ct = c["type"]
            if ct in (
                "primitive_type", "type_identifier", "sized_type_specifier",
                "type_descriptor", "qualified_identifier", "generic_type",
                "const_type", "volatile_type", "auto",
            ):
                type_node = c
            elif ct == "init_declarator":
                declarators.append(c)
            elif ct == "declarator":
                declarators.append(c)
            elif ct == "pointer_declarator":
                declarators.append(c)
            elif ct == "reference_declarator":
                declarators.append(c)
            elif ct in ("identifier", "field_identifier"):
                declarators.append(c)

        type_text = self._type_text(type_node)
        storage = self._extract_storage_class(node)
        mods, anns = self._collect_modifiers(node)
        mods.extend(storage)

        for decl in declarators:
            decl_name_node = _first_child(decl, "identifier", "field_identifier",
                                          "pointer_declarator", "reference_declarator")
            if decl_name_node and decl_name_node.get("type") in ("pointer_declarator", "reference_declarator"):
                decl_name_node = _first_child(decl_name_node, "identifier", "field_identifier")

            decl_name = _get_text(decl_name_node) if decl_name_node else "<anon>"

            if decl_name.startswith("operator") or decl_name == "<anon>":
                continue

            if decl_name_node and decl_name_node.get("type") == "identifier":
                pass

            is_function = False
            for sub in decl.get("children", []):
                if sub["type"] in ("function_declarator", "pointer_declarator",
                                   "reference_declarator"):
                    is_function = True
                    break
                # qualified_identifier inside a pointer_declarator: "PFinNormal::method"
                if sub["type"] == "qualified_identifier":
                    is_function = True
                    break

            if is_function:
                continue

            is_class_level = _is_in_type(node)
            kind = "field" if is_class_level else "variable"

            self.symbols.append(Symbol(
                name=decl_name,
                kind=kind,
                qualified_name=self._qualified(decl_name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=type_text,
                modifiers=mods,
                annotations=anns,
                lang="cpp",
            ))

    def _visit_parameters(self, node: dict) -> None:
        """Handle parameter_list nodes."""
        for c in node.get("children", []):
            t = c["type"]
            if t == "parameter_declaration":
                ptype: Optional[str] = None
                pname = ""
                is_variadic = False

                for pc in c.get("children", []):
                    pct = pc["type"]
                    if pct in (
                        "primitive_type", "type_identifier", "sized_type_specifier",
                        "type_descriptor", "qualified_identifier", "generic_type",
                        "const_type", "volatile_type", "auto",
                    ):
                        ptype = self._type_text(pc)
                    elif pct == "identifier":
                        pname = _get_text(pc)
                    elif pct == "variadic_parameter":
                        is_variadic = True
                        pname = "..."

                if is_variadic:
                    continue
                if not pname or pname in ("this",):
                    continue

                self.symbols.append(Symbol(
                    name=pname,
                    kind="parameter",
                    qualified_name=self._qualified(pname),
                    file=self._file,
                    start=tuple(c["start"]),
                    end=tuple(c["end"]),
                    scope=self._current_scope(),
                    type_hint=ptype,
                    lang="cpp",
                ))

    def build(self) -> list[Symbol]:
        if self.entry.get("parse_error") or self.entry.get("ast") is None:
            return []
        self._visit(self.entry["ast"], None)

        self.symbols.append(Symbol(
            name=Path(self._file).stem,
            kind="module",
            qualified_name=self._namespace,
            file=self._file,
            start=(1, 0),
            end=(1, 0),
            scope=self._namespace.rsplit(".", 1)[0] if "." in self._namespace else "",
            lang="cpp",
        ))

        return self.symbols


# ── call edge resolver ─────────────────────────────────────────────────────────

class _CppCallResolver:
    """Resolves function/method call edges for C++."""

    def __init__(self, symbols: list[Symbol], ast_data: list[dict]):
        self.symbols = symbols
        self.ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

        self._by_simple: dict[str, list[Symbol]] = {}
        self._by_qname: dict[str, Symbol] = {}
        self._by_scope: dict[str, list[Symbol]] = {}
        self._methods_by_class: dict[str, list[Symbol]] = {}

        for s in symbols:
            self._by_qname[s.qualified_name] = s
            self._by_simple.setdefault(s.name, []).append(s)
            self._by_scope.setdefault(s.scope, []).append(s)
            if s.kind in ("struct", "class"):
                self._methods_by_class[s.qualified_name] = []

        for s in symbols:
            if s.kind == "method" and s.scope in self._methods_by_class:
                self._methods_by_class[s.scope].append(s)

    def _get_call_target(self, call_node: dict) -> tuple[Optional[str], Optional[str]]:
        """Return (callee_name, receiver_name) from a call_expression node.

        Examples:
            foo()         → ("foo", None)
            obj->method() → ("method", "obj")
            obj.method()  → ("method", "obj")
            A::static()   → ("static", "A")
            f(a, b)       → ("f", None)
        """
        children = call_node.get("children", [])
        for i, child in enumerate(children):
            if child.get("type") == "argument_list":
                if i == 0:
                    return None, None
                target = children[i - 1]
                tn = target.get("type", "")

                if tn == "identifier":
                    return _get_text(target), None

                if tn == "field_expression":
                    parts = target.get("children", [])
                    if len(parts) >= 2:
                        receiver = parts[0]
                        method = parts[-1]
                        return _get_text(method), _get_text(receiver)
                    return None, None

                if tn == "pointer_expression":
                    parts = target.get("children", [])
                    if len(parts) >= 2:
                        receiver = parts[0]
                        method = parts[-1]
                        return _get_text(method), _get_text(receiver)
                    return None, None

                if tn == "qualified_identifier":
                    parts = target.get("children", [])
                    if len(parts) >= 2:
                        receiver = parts[0]
                        method = parts[-1]
                        return _get_text(method), _get_text(receiver)
                    return None, None

                if tn == "call_expression":
                    return None, None

                if tn == "builtin_function_call_expression":
                    return _get_text(target), None

                return None, None

        return None, None

    def _find_function_node(self, ast: dict, name: str, line: int) -> Optional[dict]:
        """Find a function_definition node matching name and line."""
        for n in _find_nodes(ast, "function_definition"):
            decl = _first_child(n, "function_declarator", "pointer_declarator",
                                "reference_declarator")
            if decl is None:
                continue
            while decl.get("type") in ("pointer_declarator", "reference_declarator"):
                inner = _first_child(decl, "function_declarator", "pointer_declarator",
                                     "reference_declarator", "identifier")
                if inner:
                    decl = inner
                else:
                    break
            id_node = _first_child(decl, "identifier", "field_identifier")
            if id_node and _get_text(id_node) == name and n["start"][0] == line:
                return n
        return None

    def _resolve_call(
        self, callee: str, receiver: Optional[str], caller_scope: str,
        caller_file: str, line: int
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve a call to (qname, receiver_type, is_external)."""
        if callee in _CPP_BUILTINS:
            return None, None, True

        if receiver is None:
            candidates = self._by_simple.get(callee, [])
            same_scope = [c for c in candidates if c.scope == caller_scope]
            if same_scope:
                resolved = next((c for c in same_scope
                               if c.kind in ("function", "method", "class")), same_scope[0])
                return resolved.qualified_name, None, False

            caller_module = caller_scope.rsplit(".", 1)[0] if "." in caller_scope else caller_scope
            same_module = [
                c for c in candidates
                if (c.scope == caller_module or c.scope.startswith(caller_module + "."))
                and c.kind in ("function", "method", "class")
            ]
            if same_module:
                resolved = same_module[0]
                return resolved.qualified_name, None, False

            if candidates:
                resolved = next((c for c in candidates
                                if c.kind in ("function", "method", "class")), candidates[0])
                return resolved.qualified_name, None, True

            return None, None, True

        if receiver:
            candidates = self._by_simple.get(receiver, [])
            for c in candidates:
                if c.kind in ("variable", "field", "parameter") and c.type_hint:
                    class_name = c.type_hint.rstrip("*&").strip().split("::")[-1].split("<")[0]
                    methods = self._methods_by_class.get(
                        f"{c.scope.rsplit('.', 1)[0] if '.' in c.scope else c.scope}.{class_name}"
                    ) or self._methods_by_class.get(c.scope + "." + class_name)
                    if not methods:
                        for qname, meths in self._methods_by_class.items():
                            if qname.endswith("." + class_name) or qname.endswith("::" + class_name):
                                methods = meths
                                break
                    if methods:
                        for m in methods:
                            if m.name == callee:
                                return m.qualified_name, c.type_hint, False

            class_methods = self._methods_by_class.get(
                caller_scope.rsplit(".", 1)[0] if "." in caller_scope else caller_scope
            ) or []
            for m in class_methods:
                if m.name == callee:
                    return m.qualified_name, None, False

            candidates2 = self._by_simple.get(callee, [])
            if candidates2:
                resolved = next((c for c in candidates2
                                if c.kind in ("function", "method", "class")), None)
                if resolved:
                    return resolved.qualified_name, receiver, True

            return None, receiver, True

        return None, None, True

    def resolve(self) -> list[Edge]:
        edges: list[Edge] = []
        seen: set[tuple] = set()

        func_syms = [s for s in self.symbols if s.kind in ("function", "method")]
        for sym in tqdm(func_syms, desc="  Stage 4a calls", unit="func", ncols=80, leave=False):
            ast = self.ast_by_file.get(sym.file)
            if ast is None:
                continue

            func_node = self._find_function_node(ast, sym.name, sym.start[0])
            if func_node is None:
                continue

            call_nodes: list[dict] = []
            _collect_calls(func_node, call_nodes)

            for call in call_nodes:
                callee, receiver = self._get_call_target(call)
                if not callee:
                    continue

                qname, recv_type, is_ext = self._resolve_call(
                    callee, receiver, sym.scope, sym.file, call["start"][0]
                )

                if qname:
                    key = (sym.qualified_name, qname)
                    if key not in seen:
                        seen.add(key)
                        edges.append(Edge(
                            kind="call",
                            from_qname=sym.qualified_name,
                            to_qname=qname,
                            file=sym.file,
                            line=call["start"][0],
                            receiver=receiver,
                            receiver_type=recv_type,
                        ))
                else:
                    to_qname = f"ext::{callee}"
                    if recv_type:
                        to_qname = f"ext::{callee}@{recv_type}"
                    key = (sym.qualified_name, to_qname)
                    if key not in seen:
                        seen.add(key)
                        edges.append(Edge(
                            kind="call",
                            from_qname=sym.qualified_name,
                            to_qname=to_qname,
                            file=sym.file,
                            line=call["start"][0],
                            receiver=receiver,
                            receiver_type=recv_type,
                        ))

        return edges


# C++ standard library, STL, and common library functions
_CPP_BUILTINS = frozenset({
    # STL containers
    "string", "wstring", "u16string", "u32string",
    "vector", "list", "deque", "array", "forward_list",
    "map", "multimap", "set", "multiset",
    "unordered_map", "unordered_multimap", "unordered_set", "unordered_multiset",
    "stack", "queue", "priority_queue",
    "span", "optional", "variant", "any",
    "tuple", "pair",
    "bitset",

    # STL algorithms
    "begin", "end", "cbegin", "cend", "rbegin", "rend", "crbegin", "crend",
    "size", "ssize", "empty",
    "push_back", "pop_back", "push_front", "pop_front",
    "insert", "erase", "emplace", "emplace_back", "emplace_front", "emplace_hint",
    "find", "count", "lower_bound", "upper_bound", "equal_range",
    "get", "get_if", "make_tuple", "tie", "tuple_size",
    "min", "max", "minmax", "swap", "clamp",
    "sort", "stable_sort", "partial_sort", "nth_element",
    "binary_search", "lower_bound", "upper_bound",
    "merge", "inplace_merge",
    "reverse", "rotate", "shuffle", "random_shuffle",
    "unique", "remove", "remove_if",
    "fill", "iota", "generate", "transform",
    "all_of", "any_of", "none_of",
    "for_each", "for_each_n",
    "copy", "copy_if", "copy_n", "copy_backward",
    "move", "move_backward",
    "equal", "mismatch", "lexicographical_compare",
    "accumulate", "reduce", "inner_product",
    "adjacent_difference", "partial_sum",
    "replace", "replace_if", "replace_copy", "replace_copy_if",
    "fill_n", "generate_n", "search_n",
    "search", "find_end", "find_first_of",
    "min_element", "max_element", "minmax_element",

    # Smart pointers
    "make_shared", "make_unique",
    "shared_ptr", "unique_ptr", "weak_ptr", "auto_ptr",
    "static_pointer_cast", "dynamic_pointer_cast", "const_pointer_cast", "reinterpret_pointer_cast",

    # Memory
    "malloc", "calloc", "realloc", "free",
    "memcpy", "memmove", "memset", "memcmp", "memchr",
    "new", "delete", "new[]", "delete[]",
    "allocate", "deallocate", "construct", "destroy",
    "addressof", "align", "launder",

    # Type traits
    "is_same", "is_base_of", "is_convertible", "is_assignable",
    "is_pod", "is_trivial", "is_trivially_copyable", "is_standard_layout",
    "is_polymorphic", "is_abstract", "is_empty",
    "underlying_type", "decay", "remove_reference", "add_pointer",
    "remove_const", "remove_volatile", "remove_cv",
    "add_const", "add_volatile", "add_cv",
    "add_lvalue_reference", "add_rvalue_reference",
    "make_signed", "make_unsigned",
    "enable_if", "conditional", "common_type",
    "void_t", "type_identity",
    "integral_constant", "bool_constant",
    "true_type", "false_type",

    # RTTI
    "typeid", "dynamic_cast", "static_cast", "reinterpret_cast", "const_cast",

    # Exception
    "throw", "try", "catch",

    # I/O
    "cout", "cin", "cerr", "clog", "wcout", "wcin",
    "printf", "fprintf", "sprintf", "snprintf",
    "scanf", "fscanf", "sscanf",
    "endl", "flush", "fixed", "setprecision",
    "getline", "wsgetline", "get",

    # String
    "strlen", "strcmp", "strncmp", "strcpy", "strncpy",
    "strcat", "strncat", "strchr", "strrchr", "strstr",
    "string", "to_string", "to_wstring", "stoi", "stol", "stoll",
    "stoul", "stoull", "stof", "stod", "stold",
    "to_chars", "from_chars",

    # Functional
    "function", "bind", "mem_fn", "reference_wrapper",
    "invoke", "invoke_result", "result_of",
    "hash",
    "placeholders::_1", "placeholders::_2",

    # Threading
    "thread", "this_thread::sleep_for", "this_thread::sleep_until",
    "this_thread::yield",
    "mutex", "timed_mutex", "recursive_mutex", "recursive_timed_mutex",
    "lock_guard", "unique_lock", "shared_lock", "scoped_lock",
    "try_lock", "lock",
    "condition_variable", "condition_variable_any",
    "promise", "future", "shared_future", "packaged_task",
    "async", "launch::async", "launch::deferred",

    # Atomics
    "atomic", "atomic_flag", "atomic_thread_fence", "atomic_signal_fence",

    # Utility
    "move", "forward", "declval", "decltype",
    "sizeof", "alignof", "offsetof",
    "addressof", "as_const", "exchange", "make_pair", "make_tuple",
    "piecewise_construct", "piecewise_construct_t",

    # Initializer lists
    "initializer_list", "begin", "end",

    # Stream manipulators
    "setw", "setfill", "setprecision", "setbase", "setiosflags", "resetiosflags",
    "left", "right", "internal", "dec", "hex", "oct",
    "showbase", "noshowbase", "showpoint", "noshowpoint",
    "showpos", "noshowpos", "uppercase", "nouppercase",
    "skipws", "noskipws", "boolalpha", "noboolalpha",
    "unitbuf", "nounitbuf", "flush", "ends", "endl",

    # chrono
    "chrono::duration", "chrono::time_point",
    "chrono::seconds", "chrono::milliseconds", "chrono::microseconds", "chrono::nanoseconds",
    "chrono::hours", "chrono::minutes",
    "chrono::steady_clock", "chrono::system_clock", "chrono::high_resolution_clock",

    # Ratio
    "ratio", "ratio_add", "ratio_subtract", "ratio_multiply", "ratio_divide",

    # filesystem
    "filesystem::path", "filesystem::exists", "filesystem::create_directory",
    "filesystem::remove", "filesystem::copy",

    # Optional / Variant
    "std::nullopt", "std::bad_optional_access",
    "std::monostate", "std::bad_variant_access",
})


# ── import edge builder ────────────────────────────────────────────────────────

def _build_include_edges(symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
    """Generate imports edges from #include directives."""
    edges: list[Edge] = []
    seen: set[tuple] = set()

    module_to_file: dict[str, str] = {}
    module_qname_by_file: dict[str, str] = {}
    for s in symbols:
        if s.kind == "module":
            module_to_file[s.qualified_name] = s.file
            module_qname_by_file[s.file] = s.qualified_name

    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

    module_syms = [s for s in symbols if s.kind == "module"]
    for s in tqdm(module_syms, desc="  Stage 4b imports", unit="file", ncols=80, leave=False):

        ast = by_file.get(s.file)
        if ast is None:
            continue

        includes = _find_nodes(ast, "preproc_include")
        for inc in includes:
            header_name = None
            is_system = False
            for child in inc.get("children", []):
                ct = child.get("type", "")
                raw = child.get("text", "") or _get_text(child)
                if ct == "system_lib_string":
                    header_name = raw.strip("<>").strip()
                    is_system = True
                    break
                elif ct == "string_literal":
                    header_name = raw.strip('"').strip()
                    is_system = False
                    break
                elif ct == "header":
                    header_name = raw.strip('"<>').strip()
                    is_system = False
                    break

            if not header_name:
                continue

            kind = "template_include" if is_system else "imports"

            target_module = None

            normalized = header_name.strip("<>\"")
            if "/" in normalized:
                parts = normalized.split("/")
                normalized = ".".join(parts)
            else:
                normalized = normalized.replace("\\", ".")

            for mqname, mfile in module_to_file.items():
                mqname_lower = mqname.lower()
                normalized_lower = normalized.lower()
                if mqname_lower.endswith(f".{normalized_lower}") or mqname_lower == normalized_lower:
                    target_module = mqname
                    break
                fname_stem = Path(mfile).stem
                hdr_stem = Path(header_name.strip("<>\"")).stem
                if fname_stem.lower() == hdr_stem.lower():
                    target_module = mqname
                    break

            if target_module is None:
                target_module = f"ext::{header_name}"

            from_module = s.qualified_name
            key = (from_module, target_module)
            if key in seen:
                continue
            seen.add(key)

            edges.append(Edge(
                kind=kind,
                from_qname=from_module,
                to_qname=target_module,
                file=s.file,
                line=inc["start"][0] if inc.get("start") else 1,
            ))

    return edges


# ── plugin class ──────────────────────────────────────────────────────────────

class CppPlugin(LanguagePlugin):
    lang_id = "cpp"
    display_name = "C++"

    def get_file_patterns(self) -> list[str]:
        return [
            "*.cpp", "*.cc", "*.cxx",
            "*.hpp", "*.hh", "*.hxx",
        ]

    def get_tree_sitter_package(self) -> str:
        return "tree_sitter_cpp"

    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        return _CppSymbolBuilder(ast_entry, src_root).build()

    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        resolver = _CppCallResolver(symbols, ast_data)
        return resolver.resolve()

    def build_import_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        return _build_include_edges(symbols, ast_data)

    def build_extends_implements_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate extends edges for C++ class/struct inheritance.

        C++ uses 'class Child : public Base' or 'struct Child : public Base' syntax.
        Base classes are stored in 'base_class_clause' nodes.
        Pure virtual (abstract) bases are treated as interfaces (implements).
        """
        edges: list[Edge] = []

        # Build symbol lookups
        by_qname: dict[str, Symbol] = {s.qualified_name: s for s in symbols}
        by_simple: dict[str, list[Symbol]] = {}
        for s in symbols:
            by_simple.setdefault(s.name, []).append(s)

        # Build AST index by file
        ast_by_file: dict[str, dict] = {}
        for entry in ast_data:
            if entry.get("ast"):
                ast_by_file[entry["file"]] = entry["ast"]

        def best_candidates(simple_name: str, ref_qname: str) -> list[Symbol]:
            """Return candidates for simple_name, preferring same-namespace."""
            candidates = [c for c in by_simple.get(simple_name, [])
                         if c.qualified_name != ref_qname]
            # C++ namespaces: same namespace = same prefix
            ref_ns = ref_qname.rsplit("::", 1)[0] if "::" in ref_qname else ""
            same_ns = [c for c in candidates if c.qualified_name.startswith(ref_ns + "::")
                      or (not ref_ns and "::" not in c.qualified_name)]
            if same_ns:
                return same_ns
            return candidates if len(candidates) == 1 else []

        def find_class_nodes(ast: dict, results: list) -> None:
            """Find all class/struct declaration nodes in AST."""
            if ast.get("type") in ("class_specifier", "struct_specifier"):
                results.append(ast)
            for child in ast.get("children", []):
                find_class_nodes(child, results)

        for sym in symbols:
            if sym.kind not in ("class", "struct"):
                continue

            ast = ast_by_file.get(sym.file)
            if ast is None:
                continue

            # Find all class/struct nodes
            class_nodes = []
            find_class_nodes(ast, class_nodes)

            # Find the matching class node
            for cls_node in class_nodes:
                # Get class name
                name_node = None
                for child in cls_node.get("children", []):
                    if child.get("type") == "type_identifier":
                        name_node = child
                        break
                if name_node is None:
                    continue
                name = name_node.get("text", "")
                if name != sym.name:
                    continue

                line = cls_node.get("start", [1, 0])[0]

                # Find base_class_clause nodes
                for child in cls_node.get("children", []):
                    if child.get("type") == "base_class_clause":
                        # Parse base class list
                        for base_child in child.get("children", []):
                            if base_child.get("type") == "type_identifier":
                                base_name = base_child.get("text", "")
                                if base_name:
                                    candidates = best_candidates(base_name, sym.qualified_name)

                                    if candidates:
                                        for cand in candidates:
                                            edges.append(Edge(
                                                kind="extends",
                                                from_qname=sym.qualified_name,
                                                to_qname=cand.qualified_name,
                                                file=sym.file,
                                                line=line,
                                            ))
                                    else:
                                        edges.append(Edge(
                                            kind="extends",
                                            from_qname=sym.qualified_name,
                                            to_qname=f"ext::{base_name}",
                                            file=sym.file,
                                            line=line,
                                        ))
                break

        return edges

    def build_inner_class_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate inner_class edges for C++ nested classes/structs."""
        edges: list[Edge] = []
        by_qname: dict[str, Symbol] = {s.qualified_name: s for s in symbols}

        for sym in symbols:
            if sym.kind not in ("class", "struct"):
                continue
            if "inner" not in (sym.modifiers or []):
                continue

            qname = sym.qualified_name
            if "::" not in qname:
                continue

            outer_qname = qname.rsplit("::", 1)[0]
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
            "#define": "macro.define",
            "#ifdef": "macro.conditional",
            "#ifndef": "macro.conditional",
            "#if": "macro.conditional",
            "#pragma": "meta.pragma",
            "__attribute__": "meta.attribute",
            "__declspec": "meta.declspec",
            "Q_OBJECT": "qt.moc",
            "Q_GADGET": "qt.moc",
            "slots": "qt.slot",
            "signals": "qt.signal",
            "Q_INVOKABLE": "qt.moc",
            "MOC_INCLUDE": "qt.moc",
            "EMIT": "qt.signal",
            "Q_EMIT": "qt.signal",
        }

    def infer_constructors(self) -> dict[str, str]:
        return {}

    def get_entry_point_names(self) -> list[str]:
        return ["main"]

    def get_control_flow_hints(self, sym: dict) -> Optional[str]:
        name = sym.get("name", "")
        if name == "main":
            return "entry_point"
        return None


# ── self-register ─────────────────────────────────────────────────────────────

register(CppPlugin)
