"""C language plugin — supports C source files via tree-sitter-c.

This plugin handles:
- C source files (.c)
- C header files (.h)

It extracts:
- Structs, unions, enums
- Functions
- Fields (member variables)
- Parameters
- Local/global variables
- Type aliases (typedef)
- Preprocessor macros (as annotations)

It generates:
- call edges for function invocations
- contains edges for members inside types
- imports edges for #include directives
- template_include edges for #include with angle brackets

Unlike C++, C has no classes, namespaces, templates, operator overloading,
or method calls. This plugin focuses on C-specific constructs like unions
and function-pointer fields.
"""

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser
from tqdm import tqdm

import tree_sitter_c as tsc

from ._register_helper import register
from ...common.base import Edge, LanguagePlugin, Symbol


_C_LANGUAGE = Language(tsc.language())
_C_PARSER = Parser(_C_LANGUAGE)


# ── tree helpers ────────────────────────────────────────────────────────────────

def _get_text(node: dict, default: str = "") -> str:
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


def _children_of_type(node: dict, *types) -> list[dict]:
    return [c for c in node.get("children", []) if c["type"] in types]


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


def _is_in_type(node: dict) -> bool:
    parent = node.get("_parent")
    while parent:
        t = parent.get("type", "")
        if t in ("struct_specifier", "union_specifier", "enum_specifier"):
            return True
        parent = parent.get("_parent")
    return False


def _is_header_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in (".h",)


# ── namespace / scope inference ─────────────────────────────────────────────────

def _infer_namespace(file_path: str, src_root: str) -> str:
    try:
        abs_root = Path(src_root).resolve()
        abs_file = Path(file_path).resolve()
        rel = abs_file.relative_to(abs_root)
        parts = list(rel.parts)
        ext = Path(file_path).suffix.lower()

        if ext == ".h":
            if parts[-1].startswith("pch.") or parts[-1].startswith("stdafx."):
                parts = parts[:-1]
        else:
            if parts[-1].endswith(".c"):
                parts[-1] = parts[-1][:-2]

        return ".".join(parts)
    except (ValueError, OSError):
        return Path(file_path).stem


# ── symbol builder ─────────────────────────────────────────────────────────────

