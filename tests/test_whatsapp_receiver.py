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


if __name__ == "__main__":
    unittest.main()
