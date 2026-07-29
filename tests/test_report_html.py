import unittest

from connectors import build_report_html

EVIL = '<img src=x onerror="alert(1)"><a href="https://evil.example">اضغط</a>'


def _results(**chief):
    base = {"overall_health": "جيد", "executive_summary": "", "kpis": [],
            "top_actions": [], "dept_scores": [], "achievements": []}
    base.update(chief)
    return {"chief": base}


class ReportHtmlEscapingTests(unittest.TestCase):
    def test_executive_summary_is_escaped(self):
        html = build_report_html(_results(executive_summary=EVIL))
        self.assertNotIn('onerror="', html)
        self.assertNotIn('href="https://evil.example"', html)
        self.assertIn("&lt;img", html)

    def test_action_fields_are_escaped(self):
        html = build_report_html(_results(top_actions=[
            {"priority": 1, "action": EVIL, "owner": EVIL, "deadline": EVIL}]))
        self.assertNotIn('onerror="', html)

    def test_kpi_fields_are_escaped(self):
        html = build_report_html(_results(kpis=[
            {"name": EVIL, "value": EVIL, "trend": EVIL, "status": "جيد"}]))
        self.assertNotIn('onerror="', html)

    def test_ordinary_arabic_is_untouched(self):
        html = build_report_html(_results(
            executive_summary="المشروع يسير وفق الخطة"))
        self.assertIn("المشروع يسير وفق الخطة", html)
        self.assertIn('dir="rtl"', html)


if __name__ == "__main__":
    unittest.main()