class _CSymbolBuilder:
    """Builds Symbol list from a C AST entry."""

    def __init__(self, ast_entry: dict, src_root: str = ""):
        self.entry = ast_entry
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._file: str = ast_entry["file"]
        self._src_root = src_root
        self._namespace = _infer_namespace(self._file, src_root)
        self._is_header = _is_header_file(self._file)

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
        for c in node.get("children", []):
            if c.get("type") in ("comment", "line_comment"):
                text = _get_text(c).lstrip("//").strip()
                if text:
                    return text
        return None

    def _collect_modifiers(self, node: dict) -> tuple[list[str], list[str]]:
        modifiers: list[str] = []
        annotations: list[str] = []

        for c in node.get("children", []):
            t = c["type"]
            if t in (
                "static", "extern", "inline", "const", "volatile",
                "auto", "register", "thread_local", "typedef",
                "_Thread_local", "_Atomic",
            ):
                modifiers.append(t)
            elif t == "attribute":
                annotations.append("@" + _get_text(c).strip())
            elif t == "attribute_declaration":
                annotations.append("@attr:" + _get_text(c).strip())

        return modifiers, annotations

    def _extract_storage_class(self, node: dict) -> list[str]:
        result = []
        for c in node.get("children", []):
            if c["type"] in ("static", "extern", "register", "thread_local",
                              "_Thread_local", "typedef", "const", "volatile"):
                result.append(c["type"])
        return result

    def _type_text(self, type_node: Optional[dict]) -> str:
        if type_node is None:
            return ""
        return _get_text(type_node).strip()

    def _get_return_type(self, node: dict) -> Optional[str]:
        for c in node.get("children", []):
            t = c["type"]
            if t in (
                "primitive_type", "type_identifier", "sized_type_specifier",
                "type_descriptor", "qualified_identifier",
                "pointer_type", "const_type", "volatile_type",
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

        # C has struct_specifier (C++) and union_specifier (C-specific)
        if t == "struct_specifier":
            self._visit_type(node, parent, "struct")
            return

        if t == "union_specifier":
            self._visit_type(node, parent, "union")
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
                lang="c",
            )
            self.symbols.append(sym)
            self._push(name)
            for c in node.get("children", []):
                self._visit(c, node)
            self._pop()
            return

        # C only has typedef — no using alias
        if t == "type_alias_declaration":
            name_node = _first_child(node, "type_identifier")
            name = _get_text(name_node) if name_node else "<anon>"
            aliased = None
            for c in node.get("children", []):
                if c["type"] not in ("typedef", "type_identifier", "=", ";"):
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
                lang="c",
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
                    lang="c",
                ))
            return

        # Generic fallback: recurse into children
        for c in node.get("children", []):
            self._visit(c, node)

    def _visit_type(self, node: dict, parent: Optional[dict], kind: str) -> None:
        name_node = _first_child(node, "type_identifier")
        name = _get_text(name_node) if name_node else "<anon>"
        if name == "<anon>":
            for c in node.get("children", []):
                self._visit(c, node)
            return

        mods, anns = self._collect_modifiers(node)
        doc = self._collect_line_comments(node)

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
            lang="c",
        )
        self.symbols.append(sym)

        if self._scope_stack:
            sym.modifiers = list(sym.modifiers) + ["inner"]

        self._push(name)

        class_body_found = False
        for c in node.get("children", []):
            ct = c["type"]
            if ct in ("field_declaration", "function_definition",
                      "declaration", "type_alias_declaration"):
                self._visit(c, node)
            elif ct in ("comment", "line_comment"):
                pass
            elif ct == "type_identifier" and not class_body_found:
                class_body_found = True
            elif ct == "field_declaration_list":
                class_body_found = True
                for member in c.get("children", []):
                    self._visit(member, node)

        self._pop()

    def _visit_function(self, node: dict, parent: Optional[dict]) -> None:
        decl = _first_child(node, "function_declarator", "pointer_declarator")
        if decl is None:
            for c in node.get("children", []):
                self._visit(c, node)
            return

        while decl.get("type") in ("pointer_declarator", "parenthesized_declarator"):
            inner = _first_child(decl, "function_declarator", "pointer_declarator", "identifier")
            if inner:
                decl = inner
            else:
                break

        name_node = _first_child(decl, "identifier", "field_identifier",
                                 "pointer_declarator")
        if name_node and name_node.get("type") in ("pointer_declarator",):
            name_node = _first_child(name_node, "identifier", "field_identifier")

        name = _get_text(name_node) if name_node else "<anon>"

        if name == "<anon>":
            for c in node.get("children", []):
                self._visit(c, node)
            return

        kind = "function"

        ret_type = self._get_return_type(node)
        mods, anns = self._collect_modifiers(node)

        doc = self._collect_line_comments(node)

        sym = Symbol(
            name=name,
            kind=kind,
            qualified_name=self._qualified(name),
            file=self._file,
            start=tuple(node["start"]),
            end=tuple(node["end"]),
            scope=self._current_scope(),
            type_hint=ret_type,
            modifiers=mods,
            annotations=anns,
            docstring=doc,
            lang="c",
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
        type_node: Optional[dict] = None
        declarators: list[dict] = []

        for c in node.get("children", []):
            ct = c["type"]
            if ct in (
                "primitive_type", "type_identifier", "sized_type_specifier",
                "type_descriptor", "qualified_identifier",
                "const_type", "volatile_type", "auto",
            ):
                type_node = c
            elif ct in ("init_declarator", "declarator",
                        "pointer_declarator", "reference_declarator"):
                declarators.append(c)
            elif ct in ("identifier", "field_identifier"):
                declarators.append(c)

        type_text = self._type_text(type_node)
        storage = self._extract_storage_class(node)
        mods, anns = self._collect_modifiers(node)
        mods.extend(storage)

        for decl in declarators:
            decl_name_node = _first_child(decl, "identifier", "field_identifier",
                                          "pointer_declarator")
            if decl_name_node and decl_name_node.get("type") in ("pointer_declarator",):
                decl_name_node = _first_child(decl_name_node, "identifier", "field_identifier")

            decl_name = _get_text(decl_name_node) if decl_name_node else "<anon>"

            if decl_name == "<anon>":
                continue

            is_function = False
            for sub in decl.get("children", []):
                if sub["type"] in ("function_declarator", "pointer_declarator"):
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
                lang="c",
            ))

    def _visit_parameters(self, node: dict) -> None:
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
                        "type_descriptor", "qualified_identifier",
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
                    lang="c",
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
            lang="c",
        ))

        return self.symbols


