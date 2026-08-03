# marsad Launch-Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every blocker and major defect found in the 2026-07-28 release audit so مرصد can be shipped to users outside the developer's machine.

**Architecture:** Work proceeds in five phases against the existing layering (`core/` is UI-agnostic, `backend/` is the Qt bridge, `api/` is the Qt-free FastAPI mirror, `qml/` is the UI). A new `tests/` package built on stdlib `unittest` — no new dependency, matching the existing `tools/test_api.py` style — is created first so every later task has a real test cycle. Every test redirects module-level path globals to a temp directory, so the suite can never touch the user's real `settings.json`, `reports/` or `data/`.

**Tech Stack:** Python 3.10+, PySide6 (Qt Quick/QML), FastAPI + uvicorn, reportlab, openpyxl, python-docx, PyPDF2, arabic-reshaper, python-bidi, qrcode. Tests: stdlib `unittest`.

## Global Constraints

- **Arabic strings are contracts.** Preserve every existing Arabic literal verbatim unless a task explicitly changes it. Status literals `جيد` / `متوسط` / `مكتمل` / `متأخر` / `عالية` / `متوسطة` / `منخفضة` / `آمن` / `خطر` / `تحذير` drive colour and branching everywhere.
- **`core/` and `connectors.py` must not import Qt.** Ever.
- **Network and parsing paths must never raise** — degrade to `{"error": …}`.
- **No blocking I/O on the Qt GUI thread.** Long work runs on a `QThread` or a daemon thread; results cross back via signals.
- **Write only under `DATA_DIR`** (`core/paths.py`). Never next to the executable.
- **The `results` dict shape is frozen.** Keys: `chief`, `ops`, `quality`, `safety`, `civil`, `cost`, `contract`, `procure`, `supply`, `risk`, `schedule`. Changing an agent's output schema means updating `core/exporters.py`, `connectors.build_report_html`, and the QML that reads it in the same task.
- **Never commit secrets.** `settings.json`, `data/contacts.json`, `reports/`, `logs/`, `uploads/` stay gitignored.
- **Do not create or modify any GitHub release or tag.** The user has explicitly withheld that permission. Tagging is a separate decision after this plan completes.
- Run the suite with: `python3 -m unittest discover -s tests -v`
- Commit after every task. Branch: `fix/launch-readiness` off the current `feat/multi-provider-arabic-redesign`.

## Release scope: desktop only

**The web API (`api/`, `run_api.py`, `marsad_api.spec`) does not ship in this release.** The code stays in the tree, but the desktop app is the product. This changes three tasks:

- **Task 5** is reduced: redact secrets from `GET /api/settings`, keep the blank-secret-means-unchanged rule on `PUT`, and make the server refuse to start unless `MARSAD_API_ENABLE=1` is set. **No token middleware** — a server that will not start needs no authentication. Read Task 5's steps with that substitution.
- **Task 14** (API guard-flag locking) and **Task 17** (WebSocket single-writer + lifespan) are **deferred**. Skip them; they are recorded as known limitations in `docs/RELEASE_CHECKLIST.md`.
- **Task 24** builds `marsad.spec` only. Task 4's one-line `web/dist` removal from `marsad_api.spec` still happens so the file is not left broken.

Because the API never starts by default, `tools/test_api.py` and every API test must set `MARSAD_API_ENABLE=1` in the environment before importing `api.app`.

## Audit correction incorporated into this plan

The audit listed missing font glyphs (`←` `·` `…` `—`) as a blocker. **That was over-called and is corrected here.** Re-testing with an offscreen Qt using only the bundled fonts showed Qt performs per-glyph fallback, so those characters render — they are not tofu boxes. Even ASCII `-` and `:` are absent from Noto Kufi Arabic and render fine for the same reason. The real defect is *typographic inconsistency* (punctuation drawn from a non-matching family), which is handled as a minor item in **Task 20**, not as a blocker.

---

## File Structure

**Created**

| File | Responsibility |
|---|---|
| `tests/__init__.py` | Marks the package. |
| `tests/_isolation.py` | `isolated_state()` context manager — redirects `settings_bridge.SETTINGS_F`, `core.engine.REPORTS`, `core.contacts` paths to a temp dir and restores them. Every test uses it. |
| `tests/test_settings_store.py` | Settings persistence: atomic write, 0600 mode, selective-key save. |
| `tests/test_engine_parsing.py` | `_parse_json` contract, including non-object replies. |
| `tests/test_engine_backends.py` | Per-provider request shape + never-raises, monkeypatched `urlopen`. |
| `tests/test_connectors_mail.py` | TLS context assertions for IMAP/SMTP. |
| `tests/test_connectors_ingest.py` | `read_file_to_report`, `guess_dept`, `is_internal_file`. |
| `tests/test_report_html.py` | HTML escaping of LLM output. |
| `tests/test_exporters.py` | Type-hostile results dicts must still export. |
| `tests/test_status_tiers.py` | Shared status→tier mapping. |
| `tests/test_api_auth.py` | Token, Host and Origin enforcement; secret redaction. |
| `tests/test_api_uploads.py` | Size cap, count cap, hostile filenames. |
| `core/status.py` | Single source of truth mapping Arabic status literals → `good`/`warn`/`bad`/`neutral`. Consumed by `core/exporters.py`, `connectors.py`, `backend/theme.py`. |
| `docs/superpowers/plans/2026-07-28-launch-readiness.md` | This plan. |

**Modified**

| File | Change |
|---|---|
| `backend/settings_bridge.py` | Atomic + 0600 write; selective-key save. |
| `connectors.py` | TLS contexts; HTML escaping; read caps; dept matching; receiver hardening; token persistence; hub-rebuild buffer handover. |
| `core/engine.py` | `_parse_json` dict guard + balanced-brace scan; HTTP status in error dicts; retry fix; `_save` degrades. |
| `core/exporters.py` | Numeric coercion; shared status tiers; escape-after-bidi; dead columns removed; the five unsurfaced agents added. |
| `api/app.py` | Auth middleware; secret redaction; upload limits; WS writer queue; lifespan hook. |
| `api/services.py` | Lock-guarded flags; `friendly_error`; results snapshot; shutdown. |
| `backend/controller.py` | Shutdown teardown; async email; guard-flag `try/finally`; bridge liveness; save gating. |
| `app.py` | `aboutToQuit` wiring. |
| `qml/Main.qml`, `qml/SettingsPage.qml`, `qml/ReportsPage.qml`, `qml/InputPage.qml`, `qml/DashboardPage.qml` | RTL anchors, save-bar padding, empty-state sizing, scrim, elide, busy feedback. |
| `requirements.txt`, `marsad_api.spec` | Dependency and packaging correctness. |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_DEFINITION.md` | Remove false claims. |

---

# Phase 0 — Test foundation

### Task 1: Test harness + hardened settings store

Closes **M2** (world-readable, non-atomic settings) and **M15's** settings-clobber half, and gives every later task a place to put tests.

**Files:**
- Create: `tests/__init__.py`, `tests/_isolation.py`, `tests/test_settings_store.py`
- Modify: `backend/settings_bridge.py`

**Interfaces:**
- Produces: `tests._isolation.isolated_state()` — a context manager yielding a `pathlib.Path` temp dir, with `backend.settings_bridge.SETTINGS_F` and `core.engine.REPORTS` pointed inside it and restored on exit. Every later test file uses this.
- Produces: `save_settings(settings: dict, changed_keys: set[str] | None = None) -> None`. When `changed_keys` is given, the on-disk file is re-read and only those keys are overwritten.

- [ ] **Step 1: Create the package marker**

```bash
mkdir -p tests
printf '' > tests/__init__.py
```

- [ ] **Step 2: Write the isolation helper**

Create `tests/_isolation.py`:

```python
"""Redirect all writable-state module globals into a temp dir for the duration
of a test. Nothing in tests/ may ever touch the user's real settings.json,
reports/ or data/."""
import contextlib
import tempfile
from pathlib import Path


@contextlib.contextmanager
def isolated_state():
    import backend.settings_bridge as sb
    import core.engine as eng

    saved = (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "reports").mkdir()
        sb.SETTINGS_F = root / "settings.json"
        sb.EXAMPLE_F = root / "settings.example.json"   # deliberately absent
        eng.REPORTS = root / "reports"
        try:
            yield root
        finally:
            sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS = saved
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_settings_store.py`:

```python
import json
import os
import unittest

from tests._isolation import isolated_state


class SettingsStoreTests(unittest.TestCase):
    def test_defaults_cover_every_provider(self):
        import backend.settings_bridge as sb
        with isolated_state():
            d = sb.load_settings()
        for key in ("ai_backend", "ollama_url", "claude_api_key", "openai_base_url",
                    "gemini_api_key", "azure_endpoint", "email_password",
                    "whatsapp_token", "engine_profiles"):
            self.assertIn(key, d)

    def test_saved_file_is_owner_only(self):
        import backend.settings_bridge as sb
        with isolated_state():
            sb.save_settings(sb.load_settings())
            mode = os.stat(sb.SETTINGS_F).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_write_is_atomic_no_temp_left_behind(self):
        import backend.settings_bridge as sb
        with isolated_state() as root:
            sb.save_settings(sb.load_settings())
            leftovers = [p.name for p in root.iterdir() if p.name.startswith(".settings-")]
        self.assertEqual(leftovers, [])

    def test_changed_keys_preserves_other_processes_edits(self):
        import backend.settings_bridge as sb
        with isolated_state():
            base = sb.load_settings()
            base["smtp_host"] = "smtp.example.com"
            sb.save_settings(base)

            stale = dict(base)              # a second process's older snapshot
            stale["smtp_host"] = "STALE"
            stale["ollama_model"] = "qwen"
            sb.save_settings(stale, changed_keys={"ollama_model"})

            on_disk = json.loads(sb.SETTINGS_F.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["ollama_model"], "qwen")
        self.assertEqual(on_disk["smtp_host"], "smtp.example.com")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run it and watch it fail**

Run: `python3 -m unittest tests.test_settings_store -v`
Expected: `test_saved_file_is_owner_only` FAILS with `644 != 384`, and `test_changed_keys_preserves_other_processes_edits` FAILS with `TypeError: save_settings() got an unexpected keyword argument 'changed_keys'`.

- [ ] **Step 5: Implement**

In `backend/settings_bridge.py`, replace the import line `import json` with:

```python
import json
import os
import tempfile
```

and replace the whole `save_settings` function with:

```python
def save_settings(settings: dict, changed_keys=None) -> None:
    """Persist settings atomically with owner-only permissions.

    `changed_keys` limits the write to those keys, re-reading whatever is on
    disk first — so a second process editing a different key is not clobbered.
    """
    if changed_keys is not None:
        merged = load_settings()
        for key in changed_keys:
            if key in settings:
                merged[key] = settings[key]
        settings = merged

    SETTINGS_F.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(SETTINGS_F.parent),
                               prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, SETTINGS_F)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

- [ ] **Step 6: Run it and watch it pass**

Run: `python3 -m unittest tests.test_settings_store -v`
Expected: 4 tests, `OK`.

- [ ] **Step 7: Pass the edited keys from the Qt controller**

In `backend/controller.py`, find the `saveSettings` slot and change the persistence call from `save_settings(self._settings)` to:

```python
        save_settings(self._settings, changed_keys=set(payload.keys()))
```

where `payload` is the dict QML handed the slot. If the local variable has a different name in the current code, use that name — it is the dict of fields the Settings page actually edited.

- [ ] **Step 8: Commit**

```bash
git add tests/ backend/settings_bridge.py backend/controller.py
git commit -m "fix(settings): atomic 0600 writes and selective-key saves

Adds the tests/ package with a state-isolation helper so the suite can never
touch real user configuration."
```

---

# Phase 1 — Blockers

### Task 2: Verify TLS certificates on IMAP and SMTP

Closes **BLOCKER-1**.

**Files:**
- Create: `tests/test_connectors_mail.py`
- Modify: `connectors.py:76`, `connectors.py:93`, `connectors.py:149-151`

**Interfaces:**
- Produces: module-level `connectors.SSL_CONTEXT` — an `ssl.SSLContext` with `verify_mode == ssl.CERT_REQUIRED` and `check_hostname is True`, used by every mail connection.

- [ ] **Step 1: Write the failing test**

Create `tests/test_connectors_mail.py`:

```python
import ssl
import unittest
from unittest import mock


class MailTlsTests(unittest.TestCase):
    def test_module_context_verifies_certificates(self):
        import connectors
        ctx = connectors.SSL_CONTEXT
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_imap_test_connection_passes_a_verifying_context(self):
        import connectors
        captured = {}

        class FakeIMAP:
            def __init__(self, host, timeout=None, ssl_context=None):
                captured["ssl_context"] = ssl_context
            def login(self, u, p): pass
            def logout(self): pass

        conn = connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})
        with mock.patch.object(connectors.imaplib, "IMAP4_SSL", FakeIMAP):
            conn.test_connection()
        ctx = captured["ssl_context"]
        self.assertIsNotNone(ctx, "IMAP4_SSL was called without an ssl_context")
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_imap_fetch_passes_a_verifying_context(self):
        import connectors
        captured = {}

        class FakeIMAP:
            def __init__(self, host, timeout=None, ssl_context=None):
                captured["ssl_context"] = ssl_context
            def login(self, u, p): pass
            def select(self, box): pass
            def search(self, *a): return ("OK", [b""])
            def close(self): pass
            def logout(self): pass

        conn = connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})
        with mock.patch.object(connectors.imaplib, "IMAP4_SSL", FakeIMAP):
            conn.fetch_new()
        self.assertEqual(captured["ssl_context"].verify_mode, ssl.CERT_REQUIRED)

    def test_smtp_starttls_gets_a_verifying_context(self):
        import connectors
        captured = {}

        class FakeSMTP:
            def __init__(self, host, port, timeout=None): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def starttls(self, context=None): captured["context"] = context
            def login(self, u, p): pass
            def sendmail(self, *a, **k): pass

        conn = connectors.EmailConnector({"email_user": "u@example.com",
                                          "email_password": "p"})
        with mock.patch.object(connectors.smtplib, "SMTP", FakeSMTP):
            conn.send_report(["boss@example.com"], "<p>x</p>", subject="t")
        self.assertEqual(captured["context"].verify_mode, ssl.CERT_REQUIRED)


if __name__ == "__main__":
    unittest.main()
