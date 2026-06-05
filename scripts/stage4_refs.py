"""Stage 4: Reference Resolution — builds edges between symbol declarations and usages.

Now language-agnostic via plugins. Falls back to legacy Java-only behavior
when no --lang is specified for backward compatibility.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from tqdm import tqdm


@dataclass
class Edge:
    kind: str
    from_qname: str
    to_qname: str
    file: str
    line: int
    receiver: Optional[str] = None


# ── Plugin-based entry point ───────────────────────────────────────────────────

def resolve_references(
    typed_data: dict,
    ast_data: list[dict],
    ui_data: dict | None = None,
    lang: Optional[str] = None,
    *,
    filter_quality: bool = True,
) -> dict:
    """Resolve references and build edges.

    Delegates to plugin-specific call resolution, with generic contains/extends/etc.
    Falls back to legacy Java-only path when lang is None.
    """
    if lang is None:
        return _resolve_java(typed_data, ast_data, ui_data)

    try:
        from .plugins import LanguageRegistry
        from .plugins.common.base import Symbol as PluginSymbol
    except ImportError:
        from plugins import LanguageRegistry
        from plugins.common.base import Symbol as PluginSymbol

    plugin = LanguageRegistry.get(lang)
    symbols = typed_data["symbols"]
    edges: list[Edge] = []

    # Build file-keyed AST index for plugins that need it
    ast_by_file = {e["file"]: e for e in ast_data}

    # ── Contains edges (class→method, class→field) ───────────────────────────
    _resolve_contains_generic(symbols, edges)

    # ── Typed_as / returns edges ─────────────────────────────────────────────
    _resolve_type_refs_generic(symbols, edges)

    # ── Language-specific edges ────────────────────────────────────────────────
    plugin_symbols = [_dict_to_symbol(s) for s in symbols]
    edges.extend(plugin.build_call_edges(plugin_symbols, ast_data))
    edges.extend(plugin.build_import_edges(plugin_symbols, ast_data))
    edges.extend(plugin.build_extends_implements_edges(plugin_symbols, ast_data))
    edges.extend(plugin.build_inner_class_edges(plugin_symbols, ast_data))

    # ── Field access edges (Java-style reads/writes) ─────────────────────────
    if lang == "java":
        _resolve_field_accesses_java(symbols, ast_data, edges)

    # ── Instantiation edges (Java-style new Foo()) ─────────────────────────────
    if lang == "java":
        _resolve_instantiates_java(symbols, ast_data, edges)

    # ── Java-specific @Execute annotation handling ─────────────────────────────
    if lang == "java":
        _resolve_execute_annotations(symbols, ast_data, edges, ui_data)

    # ── UI/JSP edge resolution (Java-specific) ─────────────────────────────────
    if ui_data and lang == "java":
        _resolve_ui_edges(ui_data, symbols, ast_data, edges)

    result = {
        "symbols": symbols,
        "edges": [e.__dict__ if hasattr(e, "__dict__") else e for e in edges],
    }
    return result


def _dict_to_symbol(d: dict) -> "PluginSymbol":
    try:
        from .plugins.common.base import Symbol
    except ImportError:
        from plugins.common.base import Symbol
    return Symbol(
        name=d.get("name", ""),
        kind=d.get("kind", ""),
        qualified_name=d.get("qualified_name", ""),
        file=d.get("file", ""),
        start=tuple(d.get("start", [1, 0])),
        end=tuple(d.get("end", [1, 0])),
        scope=d.get("scope", ""),
        type_hint=d.get("type_hint"),
        modifiers=d.get("modifiers", []),
        annotations=d.get("annotations", []),
        lang=d.get("lang", "java"),
    )


# ── Generic edge builders ────────────────────────────────────────────────────────

def _simple_name(qname: str) -> str:
    return qname.split(".")[-1]


def _best_candidates(simple_name: str, ref_qname: str, by_simple: dict) -> list[dict]:
    """Return candidates for simple_name, preferring same-package; skip if ambiguous."""
    candidates = [c for c in by_simple.get(simple_name, [])
                  if c["qualified_name"] != ref_qname]
    ref_pkg = ref_qname.rsplit(".", 1)[0] if "." in ref_qname else ""
    same_pkg = [c for c in candidates if c["qualified_name"].rsplit(".", 1)[0] == ref_pkg]
    if same_pkg:
        return same_pkg
    return candidates if len(candidates) == 1 else []


def _resolve_contains_generic(symbols: list[dict], edges: list[Edge]) -> None:
    by_qname = {s["qualified_name"]: s for s in symbols}
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    for sym in symbols:
        if sym["kind"] not in ("method", "field", "function", "property", "variable"):
            continue
        scope = sym["scope"]
        parent = by_qname.get(scope)
        if parent is None:
            simple_scope = _simple_name(scope)
            candidates = by_simple.get(simple_scope, [])
            parent = next((c for c in candidates
                           if c["kind"] in ("class", "interface", "struct", "enum")), None)
        if parent:
            edges.append(Edge(
                kind="contains",
                from_qname=parent["qualified_name"],
                to_qname=sym["qualified_name"],
                file=sym["file"],
                line=sym["start"][0] if sym.get("start") else 1,
            ))


def _resolve_type_refs_generic(symbols: list[dict], edges: list[Edge]) -> None:
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    for sym in symbols:
        th = sym.get("type_hint")
        if not th:
            continue
        if sym["kind"] == "parameter":
            continue
        simple = th.rstrip("[]").split("<")[0]
        target = _best_candidates(simple, sym["qualified_name"], by_simple)
        kind = "typed_as" if sym["kind"] in ("field", "property") else "returns"
        if target:
            for cand in target:
                edges.append(Edge(
                    kind=kind,
                    from_qname=sym["qualified_name"],
                    to_qname=cand["qualified_name"],
                    file=sym["file"],
                    line=sym["start"][0] if sym.get("start") else 1,
                ))
        else:
            edges.append(Edge(
                kind=kind,
                from_qname=sym["qualified_name"],
                to_qname=f"ext::{simple}",
                file=sym["file"],
                line=sym["start"][0] if sym.get("start") else 1,
            ))


def _resolve_inheritance_generic(symbols: list[dict], ast_data: list[dict], edges: list[Edge]) -> None:
    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
    by_qname = {s["qualified_name"]: s for s in symbols}
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    for sym in symbols:
        if sym["kind"] not in ("class", "interface", "struct", "enum"):
            continue
        ast = by_file.get(sym["file"])
        if ast is None:
            continue
        cls_node = _find_class_node_generic(ast, sym)
        if cls_node is None:
            continue
        _resolve_inheritance_node(cls_node, sym, by_simple, edges)


def _find_class_node_generic(ast: dict, sym: dict) -> Optional[dict]:
    """Find the AST class node matching the symbol.

    Uses only the class name for matching. The line-number heuristic was removed
    because symbol start lines (from 'class' keyword) and AST node start lines
    (from declaration start) can differ, causing nearly all inheritance to be missed.
    """
    class_types = ("class_declaration", "interface_declaration", "enum_declaration",
                   "class_definition", "type_declaration")
    candidates = []
    for n in _find_nodes_generic(ast, class_types):
        name_node = _first_child_generic(n, "identifier", "type_identifier")
        if name_node and _get_text_generic(name_node) == sym["name"]:
            candidates.append(n)
    if len(candidates) == 1:
        return candidates[0]
    # Disambiguate by checking the file path (helps when same class name exists in different files)
    for n in candidates:
        if n["start"][0] == sym["start"][0]:
            return n
    return candidates[0] if candidates else None


def _find_nodes_generic(node: dict, node_types) -> list[dict]:
    found = []
    t = node.get("type", "")
    if isinstance(node_types, str):
        if t == node_types:
            found.append(node)
    elif t in node_types:
        found.append(node)
    for c in node.get("children", []):
        found.extend(_find_nodes_generic(c, node_types))
    return found


def _first_child_generic(node: dict, *types) -> Optional[dict]:
    for c in node.get("children", []):
        if c["type"] in types:
            return c
    return None


def _all_children_of_type(node: dict, *types) -> list[dict]:
    """Return all direct children matching any of the given types."""
    return [c for c in node.get("children", []) if c["type"] in types]


def _get_text_generic(node: dict) -> str:
    if "text" in node:
        return node["text"]
    parts = []
    for c in node.get("children", []):
        parts.append(_get_text_generic(c))
    return "".join(parts)


def _resolve_inheritance_node(cls_node: dict, sym: dict, by_simple: dict, edges: list[Edge]) -> None:
    for child in cls_node.get("children", []):
        ct = child.get("type", "")

        # Java: superclass (extends a single class)
        if ct == "superclass":
            # Children: ['extends', 'type_identifier'] — skip the keyword, get the type
            for c in child.get("children", []):
                if c.get("type") in ("type_identifier", "generic_type", "type",
                                      "scoped_identifier", "identifier"):
                    name = _get_text_generic(c).split("<")[0]
                    if name:
                        target = _best_candidates(name, sym["qualified_name"], by_simple)
                        _emit_inheritance_edges(sym, name, "extends", target,
                                               child["start"][0], edges)
                    break

        # Java: super_interfaces (implements one or more interfaces)
        # Children: ['implements', 'type_list']
        # type_list children: one type_identifier (or scoped_identifier) per interface
        if ct == "super_interfaces":
            type_list_node = None
            for c in child.get("children", []):
                if c.get("type") == "type_list":
                    type_list_node = c
                    break
                # Fallback: if no type_list wrapper, the type is a direct child (some parsers)
                if c.get("type") in ("type_identifier", "generic_type",
                                     "scoped_identifier"):
                    name = _get_text_generic(c).split("<")[0]
                    if name:
                        target = _best_candidates(name, sym["qualified_name"], by_simple)
                        _emit_inheritance_edges(sym, name, "implements", target,
                                               child["start"][0], edges)
            if type_list_node:
                for iface in type_list_node.get("children", []):
                    # Each interface type may be wrapped or direct
                    iface_name = None
                    if iface.get("type") in ("type_identifier", "identifier",
                                             "scoped_identifier", "generic_type"):
                        iface_name = _get_text_generic(iface).split("<")[0]
                    else:
                        # Nested: ['scoped_identifier'/'type_identifier' among others]
                        for c in iface.get("children", []):
                            if c.get("type") in ("type_identifier", "identifier",
                                                "scoped_identifier", "generic_type"):
                                iface_name = _get_text_generic(c).split("<")[0]
                                break
                    if iface_name:
                        target = _best_candidates(iface_name, sym["qualified_name"], by_simple)
                        _emit_inheritance_edges(sym, iface_name, "implements", target,
                                               child["start"][0], edges)

        # Generic extends_interfaces / type_inheritance_clause
        if ct in ("extends_interfaces", "type_inheritance_clause"):
            for c in child.get("children", []):
                if c.get("type") in ("type_identifier", "identifier",
                                     "scoped_identifier", "generic_type"):
                    name = _get_text_generic(c).split("<")[0]
                    if name:
                        kind = "implements" if "interface" in sym.get("kind", "") else "extends"
                        target = _best_candidates(name, sym["qualified_name"], by_simple)
                        _emit_inheritance_edges(sym, name, kind, target,
                                               child["start"][0], edges)

        # Python: class Foo(Base1, Base2)
        if ct == "argument_list":
            for arg in child.get("children", []):
                t = arg.get("type", "")
                if t in ("identifier", "attribute", "generic_type"):
                    name = _get_text_generic(arg).split("<")[0]
                    if name:
                        target = _best_candidates(name, sym["qualified_name"], by_simple)
                        _emit_inheritance_edges(sym, name, "extends", target,
                                               cls_node["start"][0], edges)


def _emit_inheritance_edges(sym: dict, name: str, kind: str, target: list[dict],
                            line: int, edges: list[Edge]) -> None:
    if target:
        for cand in target:
            edges.append(Edge(
                kind=kind,
                from_qname=sym["qualified_name"],
                to_qname=cand["qualified_name"],
                file=sym["file"],
                line=line,
            ))
    else:
        edges.append(Edge(
            kind=kind,
            from_qname=sym["qualified_name"],
            to_qname=f"ext::{name}",
            file=sym["file"],
            line=line,
        ))


def _collect_method_calls_generic(method_node: dict, results: list) -> None:
    if method_node.get("type") == "method_invocation":
        results.append(method_node)
    for c in method_node.get("children", []):
        _collect_method_calls_generic(c, results)


def _collect_field_access_generic(method_node: dict, results: list) -> None:
    if method_node.get("type") == "field_access":
        results.append(method_node)
    for c in method_node.get("children", []):
        _collect_field_access_generic(c, results)


def _lhs_of_assignment(assign_node: dict) -> Optional[dict]:
    children = assign_node.get("children", [])
    return children[0] if children else None


# ── Java-specific: field access (reads/writes) ─────────────────────────────────

def _resolve_field_accesses_java(symbols: list[dict], ast_data: list[dict], edges: list[Edge]) -> None:
    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    for sym in symbols:
        if sym["kind"] != "method":
            continue
        ast = by_file.get(sym["file"])
        if ast is None:
            continue
        method_node = _find_method_node_generic(ast, sym)
        if method_node is None:
            continue

        write_node_ids: set[int] = set()
        for assign in _find_nodes_generic(method_node, "assignment_expression"):
            lhs = _lhs_of_assignment(assign)
            if lhs and lhs["type"] in ("field_access", "identifier"):
                write_node_ids.add(id(lhs))

        write_receiver_ids: set[int] = set()
        for call in _find_nodes_generic(method_node, "method_invocation"):
            if _receiver_node_java(call) is not None:
                write_receiver_ids.add(id(call))

        caller_class = sym.get("scope", "")

        for fa in _find_nodes_generic(method_node, "field_access"):
            field_ident = _last_child_generic(fa, "identifier")
            if field_ident is None:
                continue
            field_name = _get_text_generic(field_ident)
            is_write = id(fa) in write_node_ids
            for cand in by_simple.get(field_name, []):
                if cand["kind"] != "field":
                    continue
                if cand.get("scope") != caller_class:
                    continue
                edges.append(Edge(
                    kind="writes" if is_write else "reads",
                    from_qname=sym["qualified_name"],
                    to_qname=cand["qualified_name"],
                    file=sym["file"],
                    line=fa["start"][0],
                ))

        # Collect IDs of field_access nodes to avoid duplicate processing
        field_access_ids: set[int] = set()
        for fa in _find_nodes_generic(method_node, "field_access"):
            field_access_ids.add(id(fa))

        for ident in _find_nodes_generic(method_node, "identifier"):
            if ident.get("type") != "identifier":
                continue
            if id(ident) in field_access_ids:
                continue
            field_name = _get_text_generic(ident)
            is_write = id(ident) in write_node_ids or id(ident) in write_receiver_ids
            for cand in by_simple.get(field_name, []):
                if cand["kind"] != "field":
                    continue
                if cand.get("scope") != caller_class:
                    continue
                edges.append(Edge(
                    kind="writes" if is_write else "reads",
                    from_qname=sym["qualified_name"],
                    to_qname=cand["qualified_name"],
                    file=sym["file"],
                    line=ident["start"][0],
                ))


def _resolve_instantiates_java(symbols: list[dict], ast_data: list[dict], edges: list[Edge]) -> None:
    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    for sym in symbols:
        if sym["kind"] != "method":
            continue
        ast = by_file.get(sym["file"])
        if ast is None:
            continue
        method_node = _find_method_node_generic(ast, sym)
        if method_node is None:
            continue
        for new_node in _find_nodes_generic(method_node, "object_creation_expression"):
            type_node = _first_child_generic(new_node, "type_identifier", "generic_type")
            if type_node is None:
                continue
            type_name = _get_text_generic(type_node).split("<")[0]
            candidates = [c for c in _best_candidates(type_name, sym["qualified_name"], by_simple)
                         if c["kind"] in ("class", "enum")]
            if candidates:
                for cand in candidates:
                    edges.append(Edge(
                        kind="instantiates",
                        from_qname=sym["qualified_name"],
                        to_qname=cand["qualified_name"],
                        file=sym["file"],
                        line=new_node["start"][0],
                    ))
            else:
                edges.append(Edge(
                    kind="instantiates",
                    from_qname=sym["qualified_name"],
                    to_qname=f"ext::{type_name}",
                    file=sym["file"],
                    line=new_node["start"][0],
                ))


def _resolve_execute_annotations(
    symbols: list[dict],
    ast_data: list[dict],
    edges: list[Edge],
    ui_data: dict | None = None,
) -> None:
    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}

    # Build JSP filename → physical path mapping from ui_data.
    # execute_return uses bare filename (e.g. "JJ901SOLR00301") while jsp_page nodes
    # use physical file paths. We resolve bare names to physical paths for ID matching.
    _jsp_filename_to_physical: dict[str, str] = {}
    if ui_data:
        for jsp_entry in ui_data.get("jsp", []):
            if jsp_entry.get("parse_error"):
                continue
            jsp_path = jsp_entry["file"]
            jsp_filename = Path(jsp_path).name
            # lookup "JJ901SOLR00301.jsp" -> physical path like "test-tool\webapp\JJ901SOLR003\JJ901SOLR00301.jsp"
            bare = jsp_filename[:-4] if jsp_filename.endswith(".jsp") else jsp_filename
            _jsp_filename_to_physical[bare] = jsp_path

    for sym in symbols:
        if sym["kind"] != "method":
            continue
        anns = sym.get("annotations", [])
        if not any("@Execute" in a for a in anns):
            continue
        ast = by_file.get(sym["file"])
        if ast is None:
            continue
        method_node = _find_method_node_generic(ast, sym)
        if method_node is None:
            continue
        for ret in _find_nodes_generic(method_node, "return_statement"):
            expr_parts = []
            started = False
            first_expr_type = None
            for c in ret.get("children", []):
                t = c["type"]
                if t == "return":
                    started = True
                    continue
                if not started:
                    continue
                if t in (";", "comment", "block_comment", "line_comment"):
                    break
                if first_expr_type is None:
                    first_expr_type = t
                    # If the return value is a complex expression (not a plain string literal),
                    # it is a dynamic computation — skip it.
                    if t not in ("string_literal", "element_value", "primary_expression"):
                        break
                expr_parts.append(_get_text_generic(c))
            raw = "".join(expr_parts).strip()
            if (raw.startswith('"') and raw.endswith('"')) or \
               (raw.startswith("'") and raw.endswith("'")):
                raw = raw[1:-1]
            if not raw or raw.lower() in ("null", "true", "false", "success", "input", "error"):
                continue
            # Strip query string (e.g. "/JJ901SOLR00301.jsp?redirect=true" → "/JJ901SOLR00301.jsp")
            raw = raw.split("?")[0].split("#")[0].strip()
            if not raw:
                continue
            # Determine the base name to look up in the JSP filename table.
            # If it starts with "/" it is an absolute-style path; otherwise it is a bare name.
            if raw.startswith("/"):
                base = raw.lstrip("/")
            else:
                base = raw
            # Strip .jsp suffix for bare-name lookup (e.g. "JJ901SOLR00301.jsp" → "JJ901SOLR00301")
            lookup_name = base
            if base.endswith(".jsp"):
                lookup_name = base[:-4]
            else:
                # Also strip trailing slash that may result from query-string stripping
                lookup_name = base.rstrip("/")
            # Try to resolve bare name to webapp-relative path using the JSP filename table.
            resolved = None
            if lookup_name in _jsp_filename_to_physical:
                resolved = _jsp_filename_to_physical[lookup_name]
            # If not found in table, use the normalized path directly.
            if resolved is None:
                resolved = base.rstrip("/").lstrip("/")
            # If .jsp is missing, add it.
            if not resolved.endswith(".jsp"):
                resolved = resolved.rstrip("/") + ".jsp"
            edges.append(Edge(
                kind="execute_return",
                from_qname=sym["qualified_name"],
                        to_qname=f"file::{resolved}",
                file=sym["file"],
                line=ret["start"][0] if "start" in ret else sym["start"][0],
            ))


def _find_method_node_generic(ast: dict, sym: dict) -> Optional[dict]:
    method_types = ("method_declaration", "function_declaration",
                    "method_definition", "function_definition")
    for n in _find_nodes_generic(ast, method_types):
        name_node = _first_child_generic(n, "identifier", "property_identifier")
        if name_node and _get_text_generic(name_node) == sym["name"]:
            if n["start"][0] == sym["start"][0]:
                return n
    return None


def _last_child_generic(node: dict, *types) -> Optional[dict]:
    result = None
    for c in node.get("children", []):
        if c["type"] in types:
            result = c
    return result


def _receiver_node_java(call_node: dict) -> Optional[dict]:
    children = call_node.get("children", [])
    for i, c in enumerate(children):
        if c["type"] == "argument_list" and i >= 3 and children[i - 2]["type"] == ".":
            receiver = children[i - 3]
            if receiver["type"] == "identifier":
                return receiver
    return None


# ── UI edge resolution (Java-specific) ─────────────────────────────────────────

_EXTERNAL_PACKAGES = (
    "java.", "javax.", "org.apache.", "org.springframework.",
    "org.seasar.", "jp.co.ctc.", "r2framework.", "r2.",
    "jp.co.rct.", "jp.ricoh.", "jp.ne.", "jp.yb.",
    "com.sun.", "org.omg.", "org.w3c.", "org.xml.", "org.junit.",
    "org.mockito.", "org.hamcrest.", "org.slf4j.", "ch.qos.",
    "org.hibernate.", "javax.persistence.",
)


def _resolve_ui_edges(ui_data: dict, symbols: list[dict], ast_data: list[dict], edges: list[Edge]) -> None:
    """Generate edges from JSP elements and XML config data (Java-specific)."""
    ast_by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
    by_qname = {s["qualified_name"]: s for s in symbols}
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    action_classes: set[str] = set()
    for s in symbols:
        if s["kind"] in ("class", "interface"):
            if s.get("annotations") and any("@Execute" in a for a in s["annotations"]):
                action_classes.add(s["qualified_name"])
            elif ("Action" in s["qualified_name"] and
                  not any(s["qualified_name"].startswith(p) for p in _EXTERNAL_PACKAGES)):
                action_classes.add(s["qualified_name"])

    form_classes: set[str] = set()
    for s in symbols:
        if s["kind"] == "class":
            if s.get("annotations") and any("@ActionForm" in a for a in s["annotations"]):
                form_classes.add(s["qualified_name"])
            elif ("Form" in s["qualified_name"] and
                  not any(s["qualified_name"].startswith(p) for p in _EXTERNAL_PACKAGES)):
                form_classes.add(s["qualified_name"])

    defined_tags: set[str] = set()
    for entry in ui_data.get("tld", []):
        if "error" not in entry:
            name = entry.get("name", "")
            defined_tags.add(name)
            bare = name.split(":", 1)[-1]
            defined_tags.add(bare)

    _PROJECT_TAG_PREFIXES = ("r2", "jj", "base", "r2logic")

    def _is_project_tag(name: str) -> bool:
        bare = name.split(":", 1)[-1]
        return name.startswith(_PROJECT_TAG_PREFIXES) or bare in _PROJECT_TAG_PREFIXES

    # JSP → Action edges (renders)
    for jsp_entry in ui_data.get("jsp", []):
        if jsp_entry.get("parse_error"):
            continue
        jsp_path = jsp_entry["file"]
        jsp_name = Path(jsp_path).stem
        parent_dir = Path(jsp_path).parent.name
        if jsp_name.startswith(parent_dir):
            inferred_action = parent_dir + "Action"
            for cls in action_classes:
                if cls.endswith("." + inferred_action) or cls.endswith("." + parent_dir + "Action"):
                    edges.append(Edge(
                        kind="renders",
                        from_qname=cls,
                        to_qname=f"file::{jsp_path}",
                        file=jsp_path,
                        line=1,
                    ))
                    break

        for elem in jsp_entry.get("elements", []):
            kind = elem.get("kind", "")
            if kind == "jsp_include":
                target = elem.get("target") or elem.get("attrs", {}).get("file", "")
                if target:
                    edges.append(Edge(
                        kind="includes",
                        from_qname=f"file::{jsp_path}",
                        to_qname=f"file::{target}",
                        file=jsp_path,
                        line=elem.get("line", 1),
                    ))
            elif kind == "jsp_struts_action":
                action_url = elem.get("target") or elem.get("attrs", {}).get("action", "")
                if action_url:
                    edges.append(Edge(
                        kind="action_route",
                        from_qname=f"file::{jsp_path}",
                        to_qname=f"url::{action_url}",
                        file=jsp_path,
                        line=elem.get("line", 1),
                    ))
            elif kind == "jsp_form":
                form_prop = elem.get("target") or elem.get("attrs", {}).get("property", "")
                if form_prop:
                    matched = False
                    for cls in form_classes:
                        if cls.lower().endswith(form_prop.lower()):
                            edges.append(Edge(
                                kind="form_bound",
                                from_qname=f"file::{jsp_path}",
                                to_qname=cls,
                                file=jsp_path,
                                line=elem.get("line", 1),
                            ))
                            matched = True
                            break
                    if not matched:
                        edges.append(Edge(
                            kind="form_bound",
                            from_qname=f"file::{jsp_path}",
                            to_qname=f"ext::Form[{form_prop}]",
                            file=jsp_path,
                            line=elem.get("line", 1),
                        ))
            elif kind in ("jsp_custom_tag", "jsp_struts_tag"):
                tag_name = elem.get("tag_name", "")
                bare = tag_name.split(":", 1)[-1] if ":" in tag_name else tag_name
                if tag_name in defined_tags or bare in defined_tags:
                    if not _is_project_tag(tag_name):
                        continue
                    edges.append(Edge(
                        kind="uses_tag",
                        from_qname=f"file::{jsp_path}",
                        to_qname=f"tag::{tag_name}",
                        file=jsp_path,
                        line=elem.get("line", 1),
                    ))

    # TLD tag → TLD file (defined_in) + handler class (bound_to)
    for entry in ui_data.get("tld", []):
        if "error" in entry:
            continue
        tag_name = entry.get("name", "")
        if not _is_project_tag(tag_name):
            continue
        tag_qname = f"tag::{tag_name}"
        tld_file = entry.get("file", "")
        # defined_in: tag is declared in this TLD file
        if tld_file:
            edges.append(Edge(
                kind="defined_in",
                from_qname=tag_qname,
                to_qname=f"file::{tld_file}",
                file=tld_file,
                line=entry.get("line", 0),
            ))
        # bound_to: tag implementation is this handler class
        handler = entry.get("handler_class", "")
        if handler:
            is_external = any(handler.startswith(p) for p in _EXTERNAL_PACKAGES)
            to_qname = f"ext::{handler}" if is_external else handler
            edges.append(Edge(
                kind="bound_to",
                from_qname=tag_qname,
                to_qname=to_qname,
                file=tld_file,
                line=entry.get("line", 0),
            ))

    # struts-config.xml → Action URL mapping
    for xml_entry in ui_data.get("xml", []):
        if not xml_entry or xml_entry.get("parse_error"):
            continue
        if "action_mappings" not in xml_entry:
            continue
        xml_path = xml_entry["file"]
        for action_map in xml_entry.get("action_mappings", []):
            attrs = action_map.get("attrs", {})
            path = attrs.get("path", "")
            type_cls = attrs.get("type", "")
            if path and type_cls:
                edges.append(Edge(
                    kind="action_route",
                    from_qname=type_cls,
                    to_qname=f"url::{path}",
                    file=xml_path,
                    line=action_map.get("line", 0),
                ))
                for fwd in action_map.get("forwards", []):
                    fwd_path = fwd.get("path", "")
                    if fwd_path and fwd_path.endswith(".jsp"):
                        fwd_path = fwd_path.lstrip("/")
                        edges.append(Edge(
                            kind="forward_route",
                            from_qname=type_cls,
                            to_qname=f"file::{fwd_path}",
                            file=xml_path,
                            line=action_map.get("line", 0),
                        ))
            for fwd in action_map.get("forwards", []):
                fwd_name = fwd.get("name", "")
                fwd_path = fwd.get("path", "")
                if fwd_name and fwd_path:
                    if fwd_path.endswith(".jsp"):
                        fwd_path = fwd_path.lstrip("/")
                        to_qname = f"file::{fwd_path}"
                    else:
                        to_qname = f"url::{fwd_path}"
                    edges.append(Edge(
                        kind="forward_route",
                        from_qname=f"forward::{fwd_name}",
                        to_qname=to_qname,
                        file=xml_path,
                        line=action_map.get("line", 0),
                    ))
        for fb in xml_entry.get("form_beans", []):
            attrs = fb.get("attrs", {})
            name = attrs.get("name", "")
            cls = attrs.get("type", "")
            if name and cls:
                edges.append(Edge(
                    kind="form_bound",
                    from_qname=f"formbean::{name}",
                    to_qname=cls,
                    file=xml_path,
                    line=fb.get("line", 0),
                ))
        for gfwd in xml_entry.get("global_forwards", []):
            attrs = gfwd.get("attrs", {})
            gname = attrs.get("name", "")
            gpath = attrs.get("path", "")
            if gname and gpath:
                if gpath.endswith(".jsp"):
                    gpath = gpath.lstrip("/")
                    to_qname = f"file::{gpath}"
                else:
                    to_qname = f"url::{gpath}"
                edges.append(Edge(
                    kind="forward_route",
                    from_qname=f"forward::{gname}",
                    to_qname=to_qname,
                    file=xml_path,
                    line=gfwd.get("line", 0),
                ))

    # ── Forward chain resolution ──────────────────────────────────────────────────
    # Forward chains: <forward name="A" forward="B"/> means A → B.
    # We resolve to the final JSP destination for impact analysis.
    _fwd_to_jsp: dict[str, str] = {}
    _fwd_to_fwd: dict[str, str] = {}
    for xml_entry in ui_data.get("xml", []):
        if xml_entry.get("parse_error"):
            continue
        if "action_mappings" in xml_entry:
            for am in xml_entry.get("action_mappings", []):
                for fwd in am.get("forwards", []):
                    fname = fwd.get("name", "")
                    fpath = fwd.get("path", "")
                    fwd_ref = fwd.get("forward", "")
                    if not fname:
                        continue
                    if fpath and fpath.endswith(".jsp"):
                        _fwd_to_jsp[fname] = fpath.lstrip("/")
                    if fwd_ref:
                        _fwd_to_fwd[fname] = fwd_ref
        global_fwds = xml_entry.get("_global_forwards", {})
        for fname, fpath in global_fwds.items():
            if fpath.endswith(".jsp"):
                _fwd_to_jsp[fname] = fpath.lstrip("/")

    def _resolve_fwd_chain(start: str) -> str | None:
        visited: set[str] = set()
        cur = start
        while cur not in visited:
            visited.add(cur)
            if cur in _fwd_to_jsp:
                return _fwd_to_jsp[cur]
            if cur in _fwd_to_fwd:
                cur = _fwd_to_fwd[cur]
            else:
                return None
        return None

    _fwd_chain_done: set[tuple[str, str]] = set()
    for e in edges:
        if e.kind != "forward_route":
            continue
        if not (e.from_qname.startswith("forward::") and e.to_qname.startswith("forward::")):
            continue
        from_fwd = e.from_qname[9:]
        to_fwd = e.to_qname[9:]
        final_jsp = _resolve_fwd_chain(to_fwd)
        if final_jsp:
            key = (from_fwd, final_jsp)
            if key not in _fwd_chain_done:
                edges.append(Edge(
                    kind="forward_route",
                    from_qname=e.from_qname,
                    to_qname=f"file::{final_jsp}",
                    file=e.file,
                    line=e.line,
                ))
                _fwd_chain_done.add(key)

    # ── JSP → Action reverse edges (jsp_entry) ──────────────────────────────────
    _jsp_to_action: dict[str, str] = {}
    for e in edges:
        if e.kind == "execute_return" and e.to_qname.startswith("file::"):
            jsp_ref = e.to_qname[5:]
            jsp_filename = Path(jsp_ref).name
            if jsp_filename and e.from_qname:
                _jsp_to_action[jsp_filename] = e.from_qname
    for e in edges:
        if e.kind == "forward_route" and e.to_qname.startswith("file::"):
            jsp_ref = e.to_qname[5:]
            jsp_filename = Path(jsp_ref).name
            if jsp_filename and e.from_qname and "." in e.from_qname and jsp_filename not in _jsp_to_action:
                _jsp_to_action[jsp_filename] = e.from_qname

    _jsp_entry_done: set[str] = set()
    for jsp_entry in ui_data.get("jsp", []):
        if jsp_entry.get("parse_error"):
            continue
        jsp_path = jsp_entry["file"]
        jsp_filename = Path(jsp_path).name
        if not jsp_filename or jsp_filename in _jsp_entry_done:
            continue
        action_method = _jsp_to_action.get(jsp_filename)
        if action_method:
            edges.append(Edge(
                kind="jsp_entry",
                from_qname=f"file::{jsp_path}",
                to_qname=action_method,
                file=jsp_path,
                line=1,
            ))
            _jsp_entry_done.add(jsp_filename)

    # .dicon → Action/Form DI bindings
    for dicon_entry in ui_data.get("dicon", []):
        if dicon_entry.get("parse_error"):
            continue
        for comp in dicon_entry.get("components", []):
            cls = comp.get("class", "")
            if not cls or any(cls.startswith(p) for p in _EXTERNAL_PACKAGES):
                continue
            if "Creator" in cls:
                continue
            edges.append(Edge(
                kind="di_component",
                from_qname=f"dicon::{Path(dicon_entry['file']).name}",
                to_qname=cls,
                file=dicon_entry["file"],
                line=comp.get("line", 0),
            ))


def _find_all_method_nodes(ast: dict, method_name: str, start_line: int) -> list[dict]:
    results = []
    def _search(node: dict):
        if node.get("type") == "method_declaration":
            for c in node.get("children", []):
                if c["type"] == "identifier":
                    if _get_text_generic(c) == method_name and node.get("start", [0])[0] == start_line:
                        results.append(node)
                    break
        for c in node.get("children", []):
            _search(c)
    _search(ast)
    return results


def _find_return_statements(method_node: dict) -> list[dict]:
    results = []
    def _search(node: dict):
        if node.get("type") == "return_statement":
            results.append(node)
        for c in node.get("children", []):
            _search(c)
    _search(method_node)
    return results


def _get_return_text(ret_node: dict) -> str:
    children = ret_node.get("children", [])
    expr_parts = []
    started = False
    for c in children:
        t = c["type"]
        if t == "return":
            started = True
            continue
        if not started:
            continue
        if t in (";", "comment", "line_comment", "block_comment"):
            break
        # Stop at any complex expression — a valid forward target is just a plain string literal.
        # This catches cases like: return cookie1.getName() + ".jsp"
        if expr_parts and t in (
            "identifier", "method_invocation", "binary_expression",
            "field_access", "object_creation_expression", "assignment_expression",
        ):
            break
        expr_parts.append(_get_text_generic(c))
    raw = "".join(expr_parts).strip()
    if (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1]
    return raw


# ── Legacy Java-only path (backward-compatible) ─────────────────────────────────

def _resolve_java(typed_data: dict, ast_data: list[dict], ui_data: dict | None = None) -> dict:
    """Legacy Java-only reference resolution. Preserved for backward compatibility."""
    # Import the original Java-specific logic from the refactored code
    # We call the same internal functions but with full Java behavior
    symbols = typed_data["symbols"]
    edges: list[Edge] = []

    by_qname = {s["qualified_name"]: s for s in symbols}
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)

    # contains
    for sym in symbols:
        if sym["kind"] not in ("method", "field"):
            continue
        scope = sym["scope"]
        parent = by_qname.get(scope)
        if parent is None:
            simple_scope = _simple_name(scope)
            candidates = by_simple.get(simple_scope, [])
            parent = next((c for c in candidates
                           if c["kind"] in ("class", "interface", "enum")), None)
        if parent:
            edges.append(Edge(
                kind="contains",
                from_qname=parent["qualified_name"],
                to_qname=sym["qualified_name"],
                file=sym["file"],
                line=sym["start"][0],
            ))

    # typed_as / returns
    for sym in symbols:
        th = sym.get("type_hint")
        if not th:
            continue
        if sym["kind"] == "parameter":
            continue
        simple = th.rstrip("[]").split("<")[0]
        target = _best_candidates(simple, sym["qualified_name"], by_simple)
        kind = "typed_as" if sym["kind"] == "field" else "returns"
        if target:
            for cand in target:
                edges.append(Edge(
                    kind=kind,
                    from_qname=sym["qualified_name"],
                    to_qname=cand["qualified_name"],
                    file=sym["file"],
                    line=sym["start"][0],
                ))
        else:
            edges.append(Edge(
                kind=kind,
                from_qname=sym["qualified_name"],
                to_qname=f"ext::{simple}",
                file=sym["file"],
                line=sym["start"][0],
            ))

    # extends / implements
    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
    for sym in symbols:
        if sym["kind"] not in ("class", "interface", "enum"):
            continue
        ast = by_file.get(sym["file"])
        if ast is None:
            continue
        cls_node = _find_class_node_generic(ast, sym)
        if cls_node is None:
            continue
        _resolve_inheritance_node(cls_node, sym, by_simple, edges)

    # field accesses
    _resolve_field_accesses_java(symbols, ast_data, edges)

    # method calls
    _resolve_calls_java(symbols, ast_data, by_simple, edges)

    # instantiates
    _resolve_instantiates_java(symbols, ast_data, edges)

    # @Execute annotations
    _resolve_execute_annotations(symbols, ast_data, edges, ui_data)

    # UI edges
    if ui_data:
        _resolve_ui_edges(ui_data, symbols, ast_data, edges)

    return {
        "symbols": symbols,
        "edges": [e.__dict__ if hasattr(e, "__dict__") else e for e in edges],
    }


def _resolve_calls_java(symbols: list[dict], ast_data: list[dict],
                         by_simple: dict, edges: list[Edge]) -> None:
    by_file: dict[str, dict] = {e["file"]: e["ast"] for e in ast_data}
    _COLLECTION_TYPES = frozenset((
        "List", "ArrayList", "LinkedList", "Set", "HashSet", "LinkedHashSet",
        "TreeSet", "Map", "HashMap", "LinkedHashMap", "TreeMap",
        "Collection", "Iterable", "Iterator", "Enumeration",
        "Stream", "Optional", "OptionalInt", "OptionalLong",
    ))
    _PROJECT_PKG_PREFIXES = ("jp.",)

    for sym in symbols:
        if sym["kind"] != "method":
            continue
        ast = by_file.get(sym["file"])
        if ast is None:
            continue
        method_node = _find_method_node_generic(ast, sym)
        if method_node is None:
            continue
        call_nodes: list[dict] = []
        _collect_method_calls_generic(method_node, call_nodes)
        caller_class = sym.get("scope", "")

        for call in call_nodes:
            callee_name = _last_identifier_before_args_java(call)
            if callee_name is None:
                continue
            receiver_node = _receiver_node_java(call)
            receiver_text = _get_text_generic(receiver_node) if receiver_node else None
            receiver_type = None
            if receiver_text:
                receiver_type = _get_receiver_type_java(call, sym["file"], symbols)

            candidates = by_simple.get(callee_name, [])
            method_candidates = [c for c in candidates if c["kind"] == "method"]
            same_class = [c for c in method_candidates if c.get("scope") == caller_class]
            if same_class:
                resolved = same_class[0]
            elif len(method_candidates) == 1:
                candidate = method_candidates[0]
                cand_pkg = candidate["qualified_name"].rsplit(".", 1)[0] if "." in candidate["qualified_name"] else ""
                is_project_candidate = any(cand_pkg.startswith(p) for p in _PROJECT_PKG_PREFIXES)
                if receiver_text is None:
                    resolved = candidate
                elif is_project_candidate and receiver_type:
                    recv_pkg = receiver_type.rsplit(".", 1)[0] if "." in receiver_type else ""
                    recv_simple = receiver_type.rstrip("[]").split("<")[0].split(".")[-1]
                    if recv_simple in _COLLECTION_TYPES:
                        resolved = None
                    elif (recv_pkg.startswith("jp.") and
                          recv_pkg != cand_pkg and
                          receiver_type != candidate.get("scope")):
                        resolved = None
                    else:
                        resolved = candidate
                elif is_project_candidate:
                    resolved = None
                else:
                    resolved = None
            else:
                resolved = None

            if resolved:
                edges.append(Edge(
                    kind="call",
                    from_qname=sym["qualified_name"],
                    to_qname=resolved["qualified_name"],
                    file=sym["file"],
                    line=call["start"][0],
                ))
            else:
                if receiver_text is None and receiver_node:
                    receiver_text = _get_text_generic(receiver_node)
                edges.append(Edge(
                    kind="call",
                    from_qname=sym["qualified_name"],
                    to_qname=f"ext::{callee_name}",
                    file=sym["file"],
                    line=call["start"][0],
                    receiver=receiver_text,
                ))
                if receiver_type:
                    ext_type = f"ext::{receiver_type}"
                    edges.append(Edge(
                        kind="contains",
                        from_qname=ext_type,
                        to_qname=f"ext::{callee_name}",
                        file=sym["file"],
                        line=call["start"][0],
                    ))


def _get_receiver_type_java(call_node: dict, caller_file: str, symbols: list[dict]) -> Optional[str]:
    children = call_node.get("children", [])
    receiver_name = None
    dot_seen = False
    for c in reversed(children):
        ct = c["type"]
        if ct == "argument_list":
            continue
        if ct == "identifier":
            if dot_seen:
                receiver_name = _get_text_generic(c)
                break
            continue
        if ct == ".":
            dot_seen = True
            continue
        break
    by_simple: dict[str, list[dict]] = {}
    for s in symbols:
        by_simple.setdefault(s["name"], []).append(s)
    for sym in by_simple.get(receiver_name, []):
        if sym.get("type_hint") and sym["file"] == caller_file:
            return sym["type_hint"].rstrip("[]").split("<")[0]
    for sym in by_simple.get(receiver_name, []):
        if sym.get("type_hint"):
            return sym["type_hint"].rstrip("[]").split("<")[0]
    return None


def _last_identifier_before_args_java(call_node: dict) -> Optional[str]:
    children = call_node.get("children", [])
    last_ident = None
    for c in children:
        if c["type"] == "argument_list":
            break
        if c["type"] == "identifier":
            last_ident = _get_text_generic(c)
    return last_ident


# ── Standalone CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    typed_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/stage3_typed.json")
    ast_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/stage1_ast.json")
    out = Path("output/stage4_refs.json")
    typed_data = json.loads(typed_path.read_text(encoding="utf-8"))
    ast_data = json.loads(ast_path.read_text(encoding="utf-8"))
    result = resolve_references(typed_data, ast_data)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Stage 4 complete: {len(result['edges'])} edges -> {out}")