# ── call edge resolver ─────────────────────────────────────────────────────────

class _CCallResolver:
    """Resolves function call edges for C."""

    def __init__(self, symbols: list[Symbol], ast_data: list[dict]):
        self.symbols = symbols
        self.ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

        self._by_simple: dict[str, list[Symbol]] = {}
        self._by_qname: dict[str, Symbol] = {}
        self._by_scope: dict[str, list[Symbol]] = {}

        for s in symbols:
            self._by_qname[s.qualified_name] = s
            self._by_simple.setdefault(s.name, []).append(s)
            self._by_scope.setdefault(s.scope, []).append(s)

    def _get_call_target(self, call_node: dict) -> Optional[str]:
        """Return the callee name from a call_expression node.

        Unlike C++, C has no method calls or operator overloading.
        Only handles plain function calls: foo()
        """
        children = call_node.get("children", [])
        for i, child in enumerate(children):
            if child.get("type") == "argument_list":
                if i == 0:
                    return None
                target = children[i - 1]
                tn = target.get("type", "")

                if tn == "identifier":
                    return _get_text(target)

                if tn == "builtin_function_call_expression":
                    return _get_text(target)

                return None

        return None

    def _find_function_node(self, ast: dict, name: str, line: int) -> Optional[dict]:
        for n in _find_nodes(ast, "function_definition"):
            decl = _first_child(n, "function_declarator", "pointer_declarator")
            if decl is None:
                continue
            while decl.get("type") in ("pointer_declarator",):
                inner = _first_child(decl, "function_declarator", "pointer_declarator", "identifier")
                if inner:
                    decl = inner
                else:
                    break
            id_node = _first_child(decl, "identifier", "field_identifier")
            if id_node and _get_text(id_node) == name and n["start"][0] == line:
                return n
        return None

    def _resolve_call(
        self, callee: str, caller_scope: str, caller_file: str, line: int
    ) -> Optional[str]:
        if callee in _C_BUILTINS:
            return None

        candidates = self._by_simple.get(callee, [])
        same_scope = [c for c in candidates if c.scope == caller_scope]
        if same_scope:
            resolved = next((c for c in same_scope
                           if c.kind in ("function",)), same_scope[0])
            return resolved.qualified_name

        caller_module = caller_scope.rsplit(".", 1)[0] if "." in caller_scope else caller_scope
        same_module = [
            c for c in candidates
            if (c.scope == caller_module or c.scope.startswith(caller_module + "."))
            and c.kind in ("function",)
        ]
        if same_module:
            return same_module[0].qualified_name

        if candidates:
            resolved = next((c for c in candidates if c.kind in ("function",)), candidates[0])
            return resolved.qualified_name

        return None

    def resolve(self) -> list[Edge]:
        edges: list[Edge] = []
        seen: set[tuple] = set()

        func_syms = [s for s in self.symbols if s.kind == "function"]
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
                callee = self._get_call_target(call)
                if not callee:
                    continue

                qname = self._resolve_call(callee, sym.scope, sym.file, call["start"][0])

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
                        ))
                else:
                    to_qname = f"ext::{callee}"
                    key = (sym.qualified_name, to_qname)
                    if key not in seen:
                        seen.add(key)
                        edges.append(Edge(
                            kind="call",
                            from_qname=sym.qualified_name,
                            to_qname=to_qname,
                            file=sym.file,
                            line=call["start"][0],
                        ))

        return edges


