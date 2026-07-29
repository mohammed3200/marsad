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


if __name__ == "__main__":
    unittest.main()
