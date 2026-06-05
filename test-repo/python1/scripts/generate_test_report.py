# -*- coding: utf-8 -*-
"""执行测试并生成图文测试报告。在项目根运行: python scripts/generate_test_report.py"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
SCREENSHOTS = REPORTS / "screenshots"
FRONTEND = ROOT / "src" / "frontend"
FRONTEND_RESULTS = FRONTEND / "test-results"

REPORTS.mkdir(exist_ok=True)
SCREENSHOTS.mkdir(exist_ok=True)


def run(cmd: list, cwd: Path, shell: bool = False) -> tuple[str, int]:
    if shell and isinstance(cmd, list):
        cmd = " ".join(cmd)
    r = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=shell,
    )
    out = (r.stdout or "") + (r.stderr or "")
    return out, r.returncode


def parse_passed_failed(text: str) -> tuple[str, str]:
    m = re.search(r"(\d+) passed", text)
    passed = m.group(1) if m else "?"
    m = re.search(r"(\d+) failed", text)
    failed = m.group(1) if m else "0"
    return passed, failed


def main():
    os.environ["PYTHONPATH"] = str(ROOT / "src")
    backend_log = REPORTS / "backend-test.log"
    unit_log = REPORTS / "frontend-unit.log"
    e2e_log = REPORTS / "frontend-e2e.log"

    print("Running backend tests...")
    out, _ = run([sys.executable, "-m", "pytest", "src/backend/tests", "-v", "--tb=line", "-q"], ROOT)
    backend_log.write_text(out, encoding="utf-8")
    b_pass, b_fail = parse_passed_failed(out)

    print("Running frontend unit tests...")
    out, _ = run(["npm", "run", "test:run"], FRONTEND, shell=os.name == "nt")
    unit_log.write_text(out, encoding="utf-8")
    u_pass, u_fail = parse_passed_failed(out)

    print("Running E2E tests...")
    out, _ = run(["npx", "playwright", "test"], FRONTEND, shell=os.name == "nt")
    e2e_log.write_text(out, encoding="utf-8")
    e_pass, e_fail = parse_passed_failed(out)

    # Copy screenshots
    src_ss = FRONTEND_RESULTS / "screenshots"
    if src_ss.exists():
        for f in src_ss.glob("*.png"):
            (SCREENSHOTS / f.name).write_bytes(f.read_bytes())
    for f in FRONTEND_RESULTS.rglob("test-failed-*.png"):
        (SCREENSHOTS / f"failed-{f.parent.name}.png").write_bytes(f.read_bytes())

    # Build report
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    b_ok = "通过" if b_fail == "0" else "未通过"
    u_ok = "通过" if u_fail == "0" else "未通过"
    e_ok = "通过" if e_fail == "0" else "未通过"

    lines = [
        "# 图文测试报告",
        "",
        f"**生成时间**：{now}",
        "",
        "## 一、汇总",
        "",
        "| 维度 | 通过 | 失败 | 状态 |",
        "|------|------|------|------|",
        f"| 后端 pytest | {b_pass} | {b_fail} | {b_ok} |",
        f"| 前端 Vitest | {u_pass} | {u_fail} | {u_ok} |",
        f"| 前端 E2E | {e_pass} | {e_fail} | {e_ok} |",
        "",
        "## 二、E2E 截图",
        "",
    ]
    if (SCREENSHOTS / "login-page.png").exists():
        lines.extend(["### 登录页", "", "![登录页](screenshots/login-page.png)", ""])
    for f in sorted(SCREENSHOTS.glob("failed-*.png")):
        lines.extend([f"![{f.stem}](screenshots/{f.name})", ""])
    lines.extend([
        "## 三、详细结果",
        "",
        "详见：",
        "- reports/backend-test.log",
        "- reports/frontend-unit.log",
        "- reports/frontend-e2e.log",
        "",
    ])

    report_path = REPORTS / "test-report-with-screenshots.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
