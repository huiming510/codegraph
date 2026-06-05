"""Stage 3: Type Inference — infers types for variables, methods, and fields."""

import json
from pathlib import Path
from typing import Optional


# Primitive / well-known type aliases
_PRIMITIVES = {"int", "long", "double", "float", "boolean", "char", "byte", "short"}


def _unbox(t: Optional[str]) -> Optional[str]:
    """Normalise simple boxed types to their primitives for display."""
    if t is None:
        return None
    box_map = {
        "Integer": "int", "Long": "long", "Double": "double",
        "Float": "float", "Boolean": "boolean", "Character": "char",
        "Byte": "byte", "Short": "short",
    }
    return box_map.get(t, t)


def _infer_from_initialiser(ast_nodes_by_file: dict, file: str,
                             start: tuple, end: tuple) -> Optional[str]:
    """Very lightweight: look at variable_declarator initialiser literal type."""
    # We skip deep AST traversal here — type_hint from Stage 2 is authoritative.
    # This function is a hook for future enhancement.
    return None


class TypeInferer:
    def __init__(self, symbols: list[dict]):
        # Build index: qualified_name → symbol
        self._by_qname: dict[str, dict] = {s["qualified_name"]: s for s in symbols}
        # Build index: (file, scope, name) → symbol for local lookup
        self._by_local: dict[tuple, dict] = {}
        for s in symbols:
            key = (s["file"], s["scope"], s["name"])
            self._by_local[key] = s

    def infer_all(self, symbols: list[dict]) -> list[dict]:
        enriched = []
        for s in symbols:
            s = dict(s)
            if not s.get("type_hint"):
                s["type_hint"] = self._infer(s)
            s["type_hint"] = _unbox(s.get("type_hint"))
            enriched.append(s)
        return enriched

    def _infer(self, sym: dict) -> Optional[str]:
        kind = sym["kind"]
        if kind == "method" and not sym.get("type_hint"):
            # If constructor-like (same name as enclosing class), return class type
            scope_parts = sym["scope"].split(".")
            if scope_parts and sym["name"] == scope_parts[-1]:
                return scope_parts[-1]
        if kind == "field" and not sym.get("type_hint"):
            return "Object"
        return sym.get("type_hint")

    def resolve_field_type(self, class_qname: str, field_name: str) -> Optional[str]:
        for sym in self._by_qname.values():
            if sym["kind"] == "field" and sym["name"] == field_name:
                if sym["scope"] == class_qname:
                    return sym.get("type_hint")
        return None


def infer_types(symbols_data: dict) -> dict:
    symbols = symbols_data["symbols"]
    inferer = TypeInferer(symbols)
    enriched = inferer.infer_all(symbols)
    return {"symbols": enriched}


if __name__ == "__main__":
    import sys
    sym_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/stage2_symbols.json")
    out = Path("output/stage3_typed.json")
    data = json.loads(sym_path.read_text(encoding="utf-8"))
    result = infer_types(data)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Stage 3 complete: {len(result['symbols'])} symbols with types → {out}")