# C standard library and POSIX functions that are not resolved as internal calls
_C_BUILTINS = frozenset({
    # Standard I/O
    "printf", "fprintf", "sprintf", "snprintf",
    "vprintf", "vfprintf", "vsprintf", "vsnprintf",
    "scanf", "fscanf", "sscanf", "vscanf", "vfscanf", "vsscanf",
    "puts", "fputs", "gets", "fgets", "getchar", "fgetc", "getc",
    "putchar", "fputc", "putc", "puts",
    "perror", "feof", "ferror", "clearerr", "fflush", "fseek", "ftell",
    "rewind", "fgetpos", "fsetpos", "fread", "fwrite", "fopen", "freopen", "fclose",
    "setbuf", "setvbuf", "tmpfile", "tmpnam", "remove", "rename",

    # String / memory
    "malloc", "calloc", "realloc", "free",
    "memcpy", "memmove", "memset", "memcmp", "memchr",
    "strcpy", "strncpy", "strcat", "strncat", "strlen",
    "strcmp", "strncmp", "strchr", "strrchr", "strstr", "strtok",
    "strdup", "strndup", "strnlen", "strerror", "strsignal",

    # Character / ctype
    "isalnum", "isalpha", "isblank", "iscntrl", "isdigit", "isgraph",
    "islower", "isprint", "ispunct", "isspace", "isupper", "isxdigit",
    "tolower", "toupper",

    #stdlib
    "atoi", "atol", "atoll", "atof", "strtol", "strtoll", "strtoul",
    "strtoull", "strtod", "strtof", "strtold",
    "srand", "rand", "exit", "_exit", "abort", "atexit", "at_quick_exit",
    "system", "getenv", "putenv", "setenv", "unsetenv", "bsearch", "bsearch_s",
    "qsort", "qsort_s", "abs", "labs", "llabs", "div", "ldiv", "lldiv",

    # Time
    "time", "difftime", "clock", "mktime", "strftime", "strptime",
    "gmtime", "localtime", "ctime", "asctime", "tzset",

    # Math
    "abs", "labs", "llabs", "div", "ldiv", "lldiv",
    "fabs", "fabsf", "fabsl", "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "exp", "expf", "expl", "exp2", "exp2f", "exp2l",
    "log", "logf", "logl", "log10", "log10f", "log10l",
    "log1p", "log1pf", "log1pl", "log2", "log2f", "log2l",
    "pow", "powf", "powl", "sqrt", "sqrtf", "sqrtl",
    "ceil", "ceilf", "ceill", "floor", "floorf", "floorl",
    "round", "roundf", "roundl", "trunc", "truncf", "truncl",
    "fmod", "fmodf", "fmodl", "remainder", "remainderf", "remainderl",
    "fma", "fmaf", "fmal", "hypot", "hypotf", "hypotl",
    "copysign", "copysignf", "copysignl", "nan", "nanf", "nanl",
    "isfinite", "isinf", "isnan", "isnormal", "fpclassify",
    "signbit", "sqrt", "pow", "fdim", "fdimf", "fdiml",

    # File / fd
    "open", "read", "write", "close", "lseek", "fsync",
    "ftruncate", "truncate", "stat", "fstat", "lstat",
    "access", "dup", "dup2", "pipe", "mkfifo",
    "select", "poll",

    # Process / threading
    "fork", "execv", "execve", "execvp", "execl", "execlp", "execle",
    "wait", "waitpid", "waitid", "WIFEXITED", "WEXITSTATUS",
    "kill", "getpid", "getppid", "sleep", "usleep", "nanosleep",
    "pthread_create", "pthread_join", "pthread_detach",
    "pthread_mutex_lock", "pthread_mutex_unlock", "pthread_mutex_init",
    "pthread_mutex_destroy", "pthread_cond_init", "pthread_cond_signal",
    "pthread_cond_broadcast", "pthread_cond_wait", "pthread_cond_destroy",
    "pthread_rwlock_init", "pthread_rwlock_rdlock", "pthread_rwlock_wrlock",
    "pthread_rwlock_unlock", "pthread_rwlock_destroy",
    "pthread_self", "pthread_equal", "pthread_exit",
    "pthread_once", "pthread_key_create", "pthread_getspecific",
    "pthread_setspecific", "pthread_cleanup_push", "pthread_cleanup_pop",
    "sem_init", "sem_wait", "sem_post", "sem_destroy",
    "mmap", "munmap", "mprotect", "mlock", "munlock",

    # Sockets / network
    "socket", "bind", "listen", "accept", "connect",
    "send", "recv", "sendto", "recvfrom",
    "shutdown", "getsockopt", "setsockopt",
    "getaddrinfo", "freeaddrinfo", "getnameinfo",
    "htons", "htonl", "ntohs", "ntohl",
    "inet_ntoa", "inet_ntop", "inet_pton",

    # Signal
    "signal", "raise", "sigaction", "sigemptyset", "sigfillset",
    "sigaddset", "sigdelset", "sigismember", "sigprocmask",
    "sigpending", "sigsuspend", "pause",

    # Setjmp / longjmp
    "setjmp", "longjmp",

    # Assert / debug
    "assert", "static_assert", "sizeof", "offsetof", "container_of",
    "_Static_assert",

    # Locale
    "setlocale", "localeconv", "nl_langinfo",

    # Atomic (C11)
    "atomic_store", "atomic_load", "atomic_exchange",
    "atomic_compare_exchange_strong", "atomic_compare_exchange_weak",
    "atomic_fetch_add", "atomic_fetch_sub", "atomic_fetch_and",
    "atomic_fetch_or", "atomic_fetch_xor",

    # Threads (C11)
    "thrd_create", "thrd_join", "thrd_detach", "thrd_sleep",
    "mtx_init", "mtx_lock", "mtx_unlock", "mtx_destroy",
    "cnd_init", "cnd_signal", "cnd_broadcast", "cnd_wait", "cnd_destroy",
    "call_once", "tss_create", "tss_get", "tss_set", "tss_delete",

    # Misc
    "aligned_alloc", "exit", "quick_exit", "_Exit",
    "getopt", "getsubopt", "rand_r",
    "bcmp", "bcopy", "bzero",
    "confstr", "sysconf", "pathconf", "fpathconf",
    "fileno", "fdopen", "popen", "pclose",
})


