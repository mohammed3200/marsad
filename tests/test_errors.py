"""Regression coverage for core/errors.py — there was none before this task,
despite four commits on this branch touching its rule ordering.

friendly_error() maps raw provider/network error text to a short Arabic
message; friendly_fs_error() does the same for local filesystem/OSError
failures. Both must never raise (parsing paths must never raise) and must
never leak raw English into the fallback in a way that misdiagnoses the
cause.
"""
import errno
import unittest

from core.errors import friendly_error, friendly_fs_error


class FriendlyErrorPassthroughTests(unittest.TestCase):
    def test_empty_or_none_is_unknown_error(self):
        self.assertEqual(friendly_error(""), "خطأ غير معروف")
        self.assertEqual(friendly_error(None), "خطأ غير معروف")

    def test_arabic_text_passes_through_unchanged(self):
        text = "فشل غير معروف من المزوّد"
        self.assertEqual(friendly_error(text), text)

    def test_arabic_text_is_never_matched_against_the_english_rules(self):
        # Contains "404" as a substring but is already Arabic — must pass
        # through verbatim, not get rewritten to the 404 rule's message.
        text = "خطأ 404 غير متوقع"
        self.assertEqual(friendly_error(text), text)


class FriendlyErrorRuleOrderingTests(unittest.TestCase):
    """الترتيب مهم — الأكثر تحديداً أولاً (see the comment in core/errors.py).
    Each case below could plausibly match more than one rule; assert the
    higher-priority one wins."""

    def test_auth_failed_beats_generic_401(self):
        msg = friendly_error("IMAP AUTHENTICATIONFAILED: invalid credentials")
        self.assertIn("App Password", msg)

    def test_429_beats_400_family(self):
        # Contains both "429" and "bad request" — the 429/quota rule is
        # ranked ahead of the generic 400 rule and must win.
        msg = friendly_error("429 Too Many Requests — bad request")
        self.assertEqual(msg, "تجاوزت حصة المزوّد — راجع خطتك والفوترة أو بدّل النموذج")

    def test_401_beats_404(self):
        msg = friendly_error("401 unauthorized, model not found (404)")
        self.assertEqual(msg, "مفتاح API غير صالح أو بلا صلاحية — تحقق من المفتاح")

    def test_404_alone(self):
        msg = friendly_error("404 no such model")
        self.assertEqual(msg, "النموذج أو العنوان غير موجود — تحقق من اسم النموذج والرابط")

    def test_5xx_family(self):
        for code in ("500", "502", "503", "504"):
            with self.subTest(code=code):
                self.assertEqual(
                    friendly_error(f"{code} internal error"),
                    "خلل في خادم المزوّد — حاول بعد قليل")

    def test_timeout(self):
        self.assertEqual(friendly_error("Read timed out"),
                         "انتهت مهلة الاتصال — الخادم لا يستجيب")

    def test_dns_failure_beats_generic_connection_refused(self):
        msg = friendly_error("gaierror: Temporary failure in name resolution")
        self.assertEqual(msg, "تعذّر حل اسم الخادم (DNS) — تحقق من اتصال الإنترنت")

    def test_connection_refused(self):
        msg = friendly_error("ConnectionRefusedError: Connection refused")
        self.assertEqual(msg, "تعذّر الوصول إلى الخادم — تحقق من العنوان والشبكة")

    def test_ssl_certificate(self):
        msg = friendly_error("SSL: CERTIFICATE_VERIFY_FAILED")
        self.assertEqual(msg, "خطأ في شهادة الأمان (SSL)")

    def test_json_parse_failure(self):
        msg = friendly_error("Expecting value: line 1 column 1 (char 0)")
        self.assertEqual(msg, "رد المزوّد غير مفهوم")


class FriendlyErrorFallbackTests(unittest.TestCase):
    """Task: the fallback must not claim a connection failure for a cause
    it never actually diagnosed — a programming error routed here (e.g.
    "'NoneType' object has no attribute 'upper'") is not a network problem,
    and telling the user it is misleads them into checking the wrong thing."""

    def test_unrecognised_error_gets_a_cause_neutral_prefix(self):
        msg = friendly_error("'NoneType' object has no attribute 'upper'")
        self.assertTrue(msg.startswith("خطأ غير متوقع"))
        self.assertNotIn("تعذّر الاتصال", msg)

    def test_fallback_keeps_a_truncated_raw_tail(self):
        msg = friendly_error("'NoneType' object has no attribute 'upper'")
        self.assertIn("NoneType", msg)

    def test_fallback_truncates_to_80_chars_of_the_flattened_text(self):
        raw = "x" * 200
        msg = friendly_error(raw)
        # prefix + ": " + at most 80 chars of the flattened raw text
        tail = msg.split(": ", 1)[1]
        self.assertLessEqual(len(tail), 80)

    def test_fallback_never_raises_on_a_non_string_argument(self):
        for value in (None, 1, 1.5, ["a"], {"a": 1}, object()):
            with self.subTest(value=value):
                friendly_error(value)   # must not raise


class FriendlyFsErrorTests(unittest.TestCase):
    def test_known_errno_codes_get_specific_arabic_messages(self):
        cases = {
            errno.EACCES:    "صلاحيات",
            errno.EPERM:     "صلاحيات",
            errno.ENOSPC:    "مساحة",
            errno.EROFS:     "للقراءة فقط",
            errno.ENOENT:    "المسار غير موجود",
            errno.EADDRINUSE: "المنفذ مستخدَم",
        }
        for code, fragment in cases.items():
            with self.subTest(code=code):
                exc = OSError(code, "raw os message")
                self.assertIn(fragment, friendly_fs_error(exc))

    def test_unknown_errno_falls_back_to_system_error_prefix_not_connection(self):
        exc = OSError(errno.EBUSY, "device or resource busy")
        msg = friendly_fs_error(exc)
        self.assertTrue(msg.startswith("خطأ في النظام"))
        self.assertNotIn("تعذّر الاتصال", msg)

    def test_arabic_exception_text_passes_through(self):
        msg = friendly_fs_error(Exception("فشل غير معروف"))
        self.assertEqual(msg, "فشل غير معروف")

    def test_empty_text_is_unknown_error(self):
        msg = friendly_fs_error(Exception(""))
        self.assertEqual(msg, "خطأ غير معروف")

    def test_non_oserror_exception_still_handled(self):
        # Plain exceptions (no .errno) must fall through to the generic
        # branch rather than raising on getattr.
        msg = friendly_fs_error(ValueError("boom"))
        self.assertTrue(msg.startswith("خطأ في النظام"))
        self.assertIn("boom", msg)


if __name__ == "__main__":
    unittest.main()
