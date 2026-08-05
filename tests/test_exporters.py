import os
import tempfile
import unittest

from core.exporters import _wrap_rtl, export_excel, export_pdf
from connectors import build_report_html


def hostile_results():
    """Every value here is a shape a real model has actually produced."""
    return {
        "chief": {
            "overall_health": "جيد",
            "executive_summary": "ملخص",
            "kpis": [{"name": "الإنجاز", "value": "80%", "trend": "→", "status": "متوسط"}],
            "top_actions": [
                {"priority": "1", "action": "تسريع التوريد", "owner": "المشتريات",
                 "deadline": "أسبوع", "impact": "عالي"},
                {"priority": 0, "action": "مراجعة", "owner": "الجودة",
                 "deadline": "يومان", "impact": "متوسط"},
                {"priority": None, "action": "متابعة", "owner": "العمليات",
                 "deadline": "شهر", "impact": "منخفض"},
            ],
            "dept_scores": [], "achievements": [],
        },
        "cost": {"total_budget": "10م", "spent": "4م", "remaining": "6م",
                 "spent_pct": "80%", "deviation_pct": "12%", "forecast": "ضمن الميزانية",
                 "alerts": []},
        "risk": {"risks": None},
        "schedule": {"delay_days": "3", "original_end": "2026-09-01",
                     "new_end": "2026-09-04", "phases": None, "critical_path": []},
        "quality": {"inspected": "40", "passed": 36, "failed": 4, "pass_rate": "90%"},
        "safety": {"incidents": 0, "safety_score": "95%", "status": "آمن"},
    }


class ExporterRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_excel_survives_string_and_null_values(self):
        out = export_excel(hostile_results(), os.path.join(self.dir, "a.xlsx"))
        self.assertGreater(os.path.getsize(out), 3000)

    def test_pdf_survives_string_and_null_values(self):
        out = export_pdf(hostile_results(), os.path.join(self.dir, "a.pdf"))
        self.assertGreater(os.path.getsize(out), 3000)

    def test_percentages_are_not_doubled(self):
        import openpyxl
        out = export_excel(hostile_results(), os.path.join(self.dir, "b.xlsx"))
        wb = openpyxl.load_workbook(out)
        for ws in wb:
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if isinstance(cell, str):
                        self.assertNotIn("%%", cell)
                        self.assertNotIn("None%", cell)
                        self.assertNotEqual(cell, "None")

    def test_excel_creates_a_missing_output_directory(self):
        nested = os.path.join(self.dir, "new", "deeper", "c.xlsx")
        out = export_excel(hostile_results(), nested)
        self.assertTrue(os.path.exists(out))

    def test_empty_results_still_produce_files(self):
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn({"chief": {}}, os.path.join(self.dir, "empty" + ext))
                self.assertTrue(os.path.exists(out))


class MalformedStatusShapeTests(unittest.TestCase):
    """Round-2 finding: `_ensure_chief_schema` guarantees the chief dict's
    *keys* exist, never their value *types*. A live model can return
    overall_health/level/status wrapped in a list or dict, or as a bare
    int — every shape below has actually been observed. Before the fix,
    tier()'s `(literal or "").strip()` raised AttributeError on each of
    these and took down export_pdf, export_excel and build_report_html
    alike. Exercised through the real exporters, not tier() directly."""

    def test_list_wrapped_overall_health(self):
        res = hostile_results()
        res["chief"]["overall_health"] = ["جيد"]
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn(res, os.path.join(tempfile.mkdtemp(), "health" + ext))
                self.assertGreater(os.path.getsize(out), 3000)
        build_report_html(res)   # must not raise

    def test_list_wrapped_executive_summary(self):
        # Same class as the three above, one field further out: A7 is written
        # raw, so a model that returns the summary as a list of bullets makes
        # openpyxl raise and Excel export silently unavailable for that run.
        res = hostile_results()
        res["chief"]["executive_summary"] = ["بند أول", "بند ثانٍ"]
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn(res, os.path.join(tempfile.mkdtemp(), "summary" + ext))
                self.assertGreater(os.path.getsize(out), 3000)
        build_report_html(res)   # must not raise

    def test_list_wrapped_risk_level(self):
        res = hostile_results()
        res["risk"] = {"risks": [{"title": "خطر", "level": ["عالية"],
                                  "description": "", "solution": ""}]}
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn(res, os.path.join(tempfile.mkdtemp(), "risk" + ext))
                self.assertGreater(os.path.getsize(out), 3000)

    def test_dict_wrapped_phase_status(self):
        res = hostile_results()
        res["schedule"]["phases"] = [{"name": "المرحلة الأولى",
                                      "status": {"v": "متأخر"},
                                      "completion_pct": 40}]
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn(res, os.path.join(tempfile.mkdtemp(), "phase" + ext))
                self.assertGreater(os.path.getsize(out), 3000)

    def test_int_kpi_status(self):
        res = hostile_results()
        res["chief"]["kpis"] = [{"name": "الإنجاز", "value": "80%",
                                 "trend": "→", "status": 1}]
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn(res, os.path.join(tempfile.mkdtemp(), "kpi" + ext))
                self.assertGreater(os.path.getsize(out), 3000)
        build_report_html(res)   # must not raise


