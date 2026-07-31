"""Closing the window mid-analysis must not abort the process — and, after
review round 1, must not hang it either.

Regression coverage for AppController.shutdown(). Round 1 history, in brief
(see `.superpowers/sdd/2026-07-28-launch-readiness/task-12-findings-r1.md`
for the full findings and reproductions):

- Originally the QThread running an analysis was torn down while still
  running when the QApplication object graph was destroyed, and Qt called
  qFatal.
- The first fix (requestInterruption + quit + wait(5000), falling back to
  terminate()) looked safe but wasn't: nothing in the pipeline polled for
  interruption, so requestInterruption() was a no-op, wait(5000) timed out on
  essentially every quit during a live analysis, and terminate() ran as the
  *normal* case — which can permanently deadlock the process if the thread
  is cancelled while holding the GIL's internal mutex. That is worse than
  the abort this task set out to remove.
- The real fix is cooperative cancellation: AgentsEngine.run_all() takes an
  optional should_stop() callable, checked between agents; AnalysisWorker
  wires it to QThread.isInterruptionRequested(); shutdown() no longer has a
  terminate() branch at all.

This file constructs real AppController / AgentsEngine / AnalysisWorker
objects (redirected into a temp dir via isolated_state() so nothing touches
the user's real settings.json, reports/ or WhatsApp receiver port) and
exercises shutdown() against actual live QThreads, not mocks.
"""
import os
import sys
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # headless-safe

import shiboken6  # noqa: E402
from PySide6.QtCore import QObject, QThread, Signal, Slot  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tests._isolation import isolated_state  # noqa: E402

from backend.controller import AppController  # noqa: E402
from backend.analysis_worker import AnalysisWorker  # noqa: E402
from core.engine import AgentsEngine, WORKER_AGENTS  # noqa: E402


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _pump_until(predicate, timeout=5.0):
    """Process the main-thread Qt event loop until predicate() is true —
    needed because cross-thread queued signals (worker -> controller) are
    only delivered while something is calling processEvents(); nothing in
    this test harness runs app.exec()."""
    deadline = time.time() + timeout
    while not predicate() and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    return predicate()


class _SlowWorker(QObject):
    """Mimics AnalysisWorker's *shape* (blocks the thread's event loop the
    way a real multi-minute Ollama call would) while polling for
    interruption directly, independent of AgentsEngine/should_stop — used to
    test AppController.shutdown()'s own thread-teardown logic in isolation."""

    finished = Signal()

    def __init__(self):
        super().__init__()
        self.started_running = False
        self.ran_to_completion = False
        self.loop_iterations = 0
        self.returned_via_interruption_check = False

    @Slot()
    def run(self):
        self.started_running = True
        thread = QThread.currentThread()
        for _ in range(100):               # up to 5s if never interrupted
            self.loop_iterations += 1
            if thread.isInterruptionRequested():
                self.returned_via_interruption_check = True
                return
            time.sleep(0.05)
        self.ran_to_completion = True
        self.finished.emit()


class _StubbornWorker(QObject):
    """Deliberately ignores interruption — models a worker that predates
    cooperative cancellation (or a regression that reintroduces one). Used
    to prove shutdown() itself cannot be made to hang even when a thread
    refuses to cooperate, now that the terminate() escape hatch is gone."""

    def __init__(self, hold_seconds):
        super().__init__()
        self.hold_seconds = hold_seconds
        self.started_running = False
        self.ran_to_completion = False

    @Slot()
    def run(self):
        self.started_running = True
        time.sleep(self.hold_seconds)
        self.ran_to_completion = True


