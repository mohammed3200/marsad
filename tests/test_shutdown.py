"""Closing the window mid-analysis must not abort the process.

Regression coverage for AppController.shutdown(): before this existed, the
QThread running an analysis was torn down while still running when the
QApplication object graph was destroyed, and Qt called qFatal — a
multi-minute Ollama analysis plus an impatient user was all it took (see
`.superpowers/sdd/2026-07-28-launch-readiness/task-12-brief.md`, Step 1, for
a standalone reproduction of the underlying QThread behaviour).

This constructs a real AppController (redirected into a temp dir via
isolated_state() so it never touches the user's real settings.json, reports/
or WhatsApp receiver port), attaches a slow worker to a QThread exactly the
way runAnalysis() does, and asserts shutdown() actually interrupts a *live*
thread rather than merely tidying up an idle one.
"""
import os
import sys
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # headless-safe

from PySide6.QtCore import QObject, QThread, Signal, Slot  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tests._isolation import isolated_state  # noqa: E402

from backend.controller import AppController  # noqa: E402


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


class _SlowWorker(QObject):
    """Stands in for AnalysisWorker: blocks the thread's event loop the way a
    real multi-minute Ollama call would, checking for interruption the way
    well-behaved long-running work should."""

    finished = Signal()

    def __init__(self):
        super().__init__()
        self.started_running = False
        self.ran_to_completion = False

    @Slot()
    def run(self):
        self.started_running = True
        thread = QThread.currentThread()
        for _ in range(100):               # up to 5s if never interrupted
            if thread.isInterruptionRequested():
                return
            time.sleep(0.05)
        self.ran_to_completion = True
        self.finished.emit()


class ShutdownTests(unittest.TestCase):
    def setUp(self):
        _app()

    def test_shutdown_is_a_noop_with_no_analysis_running_and_is_idempotent(self):
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)
            c.shutdown()   # must not raise
            c.shutdown()   # calling it again must not raise either

    def test_shutdown_interrupts_a_live_analysis_thread(self):
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)

            thread = QThread(c)
            worker = _SlowWorker()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)

            def _safety_net():
                # If shutdown() regresses and leaves the thread running, fail
                # this the boring way (an assertion below) rather than let a
                # leaked running QThread abort the interpreter at exit.
                if thread.isRunning():
                    thread.requestInterruption()
                    thread.quit()
                    thread.wait(2000)
            self.addCleanup(_safety_net)

            c._thread = thread
            c._worker = worker
            thread.start()

            deadline = time.time() + 2
            while not worker.started_running and time.time() < deadline:
                time.sleep(0.01)
            self.assertTrue(worker.started_running,
                             "worker never started — test setup is broken")

            c.shutdown()

            self.assertIsNone(c._thread)
            self.assertIsNone(c._worker)
            self.assertFalse(thread.isRunning(),
                              "shutdown() returned while the analysis thread "
                              "was still running — this is exactly what used "
                              "to crash the app on quit")
            self.assertFalse(worker.ran_to_completion,
                              "shutdown() should interrupt the worker, not "
                              "let it finish on its own")

            c.shutdown()   # idempotent even with a just-torn-down thread

    def test_shutdown_stops_the_connector_hub(self):
        """shutdown() must reach ConnectorHub.stop_all(), not just the thread
        and the WhatsApp bridge — a stray IMAP/ERP watcher left alive on quit
        is the same class of bug this task closes."""
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)

            calls = []
            c._hub.stop_all = lambda: calls.append(True)

            c.shutdown()

            self.assertEqual(calls, [True])


if __name__ == "__main__":
    unittest.main()
