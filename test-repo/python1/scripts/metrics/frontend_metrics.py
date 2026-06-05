# -*- coding: utf-8 -*-
"""
前端指标采集：目录结构、文件行数、超长文件、api 模块与路径、views 列表等。
输出 JSON 到 stdout。在项目根目录执行：python scripts/metrics/frontend_metrics.py
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_SRC = ROOT / "src" / "frontend" / "src"
if not FRONTEND_SRC.exists():
    print(json.dumps({"error": "src/frontend/src not found", "root": str(ROOT)}, ensure_ascii=False, indent=2))
    sys.exit(1)

ALLOWED_TOP_LEVEL = {
    "api", "config", "constants", "router", "stores", "views", "layouts", "components",
    "assets", "styles", "utils", "directives", "hooks", "language", "main.js", "App.vue",
}

def count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def extract_api_paths(api_dir: Path) -> list:
    paths = []
    for f in api_dir.glob("**/*.js"):
        if "node_modules" in str(f) or "__tests__" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # request.get("/path", ...) or request.post("/path", ...)
            for m in re.finditer(r'request\.(get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']', text):
                method, path = m.group(1), m.group(2)
                paths.append({"module": f.name, "method": method.upper(), "path": path})
        except Exception:
            pass
    return paths

def collect():
    top_level = []
    for p in sorted(FRONTEND_SRC.iterdir()):
        name = p.name
        if p.is_dir():
            top_level.append({"name": name, "type": "dir"})
        else:
            top_level.append({"name": name, "type": "file"})

    allowed_set = set(ALLOWED_TOP_LEVEL)
    actual = {e["name"] for e in top_level}
    unexpected = actual - allowed_set

    file_lines = []
    files_over_400 = []
    api_modules = []
    api_paths = []
    views_list = []

    for root, dirs, files in os.walk(FRONTEND_SRC):
        root_path = Path(root)
        if "node_modules" in root or ".git" in root:
            continue
        rel_root = root_path.relative_to(FRONTEND_SRC) if root_path != FRONTEND_SRC else Path(".")
        for f in files:
            full = root_path / f
            rel = rel_root / f
            if full.suffix in (".vue", ".js", ".ts", ".jsx", ".tsx"):
                lines = count_lines(full)
                file_lines.append({"path": str(rel).replace("\\", "/"), "lines": lines})
                if lines > 400:
                    files_over_400.append({"path": str(rel).replace("\\", "/"), "lines": lines})
            if "api" in rel.parts and "modules" in rel.parts and f.endswith(".js"):
                api_modules.append(str(rel).replace("\\", "/"))
            if "views" in rel.parts and f.endswith(".vue"):
                views_list.append(str(rel).replace("\\", "/"))

    api_dir = FRONTEND_SRC / "api" / "modules"
    if api_dir.exists():
        api_paths = extract_api_paths(api_dir)

    out = {
        "frontend_src": str(FRONTEND_SRC),
        "allowed_top_level": list(allowed_set),
        "actual_top_level": [e["name"] for e in top_level],
        "unexpected_top_level": list(unexpected),
        "dir_structure_ok": len(unexpected) == 0,
        "file_lines": file_lines,
        "files_over_400_lines": files_over_400,
        "api_modules": api_modules,
        "api_paths": api_paths,
        "views_list": views_list,
        "summary": {
            "total_js_vue_files": len(file_lines),
            "files_over_400": len(files_over_400),
            "api_modules_count": len(api_modules),
            "api_paths_count": len(api_paths),
            "views_count": len(views_list),
            "unexpected_entries": len(unexpected),
        },
    }
    return out

if __name__ == "__main__":
    try:
        result = collect()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