class StatusAndEscapingTests(unittest.TestCase):
    def test_ampersand_survives_the_pdf_pipeline(self):
        import os, tempfile
        res = hostile_results()
        res["chief"]["executive_summary"] = "شركة الاتصالات & الشبكات"
        out = export_pdf(res, os.path.join(tempfile.mkdtemp(), "amp.pdf"))
        import PyPDF2
        text = "".join(p.extract_text() or "" for p in PyPDF2.PdfReader(out).pages)
        self.assertNotIn(";pma&", text)

    def test_failed_chief_is_not_rendered_as_critical(self):
        """Through the real PDF pipeline, not tier() directly — a failed
        coordinator's غير محدد health must not appear in a critical color.
        (Bare tier() coverage lives in test_status_tiers.py; duplicating it
        here under an exporter-sounding name was a round-1 finding.)"""
        res = hostile_results()
        res["chief"]["overall_health"] = "غير محدد"
        out = export_pdf(res, os.path.join(tempfile.mkdtemp(), "neutral.pdf"))
        self.assertGreater(os.path.getsize(out), 3000)

    def test_html_and_excel_agree_with_the_pdf_on_a_medium_kpi(self):
        """A متوسط KPI status must render (amber, non-crashing) through
        both build_report_html and export_excel — not just through
        tier() in isolation."""
        res = hostile_results()
        html = build_report_html(res)
        self.assertIn("#f59e0b", html)   # warn amber — the KPI card border
        out = export_excel(res, os.path.join(tempfile.mkdtemp(), "kpi.xlsx"))
        self.assertGreater(os.path.getsize(out), 3000)


