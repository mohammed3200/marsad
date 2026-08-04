import io
import json
import unittest
import urllib.error
import urllib.request

from core.engine import AIEngine

SETTINGS = dict(ai_timeout=5, ollama_url="http://127.0.0.1:9", ollama_model="m",
                claude_api_key="ck", claude_model="cm",
                openai_api_key="ok", openai_base_url="https://api.openai.com/v1",
                openai_model="om", gemini_api_key="gk", gemini_model="gm",
                azure_api_key="ak", azure_endpoint="https://x.openai.azure.com",
                azure_deployment="dep", azure_api_version="2024-06-01")

GOOD = '```json\n{"status":"ok"}\n```'


class _Resp:
    def __init__(self, body): self._b = json.dumps(body).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


class BackendRequestShapeTests(unittest.TestCase):
    def setUp(self):
        self._real = urllib.request.urlopen
        self.calls = []

    def tearDown(self):
        urllib.request.urlopen = self._real

    def _canned(self, body):
        def fake(req, timeout=None):
            self.calls.append(req)
            return _Resp(body)
        urllib.request.urlopen = fake

    def test_each_backend_builds_the_right_request(self):
        cases = {
            "ollama": ({"response": GOOD}, "http://127.0.0.1:9/api/generate"),
            "claude": ({"content": [{"text": GOOD}]}, "https://api.anthropic.com/v1/messages"),
            "openai": ({"choices": [{"message": {"content": GOOD}}]},
                       "https://api.openai.com/v1/chat/completions"),
            "azure":  ({"choices": [{"message": {"content": GOOD}}]},
                       "https://x.openai.azure.com/openai/deployments/dep/"
                       "chat/completions?api-version=2024-06-01"),
        }
        for backend, (body, url) in cases.items():
            with self.subTest(backend=backend):
                self.calls.clear()
                self._canned(body)
                out = AIEngine({**SETTINGS, "ai_backend": backend}).ask("sys", "user")
                self.assertEqual(out, {"status": "ok"})
                self.assertEqual(self.calls[0].full_url, url)

    def test_ask_never_raises(self):
        failures = [urllib.error.URLError(TimeoutError()), TimeoutError(),
                    urllib.error.HTTPError("u", 500, "err", {}, io.BytesIO(b"x")),
                    ConnectionResetError(), ValueError("junk")]
        for backend in ("ollama", "claude", "openai", "azure", "gemini"):
            for exc in failures:
                with self.subTest(backend=backend, exc=type(exc).__name__):
                    def boom(req, timeout=None): raise exc
                    urllib.request.urlopen = boom
                    out = AIEngine({**SETTINGS, "ai_backend": backend}).ask("s", "u")
                    self.assertIsInstance(out, dict)
                    self.assertIn("error", out)

    def test_missing_key_short_circuits_without_a_request(self):
        for backend in ("claude", "openai", "gemini", "azure"):
            with self.subTest(backend=backend):
                self.calls.clear()
                self._canned({"choices": []})
                out = AIEngine({"ai_backend": backend, "ai_timeout": 5}).ask("s", "u")
                self.assertIn("error", out)
                self.assertEqual(self.calls, [])


class OpenAiCompatRetryTests(unittest.TestCase):
    """LM Studio and several OpenRouter models reject response_format with a 400.
    The documented fallback is to retry without it."""

    def setUp(self):
        self._real = urllib.request.urlopen
        self.payloads = []

    def tearDown(self):
        urllib.request.urlopen = self._real

    def test_http_400_triggers_a_retry_without_response_format(self):
        state = {"n": 0}

        def fake(req, timeout=None):
            self.payloads.append(json.loads(req.data))
            state["n"] += 1
            if state["n"] == 1:
                raise urllib.error.HTTPError(
                    req.full_url, 400, "Bad Request", {},
                    io.BytesIO(b'{"error":"response_format not supported"}'))
            return _Resp({"choices": [{"message": {"content": GOOD}}]})

        urllib.request.urlopen = fake
        out = AIEngine({**SETTINGS, "ai_backend": "openai"}).ask("sys", "user")
        self.assertEqual(out, {"status": "ok"})
        self.assertEqual(len(self.payloads), 2, "no retry was attempted")
        self.assertIn("response_format", self.payloads[0])
        self.assertNotIn("response_format", self.payloads[1])


