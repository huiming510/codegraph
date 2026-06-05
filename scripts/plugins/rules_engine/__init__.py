"""
CodeGraph Rules Engine
======================
规则文件驱动的跨文件分析引擎核心模块。

目录结构:
    schema.py          - Pydantic models for rule file schema
    v1/
        rule_ast.py    - Rule AST classes + RuleASTBuilder
        operators.py   - Operator definitions
    bundles/
        built-in/      - 内置规则包
            java-orm/
            web-framework/
            examples/
    tests/
"""

from __future__ import annotations

__version__ = "1.0.0"
