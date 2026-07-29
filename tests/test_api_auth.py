"""Reduced-scope Task 5 tests: the web API does not ship in this release.

Covers only what actually ships: the hard opt-in gate (importing api.app
without MARSAD_API_ENABLE=1 must fail) and the secret-handling contracts on
/api/settings — values are never echoed back (top-level or inside a saved
engine profile), and a blank secret in a PUT means "leave it alone". The full
token/Host/Origin/`/ws` auth suite is out of scope for this release; see the
launch-readiness plan, task 5, "REDUCED FOR THIS RELEASE".

AppService() is constructed at import time of api.app and reads/writes
settings.json (plus reports/, data/contacts.json), and can start a real
WhatsApp receiver if whatsapp_enabled is set. tests/_isolation.py's
isolated_state() redirects backend.settings_bridge, core.engine, core.contacts
and api.services's writable-state path globals into a fresh temp directory —
entered for the whole class (not per test) because api.app's module-level
`service = AppService()` singleton is constructed once, on first import, and
must see the redirected paths at that moment. This suite never touches the
real settings.json / reports/ / data/.
"""
import os
import unittest

os.environ["MARSAD_API_ENABLE"] = "1"

from tests._isolation import isolated_state  # noqa: E402

# A fixture value standing in for a real provider key — never a real secret.
# Only ever compared for equality against itself / checked for absence; never
# printed or logged.
_FAKE_PROFILE_KEY = "sk-fixture-not-a-real-key-0000000000"


def _client():
    from fastapi.testclient import TestClient
    from api.app import app
    return TestClient(app, base_url="http://127.0.0.1")


class ApiGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Entered for the life of the class, not per-test: api.app builds its
        # AppService singleton once, at first import, so the redirected paths
        # must already be in place before that first import happens inside
        # any test method below.
        cls._iso = isolated_state()
        cls._root = cls._iso.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._iso.__exit__(None, None, None)

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

    def test_engine_profile_secrets_are_redacted_and_survive_a_round_trip(self):
        """A saved engine profile (settings["engine_profiles"]) carries a full
        copy of the provider keys (api/services.py ENGINE_KEYS) — GET must
        redact those the same way it redacts the top-level settings, and a
        GET-then-PUT round trip must not wipe the stored profile's key."""
        from api.app import service
        service.settings["engine_profiles"] = [{
            "name": "profile-under-test",
            "ai_backend": "openai",
            "ai_timeout": 180,
            "ollama_url": "http://localhost:11434",
            "ollama_model": "llama3.2",
            "claude_api_key": "",
            "claude_model": "claude-opus-4-5",
            "openai_api_key": _FAKE_PROFILE_KEY,
            "openai_base_url": "https://api.openai.com/v1",
            "openai_model": "gpt-4o-mini",
            "gemini_api_key": "",
            "gemini_model": "gemini-2.0-flash",
            "azure_endpoint": "",
            "azure_api_key": "",
            "azure_deployment": "",
            "azure_api_version": "2024-06-01",
        }]

        r = _client().get("/api/settings")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(_FAKE_PROFILE_KEY, r.text,
                         "a saved profile's real key leaked through GET /api/settings")
        body = r.json()
        profiles = body.get("engine_profiles", [])
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].get("openai_api_key", ""), "")
        self.assertEqual(profiles[0].get("claude_api_key", ""), "")
        self.assertIn("secrets_set", profiles[0])
        self.assertTrue(profiles[0]["secrets_set"]["openai_api_key"])
        self.assertFalse(profiles[0]["secrets_set"]["claude_api_key"])

        # GET-then-PUT the same body back must not wipe the profile's key.
        r2 = _client().put("/api/settings", json=body)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["ok"])
        stored = service.settings["engine_profiles"][0]
        self.assertEqual(stored["openai_api_key"], _FAKE_PROFILE_KEY)
        self.assertEqual(stored["claude_api_key"], "")

    # ── malformed engine_profiles must degrade, never 500 (fix round 2) ──
    # engine_profiles is hand-editable JSON on disk and PUT-able by any local
    # caller, so _redact_profile / _restore_profile_secrets cannot assume it
    # is already a clean list of dicts. Each test below is self-contained
    # (sets service.settings["engine_profiles"] itself) so run order doesn't
    # matter.

    def test_get_with_stored_profiles_as_a_string_degrades_to_empty(self):
        from api.app import service
        service.settings["engine_profiles"] = "not-a-list"
        r = _client().get("/api/settings")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["engine_profiles"], [])

    def test_get_with_stored_profiles_as_none_degrades_to_empty(self):
        from api.app import service
        service.settings["engine_profiles"] = None
        r = _client().get("/api/settings")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["engine_profiles"], [])

    def test_get_with_a_bad_entry_mixed_into_stored_profiles_skips_it(self):
        from api.app import service
        service.settings["engine_profiles"] = [{"name": "ok"}, "bad-entry", 42]
        r = _client().get("/api/settings")
        self.assertEqual(r.status_code, 200)
        profiles = r.json()["engine_profiles"]
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "ok")
        # read-only: the stored (still-malformed) list itself is untouched
        self.assertEqual(len(service.settings["engine_profiles"]), 3)

    def test_put_with_engine_profiles_as_a_string_is_ignored_not_wiped(self):
        from api.app import service
        service.settings["engine_profiles"] = [{"name": "keep-me"}]
        r = _client().put("/api/settings", json={"engine_profiles": "not-a-list"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        # malformed shape is dropped from the PUT, not applied — a client
        # sending garbage must not wipe whatever profiles are actually saved
        self.assertEqual(service.settings["engine_profiles"], [{"name": "keep-me"}])

    def test_put_with_a_bad_entry_mixed_into_submitted_profiles_skips_it(self):
        from api.app import service
        service.settings["engine_profiles"] = []
        r = _client().put("/api/settings",
                          json={"engine_profiles": [{"name": "ok"}, "bad-entry"]})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        stored = service.settings["engine_profiles"]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["name"], "ok")


if __name__ == "__main__":
    unittest.main()
