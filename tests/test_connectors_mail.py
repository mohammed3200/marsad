import ssl
import unittest
from unittest import mock


class MailTlsTests(unittest.TestCase):
    def test_module_context_verifies_certificates(self):
        import connectors
        ctx = connectors.SSL_CONTEXT
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_imap_test_connection_passes_a_verifying_context(self):
        import connectors
        captured = {}

        class FakeIMAP:
            def __init__(self, host, timeout=None, ssl_context=None):
                captured["ssl_context"] = ssl_context
            def login(self, u, p): pass
            def logout(self): pass

        conn = connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})
        with mock.patch.object(connectors.imaplib, "IMAP4_SSL", FakeIMAP):
            conn.test_connection()
        ctx = captured["ssl_context"]
        self.assertIsNotNone(ctx, "IMAP4_SSL was called without an ssl_context")
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_imap_fetch_passes_a_verifying_context(self):
        import connectors
        captured = {}

        class FakeIMAP:
            def __init__(self, host, timeout=None, ssl_context=None):
                captured["ssl_context"] = ssl_context
            def login(self, u, p): pass
            def select(self, box): pass
            def search(self, *a): return ("OK", [b""])
            def close(self): pass
            def logout(self): pass

        conn = connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})
        with mock.patch.object(connectors.imaplib, "IMAP4_SSL", FakeIMAP):
            conn.fetch_new()
        self.assertEqual(captured["ssl_context"].verify_mode, ssl.CERT_REQUIRED)

    def test_smtp_starttls_gets_a_verifying_context(self):
        import connectors
        captured = {}

        class FakeSMTP:
            def __init__(self, host, port, timeout=None): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): captured["context"] = context
            def login(self, u, p): pass
            def sendmail(self, *a, **k): pass

        conn = connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})
        with mock.patch.object(connectors.smtplib, "SMTP", FakeSMTP):
            conn.send_report(["boss@example.com"], "t", "<p>x</p>")
        self.assertEqual(captured["context"].verify_mode, ssl.CERT_REQUIRED)


class EmailTestCoversBothLegsTests(unittest.TestCase):
    """«اختبار البريد» tested IMAP only, so it proved nothing about the send
    path the release checklist's "email the report" item exercises. A green
    test could sit next to a send that always failed."""

    def _conn(self):
        import connectors
        return connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})

    @staticmethod
    def _fake_imap(ok=True):
        class FakeIMAP:
            def __init__(self, host, timeout=None, ssl_context=None): pass
            def login(self, u, p):
                if not ok:
                    raise OSError("[Errno -2] Name or service not known")
            def logout(self): pass
        return FakeIMAP

    @staticmethod
    def _fake_smtp(ok=True):
        class FakeSMTP:
            def __init__(self, host, port, timeout=None): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): pass
            def login(self, u, p):
                if not ok:
                    raise OSError("[Errno 111] Connection refused")
        return FakeSMTP

    def _run(self, imap_ok, smtp_ok):
        import connectors
        with mock.patch.object(connectors.imaplib, "IMAP4_SSL",
                               self._fake_imap(imap_ok)), \
             mock.patch.object(connectors.smtplib, "SMTP",
                               self._fake_smtp(smtp_ok)):
            return self._conn().test_connection()

    def test_smtp_failure_is_reported_even_when_imap_works(self):
        ok, msg = self._run(imap_ok=True, smtp_ok=False)
        self.assertFalse(ok)
        self.assertIn("تعذّر الإرسال", msg)

    def test_imap_failure_is_reported_even_when_smtp_works(self):
        ok, msg = self._run(imap_ok=False, smtp_ok=True)
        self.assertFalse(ok)
        self.assertIn("تعذّر الاستقبال", msg)

    def test_both_legs_failing_names_both(self):
        ok, msg = self._run(imap_ok=False, smtp_ok=False)
        self.assertFalse(ok)
        self.assertIn("الاستقبال", msg)
        self.assertIn("الإرسال", msg)

    def test_both_legs_working_succeeds(self):
        ok, msg = self._run(imap_ok=True, smtp_ok=True)
        self.assertTrue(ok)
        self.assertIn("u@example.com", msg)

    def test_the_smtp_leg_sends_no_message(self):
        """Logging in is the whole test — a probe that mailed someone would
        be worse than no probe."""
        import connectors
        sent = []

        class RecordingSMTP:
            def __init__(self, host, port, timeout=None): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): pass
            def login(self, u, p): pass
            def sendmail(self, *a, **k): sent.append(a)

        with mock.patch.object(connectors.imaplib, "IMAP4_SSL",
                               self._fake_imap(True)), \
             mock.patch.object(connectors.smtplib, "SMTP", RecordingSMTP):
            self._conn().test_connection()
        self.assertEqual(sent, [])


