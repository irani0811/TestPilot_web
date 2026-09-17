from __future__ import annotations

import json
import os
from typing import Any

import requests


ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["账号与权限", "数据输入", "查询与展示", "数据处理", "数据输出", "系统可靠性", "通用功能"],
                    },
                    "risk": {"type": "string", "enum": ["高", "中", "低"]},
                    "risk_keywords": {"type": "array", "items": {"type": "string"}},
                    "risk_reason": {"type": "string"},
                    "acceptance": {"type": "string"},
                    "quality_flags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "text", "category", "risk", "risk_keywords", "risk_reason", "acceptance", "quality_flags"],
                "additionalProperties": False,
            },
        },
        "cases": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "req_id": {"type": "string"},
                    "module": {"type": "string"},
                    "type": {"type": "string", "enum": ["主流程", "边界", "异常", "权限"]},
                    "title": {"type": "string"},
                    "precondition": {"type": "string"},
                    "steps": {"type": "array", "minItems": 2, "items": {"type": "string"}},
                    "expected": {"type": "string"},
                    "priority": {"type": "string", "enum": ["P0", "P1", "P2"]},
                    "risk": {"type": "string", "enum": ["高", "中", "低"]},
                    "automation": {"type": "string", "enum": ["建议自动化", "接口优先", "优先手工"]},
                    "automation_reason": {"type": "string"},
                },
                "required": ["id", "req_id", "module", "type", "title", "precondition", "steps", "expected", "priority", "risk", "automation", "automation_reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["requirements", "cases"],
    "additionalProperties": False,
}


def available() -> bool:
    return bool(os.getenv("LLM_API_URL") and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL"))


def analyze_with_llm(source_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Call an optional OpenAI-compatible endpoint. The local engine remains the fallback."""
    url = os.environ["LLM_API_URL"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    prompt = f"""
你是一名测试产品经理。请将下面的需求转换为 JSON，只返回 JSON，不要使用 Markdown。

JSON schema:
{{
  "requirements": [{{
    "id": "REQ-01", "text": "需求原文或归纳", "category": "账号与权限/数据输入/查询与展示/数据处理/数据输出/系统可靠性/通用功能",
    "risk": "高/中/低", "risk_keywords": ["关键词"], "risk_reason": "风险判断依据", "acceptance": "可验证验收标准", "quality_flags": []
  }}],
  "cases": [{{
    "id": "TC-001", "req_id": "REQ-01", "module": "需求分类", "type": "主流程/边界/异常/权限",
    "title": "测试标题", "precondition": "前置条件", "steps": ["步骤1", "步骤2"], "expected": "预期结果",
    "priority": "P0/P1/P2", "risk": "高/中/低", "automation": "建议自动化/接口优先/优先手工", "automation_reason": "建议依据"
  }}]
}}

要求：不得返回空数组。每条需求至少包含主流程、边界和异常三类用例；高风险功能优先级设为 P0/P1；验收标准必须可验证。

需求文本：
{source_text}
""".strip()

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "Content-Type": "application/json"},
        json={
            "model": os.environ["LLM_MODEL"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "test_analysis", "schema": ANALYSIS_SCHEMA},
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:].strip()
    data = json.loads(content)
    requirements = data["requirements"]
    cases = data["cases"]
    if not requirements or not cases:
        raise ValueError("模型返回了空的需求或测试用例")
    requirement_ids = {item["id"] for item in requirements}
    if any(case["req_id"] not in requirement_ids for case in cases):
        raise ValueError("模型返回的测试用例存在无效需求关联")
    return requirements, cases
