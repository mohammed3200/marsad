"""Daemon-thread workers must hand their result across, not act on it.

Four workers ran on `threading.Thread(daemon=True)` and mutated controller
state and emitted public signals directly from that thread. Two problems:
the mutation races the GUI thread, and an emit after teardown raises
`RuntimeError: Signal source has been deleted` out of a daemon thread, where
nothing catches it — it reaches `threading.excepthook` and prints a traceback
on exit.

The file already had the right pattern for one worker (`_run_send_email` →
`_emailSent` → `_on_email_sent`). These tests pin that the other four now
follow it.

Each `test_*_worker_emits_only_its_private_signal` fails against the pre-fix
code, where the worker emitted the public signal itself.
"""
import unittest
from unittest import mock

from tests._isolation import isolated_state


class _Sig:
    """Records emissions. Stands in for a Signal on an instance."""

    def __init__(self, name, sink):
        self.name = name
        self.sink = sink

    def emit(self, *args):
        self.sink.append((self.name, args))


class _WorkerHarness:
    """An AppController with no Qt event loop and every signal recorded.

    Built with __new__ so no QObject/C++ half is created: these tests are
    about which signal a plain Python method reaches for, which needs no
    running Qt.
    """

    PUBLIC = ("notify", "logMessage", "connectionTested", "emailTested",
              "engineChanged", "modelsChanged")
    PRIVATE = ("_connTested", "_mailTested", "_modelsFetched", "_workerMessage")

    def __init__(self):
        from backend.controller import AppController

        self.emitted = []
        c = AppController.__new__(AppController)
        for n in self.PUBLIC + self.PRIVATE:
            setattr(c, n, _Sig(n, self.emitted))
        c._shutting_down = False
        c._settings = {}
        c._online = False
        c._status = "غير متصل"
        c._models = []
        c._testing_engine = c._testing_email = c._models_busy = False
        c._wa_starting = False
        # Guard-flag setters emit their own notify signal; neutralise them so
        # only the worker's own emissions are recorded.
        c._set_testing_engine = lambda v: None
        c._set_testing_email = lambda v: None
        c._set_models_busy = lambda v: None
        c._set_wa_starting = lambda v: None
        self.c = c

    def names(self):
        return [n for n, _ in self.emitted]

    def public_emitted(self):
        return [n for n in self.names() if n in self.PUBLIC]

    def private_emitted(self):
        return [n for n in self.names() if n in self.PRIVATE]


class _FakeAI:
    def __init__(self, conn=None, models=None):
        self._conn = conn
        self._models = models

    def test_connection(self):
        return self._conn

    def list_models(self):
        return self._models


