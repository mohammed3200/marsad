"""Regression coverage for core/contacts.py's atomic write.

Before this fix, ContactsDB._save_data() opened CONTACTS_FILE directly and
wrote into it in place — the last non-atomic write of authoritative user
data in the app (core/engine.py's results writer and
backend/settings_bridge.py's save_settings() were both already atomic). A
write interrupted partway through (disk full, process killed) left
contacts.json truncated or corrupt, and every add/update/delete_employee
call goes straight through this write, unguarded, from a @Slot.
"""
import json
import unittest
from unittest import mock

from tests._isolation import isolated_state


class ContactsAtomicWriteTests(unittest.TestCase):
    def test_failed_write_leaves_the_original_intact(self):
        import core.contacts as contacts

        with isolated_state():
            db = contacts.ContactsDB()
            db.add_employee({"name": "أحمد", "dept": "ops", "email": "a@example.com"})
            before = contacts.CONTACTS_FILE.read_bytes()

            with mock.patch.object(json, "dump", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    db.add_employee({"name": "لن يُكتب", "dept": "ops"})

            self.assertEqual(contacts.CONTACTS_FILE.read_bytes(), before)
            leftovers = [p.name for p in contacts.CONTACTS_FILE.parent.iterdir()
                        if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_add_employee_reaches_disk_leaving_no_temp_sibling(self):
        import core.contacts as contacts

        with isolated_state():
            db = contacts.ContactsDB()
            emp_id = db.add_employee({"name": "منى", "dept": "quality"})
            on_disk = json.loads(contacts.CONTACTS_FILE.read_text(encoding="utf-8"))
            # The atomic write goes through a `.tmp` sibling; os.replace must
            # have consumed it. A leftover means the rename never happened and
            # the visible file is whatever a previous run left there.
            leftovers = list(contacts.CONTACTS_FILE.parent.glob("*.tmp"))
        names = [e["name"] for e in on_disk["employees"]]
        self.assertIn("منى", names)
        self.assertTrue(emp_id)
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
