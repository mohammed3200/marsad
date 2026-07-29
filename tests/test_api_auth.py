"""Reduced-scope Task 5 tests: the web API does not ship in this release.

Covers only what actually ships: the hard opt-in gate (importing api.app
without MARSAD_API_ENABLE=1 must fail) and the two secret-handling contracts
on /api/settings — values are never echoed back, and a blank secret in a PUT
means "leave it alone". The full token/Host/Origin/`/ws` auth suite is out of
scope for this release; see the launch-readiness plan, task 5, "REDUCED FOR
THIS RELEASE".

AppService() is constructed at import time of api.app and reads/writes the
real settings.json, including starting a real WhatsApp receiver if
whatsapp_enabled is set. tests/_isolation.py's isolated_state() does not cover
api/services.py's paths, so instead this suite backs the real settings file
up, forces whatsapp_enabled off for its duration, and restores the original
bytes afterward — the same real-state guard tools/test_api.py already applies
around reports/latest.json, applied here to settings.json.
"""
import os
import unittest

os.environ["MARSAD_API_ENABLE"] = "1"

from backend.settings_bridge import SETTINGS_F, load_settings, save_settings  # noqa: E402


def _client():
    from fastapi.testclient import TestClient
    from api.app import app
    return TestClient(app, base_url="http://127.0.0.1")


class ApiGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._had_settings = SETTINGS_F.exists()
        cls._backup = SETTINGS_F.read_bytes() if cls._had_settings else None
        # api.app builds the AppService singleton on first import, below —
        # keep whatsapp off for the life of this suite regardless of the
        # developer's real config, so no real receiver gets started.
        safe = load_settings()
        safe["whatsapp_enabled"] = False
        save_settings(safe)

    @classmethod
    def tearDownClass(cls):
        if cls._had_settings:
            SETTINGS_F.write_bytes(cls._backup)
        elif SETTINGS_F.exists():
            SETTINGS_F.unlink()

    def test_import_without_the_flag_is_refused(self):
        import subprocess
        import sys
        proc = subprocess.run(
            [sys.executable, "-c", "import api.app"],
            capture_output=True, text=True,
            env={k: v for k, v in os.environ.items() if k != "MARSAD_API_ENABLE"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("MARSAD_API_ENABLE", proc.stderr)

    def test_settings_never_returns_secret_values(self):
        from api.app import SECRET_KEYS
        r = _client().get("/api/settings")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in SECRET_KEYS:
            self.assertEqual(body.get(key, ""), "",
                             f"{key} was returned to the client")
        self.assertIn("secrets_set", body)

    def test_blank_secret_in_a_put_does_not_wipe_the_stored_one(self):
        from api.app import service
        before = service.settings.get("gemini_api_key", "")
        _client().put("/api/settings",
                      json={"gemini_api_key": "", "ollama_model": "probe-model"})
        self.assertEqual(service.settings.get("gemini_api_key", ""), before)
        self.assertEqual(service.settings.get("ollama_model"), "probe-model")


if __name__ == "__main__":
    unittest.main()
