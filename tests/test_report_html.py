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
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_action_fields_are_escaped(self):
        html = build_report_html(_results(top_actions=[
            {"priority": 1, "action": EVIL, "owner": EVIL, "deadline": EVIL}]))
        self.assertNotIn('onerror="', html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_kpi_fields_are_escaped(self):
        html = build_report_html(_results(kpis=[
            {"name": EVIL, "value": EVIL, "trend": EVIL, "status": "جيد"}]))
        self.assertNotIn('onerror="', html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_ordinary_arabic_is_untouched(self):
        html = build_report_html(_results(
            executive_summary="المشروع يسير وفق الخطة"))
        self.assertIn("المشروع يسير وفق الخطة", html)
        self.assertIn('dir="rtl"', html)


class ReportHtmlMalformedShapeTests(unittest.TestCase):
    """build_report_html is the third consumer of the frozen `results`
    contract (alongside export_pdf/export_excel) but, unlike them, never
    got the _obj()/_rows() coercion — these shapes each reached it
    directly and raised, surfacing to the user as a false "تعذّر الاتصال"
    network diagnosis from inside _run_send_email instead of the actual
    data-shape bug."""

    def test_top_actions_as_a_bare_string(self):
        # "لا يوجد" ("none") is a very plausible LLM response for an empty
        # action list — iterating a string's [:5] slice yields characters,
        # and act.get(...) on a character raises AttributeError.
        html = build_report_html(_results(top_actions="لا يوجد"))
        self.assertIn("خطة العمل الفورية", html)

    def test_top_actions_as_a_list_of_bare_strings(self):
        # A very common LLM deviation: a list of action strings instead of
        # a list of {"action": ..., "owner": ...} dicts.
        html = build_report_html(_results(top_actions=["افعل شيئاً"]))
        self.assertIn("خطة العمل الفورية", html)

    def test_kpis_as_a_dict(self):
        # chief.get("kpis", [])[:6] on a dict raises (dict does not
        # support slicing) instead of the list it's supposed to be.
        html = build_report_html(_results(kpis={"a": 1}))
        self.assertIn("مؤشرات الأداء", html)

    def test_overall_health_list_wrapped(self):
        html = build_report_html(_results(overall_health=["جيد"]))
        self.assertIn("الحالة العامة", html)


if __name__ == "__main__":
    unittest.main()