class SendReportSurfacesTheCauseTests(unittest.TestCase):
    """send_report returned a bare bool and swallowed the exception, so the UI
    could only ever show the generic «تعذّر إرسال البريد — راجع الإعدادات»
    while the real reason sat in a log file."""

    def _conn(self):
        import connectors
        return connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})

    def test_a_rejected_login_reaches_the_caller(self):
        import connectors

        class RejectingSMTP:
            def __init__(self, host, port, timeout=None): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): pass
            def login(self, u, p):
                raise connectors.smtplib.SMTPAuthenticationError(
                    535, b"5.7.8 Username and Password not accepted")
            def sendmail(self, *a, **k): pass

        with mock.patch.object(connectors.smtplib, "SMTP", RejectingSMTP):
            ok, msg = self._conn().send_report(["boss@example.com"], "t", "<p>x</p>")
        self.assertFalse(ok)
        self.assertTrue(msg)
        # Arabic, not a raw Python repr.
        self.assertNotIn("SMTPAuthenticationError", msg)
        self.assertNotIn("Traceback", msg)

    def test_success_returns_a_message_too(self):
        import connectors

        class FakeSMTP:
            def __init__(self, host, port, timeout=None): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): pass
            def login(self, u, p): pass
            def sendmail(self, *a, **k): pass

        with mock.patch.object(connectors.smtplib, "SMTP", FakeSMTP):
            ok, msg = self._conn().send_report(["boss@example.com"], "t", "<p>x</p>")
        self.assertTrue(ok)
        self.assertEqual(msg, "أُرسل التقرير بالبريد")

    def test_no_recipients_says_so(self):
        ok, msg = self._conn().send_report([], "t", "<p>x</p>")
        self.assertFalse(ok)
        self.assertIn("مستلمون", msg)


class SentMessageWireFormatTests(unittest.TestCase):
    """What actually goes on the wire.

    Delivery to a remote host is the one thing a test cannot do, but it is
    also not where this breaks. The real risk is the message marsad *builds*:
    an Arabic subject that arrives as mojibake, an HTML body mangled by the
    wrong charset, or an attachment corrupted in transfer encoding. Those are
    all verifiable by capturing the bytes handed to sendmail and parsing them
    back with the stdlib email package — which is exactly what a receiving
    server does.

    Verified against a real analysis result before being written down.
    """

    def _send(self, html, attachments=()):
        import connectors
        captured = {}

        class CapturingSMTP:
            def __init__(self, host, port, timeout=None):
                captured["target"] = (host, port)
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): captured["tls"] = context
            def login(self, u, p): captured["login"] = u
            def sendmail(self, frm, to, raw):
                captured.update(frm=frm, to=to, raw=raw)

        conn = connectors.EmailConnector({
            "email_user": "pmo@ltt.example", "email_password": "x",
            "smtp_host": "smtp.example", "smtp_port": 587})
        with mock.patch.object(connectors.smtplib, "SMTP", CapturingSMTP):
            ok, msg = conn.send_report(["boss@ltt.example"],
                                       "تقرير حالة المشروع — مرصد",
                                       html, list(attachments))
        self.assertTrue(ok, msg)
        return captured

    def _parsed(self, captured):
        import email
        return email.message_from_bytes(captured["raw"])

    def test_the_arabic_subject_survives_a_round_trip(self):
        from email.header import decode_header, make_header
        m = self._parsed(self._send("<p>مرحبا</p>"))
        self.assertEqual(str(make_header(decode_header(m["Subject"]))),
                         "تقرير حالة المشروع — مرصد")

    def test_the_html_body_arrives_byte_identical_in_utf8(self):
        html = "<p>تقرير الحالة — ٨٠٪ مكتمل</p>"
        m = self._parsed(self._send(html))
        part = [p for p in m.walk() if p.get_content_type() == "text/html"][0]
        self.assertEqual(part.get_content_charset(), "utf-8")
        decoded = part.get_payload(decode=True).decode(part.get_content_charset())
        self.assertEqual(decoded, html)

    def test_attachments_arrive_byte_intact(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        blob = os.urandom(5000)                     # binary, not text
        p = os.path.join(d, "تقرير.pdf")
        with open(p, "wb") as fh:
            fh.write(blob)
        m = self._parsed(self._send("<p>x</p>", [p]))
        got = [q for q in m.walk() if q.get_filename()]
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].get_payload(decode=True), blob)

    def test_a_missing_attachment_is_skipped_not_fatal(self):
        captured = self._send("<p>x</p>", ["/nonexistent/report.pdf"])
        m = self._parsed(captured)
        self.assertEqual([q.get_filename() for q in m.walk() if q.get_filename()], [])

    def test_the_transport_verifies_certificates(self):
        import ssl
        captured = self._send("<p>x</p>")
        self.assertEqual(captured["tls"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(captured["tls"].check_hostname)

    def test_envelope_matches_the_headers(self):
        captured = self._send("<p>x</p>")
        m = self._parsed(captured)
        self.assertEqual(captured["frm"], m["From"])
        self.assertEqual(captured["to"], ["boss@ltt.example"])
        self.assertIn("boss@ltt.example", m["To"])

if __name__ == "__main__":
    unittest.main()
