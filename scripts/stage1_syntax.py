"""Stage 1: Syntax Parsing — tree-sitter AST extraction.

Now language-agnostic via plugins. Falls back to Java for backward compatibility
when no --lang is specified and the legacy Java-only API is used.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from tqdm import tqdm

from tree_sitter import Parser

import tree_sitter_java as tsjava
from tree_sitter import Language


# ── Legacy Java parser (backward-compatible default) ────────────────────────────

_JAVA_LANGUAGE = Language(tsjava.language())
_JAVA_PARSER = Parser(_JAVA_LANGUAGE)


# ── AST node model ─────────────────────────────────────────────────────────────

@dataclass
class ASTNode:
    type: str
    text: Optional[str]
    start: tuple[int, int]   # (line, col), 1-indexed
    end: tuple[int, int]
    children: list["ASTNode"] = field(default_factory=list)


def _build_node(node, source_bytes: bytes) -> ASTNode:
    text = None
    if node.child_count == 0:
        text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    children = [_build_node(c, source_bytes) for c in node.children]
    return ASTNode(
        type=node.type,
        start=(node.start_point[0] + 1, node.start_point[1]),
        end=(node.end_point[0] + 1, node.end_point[1]),
        text=text,
        children=children,
    )


def _node_to_dict(node: ASTNode) -> dict:
    d: dict = {"type": node.type, "start": node.start, "end": node.end}
    if node.text is not None:
        d["text"] = node.text
    if node.children:
        d["children"] = [_node_to_dict(c) for c in node.children]
    return d


# ── Plugin-based parsing ───────────────────────────────────────────────────────

def _get_plugin_registry():
    """Import LanguageRegistry, handling both package and standalone execution."""
    try:
        from .plugins import LanguageRegistry
    except ImportError:
        from plugins import LanguageRegistry
    return LanguageRegistry


def _make_parser(lang_pkg: str):
    """Create a tree-sitter Parser for the given package name."""
    import importlib
    mod = importlib.import_module(lang_pkg)
    lang = Language(mod.language())
    p = Parser(lang)
    return p


def parse_file_plugin(file_path: Path, lang_id: str, parser: Parser) -> dict:
    """Parse a single file using the given parser."""
    try:
        source = file_path.read_bytes()
        tree = parser.parse(source)
        root = _build_node(tree.root_node, source)
        return {"file": str(file_path), "ast": _node_to_dict(root), "parse_error": False}
    except Exception as e:
        return {"file": str(file_path), "ast": None, "parse_error": True, "error_msg": str(e)}


def parse_directory(
    src_root: Path,
    lang: Optional[str] = None,
) -> list[dict]:
    """Parse all source files for the given language using plugins.

    If lang is None, falls back to legacy Java-only behavior.
    """
    if lang is None:
        # Legacy Java-only behavior for backward compatibility
        results = []
        for java_file in sorted(src_root.rglob("*.java")):
            results.append(_parse_file_legacy(java_file))
        return results

    # Plugin-based: dynamically resolve the parser
    Registry = _get_plugin_registry()
    plugin = Registry.get(lang)
    lang_pkg = plugin.get_tree_sitter_package()
    parser = _make_parser(lang_pkg)

    results = []
    for pattern in plugin.get_file_patterns():
        for file_path in sorted(src_root.rglob(pattern)):
            results.append(parse_file_plugin(file_path, lang, parser))

    # Deduplicate by file path (a file may match multiple patterns)
    seen: dict[str, dict] = {}
    for entry in results:
        if entry["file"] not in seen:
            seen[entry["file"]] = entry
    return list(seen.values())


def _parse_files_with_lang(
    src_root: Path,
    lang: str,
    files: list[Path],
) -> list[dict]:
    """Parse a specific list of files using the given language plugin.

    Args:
        src_root: Source root (used only for pattern matching context).
        lang: Language plugin ID.
        files: Explicit list of file paths to parse (already filtered).

    Returns:
        List of AST dicts, one per file.
    """
    Registry = _get_plugin_registry()
    plugin = Registry.get(lang)
    lang_pkg = plugin.get_tree_sitter_package()
    parser = _make_parser(lang_pkg)

    from tqdm import tqdm
    results = []
    for file_path in tqdm(files, desc=f"  Parsing {lang}", unit="file", ncols=80):
        results.append(parse_file_plugin(file_path, lang, parser))

    # Deduplicate by file path
    seen: dict[str, dict] = {}
    for entry in results:
        if entry["file"] not in seen:
            seen[entry["file"]] = entry
    return list(seen.values())


def _parse_file_legacy(path: Path) -> dict:
    """Legacy Java-only parse_file for backward compatibility."""
    try:
        source = path.read_bytes()
        tree = _JAVA_PARSER.parse(source)
        root = _build_node(tree.root_node, source)
        return {"file": str(path), "ast": _node_to_dict(root), "parse_error": False}
    except Exception as e:
        return {"file": str(path), "ast": None, "parse_error": True, "error_msg": str(e)}


# ── Standalone CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser_arg = argparse.ArgumentParser(description="Stage 1: Parse source files")
    parser_arg.add_argument("root", nargs="?", type=Path, default=None,
                            help="Source root directory (default: src/main/java or src)")
    parser_arg.add_argument("-o", "--out", type=Path, default=Path("output/stage1_ast.json"),
                            help="Output path (default: output/stage1_ast.json)")
    parser_arg.add_argument("--lang", type=str, default=None,
                            choices=["java", "python", "javascript", "go", "cpp"],
                            help="Language plugin to use (default: java)")
    args = parser_arg.parse_args()

    if args.root is None:
        src = Path("src/main/java") if Path("src/main/java").exists() else Path("src")
        if not src.exists():
            src = Path(".")
        args.root = src

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    data = parse_directory(args.root, args.lang)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Stage 1 complete: {len(data)} files -> {out}")
