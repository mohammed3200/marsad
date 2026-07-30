"""Task 7: bounds on what can enter the app as a report.

Two independent guards, both of which were missing:

* The HTTP upload endpoint accepted any number of files of any size, read each
  one whole into RAM, and 500'd on a filename of ".." (Path("..").name is
  ".." — a directory, so write_bytes raised IsADirectoryError).
* Several readers pulled an entire file into the report body, which goes
  verbatim into an LLM prompt. Excel/CSV/JSON were already capped; .txt, PDF,
  .docx and email attachments were not.

The upload tests drive the live AppService singleton, which reads and writes
settings.json, reports/ and data/contacts.json — so, exactly as in
tests/test_api_auth.py, the whole class runs inside isolated_state() entered
before api.app is first imported. This suite never touches real user state.
"""
import os
import unittest

os.environ["MARSAD_API_ENABLE"] = "1"

from tests._isolation import isolated_state  # noqa: E402


def _client():
    from fastapi.testclient import TestClient
    from api.app import app
    return TestClient(app, base_url="http://127.0.0.1")


class UploadLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Class-scoped: api.app builds its AppService singleton once, on first
        # import, so the redirected paths must be in place before that happens.
        cls._iso = isolated_state()
        cls._root = cls._iso.__enter__()
        import backend.settings_bridge as sb
        assert str(sb.SETTINGS_F).startswith(str(cls._root)), (
            "isolated_state() did not redirect SETTINGS_F into the temp root "
            "— refusing to run uploads against the real DATA_DIR")
        # This suite writes files, so DATA_DIR itself must be redirected too —
        # patching only the settings path would still land uploads in the
        # developer's real uploads/ directory.
        import api.app as api_app
        assert str(api_app.DATA_DIR).startswith(str(cls._root)), (
            "isolated_state() did not redirect DATA_DIR into the temp root "
            "— refusing to write uploads into the real data directory")

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)

    def test_oversize_upload_is_rejected(self):
        from api.app import MAX_UPLOAD_BYTES
        blob = b"a" * (MAX_UPLOAD_BYTES + 1024)
        r = _client().post("/api/reports/files",
                           files=[("files", ("big.txt", blob, "text/plain"))])
        self.assertEqual(r.status_code, 413)

    def test_oversize_upload_leaves_no_partial_file_behind(self):
        from api.app import MAX_UPLOAD_BYTES
        from core.paths import DATA_DIR
        blob = b"a" * (MAX_UPLOAD_BYTES + 1024)
        _client().post("/api/reports/files",
                       files=[("files", ("big.txt", blob, "text/plain"))])
        leftovers = list((DATA_DIR / "uploads").rglob("big.txt"))
        self.assertEqual(leftovers, [])

    def test_too_many_files_are_rejected(self):
        from api.app import MAX_UPLOAD_FILES
        files = [("files", (f"f{i}.txt", b"x", "text/plain"))
                 for i in range(MAX_UPLOAD_FILES + 1)]
        r = _client().post("/api/reports/files", files=files)
        self.assertEqual(r.status_code, 413)

    def test_a_file_at_the_limit_is_accepted(self):
        from api.app import MAX_UPLOAD_FILES
        files = [("files", (f"ok{i}.txt", b"x", "text/plain"))
                 for i in range(MAX_UPLOAD_FILES)]
        r = _client().post("/api/reports/files", files=files)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["saved"], MAX_UPLOAD_FILES)

    def test_dot_dot_filename_does_not_500(self):
        r = _client().post("/api/reports/files",
                           files=[("files", ("..", b"x", "text/plain"))])
        self.assertNotEqual(r.status_code, 500)
        self.assertEqual(r.status_code, 200)

    def test_traversal_filename_stays_inside_uploads(self):
        from core.paths import DATA_DIR
        r = _client().post("/api/reports/files",
                           files=[("files", ("../../escape.txt", b"x", "text/plain"))])
        self.assertEqual(r.status_code, 200)
        self.assertFalse((DATA_DIR / "escape.txt").exists())
        self.assertFalse((DATA_DIR.parent / "escape.txt").exists())

    def test_upload_content_survives_and_lands_under_uploads(self):
        from core.paths import DATA_DIR
        arabic = "تقرير ميداني عبر الرفع".encode("utf-8")
        r = _client().post("/api/reports/files",
                           files=[("files", ("ran_daily.txt", arabic, "text/plain"))])
        self.assertEqual(r.status_code, 200)
        written = list((DATA_DIR / "uploads").rglob("ran_daily.txt"))
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0].read_bytes(), arabic)


class ReadCapTests(unittest.TestCase):
    """read_file_to_report writes no user state, so it needs no isolation."""

    def _huge(self, name, text):
        import tempfile
        from pathlib import Path
        p = Path(tempfile.mkdtemp()) / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_txt_content_is_capped(self):
        import connectors
        p = self._huge("ran_huge.txt", "ب" * (connectors.MAX_CHARS + 5000))
        rep = connectors.read_file_to_report(p)
        self.assertLessEqual(len(rep["content"]), connectors.MAX_CHARS + 200)
        self.assertIn("اقتُطع", rep["content"])

    def test_content_under_the_cap_is_untouched(self):
        import connectors
        body = "تقرير قصير عن الموقع"
        p = self._huge("ran_small.txt", body)
        rep = connectors.read_file_to_report(p)
        self.assertEqual(rep["content"], body)
        self.assertNotIn("اقتُطع", rep["content"])

    def test_cap_helper_boundary(self):
        import connectors
        exact = "ب" * connectors.MAX_CHARS
        self.assertEqual(connectors._cap(exact), exact)
        over = "ب" * (connectors.MAX_CHARS + 1)
        capped = connectors._cap(over)
        self.assertTrue(capped.startswith("ب" * connectors.MAX_CHARS))
        self.assertIn("اقتُطع", capped)

    def test_cap_helper_tolerates_empty_and_none(self):
        import connectors
        self.assertEqual(connectors._cap(""), "")
        self.assertEqual(connectors._cap(None), "")

    def test_docx_content_is_capped(self):
        import tempfile
        from pathlib import Path
        import connectors
        try:
            import docx
        except ImportError:
            self.skipTest("python-docx not installed")
        p = Path(tempfile.mkdtemp()) / "ran_huge.docx"
        d = docx.Document()
        for _ in range(60):
            d.add_paragraph("ب" * 1000)
        d.save(p)
        rep = connectors.read_file_to_report(p)
        self.assertLessEqual(len(rep["content"]), connectors.MAX_CHARS + 200)
        self.assertIn("اقتُطع", rep["content"])


if __name__ == "__main__":
    unittest.main()