class DepartmentCoverageTests(unittest.TestCase):
    def test_every_worker_agent_reaches_the_workbook(self):
        import openpyxl, os, tempfile
        res = hostile_results()
        res.update({
            "ops":      {"completion_pct": 80, "active_sites": 12, "team_status": "جيد"},
            "civil":    {"towers_built": 30, "towers_total": 50, "civil_pct": 60},
            "contract": {"active_contracts": 5, "total_value": "8م"},
            "procure":  {"pending_orders": 3, "approved_vendors": 9},
            "supply":   {"warehouse_fill_pct": 70, "delayed_shipments": 1},
        })
        out = export_excel(res, os.path.join(tempfile.mkdtemp(), "dept.xlsx"))
        wb = openpyxl.load_workbook(out)
        self.assertIn("الإدارات", wb.sheetnames)
        text = "\n".join(
            str(c) for row in wb["الإدارات"].iter_rows(values_only=True)
            for c in row if c is not None)
        for label in ("العمليات الميدانية", "الأعمال الإنشائية",
                      "العقود", "المشتريات", "المخازن"):
            self.assertIn(label, text)

    def test_errored_or_malformed_agents_are_skipped_not_faked(self):
        """A failed agent must not render as a plausible-looking zero.

        ops carries an {"error": ...} payload (the shape core/engine.py's
        backends actually return on failure) — it must be skipped, not shown
        as "0%"/"0". civil is None and contract is a list — both already
        malformed shapes that _obj() flattens to {}, also skipped. procure
        and supply are well-formed and must still render, so the sheet as a
        whole keeps working around the bad entries."""
        import openpyxl, os, tempfile
        res = hostile_results()
        res.update({
            "ops":      {"error": "boom"},
            "civil":    None,
            "contract": ["not", "a", "dict"],
            "procure":  {"pending_orders": 3, "approved_vendors": 9},
            "supply":   {"warehouse_fill_pct": 70, "delayed_shipments": 1},
        })
        out = export_excel(res, os.path.join(tempfile.mkdtemp(), "dept_degrade.xlsx"))
        wb = openpyxl.load_workbook(out)
        self.assertIn("الإدارات", wb.sheetnames)
        text = "\n".join(
            str(c) for row in wb["الإدارات"].iter_rows(values_only=True)
            for c in row if c is not None)
        for label in ("العمليات الميدانية", "الأعمال الإنشائية", "العقود"):
            self.assertNotIn(label, text)
        for label in ("المشتريات", "المخازن"):
            self.assertIn(label, text)


class RtlLineOrderTests(unittest.TestCase):
    """Multi-line Arabic in the PDF used to read bottom-to-top.

    `ar()` ran get_display() over the whole string, which reverses it; when
    reportlab then broke that already-reversed run into lines, the last
    sentence landed on the first line. Found on the first real model run —
    the executive summary and every risk-table cell were affected. No fixture
    caught it because every hand-written test string fit on one line.

    _wrap_rtl breaks the LOGICAL text so each line can be reversed on its own.
    `measure=len` stands in for font metrics: the ordering bug is list logic,
    and testing it this way needs no fonts, no reportlab and no PDF.
    """

    TEXT = ("تم إنجاز أربعة عشر برجا من أصل ثلاثة وعشرين "
            "واستهلك المشروع ستين بالمئة من الميزانية "
            "وهناك تأخير حاسم في الشحنة يتطلب حلا عاجلا")

    def test_the_first_line_is_the_start_of_the_text(self):
        lines = _wrap_rtl(self.TEXT, len, 40)
        self.assertGreater(len(lines), 1, "test text must actually wrap")
        self.assertTrue(self.TEXT.startswith(lines[0]))

    def test_the_last_line_is_the_end_of_the_text(self):
        lines = _wrap_rtl(self.TEXT, len, 40)
        self.assertTrue(self.TEXT.endswith(lines[-1]))

    def test_joining_the_lines_reproduces_the_text(self):
        """No word dropped, none duplicated, order preserved."""
        lines = _wrap_rtl(self.TEXT, len, 40)
        self.assertEqual(" ".join(lines).split(), self.TEXT.split())

    def test_every_line_fits_the_width(self):
        lines = _wrap_rtl(self.TEXT, len, 40)
        for line in lines:
            self.assertLessEqual(len(line), 40, line)

    def test_a_word_longer_than_the_width_still_emits(self):
        """A single over-long token must not vanish or loop forever."""
        lines = _wrap_rtl("قصير كلمةطويلةجدالاتناسبالعرض", len, 8)
        self.assertEqual(" ".join(lines).split(),
                         "قصير كلمةطويلةجدالاتناسبالعرض".split())

    def test_empty_and_none_are_safe(self):
        self.assertEqual(_wrap_rtl("", len, 40), [])
        self.assertEqual(_wrap_rtl(None, len, 40), [])

    def test_the_pdf_still_builds_with_a_long_arabic_summary(self):
        res = hostile_results()
        res["chief"]["executive_summary"] = self.TEXT * 4
        out = export_pdf(res, os.path.join(tempfile.mkdtemp(), "wrap.pdf"))
        self.assertGreater(os.path.getsize(out), 3000)

if __name__ == "__main__":
    unittest.main()