class WorkerEmissionTests(unittest.TestCase):

    def test_connection_test_worker_emits_only_its_private_signal(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._ai = _FakeAI(conn=(True, "الاتصال ناجح"))
            h.c._run_connection_test()
        self.assertEqual(h.public_emitted(), [])
        self.assertEqual(h.private_emitted(), ["_connTested"])

    def test_email_test_worker_emits_only_its_private_signal(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._hub = type("H", (), {"test_email": lambda s: (False, "خطأ")})()
            h.c._run_email_test()
        self.assertEqual(h.public_emitted(), [])
        self.assertEqual(h.private_emitted(), ["_mailTested"])

    def test_fetch_models_worker_emits_only_its_private_signal(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._ai = _FakeAI(models=(True, ["a", "b"]))
            h.c._run_fetch_models()
        self.assertEqual(h.public_emitted(), [])
        self.assertEqual(h.private_emitted(), ["_modelsFetched"])

    def test_bridge_start_worker_emits_only_its_private_signal(self):
        """The bridge worker reports progress from several points rather than
        returning one result, so it routes through _workerMessage.

        subprocess is stubbed: unstubbed, this test really runs `npm install`
        against the registry — 150s and a network dependency inside a unit
        suite.
        """
        import subprocess

        class _Done:
            returncode = 0
            stdout = stderr = ""

        with isolated_state(), \
                mock.patch.object(subprocess, "run", lambda *a, **k: _Done()), \
                mock.patch.object(subprocess, "Popen",
                                  lambda *a, **k: type("P", (), {"pid": 1})()):
            h = _WorkerHarness()
            h.c._hub = type("H", (), {"wa_token": "t"})()
            h.c._run_bridge_start()
        self.assertEqual(h.public_emitted(), [])
        self.assertTrue(h.private_emitted(), "worker reported nothing at all")
        self.assertEqual(set(h.private_emitted()), {"_workerMessage"})

    def test_a_worker_never_mutates_controller_state(self):
        """The state change belongs in the slot, on the GUI thread."""
        with isolated_state():
            h = _WorkerHarness()
            h.c._ai = _FakeAI(conn=(True, "الاتصال ناجح"))
            h.c._run_connection_test()
            self.assertFalse(h.c._online, "_online was set on the worker thread")
            self.assertEqual(h.c._status, "غير متصل")

            h2 = _WorkerHarness()
            h2.c._ai = _FakeAI(models=(True, ["a", "b"]))
            h2.c._run_fetch_models()
            self.assertEqual(h2.c._models, [],
                             "_models was set on the worker thread")


class SlotEffectTests(unittest.TestCase):
    """The slots must produce exactly what the workers stopped producing —
    otherwise the fix would silently drop user-visible behaviour."""

    def test_conn_tested_slot_sets_state_and_emits(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._on_conn_tested(True, "الاتصال ناجح")
        self.assertTrue(h.c._online)
        self.assertEqual(h.c._status, "متصل")
        self.assertEqual(h.public_emitted(), ["engineChanged", "connectionTested"])

    def test_conn_tested_slot_reports_offline_on_failure(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._on_conn_tested(False, "تعذّر الوصول إلى الخادم")
        self.assertFalse(h.c._online)
        self.assertEqual(h.c._status, "غير متصل")

    def test_mail_tested_slot_emits_the_public_signal(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._on_mail_tested(False, "تعذّر الإرسال")
        self.assertEqual(h.public_emitted(), ["emailTested"])

    def test_models_fetched_slot_sets_the_list_and_notifies(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._on_models_fetched(True, ["a", "b"], "جُلبت 2 نموذجاً")
        self.assertEqual(h.c._models, ["a", "b"])
        self.assertEqual(h.public_emitted(), ["modelsChanged", "notify"])

    def test_worker_message_slot_routes_log_and_notify(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._on_worker_message("log", "سطر سجل")
            h.c._on_worker_message("notify", "تنبيه")
        self.assertEqual(h.public_emitted(), ["logMessage", "notify"])


class ShutdownSafetyTests(unittest.TestCase):
    """A worker finishing after teardown must not raise out of its thread."""

    def test_workers_emit_nothing_once_shutting_down(self):
        with isolated_state():
            h = _WorkerHarness()
            h.c._shutting_down = True
            h.c._ai = _FakeAI(conn=(True, "ok"), models=(True, ["a"]))
            h.c._hub = type("H", (), {"test_email": lambda s: (True, "ok")})()
            h.c._run_connection_test()
            h.c._run_email_test()
            h.c._run_fetch_models()
        self.assertEqual(h.emitted, [])

    def test_a_deleted_cpp_half_does_not_escape_the_worker(self):
        """RuntimeError from a dead C++ object is caught, not raised into
        threading.excepthook where nothing handles it."""
        class _DeadSig:
            def emit(self, *a):
                raise RuntimeError("Signal source has been deleted")

        with isolated_state():
            h = _WorkerHarness()
            h.c._ai = _FakeAI(conn=(True, "ok"), models=(True, ["a"]))
            h.c._hub = type("H", (), {"test_email": lambda s: (True, "ok")})()
            h.c._connTested = _DeadSig()
            h.c._mailTested = _DeadSig()
            h.c._modelsFetched = _DeadSig()
            h.c._workerMessage = _DeadSig()
            h.c._run_connection_test()      # must not raise
            h.c._run_email_test()
            h.c._run_fetch_models()
            h.c._emit_from_worker("notify", "x")


if __name__ == "__main__":
    unittest.main()
