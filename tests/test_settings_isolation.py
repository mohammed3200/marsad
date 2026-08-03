"""Regression coverage for task 16: saving settings while an analysis is
running must not corrupt it.

Two invariants, pinned independently so either can regress on its own and
still be caught:

1. runAnalysis() must build the live engine from a *copy* of settings
   (AIEngine(dict(self._settings))), never self._ai / self._settings
   directly, and nothing that later mutates self._settings in place (a
   direct assignment, not just a saveSettings() call — saveSettings() is
   now gated on self._busy and never mutates in place anyway, so calling it
   alone doesn't exercise this) may reach the running engine's snapshot.
2. _rebuild_hub() must hand the outgoing hub's pending buffer to the new
   hub, and must do so in stop-then-drain order specifically — draining
   first can lose a report a WhatsAppReceiver request handler thread
   appends *while* stop_all() is shutting it down (ThreadingHTTPServer runs
   daemon_threads=True, so stop() does not join in-flight handler threads).

See .superpowers/sdd/2026-07-28-launch-readiness/task-16-report.md for the
full history — including the round-1 review (saveSettings()'s own busy-gate,
the stop-then-drain reorder in _rebuild_hub) and the round-2 review that
corrected both tests below: round-1's buffer test seeded the buffer before
the save and so passed against either drain ordering (it never actually
pinned the reorder), and round-1's mutation leg called saveSettings() —
which the same commit had just gated on self._busy, and which never mutates
self._settings in place regardless — so only the identity assertion taken
*before* that call was ever load-bearing.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # headless-safe

from PySide6.QtCore import QObject, Signal, Slot  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tests._isolation import isolated_state  # noqa: E402

import backend.controller as controller_mod  # noqa: E402
from backend.controller import AppController  # noqa: E402


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


class _CapturingWorker(QObject):
    """Stands in for AnalysisWorker — same signal shape, but run() never
    does anything, so the thread it's moved to just idles instead of making
    real network calls. Exists purely so runAnalysis() has something to
    construct and hand the engine to; the test inspects that engine, it
    never lets it actually run."""
    agentState = Signal(str, str)
    progress   = Signal(int)
    log        = Signal(str)
    finished   = Signal("QVariant")
    failed     = Signal(str)

    def __init__(self, engine, reports):
        super().__init__()
        self.engine = engine

    @Slot()
    def run(self):
        pass


class RunAnalysisSettingsSnapshotTests(unittest.TestCase):
    def setUp(self):
        _app()

    def test_a_mid_run_mutation_of_settings_cannot_reach_the_running_engine(self):
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)
            c._reports.add({"source": "upload", "dept": "ops", "from": "f",
                             "date": "2026-07-28", "content": "c"})

            original_worker_cls = controller_mod.AnalysisWorker
            controller_mod.AnalysisWorker = _CapturingWorker
            self.addCleanup(setattr, controller_mod, "AnalysisWorker",
                             original_worker_cls)

            c.runAnalysis()
            self.assertTrue(c._busy,
                             "runAnalysis() did not go busy — test setup is broken")

            def _stop_thread():
                if c._thread:
                    c._thread.quit()
                    c._thread.wait(2000)
            self.addCleanup(_stop_thread)

            engine = c._worker.engine
            self.assertIsNot(
                engine.ai.settings, c._settings,
                "runAnalysis() must snapshot settings into a new dict "
                "(AIEngine(dict(self._settings))), not hand the engine "
                "self._ai / the live self._settings object")
            original_backend = engine.ai.settings["ai_backend"]
            self.assertNotEqual(original_backend, "claude",
                                 "test fixture assumption broken — pick a "
                                 "default that differs from the probe value")

            # Model the hazard directly rather than through a specific
            # caller (a saveSettings() call is inert here twice over: this
            # commit gates it on self._busy, and it never mutates
            # self._settings in place regardless of that gate). Before this
            # task's round-2 fix, switchEngineProfile() did exactly this —
            # assigned into self._settings in place — ahead of a
            # saveSettings({}) call; this reproduces that shape directly so
            # the test still means something even though that call site no
            # longer does it.
            c._settings["ai_backend"] = "claude"

            self.assertEqual(
                engine.ai.settings["ai_backend"], original_backend,
                "a settings mutation while the analysis was running "
                "reached the in-flight engine's provider")
            self.assertIsNot(engine.ai.settings, c._settings)


class RebuildHubBufferHandoffTests(unittest.TestCase):
    def setUp(self):
        _app()

    def test_a_report_that_arrives_while_the_old_hub_is_stopping_survives(self):
        """Discriminates the drain order, unlike a buffer seeded before the
        save (which drains identically either way). _LateAppendHub models
        WhatsAppReceiver's real behaviour under ThreadingHTTPServer with
        daemon_threads=True: a request accepted before stop_all() runs can
        still call the append callback *during* shutdown, i.e. its report
        lands in the buffer only once stop_all() is already underway — take
        this at any earlier point and it's missed. Draining before stopping
        (the round-1 order, per the brief) fails this; stopping before
        draining (the round-2 fix) passes it."""
        class _LateAppendHub:
            def __init__(self, late):
                self._buf, self._late = [], late

            def take_buffer(self):
                b, self._buf = list(self._buf), []
                return b

            def extend_buffer(self, reports):
                self._buf.extend(reports)

            def stop_all(self):
                # Models a request handler thread that's still in flight
                # when stop_all() is called — it appends *during* shutdown,
                # not before it.
                self._buf.append(self._late)

            def set_logger(self, fn):
                pass

            def set_event_handler(self, fn):
                pass

        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)

            late_report = {"source": "whatsapp", "dept": "ops",
                           "from": "+2001234", "date": "2026-07-28",
                           "content": "تقرير متأخر أثناء الإيقاف"}
            c._hub = _LateAppendHub(late_report)

            c.saveSettings({})

            self.assertNotIsInstance(
                c._hub, _LateAppendHub,
                "saveSettings() must rebuild the hub — test setup "
                "assumption broken")
            self.assertEqual(
                c._hub.take_buffer(), [late_report],
                "a report that arrived while the old hub was stopping was "
                "lost — _rebuild_hub() must stop_all() the old hub before "
                "take_buffer()'ing it, not after")


if __name__ == "__main__":
    unittest.main()
