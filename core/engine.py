"""
marsad core engine — AI backend + agent fleet.

UI-agnostic: no Tkinter/Qt imports. Extracted verbatim from the original app.py
(only AgentsEngine.run_all gains an optional per-agent callback so a UI can show
live agent state). The `results` dict keyed by agent id is the contract every
consumer (exporters, dashboard) reads.
"""
import json
import datetime

from .paths import DATA_DIR
from .errors import friendly_error

BASE_DIR = DATA_DIR
REPORTS  = DATA_DIR / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


# ════════════════════════════════════════════════════
# محرك الذكاء الاصطناعي — يدعم Ollama و Claude
# ════════════════════════════════════════════════════
class AIEngine:
    def __init__(self, settings):
        self.settings = settings

    def ask(self, system_prompt: str, user_text: str) -> dict:
        """استدعاء نموذج الذكاء الاصطناعي وإرجاع dict"""
        backend = self.settings.get("ai_backend", "ollama")
        return {
            "claude": self._ask_claude,
            "openai": self._ask_openai,
            "gemini": self._ask_gemini,
            "azure":  self._ask_azure,
        }.get(backend, self._ask_ollama)(system_prompt, user_text)

    @staticmethod
    def _bad_scheme(url: str) -> dict | None:
        """يرفض أي مخطط غير http/https قبل الطلب — يُعيد {"error":…} عند الرفض وNone عند القبول."""
        if not url.lower().startswith(("http://", "https://")):
            return {"error": f"رابط غير مدعوم (http/https فقط): {url}", "status": None}
        return None

    @staticmethod
    def _http_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
        """POST JSON، أعِد رداً مُفكَّكاً أو {"error":…}. لا يرفع استثناء أبداً."""
        import urllib.request, urllib.error
        bad = AIEngine._bad_scheme(url)
        if bad is not None:
            return bad
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {"_ok": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                body = ""
            # جسم الرد الخام (JSON إنجليزي) لا يصل الواجهة — رسالة عربية موجزة
            return {"error": friendly_error(f"HTTP {e.code}: {body or e.reason}"), "status": e.code}
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError) or "timed out" in str(e.reason):
                return {"error": "انتهت مهلة الاتصال — الخادم لا يستجيب", "status": None}
            # السبب الخام (gaierror/Errno…) يمرّ عبر المترجم — لا يصل الواجهة خاماً
            return {"error": friendly_error(str(e.reason)), "status": None}
        except TimeoutError:
            return {"error": "انتهت مهلة الاتصال — الخادم لا يستجيب", "status": None}
        except Exception as e:
            return {"error": str(e), "status": None}

    @staticmethod
    def _http_get_json(url: str, headers: dict, timeout: int) -> dict:
        """GET JSON، أعِد رداً مُفكَّكاً أو {"error":…}. لا يرفع استثناء أبداً."""
        import urllib.request, urllib.error
        bad = AIEngine._bad_scheme(url)
        if bad is not None:
            return bad
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {"_ok": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                body = ""
            return {"error": friendly_error(f"HTTP {e.code}: {body or e.reason}"), "status": e.code}
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError) or "timed out" in str(e.reason):
                return {"error": "انتهت مهلة الاتصال — الخادم لا يستجيب", "status": None}
            return {"error": friendly_error(str(e.reason)), "status": None}
        except TimeoutError:
            return {"error": "انتهت مهلة الاتصال — الخادم لا يستجيب", "status": None}
        except Exception as e:
            return {"error": str(e), "status": None}

    def list_models(self) -> tuple:
        """قائمة النماذج المتاحة من المزوّد المُختار — (ok, models | رسالة)."""
        backend = self.settings.get("ai_backend", "ollama")
        if backend == "ollama":
            url = (self.settings.get("ollama_url")
                   or "http://localhost:11434").rstrip("/")
            res = self._http_get_json(f"{url}/api/tags", {}, 10)
            if "error" in res:
                return False, res["error"]
            models = sorted(m.get("name", "")
                            for m in res["_ok"].get("models", []))
            models = [m for m in models if m]
            return (True, models) if models else (
                False, "لا توجد نماذج — نزّل نموذجاً أولاً (ollama pull)")
        if backend == "openai":
            api_key = self.settings.get("openai_api_key", "")
            if not api_key:
                return False, "لم يُضبَط مفتاح OpenAI في الإعدادات"
            base = (self.settings.get("openai_base_url")
                    or "https://api.openai.com/v1").rstrip("/")
            res = self._http_get_json(f"{base}/models",
                                      {"Authorization": f"Bearer {api_key}"}, 15)
            if "error" in res:
                return False, res["error"]
            models = sorted(m.get("id", "") for m in res["_ok"].get("data", []))
            models = [m for m in models if m]
            return (True, models) if models else (False, "رد غير متوقع من الخدمة")
        if backend == "gemini":
            api_key = self.settings.get("gemini_api_key", "")
            if not api_key:
                return False, "لم يُضبَط مفتاح Gemini في الإعدادات"
            res = self._http_get_json(
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={api_key}", {}, 15)
            if "error" in res:
                return False, res["error"]
            models = sorted(
                m.get("name", "").replace("models/", "")
                for m in res["_ok"].get("models", [])
                if "generateContent" in (m.get("supportedGenerationMethods") or []))
            models = [m for m in models if m]
            return (True, models) if models else (False, "رد غير متوقع من الخدمة")
        if backend == "claude":
            # لا توجد واجهة قائمة — قائمة ثابتة من الإصدارات المعروفة
            return True, ["claude-opus-4-5", "claude-sonnet-4-5",
                          "claude-haiku-4-5"]
        return False, "أدخل اسم النشر (Deployment) يدوياً"

    def _timeout(self) -> int:
        try:
            return int(self.settings.get("ai_timeout", 180))
        except (TypeError, ValueError):
            return 180

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

        # First try to parse the clean text as-is
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                return parsed
            # If it parses but isn't a dict, it's an error
            # (don't silently extract from arrays/scalars)
            return {"raw": raw, "error": "json_parse"}
        except json.JSONDecodeError:
            pass

        # Only if full parse failed, try to extract the first object
        candidate = AIEngine._first_json_object(clean)
        if candidate:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        return {"raw": raw, "error": "json_parse"}

    def _ask_ollama(self, system_prompt: str, user_text: str) -> dict:
        import urllib.request, urllib.error
        model   = self.settings.get("ollama_model", "llama3.2")
        url     = self.settings.get("ollama_url", "http://localhost:11434")
        bad     = self._bad_scheme(url)
        if bad is not None:
            return bad
        payload = json.dumps({
            "model"  : model,
            "prompt" : f"SYSTEM: {system_prompt}\n\nUSER: {user_text}",
            "stream" : False,
            "options": {"temperature": 0.2}
        }).encode()
        req = urllib.request.Request(
            f"{url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout()) as resp:
                data = json.loads(resp.read())
                return self._parse_json(data.get("response", ""))
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError) or "timed out" in str(e.reason):
                return {"error": "انتهت مهلة الاتصال بـ Ollama — النموذج لا يستجيب (قد يكون قيد التحميل)"}
            return {"error": f"تعذر الاتصال بـ Ollama: {e.reason}\nتأكد من تشغيل Ollama أولاً"}
        except TimeoutError:
            return {"error": "انتهت مهلة الاتصال بـ Ollama — النموذج لا يستجيب (قد يكون قيد التحميل)"}
        except Exception as e:
            return {"error": str(e)}

    def _ask_claude(self, system_prompt: str, user_text: str) -> dict:
        api_key = self.settings.get("claude_api_key", "")
        if not api_key:
            return {"error": "لم يُضبَط مفتاح Claude API في الإعدادات"}
        import urllib.request
        payload = json.dumps({
            "model"     : self.settings.get("claude_model", "claude-opus-4-5"),
            "max_tokens": 4096,
            "system"    : system_prompt,
            "messages"  : [{"role": "user", "content": user_text}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type"     : "application/json",
                "x-api-key"        : api_key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout()) as resp:
                data = json.loads(resp.read())
                return self._parse_json(data["content"][0]["text"])
        except Exception as e:
            return {"error": str(e)}

    def _openai_chat(self, base_url: str, api_key: str, model: str,
                     headers: dict, system_prompt: str, user_text: str) -> dict:
        """قالب موحّد لكل واجهات OpenAI (OpenAI / متوافق / Azure)."""
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_text},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        if model:
            payload["model"] = model
        res = self._http_json(base_url, payload, headers, self._timeout())
        if "error" in res:
            # بعض الواجهات المتوافقة (مثل LM Studio) ترفض response_format بـ HTTP 400 — أعِد المحاولة بدونه
            if res.get("status") == 400 and "response_format" in payload:
                payload.pop("response_format", None)
                res = self._http_json(base_url, payload, headers, self._timeout())
            if "error" in res:
                return res
        try:
            return self._parse_json(res["_ok"]["choices"][0]["message"]["content"])
        except Exception as e:
            return {"error": f"رد غير متوقع: {e}"}

    def _ask_openai(self, system_prompt: str, user_text: str) -> dict:
        api_key = self.settings.get("openai_api_key", "")
        if not api_key:
            return {"error": "لم يُضبَط مفتاح OpenAI في الإعدادات"}
        base = (self.settings.get("openai_base_url") or "https://api.openai.com/v1").rstrip("/")
        model = self.settings.get("openai_model", "gpt-4o-mini")
        return self._openai_chat(f"{base}/chat/completions", api_key, model,
                                 {"Authorization": f"Bearer {api_key}"},
                                 system_prompt, user_text)

    def _ask_azure(self, system_prompt: str, user_text: str) -> dict:
        api_key    = self.settings.get("azure_api_key", "")
        endpoint   = (self.settings.get("azure_endpoint", "") or "").rstrip("/")
        deployment = self.settings.get("azure_deployment", "")
        version    = self.settings.get("azure_api_version", "2024-06-01")
        if not (api_key and endpoint and deployment):
            return {"error": "أكمل إعداد Azure (endpoint / deployment / مفتاح) في الإعدادات"}
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}"
        return self._openai_chat(url, api_key, "", {"api-key": api_key},
                                 system_prompt, user_text)

    def _ask_gemini(self, system_prompt: str, user_text: str) -> dict:
        api_key = self.settings.get("gemini_api_key", "")
        if not api_key:
            return {"error": "لم يُضبَط مفتاح Gemini في الإعدادات"}
        model = self.settings.get("gemini_model", "gemini-2.0-flash")
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={api_key}")
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_text}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        res = self._http_json(url, payload, {}, self._timeout())
        if "error" in res:
            return res
        try:
            return self._parse_json(res["_ok"]["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:
            return {"error": f"رد غير متوقع: {e}"}

    def test_connection(self) -> tuple:
        """اختبار الاتصال بالمحرّك المُختار (يعمل لكل المزوّدين عبر ask())."""
        result = _as_result(self.ask(
            "أجب بـ JSON فقط.",
            'أجب بالتالي حرفياً: {"status":"ok","message":"الاتصال ناجح"}'
        ))
        if "error" in result:
            return False, result["error"]
        return True, result.get("message", "الاتصال ناجح")


# ════════════════════════════════════════════════════
# الوكلاء الذكيون — 11 وكيل
# ════════════════════════════════════════════════════
AGENT_PROMPTS = {
    "ops": (
        "وكيل العمليات الميدانية لمشروع LTT 4G/5G.",
        '{"completion_pct":0,"active_sites":0,"issues":["..."],"team_status":"...","recommendations":["..."]}'
    ),
    "quality": (
        "وكيل الجودة والامتثال لمعايير 3GPP.",
        '{"inspected":0,"passed":0,"failed":0,"pass_rate":0,"issues":["..."],"recommendations":["..."]}'
    ),
    "safety": (
        "وكيل السلامة والصحة المهنية.",
        '{"incidents":0,"near_misses":0,"safety_score":0,"violations":["..."],"corrective_actions":["..."],"status":"آمن"}'
    ),
    "civil": (
        "وكيل الأعمال الإنشائية.",
        '{"towers_built":0,"towers_total":0,"civil_pct":0,"pending_permits":0,"issues":["..."],"materials_status":"..."}'
    ),
    "cost": (
        "وكيل التكاليف والميزانية.",
        '{"total_budget":"...","spent":"...","remaining":"...","spent_pct":0,"deviation_pct":0,"forecast":"...","alerts":["..."]}'
    ),
    "contract": (
        "وكيل العقود والشؤون القانونية.",
        '{"active_contracts":0,"total_value":"...","pending_payments":"...","claims":["..."],"expiring_soon":["..."]}'
    ),
    "procure": (
        "وكيل المشتريات وإدارة الموردين.",
        '{"pending_orders":0,"approved_vendors":0,"total_po_value":"...","critical_shortages":["..."],"recommendations":["..."]}'
    ),
    "supply": (
        "وكيل المخازن وسلاسل التوريد.",
        '{"warehouse_fill_pct":0,"in_transit_shipments":0,"delayed_shipments":0,"critical_items":["..."],"logistics_issues":["..."]}'
    ),
    "risk": (
        "وكيل إدارة المخاطر الشامل.",
        '{"risks":[{"title":"...","level":"عالية","category":"فني","description":"...","solution":"...","owner":"..."}]}'
    ),
    "schedule": (
        "وكيل الجدول الزمني والمسار الحرج.",
        '{"delay_days":0,"original_end":"...","new_end":"...","phases":[{"name":"...","status":"في الموعد","completion_pct":0}],"critical_path":["..."]}'
    ),
    "chief": (
        "وكيل التنسيق المركزي — يجمع نتائج جميع الوكلاء ويُعدّ التقرير التنفيذي.",
        '{"overall_health":"جيد","executive_summary":"...","dept_scores":[{"dept":"...","score":0,"status":"جيد","key_issue":"..."}],"top_actions":[{"priority":1,"action":"...","owner":"...","deadline":"...","impact":"..."}],"kpis":[{"name":"...","value":"...","trend":"→","status":"جيد"}],"achievements":["..."]}'
    ),
}

WORKER_AGENTS = ["ops","quality","safety","civil","cost","contract","procure","supply","risk","schedule"]


def _ensure_chief_schema(chief: dict) -> dict:
    """يضمن أن مخرجات وكيل التنسيق تحوي كل المفاتيح التي تقرأها اللوحة والمصدّرات،
    حتى لو فشل الاستدعاء أو عاد بنص غير صالح — فلا تنكسر الواجهة أبداً."""
    chief = chief if isinstance(chief, dict) else {}
    err   = chief.get("error")
    summary = chief.get("executive_summary")
    if not summary:
        summary = (f"تعذّر إكمال التحليل: {err}" if err
                   else "لم يُنتِج وكيل التنسيق ملخصاً.")
    return {
        "overall_health":    chief.get("overall_health", "غير محدد"),
        "executive_summary": summary,
        "kpis":              chief.get("kpis", []) or [],
        "top_actions":       chief.get("top_actions", []) or [],
        "dept_scores":       chief.get("dept_scores", []) or [],
        "achievements":      chief.get("achievements", []) or [],
    }


def _as_result(value) -> dict:
    """Any agent result that is not a dict is a failed agent, not a crash."""
    if isinstance(value, dict):
        return value
    return {"raw": repr(value), "error": "bad_shape"}


class AgentsEngine:
    def __init__(self, ai: AIEngine, log_fn=None):
        self.ai  = ai
        self.log = log_fn or print

    def run_agent(self, agent_id: str, reports_text: str) -> dict:
        desc, schema = AGENT_PROMPTS[agent_id]
        system = (
            f"{desc}\n"
            f"حلّل البيانات المُدخَلة واستخرج المعلومات المطلوبة.\n"
            f"أجب بـ JSON فقط بهذا الهيكل بدون أي نص آخر:\n{schema}"
        )
        return self.ai.ask(system, reports_text)

    def run_all(self, reports: list, progress_cb=None, agent_cb=None) -> dict:
        """تشغيل جميع الوكلاء وإرجاع النتائج.

        agent_cb(agent_id, state) — state ∈ {"running","done","error"} — يُستدعى
        قبل/بعد كل وكيل حتى تعرض الواجهة الحالة الحيّة لكل وكيل.
        """
        text = self._format_reports(reports)
        results = {}
        total   = len(WORKER_AGENTS) + 1

        for i, ag_id in enumerate(WORKER_AGENTS):
            self.log(f"⏳ {ag_id}...")
            if agent_cb:
                agent_cb(ag_id, "running")
            result = _as_result(self.run_agent(ag_id, text))
            results[ag_id] = result
            if "error" in result:
                self.log(f"  ✗ {result['error']}")
                if agent_cb:
                    agent_cb(ag_id, "error")
            else:
                self.log(f"  ✓ اكتمل")
                if agent_cb:
                    agent_cb(ag_id, "done")
            if progress_cb:
                progress_cb(int((i+1)/total*100))

        # وكيل التنسيق — يُغذّى فقط بنتائج الوكلاء الناجحة (لا نمرّر أخطاء)
        self.log("⏳ وكيل التنسيق المركزي...")
        if agent_cb:
            agent_cb("chief", "running")
        clean = {k: v for k, v in results.items() if "error" not in v}
        chief_input = (
            f"التقارير:\n{text}\n\n"
            f"نتائج الوكلاء:\n{json.dumps(clean, ensure_ascii=False)}"
        )
        desc, schema = AGENT_PROMPTS["chief"]
        system = (
            f"{desc}\n"
            f"أجب بـ JSON فقط بهذا الهيكل:\n{schema}"
        )
        chief = _as_result(self.ai.ask(system, chief_input))
        chief_ok = "error" not in chief and "raw" not in chief
        results["chief"] = _ensure_chief_schema(chief)
        if agent_cb:
            agent_cb("chief", "done" if chief_ok else "error")
        if progress_cb:
            progress_cb(100)
        self.log("✓ اكتمل التحليل الشامل")
        self._save(results)
        return results

    def _format_reports(self, reports: list) -> str:
        parts = []
        for r in reports:
            parts.append(
                f"[{r.get('source','').upper()}]"
                f"[{r.get('dept','')}] "
                f"من: {r.get('from','')} | "
                f"{r.get('date','')}\n"
                f"{r.get('content','')}"
            )
        return "\n\n---\n\n".join(parts)

    def _save(self, results: dict):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORTS / f"results_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        latest = REPORTS / "latest.json"
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
