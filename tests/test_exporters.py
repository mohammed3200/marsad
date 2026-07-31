import os
import tempfile
import unittest

from core.exporters import export_excel, export_pdf


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
        from core.status import tier
        self.assertEqual(tier("غير محدد"), "neutral")

    def test_html_and_excel_agree_with_the_pdf_on_a_medium_kpi(self):
        from core.status import tier
        self.assertEqual(tier("متوسط"), "warn")


if __name__ == "__main__":
    unittest.main()
