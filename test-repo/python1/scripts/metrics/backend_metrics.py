# -*- coding: utf-8 -*-
"""Backend metrics: dir structure, file lines, oversized files, router list. Output JSON to stdout."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "src" / "backend"
if not BACKEND.exists():
    print(json.dumps({"error": "src/backend not found"}, ensure_ascii=False, indent=2))
    sys.exit(1)

ALLOWED_TOP = {"main.py", "config.py", "database", "routers", "llm", "logger", "server",
    "migrate_db.py", "migrate_add_es_id.py", "migrate_add_es_id.sql", "migrate_add_model_config.py",
    "requirements.txt", ".env.example", "README.md"}

def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def collect():
    actual = {p.name for p in BACKEND.iterdir()}
    unexpected = actual - ALLOWED_TOP
    unexpected = {u for u in unexpected if not u.startswith(".") and u != "__pycache__"}

    file_lines = []
    over_400 = []
    router_files = []
    for root, dirs, files in os.walk(BACKEND):
        if "__pycache__" in root or ".venv" in root:
            continue
        root_path = Path(root)
        rel_root = root_path.relative_to(BACKEND) if root_path != BACKEND else Path(".")
        for f in files:
            if not f.endswith(".py"):
                continue
            full = root_path / f
            rel = rel_root / f
            lines = count_lines(full)
            path_str = str(rel).replace("\\", "/")
            file_lines.append({"path": path_str, "lines": lines})
            if lines > 400:
                over_400.append({"path": path_str, "lines": lines})
            if "routers" in rel.parts and f.endswith(".py") and f != "__init__.py":
                router_files.append(path_str)

    return {
        "backend_root": str(BACKEND),
        "allowed_top_level": list(ALLOWED_TOP),
        "actual_top_level": list(actual),
        "unexpected_top_level": list(unexpected),
        "dir_structure_ok": len(unexpected) == 0,
        "file_count_py": len(file_lines),
        "file_lines": file_lines,
        "files_over_400_lines": over_400,
        "router_files": router_files,
        "summary": {"total_py_files": len(file_lines), "files_over_400": len(over_400), "unexpected_entries": len(unexpected)},
    }

if __name__ == "__main__":
    try:
        print(json.dumps(collect(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
