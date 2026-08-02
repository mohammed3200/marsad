import datetime
import json
import tempfile
import unittest
from pathlib import Path

import connectors
from connectors import guess_dept, is_internal_file, read_file_to_report

ARABIC = "أنجز فريق الموقع ٨٠٪ من أعمال الحفر اليوم"


class GuessDeptTests(unittest.TestCase):
    def test_english_keywords(self):
        self.assertEqual(guess_dept("ran_daily.docx"), "ran")
        self.assertEqual(guess_dept("core_network.csv"), "core")
        self.assertEqual(guess_dept("quality_sites.xlsx"), "quality")
        self.assertEqual(guess_dept("safety_site.pdf"), "safety")

    def test_ran_does_not_match_inside_ordinary_words(self):
        for name in ("random_stuff.txt", "transfer_log.txt",
                     "grant_letter.txt", "France_visit.txt"):
            with self.subTest(name=name):
                self.assertEqual(guess_dept(name), "admin")

    def test_normal_arabic_spellings_are_recognised(self):
        self.assertEqual(guess_dept("تكاليف_المشروع.xlsx"), "cost")
        self.assertEqual(guess_dept("إنشاء_الأبراج.docx"), "civil")
        self.assertEqual(guess_dept("تقرير_الجودة.pdf"), "quality")
        self.assertEqual(guess_dept("السلامة_اليومي.txt"), "safety")

    def test_unknown_falls_back_to_admin(self):
        self.assertEqual(guess_dept("notes.txt"), "admin")

    def test_arabic_keywords_do_not_match_as_mere_substrings(self):
        # Regression for the عقد collision: it should not match in unrelated words
        # معقد (muʿaqqad) = complicated, not a contract
        self.assertEqual(guess_dept("تقرير_معقد.pdf"), "admin")
        # العقد here means "decade", not singular contract
        self.assertEqual(guess_dept("خطة_العقد_القادم.xlsx"), "admin")
        # عقدة (ʿuqda) = psychological complex, not a contract
        self.assertEqual(guess_dept("عقدة_نفسية.docx"), "admin")

    def test_latin_keywords_match_when_attached_to_digits(self):
        # Regression for digit handling: RAN2024 should still match "ran"
        self.assertEqual(guess_dept("RAN2024_report.docx"), "ran")
        # core5g should match "core" (and would have matched via "network" too)
        self.assertEqual(guess_dept("core5g_network.csv"), "core")
        # 5Gcore should not match (5G prefix, digit-glued to "core", creates "gcore" token)
        # This is a known gap: false negative (manual triage) not false positive
        self.assertEqual(guess_dept("5Gcore_report.csv"), "admin")

    def test_quality_keyword_does_not_match_existing_data(self):
        # Regression for جودة collision with موجودة (existing)
        # بيانات_موجودة = "existing data"
        self.assertEqual(guess_dept("بيانات_موجودة.xlsx"), "admin")
        # Positive case: genuine quality reports still route via الجودة (with definite article)
        self.assertEqual(guess_dept("تقرير_الجودة.pdf"), "quality")

    def test_cost_keyword_does_not_match_northern_or_probability(self):
        # Regression for مالية collision with شمالية (northern), احتمالية (probability),
        # and عمالية (labor) — all common words that would misroute files
        # المنطقة_الشمالية = "Northern region" (very common in telecom regional rollout context)
        self.assertEqual(guess_dept("المنطقة_الشمالية.pdf"), "admin")
        # تحليل_احتمالية_المخاطر = "risk probability analysis"
        self.assertEqual(guess_dept("تحليل_احتمالية_المخاطر.xlsx"), "admin")
        # نزاع_عمالية = "labor dispute"
        self.assertEqual(guess_dept("نزاع_عمالية.pdf"), "admin")
        # Positive case: genuine cost reports still route via more specific keywords
        self.assertEqual(guess_dept("تقرير_التكاليف.xlsx"), "cost")
        self.assertEqual(guess_dept("الميزانية_السنوية.pdf"), "cost")


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_every_supported_format_round_trips(self):
        import docx, openpyxl
        from reportlab.pdfgen import canvas

        d = docx.Document(); d.add_paragraph(ARABIC); d.save(self.dir / "ran_daily.docx")
        wb = openpyxl.Workbook(); wb.active.append(["البند", ARABIC])
        wb.save(self.dir / "quality_sites.xlsx")
        (self.dir / "core_network.csv").write_text(
            f"القسم,الحالة\nالنواة,{ARABIC}\n", encoding="utf-8")
        (self.dir / "تقرير_الجودة.txt").write_text(ARABIC, encoding="utf-8")
        (self.dir / "plain.json").write_text(
            json.dumps({"ملاحظة": ARABIC}, ensure_ascii=False), encoding="utf-8")
        c = canvas.Canvas(str(self.dir / "safety_site.pdf"))
        c.drawString(72, 720, "RAN site safety inspection completed")
        c.save()

        today = datetime.date.today().isoformat()
        for name, dept in (("ran_daily.docx", "ran"),
                           ("quality_sites.xlsx", "quality"),
                           ("core_network.csv", "core"),
                           ("تقرير_الجودة.txt", "quality"),
                           ("plain.json", "admin"),
                           ("safety_site.pdf", "safety")):
            with self.subTest(name=name):
                rep = read_file_to_report(self.dir / name)
                self.assertIsNotNone(rep)
                self.assertEqual(set(rep),
                                 {"id", "source", "dept", "from", "date", "content"})
                self.assertEqual(rep["source"], "upload")
                self.assertEqual(rep["date"], today)
                self.assertEqual(rep["dept"], dept)

    def test_empty_file_is_rejected(self):
        (self.dir / "empty.txt").write_text("", encoding="utf-8")
        self.assertIsNone(read_file_to_report(self.dir / "empty.txt"))

    def test_internal_files_can_never_be_ingested(self):
        from core.paths import BUNDLE_DIR, DATA_DIR
        for path in (DATA_DIR / "settings.json",
                     BUNDLE_DIR / "settings.example.json",
                     DATA_DIR / "data" / "contacts.json",
                     DATA_DIR / "reports" / "latest.json"):
            with self.subTest(path=path.name):
                self.assertTrue(is_internal_file(path))
                self.assertIsNone(read_file_to_report(path))


if __name__ == "__main__":
    unittest.main()