```

If `EmailConnector.__init__` takes a different argument shape than a settings dict, read `connectors.py` and adapt the two constructor calls — the assertions are what matter.

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_connectors_mail -v`
Expected: FAIL — `AttributeError: module 'connectors' has no attribute 'SSL_CONTEXT'`.

- [ ] **Step 3: Implement**

In `connectors.py`, add `import ssl` to the imports, and immediately after the `log = logging.getLogger(...)` block add:

```python
# TLS for every outbound mail connection. Without an explicit context both
# imaplib and smtplib fall back to ssl._create_stdlib_context(), which is
# CERT_NONE with check_hostname disabled — i.e. no verification at all.
SSL_CONTEXT = ssl.create_default_context()
```

Then change the three call sites:

```python
            mail = imaplib.IMAP4_SSL(self.imap_host, timeout=10, ssl_context=SSL_CONTEXT)
```

```python
            mail = imaplib.IMAP4_SSL(self.imap_host, timeout=20, ssl_context=SSL_CONTEXT)
```

(the second one is in `fetch_new` and previously had no timeout at all — the `timeout=20` also closes half of **M12**)

```python
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as srv:
                srv.starttls(context=SSL_CONTEXT)
```

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_connectors_mail -v`
Expected: 4 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add connectors.py tests/test_connectors_mail.py
git commit -m "fix(security): verify TLS certificates on IMAP and SMTP

imaplib and smtplib silently fall back to an unverified context when none is
passed, so mail credentials were sent to whatever host answered. Also adds the
missing connect timeouts."
```

---

### Task 3: Make the JSON parser reject non-object replies

Closes **BLOCKER-6**.

**Files:**
- Create: `tests/test_engine_parsing.py`
- Modify: `core/engine.py:154-169`

**Interfaces:**
- Produces: `AIEngine._parse_json(raw: str) -> dict` — always returns a `dict`. A non-object reply yields `{"raw": raw, "error": "json_parse"}`.
- Produces: `AIEngine._first_json_object(text: str) -> str | None` — returns the first balanced `{…}` span, ignoring braces inside strings.

- [ ] **Step 1: Write the failing test**

Create `tests/test_engine_parsing.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_engine_parsing -v`
Expected: `test_top_level_array_is_an_error_not_a_list`, `test_null_is_an_error_dict`, `test_scalars_are_error_dicts`, `test_prose_with_braces_after_the_object` and `test_two_objects_returns_the_first` all FAIL.

- [ ] **Step 3: Implement**

In `core/engine.py`, replace the entire `_parse_json` static method with these two static methods:

```python
    @staticmethod
    def _first_json_object(text: str):
        """First balanced {...} span, ignoring braces inside string literals."""
        depth = 0
        start = -1
        in_str = False
        escaped = False
        for i, ch in enumerate(text):
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}" and depth:
                depth -= 1
                if depth == 0 and start >= 0:
                    return text[start:i + 1]
        return None

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """استخراج JSON من رد النموذج — يزيل أسوار ```json ثم يجرّب استخراج {}.

        يجب أن تكون النتيجة قاموساً؛ أي رد آخر (قائمة أو قيمة مفردة) يُعامَل
        كخطأ تحليل حتى لا ينهار المُصدِّر أو خط التحليل لاحقاً.
        يُعيد {"raw":…, "error":"json_parse"} إذا تعذّر.
        """
        clean = raw.replace("```json", "").replace("```", "").strip()
        for candidate in (clean, AIEngine._first_json_object(clean)):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return {"raw": raw, "error": "json_parse"}
```

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_engine_parsing -v`
Expected: 11 tests, `OK`.

- [ ] **Step 5: Add the end-to-end regression test**

Append to `tests/test_engine_parsing.py`:

```python
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
```

The stub returns already-parsed values, so `run_all` must tolerate a worker
result that is not a dict regardless of where it came from.

- [ ] **Step 6: Run it and watch it fail**

Run: `python3 -m unittest tests.test_engine_parsing -v`
Expected: `test_none_reply_does_not_destroy_the_run` FAILS with `TypeError: argument of type 'NoneType' is not a container or iterable`.

- [ ] **Step 7: Harden the membership checks**

In `core/engine.py`, add this module-level helper just above `class AgentsEngine`:

```python
def _as_result(value) -> dict:
    """Any agent result that is not a dict is a failed agent, not a crash."""
    if isinstance(value, dict):
        return value
    return {"raw": repr(value), "error": "bad_shape"}
```

In `AgentsEngine.run_all`, change the worker loop line

```python
            result = self.run_agent(ag_id, text)
```

to

```python
            result = _as_result(self.run_agent(ag_id, text))
```

and in the same method change the chief call

```python
        chief = self.ai.ask(system, chief_input)
```

to

```python
        chief = _as_result(self.ai.ask(system, chief_input))
```

Finally, in `AIEngine.test_connection`, wrap its `ask` result the same way — locate the line that assigns the reply and wrap it in `_as_result(...)` before the `"error" in` test.

- [ ] **Step 8: Run it and watch it pass**

Run: `python3 -m unittest tests.test_engine_parsing -v`
Expected: 13 tests, `OK`.

- [ ] **Step 9: Commit**

```bash
git add core/engine.py tests/test_engine_parsing.py
git commit -m "fix(engine): never let a non-object model reply break the run

A top-level JSON array killed both exporters with AttributeError and a null
reply raised TypeError mid-run, discarding a completed analysis. Also fixes
brace extraction so trailing prose containing braces no longer loses the JSON."
```

---

### Task 4: Correct the dependency list and the API PyInstaller spec

Closes **BLOCKER-4** and **BLOCKER-3**.

**Files:**
- Modify: `requirements.txt`, `marsad_api.spec:16`, `CLAUDE.md:12`

- [ ] **Step 1: Prove the gap**

```bash
python3 - <<'EOF'
import ast, importlib, sys
from pathlib import Path
mods = set()
for f in [Path("connectors.py"), Path("app.py"), Path("run_api.py"),
          *Path("api").glob("*.py"), *Path("core").glob("*.py"), *Path("backend").glob("*.py")]:
    for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
local = {"api", "core", "backend", "connectors", "app", "run_api", "tests"}
third = sorted(m for m in mods - local if m not in sys.stdlib_module_names)
missing = []
for m in third:
    try: importlib.import_module(m)
    except Exception: missing.append(m)
print("third-party imports:", third)
print("NOT INSTALLED:", missing)
req = Path("requirements.txt").read_text()
print("absent from requirements.txt:",
      [p for p in ("python-multipart", "httpx") if p not in req])
EOF
```

Expected: `NOT INSTALLED` lists at least `arabic_reshaper` and `bidi`, and both `python-multipart` and `httpx` are reported absent from `requirements.txt`.

- [ ] **Step 2: Add the missing requirements**

In `requirements.txt`, after the `uvicorn[standard]>=0.27` line add:

```
python-multipart>=0.0.9  # FastAPI UploadFile parsing for POST /api/reports/files
httpx>=0.27         # required by fastapi.testclient (tools/test_api.py, tests/)
```

- [ ] **Step 3: Install and verify**

```bash
python3 -m pip install -r requirements.txt
python3 -c "import arabic_reshaper, bidi, multipart, httpx, fastapi; print('deps OK')"
```

Expected: `deps OK`.

- [ ] **Step 4: Prove PDF export now works**

```bash
python3 - <<'EOF'
import tempfile, os
from core.exporters import export_pdf
res = {"chief": {"overall_health": "جيد", "executive_summary": "ملخص تجريبي",
                 "kpis": [], "top_actions": [], "dept_scores": [], "achievements": []}}
out = os.path.join(tempfile.mkdtemp(), "probe.pdf")
print("wrote", export_pdf(res, out), os.path.getsize(out), "bytes")
EOF
```

Expected: a path and a non-zero byte count — no `ModuleNotFoundError`.

- [ ] **Step 5: Fix the API spec**

In `marsad_api.spec`, delete the `("web/dist", "web/dist"),` entry from the `datas` list. The `web/` tree does not exist in the working directory or anywhere in git history, and PyInstaller aborts Analysis on a missing `datas` source.

- [ ] **Step 6: Correct the stale dependency note**

In `CLAUDE.md`, replace the sentence

```
Qt shapes/orders Arabic natively (HarfBuzz + BiDi),
so no reshaper/bidi libraries are used.
```

with

```
Qt shapes/orders Arabic natively (HarfBuzz + BiDi) for the on-screen UI, so the
QML layer needs no reshaper. The **PDF exporter does**: reportlab shapes
nothing on its own, so `core/exporters.py` uses `arabic-reshaper` +
`python-bidi`. Both are required dependencies — do not remove them.
```

- [ ] **Step 7: Verify the spec parses**

```bash
python3 - <<'EOF'
import re
from pathlib import Path
txt = Path("marsad_api.spec").read_text(encoding="utf-8")
block = txt[txt.index("datas"):]
block = block[:block.index("]") + 1]
for src, _ in re.findall(r'\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\)', block):
    assert Path(src).exists(), f"datas source missing: {src}"
print("all datas sources exist")
EOF
```

Expected: `all datas sources exist`.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt marsad_api.spec CLAUDE.md
git commit -m "fix(packaging): declare python-multipart and httpx, drop dead web/dist

PDF export failed on any machine that installed only the declared deps, the
upload route 500'd without python-multipart, and pyinstaller marsad_api.spec
aborted on a web/ tree that has never existed."
```

---

### Task 5: Stop the web API starting by default, and stop it echoing secrets

> **REDUCED FOR THIS RELEASE — read this box before the steps below.**
> The web API does not ship (see "Release scope: desktop only"). Implement only:
> 1. `SECRET_KEYS` and the redacted `GET /api/settings` (Steps 5's redaction part).
> 2. The blank-secret-means-unchanged rule on `PUT /api/settings`.
> 3. A hard opt-in gate: importing `api.app` raises `RuntimeError` unless the
>    environment variable `MARSAD_API_ENABLE=1` is set.
> 4. `tools/test_api.py` and `tests/test_api_auth.py` set `MARSAD_API_ENABLE=1`
>    before importing `api.app`.
>
> **Do NOT implement:** the token (`api_token` setting, `AppService.api_token`,
> the `X-Marsad-Token` header), the `_guard` middleware, the `Host`/`Origin`
> checks, the `/ws` token parameter, or the token print in the entry points.
> A server that refuses to start needs no authentication. Ignore every step
> below that concerns the token or the middleware; keep everything that
> concerns redaction and the opt-in gate.

Closes **BLOCKER-2** by not shipping the surface.

**Files:**
- Create: `tests/test_api_auth.py`
- Modify: `api/app.py`, `tools/test_api.py`

**Interfaces:**
- Produces: `api.app.SECRET_KEYS: tuple[str, ...]` — settings keys never returned over HTTP.
- Produces: importing `api.app` without `MARSAD_API_ENABLE=1` raises `RuntimeError`.

**Gate implementation** — put this at the top of `api/app.py`, before `service = AppService()`:

```python
import os

if os.environ.get("MARSAD_API_ENABLE") != "1":
    raise RuntimeError(
        "الواجهة البرمجية غير مفعّلة في هذا الإصدار — "
        "شغّلها بـ MARSAD_API_ENABLE=1 على مسؤوليتك (تجريبية، بلا مصادقة)."
    )
```

**Replacement test file** — use this instead of the token tests below:

```python
import os
import unittest

os.environ["MARSAD_API_ENABLE"] = "1"


def _client():
    from fastapi.testclient import TestClient
    from api.app import app
    return TestClient(app, base_url="http://127.0.0.1")


class ApiGateTests(unittest.TestCase):
    def test_import_without_the_flag_is_refused(self):
        import subprocess
        import sys
        proc = subprocess.run(
            [sys.executable, "-c", "import api.app"],
            capture_output=True, text=True,
            env={k: v for k, v in os.environ.items() if k != "MARSAD_API_ENABLE"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("MARSAD_API_ENABLE", proc.stderr)

    def test_settings_never_returns_secret_values(self):
        from api.app import SECRET_KEYS
        r = _client().get("/api/settings")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in SECRET_KEYS:
            self.assertEqual(body.get(key, ""), "",
                             f"{key} was returned to the client")
        self.assertIn("secrets_set", body)

    def test_blank_secret_in_a_put_does_not_wipe_the_stored_one(self):
        from api.app import service
        before = service.settings.get("gemini_api_key", "")
        _client().put("/api/settings",
                      json={"gemini_api_key": "", "ollama_model": "probe-model"})
        self.assertEqual(service.settings.get("gemini_api_key", ""), before)
        self.assertEqual(service.settings.get("ollama_model"), "probe-model")


if __name__ == "__main__":
    unittest.main()
```

`SECRET_KEYS` still excludes `api_token` — that key is not introduced in this release.

- [ ] **Step 1: Add the settings key**

In `backend/settings_bridge.py`, add to `_DEFAULTS` immediately after the `"engine_profiles":  [],` line:

```python
    # local REST API shared secret — generated on first API start
    "api_token":        "",
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_api_auth.py`:

```python
import unittest


def _client():
    from fastapi.testclient import TestClient
    from api.app import app
    # base_url makes TestClient send "Host: 127.0.0.1", which the guard requires
    return TestClient(app, base_url="http://127.0.0.1")


def _token():
    from api.app import service
    return service.api_token


class ApiAuthTests(unittest.TestCase):
    def test_token_is_generated_and_long_enough(self):
        self.assertGreaterEqual(len(_token()), 32)

    def test_request_without_a_token_is_rejected(self):
        r = _client().get("/api/meta")
        self.assertEqual(r.status_code, 401)

    def test_request_with_a_wrong_token_is_rejected(self):
        r = _client().get("/api/meta", headers={"X-Marsad-Token": "nope"})
        self.assertEqual(r.status_code, 401)

    def test_request_with_the_right_token_is_allowed(self):
        r = _client().get("/api/meta", headers={"X-Marsad-Token": _token()})
        self.assertEqual(r.status_code, 200)

    def test_non_loopback_host_is_rejected(self):
        r = _client().get("/api/meta", headers={"X-Marsad-Token": _token(),
                                                "Host": "marsad.attacker.test"})
        self.assertEqual(r.status_code, 403)

    def test_browser_cross_origin_request_is_rejected(self):
        r = _client().post("/api/reports/collect",
                           headers={"X-Marsad-Token": _token(),
                                    "Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_settings_never_returns_secret_values(self):
        from api.app import SECRET_KEYS
        r = _client().get("/api/settings", headers={"X-Marsad-Token": _token()})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in SECRET_KEYS:
            self.assertEqual(body.get(key, ""), "",
                             f"{key} was returned to the client")
        self.assertIn("secrets_set", body)

    def test_blank_secret_in_a_put_does_not_wipe_the_stored_one(self):
        from api.app import service
        h = {"X-Marsad-Token": _token()}
        before = service.settings.get("gemini_api_key", "")
        _client().put("/api/settings", headers=h,
                      json={"gemini_api_key": "", "ollama_model": "probe-model"})
        self.assertEqual(service.settings.get("gemini_api_key", ""), before)
        self.assertEqual(service.settings.get("ollama_model"), "probe-model")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and watch it fail**

Run: `python3 -m unittest tests.test_api_auth -v`
Expected: FAIL — `AttributeError: module 'api.app' has no attribute 'SECRET_KEYS'` and the unauthenticated request returns 200.

- [ ] **Step 4: Generate and persist the token**

In `api/services.py`, add `import secrets` to the imports. In `AppService.__init__`, immediately after the settings are first loaded, add:

```python
        if not self._settings.get("api_token"):
            self._settings["api_token"] = secrets.token_urlsafe(32)
            save_settings(self._settings, changed_keys={"api_token"})
```

and add this property to `AppService`:

```python
    @property
    def api_token(self) -> str:
        return self._settings.get("api_token", "")
```

- [ ] **Step 5: Add the guard middleware and redaction**

In `api/app.py`, add to the imports:

```python
import hmac

from fastapi.responses import JSONResponse
```

Immediately after `app = FastAPI(title="marsad API", docs_url="/api/docs")` add:

```python
SECRET_KEYS = ("claude_api_key", "openai_api_key", "gemini_api_key",
               "azure_api_key", "email_password", "whatsapp_token", "api_token")

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


@app.middleware("http")
async def _guard(request, call_next):
    """Loopback-only, no-browser, token-authenticated.

    The Host check defeats DNS rebinding (a page that resolves its own hostname
    to 127.0.0.1 still sends that hostname in Host). Rejecting any Origin header
    means no browser page can drive the API at all, which closes CSRF on the
    no-body POST routes."""
    host = (request.headers.get("host") or "").rsplit(":", 1)[0]
    if host not in _LOOPBACK_HOSTS:
        return JSONResponse({"detail": "host not allowed"}, status_code=403)
    if request.headers.get("origin") is not None:
        return JSONResponse({"detail": "cross-origin blocked"}, status_code=403)
    sent = request.headers.get("x-marsad-token") or ""
    if not hmac.compare_digest(sent, service.api_token):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)
```

Replace the `get_settings` endpoint body with:

```python
@app.get("/api/settings")
def get_settings():
    """Secrets are never sent to the client — only whether each one is set."""
    raw = service.settings
    safe = {k: v for k, v in raw.items() if k not in SECRET_KEYS}
    for key in SECRET_KEYS:
        safe[key] = ""
    safe["secrets_set"] = {k: bool(raw.get(k)) for k in SECRET_KEYS}
    return safe
```

Replace the `put_settings` endpoint body with:

```python
@app.put("/api/settings")
def put_settings(values: dict):
    """A blank secret means 'unchanged' — the client never had the real value."""
    values = {k: v for k, v in values.items() if k != "secrets_set"}
    for key in SECRET_KEYS:
        if key in values and values[key] == "":
            values.pop(key)
    service.update_settings(values)
    return {"ok": True}
```

If `AppService.update_settings` currently persists with `save_settings(self._settings)`, change it to `save_settings(self._settings, changed_keys=set(values.keys()))`.

- [ ] **Step 6: Authenticate the WebSocket**

In `api/app.py`, change the `/ws` endpoint signature and add a token check as its first statement:

```python
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = ""):
    if not hmac.compare_digest(token, service.api_token):
        await ws.close(code=1008)
        return
```

keeping the rest of the existing handler body unchanged below it.

- [ ] **Step 7: Print the token at startup**

In `api/__main__.py` and `run_api.py`, immediately before the `uvicorn.run(...)` call add:

```python
    from api.app import service
    print(f"marsad API token: {service.api_token}")
    print("send it as the  X-Marsad-Token  header (and ?token=… on /ws)")
```

- [ ] **Step 8: Run it and watch it pass**

Run: `python3 -m unittest tests.test_api_auth -v`
Expected: 8 tests, `OK`.

- [ ] **Step 9: Update the existing smoke suite for the new contract**

`tools/test_api.py` will now get 401s. In its `setUpClass`, replace the client construction with:

```python
        from api.app import service
        cls.client = TestClient(app, base_url="http://127.0.0.1")
        cls.client.headers.update({"X-Marsad-Token": service.api_token})
```

Run: `python3 tools/test_api.py`
Expected: `Ran 7 tests`, `OK`.

- [ ] **Step 10: Commit**

```bash
git add api/ tools/test_api.py backend/settings_bridge.py tests/test_api_auth.py
git commit -m "feat(api): require a local token, reject browsers, stop echoing secrets

GET /api/settings returned every API key and the mail password to any
unauthenticated caller, and the no-body POST routes (including the one that
runs npm install) were reachable cross-origin. Loopback binding alone does not
stop DNS rebinding."
```

---

# Phase 2 — Data safety and output correctness

### Task 6: Escape LLM output in the emailed HTML report

Closes **M1**.

**Files:**
- Create: `tests/test_report_html.py`
- Modify: `connectors.py:826-907`

**Interfaces:**
- Produces: `connectors._h(value) -> str` — HTML-escapes any value, including quotes, for interpolation into the report template.

- [ ] **Step 1: Write the failing test**

Create `tests/test_report_html.py`:

```python
import unittest

from connectors import build_report_html

EVIL = '<img src=x onerror="alert(1)"><a href="https://evil.example">اضغط</a>'


def _results(**chief):
    base = {"overall_health": "جيد", "executive_summary": "", "kpis": [],
            "top_actions": [], "dept_scores": [], "achievements": []}
    base.update(chief)
    return {"chief": base}


class ReportHtmlEscapingTests(unittest.TestCase):
    def test_executive_summary_is_escaped(self):
        html = build_report_html(_results(executive_summary=EVIL))
        self.assertNotIn("onerror=", html)
        self.assertNotIn('href="https://evil.example"', html)
        self.assertIn("&lt;img", html)

    def test_action_fields_are_escaped(self):
        html = build_report_html(_results(top_actions=[
            {"priority": 1, "action": EVIL, "owner": EVIL, "deadline": EVIL}]))
        self.assertNotIn("onerror=", html)

    def test_kpi_fields_are_escaped(self):
        html = build_report_html(_results(kpis=[
            {"name": EVIL, "value": EVIL, "trend": EVIL, "status": "جيد"}]))
        self.assertNotIn("onerror=", html)

    def test_ordinary_arabic_is_untouched(self):
        html = build_report_html(_results(
            executive_summary="المشروع يسير وفق الخطة"))
        self.assertIn("المشروع يسير وفق الخطة", html)
        self.assertIn('dir="rtl"', html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_report_html -v`
Expected: the three escaping tests FAIL — `onerror=` is present.

- [ ] **Step 3: Implement**

In `connectors.py`, add `import html as _html` to the imports, and immediately above `def build_report_html(` add:

```python
def _h(value) -> str:
    """Escape a value for HTML interpolation.

    Report content is model output derived from field reports that arrive from
    WhatsApp groups, inbound email and watched folders — i.e. from outside the
    trust boundary. The PDF exporter escapes; this path must too."""
    return _html.escape("" if value is None else str(value), quote=True)
```

Then wrap every interpolated model value in `build_report_html`. The action rows become:

```python
        actions_rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #e2e8f0;text-align:center;
                     font-weight:bold;">{_h(act.get('priority',''))}</td>
          <td style="padding:8px;border:1px solid #e2e8f0;">{_h(act.get('action',''))}</td>
          <td style="padding:8px;border:1px solid #e2e8f0;">{_h(act.get('owner',''))}</td>
          <td style="padding:8px;border:1px solid #e2e8f0;">{_h(act.get('deadline',''))}</td>
        </tr>"""
