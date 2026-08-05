"""What a brand-new user gets before they configure anything.

`backend/settings_bridge.load_settings` returns the first of
(settings.json, settings.example.json) that exists, so on a machine with no
saved config **the shipped example file IS the live config**. Anything left in
it is not a sample — it is that user's real settings.

That is how 14 `*@example.com` addresses came to sit in `email_dept_map`:
`AppController._refresh_recipients` falls back to `email_dept_map.keys()` when
`report_recipients` is empty, so the Reports page listed them under
«سيُرسَل إلى:» with the Send button enabled, one click from an SMTP delivery
attempt to fourteen fabricated addresses.

These tests fail against that example file.
"""
import json
import os
import shutil
import unittest

from tests._isolation import isolated_state

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(REPO, "settings.example.json")


class FreshInstallTests(unittest.TestCase):

    def _example(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            return json.load(fh)

    def test_the_shipped_example_carries_no_routing_entries(self):
        """Empty, not illustrative. An address here is a live recipient."""
        cfg = self._example()
        self.assertEqual(cfg["email_dept_map"], {})
        self.assertEqual(cfg["whatsapp_groups"], {})
        self.assertEqual(cfg["report_recipients"], [])

    def test_the_shipped_example_holds_no_placeholder_addresses(self):
        raw = json.dumps(self._example(), ensure_ascii=False)
        for marker in ("example.com", "+1000000000", "example.org", "test@"):
            self.assertNotIn(marker, raw, f"placeholder {marker!r} ships to users")

    def test_the_shipped_example_carries_no_credentials(self):
        cfg = self._example()
        for key in ("claude_api_key", "openai_api_key", "gemini_api_key",
                    "azure_api_key", "email_user", "email_password"):
            self.assertEqual(cfg[key], "", f"{key} must ship blank")

    def test_a_fresh_install_offers_no_recipients(self):
        """The end-to-end shape of it: load the example as the live config the
        way a first launch does, and resolve recipients exactly as
        AppController does."""
        import backend.settings_bridge as sb

        with isolated_state() as root:
            # No settings.json — only the example, which is what ships.
            shutil.copy(EXAMPLE, sb.EXAMPLE_F)
            self.assertFalse(sb.SETTINGS_F.exists())
            cfg = sb.load_settings()

            # backend/controller.py::_refresh_recipients, verbatim.
            recipients = (cfg.get("report_recipients")
                          or list(cfg.get("email_dept_map", {}).keys()))
            self.assertEqual(recipients, [])
            self.assertTrue(str(root))          # keep the temp root referenced

    def test_defaults_alone_also_offer_no_recipients(self):
        """The third fallback, when even the example is missing."""
        import backend.settings_bridge as sb

        with isolated_state():
            self.assertFalse(sb.SETTINGS_F.exists())
            self.assertFalse(sb.EXAMPLE_F.exists())
            cfg = sb.load_settings()
            recipients = (cfg.get("report_recipients")
                          or list(cfg.get("email_dept_map", {}).keys()))
            self.assertEqual(recipients, [])


if __name__ == "__main__":
    unittest.main()
