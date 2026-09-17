from __future__ import annotations

import re
from collections import Counter
from typing import Any


RISK_TERMS = {
    "高": ["登录", "权限", "支付", "订单", "退款", "删除", "上传", "下载", "隐私", "安全", "账号", "认证", "同步", "并发"],
    "中": ["搜索", "筛选", "导出", "通知", "推荐", "编辑", "保存", "历史", "版本", "接口", "缓存", "超时"],
}

CATEGORY_TERMS = {
    "账号与权限": ["登录", "注册", "账号", "用户", "权限", "认证", "角色"],
    "数据输入": ["上传", "输入", "导入", "填写", "选择", "提交", "创建", "新增", "编辑"],
    "查询与展示": ["搜索", "查询", "筛选", "展示", "列表", "详情", "排序", "看板"],
    "数据处理": ["解析", "分析", "计算", "生成", "匹配", "识别", "转换", "拖拽"],
    "数据输出": ["导出", "下载", "报告", "结果", "通知"],
    "系统可靠性": ["超时", "失败", "异常", "重试", "并发", "缓存", "实时"],
}

VAGUE_TERMS = ["尽快", "友好", "适当", "较快", "高效", "智能", "等", "相关"]


def _split_requirements(text: str) -> list[str]:
    """Turn common PRD prose and numbered lists into stable requirement items."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"(?<!\n)(?=\s*\d+[.、)]\s*)", "\n", normalized)
    raw_lines = [re.sub(r"^[\s\-*•\d.、)（(]+", "", line).strip() for line in normalized.split("\n")]

    items: list[str] = []
    for line in raw_lines:
        if not line:
            continue
        chunks = [line]
        if len(line) > 100:
            chunks = re.split(r"[。；;](?=\S)", line)
        for chunk in chunks:
            cleaned = chunk.strip(" ，,。；;")
            if re.match(r"^(产品|项目|版本|模块|文档)[：:]", cleaned):
                continue
            if len(cleaned) >= 6:
                items.append(cleaned)

    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = re.sub(r"\s+", "", item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result[:24]


def _category(text: str) -> str:
    scores = {
        category: sum(1 for word in words if word in text)
        for category, words in CATEGORY_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "通用功能"


def _risk(text: str) -> tuple[str, list[str], str]:
    high_hits = [word for word in RISK_TERMS["高"] if word in text]
    medium_hits = [word for word in RISK_TERMS["中"] if word in text]
    if high_hits:
        hits = high_hits[:4]
        return "高", hits, f"涉及{ '、'.join(hits) }，需优先验证权限边界与数据一致性"
    if medium_hits:
        hits = medium_hits[:4]
        return "中", hits, f"涉及{ '、'.join(hits) }，需覆盖失败恢复与边界条件"
    return "低", [], "常规业务功能，按主流程、边界和异常场景验证"


def _acceptance(text: str, category: str) -> str:
    if category == "账号与权限":
        return "合法身份可访问授权资源；未登录、越权和失效凭证均被拒绝，且不泄露受限数据。"
    if category == "数据输入":
        return "合法输入可成功提交并正确落库；空值、非法格式、超限和重复提交均有明确反馈且不产生脏数据。"
    if category == "查询与展示":
        return "正常、空结果及组合条件下均返回准确结果；筛选条件可复现，刷新前后状态与数据保持一致。"
    if category == "数据处理":
        return "处理成功时输出完整且可追踪；输入异常或依赖失败时给出明确原因，并保证原有数据一致性。"
    if category == "数据输出":
        return "导出内容与当前数据及筛选条件一致；文件可打开、字段完整，空数据和生成失败时反馈明确。"
    if category == "系统可靠性":
        return "依赖超时或失败时系统可恢复、可重试且不重复写入；状态反馈明确，核心数据保持一致。"
    return "主流程可完成；边界输入、异常状态和重复操作均得到一致、可验证的系统反馈。"


def _quality_flags(text: str) -> list[str]:
    flags: list[str] = []
    if any(term in text for term in VAGUE_TERMS):
        flags.append("存在模糊表述，建议补充量化口径")
    if not re.search(r"\d", text) and any(term in text for term in ["超时", "长度", "大小", "数量", "实时"]):
        flags.append("缺少明确阈值")
    if not any(term in text for term in ["失败", "异常", "错误", "重试", "提示"]):
        flags.append("未描述失败分支")
    return flags[:2]


def analyze_requirements(text: str) -> list[dict[str, Any]]:
    items = _split_requirements(text) or ["系统应支持用户提交需求并获得测试分析结果"]
    requirements: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        category = _category(item)
        risk, hits, reason = _risk(item)
        requirements.append(
            {
                "id": f"REQ-{index:02d}",
                "text": item,
                "category": category,
                "risk": risk,
                "risk_keywords": hits,
                "risk_reason": reason,
                "acceptance": _acceptance(item, category),
                "quality_flags": _quality_flags(item),
            }
        )
    return requirements


def _case(
    req: dict[str, Any],
    number: int,
    case_type: str,
    title: str,
    precondition: str,
    steps: list[str],
    expected: str,
    priority: str,
    automation: str,
    automation_reason: str,
) -> dict[str, Any]:
    return {
        "id": f"TC-{number:03d}",
        "req_id": req["id"],
        "module": req["category"],
        "type": case_type,
        "title": title,
        "precondition": precondition,
        "steps": steps,
        "expected": expected,
        "priority": priority,
        "risk": req["risk"],
        "automation": automation,
        "automation_reason": automation_reason,
    }


def generate_test_cases(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    number = 1
    for req in requirements:
        short = req["text"][:30] + ("…" if len(req["text"]) > 30 else "")
        base_priority = "P0" if req["risk"] == "高" else "P1" if req["risk"] == "中" else "P2"

        cases.append(
            _case(
                req,
                number,
                "主流程",
                f"{short} · 正常完成",
                "系统可用，测试账号具备正常访问条件。",
                ["准备符合要求的合法数据", "按用户主流程完成操作", "核对页面反馈、接口返回与数据落库结果"],
                req["acceptance"],
                base_priority,
                "建议自动化",
                "流程稳定且预期明确，适合作为核心回归用例。",
            )
        )
        number += 1

        cases.append(
            _case(
                req,
                number,
                "边界",
                f"{short} · 空值、上限与重复操作",
                "系统可用，可构造边界测试数据。",
                ["分别准备空值、临界值、超限值和重复请求", "逐一执行功能操作", "核对校验提示、幂等处理和数据一致性"],
                "所有边界输入均有确定结果；不得出现崩溃、重复脏数据或静默失败。",
                "P1" if req["risk"] != "低" else "P2",
                "建议自动化",
                "输入组合可参数化，适合数据驱动测试。",
            )
        )
        number += 1

        cases.append(
            _case(
                req,
                number,
                "异常",
                f"{short} · 非法输入与依赖失败",
                "可模拟非法参数、断网或下游服务异常。",
                ["提交非法或缺失参数", "模拟依赖超时或服务失败", "检查错误码、用户提示、重试与数据回滚"],
                "系统拒绝非法输入；依赖异常时反馈清晰且可恢复，核心数据保持一致。",
                "P0" if req["risk"] == "高" else "P1",
                "接口优先",
                "异常注入在接口层更稳定，UI 保留关键提示校验。",
            )
        )
        number += 1

        if req["category"] == "账号与权限" or any(word in req["text"] for word in ["登录", "权限", "账号", "认证", "角色"]):
            cases.append(
                _case(
                    req,
                    number,
                    "权限",
                    f"{short} · 未登录与越权访问",
                    "准备未登录、低权限及高权限三类身份。",
                    ["使用不同身份访问受限资源", "尝试读取和修改非授权数据", "检查状态码、页面提示、审计记录与响应内容"],
                    "未授权访问必须被拒绝；授权用户仅能访问权限范围内的数据，响应不得泄露敏感字段。",
                    "P0",
                    "建议自动化",
                    "权限矩阵需持续回归，适合接口自动化覆盖。",
                )
            )
            number += 1

    return cases


def build_summary(requirements: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    risks = Counter(req["risk"] for req in requirements)
    types = Counter(case["type"] for case in cases)
    priorities = Counter(case["priority"] for case in cases)
    covered = len({case["req_id"] for case in cases})
    coverage = round(covered / max(len(requirements), 1) * 100)
    automatable = sum(1 for case in cases if case["automation"] in {"建议自动化", "接口优先"})
    flagged = sum(1 for req in requirements if req.get("quality_flags"))
    diversity = min(len(types) / 4, 1)
    completeness = round(min(100, coverage * 0.55 + diversity * 25 + (1 - flagged / max(len(requirements), 1)) * 20))

    if risks.get("高", 0):
        release_advice = f"有 {risks['高']} 项高风险需求，建议完成全部 P0 用例后再进入发布评审。"
        release_level = "需关注"
    elif flagged:
        release_advice = f"有 {flagged} 项需求存在口径缺口，建议确认后再冻结测试范围。"
        release_level = "待澄清"
    else:
        release_advice = "当前需求未发现高风险项，可按优先级推进测试设计评审。"
        release_level = "可评审"

    return {
        "requirement_count": len(requirements),
        "case_count": len(cases),
        "coverage": coverage,
        "completeness": completeness,
        "high_risk_requirements": risks.get("高", 0),
        "p0_count": priorities.get("P0", 0),
        "automatable_count": automatable,
        "flagged_requirements": flagged,
        "risk_distribution": dict(risks),
        "type_distribution": dict(types),
        "priority_distribution": dict(priorities),
        "release_advice": release_advice,
        "release_level": release_level,
    }
