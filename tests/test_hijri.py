import datetime
import unittest

from core.hijri import dual_label, gregorian_to_hijri, hijri_label


class HijriTests(unittest.TestCase):
    def test_known_conversions(self):
        self.assertEqual(gregorian_to_hijri(2000, 1, 1), (1420, 9, 24))
        self.assertEqual(gregorian_to_hijri(2023, 3, 23), (1444, 9, 1))

    def test_labels(self):
        self.assertEqual(hijri_label(datetime.date(2000, 1, 1)), "٢٤ رمضان ١٤٢٠ هـ")
        self.assertEqual(hijri_label(datetime.date(2023, 3, 23)), "١ رمضان ١٤٤٤ هـ")

    def test_dual_label_uses_a_bundled_separator(self):
        label = dual_label(datetime.date(2023, 3, 23))
        self.assertEqual(label, "١ رمضان ١٤٤٤ هـ، 2023-03-23")
        self.assertNotIn("·", label)

    def test_dual_label_today_ends_with_the_iso_date(self):
        self.assertTrue(dual_label().endswith(datetime.date.today().isoformat()))


if __name__ == "__main__":
    unittest.main()
