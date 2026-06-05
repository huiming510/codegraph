# -*- coding: utf-8 -*-
"""
前后端 API 路径 diff：从后端 routers 与前端 api/modules 提取路径，生成 diff 报告。
在项目根目录执行：python scripts/metrics/api_path_diff.py
输出：reports/api-path-diff.md
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROUTERS = ROOT / "src" / "backend" / "routers"
REPORT_PATH = ROOT / "reports" / "api-path-diff.md"


def _normalize_path(p: str) -> str:
    """统一路径格式：去掉末尾斜杠，保留前缀 /api。"""
    if not p:
        return "/"
    s = ("/" + p.strip()).replace("//", "/")
    return s if s != "" else "/"


def collect_backend_routes() -> list[tuple[str, str]]:
    """从 routers/*.py 解析 prefix 与 @router.METHOD("path")，返回 [(method, full_path), ...]。"""
    routes = []
    if not BACKEND_ROUTERS.exists():
        return routes
    for f in sorted(BACKEND_ROUTERS.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        prefix_m = re.search(r'APIRouter\s*\(\s*prefix\s*=\s*["\']([^"\']*)["\']', text)
        prefix = (prefix_m.group(1) if prefix_m else "").strip()
        prefix = _normalize_path(prefix).rstrip("/") or ""
        for m in re.finditer(r"@router\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']*)[\"']", text):
            method, path = m.group(1).upper(), m.group(2).strip()
            if path == "":
                full = prefix if prefix else "/"
            else:
                full = (prefix + "/" + path.lstrip("/")).replace("//", "/")
            full = _normalize_path(full).rstrip("/") or "/"
            routes.append((method, full))
    return routes


def _normalize_path_param(p: str) -> str:
    """将路径中的 ${var} 或 {var} 规范为 {id} 便于前后端对比。"""
    return re.sub(r"\$\{[^}]+\}", "{id}", re.sub(r"\{[^}]+\}", "{id}", p))


def collect_frontend_paths() -> list[tuple[str, str]]:
    """从 frontend api/modules 提取 request.get/post/put/delete 的 path，规范化为带 /api 的完整路径。"""
    api_dir = ROOT / "src" / "frontend" / "src" / "api" / "modules"
    if not api_dir.exists():
        return []
    paths = []
    for f in api_dir.rglob("*.js"):
        if "node_modules" in str(f) or "__tests__" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # 支持 "path"、'path'、`path`（含 ${id}）
        for m in re.finditer(r"(?:request|http)\.(get|post|put|delete)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", text):
            method, path = m.group(1).upper(), m.group(2).strip()
            path = _normalize_path_param(path)
            full = path if path.startswith("/api") else ("/api" + path if path.startswith("/") else "/api/" + path)
            full = _normalize_path(full).rstrip("/") or "/"
            paths.append((method, full))
    return paths


def main() -> str:
    backend = list(set(collect_backend_routes()))
    frontend = list(set(collect_frontend_paths()))
    # 路径参数统一为 {id} 便于前后端对比
    back_set = {(m, _normalize_path_param(p)) for m, p in backend}
    front_set = {(m, p) for m, p in frontend}  # 前端已在 collect 里规范化
    only_backend = sorted(back_set - front_set, key=lambda x: (x[1], x[0]))
    only_frontend = sorted(front_set - back_set, key=lambda x: (x[1], x[0]))
    matched = sorted(back_set & front_set, key=lambda x: (x[1], x[0]))

    lines = [
        "# 前后端 API 路径 Diff 报告",
        "",
        "> 后端从 `src/backend/routers/*.py` 解析；前端从 `src/frontend/src/api/modules/*.js` 的 request/http 调用解析。",
        "",
        "## 汇总",
        "",
        f"- 仅后端有: {len(only_backend)}",
        f"- 仅前端有: {len(only_frontend)}",
        f"- 两端一致: {len(matched)}",
        "",
        "## 仅后端有（前端未调用）",
        "",
    ]
    if only_backend:
        for method, path in only_backend:
            lines.append(f"- `{method} {path}`")
        lines.append("")
    else:
        lines.append("（无）")
        lines.append("")

    lines.append("## 仅前端有（后端未注册或路径不一致）")
    lines.append("")
    if only_frontend:
        for method, path in only_frontend:
            lines.append(f"- `{method} {path}`")
        lines.append("")
    else:
        lines.append("（无）")
        lines.append("")

    lines.append("## 两端一致")
    lines.append("")
    if matched:
        for method, path in matched:
            lines.append(f"- `{method} {path}`")
    else:
        lines.append("（无）")

    return "\n".join(lines)


if __name__ == "__main__":
    try:
        report = main()
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"Report written to {REPORT_PATH}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