```

the KPI cards become:

```python
        kpi_cards += f"""
        <div style="background:#f8fafc;border:1px solid {sc};border-radius:8px;
                    padding:12px;text-align:center;min-width:100px;">
          <div style="font-size:20px;font-weight:bold;color:{sc};">{_h(kpi.get('value',''))}</div>
          <div style="font-size:11px;color:#64748b;">{_h(kpi.get('name',''))}</div>
          <div style="font-size:14px;">{_h(kpi.get('trend','→'))}</div>
        </div>"""
```

and in the final `return f"""…"""` template wrap `{chief.get('executive_summary','')}` as `{_h(chief.get('executive_summary',''))}` and `{health}` as `{_h(health)}`. Read the whole template and wrap **every** `{…}` that reads from `results`; leave the hard-coded colour variables (`color`, `sc`) and the `date` unwrapped — they are generated locally, not model output.

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_report_html -v`
Expected: 4 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add connectors.py tests/test_report_html.py
git commit -m "fix(security): escape model output in the emailed HTML report

Field reports arrive from outside the trust boundary, so prompt-injected markup
reached executives' inboxes as live HTML. The PDF path already escaped."
```

---

### Task 7: Bound uploads and file reads

Closes **M3** and **M4**.

**Files:**
- Create: `tests/test_api_uploads.py`
- Modify: `api/app.py:184-196`, `connectors.py` (`_read_pdf`, `_read_docx`, the `.txt` branch, and the email attachment path)

**Interfaces:**
- Produces: `api.app.MAX_UPLOAD_BYTES = 25 * 1024 * 1024`, `api.app.MAX_UPLOAD_FILES = 20`.
- Produces: `connectors.MAX_CHARS = 40_000` — the per-report content ceiling applied by every reader.
- Produces: `connectors._cap(text: str) -> str` — truncates to `MAX_CHARS` and appends `\n\n[اقتُطع النص — تجاوز الحد المسموح]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_api_uploads.py`:

```python
import unittest


def _client():
    from fastapi.testclient import TestClient
    from api.app import app
    from api.app import service
    c = TestClient(app, base_url="http://127.0.0.1")
    c.headers.update({"X-Marsad-Token": service.api_token})
    return c


class UploadLimitTests(unittest.TestCase):
    def test_oversize_upload_is_rejected(self):
        from api.app import MAX_UPLOAD_BYTES
        blob = b"a" * (MAX_UPLOAD_BYTES + 1024)
        r = _client().post("/api/reports/files",
                           files=[("files", ("big.txt", blob, "text/plain"))])
        self.assertEqual(r.status_code, 413)

    def test_too_many_files_are_rejected(self):
        from api.app import MAX_UPLOAD_FILES
        files = [("files", (f"f{i}.txt", b"x", "text/plain"))
                 for i in range(MAX_UPLOAD_FILES + 1)]
        r = _client().post("/api/reports/files", files=files)
        self.assertEqual(r.status_code, 413)

    def test_dot_dot_filename_does_not_500(self):
        r = _client().post("/api/reports/files",
                           files=[("files", ("..", b"x", "text/plain"))])
        self.assertNotEqual(r.status_code, 500)
        self.assertEqual(r.status_code, 200)

    def test_traversal_filename_stays_inside_uploads(self):
        from core.paths import DATA_DIR
        r = _client().post("/api/reports/files",
                           files=[("files", ("../../escape.txt", b"x", "text/plain"))])
        self.assertEqual(r.status_code, 200)
        self.assertFalse((DATA_DIR / "escape.txt").exists())


