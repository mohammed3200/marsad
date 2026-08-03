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


if __name__ == "__main__":
    unittest.main()
