"""The run must not report success when it failed.

Measured on the owner's machine: a CPU-only ollama at ~0.33 tok/s against
ai_timeout=180 makes every one of the 11 agents time out. The dashboard
degraded honestly («غير محدد» plus an Arabic explanation), but four separate
surfaces still said the analysis had succeeded — the log's last line, the
progress bar, the toast, and the auto-navigation to the empty dashboard.

These tests pin the log verdict and the controller's branch. Both fail against
the pre-fix code: `run_all` logged "✓ اكتمل التحليل الشامل" unconditionally,
and `_on_analysis_done` always emitted `analysisDone` plus the success toast.
"""
import unittest

from tests._isolation import isolated_state

from core.engine import AgentsEngine, WORKER_AGENTS


class _StubAI:
    """Stands in for AIEngine. `failing` names the agents that error."""

    def __init__(self, failing):
        self.failing = failing
        self.calls = 0

    def ask(self, system, prompt=""):
        self.calls += 1
        # The chief call is the only one routed through ask() directly by
        # run_all; workers go through run_agent, which calls ask() too. We
        # cannot tell them apart here, so `run_agent` is stubbed instead.
        return {"error": "انتهت مهلة الاتصال — الخادم لا يستجيب"}


class _RecordingEngine(AgentsEngine):
    """AgentsEngine with run_agent stubbed so no network is touched."""

    def __init__(self, failing):
        super().__init__(_StubAI(failing))
        self.failing = failing
        self.lines = []
        self.log = self.lines.append

    def run_agent(self, agent_id, text):
        if agent_id in self.failing:
            return {"error": "انتهت مهلة الاتصال — الخادم لا يستجيب"}
        return {"summary": "تم"}


class RunVerdictTests(unittest.TestCase):
    def _run(self, failing):
        with isolated_state():
            eng = _RecordingEngine(failing)
            results = eng.run_all([{"content": "تقرير", "source": "test"}])
        return eng.lines, results

    def test_total_failure_is_not_reported_as_success(self):
        lines, _ = self._run(set(WORKER_AGENTS))
        self.assertNotIn("✓ اكتمل التحليل الشامل", lines)
        self.assertIn("✗ تعذّر إكمال التحليل — لم ينجح أي وكيل", lines)

    def test_partial_failure_says_how_many_succeeded(self):
        failing = set(WORKER_AGENTS[:3])
        lines, _ = self._run(failing)
        expected = len(WORKER_AGENTS) - len(failing)
        # The chief also fails (the stub AI always errors), so this is the
        # partial branch, not the clean one.
        self.assertNotIn("✓ اكتمل التحليل الشامل", lines)
        self.assertIn(
            f"✓ اكتمل التحليل الشامل — نجح {expected} من {len(WORKER_AGENTS)}",
            lines,
        )

    def test_the_results_contract_is_unchanged_by_the_verdict(self):
        """The verdict must not alter what run_all returns — every layer
        downstream reads this dict."""
        _, results = self._run(set(WORKER_AGENTS))
        self.assertEqual(set(results) - {"chief"}, set(WORKER_AGENTS))
        for key in ("overall_health", "executive_summary", "kpis",
                    "top_actions", "dept_scores", "achievements"):
            self.assertIn(key, results["chief"])


class ControllerVerdictTests(unittest.TestCase):
    """The controller must not toast success, and must not navigate to an
    empty dashboard, when nothing succeeded."""

    def _emissions(self, results):
        with isolated_state():
            from backend.controller import AppController

            c = AppController.__new__(AppController)   # no Qt event loop needed
            seen = {"done": 0, "failed": [], "notify": []}

            class _Sig:
                def __init__(self, sink):
                    self.sink = sink

                def emit(self, *a):
                    self.sink(*a)

            c._results = {}
            c._dash = {}
            c._date = ""
            c._teardown_thread = lambda: None
            c._set_busy = lambda v: None
            c.dashModelChanged = _Sig(lambda *a: None)
            c.reportDateChanged = _Sig(lambda *a: None)
            c.analysisDone = _Sig(lambda *a: seen.__setitem__("done", seen["done"] + 1))
            c.analysisFailed = _Sig(lambda m: seen["failed"].append(m))
            c.notify = _Sig(lambda m: seen["notify"].append(m))
            AppController._on_analysis_done(c, results)
            return seen

    def test_all_workers_errored_emits_failed_not_done(self):
        results = {a: {"error": "انتهت المهلة"} for a in WORKER_AGENTS}
        results["chief"] = {"overall_health": "غير محدد"}
        seen = self._emissions(results)
        self.assertEqual(seen["done"], 0)
        self.assertEqual(len(seen["failed"]), 1)
        self.assertNotIn("اكتمل التحليل — عُرضت النتائج في لوحة التحكم",
                         seen["notify"])

    def test_one_success_still_counts_as_done(self):
        results = {a: {"error": "انتهت المهلة"} for a in WORKER_AGENTS}
        results[WORKER_AGENTS[0]] = {"summary": "تم"}
        results["chief"] = {"overall_health": "متوسط"}
        seen = self._emissions(results)
        self.assertEqual(seen["done"], 1)
        self.assertEqual(seen["failed"], [])

    def test_cancelled_run_with_no_workers_is_not_called_a_failure(self):
        seen = self._emissions({})
        self.assertEqual(seen["done"], 1)
        self.assertEqual(seen["failed"], [])


if __name__ == "__main__":
    unittest.main()
