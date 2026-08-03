import unittest

from core.engine import AIEngine

parse = AIEngine._parse_json


class ParseJsonTests(unittest.TestCase):
    def test_plain_object(self):
        self.assertEqual(parse('{"a": 1}'), {"a": 1})

    def test_fenced_object(self):
        self.assertEqual(parse('```json\n{"a": 1}\n```'), {"a": 1})

    def test_object_surrounded_by_prose(self):
        self.assertEqual(parse('قبل {"a": 1} بعد'), {"a": 1})

    def test_prose_with_braces_after_the_object(self):
        out = parse('{"completion_pct": 80}\n\nملاحظة: راجع {الحقل} لاحقاً')
        self.assertEqual(out, {"completion_pct": 80})

    def test_two_objects_returns_the_first(self):
        self.assertEqual(parse('{"a": 1}\n{"b": 2}'), {"a": 1})

    def test_braces_inside_strings_do_not_confuse_the_scan(self):
        self.assertEqual(parse('{"note": "استخدم } هنا"}'), {"note": "استخدم } هنا"})

    def test_top_level_array_is_an_error_not_a_list(self):
        out = parse('[{"title": "تأخر"}]')
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("error"), "json_parse")

    def test_null_is_an_error_dict(self):
        out = parse("null")
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("error"), "json_parse")

    def test_scalars_are_error_dicts(self):
        for raw in ("5", '"نص"', "true"):
            with self.subTest(raw=raw):
                out = parse(raw)
                self.assertIsInstance(out, dict)
                self.assertEqual(out.get("error"), "json_parse")

    def test_garbage_is_an_error_dict(self):
        out = parse("لا يوجد JSON هنا")
        self.assertEqual(out.get("error"), "json_parse")
        self.assertIn("raw", out)

    def test_empty_string(self):
        self.assertEqual(parse("").get("error"), "json_parse")


class RunAllSurvivesBadRepliesTests(unittest.TestCase):
    def _run(self, bad_reply):
        from core.engine import AgentsEngine, WORKER_AGENTS
        from tests._isolation import isolated_state

        class Stub:
            def ask(self, system, user):
                if "التنسيق المركزي" in system:
                    return {"overall_health": "جيد", "executive_summary": "م",
                            "kpis": [], "top_actions": [], "dept_scores": [],
                            "achievements": []}
                if "المخاطر" in system:
                    return bad_reply
                return {"ok": 1}

        reports = [{"source": "upload", "dept": "ops", "from": "f",
                    "date": "2026-07-28", "content": "c"}]
        with isolated_state():
            return AgentsEngine(Stub(), log_fn=lambda m: None).run_all(reports)

    def test_none_reply_does_not_destroy_the_run(self):
        results = self._run(None)
        self.assertIn("chief", results)
        self.assertIn("error", results["risk"])

    def test_list_reply_does_not_reach_the_exporters(self):
        results = self._run([{"title": "تأخر"}])
        self.assertIsInstance(results["risk"], dict)


if __name__ == "__main__":
    unittest.main()
