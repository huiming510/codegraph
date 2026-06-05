"""Stage 2: Symbol Table Building — traverses AST to build scoped symbol table.

Now language-agnostic via plugins. Falls back to Java for backward compatibility.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from tqdm import tqdm

# ── Legacy Symbol dataclass (backward-compatible) ────────────────────────────────

@dataclass
class Symbol:
    name: str
    kind: str
    qualified_name: str
    file: str
    start: tuple[int, int]
    end: tuple[int, int]
    scope: str
    type_hint: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    lang: str = "java"


# ── Plugin-based symbol table building ──────────────────────────────────────────

def build_symbol_table(
    ast_data: list[dict],
    lang: Optional[str] = None,
    src_root: str = "",
) -> dict:
    """Build symbol table from AST data using language plugins.

    If lang is None, falls back to legacy Java-only behavior.
    """
    if lang is None:
        # Legacy Java-only path
        return _build_java_symbol_table(ast_data)

    try:
        from .plugins import LanguageRegistry
        from .plugins.common.base import Symbol as PluginSymbol
    except ImportError:
        from plugins import LanguageRegistry
        from plugins.common.base import Symbol as PluginSymbol

    plugin = LanguageRegistry.get(lang)
    all_symbols: list[dict] = []

    for entry in tqdm(ast_data, desc=f"  Stage 2", unit="file", ncols=80):
        syms = plugin.build_symbols(entry, src_root)
        for s in syms:
            all_symbols.append(s.to_dict())

    return {"symbols": all_symbols}


# ── Legacy Java symbol table (backward-compatible) ────────────────────────────────

def _build_java_symbol_table(ast_data: list[dict]) -> dict:
    """Original Java-only symbol table builder. Kept for backward compatibility."""
    builder = _JavaSymbolTableBuilder()
    all_symbols: list[dict] = []
    for entry in ast_data:
        syms = builder.build(entry)
        for s in syms:
            all_symbols.append(s.__dict__)
    return {"symbols": all_symbols}


class _JavaSymbolTableBuilder:
    def __init__(self):
        self.symbols: list[Symbol] = []
        self._scope_stack: list[str] = []
        self._package: str = ""
        self._file: str = ""

    def _current_scope(self) -> str:
        return ".".join(self._scope_stack) if self._scope_stack else "<global>"

    def _push_scope(self, name: str):
        self._scope_stack.append(name)

    def _pop_scope(self):
        if self._scope_stack:
            self._scope_stack.pop()

    def _qualified(self, name: str) -> str:
        parts = [p for p in [self._package, *self._scope_stack, name] if p]
        return ".".join(parts)

    def build(self, ast_entry: dict) -> list[Symbol]:
        self.symbols = []
        self._scope_stack = []
        self._package = ""
        self._file = ast_entry["file"]
        if ast_entry.get("parse_error") or ast_entry.get("ast") is None:
            return []
        self._visit(ast_entry["ast"])
        return self.symbols

    def _get_text(self, node: dict) -> str:
        if "text" in node:
            return node["text"]
        for c in node.get("children", []):
            t = self._get_text(c)
            if t:
                return t
        return ""

    def _children_of_type(self, node: dict, *types) -> list[dict]:
        return [c for c in node.get("children", []) if c["type"] in types]

    def _first_child(self, node: dict, *types) -> Optional[dict]:
        for c in node.get("children", []):
            if c["type"] in types:
                return c
        return None

    def _collect_modifiers(self, node: dict) -> tuple[list[str], list[str]]:
        mods, anns = [], []
        for c in node.get("children", []):
            if c["type"] == "modifiers":
                for m in c.get("children", []):
                    if m["type"] in ("marker_annotation", "annotation"):
                        ann = self._get_text(self._first_child(m, "identifier") or m)
                        anns.append("@" + ann)
                    elif m["type"] in ("public", "private", "protected", "static",
                                       "final", "abstract", "synchronized"):
                        mods.append(m["type"])
        return mods, anns

    def _type_text(self, node: dict) -> str:
        if node is None:
            return ""
        t = node.get("type", "")
        if t in ("type_identifier", "void_type", "integral_type",
                 "floating_point_type", "boolean_type"):
            return self._get_text(node)
        if t == "array_type":
            return self._type_text(node["children"][0]) + "[]"
        if t in ("generic_type",):
            return self._get_text(node)
        return self._get_text(node)

    def _visit(self, node: dict):
        t = node.get("type", "")

        if t == "package_declaration":
            name_node = self._first_child(node, "scoped_identifier", "identifier")
            self._package = self._get_text(name_node) if name_node else ""
            return

        if t in ("class_declaration", "interface_declaration", "enum_declaration"):
            name_node = self._first_child(node, "identifier")
            name = self._get_text(name_node) if name_node else "<anon>"
            mods, anns = self._collect_modifiers(node)
            kind = "interface" if t == "interface_declaration" else (
                "enum" if t == "enum_declaration" else "class")
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
            )
            self.symbols.append(sym)
            self._push_scope(name)
            for c in node.get("children", []):
                self._visit(c)
            self._pop_scope()
            return

        if t == "method_declaration":
            name_node = self._first_child(node, "identifier")
            name = self._get_text(name_node) if name_node else "<anon>"
            mods, anns = self._collect_modifiers(node)
            ret_node = self._first_child(node, "void_type", "type_identifier",
                                          "array_type", "generic_type",
                                          "integral_type", "floating_point_type",
                                          "boolean_type")
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
            )
            self.symbols.append(sym)
            self._push_scope(name)
            for c in node.get("children", []):
                self._visit(c)
            self._pop_scope()
            return

        if t == "field_declaration":
            mods, anns = self._collect_modifiers(node)
            type_node = self._first_child(node, "type_identifier", "array_type",
                                           "generic_type", "integral_type",
                                           "floating_point_type", "boolean_type",
                                           "void_type")
            for declarator in self._children_of_type(node, "variable_declarator"):
                name_node = self._first_child(declarator, "identifier")
                name = self._get_text(name_node) if name_node else "<anon>"
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
                )
                self.symbols.append(sym)
            return

        if t == "formal_parameter":
            type_node = self._first_child(node, "type_identifier", "array_type",
                                           "generic_type", "integral_type",
                                           "floating_point_type", "boolean_type",
                                           "void_type")
            name_node = self._first_child(node, "identifier")
            if name_node:
                name = self._get_text(name_node)
                sym = Symbol(
                    name=name,
                    kind="parameter",
                    qualified_name=self._qualified(name),
                    file=self._file,
                    start=tuple(node["start"]),
                    end=tuple(node["end"]),
                    scope=self._current_scope(),
                    type_hint=self._type_text(type_node),
                )
                self.symbols.append(sym)
            return

        for c in node.get("children", []):
            self._visit(c)


# ── Standalone CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Stage 2: Extract symbols from AST")
    parser.add_argument("ast", type=Path, help="AST JSON from stage 1")
    parser.add_argument("-o", "--out", type=Path, default=Path("output/stage2_symbols.json"),
                        help="Output path (default: output/stage2_symbols.json)")
    parser.add_argument("--lang", type=str, default=None,
                        choices=["java", "python", "javascript", "go", "cpp"],
                        help="Language plugin (default: java)")
    parser.add_argument("--src-root", type=str, default="",
                        help="Source root directory")
    args = parser.parse_args()

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    ast_data = json.loads(args.ast.read_text(encoding="utf-8"))
    result = build_symbol_table(ast_data, lang=args.lang, src_root=args.src_root)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Stage 2 complete: {len(result['symbols'])} symbols -> {out}")
