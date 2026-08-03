import json
import os
import sys
import types
import unittest
from unittest import mock

from tests._isolation import isolated_state


class SettingsStoreTests(unittest.TestCase):
    def test_defaults_cover_every_provider(self):
        import backend.settings_bridge as sb
        with isolated_state():
            d = sb.load_settings()
        for key in ("ai_backend", "ollama_url", "claude_api_key", "openai_base_url",
                    "gemini_api_key", "azure_endpoint", "email_password",
                    "whatsapp_token", "engine_profiles"):
            self.assertIn(key, d)

    def test_saved_file_is_owner_only(self):
        import backend.settings_bridge as sb
        with isolated_state():
            sb.save_settings(sb.load_settings())
            mode = os.stat(sb.SETTINGS_F).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_failed_write_leaves_the_original_intact(self):
        import json as _json
        import backend.settings_bridge as sb
        with isolated_state() as root:
            good = sb.load_settings()
            good["ollama_model"] = "original"
            sb.save_settings(good)
            before = sb.SETTINGS_F.read_bytes()

            doomed = dict(good, ollama_model="never-written")
            with mock.patch.object(_json, "dump", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    sb.save_settings(doomed)

            self.assertEqual(sb.SETTINGS_F.read_bytes(), before)
            leftovers = [p.name for p in root.iterdir() if p.name.startswith(".settings-")]
        self.assertEqual(leftovers, [])

    def test_changed_keys_preserves_other_processes_edits(self):
        import backend.settings_bridge as sb
        with isolated_state():
            base = sb.load_settings()
            base["smtp_host"] = "smtp.example.com"
            sb.save_settings(base)

            stale = dict(base)              # a second process's older snapshot
            stale["smtp_host"] = "STALE"
            stale["ollama_model"] = "qwen"
            sb.save_settings(stale, changed_keys={"ollama_model"})

            on_disk = json.loads(sb.SETTINGS_F.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["ollama_model"], "qwen")
        self.assertEqual(on_disk["smtp_host"], "smtp.example.com")

    def test_empty_changed_keys_writes_the_whole_dict(self):
        import backend.settings_bridge as sb
        with isolated_state():
            base = sb.load_settings()
            sb.save_settings(base)
            base["ollama_model"] = "switched-by-profile"
            base["ai_backend"] = "claude"
            sb.save_settings(base, changed_keys=set())   # what saveSettings({}) produces
            on_disk = sb.load_settings()
        self.assertEqual(on_disk["ollama_model"], "switched-by-profile")
        self.assertEqual(on_disk["ai_backend"], "claude")

    def test_isolation_covers_the_controller_path_globals(self):
        """Regression: this test used to swap in a fake module and `del`
        it in `finally` — which discards whatever real `backend.controller`
        was registered in sys.modules before this test ran, rather than
        restoring it. isolated_state() looks the module up via
        `sys.modules.get("backend.controller")`, so any test executed
        after this one (unittest discover runs files in sorted order —
        test_settings_store sorts before test_shutdown) would silently
        stop being redirected into a temp dir and run its 14
        AppController() constructions against the developer's real
        settings.json/reports/data. Save-and-restore the real module
        object instead, exactly like isolated_state() itself does for
        every other patched global."""
        real_controller = sys.modules.get("backend.controller")
        fake = types.ModuleType("backend.controller")
        fake.REPORTS = "REAL_REPORTS"
        fake.SAMPLES_F = "REAL_SAMPLES"
        fake.LATEST_F = "REAL_LATEST"
        fake.DATA_DIR = "REAL_DATA_DIR"
        sys.modules["backend.controller"] = fake
        try:
            with isolated_state() as root:
                self.assertNotEqual(fake.REPORTS, "REAL_REPORTS")
                self.assertEqual(str(fake.LATEST_F).startswith(str(root)), True)
                self.assertEqual(fake.DATA_DIR, root)
            self.assertEqual(fake.REPORTS, "REAL_REPORTS")   # restored
            self.assertEqual(fake.LATEST_F, "REAL_LATEST")
            self.assertEqual(fake.DATA_DIR, "REAL_DATA_DIR")
        finally:
            if real_controller is not None:
                sys.modules["backend.controller"] = real_controller
            else:
                sys.modules.pop("backend.controller", None)
            # The real module (if any) must come back exactly as it was —
            # not left holding this test's temp-dir globals.
            if real_controller is not None:
                self.assertIs(sys.modules["backend.controller"], real_controller)


if __name__ == "__main__":
    unittest.main()
