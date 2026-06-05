"""Python language plugin — supports Python 3 source files via tree-sitter-python."""

import os
from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser

import tree_sitter_python as tspython
from tqdm import tqdm

from ._register_helper import register
from ...common.base import Edge, LanguagePlugin, Symbol


_PYTHON_LANGUAGE = Language(tspython.language())
_PYTHON_PARSER = Parser(_PYTHON_LANGUAGE)


# ── tree helpers ────────────────────────────────────────────────────────────────

def _get_text(node: dict, default: str = "") -> str:
    # tree-sitter may store text="" (empty string) on compressed nodes whose
    # children carry the actual text.  Only trust the pre-computed text when
    # it is a non-empty string.
    if node.get("text") not in (None, ""):
        return node["text"]
    parts = []
    for c in node.get("children", []):
        parts.append(_get_text(c))
    result = "".join(parts)
    return result if result else default


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


def _extract_docstring(func_or_class_node: dict) -> Optional[str]:
    """Extract docstring from a function_definition or class_definition node.

    Python docstrings are the first string expression inside the block body.
    Handles both single-line and multi-line string expressions.
    """
    for child in func_or_class_node.get("children", []):
        if child.get("type") == "block":
            first_stmt_list = child.get("children", [])
            if first_stmt_list:
                first_stmt = first_stmt_list[0]
                if first_stmt.get("type") == "expression_statement":
                    exprs = first_stmt.get("children", [])
                    if exprs and exprs[0].get("type") == "string":
                        raw = _get_text(exprs[0]).strip()
                        # Strip triple-quote prefixes/suffixes (""" or ''' or " or ')
                        for quote in ('"""', "'''", '"', "'"):
                            if raw.startswith(quote) and raw.endswith(quote) and len(quote) <= len(raw) // 2:
                                raw = raw[len(quote):-len(quote)]
                                break
                        return raw.strip()
    return None


def _collect_calls(method_node: dict, results: list) -> None:
    if method_node.get("type") == "call":
        results.append(method_node)
    for c in method_node.get("children", []):
        _collect_calls(c, results)


def _is_in_class(node: dict) -> bool:
    """Return True if this node is nested inside a class body.

    decorated_definition wrappers are skipped — they are AST artefacts, not scoping units.
    """
    parent = node.get("_parent")
    while parent:
        if parent.get("type") == "class_definition":
            return True
        if parent.get("type") == "decorated_definition":
            # decorated_definition is a wrapper. Its _parent points to the enclosing
            # scope (e.g. class body, module). We skip it and continue from there.
            parent = parent.get("_parent")
        else:
            parent = parent.get("_parent")
    return False


# ── module path resolution ─────────────────────────────────────────────────────

def _infer_module_path(file_path: str, src_root: str) -> str:
    """Infer a dotted module path from a file path.

    src_root = "project/src", file = "project/src/django/views/http.py"
        → "django.views.http"
    src_root = "project/src", file = "project/src/models.py"
        → "models"
    src_root = "project/src", file = "project/src/django/__init__.py"
        → "django"
    """
    try:
        abs_root = Path(src_root).resolve()
        abs_file = Path(file_path).resolve()
        rel = abs_file.relative_to(abs_root)
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        elif parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)
    except (ValueError, OSError):
        return Path(file_path).stem


# ── symbol builder ─────────────────────────────────────────────────────────────