class _CountingAI:
    """Stands in for AIEngine: records every agent call actually made and
    signals when the first one starts, so a test can assert should_stop was
    honoured *between* agents — the cooperative path — rather than the
    thread merely finishing for some unrelated reason."""

    def __init__(self, delay=0.0):
        self.calls = []
        self.delay = delay
        self.first_call_started = threading.Event()

    def ask(self, system_prompt, user_text):
        self.calls.append(system_prompt[:20])
        self.first_call_started.set()
        if self.delay:
            time.sleep(self.delay)
        return {"ok": True}


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
            # Prove *how* it stopped, not just that it did: it must have hit
            # the interruption check, not run to completion on its own, and
            # it must not have run through every remaining iteration.
            self.assertTrue(worker.returned_via_interruption_check,
                             "worker did not report exiting via the "
                             "interruption check — its meaning drifted")
            self.assertFalse(worker.ran_to_completion,
                              "shutdown() should interrupt the worker, not "
                              "let it finish on its own")
            self.assertLess(worker.loop_iterations, 100,
                             "worker ran through every iteration instead of "
                             "being interrupted early")

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

    def test_shutdown_honours_should_stop_through_the_real_pipeline(self):
        """End-to-end through the real AgentsEngine.run_all + AnalysisWorker
        (not the hand-rolled _SlowWorker above) — proves should_stop is
        actually wired from QThread.isInterruptionRequested() through
        AnalysisWorker into AgentsEngine.run_all, and that a quit mid-run
        stops it *between* agents rather than letting every agent (and the
        chief) run to completion."""
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)
            c._shutdown_wait_budget_ms = lambda: 4000  # keep the test fast

            ai = _CountingAI(delay=0.15)
            engine = AgentsEngine(ai, log_fn=lambda m: None)
            reports = [{"source": "upload", "dept": "ops", "from": "f",
                        "date": "2026-07-28", "content": "c"}]

            thread = QThread(c)
            worker = AnalysisWorker(engine, reports)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            thread.finished.connect(worker.deleteLater)
            self.addCleanup(lambda: thread.wait(3000))

            c._thread = thread
            c._worker = worker
            thread.start()

            self.assertTrue(ai.first_call_started.wait(2),
                             "the stub AI engine was never called — the "
                             "pipeline did not actually start")

            c.shutdown()

            self.assertTrue(thread.wait(3000),
                             "shutdown() returned but the analysis thread "
                             "never actually finished")
            self.assertLess(len(ai.calls), len(WORKER_AGENTS) + 1,
                             "run_all made every agent call — should_stop "
                             "was never honoured, cooperative cancellation "
                             "did not happen")

    def test_shutdown_does_not_hang_when_the_worker_ignores_interruption(self):
        """The old terminate() fallback is gone. Prove that was safe: a
        worker that never checks isInterruptionRequested() must not be able
        to hang shutdown() itself — it returns within its own wait budget,
        logs the situation, and leaves the thread referenced (not silently
        dropped) rather than deadlocking the process the way terminate()
        could."""
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)
            c._shutdown_wait_budget_ms = lambda: 200  # keep the test fast

            thread = QThread(c)
            worker = _StubbornWorker(hold_seconds=1.0)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            thread.finished.connect(worker.deleteLater)
            # Let the real 1s sleep finish for real before the test process
            # exits — a leaked *actually* running QThread is the exact crash
            # this whole task closes, so nothing here may outlive the test.
            self.addCleanup(lambda: thread.wait(5000))

            c._thread = thread
            c._worker = worker
            thread.start()

            self.assertTrue(_pump_until(lambda: worker.started_running, 2),
                             "worker never started — test setup is broken")

            t0 = time.time()
            c.shutdown()
            elapsed = time.time() - t0

            self.assertLess(elapsed, 1.0,
                             "shutdown() blocked far longer than its own "
                             "wait budget — an uncooperative worker must "
                             "not be able to hang shutdown()")
            self.assertIsNotNone(c._thread,
                                  "a thread that never actually stopped "
                                  "must not be silently forgotten")
            self.assertIsNotNone(c._worker)
            self.assertFalse(worker.ran_to_completion,
                              "shutdown() returned before the stubborn "
                              "worker's real sleep finished, as expected")

    def test_run_analysis_frees_the_worker_once_the_thread_finishes(self):
        """Regression for the QObject leak found in review: runAnalysis()
        must connect thread.finished -> worker.deleteLater(), or the
        AnalysisWorker — and the AgentsEngine/report-text snapshot it pins —
        survives every completed analysis run forever."""
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)

            c._ai = _CountingAI(delay=0.0)
            c._reports.add({"source": "upload", "dept": "ops", "from": "f",
                             "date": "2026-07-28", "content": "c"})

            done = {"flag": False}
            c.analysisDone.connect(lambda: done.__setitem__("flag", True))
            c.analysisFailed.connect(lambda *_: done.__setitem__("flag", True))

            c.runAnalysis()
            worker_ref = c._worker
            self.assertIsNotNone(worker_ref)

            self.assertTrue(_pump_until(lambda: done["flag"], 10),
                             "analysis never completed")

            self.assertFalse(shiboken6.isValid(worker_ref),
                              "AnalysisWorker was never deleted — "
                              "thread.finished -> worker.deleteLater() is "
                              "missing or broken")


if __name__ == "__main__":
    unittest.main()