class ReadCapTests(unittest.TestCase):
    def test_txt_content_is_capped(self):
        import tempfile
        from pathlib import Path
        import connectors
        p = Path(tempfile.mkdtemp()) / "ran_huge.txt"
        p.write_text("ب" * (connectors.MAX_CHARS + 5000), encoding="utf-8")
        rep = connectors.read_file_to_report(p)
        self.assertLessEqual(len(rep["content"]), connectors.MAX_CHARS + 200)
        self.assertIn("اقتُطع", rep["content"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_api_uploads -v`
Expected: FAIL — `ImportError: cannot import name 'MAX_UPLOAD_BYTES'`.

- [ ] **Step 3: Implement the upload guard**

In `api/app.py`, add `import re` to the imports and these constants next to `SECRET_KEYS`:

```python
MAX_UPLOAD_BYTES = 25 * 1024 * 1024   # per file
MAX_UPLOAD_FILES = 20                 # per request
_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|]')


def _safe_upload_name(raw: str) -> str:
    name = Path(raw or "").name
    if name in ("", ".", ".."):
        name = "upload"
    return _UNSAFE_NAME.sub("_", name)[:120]
```

Replace the `upload_files` body with:

```python
@app.post("/api/reports/files")
async def upload_files(files: list[UploadFile] = File(...)):
    """Save uploads under DATA_DIR, then hand them to the async add-files path."""
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(413, f"عدد الملفات يتجاوز الحد ({MAX_UPLOAD_FILES})")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest_dir = DATA_DIR / "uploads" / f"api_{ts}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        dest = dest_dir / _safe_upload_name(f.filename)
        written = 0
        try:
            with open(dest, "wb") as out:
                while True:
                    chunk = await f.read(1 << 20)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_UPLOAD_BYTES:
                        out.close()
                        dest.unlink(missing_ok=True)
                        raise HTTPException(
                            413, f"حجم الملف يتجاوز الحد ({MAX_UPLOAD_BYTES // (1024*1024)} ميغابايت)")
                    out.write(chunk)
        except HTTPException:
            raise
        except OSError as e:
            raise HTTPException(400, f"تعذّر حفظ الملف: {_safe_upload_name(f.filename)}") from e
        paths.append(str(dest))
    return {"started": service.add_files(paths), "saved": len(paths)}
```

Note the `%f` added to the timestamp — it also fixes same-second uploads colliding into one directory.

- [ ] **Step 4: Implement the read caps**

In `connectors.py`, add next to the other module constants:

```python
MAX_CHARS = 40_000   # per-report content ceiling — everything downstream of a
                     # reader goes verbatim into an LLM prompt


def _cap(text: str) -> str:
    text = text or ""
    if len(text) <= MAX_CHARS:
        return text
    return text[:MAX_CHARS] + "\n\n[اقتُطع النص — تجاوز الحد المسموح]"
```

Then wrap the return value of the uncapped readers. In `_read_pdf`, `_read_docx`, and the `.txt` branch of `read_file_to_report`, wrap the produced string in `_cap(...)`. In the email path, wrap the decoded body and each extracted attachment text in `_cap(...)` as well. Do not change the already-capped `_read_excel`, `_read_csv` or `_read_json`.

- [ ] **Step 5: Run it and watch it pass**

Run: `python3 -m unittest tests.test_api_uploads -v`
Expected: 5 tests, `OK`.

- [ ] **Step 6: Commit**

```bash
git add api/app.py connectors.py tests/test_api_uploads.py
git commit -m "fix(api): cap upload size and count, sanitize filenames, cap reads

An unbounded upload was read whole into RAM, a filename of '..' produced an
unhandled 500, and .txt/PDF/docx/attachments were read without limit straight
into the model prompt."
```

---

### Task 8: Make the exporters survive real model output

Closes **M5** and **M6**.

**Files:**
- Create: `tests/test_exporters.py`
- Modify: `core/exporters.py`

**Interfaces:**
- Produces, all in `core/exporters.py`: `_num(v, default=0.0) -> float`, `_int(v, default=0) -> int`, `_pct(v) -> str`, `_rows(v) -> list`, `_obj(v) -> dict`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_exporters.py`:

```python
import os
import tempfile
import unittest

from core.exporters import export_excel, export_pdf


def hostile_results():
    """Every value here is a shape a real model has actually produced."""
    return {
        "chief": {
            "overall_health": "جيد",
            "executive_summary": "ملخص",
            "kpis": [{"name": "الإنجاز", "value": "80%", "trend": "→", "status": "متوسط"}],
            "top_actions": [
                {"priority": "1", "action": "تسريع التوريد", "owner": "المشتريات",
                 "deadline": "أسبوع", "impact": "عالي"},
                {"priority": 0, "action": "مراجعة", "owner": "الجودة",
                 "deadline": "يومان", "impact": "متوسط"},
                {"priority": None, "action": "متابعة", "owner": "العمليات",
                 "deadline": "شهر", "impact": "منخفض"},
            ],
            "dept_scores": [], "achievements": [],
        },
        "cost": {"total_budget": "10م", "spent": "4م", "remaining": "6م",
                 "spent_pct": "80%", "deviation_pct": "12%", "forecast": "ضمن الميزانية",
                 "alerts": []},
        "risk": {"risks": None},
        "schedule": {"delay_days": "3", "original_end": "2026-09-01",
                     "new_end": "2026-09-04", "phases": None, "critical_path": []},
        "quality": {"inspected": "40", "passed": 36, "failed": 4, "pass_rate": "90%"},
        "safety": {"incidents": 0, "safety_score": "95%", "status": "آمن"},
    }


class ExporterRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_excel_survives_string_and_null_values(self):
        out = export_excel(hostile_results(), os.path.join(self.dir, "a.xlsx"))
        self.assertGreater(os.path.getsize(out), 3000)

    def test_pdf_survives_string_and_null_values(self):
        out = export_pdf(hostile_results(), os.path.join(self.dir, "a.pdf"))
        self.assertGreater(os.path.getsize(out), 3000)

    def test_percentages_are_not_doubled(self):
        import openpyxl
        out = export_excel(hostile_results(), os.path.join(self.dir, "b.xlsx"))
        wb = openpyxl.load_workbook(out)
        for ws in wb:
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if isinstance(cell, str):
                        self.assertNotIn("%%", cell)
                        self.assertNotIn("None%", cell)

    def test_excel_creates_a_missing_output_directory(self):
        nested = os.path.join(self.dir, "new", "deeper", "c.xlsx")
        out = export_excel(hostile_results(), nested)
        self.assertTrue(os.path.exists(out))

    def test_empty_results_still_produce_files(self):
        for fn, ext in ((export_pdf, ".pdf"), (export_excel, ".xlsx")):
            with self.subTest(ext=ext):
                out = fn({"chief": {}}, os.path.join(self.dir, "empty" + ext))
                self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_exporters -v`
Expected: `test_excel_survives_string_and_null_values` FAILS with `TypeError: unsupported operand type(s) for -: 'str' and 'int'`.

- [ ] **Step 3: Add the coercion helpers**

In `core/exporters.py`, add `import re` at the top and these module-level helpers above `export_pdf`:

```python
def _num(value, default=0.0) -> float:
    """First number in a value the model may have returned as '80%' or '4.2 مليون'."""
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if m:
            return float(m.group())
    return float(default)


def _int(value, default=0) -> int:
    return int(_num(value, default))


def _pct(value) -> str:
    """Format a percentage without ever producing '80%%' or 'None%'."""
    return f"{_num(value, 0.0):g}%"


def _rows(value) -> list:
    return value if isinstance(value, list) else []


def _obj(value) -> dict:
    return value if isinstance(value, dict) else {}
```

- [ ] **Step 4: Apply them at every fragile site**

In `export_pdf`, change the finance block to:

```python
    dev = _num(fin.get("deviation_pct", 0))
    fdata = [[Paragraph(ar(lbl), PS("fl", "Naskh", 10, INK2)), val(v)]
             for lbl, v in (("الميزانية الإجمالية", fin.get("total_budget", "-")),
                            ("المُنفَق", fin.get("spent", "-")),
                            ("المتبقي", fin.get("remaining", "-")),
                            ("نسبة الإنفاق", _pct(fin.get("spent_pct", 0))))]
    fdata.append([Paragraph(ar("نسبة الانحراف"), PS("fld", "Naskh", 10, INK2)),
                  val(f"{dev:+g}%", color=BAD if dev > 0 else INK)])
```

`{dev:+g}` produces `+12%` and `-5%` correctly, and only a *positive* deviation is now red.

In `export_excel`, change the action-plan loop to:

```python
    for i,act in enumerate(_rows(chief.get("top_actions")),act_start+2):
        act=_obj(act)
        p=max(0,min(_int(act.get("priority",1),1)-1,2)); bg=pbgs[p]
```

and drop `act.get("dept","")` from the value list and `"الإدارة"` from the header list — no prompt ever asks for that key, so the column is permanently blank (part of **M7**).

Everywhere in both exporters, replace `results.get("<agent>", {})` with `_obj(results.get("<agent>"))`, replace `<section>.get("<list>", [])` with `_rows(<section>.get("<list>"))`, and replace every `f'{x}%'` with `_pct(x)`. Also remove `ph.get("responsible_dept","")` from the schedule sheet and `fin.get("next_payment","-")` from the cost sheet, together with their headers — same reason.

At the top of `export_excel`, add the directory creation `export_pdf` already has:

```python
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
```

(import `Path` from `pathlib` if it is not already imported).

- [ ] **Step 5: Run it and watch it pass**

Run: `python3 -m unittest tests.test_exporters -v`
Expected: 5 tests, `OK`.

- [ ] **Step 6: Commit**

```bash
git add core/exporters.py tests/test_exporters.py
git commit -m "fix(export): tolerate the shapes models actually return

A priority of \"1\" killed Excel export outright, a deviation of \"12%\" was
silently rendered as +0%, and percentages were doubled to 80%%. Also removes
three columns that read keys no prompt requests."
```

---

### Task 9: One status→colour table for every surface

Closes **M8** and **M10**.

**Files:**
- Create: `core/status.py`, `tests/test_status_tiers.py`
- Modify: `core/exporters.py`, `connectors.py`, `backend/theme.py`

**Interfaces:**
- Produces: `core.status.tier(literal: str) -> str` returning one of `"good"`, `"warn"`, `"bad"`, `"neutral"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_status_tiers.py`:

```python
import unittest

from core.status import tier


class StatusTierTests(unittest.TestCase):
    def test_good_literals(self):
        for s in ("جيد", "مكتمل", "آمن", "منخفضة"):
            self.assertEqual(tier(s), "good", s)

    def test_warn_literals(self):
        for s in ("متوسط", "متوسطة", "تحذير", "في الموعد"):
            self.assertEqual(tier(s), "warn", s)

    def test_bad_literals(self):
        for s in ("متأخر", "خطر", "عالية"):
            self.assertEqual(tier(s), "bad", s)

    def test_unknown_and_empty_are_neutral_not_critical(self):
        for s in ("", None, "غير محدد", "شيء آخر"):
            self.assertEqual(tier(s), "neutral", repr(s))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_status_tiers -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.status'`.

- [ ] **Step 3: Implement**

Create `core/status.py`:

```python
"""Single source of truth for the fixed Arabic status literals.

Every surface — the PDF, the Excel workbook, the emailed HTML and the Qt theme
— must agree on which tier a literal belongs to. Before this module they did
not: `متوسط` was amber in the PDF and red in Excel and in email, and the
`غير محدد` value that `_ensure_chief_schema` writes when the coordinator agent
fails was rendered as a critical-red banner instead of a neutral one.
"""

_GOOD = {"جيد", "مكتمل", "آمن", "منخفضة", "منخفض", "ناجح"}
_WARN = {"متوسط", "متوسطة", "تحذير", "في الموعد", "قيد التنفيذ"}
_BAD  = {"متأخر", "خطر", "عالية", "عالٍ", "حرج", "فشل"}


def tier(literal) -> str:
    """Map a status literal to good / warn / bad / neutral.

    Anything unrecognised — including empty and `غير محدد` — is neutral, never
    critical: an unknown status is missing information, not an alarm.
    """
    s = (literal or "").strip()
    if s in _GOOD:
        return "good"
    if s in _WARN:
        return "warn"
    if s in _BAD:
        return "bad"
    return "neutral"
```

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_status_tiers -v`
Expected: 4 tests, `OK`.

- [ ] **Step 5: Route the three consumers through it**

In `core/exporters.py`, add `from core.status import tier` and replace every inline
`"جيد" if … else "تحذير" if … else …` colour choice with a lookup:

```python
    _PDF_TIER = {"good": OK, "warn": WARN, "bad": BAD, "neutral": INK2}
    _XL_TIER  = {"good": "065F46", "warn": "78350F", "bad": "7F1D1D", "neutral": "334155"}
```

and use `_PDF_TIER[tier(value)]` / `_XL_TIER[tier(value)]` at each site. Use the existing colour constant names from the file if they differ from `OK`/`WARN`/`BAD`.

In `connectors.py`, add `from core.status import tier` (guarding it the same way the existing `friendly_error` import is guarded) and replace both colour ladders in `build_report_html`:

```python
    _HTML_TIER = {"good": "#10b981", "warn": "#f59e0b",
                  "bad": "#ef4444", "neutral": "#64748b"}
    color = _HTML_TIER[tier(health)]
```

```python
        sc = _HTML_TIER[tier(kpi.get("status"))]
```

In `backend/theme.py`, rewrite `statusColor` to delegate:

```python
    @Slot(str, result=str)
    def statusColor(self, literal: str) -> str:
        from core.status import tier
        return {"good": self._C["ok"], "warn": self._C["warn"],
                "bad": self._C["danger"], "neutral": self._C["ink2"]}[tier(literal)]
```

Use the actual key names present in `theme.py`'s colour map.

- [ ] **Step 6: Fix escape-after-bidi in the PDF**

In `core/exporters.py`, the `ar()` helper currently escapes *before* reordering, so `&amp;` is emitted reversed as `;pma&`. Replace its body with:

```python
    def ar(text):
        """Arabic-ready string for a reportlab Paragraph: reshape → bidi → escape.

        Escaping must come last: XML entities contain Latin letters and ASCII
        punctuation, so reordering them inside an RTL run emits ';pma&'.

        En/em dashes become hyphen-minus first: U+2013/2014 break the BiDi
        number run (renders "8060" out of "60–80%"), while ES separators
        (-, /, .) keep digits as one LTR run."""
        s = str(text if text is not None else "")
        s = s.replace("–", "-").replace("—", "-")
        s = get_display(arabic_reshaper.reshape(s)) if _has_ar(s) else s
        return _esc(s)
```

- [ ] **Step 7: Add the regression tests**

Append to `tests/test_exporters.py`:

```python
class StatusAndEscapingTests(unittest.TestCase):
    def test_ampersand_survives_the_pdf_pipeline(self):
        import os, tempfile
        res = hostile_results()
        res["chief"]["executive_summary"] = "شركة الاتصالات & الشبكات"
        out = export_pdf(res, os.path.join(tempfile.mkdtemp(), "amp.pdf"))
        import PyPDF2
        text = "".join(p.extract_text() or "" for p in PyPDF2.PdfReader(out).pages)
        self.assertNotIn(";pma&", text)

    def test_failed_chief_is_not_rendered_as_critical(self):
        from core.status import tier
        self.assertEqual(tier("غير محدد"), "neutral")

    def test_html_and_excel_agree_with_the_pdf_on_a_medium_kpi(self):
        from core.status import tier
        self.assertEqual(tier("متوسط"), "warn")
```

Run: `python3 -m unittest tests.test_exporters tests.test_status_tiers -v`
Expected: `OK`.

- [ ] **Step 8: Commit**

```bash
git add core/status.py core/exporters.py connectors.py backend/theme.py tests/
git commit -m "fix(report): one status-tier table for PDF, Excel, email and UI

The same KPI status rendered amber in the PDF and red in Excel and email, and a
failed coordinator agent was emailed as a critical red banner. Also escapes
after bidi reordering so '&' no longer renders as ';pma&'."
```

---

### Task 10: Restore the OpenAI-compatible retry

Closes **M9**.

**Files:**
- Create: `tests/test_engine_backends.py`
- Modify: `core/engine.py` (`_http_json`, `_openai_chat`)

**Interfaces:**
- Produces: `_http_json` error dicts now carry `{"error": <arabic>, "status": <int|None>}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_engine_backends.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_engine_backends -v`
Expected: `test_http_400_triggers_a_retry_without_response_format` FAILS with `2 != 1` — the retry never fires because `_http_json` already replaced the message with Arabic text, so `res["error"].startswith("HTTP 400")` is always False.

- [ ] **Step 3: Implement**

In `core/engine.py`, in `_http_json`, add the status code to every error return. Where the `HTTPError` branch builds its dict, change it to include the code, and give the other error branches `"status": None`:

```python
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            return {"error": friendly_error(f"HTTP {e.code}: {body}"), "status": e.code}
```

Then in `_openai_chat`, replace the retry condition:

```python
        res = self._http_json(base_url, payload, headers, self._timeout())
        if "error" in res:
            # بعض الواجهات المتوافقة (مثل LM Studio) ترفض response_format بـ HTTP 400 — أعِد المحاولة بدونه
            if res.get("status") == 400 and "response_format" in payload:
                payload.pop("response_format", None)
                res = self._http_json(base_url, payload, headers, self._timeout())
            if "error" in res:
                return res
```

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_engine_backends -v`
Expected: 4 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add core/engine.py tests/test_engine_backends.py
git commit -m "fix(engine): restore the OpenAI-compatible 400 retry

friendly_error() had already translated the message, so the startswith('HTTP
400') test could never match and LM Studio / OpenRouter models that reject
response_format failed permanently."
```

---

### Task 11: Surface the five agents the user never sees

Closes the remainder of **M7**.

**Files:**
- Modify: `core/exporters.py`
- Test: `tests/test_exporters.py`

**Interfaces:**
- Consumes: `_obj`, `_rows`, `_num`, `_pct` from Task 8; `tier` from Task 9.
- Produces: an Excel worksheet named `الإدارات` containing one row per department agent.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_exporters.py`:

```python
class DepartmentCoverageTests(unittest.TestCase):
    def test_every_worker_agent_reaches_the_workbook(self):
        import openpyxl, os, tempfile
        res = hostile_results()
        res.update({
            "ops":      {"completion_pct": 80, "active_sites": 12, "team_status": "جيد"},
            "civil":    {"towers_built": 30, "towers_total": 50, "civil_pct": 60},
            "contract": {"active_contracts": 5, "total_value": "8م"},
            "procure":  {"pending_orders": 3, "approved_vendors": 9},
            "supply":   {"warehouse_fill_pct": 70, "delayed_shipments": 1},
        })
        out = export_excel(res, os.path.join(tempfile.mkdtemp(), "dept.xlsx"))
        wb = openpyxl.load_workbook(out)
        self.assertIn("الإدارات", wb.sheetnames)
        text = "\n".join(
            str(c) for row in wb["الإدارات"].iter_rows(values_only=True)
            for c in row if c is not None)
        for label in ("العمليات الميدانية", "الأعمال الإنشائية",
                      "العقود", "المشتريات", "المخازن"):
            self.assertIn(label, text)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_exporters -v`
Expected: FAIL — `'الإدارات' not found in [...]`.

- [ ] **Step 3: Implement**

In `core/exporters.py`, inside `export_excel` and after the existing sheets are built, add:

```python
    # ── ورقة الإدارات — الوكلاء الذين لا تظهر نتائجهم في أي مكان آخر ──
    DEPT_ROWS = (
        ("العمليات الميدانية", "ops", (
            ("نسبة الإنجاز", lambda d: _pct(d.get("completion_pct", 0))),
            ("المواقع النشطة", lambda d: _int(d.get("active_sites", 0))),
            ("حالة الفريق", lambda d: d.get("team_status", "-")))),
        ("الأعمال الإنشائية", "civil", (
            ("الأبراج المنجزة", lambda d: _int(d.get("towers_built", 0))),
            ("إجمالي الأبراج", lambda d: _int(d.get("towers_total", 0))),
            ("نسبة الإنشاء", lambda d: _pct(d.get("civil_pct", 0))))),
        ("العقود", "contract", (
            ("العقود النشطة", lambda d: _int(d.get("active_contracts", 0))),
            ("القيمة الإجمالية", lambda d: d.get("total_value", "-")),
            ("مدفوعات معلّقة", lambda d: d.get("pending_payments", "-")))),
        ("المشتريات", "procure", (
            ("طلبات معلّقة", lambda d: _int(d.get("pending_orders", 0))),
            ("موردون معتمدون", lambda d: _int(d.get("approved_vendors", 0))),
            ("قيمة أوامر الشراء", lambda d: d.get("total_po_value", "-")))),
        ("المخازن وسلاسل التوريد", "supply", (
            ("امتلاء المخزن", lambda d: _pct(d.get("warehouse_fill_pct", 0))),
            ("شحنات في الطريق", lambda d: _int(d.get("in_transit_shipments", 0))),
            ("شحنات متأخرة", lambda d: _int(d.get("delayed_shipments", 0))))),
    )

    wsd = wb.create_sheet("الإدارات")
    wsd.sheet_view.rightToLeft = True
    for ci, h in enumerate(["الإدارة", "المؤشر", "القيمة"], 1):
        hdr(wsd.cell(1, ci), MID)
        wsd.cell(1, ci).value = h
    r = 2
    for label, key, fields in DEPT_ROWS:
        data = _obj(results.get(key))
        if not data:
            continue
        for field_label, getter in fields:
            wsd.cell(r, 1).value = label
            wsd.cell(r, 2).value = field_label
            try:
                wsd.cell(r, 3).value = getter(data)
            except Exception:
                wsd.cell(r, 3).value = "-"
            for ci in (1, 2, 3):
                body(wsd.cell(r, ci), bg=(GRAY if r % 2 == 0 else WHITE))
            r += 1
    wsd.column_dimensions["A"].width = 28
    wsd.column_dimensions["B"].width = 24
    wsd.column_dimensions["C"].width = 18
```

Use the actual helper names present in the file for `hdr`, `body`, `MID`, `GRAY`, `WHITE` — read the surrounding sheet-building code and match it.

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_exporters -v`
Expected: all tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add core/exporters.py tests/test_exporters.py
git commit -m "feat(export): surface ops, civil, contract, procure and supply

Five of the ten worker agents appeared in no export, no email and no page —
the user paid for eleven model calls and saw six. They now have a sheet."
```

---

# Phase 3 — Threading and process safety

### Task 12: Shut down cleanly

Closes **M11**.

**Files:**
- Modify: `app.py`, `backend/controller.py`

**Interfaces:**
- Produces: `AppController.shutdown()` — a `@Slot()` that stops the analysis thread, the connector hub and the WhatsApp bridge. Idempotent.

- [ ] **Step 1: Reproduce the crash**

```bash
QT_QPA_PLATFORM=offscreen python3 - <<'EOF'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, QTimer
import sys
app = QApplication(sys.argv)
t = QThread()
class Slow(QThread):
    def run(self):
        import time; time.sleep(30)
s = Slow(); s.start()
QTimer.singleShot(200, app.quit)
app.exec()
print("if you see 'QThread: Destroyed while thread is still running' below, that is the bug")
EOF
```

Expected: the process aborts or prints the `QThread: Destroyed while thread is still running` warning. This is what happens when the user closes the window mid-analysis.

- [ ] **Step 2: Implement the shutdown slot**

In `backend/controller.py`, add to `AppController`:

```python
    @Slot()
    def shutdown(self):
        """Stop every background worker before the app object is destroyed.

        Without this the QThread is torn down while still running and Qt calls
        qFatal — closing the window during an analysis aborted the process."""
        if getattr(self, "_shutting_down", False):
            return
        self._shutting_down = True
        try:
            self.stopWhatsAppBridge()
        except Exception:
            pass
        try:
            if self._hub:
                self._hub.stop_all()
        except Exception:
            pass
        if self._thread:
            self._thread.requestInterruption()
            self._thread.quit()
            if not self._thread.wait(5000):
                self._thread.terminate()
                self._thread.wait(1000)
            self._thread = None
            self._worker = None
```

- [ ] **Step 3: Wire it up**

In `app.py`, immediately after `view.show()` add:

```python
    app.aboutToQuit.connect(controller.shutdown)
```

- [ ] **Step 4: Stop leaking a QThread per run**

In `backend/controller.py`, change `_teardown_thread` to release the worker properly:

```python
    def _teardown_thread(self):
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
```

- [ ] **Step 5: Verify**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py /tmp/marsad-shots 2>&1 | tail -5
ls /tmp/marsad-shots
```

Expected: six PNGs, and **no** `QThread: Destroyed while thread is still running` in the output.

- [ ] **Step 6: Commit**

```bash
git add app.py backend/controller.py
git commit -m "fix(desktop): stop background workers on quit

Closing the window during an analysis destroyed a running QThread and aborted
the process. Also releases the thread and worker instead of leaking one per run."
```

---

### Task 13: No blocking network calls on the GUI thread, and no stuck flags

Closes **M13** and the remainder of **M12**.

**Files:**
- Modify: `backend/controller.py`

**Interfaces:**
- Produces: `AppController.emailSent = Signal(bool, str)` — emitted on the GUI thread when the report email finishes.

- [ ] **Step 1: Find every guard flag set outside a `try/finally`**

```bash
grep -n "_collecting\|_adding\|_testing_engine\|_testing_email\|_models_busy\|_wa_starting" backend/controller.py
```

Expected: several `= True` assignments immediately before a `threading.Thread(...).start()`, with the matching `= False` only on some paths.

- [ ] **Step 2: Make `sendEmailReport` asynchronous**

In `backend/controller.py`, add the signal next to the other `Signal` declarations:

```python
    emailSent = Signal(bool, str)
```

Replace the body of the `sendEmailReport` slot with:

```python
    @Slot()
    def sendEmailReport(self):
        if not self._results:
            self.notify.emit("لا توجد نتائج لإرسالها")
            return
        if self._sending_email:
            return
        self._sending_email = True
        threading.Thread(target=self._run_send_email, daemon=True).start()

    def _run_send_email(self):
        """SMTP on a worker thread — smtplib blocks for the OS TCP timeout."""
        try:
            recipients = self._settings.get("report_recipients") or []
            if not recipients:
                self._emailSent.emit(False, "لا يوجد مستلمون مضبوطون — اضبطهم في الإعدادات")
                return
            html = build_report_html(self._results)
            ok = self._hub.send_report(recipients, html)
            self._emailSent.emit(
                bool(ok),
                "أُرسل التقرير بالبريد" if ok else "تعذّر إرسال البريد — راجع الإعدادات")
        except Exception as e:
            self._emailSent.emit(False, friendly_error(str(e)))
        finally:
            self._sending_email = False
```

Add a private cross-thread signal beside the others:

```python
    _emailSent = Signal(bool, str)
```

connect it in `__init__` (next to the other private-signal connections):

```python
        self._sending_email = False
        self._emailSent.connect(self._on_email_sent)
```

and add the GUI-thread slot:

```python
    @Slot(bool, str)
    def _on_email_sent(self, ok, message):
        self.emailSent.emit(ok, message)
        self.notify.emit(message)
```

If `send_report` in the current code takes a subject or attachments, pass the same arguments the old synchronous call used.

- [ ] **Step 3: Make every guarded thread clear its flag**

For each guarded operation, move the flag reset into a `finally`. `_run_collect` becomes:

```python
    def _run_collect(self):
        """جمع التقارير (IMAP/ERP/HTTP) على خيط منفصل حتى لا تتجمّد الواجهة."""
        try:
            self._collected.emit(self._hub.collect_all())
        except Exception as e:
            self.notify.emit(f"تعذّر الجمع: {friendly_error(str(e))}")
        finally:
            self._collecting = False
```

Then, in `_on_collected`, delete the `self._collecting = False` line if one is present — the `finally` now owns it. Apply the same `try/…/finally` shape to `_run_add_files`, `_run_connection_test`, `_run_email_test`, `_run_fetch_models` and `_run_bridge_start`, each clearing its own flag.

- [ ] **Step 4: Detect a dead WhatsApp bridge**

In `backend/controller.py`, replace the guard at the top of the bridge-start path:

```python
        if self._wa_starting:
            return
        if self._wa_proc is not None and self._wa_proc.poll() is None:
            return          # still running
        self._wa_proc = None  # it exited — allow a fresh attempt
```

- [ ] **Step 5: Verify nothing regressed**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py /tmp/marsad-shots2 2>&1 \
  | grep -E "QML ERROR:|ReferenceError|TypeError" || echo "no fatal QML errors"
```

Expected: `no fatal QML errors`.

- [ ] **Step 6: Commit**

```bash
git add backend/controller.py
git commit -m "fix(desktop): move SMTP off the GUI thread, never strand a guard flag

An unreachable SMTP host froze the whole window, and a blocked IMAP connect left
_collecting stuck True so the collect button silently did nothing for the rest
of the session. A dead node bridge no longer disables the link button forever."
```

---

### Task 14: Serialize the API's guard flags and result reads — DEFERRED

> **DEFERRED — do not implement.** The web API does not ship in this release
> (see "Release scope: desktop only"), and it now refuses to start without an
> explicit opt-in, so the concurrency it describes is unreachable for users.
> Recorded as a known limitation in `docs/RELEASE_CHECKLIST.md`. Skip to Task 15.

<details>
<summary>Original task text (for the release that ships the API)</summary>


Closes **M14** and the `_results` race.

**Files:**
- Modify: `api/services.py`
- Create: `tests/test_api_concurrency.py`

**Interfaces:**
- Produces: `AppService._claim(name: str) -> bool` — atomically tests and sets a guard flag under `self._lock`; returns `False` if it was already set.
- Produces: `AppService._release(name: str) -> None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_api_concurrency.py`:

```python
import threading
import unittest


class ClaimTests(unittest.TestCase):
    def test_only_one_caller_claims_a_flag(self):
        from api.services import AppService
        svc = AppService.__new__(AppService)        # no __init__ side effects
        svc._lock = threading.RLock()
        svc._busy = False

        results = []
        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()
            results.append(svc._claim("_busy"))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sum(1 for r in results if r), 1,
                         "more than one caller claimed the flag")

    def test_release_allows_a_later_claim(self):
        from api.services import AppService
        svc = AppService.__new__(AppService)
        svc._lock = threading.RLock()
        svc._busy = False
        self.assertTrue(svc._claim("_busy"))
        self.assertFalse(svc._claim("_busy"))
        svc._release("_busy")
        self.assertTrue(svc._claim("_busy"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_api_concurrency -v`
Expected: FAIL — `AttributeError: 'AppService' object has no attribute '_claim'`.

- [ ] **Step 3: Implement**

In `api/services.py`, add to `AppService`:

```python
    def _claim(self, name: str) -> bool:
        """Atomically test-and-set a guard flag.

        FastAPI runs sync endpoints concurrently in a threadpool, so the
        check-then-set pattern that is safe on Qt's single GUI thread is a race
        here: two POST /api/analysis/run calls could both start a full run."""
        with self._lock:
            if getattr(self, name):
                return False
            setattr(self, name, True)
            return True

    def _release(self, name: str) -> None:
        with self._lock:
            setattr(self, name, False)
```

Then rewrite each guarded entry point to use it. `run_analysis` becomes:

```python
    def run_analysis(self):
        if not self._reports:
            return False, "لا توجد تقارير للتحليل"
        if not self._claim("_busy"):
            return False, "التحليل قيد التشغيل بالفعل"
        threading.Thread(target=self._run_analysis, daemon=True).start()
        return True, ""
```

and its worker must end with `self._release("_busy")` in a `finally`. Apply the same pattern to `collect_reports` (`_collecting`), `add_files` (`_adding`), `test_engine` (`_testing_engine`), `test_email` (`_testing_email`), `fetch_models` (`_models_busy`) and `start_whatsapp_bridge` (`_wa_starting`). Delete the now-redundant unlocked re-checks inside each worker.

- [ ] **Step 4: Snapshot results before exporting**

In `api/services.py`, change `_export` so it reads `self._results` exactly once, under the lock:

```python
    def _export(self, fn, path, ext):
        """Returns (ok, path_or_error)."""
        with self._lock:
            results = dict(self._results)
        if not results:
            err = "لا توجد نتائج للتصدير — شغّل التحليل أولاً"
            self._emit("export_failed", error=err)
            return False, err
```

and use the local `results` for the rest of the method instead of `self._results`. Apply the same snapshot to `send_email_report`.

- [ ] **Step 5: Run it and watch it pass**

Run: `python3 -m unittest tests.test_api_concurrency -v && python3 tools/test_api.py`
Expected: both `OK`.

- [ ] **Step 6: Commit**

```bash
git add api/services.py tests/test_api_concurrency.py
git commit -m "fix(api): serialize guard flags and snapshot results

Two concurrent POST /api/analysis/run calls both passed the unlocked check and
started full runs, doubling model spend and interleaving writes to latest.json.
An export racing a dashboard clear could return an empty PDF as a 200."
```

---

</details>

---

### Task 15: Persist the WhatsApp token, save results atomically, and retry a failed receiver

Closes **M15** and **M17**.

**Files:**
- Modify: `connectors.py`, `core/engine.py`

**Interfaces:**
- Produces: `ConnectorHub.wa_token` is persisted to settings the first time it is generated.
- Produces: `ConnectorHub.start_whatsapp(port)` returns `bool` and leaves `self.whatsapp` as `None` when the bind fails, so the next attempt retries.

- [ ] **Step 1: Write the failing test**

Create `tests/test_whatsapp_receiver.py`:

```python
import socket
import unittest


class ReceiverLifecycleTests(unittest.TestCase):
    def test_failed_bind_leaves_no_half_built_receiver(self):
        import connectors
        blocker = socket.socket()
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        try:
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
        from tests._isolation import isolated_state
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
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_whatsapp_receiver -v`
Expected: both the half-built-receiver and the token-persistence tests FAIL.

- [ ] **Step 3: Implement the receiver lifecycle fix**

In `connectors.py`, change `WhatsAppReceiver.start` to report success and to leave nothing behind on failure:

```python
    def start(self) -> bool:
        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", self.port),
                                               self._make_handler())
        except OSError as e:
            self._log(f"تعذّر بدء المستقبِل على المنفذ {self.port}: {friendly_error(str(e))}")
            self._server = None
            return False
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._log(f"[WA] المستقبِل يعمل على 127.0.0.1:{self.port}")
        return True
```

Match the existing handler-construction call and logging helper names in the file.

Change `ConnectorHub.start_whatsapp` to only keep a receiver that actually listens:

```python
    def start_whatsapp(self, port: int) -> bool:
        self.stop_whatsapp()
        recv = WhatsAppReceiver(port, on_message=self._append,
                                dept_fn=self._wa_dept, logger=self._log_fn,
                                token=self.wa_token,
                                event_fn=self._event_fn)
        if not recv.start():
            self.whatsapp = None       # never keep a receiver that is not listening
            return False
        self.whatsapp = recv
        return True
```

Match the existing constructor keyword names exactly. Add a `stop_whatsapp()` method if one does not already exist:

```python
    def stop_whatsapp(self):
        if self.whatsapp:
            try:
                self.whatsapp.stop()
            except Exception:
                pass
            self.whatsapp = None
```

Make `WhatsAppReceiver.stop` join its thread:

```python
    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
```

- [ ] **Step 4: Persist the generated token**

In `connectors.py`, in `ConnectorHub.__init__`, replace the token line with:

```python
        self.wa_token = settings.get("whatsapp_token") or ""
        if not self.wa_token:
            self.wa_token = secrets.token_hex(16)
            settings["whatsapp_token"] = self.wa_token
            try:
                from backend.settings_bridge import save_settings
                save_settings(settings, changed_keys={"whatsapp_token"})
            except Exception as e:      # core must never hard-depend on backend
                log.warning(f"could not persist whatsapp_token: {e}")
```

- [ ] **Step 5: Make `_save` degrade instead of raising**

In `core/engine.py`, replace `_save` with:

```python
    def _save(self, results: dict):
        """Persisting must never destroy a completed analysis."""
        try:
            REPORTS.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            self._write_json(REPORTS / f"results_{ts}.json", results)
            self._write_json(REPORTS / "latest.json", results)
        except OSError as e:
            self.log(f"تعذّر حفظ النتائج: {friendly_error(str(e))}")

    @staticmethod
    def _write_json(path, payload):
        """Atomic write — a torn latest.json silently empties the dashboard."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
```

Add `import os` to `core/engine.py` if it is not already imported. The `%f` in the timestamp also stops two runs in the same second from overwriting each other.

- [ ] **Step 6: Run it and watch it pass**

Run: `python3 -m unittest tests.test_whatsapp_receiver -v`
Expected: 3 tests, `OK`.

- [ ] **Step 7: Commit**

```bash
git add connectors.py core/engine.py tests/test_whatsapp_receiver.py
git commit -m "fix(whatsapp): persist the token, retry a failed bind, save atomically

A regenerated token made the receiver 403 its own bridge with no log line, a
busy port left a non-listening receiver that blocked every retry, and
latest.json was written non-atomically."
```

---

### Task 16: Do not let a settings save corrupt a running analysis

Closes **M16**.

**Files:**
- Modify: `backend/controller.py`, `qml/SettingsPage.qml`, `connectors.py`

- [ ] **Step 1: Snapshot the engine settings per run**

In `backend/controller.py`, in `runAnalysis`, build the engine from a copy so a later save cannot change the provider mid-run:

```python
        engine = AgentsEngine(AIEngine(dict(self._settings)))
```

Import `AIEngine` alongside `AgentsEngine` if it is not already imported.

- [ ] **Step 2: Hand the buffered reports to the new hub**

In `backend/controller.py`, in `_rebuild_hub`, carry the pending WhatsApp reports across:

```python
    def _rebuild_hub(self):
        pending = []
        if self._hub:
            try:
                pending = self._hub.take_buffer()
            except Exception:
                pending = []
            try:
                self._hub.stop_all()
            except Exception:
                pass
        self._hub = ConnectorHub(self._settings)
        if pending:
            self._hub.extend_buffer(pending)
        self._start_whatsapp_if_enabled()
```

In `connectors.py`, add the two buffer methods to `ConnectorHub`:

```python
    def take_buffer(self) -> list:
        """Drain pending reports so a hub rebuild does not discard them."""
        with self._lock:
            pending, self._buffer = list(self._buffer), []
        return pending

    def extend_buffer(self, reports: list) -> None:
        with self._lock:
            self._buffer.extend(reports)
```

Use the file's existing buffer and lock attribute names.

- [ ] **Step 3: Disable saving during a run**

In `qml/SettingsPage.qml`, find the save button and add:

```qml
        enabled: !app.busy
```

and on the same page's footer note, show why when it is disabled:

```qml
            text: app.busy ? "التحليل قيد التشغيل — تعذّر الحفظ الآن"
                           : (pg.dirty ? "توجد تغييرات غير محفوظة" : "كل الإعدادات محفوظة")
```

Match the existing property and id names on that page.

- [ ] **Step 4: Verify**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py /tmp/marsad-shots3 2>&1 \
  | grep -E "QML ERROR:|ReferenceError|Unable to assign" || echo "settings page still loads"
```

Expected: `settings page still loads`.

- [ ] **Step 5: Commit**

```bash
git add backend/controller.py connectors.py qml/SettingsPage.qml
git commit -m "fix(desktop): isolate a running analysis from settings changes

Saving mid-run switched provider between agents and rebuilt the connector hub,
silently discarding WhatsApp reports that had arrived but not been collected."
```

---

### Task 17: Give each WebSocket client a single writer — DEFERRED

> **DEFERRED — do not implement.** Same reason as Task 14: the web API does not
> ship in this release and refuses to start without an explicit opt-in. Recorded
> as a known limitation in `docs/RELEASE_CHECKLIST.md`. Skip to Task 18.

<details>
<summary>Original task text (for the release that ships the API)</summary>


Closes **M18**.

**Files:**
- Modify: `api/app.py`

- [ ] **Step 1: Implement the per-client queue**

In `api/app.py`, replace the `WSManager` class with:

```python
class WSManager:
    """One queue and one writer task per client.

    Previously every service event scheduled its own send task, so ordering was
    not preserved and two tasks could sit inside send_text on the same socket —
    which Starlette does not support, and the loser dropped the client."""

    def __init__(self):
        self.queues = {}        # WebSocket -> asyncio.Queue
        self.loop = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.queues[ws] = asyncio.Queue(maxsize=1000)

    def disconnect(self, ws: WebSocket):
        self.queues.pop(ws, None)

    async def writer(self, ws: WebSocket):
        queue = self.queues.get(ws)
        if queue is None:
            return
        while True:
            event = await queue.get()
            if event is None:
                return
            try:
                await ws.send_text(json.dumps(event, ensure_ascii=False))
            except Exception:
                self.disconnect(ws)
                return

    def broadcast(self, event: dict):
        for ws, queue in list(self.queues.items()):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self.disconnect(ws)
```

- [ ] **Step 2: Run the writer alongside the reader**

In the `/ws` endpoint, after the token check and `await ws_manager.connect(ws)`, start the writer and keep the existing receive loop:

```python
    writer_task = asyncio.create_task(ws_manager.writer(ws))
    try:
        await ws_manager.queues[ws].put(service.snapshot_event())
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(ws)
        writer_task.cancel()
```

Use whatever the existing code calls its initial `state_snapshot` payload builder in place of `service.snapshot_event()`.

- [ ] **Step 3: Replace the fan-out call**

Change `_broadcast_from_service` so it hands the event to the queues on the loop thread rather than scheduling a task per event:

```python
def _broadcast_from_service(event: dict):
    loop = ws_manager.loop
    if loop is None:
        return
    loop.call_soon_threadsafe(ws_manager.broadcast, event)
```

- [ ] **Step 4: Replace the deprecated startup hook**

Replace the `@app.on_event("startup")` handler with a lifespan context manager, which also gives the API the shutdown hook it never had:

```python
import contextlib


@contextlib.asynccontextmanager
async def lifespan(_app):
    ws_manager.loop = asyncio.get_running_loop()
    service.subscribe(_broadcast_from_service)
    try:
        yield
    finally:
        service.shutdown()


app = FastAPI(title="marsad API", docs_url="/api/docs", lifespan=lifespan)
```

Move this above the `app = FastAPI(...)` line and delete the old `@app.on_event("startup")` function. Use the existing subscription call in place of `service.subscribe(...)` if it is named differently.

- [ ] **Step 5: Add the service shutdown**

In `api/services.py`, add:

```python
    def shutdown(self):
        """Called from the FastAPI lifespan — the Qt app has an atexit
        equivalent, the API had nothing, so the node bridge outlived it."""
        try:
            self.stop_whatsapp_bridge()
        except Exception:
            pass
        try:
            self._hub.stop_all()
        except Exception:
            pass
```

- [ ] **Step 6: Verify**

Run: `python3 tools/test_api.py && python3 -m unittest tests.test_api_auth -v`
Expected: both `OK`.

- [ ] **Step 7: Commit**

```bash
git add api/app.py api/services.py
git commit -m "fix(api): one writer per websocket client, add a shutdown hook

Concurrent send_text on one socket dropped clients mid-analysis and event order
was not preserved. Replaces the deprecated on_event startup hook with lifespan,
which finally gives the API somewhere to stop the node bridge."
```

---

</details>

---

# Phase 4 — Interface

### Task 18: Put the RTL markers on the correct edge

Closes **M19**.

**Files:**
- Modify: `qml/Main.qml:52-55`, `qml/Main.qml:109-114`, `qml/Main.qml:116-119`

- [ ] **Step 1: Confirm the mirroring behaviour**

```bash
QT_QPA_PLATFORM=offscreen python3 - <<'EOF'
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QTimer
import sys, tempfile, os
qml = '''
import QtQuick
Item {
  width: 200; height: 40
  LayoutMirroring.enabled: true
  LayoutMirroring.childrenInherit: true
  Rectangle { anchors.fill: parent; color: "white" }
  Rectangle { width: 10; height: 40; color: "black"; anchors.left: parent.left }
}
'''
p = os.path.join(tempfile.mkdtemp(), "t.qml")
open(p, "w").write(qml)
app = QApplication(sys.argv)
v = QQuickView(); v.setSource(QUrl.fromLocalFile(p)); v.show()
def check():
    img = v.grabWindow()
    print("anchors.left under mirroring paints at:",
          "RIGHT" if img.pixelColor(195, 20).value() < 128 else "LEFT")
    app.quit()
QTimer.singleShot(400, check)
app.exec()
EOF
```

Expected: `anchors.left under mirroring paints at: RIGHT`. So an `anchors.left` written to mean "the visual left" lands on the right, and vice-versa.

- [ ] **Step 2: Fix the sidebar hairline**

In `qml/Main.qml`, the hairline is commented as being on the inner, content-facing edge. Under mirroring, `anchors.left` puts it on the outer window edge. Change it to:

```qml
        // hairline on the inner (content-facing) edge — anchors are mirrored by
        // LayoutMirroring, so `right` here is the visual left of the sidebar
        Rectangle {
            width: 1
            color: Theme.colors.border
            anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        }
```

- [ ] **Step 3: Fix the active-item marker**

The nav marker is commented as the leading edge (right in RTL) but renders on the left. Change it to:

```qml
            // leading-edge marker (visually right in RTL — anchors are mirrored)
            Rectangle {
                visible: nav.currentIndex === index
                width: 3; height: parent.height * 0.55
                radius: 1.5
                color: Theme.colors.accent
                anchors { left: parent.left; leftMargin: 6
                          verticalCenter: parent.verticalCenter }
            }
```

- [ ] **Step 4: Fix the swapped gutters**

In the same delegate, the row's margins are reversed by mirroring. Swap them so the leading gutter is the wider one again:

```qml
                anchors { fill: parent; leftMargin: 20; rightMargin: 14 }
```

- [ ] **Step 5: Verify visually**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py /tmp/marsad-rtl
```

Open `/tmp/marsad-rtl/2-dashboard.png` and confirm the teal marker on the active nav item is now on the **right** edge of the pill (the side nearest the page content is the left; the leading edge in RTL is the right), and the sidebar hairline separates the sidebar from the content rather than hugging the window edge.

- [ ] **Step 6: Commit**

```bash
git add qml/Main.qml
git commit -m "fix(ui): stop double-mirroring the sidebar hairline and nav marker

LayoutMirroring already flips anchors, so the hand-written RTL anchors landed
on the opposite edge from what their own comments described."
```

---

### Task 19: Fix the clipped, overlapped and silently-truncated widgets

Closes the save-bar overlap, the `EmptyState` overflow, the modal scrim and the no-op elision.

**Files:**
- Modify: `qml/SettingsPage.qml`, `qml/ReportsPage.qml`, `qml/Main.qml`, `qml/InputPage.qml`

- [ ] **Step 1: Stop the sticky save bar covering the last field**

In `qml/SettingsPage.qml`, the scrollable content must reserve the footer's height. Add to the `Flickable` (or `ScrollView`) that wraps the form:

```qml
        bottomMargin: 72     // clears the sticky save bar (60px + hairline + air)
```

If the page uses a `ColumnLayout` inside the flickable, add instead:

```qml
            Item { Layout.fillWidth: true; Layout.preferredHeight: 72 }
```

as the final child.

- [ ] **Step 2: Let the Reports empty state size itself**

In `qml/ReportsPage.qml`, replace the fixed height on the `EmptyState`:

```qml
            Layout.preferredHeight: 160
```

with

```qml
            Layout.preferredHeight: implicitHeight
            Layout.minimumHeight: implicitHeight
```

- [ ] **Step 3: Make the modal dimmer actually modal**

In `qml/Main.qml`, the WhatsApp scrim is declared inside the content `Item`, so it never covers the 256px sidebar. Move the scrim `Rectangle` and the dialog it dims out of the content item and make them the last children of the window's root item, so they paint above everything:

```qml
    // ── modal layer — last child of root so it covers the sidebar too ──
    Rectangle {
        id: waScrim
        anchors.fill: parent
        color: "#66000000"
        visible: app.waDialogOpen
        z: 100
        TapHandler { onTapped: app.closeWhatsAppQr() }
    }
```

and give the dialog panel `z: 101` with `anchors.centerIn: parent`. Keep every existing child of the panel unchanged.

- [ ] **Step 4: Make truncation show an ellipsis**

Qt only elides multi-line text with `ElideRight`. At each of these five sites, change `elide: Text.ElideLeft` to `elide: Text.ElideRight`:

- `qml/InputPage.qml:113`
- `qml/ReportsPage.qml:83`
- `qml/ReportsPage.qml:104`
- `qml/SettingsPage.qml:286`
- `qml/SettingsPage.qml:324`

Leave the single-line `ElideLeft` uses on file paths and emails alone — those legitimately want the tail kept.

- [ ] **Step 5: Verify**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py /tmp/marsad-ui 2>&1 \
  | grep -E "QML ERROR:|ReferenceError|Unable to assign" || echo "all pages load"
```

Expected: `all pages load`. Then open `/tmp/marsad-ui/4-settings.png` and confirm the model-name field is fully visible above the save bar, and `/tmp/marsad-ui/3-reports.png` and confirm the empty state is not clipped.

- [ ] **Step 6: Commit**

```bash
git add qml/
git commit -m "fix(ui): save bar no longer covers the last field; empty state fits

Also makes the WhatsApp dialog genuinely modal (the scrim never covered the
sidebar) and restores the ellipsis on five truncated labels — ElideLeft is a
no-op on wrapped text."
```

---

### Task 20: Finish the interface pass

Closes the dashboard action-row layout, the missing busy feedback, the un-handled `analysisDone`, and the typographic-consistency item that replaced the font blocker.

**Files:**
- Modify: `qml/DashboardPage.qml`, `qml/InputPage.qml`, `qml/Main.qml`, `backend/theme.py`

- [ ] **Step 1: Group the action number with its action**

In `qml/DashboardPage.qml`, the ordered-action delegate currently lets the number and the title drift to opposite edges. Give the row a leading number column and let the text take the remaining width:

```qml
        RowLayout {
            width: parent.width
            spacing: 12

            Text {                       // the ordinal, pinned to the leading edge
                text: pg.arabicNumber(index + 1)
                font.family: Theme.fonts.body
                font.pixelSize: Theme.fs.title
                color: Theme.colors.accent
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: 24
                horizontalAlignment: Text.AlignRight
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: modelData.action || ""
                    font.family: Theme.fonts.body
                    font.pixelSize: Theme.fs.body
                    color: Theme.colors.ink
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                }
                Text {
                    text: [modelData.owner, modelData.deadline, modelData.impact]
                          .filter(function (p) { return !!p }).join("  ·  ")
                    font.family: Theme.fonts.body
                    font.pixelSize: Theme.fs.small
                    color: Theme.colors.ink3
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                }
            }
        }
```

Use the page's existing helper for Arabic-Indic numerals in place of `pg.arabicNumber` if it is named differently, and the existing model property names.

- [ ] **Step 2: Give the collect button a busy state**

In `qml/InputPage.qml`, on the «جمع من المصادر» button add:

```qml
            enabled: !app.collecting
            label: app.collecting ? "جارٍ الجمع…" : "جمع من المصادر"
```

Use the button's actual text property name. In `backend/controller.py`, expose the flag as a notifying property next to the others:

```python
    collectingChanged = Signal()

    @Property(bool, notify=collectingChanged)
    def collecting(self):
        return self._collecting
```

and emit `collectingChanged` wherever `_collecting` is set or cleared — including the `finally` added in Task 13. Introduce a small setter to keep that in one place:

```python
    def _set_collecting(self, value: bool):
        if self._collecting != value:
            self._collecting = value
            self.collectingChanged.emit()
```

and use `self._set_collecting(True/False)` at every site.

- [ ] **Step 3: Go to the dashboard when the analysis finishes**

In `qml/Main.qml`, inside the existing `Connections { target: app … }` block, add:

```qml
        function onAnalysisDone() { root.currentIndex = 2 }   // لوحة التحكم
```

Confirm index 2 is the dashboard in this file's page order before committing; use the correct index if it differs.

- [ ] **Step 4: Keep punctuation in the family that has it**

The audit's font finding is downgraded — Qt falls back per glyph, so `←`, `·`, `…` and `—` do render. They render from a *different* family, which is a consistency problem, not a correctness one. Reduce the mismatch where it is most visible, the permanent sidebar date, by switching its separator to a character both bundled Arabic families contain (verified: U+060C `،` and U+061B `؛` are present in all six):

In `core/hijri.py`, change `dual_label` to join with an Arabic comma:

```python
    return f"{hijri_label(date)}، {date.isoformat()}"
```

Leave the em dashes and ellipses as they are — they fall back cleanly and reading them as `-` or `...` would be worse typography.

- [ ] **Step 5: Update the hijri test**

In `tests/`, create `tests/test_hijri.py`:

```python
import datetime
import unittest

from core.hijri import dual_label, gregorian_to_hijri, hijri_label


class HijriTests(unittest.TestCase):
    def test_known_conversions(self):
        self.assertEqual(gregorian_to_hijri(2000, 1, 1), (1420, 9, 24))
        self.assertEqual(gregorian_to_hijri(2023, 3, 23), (1444, 9, 1))

    def test_labels(self):
        self.assertEqual(hijri_label(datetime.date(2000, 1, 1)), "٢٤ رمضان ١٤٢٠ هـ")
        self.assertEqual(hijri_label(datetime.date(2023, 3, 23)), "١ رمضان ١٤٤٤ هـ")

    def test_dual_label_uses_a_bundled_separator(self):
        label = dual_label(datetime.date(2023, 3, 23))
        self.assertEqual(label, "١ رمضان ١٤٤٤ هـ، 2023-03-23")
        self.assertNotIn("·", label)

    def test_dual_label_today_ends_with_the_iso_date(self):
        self.assertTrue(dual_label().endswith(datetime.date.today().isoformat()))


if __name__ == "__main__":
    unittest.main()
```

Run: `python3 -m unittest tests.test_hijri -v`
Expected: 4 tests, `OK`.

- [ ] **Step 6: Verify the pages still render**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py /tmp/marsad-ui2 2>&1 \
  | grep -E "QML ERROR:|ReferenceError|Unable to assign" || echo "all pages load"
```

Expected: `all pages load`.

- [ ] **Step 7: Commit**

```bash
git add qml/ backend/controller.py core/hijri.py tests/test_hijri.py
git commit -m "feat(ui): readable action rows, busy feedback, auto-navigate on finish

Also switches the sidebar date separator to an Arabic comma, which both bundled
Arabic families contain, so the most visible string no longer falls back to a
different typeface."
```

---

# Phase 5 — Ingestion, errors, docs, release

### Task 21: Route files to the right department

Closes the substring-matching defect and the two Arabic keyword typos.

**Files:**
- Create: `tests/test_connectors_ingest.py`
- Modify: `connectors.py` (`guess_dept`)

- [ ] **Step 1: Write the failing test**

Create `tests/test_connectors_ingest.py`:

```python
import datetime
import json
import tempfile
import unittest
from pathlib import Path

import connectors
from connectors import guess_dept, is_internal_file, read_file_to_report

ARABIC = "أنجز فريق الموقع ٨٠٪ من أعمال الحفر اليوم"


class GuessDeptTests(unittest.TestCase):
    def test_english_keywords(self):
        self.assertEqual(guess_dept("ran_daily.docx"), "ran")
        self.assertEqual(guess_dept("core_network.csv"), "core")
        self.assertEqual(guess_dept("quality_sites.xlsx"), "quality")
        self.assertEqual(guess_dept("safety_site.pdf"), "safety")

    def test_ran_does_not_match_inside_ordinary_words(self):
        for name in ("random_stuff.txt", "transfer_log.txt",
                     "grant_letter.txt", "France_visit.txt"):
            with self.subTest(name=name):
                self.assertEqual(guess_dept(name), "admin")

    def test_normal_arabic_spellings_are_recognised(self):
        self.assertEqual(guess_dept("تكاليف_المشروع.xlsx"), "cost")
        self.assertEqual(guess_dept("إنشاء_الأبراج.docx"), "civil")
        self.assertEqual(guess_dept("تقرير_الجودة.pdf"), "quality")
        self.assertEqual(guess_dept("السلامة_اليومي.txt"), "safety")

    def test_unknown_falls_back_to_admin(self):
        self.assertEqual(guess_dept("notes.txt"), "admin")


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_every_supported_format_round_trips(self):
        import docx, openpyxl
        from reportlab.pdfgen import canvas

        d = docx.Document(); d.add_paragraph(ARABIC); d.save(self.dir / "ran_daily.docx")
        wb = openpyxl.Workbook(); wb.active.append(["البند", ARABIC])
        wb.save(self.dir / "quality_sites.xlsx")
        (self.dir / "core_network.csv").write_text(
            f"القسم,الحالة\nالنواة,{ARABIC}\n", encoding="utf-8")
        (self.dir / "تقرير_الجودة.txt").write_text(ARABIC, encoding="utf-8")
        (self.dir / "plain.json").write_text(
            json.dumps({"ملاحظة": ARABIC}, ensure_ascii=False), encoding="utf-8")
        c = canvas.Canvas(str(self.dir / "safety_site.pdf"))
        c.drawString(72, 720, "RAN site safety inspection completed")
        c.save()

        today = datetime.date.today().isoformat()
        for name, dept in (("ran_daily.docx", "ran"),
                           ("quality_sites.xlsx", "quality"),
                           ("core_network.csv", "core"),
                           ("تقرير_الجودة.txt", "quality"),
                           ("plain.json", "admin"),
                           ("safety_site.pdf", "safety")):
            with self.subTest(name=name):
                rep = read_file_to_report(self.dir / name)
                self.assertIsNotNone(rep)
                self.assertEqual(set(rep),
                                 {"id", "source", "dept", "from", "date", "content"})
                self.assertEqual(rep["source"], "upload")
                self.assertEqual(rep["date"], today)
                self.assertEqual(rep["dept"], dept)

    def test_empty_file_is_rejected(self):
        (self.dir / "empty.txt").write_text("", encoding="utf-8")
        self.assertIsNone(read_file_to_report(self.dir / "empty.txt"))

    def test_internal_files_can_never_be_ingested(self):
        from core.paths import BUNDLE_DIR, DATA_DIR
        for path in (DATA_DIR / "settings.json",
                     BUNDLE_DIR / "settings.example.json",
                     DATA_DIR / "data" / "contacts.json",
                     DATA_DIR / "reports" / "latest.json"):
            with self.subTest(path=path.name):
                self.assertTrue(is_internal_file(path))
                self.assertIsNone(read_file_to_report(path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest tests.test_connectors_ingest -v`
Expected: `test_ran_does_not_match_inside_ordinary_words` FAILS (`'ran' != 'admin'`) and `test_normal_arabic_spellings_are_recognised` FAILS on `تكاليف` and `إنشاء`.

- [ ] **Step 3: Implement**

In `connectors.py`, replace `guess_dept` with:

```python
_DEPT_KEYWORDS = (
    # (keyword, dept) — order matters: the first match wins
    ("ran", "ran"), ("radio", "ran"), ("راديو", "ran"),
    ("core", "core"), ("network", "core"), ("النواة", "core"),
    ("quality", "quality"), ("جودة", "quality"),
    ("safety", "safety"), ("سلامة", "safety"),
    ("civil", "civil"), ("انشاء", "civil"), ("إنشاء", "civil"), ("مدني", "civil"),
    ("cost", "cost"), ("finance", "cost"), ("تكاليف", "cost"), ("تكلفة", "cost"),
    ("مالية", "cost"), ("ميزانية", "cost"),
    ("contract", "contract"), ("عقود", "contract"), ("عقد", "contract"),
    ("procure", "procure"), ("purchase", "procure"), ("مشتريات", "procure"),
    ("supply", "supply"), ("warehouse", "supply"), ("مخازن", "supply"),
    ("توريد", "supply"),
    ("schedule", "schedule"), ("جدول", "schedule"), ("زمني", "schedule"),
    ("ops", "ops"), ("operations", "ops"), ("عمليات", "ops"),
)

# Latin keywords must match whole words: "ran" inside "random"/"transfer"/
# "grant"/"France" used to route unrelated files to the RAN department.
_WORD_SPLIT = re.compile(r"[^0-9a-z؀-ۿ]+")


def guess_dept(filename: str) -> str:
    """محاولة تخمين القسم من اسم الملف"""
    stem = str(filename).lower()
    tokens = set(_WORD_SPLIT.split(stem)) - {""}
    for keyword, dept in _DEPT_KEYWORDS:
        if keyword.isascii():
            if keyword in tokens:
                return dept
        elif keyword in stem:          # Arabic: affixes make whole-word matching wrong
            return dept
    return "admin"
```

Add `import re` to `connectors.py` if it is not already imported.

- [ ] **Step 4: Run it and watch it pass**

Run: `python3 -m unittest tests.test_connectors_ingest -v`
Expected: 8 tests, `OK`.

- [ ] **Step 5: Commit**

```bash
git add connectors.py tests/test_connectors_ingest.py
git commit -m "fix(ingest): whole-word Latin matching and correct Arabic keywords

'ran' matched inside random/transfer/grant/France, and the cost keyword was
misspelled تكالف so ordinary تكاليف files fell through to admin, as did the
normal hamza spelling إنشاء."
```

---

### Task 22: Show Arabic errors, not Python exceptions

Closes **M20**.

**Files:**
- Modify: `api/services.py`, `backend/controller.py`

- [ ] **Step 1: Find every raw leak**

```bash
grep -n "str(e)" api/services.py backend/controller.py | grep -v friendly_error
```

Expected: roughly ten hits in `api/services.py` and several in `backend/controller.py`.

- [ ] **Step 2: Import the classifier**

At the top of `api/services.py` and `backend/controller.py` add:

```python
from core.errors import friendly_error
```

- [ ] **Step 3: Replace every user-facing leak**

For each hit from Step 1, wrap the message and log the raw detail. The pattern, applied at each site:

```python
        except Exception as e:
            log.warning("export failed: %s", e, exc_info=True)   # raw detail → logs
            self._emit("export_failed", error=friendly_error(str(e)))
            self._emit("notify", message=f"تعذّر التصدير: {friendly_error(str(e))}")
            return False, friendly_error(str(e))
```

In `backend/controller.py` the equivalent export handler becomes:

```python
        except Exception as e:
            log.warning("export failed: %s", e, exc_info=True)
            msg = friendly_error(str(e))
            self.exportFailed.emit(msg)
            self.notify.emit(f"تعذّر التصدير: {msg}")
```

If `backend/controller.py` has no module logger, add one next to the imports:

```python
import logging
log = logging.getLogger(__name__)
```

Do **not** wrap messages that are already Arabic literals — `friendly_error` passes Arabic through unchanged, but wrapping adds noise.

- [ ] **Step 4: Verify no leaks remain**

```bash
grep -n "str(e)" api/services.py backend/controller.py | grep -v friendly_error \
  && echo "STILL LEAKING" || echo "all user-facing errors classified"
```

Expected: `all user-facing errors classified`.

- [ ] **Step 5: Prove it end to end**

```bash
python3 - <<'EOF'
from core.errors import friendly_error
for raw in ("No module named 'arabic_reshaper'",
            "[Errno 111] Connection refused",
            "HTTP 401: {\"error\":\"invalid key\"}",
            "timed out"):
    print(f"{raw[:44]:46s} -> {friendly_error(raw)}")
EOF
```

Expected: every line maps to a short Arabic message.

- [ ] **Step 6: Commit**

```bash
git add api/services.py backend/controller.py
git commit -m "fix(ux): classify user-facing errors into Arabic

AGENTS.md and PROJECT_DEFINITION both state this as an invariant, but neither
the controller nor the API service imported friendly_error, so raw English
exception text reached an Arabic-only UI."
```

---

### Task 23: Make the documentation true

Closes **M21**, **M22** and the documentation minors.

**Files:**
- Modify: `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_DEFINITION.md`

- [ ] **Step 1: List every false claim**

```bash
grep -rn "web/" README.md AGENTS.md docs/PROJECT_DEFINITION.md | head -30
grep -n "no copies are made\|No test suite\|no linter" README.md AGENTS.md CLAUDE.md
```

Expected: the `web/` build commands, the "Complete" status row, the "kept on disk" sentence, the uploads privacy claim, and the "no test suite" assertions.

- [ ] **Step 2: Remove the `web/` frontend from the docs**

The `web/` directory does not exist on disk or in any commit. In `AGENTS.md`, delete the entire `web/` section (the build commands and the "kept on disk for reference" sentence) and remove `web/` from the architecture tree. In `docs/PROJECT_DEFINITION.md`, delete the `web/` row from the repo-layout table, remove `web/` from the architecture map, and change the §12 status row to:

```
| Web frontend | **Not built.** Cancelled 2026-07; no `web/` tree exists in the repo or its history. The API serves JSON only. |
```

In `README.md`, remove any instruction to build the web UI.

- [ ] **Step 3: Correct the uploads privacy claim**

In `README.md`, replace the "Data & privacy" sentence about uploads with:

```
Uploaded files picked in the desktop app are read in place from wherever you
picked them — no copies are made. The optional web API is different: files sent
to `POST /api/reports/files` are saved under `uploads/api_<timestamp>/` and kept
there until you delete them.
```

- [ ] **Step 4: Correct the test-suite claims**

In `AGENTS.md` and `CLAUDE.md`, replace "No test suite and no linter exist in this project. Verification is manual." with:

```
Tests: `python3 -m unittest discover -s tests -v` runs the unit suite (stdlib
unittest, no extra dependency). `python3 tools/test_api.py` runs the REST smoke
suite. There is no linter. Every test isolates writable state via
`tests/_isolation.isolated_state()` — never point a test at the real
`settings.json`, `reports/` or `data/`.
```

- [ ] **Step 5: Document the API token**

In `README.md`, in the Web API section, add:

```
The API requires a local token. It is generated on first start, stored in
`settings.json` as `api_token`, and printed when the server starts. Send it as
`X-Marsad-Token: <token>` on every `/api/*` request and as `?token=<token>` on
`/ws`. The server binds `127.0.0.1`, rejects any non-loopback `Host`, and
rejects any request carrying an `Origin` header — so no web page can drive it.
```

- [ ] **Step 6: Add the missing dept key**

In `docs/PROJECT_DEFINITION.md` §6.3, add `ops` to the fixed department vocabulary list — `core/contacts.py` defines it (`إدارة العمليات` → `ops`) and the connectors use it.

- [ ] **Step 7: Bring CLAUDE.md up to date with the API layer**

In `CLAUDE.md`, add to the architecture section:

```
**`api/`** — a Qt-free FastAPI mirror of `AppController` (`app.py` routes,
`services.py` the controller equivalent, `__main__.py` the entry point). It
shares every state file with the desktop app, so do not run both against the
same `DATA_DIR` at once. `run_api.py` + `marsad_api.spec` package it.
`core/errors.py::friendly_error()` classifies raw errors into short Arabic and
must be used for anything a user will read.
```

- [ ] **Step 8: Verify no dangling references remain**

```bash
grep -rn "cd web\|web/dist\|npm run build" README.md AGENTS.md docs/PROJECT_DEFINITION.md \
  && echo "STILL REFERENCES web/" || echo "docs clean"
```

Expected: `docs clean`.

- [ ] **Step 9: Commit**

```bash
git add README.md AGENTS.md CLAUDE.md docs/PROJECT_DEFINITION.md
git commit -m "docs: remove the web/ frontend that never existed, fix false claims

PROJECT_DEFINITION listed it as Complete and AGENTS gave build commands for a
directory absent from every commit. Also corrects the uploads privacy claim,
the 'no test suite' note, and documents the new API token."
```

---

### Task 24: Full verification and release preparation

**Files:**
- Create: `docs/RELEASE_CHECKLIST.md`
- Modify: none

- [ ] **Step 1: Run the whole suite**

```bash
python3 -m unittest discover -s tests -v
python3 tools/test_api.py
```

Expected: both `OK`, zero failures, zero errors.

- [ ] **Step 2: Render every page**

```bash
QT_QPA_PLATFORM=offscreen timeout 180 python3 tools/capture_qt.py docs/screenshots
ls -l docs/screenshots
```

Expected: six PNGs, each over 20 KB, no `QML ERROR` on stderr.

- [ ] **Step 3: Confirm the security fixes hold**

```bash
python3 - <<'EOF'
import ssl, connectors
assert connectors.SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED
assert connectors.SSL_CONTEXT.check_hostname
print("TLS verification: ON")
EOF

python3 - <<'EOF'
from fastapi.testclient import TestClient
from api.app import app, service, SECRET_KEYS
c = TestClient(app, base_url="http://127.0.0.1")
assert c.get("/api/meta").status_code == 401, "API is not authenticated"
c.headers.update({"X-Marsad-Token": service.api_token})
body = c.get("/api/settings").json()
assert all(body.get(k, "") == "" for k in SECRET_KEYS), "secrets still exposed"
print("API auth: ON, secrets: redacted")
EOF

python3 - <<'EOF'
from connectors import build_report_html
html = build_report_html({"chief": {"overall_health": "جيد",
    "executive_summary": '<img src=x onerror="alert(1)">', "kpis": [],
    "top_actions": [], "dept_scores": [], "achievements": []}})
assert "onerror=" not in html, "HTML email still injectable"
print("email HTML: escaped")
EOF
```

Expected: three confirmation lines.

- [ ] **Step 4: Confirm both bundles build**

```bash
python3 -m pip install pyinstaller
pyinstaller --noconfirm marsad.spec 2>&1 | tail -5
ls dist/
```

Expected: it completes without a `datas` error and `dist/` contains `marsad/`.
The API bundle is **not** built — the web API does not ship in this release.

- [ ] **Step 5: Confirm no secret is tracked**

```bash
git ls-files | grep -E "settings\.json$|contacts\.json$|^reports/|^logs/|^uploads/" \
  && echo "SECRET TRACKED - STOP" || echo "no secrets tracked"
git status --porcelain
```

Expected: `no secrets tracked`, and a clean or intentional working tree.

- [ ] **Step 6: Write the release checklist**

Create `docs/RELEASE_CHECKLIST.md`:

```markdown
# Release checklist — مرصد

Run this before tagging any version.

## Automated
- [ ] `python3 -m unittest discover -s tests -v` — all pass
- [ ] `python3 tools/test_api.py` — all pass
- [ ] `QT_QPA_PLATFORM=offscreen python3 tools/capture_qt.py docs/screenshots` — six PNGs, no `QML ERROR`
- [ ] `pyinstaller --noconfirm marsad.spec` — completes
- [ ] `pyinstaller --noconfirm marsad_api.spec` — completes
- [ ] `git ls-files | grep -E "settings\.json$|contacts\.json$|^reports/"` — no output

## Manual, on a clean machine
- [ ] Fresh `pip install -r requirements.txt` in an empty virtualenv, then `python app.py` starts
- [ ] Settings page: enter a provider key, "اختبار المحرّك" reports success
- [ ] Input page: upload one `.docx`, one `.xlsx` and one `.pdf` — all three appear with the right department
- [ ] Run an analysis end to end against a real model — the dashboard fills and the app navigates to it
- [ ] Export PDF and Excel — both open, Arabic reads right-to-left, no `%%` or `None%`
- [ ] Email the report to a real address — it arrives and renders
- [ ] Link WhatsApp, send one group message, collect — it appears as a report
- [ ] Close the window mid-analysis — the process exits cleanly, no crash dialog

## Known accepted limitations to state in the release notes
- **The web API does not ship in this release.** `api/` remains in the tree but
  refuses to start without `MARSAD_API_ENABLE=1`. It is experimental,
  unauthenticated, and not hardened. Two known defects are deferred with it:
  its guard flags are not lock-protected (two concurrent analysis requests can
  both start), and its WebSocket fan-out schedules one send task per event
  (ordering is not preserved and a client can be dropped mid-run).
- Running the desktop app and the web API against the same data directory at the
  same time is not supported (no cross-process locking).
- Department creation and employee editing are not available in the Contacts UI;
  the seeded default org structure is what ships.
```

- [ ] **Step 7: Commit**

```bash
git add docs/RELEASE_CHECKLIST.md docs/screenshots
git commit -m "docs: add the release checklist and refresh screenshots"
```

- [ ] **Step 8: Push the branch**

```bash
git push -u origin fix/launch-readiness
```

**Do not create or move any tag, and do not publish a release.** The user has withheld that permission; tagging is a separate decision once this branch is reviewed and merged.

---

## Self-review

**Spec coverage.** Every blocker and major from the audit maps to a task: BLOCKER-1→T2, BLOCKER-2→T5, BLOCKER-3→T4, BLOCKER-4→T4, BLOCKER-5→downgraded, handled in T20 Step 4, BLOCKER-6→T3. M1→T6, M2→T1, M3→T7, M4→T7, M5→T8, M6→T8, M7→T8+T11, M8→T9, M9→T10, M10→T9, M11→T12, M12→T2+T13, M13→T13, M14→T14, M15→T15, M16→T16, M17→T15, M18→T17, M19→T18, M20→T22, M21→T23, M22→T23. Minors covered: Arabic keyword typos and substring matching (T21), `_save` raising and non-atomic writes (T15), `export_excel` not creating its directory (T8), deprecated `on_event` and the missing API shutdown (T17), the QThread leak (T12), the elide no-op, empty-state overflow and non-modal scrim (T19), `analysisDone` unhandled (T20), the `ops` dept key and the "no test suite" claims (T23).

**Deliberately deferred**, with a line in the release notes rather than code: full cross-process locking between the desktop app and the API (T15 removes the token divergence and the silent port failure, which were the parts that actually bit); department creation UI in ContactsPage (the default structure makes the page usable); employee editing; the Gemini key moving from query string to `x-goog-api-key`; and the ERP watcher's filename-only dedup, since `start_all` has no caller today.

**Type consistency.** `save_settings(settings, changed_keys=None)` from T1 is used with that exact signature in T5, T15 and T16. `_num`/`_int`/`_pct`/`_rows`/`_obj` from T8 are reused in T11. `core.status.tier()` from T9 is consumed by the exporters, the connectors and the theme. `AppService._claim`/`_release` from T14 are used across every guarded entry point. `tests._isolation.isolated_state()` from T1 is used in T3, T15 and elsewhere.
