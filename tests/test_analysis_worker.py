"""Fix round 3 (task 22): backend/analysis_worker.py leaked raw English
exception text into the desktop toast on any AgentsEngine.run_all() failure.

AgentsEngine.run_all() is not exception-safe — _format_reports()
(core/engine.py) calls `r.get('source','').upper()`, which raises
AttributeError when a report's `source` key is present but None (the
`.get(key, default)` default only applies when the key is *missing*, not
when it's explicitly None). AnalysisWorker.run() caught that with a bare
`except Exception as e: self.failed.emit(str(e))`, so
"'NoneType' object has no attribute 'upper'" flowed straight through
AppController._on_analysis_failed() into `notify` as
"فشل التحليل: 'NoneType' object has no attribute 'upper'" — raw Python,
not Arabic, on screen. This mirrors the sibling bug already fixed in
api/services.py's _run_analysis() (which classifies via friendly_error()
before emitting).

This test drives the real AppController + QThread + AnalysisWorker +
AgentsEngine pipeline (no mocks on the failure path itself) end to end,
the same way tests/test_shutdown.py does, to prove the classification
actually reaches both the `analysisFailed` signal and the `notify` toast.
"""
import os
import sys
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # headless-safe

from PySide6.QtWidgets import QApplication  # noqa: E402

from tests._isolation import isolated_state  # noqa: E402

from backend.controller import AppController  # noqa: E402
from core.errors import friendly_error  # noqa: E402

# The exact message core/engine.py's _format_reports() raises for a report
# whose `source` key is present but None: `r.get('source', '').upper()` only
# falls back to '' when the key is *missing* — an explicit None survives
# .get() and .upper() then blows up. Hardcoded here (rather than trying to
# provoke-and-capture it) because the fallback branch of friendly_error()
# embeds a length-capped fragment of whatever text it is given, so the
# expected classified output must be computed from the same known input the
# malformed report is designed to trigger.
_RAW_ATTRIBUTE_ERROR = "'NoneType' object has no attribute 'upper'"


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


def _pump_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while not predicate() and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    return predicate()


class AnalysisWorkerErrorClassificationTests(unittest.TestCase):
    def setUp(self):
        _app()

    def test_malformed_report_produces_arabic_not_a_python_traceback(self):
        """A report with source=None (key present, value None — guess_dept()
        and connectors.py never produce this, but nothing stops a future
        caller of AppController.addReport or a malformed upload/ERP report
        from doing so) must fail the run with a short Arabic message, not
        the raw AttributeError text."""
        with isolated_state():
            c = AppController()
            self.addCleanup(c.deleteLater)

            c._reports.add({
                "source": None, "dept": "ops", "from": "x",
                "date": "2026-08-01", "content": "hi",
            })

            failed_msgs = []
            notify_msgs = []
            c.analysisFailed.connect(lambda msg: failed_msgs.append(msg))
            c.notify.connect(lambda msg: notify_msgs.append(msg))

            c.runAnalysis()

            self.assertTrue(_pump_until(lambda: failed_msgs, 10),
                             "analysisFailed never fired — the malformed "
                             "report did not reproduce the crash this test "
                             "targets")

            # friendly_error()'s catch-all fallback for an unrecognized error
            # string is not to erase it — it prepends a short Arabic label
            # and caps the length (core/errors.py:70-71). That fallback IS
            # the "classified" outcome for a Python-internal message like
            # this one (there is no dedicated _RULES entry for it), so the
            # regression to guard is specifically "AnalysisWorker.run() ran
            # the exception through friendly_error() at all" — provable by
            # checking the emitted message matches applying the classifier
            # to the known raw text, not the bare unclassified string.
            expected = friendly_error(_RAW_ATTRIBUTE_ERROR)
            self.assertNotEqual(
                expected, _RAW_ATTRIBUTE_ERROR,
                "test sanity: friendly_error() must actually transform this "
                "input, or this test can't distinguish fixed from broken")

            failed_msg = failed_msgs[0]
            self.assertEqual(
                failed_msg, expected,
                "analysisFailed did not carry the friendly_error()-"
                "classified message — either the raw exception leaked "
                "unwrapped, or classification produced something other "
                "than what api/services.py's sibling path would")
            self.assertNotEqual(
                failed_msg, _RAW_ATTRIBUTE_ERROR,
                "analysisFailed carried the bare, unclassified Python "
                "exception text — AnalysisWorker.run() is not calling "
                "friendly_error()")

            notify_msg = next(
                (m for m in notify_msgs if m.startswith("فشل التحليل")), None)
            self.assertIsNotNone(
                notify_msg, "no 'فشل التحليل' notify was emitted")
            self.assertEqual(notify_msg, f"فشل التحليل: {expected}")
            # Arabic content actually made it into the message (not just an
            # empty/opaque fallback).
            self.assertTrue(
                any("؀" <= ch <= "ۿ" for ch in notify_msg),
                f"notify message has no Arabic in it: {notify_msg!r}")

            self.assertFalse(c.busy,
                              "busy must be cleared even on a failed run")


if __name__ == "__main__":
    unittest.main()