# ── import edge builder ────────────────────────────────────────────────────────

def _build_include_edges(symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
    """Generate imports edges from #include directives.

    Creates an edge for each #include from the including file to the included header.
    """
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

            kind = "c_include"

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

class CPlugin(LanguagePlugin):
    lang_id = "c"
    display_name = "C"

    def get_file_patterns(self) -> list[str]:
        return ["*.c", "*.h"]

    def get_tree_sitter_package(self) -> str:
        return "tree_sitter_c"

    def build_symbols(self, ast_entry: dict, src_root: str = "") -> list[Symbol]:
        return _CSymbolBuilder(ast_entry, src_root).build()

    def build_call_edges(self, symbols: list[Symbol], ast_data: list[dict]) -> list[Edge]:
        resolver = _CCallResolver(symbols, ast_data)
        return resolver.resolve()

    def build_import_edges(
        self, symbols: list[Symbol], ast_data: list[dict]
    ) -> list[Edge]:
        return _build_include_edges(symbols, ast_data)

    def get_framework_annotations(self) -> dict[str, str]:
        return {
            "#define": "macro.define",
            "#ifdef": "macro.conditional",
            "#ifndef": "macro.conditional",
            "#if": "macro.conditional",
            "#elif": "macro.conditional",
            "#else": "macro.conditional",
            "#pragma": "meta.pragma",
            "#include": "meta.include",
            "#line": "meta.line",
            "#error": "meta.error",
            "#warning": "meta.warning",
            "__attribute__": "meta.attribute",
            "__declspec": "meta.declspec",
            "DLLEXPORT": "meta.dll",
            "DLLIMPORT": "meta.dll",
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

register(CPlugin)
