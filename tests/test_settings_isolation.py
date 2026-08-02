"""Regression coverage for task 16: saving settings while an analysis is
running must not corrupt it.

Two invariants, pinned independently so either can regress on its own and
still be caught:

1. runAnalysis() must build the live engine from a *copy* of settings
   (AIEngine(dict(self._settings))), never self._ai / self._settings
   directly — or a settings save that lands mid-run (any caller: the save
   button, "حفظ كملف", the test/fetch buttons that save-before-testing, or
   switchEngineProfile()) can switch the AI provider partway through a run,
   splitting one analysis across two backends.
2. _rebuild_hub() must hand the outgoing hub's pending buffer to the new
   hub — or a settings save silently discards WhatsApp reports that had
   already arrived but had not yet been collect_all()'d.

See .superpowers/sdd/2026-07-28-launch-readiness/task-16-report.md for the
full history (including the round-1 review that added
AppController.saveSettings()'s own busy-gate and reordered _rebuild_hub to
stop the old hub before draining it).
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

    def test_a_mid_run_save_cannot_reach_the_running_engines_settings(self):
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

            c.saveSettings({"ai_backend": "claude"})

            self.assertEqual(
                engine.ai.settings["ai_backend"], original_backend,
                "a settings save while the analysis was running mutated "
                "the in-flight engine's provider")
            self.assertIsNot(engine.ai.settings, c._settings)


class RebuildHubBufferHandoffTests(unittest.TestCase):
    def setUp(self):
        _app()

    def test_save_settings_carries_the_pending_buffer_to_the_new_hub(self):
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)

            report = {"source": "whatsapp", "dept": "ops", "from": "+2001234",
                      "date": "2026-07-28", "content": "تقرير من واتساب"}
            old_hub = c._hub
            old_hub.extend_buffer([report])

            c.saveSettings({})

            self.assertIsNot(c._hub, old_hub,
                              "saveSettings() must rebuild the hub — test "
                              "setup assumption broken")
            self.assertEqual(
                c._hub.take_buffer(), [report],
                "_rebuild_hub() discarded a WhatsApp report that had "
                "already arrived but had not yet been collect_all()'d")


if __name__ == "__main__":
    unittest.main()
