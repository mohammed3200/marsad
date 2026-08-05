import socket
import unittest

from tests._isolation import isolated_state


class ReceiverLifecycleTests(unittest.TestCase):
    def test_failed_bind_leaves_no_half_built_receiver(self):
        import connectors
        blocker = socket.socket()
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        try:
            with isolated_state():
                hub = connectors.ConnectorHub({"whatsapp_token": "t", "email_user": "",
                                               "erp_folder": ""})
                ok = hub.start_whatsapp(port)
                self.assertFalse(ok, "start_whatsapp reported success on a busy port")
                self.assertIsNone(hub.whatsapp,
                                  "a non-listening receiver was left in place, "
                                  "which blocks every later retry")
        finally:
            blocker.close()

    def test_successful_start_then_stop_frees_the_port(self):
        import connectors, time
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        with isolated_state():
            hub = connectors.ConnectorHub({"whatsapp_token": "t", "email_user": "",
                                           "erp_folder": ""})
            self.assertTrue(hub.start_whatsapp(port))
            time.sleep(0.2)
            hub.stop_all()
        time.sleep(0.3)
        probe = socket.socket()
        probe.bind(("127.0.0.1", port))     # must not raise
        probe.close()


class TokenPersistenceTests(unittest.TestCase):
    def test_generated_token_is_written_to_settings(self):
        import backend.settings_bridge as sb
        import connectors
        with isolated_state():
            settings = sb.load_settings()
            settings["whatsapp_token"] = ""
            connectors.ConnectorHub(settings)
            on_disk = sb.load_settings()
        self.assertTrue(on_disk["whatsapp_token"],
                        "a freshly minted token was not persisted, so the next "
                        "run mints a different one and 403s its own bridge")


# ── moved here when the web API was removed ────────────────────────────
# These test connectors.py, not the API. They lived in
# tests/test_api_uploads.py only because that file was written when the
# upload endpoint was the thing under test; deleting it wholesale would
# have silently dropped real coverage of the read caps.


class WhatsAppReceiverCapTests(unittest.TestCase):
    """Fix round 1, important finding 4: WhatsAppReceiver.do_POST built a
    report with "content": text straight from the request body, with no
    _cap() — a content-producing path in the same file as the four capped
    readers above, feeding the same LLM prompt. It also read Content-Length
    bytes into memory with no upper bound before parsing JSON, the same
    unbounded-body pattern flagged for the HTTP upload endpoint, on a second
    local server.

    WhatsAppReceiver writes no app state — it only logs to the gitignored
    logs/connectors.log (pre-existing, deferred as minor 6) — so this class
    needs no isolated_state()."""

    def _free_port(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _start_receiver(self):
        import connectors
        received = []
        port = self._free_port()
        recv = connectors.WhatsAppReceiver(port, received.append)
        recv.start()
        self.addCleanup(recv.stop)
        return port, received

    def _post(self, port, path, body_bytes):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            conn.request("POST", path, body=body_bytes,
                        headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            status = resp.status
            resp.read()
        finally:
            conn.close()
        return status

    def test_whatsapp_message_content_is_capped(self):
        import connectors
        import json
        port, received = self._start_receiver()
        # A text long enough to need capping, but still comfortably under
        # MAX_WA_BODY_BYTES once encoded. ensure_ascii=False matches the real
        # sender: the Node/Baileys bridge's JSON.stringify does not escape
        # non-ASCII, unlike json.dumps' default — with the default, each
        # Arabic character would balloon to a 6-byte \uXXXX escape and blow
        # the body past the Content-Length ceiling before it ever reaches
        # the cap this test means to exercise.
        huge_text = "ب" * (connectors.MAX_CHARS + 5000)
        body = json.dumps({"group_id": "g1", "sender": "s", "text": huge_text},
                          ensure_ascii=False).encode("utf-8")
        self.assertLess(len(body), connectors.MAX_WA_BODY_BYTES)
        status = self._post(port, "/wa_message", body)
        self.assertEqual(status, 200)
        self.assertEqual(len(received), 1)
        rep = received[0][0]
        self.assertLessEqual(len(rep["content"]), connectors.MAX_CHARS + 200)
        self.assertIn("اقتُطع", rep["content"])

    def test_whatsapp_message_content_under_the_cap_is_untouched(self):
        import connectors
        import json
        port, received = self._start_receiver()
        body_text = "تحديث ميداني عبر واتساب"
        body = json.dumps({"group_id": "g1", "sender": "s", "text": body_text},
                          ensure_ascii=False).encode("utf-8")
        status = self._post(port, "/wa_message", body)
        self.assertEqual(status, 200)
        self.assertEqual(received[0][0]["content"], body_text)

    def test_oversized_whatsapp_body_is_rejected_before_reading(self):
        import connectors
        import json
        port, received = self._start_receiver()
        oversized = json.dumps({
            "group_id": "g1", "sender": "s",
            "text": "x" * (connectors.MAX_WA_BODY_BYTES + 1000),
        }).encode("utf-8")
        status = self._post(port, "/wa_message", oversized)
        self.assertEqual(status, 413)
        self.assertEqual(received, [])

if __name__ == "__main__":
    unittest.main()
