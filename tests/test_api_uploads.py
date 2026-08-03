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

Fix round 1 additions:

* A filename with an embedded null byte still reached open() unmodified and
  raised ValueError (not OSError), which `except OSError` did not catch, so
  it 500'd. httpx's `files=` helper percent-encodes null bytes before they
  ever leave the client, so the test that reproduces this builds the
  multipart body by hand (see test_embedded_null_byte_filename_does_not_500).
* A long filename was truncated as a whole, stripping its extension —
  downstream, read_file_to_report dispatches on fpath.suffix, so such an
  upload was silently dropped instead of processed.
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

    def test_a_file_of_exactly_max_upload_bytes_is_accepted(self):
        """MAX_UPLOAD_FILES had a boundary test on both sides; MAX_UPLOAD_BYTES
        only had an over-the-limit test (test_oversize_upload_is_rejected).
        Add the at-the-limit counterpart so an off-by-one in the streaming
        loop's `written > MAX_UPLOAD_BYTES` check would be caught."""
        from api.app import MAX_UPLOAD_BYTES
        from core.paths import DATA_DIR
        blob = b"a" * MAX_UPLOAD_BYTES
        r = _client().post("/api/reports/files",
                           files=[("files", ("atlimit.txt", blob, "text/plain"))])
        self.assertEqual(r.status_code, 200)
        written = list((DATA_DIR / "uploads").rglob("atlimit.txt"))
        self.assertEqual(len(written), 1)
        self.assertEqual(len(written[0].read_bytes()), MAX_UPLOAD_BYTES)

    def test_embedded_null_byte_filename_does_not_500(self):
        """Fix round 1, critical finding 1. open() raises ValueError (not
        OSError) for a path containing an embedded null byte, so the
        endpoint's `except OSError` alone did not catch it and it 500'd.

        httpx's `files=` helper percent-encodes a null byte in a filename
        before the request ever leaves the client, so it cannot reproduce
        this — the multipart body is built by hand here so a raw null byte
        actually reaches the server, the way a real client (e.g. curl) can
        send one."""
        boundary = "----marsadnulltest"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="files"; filename="a\x00b.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "hello\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        r = _client().post(
            "/api/reports/files",
            content=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        self.assertNotEqual(r.status_code, 500)
        # The sanitiser strips the null byte rather than rejecting the
        # upload outright, so the expected outcome is success, not just
        # "not a crash".
        self.assertEqual(r.status_code, 200)

    def test_long_filename_truncation_preserves_extension(self):
        """Fix round 1, minor finding 5. [:120] on the whole sanitised name
        truncated "aaa....a.txt" (130 a's + .txt) down to 120 bare a's with
        no suffix — read_file_to_report dispatches on fpath.suffix, so the
        upload was silently dropped rather than processed."""
        from core.paths import DATA_DIR
        long_name = "a" * 130 + ".txt"
        r = _client().post("/api/reports/files",
                           files=[("files", (long_name, b"x", "text/plain"))])
        self.assertEqual(r.status_code, 200)
        saved = list((DATA_DIR / "uploads").rglob("*.txt"))
        matches = [p for p in saved if p.name.startswith("a" * 100)]
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].name.endswith(".txt"))
        self.assertLessEqual(len(matches[0].name), 120)

    def test_safe_upload_name_strips_control_characters(self):
        """Direct unit test of the sanitiser fix, complementing the
        HTTP-level repro above: control characters (0x00-0x1f), including an
        embedded null byte, must not survive into the returned name."""
        from api.app import _safe_upload_name
        self.assertEqual(_safe_upload_name("a\x00b.txt"), "ab.txt")
        self.assertEqual(_safe_upload_name("a\x01\x1fb.txt"), "ab.txt")
        # a name that is nothing but control characters degrades to "upload",
        # same as the existing "", ".", ".." cases.
        self.assertEqual(_safe_upload_name("\x00\x00\x00"), "upload")

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


class WhatsAppReceiverCapTests(unittest.TestCase):
    """Fix round 1, important finding 4: WhatsAppReceiver.do_POST built a
    report with "content": text straight from the request body, with no
    _cap() — a content-producing path in the same file as the four capped
    readers above, feeding the same LLM prompt. It also read Content-Length
    bytes into memory with no upper bound before parsing JSON, the same
    unbounded-body pattern flagged for the HTTP upload endpoint, on a second
    local server.

    WhatsAppReceiver writes no app state — it only logs to the gitignored
    logs/connectors.log (pre-existing, deferred as minor 6) — so this class
    needs no isolated_state()."""

    def _free_port(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _start_receiver(self):
        import connectors
        received = []
        port = self._free_port()
        recv = connectors.WhatsAppReceiver(port, received.append)
        recv.start()
        self.addCleanup(recv.stop)
        return port, received

    def _post(self, port, path, body_bytes):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            conn.request("POST", path, body=body_bytes,
                        headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            status = resp.status
            resp.read()
        finally:
            conn.close()
        return status

    def test_whatsapp_message_content_is_capped(self):
        import connectors
        import json
        port, received = self._start_receiver()
        # A text long enough to need capping, but still comfortably under
        # MAX_WA_BODY_BYTES once encoded. ensure_ascii=False matches the real
        # sender: the Node/Baileys bridge's JSON.stringify does not escape
        # non-ASCII, unlike json.dumps' default — with the default, each
        # Arabic character would balloon to a 6-byte \uXXXX escape and blow
        # the body past the Content-Length ceiling before it ever reaches
        # the cap this test means to exercise.
        huge_text = "ب" * (connectors.MAX_CHARS + 5000)
        body = json.dumps({"group_id": "g1", "sender": "s", "text": huge_text},
                          ensure_ascii=False).encode("utf-8")
        self.assertLess(len(body), connectors.MAX_WA_BODY_BYTES)
        status = self._post(port, "/wa_message", body)
        self.assertEqual(status, 200)
        self.assertEqual(len(received), 1)
        rep = received[0][0]
        self.assertLessEqual(len(rep["content"]), connectors.MAX_CHARS + 200)
        self.assertIn("اقتُطع", rep["content"])

    def test_whatsapp_message_content_under_the_cap_is_untouched(self):
        import connectors
        import json
        port, received = self._start_receiver()
        body_text = "تحديث ميداني عبر واتساب"
        body = json.dumps({"group_id": "g1", "sender": "s", "text": body_text},
                          ensure_ascii=False).encode("utf-8")
        status = self._post(port, "/wa_message", body)
        self.assertEqual(status, 200)
        self.assertEqual(received[0][0]["content"], body_text)

    def test_oversized_whatsapp_body_is_rejected_before_reading(self):
        import connectors
        import json
        port, received = self._start_receiver()
        oversized = json.dumps({
            "group_id": "g1", "sender": "s",
            "text": "x" * (connectors.MAX_WA_BODY_BYTES + 1000),
        }).encode("utf-8")
        status = self._post(port, "/wa_message", oversized)
        self.assertEqual(status, 413)
        self.assertEqual(received, [])


if __name__ == "__main__":
    unittest.main()
