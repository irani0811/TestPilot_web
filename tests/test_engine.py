import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
import db
from engine import analyze_requirements, build_summary, generate_test_cases


SAMPLE = """
1. 用户可以使用邮箱登录系统，不同角色拥有不同项目权限。
2. 用户可以按状态筛选任务，并将当前结果导出为 CSV。
3. 当保存接口超时或失败时，系统需要提示用户并允许重试。
"""


class EngineTests(unittest.TestCase):
    def test_analysis_builds_traceable_test_assets(self):
        requirements = analyze_requirements(SAMPLE)
        cases = generate_test_cases(requirements)
        summary = build_summary(requirements, cases)

        self.assertEqual(len(requirements), 3)
        self.assertGreaterEqual(len(cases), len(requirements) * 3)
        self.assertEqual(summary["coverage"], 100)
        self.assertTrue(any(case["type"] == "权限" for case in cases))
        self.assertTrue(any(case["automation"] == "建议自动化" for case in cases))
        self.assertTrue(all(case["req_id"].startswith("REQ-") for case in cases))
        self.assertIn(summary["release_level"], {"需关注", "待澄清", "可评审"})

    def test_requirement_quality_flags_missing_threshold(self):
        requirements = analyze_requirements("任务状态需要实时同步并支持接口超时重试")
        self.assertIn("缺少明确阈值", requirements[0]["quality_flags"])


class WebFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "testpilot_test.db"
        db.init_db()
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_home_page_is_available(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("测试设计工作台".encode(), response.data)

    def test_health_check_is_available(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_analyze_and_export_flow(self):
        response = self.client.post(
            "/analyze",
            data={"project_name": "回归测试项目", "requirement_text": SAMPLE, "mode": "rules"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        detail_url = response.headers["Location"]

        detail = self.client.get(detail_url)
        self.assertEqual(detail.status_code, 200)
        self.assertIn("需求覆盖追踪".encode(), detail.data)
        self.assertIn("回归测试项目".encode(), detail.data)

        analysis_id = detail_url.rstrip("/").split("/")[-1]
        export = self.client.get(f"/analysis/{analysis_id}/export/csv")
        self.assertEqual(export.status_code, 200)
        self.assertTrue(export.data.startswith("\ufeff".encode("utf-8")))


if __name__ == "__main__":
    unittest.main()
