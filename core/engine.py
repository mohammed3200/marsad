"""
marsad core engine — AI backend + agent fleet.

UI-agnostic: no Tkinter/Qt imports. Extracted verbatim from the original app.py
(only AgentsEngine.run_all gains an optional per-agent callback so a UI can show
live agent state). The `results` dict keyed by agent id is the contract every
consumer (exporters, dashboard) reads.
"""
import json
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS  = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)


# ════════════════════════════════════════════════════
# محرك الذكاء الاصطناعي — يدعم Ollama و Claude
# ════════════════════════════════════════════════════
class AIEngine:
    def __init__(self, settings):
        self.settings = settings

    def ask(self, system_prompt: str, user_text: str) -> dict:
        """استدعاء نموذج الذكاء الاصطناعي وإرجاع dict"""
        backend = self.settings.get("ai_backend", "ollama")
        if backend == "claude":
            return self._ask_claude(system_prompt, user_text)
        else:
            return self._ask_ollama(system_prompt, user_text)

    def _ask_ollama(self, system_prompt: str, user_text: str) -> dict:
        import urllib.request, urllib.error
        model   = self.settings.get("ollama_model", "llama3.2")
        url     = self.settings.get("ollama_url", "http://localhost:11434")
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
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                raw  = data.get("response", "")
                # تنظيف JSON
                clean = raw.replace("```json","").replace("```","").strip()
                # محاولة أولى: JSON مباشر
                try:
                    return json.loads(clean)
                except json.JSONDecodeError:
                    # محاولة ثانية: استخراج أول {} من النص
                    start = clean.find("{")
                    end   = clean.rfind("}") + 1
                    if start >= 0 and end > start:
                        return json.loads(clean[start:end])
                    return {"raw": raw, "error": "json_parse"}
        except urllib.error.URLError as e:
            return {"error": f"تعذر الاتصال بـ Ollama: {e.reason}\nتأكد من تشغيل Ollama أولاً"}
        except Exception as e:
            return {"error": str(e)}

    def _ask_claude(self, system_prompt: str, user_text: str) -> dict:
        api_key = self.settings.get("claude_api_key", "")
        if not api_key:
            return {"error": "لم يُضبَط مفتاح Claude API في الإعدادات"}
        import urllib.request
        payload = json.dumps({
            "model"     : self.settings.get("claude_model", "claude-opus-4-5"),
            "max_tokens": 1500,
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
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                raw  = data["content"][0]["text"]
                clean = raw.replace("```json","").replace("```","").strip()
                return json.loads(clean)
        except Exception as e:
            return {"error": str(e)}

    def test_connection(self) -> tuple:
        """اختبار الاتصال بالنموذج"""
        backend = self.settings.get("ai_backend", "ollama")
        if backend == "ollama":
            result = self.ask(
                "أجب بـ JSON فقط.",
                'أجب بالتالي: {"status": "ok", "message": "الاتصال ناجح"}'
            )
        else:
            result = self.ask(
                "أجب بـ JSON فقط.",
                'أجب بالتالي: {"status": "ok", "message": "Claude متصل"}'
            )
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
            result = self.run_agent(ag_id, text)
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

        # وكيل التنسيق
        self.log("⏳ وكيل التنسيق المركزي...")
        if agent_cb:
            agent_cb("chief", "running")
        chief_input = f"التقارير:\n{text}\n\nنتائج الوكلاء:\n{json.dumps(results, ensure_ascii=False)}"
        desc, schema = AGENT_PROMPTS["chief"]
        system = (
            f"{desc}\n"
            f"أجب بـ JSON فقط بهذا الهيكل:\n{schema}"
        )
        results["chief"] = self.ai.ask(system, chief_input)
        if agent_cb:
            agent_cb("chief", "error" if "error" in results["chief"] else "done")
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
