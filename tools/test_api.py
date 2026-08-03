#!/usr/bin/env python3
"""Lightweight in-process verification of the marsad REST API.

Uses FastAPI's TestClient, so no server or live LLM/email backends are needed.
Run from the repo root:

    python3 tools/test_api.py

The tests exercise the input queue, samples, dashboard, contacts, and settings
endpoints. They rely on the singleton AppService in api/app.py.
"""
import os
import shutil
import sys
import unittest
from pathlib import Path

# Ensure repo root is on path when running as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The web API does not ship in this release — importing api.app refuses
# unless this is set. This tool is an explicit, opt-in dev check.
os.environ["MARSAD_API_ENABLE"] = "1"

from fastapi.testclient import TestClient

from tests._isolation import isolated_state


class ApiSmokeTests(unittest.TestCase):
    # This suite MUST run under isolated_state(), entered here in setUpClass
    # before api.app is ever imported. api.app builds its AppService
    # singleton at import time (`service = AppService()`), and that
    # singleton's clear_dashboard() unlinks reports/latest.json outright —
    # against the real DATA_DIR, that means any run that never reaches
    # tearDownClass (a crash, Ctrl-C, a timeout, an OOM kill) permanently
    # destroys the developer's last analysis, with no recovery, because
    # reports/latest.json is gitignored. That is not hypothetical: an
    # earlier hand-rolled backup/restore version of this file did exactly
    # that. isolated_state() redirects every writable-state path (settings,
    # reports, contacts) into a throwaway temp directory for the life of the
    # class, so there is nothing real left to destroy — do not revert to
    # touching the real DATA_DIR here.
    @classmethod
    def setUpClass(cls):
        cls._iso = isolated_state()
        cls._root = cls._iso.__enter__()
        global app, service
        from api.app import app, service
        # isolated_state() deliberately leaves SAMPLES_F pointing at a path
        # that doesn't exist (other suites exercise that failure path) — this
        # suite's test_samples_and_clear exercises the success path via
        # POST /api/reports/samples, so seed the isolated location with a
        # copy of the real sample_reports.json (never written to; read-only).
        import api.services as svc
        shutil.copy(ROOT / "sample_reports.json", svc.SAMPLES_F)
        cls.client = TestClient(app)
        # Start each run with a clean report queue.
        service.clear_reports()
        service.clear_dashboard()

    @classmethod
    def tearDownClass(cls):
        service.clear_reports()
        service.clear_dashboard()
        cls._iso.__exit__(None, None, None)

    def test_meta(self):
        r = self.client.get("/api/meta")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("today_label", data)
        self.assertIn("backend", data)
        self.assertIn("engine_online", data)
        self.assertIn("engine_status", data)
        self.assertIn("reports_dir", data)

    def test_settings_roundtrip(self):
        original = self.client.get("/api/settings").json()
        # Save current settings back unchanged; should not raise.
        r = self.client.put("/api/settings", json=original)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_reports_crud(self):
        service.clear_reports()

        # Empty queue.
        r = self.client.get("/api/reports")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 0)

        # Add a manual report.
        r = self.client.post("/api/reports", json={
            "content": "أنجز فريق الموقع 80% من أعمال الحفر اليوم",
            "dept": "ops",
            "source": "يدوي",
        })
        self.assertEqual(r.status_code, 201)

        r = self.client.get("/api/reports")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)

        # Reject empty report.
        r = self.client.post("/api/reports", json={"content": ""})
        self.assertEqual(r.status_code, 400)

        # Remove the report.
        r = self.client.delete("/api/reports/0")
        self.assertEqual(r.status_code, 200)

        r = self.client.get("/api/reports")
        self.assertEqual(r.json()["count"], 0)

        # Out-of-range delete returns 404.
        r = self.client.delete("/api/reports/99")
        self.assertEqual(r.status_code, 404)

    def test_samples_and_clear(self):
        service.clear_reports()
        r = self.client.post("/api/reports/samples")
        self.assertEqual(r.status_code, 200)
        loaded = r.json()["loaded"]
        self.assertGreater(loaded, 0)

        r = self.client.get("/api/reports")
        self.assertEqual(r.json()["count"], loaded)

        r = self.client.delete("/api/reports")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/api/reports").json()["count"], 0)

    def test_dashboard(self):
        r = self.client.get("/api/dashboard")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("chief", data)
        self.assertIn("date", data)
        self.assertIn("has_results", data)

        r = self.client.delete("/api/dashboard")
        self.assertEqual(r.status_code, 200)

    def test_contacts_structure(self):
        r = self.client.get("/api/contacts/structure")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), dict)

        r = self.client.get("/api/contacts/employees")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_snapshot_matches_get_endpoints(self):
        snapshot = service.snapshot()
        self.assertIn("reports_count", snapshot)
        self.assertIn("agents", snapshot)
        self.assertIn("busy", snapshot)
        self.assertEqual(len(snapshot["agents"]), 11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