class _PythonSymbolBuilder:
    """Builds Symbol list from a Python AST entry."""

    def __init__(self, ast_entry: dict, src_root: str = ""):
        self.entry = ast_entry
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._file: str = ast_entry["file"]
        self._src_root = src_root
        self._module_path = _infer_module_path(self._file, src_root)

    def _current_scope(self) -> str:
        """Return the fully-qualified current scope, including the module path prefix."""
        parts = [p for p in [self._module_path, *self._scope_stack] if p]
        return ".".join(parts)

    def _qualified(self, name: str) -> str:
        parts = [p for p in [self._module_path, *self._scope_stack, name] if p]
        return ".".join(parts)

    def _push(self, name: str) -> None:
        self._scope_stack.append(name)

    def _pop(self) -> None:
        if self._scope_stack:
            self._scope_stack.pop()

    def _collect_decorators(self, node: dict) -> list[str]:
        """Collect all decorators from this node and its ancestors.

        Python decorators live on the wrapper node (decorated_definition), not on
        the inner function_definition. We need to walk up the parent chain to find
        decorators for nested/decorated definitions.

        When the parent is NOT the decorated_definition itself (e.g., when _visit
        passes the grandparent), we check the function_definition's immediate
        preceding siblings for decorator nodes.
        """
        decorators: list[str] = []

        # Check immediate preceding siblings for decorator nodes.
        # In a decorated_definition, the structure is: [decorator*, function/class_definition]
        # When we visit the function_definition, its parent chain bypasses decorated_definition,
        # so we manually check its preceding siblings.
        parent_of_node = node.get("_parent")
        if parent_of_node and parent_of_node.get("type") != "decorated_definition":
            # We're in a child of decorated_definition but parent is the grandparent.
            # Check if the decorated_definition grandparent has any decorator children.
            if parent_of_node.get("_parent") and parent_of_node.get("_parent").get("type") == "decorated_definition":
                dd = parent_of_node.get("_parent")
                for child in dd.get("children", []):
                    if child.get("type") == "decorator":
                        decorators.append("@" + _get_text(child).lstrip("@"))

        # Collect from this node's immediate decorator children
        for d in node.get("children", []):
            if d.get("type") == "decorator":
                decorators.append("@" + _get_text(d).lstrip("@"))

        # Walk up ancestor chain for decorator nodes (handles nested decorated definitions)
        ancestor = node.get("_parent")
        while ancestor:
            if ancestor.get("type") == "decorated_definition":
                for d in ancestor.get("children", []):
                    if d.get("type") == "decorator":
                        decorators.append("@" + _get_text(d).lstrip("@"))
            ancestor = ancestor.get("_parent")
        return decorators

    def _visit(self, node: dict, parent: Optional[dict] = None) -> None:
        node["_parent"] = parent
        t = node.get("type", "")

        # Always collect decorators (including from ancestor decorated_definition nodes)
        decorators = self._collect_decorators(node)

        if t == "decorated_definition":
            # decorated_definition wraps function/class definitions with decorators.
            # We visit children with the decorated_definition as parent so:
            #   1. _is_in_class() skips over it to find the real class context
            #   2. _collect_decorators() can walk up to find decorator nodes
            for child in node.get("children", []):
                self._visit(child, node)
            return

        if t == "class_definition":
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            sym = Symbol(
                name=name,
                kind="class",
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                annotations=decorators,
                docstring=_extract_docstring(node),
                lang="python",
            )
            if self._scope_stack:
                sym.modifiers = ["inner"]
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        if t in ("function_definition", "async_function_definition"):
            is_method = _is_in_class(node)
            kind = "method" if is_method else "function"
            name_node = _first_child(node, "identifier")
            name = _get_text(name_node) if name_node else "<anon>"

            ret_type: Optional[str] = None
            for child in node.get("children", []):
                if child.get("type") == "annotation":
                    ret_type = _get_text(child)
                    if ret_type:
                        ret_type = ret_type.lstrip("->").strip()

            modifiers: list[str] = []
            if t == "async_function_definition":
                modifiers.append("async")
            # Map decorator names to modifier keywords
            for ann in decorators:
                stripped = ann.lstrip("@")
                if stripped.startswith("staticmethod"):
                    modifiers.append("staticmethod")
                elif stripped.startswith("classmethod"):
                    modifiers.append("classmethod")
                elif stripped.startswith("property"):
                    modifiers.append("property")
                elif stripped.startswith("abstractmethod"):
                    modifiers.append("abstract")

            docstring = _extract_docstring(node)

            sym = Symbol(
                name=name,
                kind=kind,
                qualified_name=self._qualified(name),
                file=self._file,
                start=tuple(node["start"]),
                end=tuple(node["end"]),
                scope=self._current_scope(),
                type_hint=ret_type,
                modifiers=modifiers,
                annotations=decorators,
                docstring=docstring,
                lang="python",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        if t == "assignment":
            for child in node.get("children", []):
                if child.get("type") == "lambda":
                    return
                for sub in child.get("children", []):
                    if sub.get("type") == "lambda":
                        return

            lhs_nodes = []
            for child in node.get("children", []):
                if child.get("type") in ("identifier", "attribute"):
                    lhs_nodes.append(child)
                elif child.get("type") == "=":
                    break

            rhs_type: Optional[str] = None
            for child in node.get("children", []):
                if child.get("type") == "type_annotation":
                    rhs_type = _get_text(child)
                    break

            for lhs in lhs_nodes:
                lhs_text = _get_text(lhs)
                if not lhs_text or lhs_text in ("self", "cls"):
                    continue
                is_class_level = not self._scope_stack and _is_in_class(node)
                kind = "field" if is_class_level else "variable"
                self.symbols.append(Symbol(
                    name=lhs_text,
                    kind=kind,
                    qualified_name=self._qualified(lhs_text),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    type_hint=rhs_type.lstrip(":").strip() if rhs_type else None,
                    annotations=decorators,
                    lang="python",
                ))
            return

        if t == "parameters":
            for child in node.get("children", []):
                if child.get("type") in (
                    "identifier", "typed_parameter",
                    "default_parameter", "typed_default_parameter"
                ):
                    raw = _get_text(child)
                    name = raw.split(":")[0].split("=")[0].strip()
                    if name and name != "self":
                        ptype: Optional[str] = None
                        if ":" in raw:
                            ptype = raw.split(":", 1)[1].strip().split("=", 1)[0].strip()
                        self.symbols.append(Symbol(
                            name=name,
                            kind="parameter",
                            qualified_name=self._qualified(name),
                            file=self._file,
                            start=tuple(node["start"]),
                            end=tuple(node["end"]),
                            scope=self._current_scope(),
                            type_hint=ptype,
                            lang="python",
                        ))
            return

        # import_from: from module import name [, name as alias, ...]
        # Also handles: from . import x  (relative import to sibling)
        #              from .. import x  (relative import to parent)
        #              from .submodule import x
        if t == "import_from_statement":
            children = node.get("children", [])
            module_prefix = ""
            is_relative = False
            rel_level = 0

            # Find the dotted_name (or relative dots) after 'from'
            for i, child in enumerate(children):
                ct = child.get("type", "")
                if ct == "dotted_name":
                    module_prefix = _get_text(child).replace("/", ".")
                    break
                elif ct == "relative_import":
                    # e.g. "." or ".." or "...pkg"
                    dots = child.get("text", "") or ""
                    rel_level = len(dots.rstrip("abcdefghijklmnopqrstuvwxyz_"))
                    remainder = dots[len("." * rel_level):]
                    if rel_level > 0:
                        is_relative = True
                        parent_parts = self._module_path.rsplit(".", rel_level)
                        if parent_parts:
                            module_prefix = parent_parts[0]
                        if remainder:
                            module_prefix = f"{module_prefix}.{remainder}" if module_prefix else remainder
                    break

            i = 0
            while i < len(children):
                child = children[i]
                ct = child.get("type", "")

                if ct == "identifier":
                    imported_name = child.get("text", "") or child.get("children", [{}])[0].get("text", "")
                    if not imported_name:
                        imported_name = _get_text(child)
                    alias = None
                    if i + 1 < len(children) and children[i + 1].get("type") == "as":
                        if i + 2 < len(children) and children[i + 2].get("type") == "identifier":
                            alias = _get_text(children[i + 2])
                            i += 2
                    local_name = alias if alias else imported_name
                    target_qname = f"{module_prefix}.{imported_name}" if module_prefix else imported_name

                    # Distinguish submodule imports from symbol imports.
                    # A submodule import (e.g. from database import crud) means the local
                    # name 'crud' refers to the *module* database.crud, not a symbol in it.
                    # We create a kind=module symbol so module_to_file() can resolve it.
                    is_submodule_import = not alias and _is_likely_submodule(imported_name, target_qname)

                    sym_kind = "module" if is_submodule_import else "import"
                    # For submodule imports, qualified_name IS the module path.
                    # For symbol imports, qualified_name points to the specific symbol.
                    sym_qname = target_qname if is_submodule_import else target_qname

                    self.symbols.append(Symbol(
                        name=local_name,
                        kind=sym_kind,
                        qualified_name=sym_qname,
                        file=self._file,
                        start=tuple(node["start"]),
                        end=tuple(node["end"]),
                        scope=self._current_scope(),
                        lang="python",
                    ))
                elif ct == "aliased_import":
                    # from x import y as z
                    dotted = _first_child(child, "dotted_name")
                    if dotted:
                        imported_name = _get_text(dotted)
                        alias = None
                        child_children = child.get("children", [])
                        for j, c2 in enumerate(child_children):
                            if c2.get("type") == "as" and j + 1 < len(child_children):
                                alias_child = child_children[j + 1]
                                if alias_child.get("type") == "identifier":
                                    alias = _get_text(alias_child)
                                    break
                        local_name = alias if alias else imported_name
                        target_qname = f"{module_prefix}.{imported_name}" if module_prefix else imported_name
                        is_submodule_import = not alias and _is_likely_submodule(imported_name, target_qname)
                        sym_kind = "module" if is_submodule_import else "import"
                        sym_qname = target_qname if is_submodule_import else target_qname
                        self.symbols.append(Symbol(
                            name=local_name,
                            kind=sym_kind,
                            qualified_name=sym_qname,
                            file=self._file,
                            start=tuple(node["start"]),
                            end=tuple(node["end"]),
                            scope=self._current_scope(),
                            lang="python",
                        ))
                elif ct == "dotted_name":
                    # from x import submodule (no alias, snake_case submodule)
                    imported_name = _get_text(child)
                    target_qname = f"{module_prefix}.{imported_name}" if module_prefix else imported_name
                    is_submodule_import = _is_likely_submodule(imported_name, target_qname)
                    sym_kind = "module" if is_submodule_import else "import"
                    sym_qname = target_qname if is_submodule_import else target_qname
                    self.symbols.append(Symbol(
                        name=imported_name,
                        kind=sym_kind,
                        qualified_name=sym_qname,
                        file=self._file,
                        start=tuple(node["start"]),
                        end=tuple(node["end"]),
                        scope=self._current_scope(),
                        lang="python",
                    ))
                elif ct == "wildcard_import":
                    self.symbols.append(Symbol(
                        name="*",
                        kind="import",
                        qualified_name=module_prefix + ".*" if module_prefix else "*",
                        file=self._file,
                        start=tuple(node["start"]),
                        end=tuple(node["end"]),
                        scope=self._current_scope(),
                        lang="python",
                    ))
                i += 1
            return

        # import_statement: import module [, module as alias, ...]
        if t == "import_statement":
            children = node.get("children", [])
            i = 0
            while i < len(children):
                child = children[i]
                if child.get("type") == "dotted_name":
                    module_path = _get_text(child).replace("/", ".")
                    alias = None
                    if i + 1 < len(children) and children[i + 1].get("type") == "as":
                        if i + 2 < len(children) and children[i + 2].get("type") == "identifier":
                            alias = _get_text(children[i + 2])
                            i += 2
                    name = alias if alias else module_path.split(".")[-1]
                    # import X means local 'X' refers to the module X
                    self.symbols.append(Symbol(
                        name=name,
                        kind="module",
                        qualified_name=module_path,
                        file=self._file,
                        start=tuple(node["start"]),
                        end=tuple(node["end"]),
                        scope=self._current_scope(),
                        lang="python",
                    ))
                i += 1
            return

        for c in node.get("children", []):
            self._visit(c, node)

    def build(self) -> list[Symbol]:
        if self.entry.get("parse_error") or self.entry.get("ast") is None:
            return []
        self._visit(self.entry["ast"], None)
        self.symbols.append(Symbol(
            name=self._module_path.rsplit(".", 1)[-1],
            kind="module",
            qualified_name=self._module_path,
            file=self._file,
            start=(1, 0),
            end=(1, 0),
            scope=self._module_path.rsplit(".", 1)[0] if "." in self._module_path else "",
            lang="python",
        ))
        return self.symbols


def _is_likely_submodule(name: str, qname: str) -> bool:
    """Guess whether 'name' is a submodule import rather than a symbol import.

    e.g. 'from database import crud' → crud is likely a submodule
         'from os import path' → path is likely a submodule
         'from datetime import datetime' → datetime is a class name (symbol)
    """
    if name[0].isupper():
        return False  # PascalCase → class or type (symbol)
    # snake_case or common short names → submodule
    return True


# ── Python builtins ────────────────────────────────────────────────────────────

_PYTHON_BUILTINS = frozenset({
    "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray",
    "bytes", "callable", "chr", "classmethod", "compile", "complex",
    "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec",
    "filter", "float", "format", "frozenset", "getattr", "globals",
    "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance",
    "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview",
    "min", "next", "object", "oct", "open", "ord", "pow", "print", "property",
    "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted",
    "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip",
    "BaseException", "Exception", "SystemExit", "KeyboardInterrupt",
    "GeneratorExit", "StopIteration", "ArithmeticError", "FloatingPointError",
    "OverflowError", "ZeroDivisionError", "AssertionError", "AttributeError",
    "BufferError", "EOFError", "ImportError", "ModuleNotFoundError",
    "IndexError", "KeyError", "LookupError", "MemoryError", "NameError",
    "UnboundLocalError", "OSError", "BlockingIOError", "ChildProcessError",
    "ConnectionError", "BrokenPipeError", "ConnectionAbortedError",
    "ConnectionRefusedError", "ConnectionResetError", "FileExistsError",
    "FileNotFoundError", "IsADirectoryError", "NotADirectoryError",
    "InterruptedError", "PermissionError", "ProcessLookupError",
    "TimeoutError", "ReferenceError", "RuntimeError", "NotImplementedError",
    "RecursionError", "IndentationError", "TabError", "SyntaxError",
    "SystemError", "TypeError", "ValueError", "UnicodeError",
    "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError",
    "Warning", "DeprecationWarning", "PendingDeprecationWarning",
    "RuntimeWarning", "SyntaxWarning", "ImportWarning", "FutureWarning",
    "frozenset", "bytearray", "memoryview",
})

_UNRESOLVABLE_RECEIVERS = frozenset({"self", "cls", "mcs", "s"})


# ── call edge resolver ─────────────────────────────────────────────────────────

_COMMON_PACKAGES = frozenset([
    "os", "sys", "re", "json", "time", "datetime", "collections", "itertools",
    "functools", "operator", "pathlib", "typing", "abc", "copy", "io", "pickle",
    "hashlib", "uuid", "random", "math", "statistics", "logging", "warnings",
    "threading", "multiprocessing", "asyncio", "concurrent", "contextlib",
    "urllib", "http", "email", "html", "xml", "csv", "sqlite3", "argparse",
    "configparser", "tempfile", "shutil", "glob", "fnmatch", "platform",
    "subprocess", "signal", "socket", "ssl", "struct", "array", "bisect",
    "heapq", "deque", "flask", "fastapi", "django", "starlette", "requests",
    "httpx", "aiohttp", "tornado", "bottle", "pyramid", "falcon", "sanic",
    "uvicorn", "gunicorn", "numpy", "pandas", "scipy", "sklearn", "tensorflow",
    "torch", "keras", "jax", "transformers", "pillow", "cv2", "PIL",
    "sqlalchemy", "psycopg2", "pymysql", "redis", "mongodb", "elasticsearch",
    "asyncio", "aiofiles", "aioredis", "celery", "rq", "pydantic", "dataclasses",
    "attrs", "tqdm", "yaml", "toml", "pytest", "unittest", "mock", "coverage",
    "tox",
])


class _CallInfo:
    """Describes a resolved call target."""
    __slots__ = ("callee_name", "receiver", "is_external")

    def __init__(
        self,
        callee_name: str,
        receiver: Optional[str] = None,
        is_external: bool = False,
    ):
        self.callee_name = callee_name
        self.receiver = receiver
        self.is_external = is_external


class _PythonCallResolver:
    """Resolves function/method call edges for Python."""

    def __init__(self, symbols: list[Symbol], ast_data: list[dict]):
        self.symbols = symbols
        self.ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

        # ── Indexes ──────────────────────────────────────────────────────────────
        self._by_qname: dict[str, Symbol] = {}
        self._by_simple: dict[str, list[Symbol]] = {}
        self._by_scope: dict[str, list[Symbol]] = {}
        # import_alias: local name → module/symbol qualified name
        # e.g. {"crud": "database.crud", "success_response": "routers.common.success_response"}
        self._import_alias: dict[str, str] = {}
        # module_to_file: module qualified name → file path
        self._module_to_file: dict[str, str] = {}
        # instance_types: (class_scope, field) → type name
        self._instance_types: dict[tuple[str, str], str] = {}

        for s in symbols:
            self._by_qname[s.qualified_name] = s
            self._by_simple.setdefault(s.name, []).append(s)
            self._by_scope.setdefault(s.scope, []).append(s)
            if s.kind == "module":
                self._module_to_file[s.qualified_name] = s.file

        # Build import alias map
        for s in symbols:
            if s.kind in ("import", "module"):
                qname = s.qualified_name
                # local_name → qualified_name
                self._import_alias[s.name] = qname

        # Variable → class inference
        for s in symbols:
            if s.kind in ("variable", "field") and s.scope == s.qualified_name.rsplit(".", 1)[0]:
                th = s.type_hint
                if th:
                    inferred = th.lstrip(":").strip().split("|")[0].strip()
                    if inferred in self._by_simple:
                        self._by_simple.setdefault(s.name, []).append(
                            self._by_simple[inferred][0]
                        )

        self._build_instance_type_map()

    def _build_instance_type_map(self) -> None:
        for sym in self.symbols:
            if sym.kind != "method" or sym.name != "__init__":
                continue
            ast = self.ast_by_file.get(sym.file)
            if ast is None:
                continue
            method_node = self._find_method_node(ast, sym.name, sym.start[0])
            if method_node is None:
                continue
            class_scope = sym.scope
            for assign in _find_nodes(method_node, "assignment"):
                lhs_nodes = []
                rhs_call_type: Optional[str] = None
                for child in assign.get("children", []):
                    if child.get("type") == "=":
                        break
                    if child.get("type") in ("identifier", "attribute"):
                        lhs_nodes.append(child)
                    if child.get("type") == "call":
                        for c in child.get("children", []):
                            if c.get("type") == "identifier":
                                rhs_call_type = _get_text(c)
                                break
                            if c.get("type") == "attribute":
                                rhs_call_type = _get_text(c)
                                break

                for lhs in lhs_nodes:
                    lhs_text = _get_text(lhs)
                    if lhs_text in ("self", "cls", "__class__"):
                        continue
                    if rhs_call_type:
                        self._instance_types[(class_scope, lhs_text)] = rhs_call_type
                    else:
                        for child in assign.get("children", []):
                            if child.get("type") == "type_annotation":
                                ann = _get_text(child).lstrip(":").strip().split("|")[0].strip()
                                if ann:
                                    self._instance_types[(class_scope, lhs_text)] = ann
                                    break

    def _try_prefix_strip(self, name: str, caller_scope: str, preferred_kinds: tuple[str, ...]) -> Optional[Symbol]:
        """Try to resolve a possibly-truncated qname by expanding caller-scope prefixes.

        When project qnames are longer than the import-path qnames (e.g. stored qname is
        'src.backend.server.rag.single_turn_rag' but the import alias resolves to
        'server.rag.single_turn_rag'), we progressively add caller-scope prefixes
        to the right-hand side of the name until we find a match.

        Example:
          name = 'server.rag.single_turn_rag'
          caller_scope = 'src.backend.routers.rag.chat'
          Try: 'src.backend.routers.rag.server.rag.single_turn_rag'   (not found)
          Try: 'src.backend.routers.server.rag.single_turn_rag'     (not found)
          ...
          Try: 'src.backend.server.rag.single_turn_rag'              ✓ found

        Args:
            name: the possibly-shortened qualified name to resolve
            caller_scope: the scope of the calling function (used to find module prefix)
            preferred_kinds: symbol kinds to accept (e.g. ('function', 'method', 'class'))

        Returns the matching Symbol or None.
        """
        # Extract the module part of the caller scope (strip last component)
        caller_module = caller_scope.rsplit(".", 1)[0] if "." in caller_scope else caller_scope

        # Build candidate qnames by prepending increasingly shorter caller-module prefixes
        while "." in caller_module:
            candidate = f"{caller_module}.{name}"
            resolved = self._by_qname.get(candidate)
            if resolved and resolved.kind in preferred_kinds:
                return resolved
            # Shorten caller_module by one level
            caller_module = caller_module.rsplit(".", 1)[0]

        # Fallback: also try stripping leading components from name itself
        # (handles cases where name has extra leading segments)
        stripped = name
        while "." in stripped:
            stripped = stripped[stripped.index(".") + 1:]
            if not stripped:
                break
            resolved = self._by_qname.get(stripped)
            if resolved and resolved.kind in preferred_kinds:
                return resolved

        return None

    def _find_method_node(self, ast: dict, name: str, line: int) -> Optional[dict]:
        for n in _find_nodes(ast, "function_definition") + _find_nodes(ast, "async_function_definition"):
            id_node = _first_child(n, "identifier")
            if id_node and _get_text(id_node) == name and n["start"][0] == line:
                return n
        return None

    def _is_builtin(self, name: str) -> bool:
        return name in _PYTHON_BUILTINS

    def _get_call_info(self, call_node: dict) -> Optional[_CallInfo]:
        """Extract callee metadata from a call node.

        Handles:
          foo()              → callee="foo", receiver=None
          obj.method()       → callee="method", receiver="obj"
          pkg.mod.func()     → callee="func", receiver="pkg.mod"
          crud.get_user()    → callee="get_user", receiver="crud"
        """
        children = call_node.get("children", [])
        arg_list_idx = None
        for i, child in enumerate(children):
            if child.get("type") == "argument_list":
                arg_list_idx = i
                break

        if arg_list_idx is None or arg_list_idx == 0:
            return None

        target = children[arg_list_idx - 1]
        tn = target.get("type", "")

        if tn == "identifier":
            callee = _get_text(target)
            return _CallInfo(callee)

        if tn == "attribute":
            attr_parts = target.get("children", [])
            if not attr_parts:
                return None

            method_name = attr_parts[-1].get("text") or _get_text(attr_parts[-1])

            # Walk the attribute chain to extract the full receiver.
            # e.g. for "pkg.mod.func": attribute chain has nested attributes,
            # and the deepest identifier is "pkg", method is "func".
            receiver_parts = []
            cur = target
            while cur.get("type") == "attribute":
                parts = cur.get("children", [])
                if len(parts) >= 2:
                    receiver_parts.append(parts[-1].get("text") or _get_text(parts[-1]))
                    cur = parts[0]
                else:
                    break
            receiver_parts.append(_get_text(cur))
            receiver_parts.reverse()
            receiver = ".".join(receiver_parts[:-1]) if len(receiver_parts) > 1 else None

            return _CallInfo(method_name, receiver=receiver)

        if tn == "call":
            # Nested call: executor.submit(summarize, ...)
            arg_list = children[arg_list_idx]
            for arg in arg_list.get("children", []):
                arg_t = arg.get("type", "")
                if arg_t == "identifier":
                    return _CallInfo(_get_text(arg))
                if arg_t == "attribute":
                    return _CallInfo(_get_text(arg))
            return None

        return None

    def resolve(self) -> list[Edge]:
        edges: list[Edge] = []
        seen: set[tuple] = set()

        # Only function/method symbols need call resolution
        func_syms = [s for s in self.symbols if s.kind in ("function", "method")]
        for sym in tqdm(func_syms, desc="  Stage 4a calls", unit="func", ncols=80, leave=False):
            ast = self.ast_by_file.get(sym.file)
            if ast is None:
                continue

            method_node = self._find_method_node(ast, sym.name, sym.start[0])
            if method_node is None:
                continue

            call_nodes: list[dict] = []
            _collect_calls(method_node, call_nodes)

            class_scope = sym.scope.rsplit(".", 1)[0] if "." in sym.scope else ""

            for call in call_nodes:
                info = self._get_call_info(call)
                if info is None:
                    continue

                callee = info.callee_name
                receiver = info.receiver

                if self._is_builtin(callee):
                    continue

                # executor.submit(func, ...)
                if callee in ("submit", "map", "apply_async"):
                    resolved = self._resolve_submitted_func(callee, sym, call)
                    if resolved:
                        key = (sym.qualified_name, resolved.qualified_name)
                        if key not in seen:
                            seen.add(key)
                            edges.append(Edge(
                                kind="call",
                                from_qname=sym.qualified_name,
                                to_qname=resolved.qualified_name,
                                file=sym.file,
                                line=call["start"][0],
                            ))
                    continue

                # self.xxx / cls.xxx
                if receiver in _UNRESOLVABLE_RECEIVERS:
                    resolved = self._resolve_self_method(class_scope, sym.scope, callee)
                    if resolved:
                        key = (sym.qualified_name, resolved.qualified_name)
                        if key not in seen:
                            seen.add(key)
                            edges.append(Edge(
                                kind="call",
                                from_qname=sym.qualified_name,
                                to_qname=resolved.qualified_name,
                                file=sym.file,
                                line=call["start"][0],
                                receiver=receiver,
                            ))
                    continue

                # receiver.method() — instance variable method call
                if receiver:
                    resolved = self._resolve_instance_call(class_scope, receiver, callee)
                    if resolved:
                        key = (sym.qualified_name, resolved.qualified_name)
                        if key not in seen:
                            seen.add(key)
                            edges.append(Edge(
                                kind="call",
                                from_qname=sym.qualified_name,
                                to_qname=resolved.qualified_name,
                                file=sym.file,
                                line=call["start"][0],
                                receiver=receiver,
                            ))
                    continue

                # Plain function call: foo()
                resolved_sym = self._resolve_plain_call(callee, sym.scope, sym.file)
                if resolved_sym:
                    key = (sym.qualified_name, resolved_sym.qualified_name)
                    if key not in seen:
                        seen.add(key)
                        edges.append(Edge(
                            kind="call",
                            from_qname=sym.qualified_name,
                            to_qname=resolved_sym.qualified_name,
                            file=sym.file,
                            line=call["start"][0],
                        ))

        return edges

    def _resolve_submitted_func(self, _callee: str, caller_sym: Symbol, call_node: dict) -> Optional[Symbol]:
        arg_list = None
        for c in call_node.get("children", []):
            if c.get("type") == "argument_list":
                arg_list = c
                break
        if arg_list is None:
            return None
        for arg in arg_list.get("children", []):
            arg_t = arg.get("type", "")
            if arg_t not in ("identifier", "attribute"):
                continue
            name = _get_text(arg)
            if self._is_builtin(name):
                continue
            if "." in name:
                name = name.rsplit(".", 1)[-1]
            candidates = self._by_simple.get(name, [])
            same_scope = [c for c in candidates if c.scope == caller_sym.scope]
            if same_scope:
                return next((c for c in same_scope if c.kind in ("function", "method")), same_scope[0])
            caller_module = caller_sym.scope.rsplit(".", 1)[0] if "." in caller_sym.scope else caller_sym.scope
            same_module = [c for c in candidates if c.scope.startswith(caller_module + ".")]
            if same_module:
                return next((c for c in same_module if c.kind in ("function", "method")), same_module[0])
        return None

    def _resolve_self_method(
        self, class_scope: str, method_scope: str, callee: str
    ) -> Optional[Symbol]:
        candidates = self._by_simple.get(callee, [])
        for c in candidates:
            if c.scope == method_scope or c.scope == class_scope:
                return c
        return None

    def _resolve_instance_call(
        self, class_scope: str, receiver: str, method_name: str
    ) -> Optional[Symbol]:
        inst_type = self._instance_types.get((class_scope, receiver))
        if inst_type:
            type_candidates = self._by_simple.get(inst_type, [])
            for tc in type_candidates:
                if tc.scope == class_scope or tc.scope == inst_type:
                    method_candidates = self._by_simple.get(method_name, [])
                    for mc in method_candidates:
                        if mc.scope == tc.qualified_name or mc.scope == tc.scope:
                            return mc
        # Fallback: when receiver is 'self' or 'cls', look up the method name
        # directly in the class's scope (handles patterns like cls.register, self.xxx
        # where we can find the method by name alone).
        if receiver in ("self", "cls"):
            candidates = self._by_simple.get(method_name, [])
            for c in candidates:
                if c.scope == class_scope and c.kind in ("method", "function"):
                    return c
        return None

    def _resolve_plain_call(
        self, callee: str, caller_scope: str, caller_file: str
    ) -> Optional[Symbol]:
        """Resolve a plain function/class call to a project symbol.

        Key improvements over the baseline:
        1. Import alias resolution: 'crud' → 'database.crud'
        2. Cross-file module lookup: 'crud.get_user' → 'database.crud.get_user'
        3. When receiver is an import alias, look up the method in that module's scope.
        """
        # Check if callee is an import alias → resolve to its module/symbol qname
        resolved_callee = self._import_alias.get(callee, callee)

        # Look up directly by qname (handles submodule-qualified names)
        direct = self._by_qname.get(resolved_callee)
        if direct and direct.kind in ("function", "method", "class"):
            return direct

        # Fallback: resolved_callee may be shorter than the stored qname
        # (e.g. 'server.rag.single_turn_rag' vs 'backend.server.rag.single_turn_rag'
        # when the project is scanned from a subdirectory).
        # Try stripping leading components to find a match.
        stripped = self._try_prefix_strip(resolved_callee, caller_scope, ("function", "method", "class"))
        if stripped:
            return stripped

        # Search by simple name across all scopes
        candidates = self._by_simple.get(resolved_callee, [])

        if not candidates:
            candidates = self._by_simple.get(callee, [])

        if not candidates:
            return None

        # Prefer same-scope callable
        same_scope = [c for c in candidates if c.scope == caller_scope and c.kind in ("function", "method", "class")]
        if same_scope:
            return same_scope[0]

        # Prefer same-module callable
        caller_module = caller_scope.rsplit(".", 1)[0] if "." in caller_scope else caller_scope
        same_module = [
            c for c in candidates
            if (c.scope == caller_module or c.scope.startswith(caller_module + "."))
            and c.kind in ("function", "method", "class")
        ]
        if same_module:
            return same_module[0]

        # Any callable at same scope
        same_scope_any = [c for c in candidates if c.scope == caller_scope]
        if same_scope_any:
            return same_scope_any[0]

        # Accept first callable candidate from same file
        same_file = [c for c in candidates if c.file == caller_file and c.kind in ("function", "method", "class")]
        if same_file:
            return same_file[0]

        return None

    def _resolve_attribute_call(
        self, receiver: str, method_name: str, caller_scope: str, caller_file: str
    ) -> Optional[Symbol]:
        """Resolve a call like 'receiver.method_name()' where receiver is a module alias.

        Steps:
        1. Check if receiver is an import alias → get module qname
        2. Try: module_qname.method_name
        3. Try: module_qname's scope + "." + method_name
        """
        # Resolve the receiver alias to its module qualified name
        module_qname = self._import_alias.get(receiver, receiver)

        # Try direct qname lookup: database.crud.get_user
        direct = self._by_qname.get(f"{module_qname}.{method_name}")
        if direct and direct.kind in ("function", "method", "class"):
            return direct

        # Fallback: module_qname may be shorter than the stored qname.
        # Use the same prefix-expansion logic as _try_prefix_strip.
        stripped_result = self._try_prefix_strip(
            f"{module_qname}.{method_name}", caller_scope, ("function", "method", "class")
        )
        if stripped_result:
            return stripped_result

        # Try scope-based lookup: find symbols in the module's scope with matching name
        module_candidates = self._by_scope.get(module_qname, [])
        method_candidates = [s for s in module_candidates
                             if s.name == method_name and s.kind in ("function", "method", "class")]
        if method_candidates:
            return method_candidates[0]

        # Try within all symbols in the module's sub-scopes
        # e.g. database.crud scope has methods like get_user_by_username
        for sym in self.symbols:
            if sym.name == method_name and sym.kind in ("function", "method", "class"):
                # Check if the symbol's file belongs to the module
                if self._file_belongs_to_module(sym.file, module_qname):
                    return sym

        # Fallback: any symbol with matching name and kind
        all_candidates = self._by_simple.get(method_name, [])
        for c in all_candidates:
            if c.kind in ("function", "method", "class"):
                return c

        return None

    def _file_belongs_to_module(self, file: str, module_qname: str) -> bool:
        """Check if a file belongs to a given module."""
        mod_file = self._module_to_file.get(module_qname)
        if mod_file:
            if file == mod_file:
                return True
            mod_file_norm = mod_file.replace("\\", "/")
            file_norm = file.replace("\\", "/")
            if file_norm.startswith(mod_file_norm):
                return True
        return False

    def resolve_attribute_calls(self) -> list[Edge]:
        """Resolve calls like 'receiver.method()' where receiver is a module import alias.

        For each call, checks if the receiver is an import alias pointing to a module,
        then resolves the method within that module's scope.
        """
        edges: list[Edge] = []
        seen: set[tuple] = set()

        for sym in self.symbols:
            if sym.kind not in ("function", "method"):
                continue
            ast = self.ast_by_file.get(sym.file)
            if ast is None:
                continue

            method_node = self._find_method_node(ast, sym.name, sym.start[0])
            if method_node is None:
                continue

            call_nodes: list[dict] = []
            _collect_calls(method_node, call_nodes)

            for call in call_nodes:
                info = self._get_call_info(call)
                if info is None or info.receiver is None:
                    continue
                if self._is_builtin(info.callee_name):
                    continue
                if info.receiver in _UNRESOLVABLE_RECEIVERS:
                    continue

                resolved = self._resolve_attribute_call(
                    info.receiver, info.callee_name, sym.scope, sym.file
                )
                if resolved:
                    key = (sym.qualified_name, resolved.qualified_name)
                    if key not in seen:
                        seen.add(key)
                        edges.append(Edge(
                            kind="call",
                            from_qname=sym.qualified_name,
                            to_qname=resolved.qualified_name,
                            file=sym.file,
                            line=call["start"][0],
                            receiver=info.receiver,
                        ))
        return edges


# ── plugin class ──────────────────────────────────────────────────────────────

class PythonPlugin(LanguagePlugin):
    lang_id = "python"
    display_name = "Python"

    def get_file_patterns(self) -> list[str]:
        return ["*.py", "*.pyi"]

    def get_tree_sitter_package(self) -> str:
        return "tree_sitter_python"

    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        return _PythonSymbolBuilder(ast_entry, src_root).build()

    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        resolver = _PythonCallResolver(symbols, ast_data)

        # Build edges for attribute calls (module.attr()) in addition to plain calls
        edges = resolver.resolve()

        # Also generate edges for attribute calls where the receiver is an import alias
        attr_edges = resolver.resolve_attribute_calls()
        for e in attr_edges:
            key = (e.from_qname, e.to_qname)
            seen = {(ed.from_qname, ed.to_qname) for ed in edges}
            if key not in seen:
                edges.append(e)

        return edges

    def build_import_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        edges: list[Edge] = []

        # module symbols provide module → file resolution
        module_to_file: dict[str, str] = {}
        module_qname_by_file: dict[str, str] = {}
        for s in symbols:
            if s.kind == "module":
                module_to_file[s.qualified_name] = s.file
                module_qname_by_file[s.file] = s.qualified_name

        seen: set[tuple] = set()

        import_syms = [s for s in symbols if s.kind in ("import", "module")]
        for s in tqdm(import_syms, desc="  Stage 4b imports", unit="file", ncols=80, leave=False):

            from_file = s.file
            from_module = module_qname_by_file.get(from_file)
            if not from_module:
                continue

            target_qname = s.qualified_name

            # For symbol imports (kind=import, e.g. "from database import get_user"),
            # the qualified_name includes the symbol name. Strip to get the module prefix.
            # For submodule imports (kind=module, e.g. "from database import crud"),
            # qualified_name IS the module path — use as-is.
            if s.kind == "import" and not target_qname.endswith(".*"):
                target_qname = target_qname.rsplit(".", 1)[0]

            # Skip wildcard imports.
            if target_qname.endswith(".*"):
                continue

            # Resolve target module qname to file first.
            # We check module_to_file BEFORE the external-package skip check so that
            # project-internal modules (e.g. "preprocess", "storage", "workflow") are
            # recognized even if their top-level name matches a common external name.
            target_file = module_to_file.get(target_qname)
            if target_file is None:
                # Try prefix match: import database.crud → database module
                for mod_qname, mod_file in module_to_file.items():
                    if target_qname.startswith(mod_qname + ".") or target_qname == mod_qname:
                        target_file = mod_file
                        break

            # If resolved to a known project module, it is internal — don't skip.
            if target_file is not None:
                pass  # keep processing
            else:
                # Module not found in project: check whether the top-level name
                # looks like a common external package to avoid noisy imports edges.
                top_level = target_qname.split(".")[0]
                _COMMON_EXTERNAL_PACKAGES = (
                    "os", "sys", "re", "json", "typing", "datetime", "pathlib",
                    "fastapi", "flask", "pydantic", "sqlalchemy", "pytest", "unittest",
                    "httpx", "requests", "starlette", "tqdm", "yaml", "toml", "hashlib",
                    "uuid", "subprocess", "asyncio", "collections", "itertools",
                    "functools", "operator", "copy", "io", "pickle", "argparse",
                    "logging", "threading", "multiprocessing", "concurrent", "contextlib",
                    "urllib", "http", "email", "html", "xml", "csv", "sqlite3",
                    "configparser", "tempfile", "shutil", "glob", "fnmatch", "platform",
                    "signal", "socket", "ssl", "struct", "array", "bisect", "heapq",
                    "numpy", "pandas", "scipy", "sklearn", "tensorflow", "torch", "keras",
                    "jax", "transformers", "pillow", "cv2", "PIL", "redis", "mongodb",
                    "elasticsearch", "celery", "pymysql", "psycopg2", "aiofiles",
                    "aioredis", "rq", "struct", "time", "random", "math", "statistics",
                    "base64", "binascii", "calendar", "codecs", "copyreg", "dis",
                    "fileinput", "getopt", "getpass", "gettext", "graphlib", "inspect",
                    "keyword", "linecache", "locale", "marshal", "mgctypes", "netrc",
                    "ntpath", "nturl2path", "opcode", "optparse", "os", "pathlib",
                    "pipes", "pkgutil", "platform", "plistlib", "posixpath", "pprint",
                    "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr", "queue",
                    "quopri", "reprlib", "runpy", "sched", "secrets", "select",
                    "selectors", "shlex", "spwd", "sre", "stat", "statvfs", "string",
                    "stringprep", "subprocess", "sunau", "symbol", "sysconfig",
                    "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
                    "textwrap", "this", "token", "tokenize", "traceback", "tty", "turtle",
                    "types", "typing", "unicodedata", "uu", "uuid", "warnings", "wave",
                    "weakref", "webbrowser", "winsound", "xdrlib", "zipfile", "zipimport",
                    "zoneinfo", "pydantic_settings",
                )
                if top_level in _COMMON_EXTERNAL_PACKAGES:
                    continue

            if target_file is None:
                continue

            if target_file == from_file:
                continue  # same file

            key = (from_file, target_file)
            if key in seen:
                continue
            seen.add(key)

            to_module = module_qname_by_file.get(target_file)
            if not to_module:
                continue

            edges.append(Edge(
                kind="imports",
                from_qname=from_module,
                to_qname=to_module,
                file=from_file,
                line=s.start[0] if s.start else 0,
            ))
        return edges

    def build_extends_implements_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate extends edges for Python class declarations.

        Python uses 'class Child(Parent):' syntax. Base classes are stored in
        an 'argument_list' node as direct children of the class_definition node.
        All Python inheritance is treated as 'extends' (no interface distinction).
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
            """Return candidates for simple_name, preferring same-module."""
            candidates = [c for c in by_simple.get(simple_name, [])
                         if c.qualified_name != ref_qname]
            # Python modules: same module = same file
            ref_module = ref_qname.rsplit(".", 1)[0]
            same_module = [c for c in candidates if c.qualified_name.rsplit(".", 1)[0] == ref_module]
            if same_module:
                return same_module
            return candidates if len(candidates) == 1 else []

        def find_class_nodes(ast: dict, results: list) -> None:
            """Find all class_definition nodes in AST."""
            if ast.get("type") == "class_definition":
                results.append(ast)
            for child in ast.get("children", []):
                find_class_nodes(child, results)

        for sym in symbols:
            if sym.kind != "class":
                continue

            ast = ast_by_file.get(sym.file)
            if ast is None:
                continue

            # Find all class_definition nodes
            class_nodes = []
            find_class_nodes(ast, class_nodes)

            # Find the matching class node
            for cls_node in class_nodes:
                # Get class name
                name_node = None
                for child in cls_node.get("children", []):
                    if child.get("type") == "identifier":
                        name_node = child
                        break
                if name_node is None:
                    continue
                name = name_node.get("text", "")
                if name != sym.name:
                    continue

                # Find argument_list (base classes)
                for child in cls_node.get("children", []):
                    if child.get("type") == "argument_list":
                        for arg in child.get("children", []):
                            if arg.get("type") == "identifier":
                                base_name = arg.get("text", "")
                                if base_name:
                                    candidates = best_candidates(base_name, sym.qualified_name)
                                    line = cls_node.get("start", [1, 0])[0]

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
                break

        return edges

    def build_inner_class_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        """Generate inner_class edges for Python nested classes."""
        edges: list[Edge] = []
        by_qname: dict[str, Symbol] = {s.qualified_name: s for s in symbols}

        for sym in symbols:
            if sym.kind != "class":
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
            "@app.route": "web.route",
            "@app.get": "web.route",
            "@app.post": "web.route",
            "@app.put": "web.route",
            "@app.delete": "web.route",
            "@app.patch": "web.route",
            "@router.get": "web.route",
            "@router.post": "web.route",
            "@router.put": "web.route",
            "@router.delete": "web.route",
            "@django.views.http": "web.route",
            "@fastapi": "web.api",
            "@starlette.exceptions": "web.middleware",
            "@pytest.fixture": "test.fixture",
            "@pytest.mark.parametrize": "test.parametrized",
            "@unittest.mock.patch": "test.mock",
            "@dataclass": "data.class",
            "@property": "oo.property",
            "@abstractmethod": "oo.abstract",
            "@staticmethod": "oo.static",
            "@classmethod": "oo.classmethod",
            "@cached_property": "oo.cached_prop",
            "@lru_cache": "perf.cache",
        }

    def infer_constructors(self) -> dict[str, str]:
        return {}

    def get_entry_point_names(self) -> list[str]:
        return ["main"]


register(PythonPlugin)
