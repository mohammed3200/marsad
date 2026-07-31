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


if __name__ == "__main__":
    unittest.main()
