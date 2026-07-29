#!/usr/bin/env python3
"""Lightweight in-process verification of the marsad REST API.

Uses FastAPI's TestClient, so no server or live LLM/email backends are needed.
Run from the repo root:

    python3 tools/test_api.py

The tests exercise the input queue, samples, dashboard, contacts, and settings
endpoints. They rely on the singleton AppService in api/app.py.
"""
import os
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

from api.app import app, service


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # clear_dashboard() deletes reports/latest.json — preserve the user's
        # real dashboard data around the suite and restore it afterwards.
        from api.services import LATEST_F
        cls._latest_backup = LATEST_F.read_bytes() if LATEST_F.exists() else None
        # Start each run with a clean report queue.
        service.clear_reports()
        service.clear_dashboard()

    @classmethod
    def tearDownClass(cls):
        service.clear_reports()
        service.clear_dashboard()
        if cls._latest_backup is not None:
            from api.services import LATEST_F
            LATEST_F.write_bytes(cls._latest_backup)

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
