import unittest

from core.status import tier


class StatusTierTests(unittest.TestCase):
    def test_good_literals(self):
        for s in ("جيد", "مكتمل", "آمن", "منخفضة"):
            self.assertEqual(tier(s), "good", s)

    def test_warn_literals(self):
        for s in ("متوسط", "متوسطة", "تحذير", "في الموعد"):
            self.assertEqual(tier(s), "warn", s)

    def test_bad_literals(self):
        for s in ("متأخر", "خطر", "عالية"):
            self.assertEqual(tier(s), "bad", s)

    def test_unknown_and_empty_are_neutral_not_critical(self):
        for s in ("", None, "غير محدد", "شيء آخر"):
            self.assertEqual(tier(s), "neutral", repr(s))

    def test_non_string_truthy_values_do_not_raise(self):
        """`_ensure_chief_schema` only guarantees the chief dict's *keys*
        exist, never their value types — a model can return
        overall_health=["جيد"], a risk level of {"v": "عالية"}, or a KPI
        status of 1. Before this fix `(literal or "").strip()` raised
        AttributeError on every one of these, taking down all three
        exporters. None of them classify as anything but neutral (they
        don't equal any known literal once stringified) — the point is
        only that tier() must never raise."""
        for value in (["جيد"], ["عالية"], {"v": "متأخر"}, 1, 1.5, True, ("عالية",)):
            with self.subTest(value=value):
                self.assertEqual(tier(value), "neutral", repr(value))


if __name__ == "__main__":
    unittest.main()