class ClaudeHttpErrorClassificationTests(unittest.TestCase):
    """Round-2 launch-readiness finding: _ask_claude had no urllib.error.HTTPError
    branch at all (unlike _ask_ollama/_http_json/_http_get_json), so a real 401
    invalid-key / 429 rate-limit / 5xx response from Anthropic returned
    {"error": str(e)} verbatim — raw English JSON reaching the Arabic-only UI
    through test_connection() -> testConnection()/_run_connection_test() -> notify,
    and through run_all()'s per-agent log line. Proves the fix classifies it, and
    that the classified message never echoes the outgoing x-api-key header."""

    def setUp(self):
        self._real = urllib.request.urlopen

    def tearDown(self):
        urllib.request.urlopen = self._real

    def _raise_401(self, req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", {},
            io.BytesIO(b'{"type":"error","error":{"type":"authentication_error",'
                      b'"message":"invalid x-api-key"}}'))

    def test_claude_401_produces_arabic_not_raw_english(self):
        urllib.request.urlopen = self._raise_401
        settings = {**SETTINGS, "ai_backend": "claude"}
        out = AIEngine(settings).ask("sys", "user")
        self.assertIn("error", out)
        self.assertEqual(out["error"],
                         "مفتاح API غير صالح أو بلا صلاحية — تحقق من المفتاح")
        # the raw response body must not survive into the user-facing message
        self.assertNotIn("invalid x-api-key", out["error"])
        self.assertNotIn("authentication_error", out["error"])
        # and the classified message must never echo the request's own
        # x-api-key header value (the secret used to authenticate)
        self.assertNotIn(settings["claude_api_key"], out["error"])

    def test_claude_test_connection_surfaces_the_same_arabic_message(self):
        """test_connection() is exactly what testConnection()/_run_connection_test()
        in both backend/controller.py and api/services.py show via notify."""
        urllib.request.urlopen = self._raise_401
        ok, msg = AIEngine({**SETTINGS, "ai_backend": "claude"}).test_connection()
        self.assertFalse(ok)
        self.assertEqual(msg, "مفتاح API غير صالح أو بلا صلاحية — تحقق من المفتاح")


class TwoStageConnectionTests(unittest.TestCase):
    """One round-trip could not tell the user which thing was broken.

    Measured on the owner's machine: a CPU-only ollama at ~0.33 tok/s times
    out exactly like an unreachable server does, and the one message that
    came back — «انتهت مهلة الاتصال» — sent them to check a network that was
    fine. Stage 1 reuses list_models(), which already bounds itself at 10-15s
    independently of ai_timeout."""

    def setUp(self):
        self._real = urllib.request.urlopen

    def tearDown(self):
        urllib.request.urlopen = self._real

    def test_unreachable_server_says_so_and_never_reaches_generation(self):
        asked = []

        def refuse(req, timeout=None):
            asked.append(req.full_url)
            raise urllib.error.URLError("Connection refused")

        urllib.request.urlopen = refuse
        ok, msg = AIEngine({**SETTINGS, "ai_backend": "ollama"}).test_connection()
        self.assertFalse(ok)
        self.assertIn("تعذّر الوصول إلى الخادم", msg)
        # Stage 1 short-circuits: only /api/tags was tried, never /api/generate.
        self.assertTrue(all("/api/tags" in u for u in asked), asked)

    def test_reachable_server_but_slow_model_blames_the_model(self):
        def dispatch(req, timeout=None):
            if "/api/tags" in req.full_url:
                return _Resp({"models": [{"name": "m"}]})
            raise TimeoutError()

        urllib.request.urlopen = dispatch
        ok, msg = AIEngine({**SETTINGS, "ai_backend": "ollama"}).test_connection()
        self.assertFalse(ok)
        self.assertIn("الخادم يستجيب", msg)
        self.assertNotIn("تعذّر الوصول إلى الخادم", msg)
        # names the setting the user can actually change
        self.assertIn("مهلة الاستجابة", msg)

    def test_both_stages_passing_still_succeeds(self):
        def dispatch(req, timeout=None):
            if "/api/tags" in req.full_url:
                return _Resp({"models": [{"name": "m"}]})
            return _Resp({"response": '{"status":"ok","message":"الاتصال ناجح"}'})

        urllib.request.urlopen = dispatch
        ok, msg = AIEngine({**SETTINGS, "ai_backend": "ollama"}).test_connection()
        self.assertTrue(ok)
        self.assertEqual(msg, "الاتصال ناجح")

    def test_claude_has_no_cheap_probe_so_its_message_is_unchanged(self):
        """list_models() for claude is a hardcoded list — it touches no
        network, so it cannot answer 'is the server up?'. Prefixing its
        failures with a reachability verdict would be a lie."""
        def raise_401(req, timeout=None):
            raise urllib.error.HTTPError(
                req.full_url, 401, "Unauthorized", {},
                io.BytesIO(b'{"error":{"message":"invalid x-api-key"}}'))

        urllib.request.urlopen = raise_401
        ok, msg = AIEngine({**SETTINGS, "ai_backend": "claude"}).test_connection()
        self.assertFalse(ok)
        self.assertEqual(msg, "مفتاح API غير صالح أو بلا صلاحية — تحقق من المفتاح")

    def test_the_return_shape_is_unchanged(self):
        """Both callers — AppController._run_connection_test and
        api/services.py — unpack (ok, msg)."""
        urllib.request.urlopen = lambda req, timeout=None: _Resp(
            {"models": [{"name": "m"}]}) if "/api/tags" in req.full_url else _Resp(
            {"response": '{"status":"ok"}'})
        out = AIEngine({**SETTINGS, "ai_backend": "ollama"}).test_connection()
        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 2)
        self.assertIsInstance(out[0], bool)
        self.assertIsInstance(out[1], str)


if __name__ == "__main__":
    unittest.main()
