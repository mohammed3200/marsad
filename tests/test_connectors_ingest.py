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
