# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/26 13:43
# @Author  : dingsh
# @Description:
AI代码元素抽取模块
使用大模型从代码中提取类和方法信息，
"""

import os


def safe_read_file(file_path, encodings=None):
    """安全地读取文件，尝试多种编码"""
    if encodings is None:
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {str(e)}")
            return None
    print(f"无法使用任何编码读取文件: {file_path}")
    return None


def extract_with_ai(file_path):
    """使用AI从文件中提取类和方法信息"""
    classes = []
    methods = []

    try:
        # 安全地读取文件内容
        code = safe_read_file(file_path)
        if code is None:
            return classes, methods

        # 检查是否配置了AI API
        ai_api_url = os.environ.get('LLM_API_URL')
        if not ai_api_url:
            print(f"未配置AI API URL，使用默认处理方式: {file_path}")
            # 使用简单的启发式方法分割代码
            return simple_split(code)

        # 构造prompt
        prompt = f"""请从以下代码中提取所有的类和方法/函数，按以下JSON格式返回：
{{
  "classes": [
    {{
      "name": "类名",
      "content": "类的完整代码",
      "start_line": 起始行号,
      "end_line": 结束行号
    }}
  ],
  "methods": [
    {{
      "name": "方法名/函数名",
      "content": "方法/函数的完整代码",
      "start_line": 起始行号,
      "end_line": 结束行号
    }}
  ]
}}

如果代码中没有明显的类或方法结构，请根据代码的逻辑结构进行合理的分割。

代码内容：
{code}"""

        # 调用AI API
        import requests
        import json

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {os.environ.get('LLM_API_KEY', 'your-api-key')}"
        }

        data = {
            "model": os.environ.get('LLM_MODEL', 'your-model'),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }

        response = requests.post(ai_api_url, headers=headers, json=data)
        response.raise_for_status()

        # 解析响应
        result = response.json()
        content = result['choices'][0]['message']['content']

        # 提取JSON部分
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            parsed_result = json.loads(json_str)
            classes = parsed_result.get('classes', [])
            methods = parsed_result.get('methods', [])

        return classes, methods

    except Exception as e:
        print(f"使用AI处理文件 {file_path} 时出错: {str(e)}")
        # 出错时回退到简单分割方法
        code = safe_read_file(file_path)
        if code is None:
            return classes, methods
        return simple_split(code)


def simple_split(code) -> list[dict]:
    """简单的代码分割方法，作为AI调用失败时的备选方案"""
    classes = []
    methods = []

    lines = code.split('\n')
    if len(lines) >= 5:  # 只处理至少5行的文件
        # 简单示例：将文件分为两部分
        mid = len(lines) // 2
        if mid > 2:
            classes.append({
                "name": "part1",
                "content": '\n'.join(lines[:mid]),
                "start_line": 1,
                "end_line": mid
            })
        if len(lines) - mid > 2:
            methods.append({
                "name": "part2",
                "content": '\n'.join(lines[mid:]),
                "start_line": mid + 1,
                "end_line": len(lines)
            })

    return classes, methods


def extract(file_path) -> list[dict]:
    """
    使用AI从文件中提取类和方法信息
    """
    return extract_with_ai(file_path)
