from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, Response, flash, redirect, render_template, request, url_for

from db import get_analysis, init_db, list_analyses, save_analysis
from engine import analyze_requirements, build_summary, generate_test_cases
from llm_provider import analyze_with_llm, available as llm_available

# Keep Flask's static route for local/Docker runs; Vercel also serves the
# mirrored public/ directory directly from its CDN.
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "testpilot-local-dev")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
init_db()

SAMPLE_PRD = """
产品：团队任务看板 V1.0
1. 用户可以使用邮箱和密码登录系统，不同角色拥有不同项目权限。
2. 用户可以创建项目，并在项目中新增、编辑、删除任务。
3. 任务支持标题、描述、负责人、优先级、截止日期和状态字段。
4. 用户可以按负责人、状态和优先级组合筛选任务，并支持关键词搜索。
5. 看板支持拖拽修改任务状态，操作结果需实时保存，2 秒内完成状态同步。
6. 用户可以将当前筛选结果导出为 CSV，导出文件需包含全部可见字段。
7. 当接口超时或保存失败时，需明确提示用户并允许重试，不得产生重复任务。
""".strip()


def _run_analysis(project_name: str, source_text: str, mode: str) -> tuple[int, str]:
    actual_mode = mode
    if mode == "llm" and llm_available():
        requirements, cases = analyze_with_llm(source_text)
    else:
        if mode == "llm":
            flash("未检测到大模型配置，已切换至稳定的本地分析引擎。", "info")
            actual_mode = "rules"
        requirements = analyze_requirements(source_text)
        cases = generate_test_cases(requirements)

    summary = build_summary(requirements, cases)
    analysis_id = save_analysis(project_name, source_text, actual_mode, requirements, cases, summary)
    return analysis_id, actual_mode


@app.get("/")
def index():
    analyses = list_analyses()
    total_cases = sum(item["summary"].get("case_count", 0) for item in analyses)
    high_risks = sum(item["summary"].get("high_risk_requirements", 0) for item in analyses)
    completeness_values = [item["summary"].get("completeness", 0) for item in analyses]
    overview = {
        "analysis_count": len(analyses),
        "case_count": total_cases,
        "high_risks": high_risks,
        "avg_completeness": round(sum(completeness_values) / len(completeness_values)) if completeness_values else 0,
    }
    return render_template(
        "index.html",
        analyses=analyses,
        sample_prd=SAMPLE_PRD,
        llm_ready=llm_available(),
        overview=overview,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/analyze")
def analyze():
    project_name = request.form.get("project_name", "").strip() or "未命名项目"
    source_text = request.form.get("requirement_text", "").strip()
    mode = request.form.get("mode", "rules")

    if len(source_text) < 12:
        flash("需求内容过短，请至少提供一段可分析的产品需求。", "error")
        return redirect(url_for("index"))

    try:
        analysis_id, _ = _run_analysis(project_name, source_text, mode)
    except Exception as exc:
        if mode != "llm":
            raise
        flash(f"AI 增强调用失败，已使用本地引擎完成分析：{exc}", "info")
        analysis_id, _ = _run_analysis(project_name, source_text, "rules")
    return redirect(url_for("detail", analysis_id=analysis_id))


@app.post("/demo")
def demo():
    mode = request.form.get("mode", "rules")
    try:
        analysis_id, _ = _run_analysis("团队任务看板 V1.0", SAMPLE_PRD, mode)
    except Exception as exc:
        if mode != "llm":
            raise
        flash(f"AI 示例分析失败，已使用本地引擎完成：{exc}", "info")
        analysis_id, _ = _run_analysis("团队任务看板 V1.0", SAMPLE_PRD, "rules")
    return redirect(url_for("detail", analysis_id=analysis_id))


@app.get("/analysis/<int:analysis_id>")
def detail(analysis_id: int):
    item = get_analysis(analysis_id)
    if not item:
        return render_template("404.html"), 404
    return render_template("detail.html", item=item)


@app.get("/analysis/<int:analysis_id>/export/<fmt>")
def export(analysis_id: int, fmt: str):
    item = get_analysis(analysis_id)
    if not item:
        return render_template("404.html"), 404

    filename_base = f"testpilot_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    if fmt == "json":
        payload = json.dumps(
            {
                "project_name": item["project_name"],
                "requirements": item["requirements"],
                "cases": item["cases"],
                "summary": item["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
        return Response(
            payload,
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
        )

    if fmt == "csv":
        output = io.StringIO()
        fields = ["id", "req_id", "module", "type", "title", "precondition", "steps", "expected", "priority", "risk", "automation"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for case in item["cases"]:
            row = case.copy()
            row["steps"] = " -> ".join(row.get("steps", []))
            writer.writerow(row)
        return Response(
            "\ufeff" + output.getvalue(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    if fmt == "md":
        summary = item["summary"]
        lines = [
            f"# {item['project_name']} - TestPilot 测试设计报告",
            "",
            f"- 需求数：{summary.get('requirement_count', 0)}",
            f"- 测试用例数：{summary.get('case_count', 0)}",
            f"- 需求覆盖率：{summary.get('coverage', 0)}%",
            f"- 方案完整度：{summary.get('completeness', 0)}%",
            f"- 高风险需求：{summary.get('high_risk_requirements', 0)}",
            f"- 发布建议：{summary.get('release_advice', '')}",
            "",
            "## 需求与风险",
            "",
        ]
        for req in item["requirements"]:
            lines.extend(
                [
                    f"### {req['id']} · {req['category']} · {req['risk']}风险",
                    req["text"],
                    "",
                    f"**风险依据：** {req.get('risk_reason', '-')}",
                    "",
                    f"**验收标准：** {req['acceptance']}",
                    "",
                ]
            )
        lines.extend(["## 测试用例", ""])
        for case in item["cases"]:
            lines.extend(
                [
                    f"### {case['id']} · {case['priority']} · {case['type']}",
                    f"**{case['title']}**",
                    "",
                    f"- 关联需求：{case['req_id']}",
                    f"- 前置条件：{case['precondition']}",
                    f"- 步骤：{'；'.join(case['steps'])}",
                    f"- 预期结果：{case['expected']}",
                    f"- 自动化建议：{case.get('automation', '-')}（{case.get('automation_reason', '-')}）",
                    "",
                ]
            )
        return Response(
            "\n".join(lines),
            content_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
        )

    return "Unsupported format", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
