"""
╔══════════════════════════════════════════════════════════════╗
║   نظام إدارة المشاريع الذكي — LTT PM Intelligence Desktop   ║
║   تطبيق سطح المكتب الكامل                                    ║
║   يعمل بـ Ollama (محلي مجاني) + Claude API (اختياري)        ║
╚══════════════════════════════════════════════════════════════╝

الاستخدام:
    python app.py

المتطلبات:
    pip install -r requirements.txt
    + تثبيت Ollama من ollama.com
"""

# ══════════════════════════════════════════════════
# تثبيت تلقائي للمكتبات الناقصة عند أول تشغيل
# ══════════════════════════════════════════════════
import sys, subprocess

def _auto_install():
    """تثبيت المكتبات المطلوبة — يعمل بشكل مرئي ويتحقق من النجاح"""
    PACKAGES = [
        ("openpyxl",       "openpyxl"),
        ("reportlab",      "reportlab"),
        ("arabic_reshaper","arabic-reshaper"),
        ("bidi",           "python-bidi"),
        ("PyPDF2",         "PyPDF2"),
        ("PIL",            "Pillow"),
        ("dotenv",         "python-dotenv"),
        ("schedule",       "schedule"),
    ]
    missing = []
    for module, pkg in PACKAGES:
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)

    if not missing:
        print("[✓] جميع المكتبات مثبتة")
        return

    print(f"[تثبيت] {len(missing)} مكتبة ناقصة: {', '.join(missing)}")
    for pkg in missing:
        print(f"  جاري تثبيت {pkg}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg,
             "--quiet", "--no-warn-script-location"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓")
        else:
            print(f"✗  ({result.stderr.strip()[:80]})")
            # محاولة ثانية بدون --quiet لعرض الخطأ
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                check=False
            )
    print("[✓] اكتمل التثبيت — أعد تشغيل التطبيق إذا ظهرت أخطاء")

_auto_install()
# ══════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
import os
import datetime
import subprocess
import sys
from pathlib import Path
from contacts_manager import ContactsDB, ContactsTab
from connectors import ConnectorHub, WhatsAppHelper, build_report_html

# ── إعداد المجلدات ──
BASE_DIR   = Path(__file__).parent
REPORTS    = BASE_DIR / "reports"
UPLOADS    = BASE_DIR / "uploads"
LOGS       = BASE_DIR / "logs"
SETTINGS_F = BASE_DIR / "settings.json"
for d in [REPORTS, UPLOADS, LOGS]: d.mkdir(exist_ok=True)

# ── ألوان التطبيق ──
BG_DARK   = "#0D1B2A"
BG_MID    = "#1E3A5F"
BG_CARD   = "#162032"
ACCENT    = "#2563EB"
ACCENT2   = "#38BDF8"
SUCCESS   = "#10B981"
WARNING   = "#F59E0B"
DANGER    = "#EF4444"
TEXT_PRI  = "#E2E8F0"
TEXT_SEC  = "#94A3B8"
TEXT_DIM  = "#475569"
WHITE     = "#FFFFFF"

FONT_TITLE  = ("Arial", 18, "bold")
FONT_HEAD   = ("Arial", 13, "bold")
FONT_BODY   = ("Arial", 11)
FONT_SMALL  = ("Arial", 9)
FONT_MONO   = ("Courier New", 10)

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
            "model"     : "claude-opus-4-5",
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

    def test_connection(self) -> tuple[bool, str]:
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

    def run_all(self, reports: list, progress_cb=None) -> dict:
        """تشغيل جميع الوكلاء وإرجاع النتائج"""
        text = self._format_reports(reports)
        results = {}
        total   = len(WORKER_AGENTS) + 1

        for i, ag_id in enumerate(WORKER_AGENTS):
            self.log(f"⏳ {ag_id}...")
            result = self.run_agent(ag_id, text)
            results[ag_id] = result
            if "error" in result:
                self.log(f"  ✗ {result['error']}")
            else:
                self.log(f"  ✓ اكتمل")
            if progress_cb:
                progress_cb(int((i+1)/total*100))

        # وكيل التنسيق
        self.log("⏳ وكيل التنسيق المركزي...")
        chief_input = f"التقارير:\n{text}\n\nنتائج الوكلاء:\n{json.dumps(results, ensure_ascii=False)}"
        desc, schema = AGENT_PROMPTS["chief"]
        system = (
            f"{desc}\n"
            f"أجب بـ JSON فقط بهذا الهيكل:\n{schema}"
        )
        results["chief"] = self.ai.ask(system, chief_input)
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


# ════════════════════════════════════════════════════
# التطبيق الرئيسي — واجهة رسومية
# ════════════════════════════════════════════════════
class LTTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("نظام إدارة المشاريع الذكي — LTT Intelligence")
        self.geometry("1200x750")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        # تحميل الإعدادات
        self.settings  = self._load_settings()
        self.ai_engine  = AIEngine(self.settings)
        self.contacts_db = ContactsDB()
        self.hub = ConnectorHub(self.settings, self.contacts_db)
        self.hub.set_logger(self._log)
        self.agents    = None
        self.reports   = self._load_sample_reports()
        self.results   = self._load_latest_results()

        self._setup_styles()
        self._build_ui()
        self.after(100, self._check_ollama)

    # ── إعدادات ttk ──
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.TFrame",     background=BG_DARK)
        style.configure("Card.TFrame",     background=BG_CARD)
        style.configure("Accent.TButton",  background=ACCENT,  foreground=WHITE,
                        font=FONT_BODY, borderwidth=0, focusthickness=0, padding=(14,8))
        style.map("Accent.TButton",        background=[("active","#1D4ED8")])
        style.configure("Success.TButton", background=SUCCESS, foreground=WHITE,
                        font=FONT_BODY, borderwidth=0, padding=(14,8))
        style.configure("Danger.TButton",  background=DANGER,  foreground=WHITE,
                        font=FONT_BODY, borderwidth=0, padding=(14,8))
        style.configure("Dark.TLabel",     background=BG_DARK, foreground=TEXT_PRI,
                        font=FONT_BODY)
        style.configure("Card.TLabel",     background=BG_CARD, foreground=TEXT_PRI,
                        font=FONT_BODY)
        style.configure("Title.TLabel",    background=BG_DARK, foreground=ACCENT2,
                        font=FONT_TITLE)
        style.configure("Head.TLabel",     background=BG_DARK, foreground=TEXT_PRI,
                        font=FONT_HEAD)
        style.configure("Dim.TLabel",      background=BG_DARK, foreground=TEXT_DIM,
                        font=FONT_SMALL)
        style.configure("Dark.TNotebook",          background=BG_DARK, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                        background=BG_MID, foreground=TEXT_SEC,
                        padding=(16,8), font=FONT_BODY)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected",BG_CARD)],
                  foreground=[("selected",ACCENT2)])
        style.configure("Dark.Horizontal.TProgressbar",
                        troughcolor=BG_MID, background=ACCENT,
                        thickness=10, borderwidth=0)
        style.configure("Dark.TEntry",     fieldbackground="#0f1e2e",
                        foreground=TEXT_PRI, bordercolor=BG_MID,
                        insertcolor=TEXT_PRI)
        style.configure("Dark.TCombobox",  fieldbackground="#0f1e2e",
                        foreground=TEXT_PRI, selectbackground=ACCENT)
        style.configure("Dark.TSeparator", background=BG_MID)

    # ════════════════════════════════════════════════
    # بناء واجهة المستخدم
    # ════════════════════════════════════════════════
    def _build_ui(self):
        # ── شريط العنوان ──
        header = tk.Frame(self, bg=BG_MID, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header, text="⚡", bg=BG_MID, fg=ACCENT2,
                 font=("Arial",22)).pack(side="left", padx=(16,6), pady=10)
        tk.Label(header, text="نظام إدارة المشاريع الذكي — LTT Intelligence",
                 bg=BG_MID, fg=ACCENT2,
                 font=("Arial",15,"bold")).pack(side="left", pady=10)
        tk.Label(header, text="شركة ليبيا للاتصالات والتقنية | مشروع 4G/5G",
                 bg=BG_MID, fg=TEXT_DIM,
                 font=FONT_SMALL).pack(side="left", padx=12, pady=10)

        self.status_lbl = tk.Label(header, text="● Ollama غير متصل",
                                   bg=BG_MID, fg=DANGER, font=FONT_SMALL)
        self.status_lbl.pack(side="right", padx=16)

        # ── Notebook (تبويبات) ──
        nb = ttk.Notebook(self, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, padx=8, pady=(0,8))

        tab1 = ttk.Frame(nb, style="Dark.TFrame")
        tab2 = ttk.Frame(nb, style="Dark.TFrame")
        tab3 = ttk.Frame(nb, style="Dark.TFrame")
        tab4 = ttk.Frame(nb, style="Dark.TFrame")
        tab5 = ttk.Frame(nb, style="Dark.TFrame")

        tab6 = ContactsTab(nb, self.contacts_db)

        nb.add(tab1, text="  📥 إدخال البيانات  ")
        nb.add(tab2, text="  ⚡ التحليل والوكلاء  ")
        nb.add(tab3, text="  📊 لوحة التحكم  ")
        nb.add(tab4, text="  📄 التقارير  ")
        nb.add(tab5, text="  ⚙️ الإعدادات  ")
        nb.add(tab6, text="  👥 جهات الاتصال  ")

        self._build_input_tab(tab1)
        self._build_analysis_tab(tab2)
        self._build_dashboard_tab(tab3)
        self._build_reports_tab(tab4)
        self._build_settings_tab(tab5)

    # ════════════════════════════════════════════════
    # تبويب 1: إدخال البيانات
    # ════════════════════════════════════════════════
    def _build_input_tab(self, parent):
        # ── قائمة التقارير الحالية ──
        left = tk.Frame(parent, bg=BG_DARK, width=400)
        left.pack(side="left", fill="both", padx=(8,4), pady=8)
        left.pack_propagate(False)

        tk.Label(left, text="📋 التقارير المُدخَلة",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", pady=(0,6))

        # Listbox مع scrollbar
        lf = tk.Frame(left, bg=BG_CARD, bd=1, relief="flat")
        lf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lf, bg=BG_MID, troughcolor=BG_DARK)
        sb.pack(side="right", fill="y")
        self.reports_list = tk.Listbox(
            lf, bg=BG_CARD, fg=TEXT_PRI, font=FONT_SMALL,
            selectbackground=ACCENT, selectforeground=WHITE,
            borderwidth=0, highlightthickness=0,
            yscrollcommand=sb.set, activestyle="none"
        )
        self.reports_list.pack(fill="both", expand=True)
        sb.config(command=self.reports_list.yview)
        self.reports_list.bind("<Double-Button-1>", self._view_report)
        self._refresh_reports_list()

        btn_row = tk.Frame(left, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(6,0))
        tk.Button(btn_row, text="🗑 حذف المحدد",
                  bg=DANGER, fg=WHITE, font=FONT_SMALL,
                  bd=0, padx=10, pady=5, cursor="hand2",
                  command=self._delete_report).pack(side="right", padx=2)
        tk.Button(btn_row, text="👁 عرض التقرير",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_SMALL,
                  bd=0, padx=10, pady=5, cursor="hand2",
                  command=self._view_report).pack(side="right", padx=2)

        # ── نموذج إضافة تقرير ──
        right = tk.Frame(parent, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)

        tk.Label(right, text="➕ إضافة تقرير جديد",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", pady=(0,8))

        # صف الحقول العلوية
        row1 = tk.Frame(right, bg=BG_DARK)
        row1.pack(fill="x", pady=(0,6))
        for label, var_name, opts in [
            ("المصدر", "_src_var", ["📧 بريد إلكتروني","💬 واتساب","🖥️ نظام ERP","✍️ يدوي","📄 تقرير PDF"]),
            ("القسم",  "_dept_var", ["ran","core","ops","quality","safety","civil","cost","contract","procure","supply","admin"]),
        ]:
            f = tk.Frame(row1, bg=BG_DARK)
            f.pack(side="left", fill="x", expand=True, padx=(0,8))
            tk.Label(f, text=label, bg=BG_DARK, fg=TEXT_SEC, font=FONT_SMALL).pack(anchor="w")
            v = tk.StringVar(value=opts[0])
            setattr(self, var_name, v)
            cb = ttk.Combobox(f, textvariable=v, values=opts,
                              style="Dark.TCombobox", state="readonly", font=FONT_SMALL)
            cb.pack(fill="x", ipady=4)

        # حقل المرسل والتاريخ
        row2 = tk.Frame(right, bg=BG_DARK)
        row2.pack(fill="x", pady=(0,6))
        # حقل "من / المرسل" مع زر جهات الاتصال
        f_from = tk.Frame(row2, bg=BG_DARK)
        f_from.pack(side="left", fill="x", expand=True, padx=(0,8))
        tk.Label(f_from, text="من / المرسل", bg=BG_DARK,
                 fg=TEXT_SEC, font=FONT_SMALL).pack(anchor="w")
        from_row = tk.Frame(f_from, bg=BG_DARK)
        from_row.pack(fill="x")
        self._from_var = tk.StringVar(value="اسم المرسل أو القسم")
        self._from_entry = tk.Entry(from_row, textvariable=self._from_var,
                                    bg="#0f1e2e", fg=TEXT_PRI,
                                    font=FONT_SMALL, bd=1, relief="solid",
                                    insertbackground=TEXT_PRI)
        self._from_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(from_row, text="👤",
                  bg=BG_MID, fg=ACCENT2, font=("Arial",12),
                  bd=0, padx=6, cursor="hand2",
                  command=self._pick_from_contacts).pack(side="right", padx=(4,0))

        # حقل التاريخ
        f_date = tk.Frame(row2, bg=BG_DARK)
        f_date.pack(side="left", fill="x", expand=True, padx=(0,8))
        tk.Label(f_date, text="التاريخ", bg=BG_DARK,
                 fg=TEXT_SEC, font=FONT_SMALL).pack(anchor="w")
        self._date_var = tk.StringVar(value=datetime.date.today().isoformat())
        tk.Entry(f_date, textvariable=self._date_var,
                 bg="#0f1e2e", fg=TEXT_PRI, font=FONT_SMALL,
                 bd=1, relief="solid", insertbackground=TEXT_PRI).pack(fill="x", ipady=4)

        # محتوى التقرير
        tk.Label(right, text="محتوى التقرير / نص الرسالة",
                 bg=BG_DARK, fg=TEXT_SEC, font=FONT_SMALL).pack(anchor="w")
        self._content_box = scrolledtext.ScrolledText(
            right, height=8, bg="#0f1e2e", fg=TEXT_PRI,
            font=FONT_SMALL, bd=1, relief="solid",
            insertbackground=TEXT_PRI, wrap="word",
            selectbackground=ACCENT
        )
        self._content_box.pack(fill="x", pady=(2,8))

        # أزرار الإجراءات
        act_row = tk.Frame(right, bg=BG_DARK)
        act_row.pack(fill="x")
        tk.Button(act_row, text="➕ إضافة التقرير",
                  bg=ACCENT, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._add_report).pack(side="left", padx=(0,8))
        tk.Button(act_row, text="📂 استيراد ملف PDF/TXT",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._import_file).pack(side="left", padx=(0,8))
        tk.Button(act_row, text="🗃 تحميل بيانات نموذجية",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._load_samples).pack(side="left")

        # شريط المعلومات
        info = tk.Frame(right, bg=BG_MID, height=36)
        info.pack(fill="x", pady=(12,0))
        info.pack_propagate(False)
        self._info_lbl = tk.Label(info, text=f"إجمالي التقارير: {len(self.reports)}",
                                  bg=BG_MID, fg=TEXT_PRI, font=FONT_SMALL)
        self._info_lbl.pack(side="left", padx=12, pady=8)

    # ════════════════════════════════════════════════
    # تبويب 2: التحليل والوكلاء
    # ════════════════════════════════════════════════
    def _build_analysis_tab(self, parent):
        # ── بطاقات الوكلاء ──
        agents_frame = tk.Frame(parent, bg=BG_DARK)
        agents_frame.pack(fill="x", padx=8, pady=(8,4))

        tk.Label(agents_frame, text="🤖 الوكلاء الذكيون",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", pady=(0,6))

        grid = tk.Frame(agents_frame, bg=BG_DARK)
        grid.pack(fill="x")
        self._agent_cards = {}
        agent_info = [
            ("ops","🔧","العمليات"), ("quality","✅","الجودة"),
            ("safety","🦺","السلامة"), ("civil","🏗️","الإنشاء"),
            ("cost","📊","التكاليف"), ("contract","📝","العقود"),
            ("procure","🛒","المشتريات"), ("supply","🚛","التوريد"),
            ("risk","⚠️","المخاطر"), ("schedule","📅","الجدول"),
            ("chief","🤖","التنسيق"),
        ]
        for col, (aid, icon, name) in enumerate(agent_info):
            card = tk.Frame(grid, bg=BG_CARD, bd=1, relief="flat",
                            highlightbackground=BG_MID, highlightthickness=1)
            card.grid(row=0, column=col, padx=2, pady=2, sticky="nsew")
            grid.columnconfigure(col, weight=1)
            tk.Label(card, text=icon, bg=BG_CARD, font=("Arial",16)).pack(pady=(6,2))
            tk.Label(card, text=name, bg=BG_CARD, fg=TEXT_SEC,
                     font=("Arial",8)).pack(pady=(0,2))
            st = tk.Label(card, text="⏸", bg=BG_CARD, fg=TEXT_DIM,
                          font=("Arial",8))
            st.pack(pady=(0,6))
            self._agent_cards[aid] = {"frame": card, "status": st}

        # ── شريط التقدم والسجل ──
        mid = tk.Frame(parent, bg=BG_DARK)
        mid.pack(fill="x", padx=8, pady=4)

        tk.Label(mid, text="تقدم التحليل:", bg=BG_DARK, fg=TEXT_SEC,
                 font=FONT_SMALL).pack(anchor="w")
        self._progress_var = tk.IntVar(value=0)
        self._prog_bar = ttk.Progressbar(mid, variable=self._progress_var,
                                         maximum=100, style="Dark.Horizontal.TProgressbar")
        self._prog_bar.pack(fill="x", pady=(2,6))
        self._prog_lbl = tk.Label(mid, text="0%", bg=BG_DARK, fg=TEXT_SEC,
                                  font=FONT_SMALL)
        self._prog_lbl.pack(anchor="e")

        # سجل التشغيل
        tk.Label(parent, text="📋 سجل التشغيل",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", padx=8)
        self._log_box = scrolledtext.ScrolledText(
            parent, height=14, bg="#080f1a", fg="#6ee7b7",
            font=FONT_MONO, bd=0, state="disabled",
            insertbackground="#6ee7b7", selectbackground=ACCENT
        )
        self._log_box.pack(fill="both", expand=True, padx=8, pady=(4,4))

        # أزرار التشغيل
        btn_row = tk.Frame(parent, bg=BG_DARK)
        btn_row.pack(fill="x", padx=8, pady=(0,8))
        self._run_btn = tk.Button(
            btn_row, text="⚡ بدء التحليل الشامل",
            bg=ACCENT, fg=WHITE, font=("Arial",12,"bold"),
            bd=0, padx=24, pady=10, cursor="hand2",
            command=self._run_analysis
        )
        self._run_btn.pack(side="left", padx=(0,8))
        tk.Button(btn_row, text="🔄 مسح السجل",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=10, cursor="hand2",
                  command=self._clear_log).pack(side="left")
        self._status_run = tk.Label(btn_row, text="",
                                    bg=BG_DARK, fg=TEXT_SEC, font=FONT_SMALL)
        self._status_run.pack(side="right", padx=8)

    # ════════════════════════════════════════════════
    # تبويب 3: لوحة التحكم
    # ════════════════════════════════════════════════
    def _build_dashboard_tab(self, parent):
        tk.Label(parent, text="📊 لوحة التحكم التنفيذية",
                 bg=BG_DARK, fg=ACCENT2, font=FONT_TITLE).pack(anchor="w", padx=8, pady=(8,4))

        # شريط الحالة
        status_bar = tk.Frame(parent, bg=BG_MID, height=50)
        status_bar.pack(fill="x", padx=8, pady=(0,8))
        status_bar.pack_propagate(False)
        self._health_lbl = tk.Label(status_bar, text="الحالة: لم يتم التحليل بعد",
                                    bg=BG_MID, fg=TEXT_SEC,
                                    font=("Arial",13,"bold"))
        self._health_lbl.pack(side="left", padx=16, pady=12)
        tk.Button(status_bar, text="🔄 تحديث",
                  bg=ACCENT, fg=WHITE, font=FONT_SMALL,
                  bd=0, padx=12, pady=4, cursor="hand2",
                  command=self._refresh_dashboard).pack(side="right", padx=12, pady=10)

        # KPIs
        self._kpi_frame = tk.Frame(parent, bg=BG_DARK)
        self._kpi_frame.pack(fill="x", padx=8, pady=(0,8))

        # الملخص التنفيذي
        tk.Label(parent, text="الملخص التنفيذي",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", padx=8)
        self._summary_box = scrolledtext.ScrolledText(
            parent, height=6, bg=BG_CARD, fg=TEXT_PRI,
            font=FONT_BODY, bd=0, wrap="word",
            state="disabled", selectbackground=ACCENT
        )
        self._summary_box.pack(fill="x", padx=8, pady=(4,8))

        # قائمة الإجراءات
        tk.Label(parent, text="🎯 خطة العمل الفورية",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", padx=8)
        self._actions_box = scrolledtext.ScrolledText(
            parent, height=8, bg=BG_CARD, fg=TEXT_PRI,
            font=FONT_BODY, bd=0, wrap="word",
            state="disabled", selectbackground=ACCENT
        )
        self._actions_box.pack(fill="both", expand=True, padx=8, pady=(4,8))

        if self.results:
            self._refresh_dashboard()

    # ════════════════════════════════════════════════
    # تبويب 4: التقارير
    # ════════════════════════════════════════════════
    def _build_reports_tab(self, parent):
        tk.Label(parent, text="📄 التقارير المُنتَجة",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w", padx=8, pady=(8,4))

        # قائمة الملفات
        lf = tk.Frame(parent, bg=BG_CARD, bd=1)
        lf.pack(fill="both", expand=True, padx=8, pady=(0,8))
        sb = tk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        self._files_list = tk.Listbox(
            lf, bg=BG_CARD, fg=TEXT_PRI, font=FONT_BODY,
            selectbackground=ACCENT, selectforeground=WHITE,
            borderwidth=0, highlightthickness=0,
            yscrollcommand=sb.set, activestyle="none"
        )
        self._files_list.pack(fill="both", expand=True)
        sb.config(command=self._files_list.yview)
        self._refresh_files_list()

        btn_row = tk.Frame(parent, bg=BG_DARK)
        btn_row.pack(fill="x", padx=8, pady=(0,8))
        tk.Button(btn_row, text="📄 تصدير PDF",
                  bg="#7C3AED", fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._export_pdf).pack(side="left", padx=(0,8))
        tk.Button(btn_row, text="📊 تصدير Excel",
                  bg=SUCCESS, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._export_excel).pack(side="left", padx=(0,8))
        tk.Button(btn_row, text="📂 فتح مجلد التقارير",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=lambda: os.startfile(str(REPORTS))).pack(side="left")

    # ════════════════════════════════════════════════
    # تبويب 5: الإعدادات
    # ════════════════════════════════════════════════
    def _build_settings_tab(self, parent):
        sv = tk.Frame(parent, bg=BG_DARK)
        sv.pack(fill="both", expand=True, padx=24, pady=16)

        tk.Label(sv, text="⚙️ إعدادات النظام",
                 bg=BG_DARK, fg=TEXT_PRI, font=FONT_TITLE).pack(anchor="w", pady=(0,16))

        # ── قسم الذكاء الاصطناعي ──
        self._section(sv, "🤖 إعدادات الذكاء الاصطناعي")

        ai_row = tk.Frame(sv, bg=BG_DARK)
        ai_row.pack(fill="x", pady=(0,8))
        tk.Label(ai_row, text="المحرك:", bg=BG_DARK, fg=TEXT_SEC,
                 font=FONT_BODY, width=14, anchor="w").pack(side="left")
        self._ai_var = tk.StringVar(value=self.settings.get("ai_backend","ollama"))
        for val, lbl in [("ollama","🦙 Ollama (محلي مجاني)"),("claude","🤖 Claude API (سحابي)")]:
            tk.Radiobutton(ai_row, text=lbl, variable=self._ai_var, value=val,
                          bg=BG_DARK, fg=TEXT_PRI, selectcolor=BG_MID,
                          activebackground=BG_DARK, activeforeground=TEXT_PRI,
                          font=FONT_BODY).pack(side="left", padx=8)

        # Ollama
        self._section(sv, "  🦙 إعدادات Ollama")
        for label, key, default in [
            ("رابط الخادم:", "ollama_url", "http://localhost:11434"),
            ("النموذج:",     "ollama_model", "llama3.2"),
        ]:
            self._setting_row(sv, label, key, default)

        tk.Button(sv, text="⬇️ تثبيت Ollama",
                  bg=WARNING, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=6, cursor="hand2",
                  command=lambda: self._open_url("https://ollama.com")).pack(anchor="w", pady=4)
        tk.Button(sv, text="📥 تحميل نموذج llama3.2",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=6, cursor="hand2",
                  command=self._pull_ollama_model).pack(anchor="w", pady=4)

        # البريد الإلكتروني
        self._section(sv, "  📧 إعدادات البريد الإلكتروني")
        self._setting_row(sv, "عنوان البريد:", "email_user",      "pm-system@gmail.com")
        self._setting_row(sv, "كلمة المرور:",  "email_password",  "xxxx-xxxx-xxxx-xxxx", show="*")

        row_test = tk.Frame(sv, bg=BG_DARK); row_test.pack(fill="x", pady=4)
        tk.Button(row_test, text="🔌 اختبار البريد",
                  bg=WARNING, fg=WHITE, font=FONT_SMALL,
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=self._test_email_conn).pack(side="left", padx=(0,8))
        tk.Button(row_test, text="🔄 سحب البريد الآن",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_SMALL,
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=self._fetch_email_now).pack(side="left")
        self._email_status = tk.Label(row_test, text="", bg=BG_DARK,
                                       fg=TEXT_SEC, font=FONT_SMALL)
        self._email_status.pack(side="left", padx=8)

        # مجلد ERP
        self._section(sv, "  🖥️ مجلد تقارير ERP (اختياري)")
        self._setting_row(sv, "مسار المجلد:", "erp_folder", r"C:\Reports\ERP")
        tk.Button(sv, text="📂 اختيار المجلد",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_SMALL,
                  bd=0, padx=12, pady=5, cursor="hand2",
                  command=self._browse_erp_folder).pack(anchor="w", pady=4)

        # مستلمو التقارير
        self._section(sv, "  📤 إرسال التقارير تلقائياً")
        self._setting_row(sv, "المستلمون (مفصولون بفاصلة):", "report_recipients",
                          "manager@example.com, pmo@example.com")

        # Claude
        self._section(sv, "  🤖 إعدادات Claude API (اختياري)")
        self._setting_row(sv, "مفتاح API:", "claude_api_key", "sk-ant-...", show="*")

        tk.Button(sv, text="🔑 احصل على مفتاح API",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=6, cursor="hand2",
                  command=lambda: self._open_url("https://console.anthropic.com")).pack(anchor="w", pady=4)

        # ── زر الاختبار والحفظ ──
        btn_row = tk.Frame(sv, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(16,0))
        tk.Button(btn_row, text="🔌 اختبار الاتصال",
                  bg=WARNING, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._test_connection).pack(side="left", padx=(0,8))
        tk.Button(btn_row, text="💾 حفظ الإعدادات",
                  bg=SUCCESS, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=8, cursor="hand2",
                  command=self._save_settings).pack(side="left")
        self._conn_lbl = tk.Label(btn_row, text="",
                                  bg=BG_DARK, fg=TEXT_SEC, font=FONT_BODY)
        self._conn_lbl.pack(side="left", padx=16)


    def _test_email_conn(self):
        self._save_settings()
        try:
            self._email_status.config(text="✓ الإعدادات سليمة", fg=SUCCESS)
        except Exception:
            pass

    def _fetch_email_now(self):
        try:
            self._log("📧 بدء سحب البريد...")
            reports = self.hub.collect_all()
            if reports:
                self.reports.extend(reports)
                self._refresh_reports_list()
            try:
                self._email_status.config(text=f"✓ تم جلب {len(reports) if reports else 0} تقرير", fg=SUCCESS)
            except Exception:
                pass
        except Exception as e:
            try:
                self._email_status.config(text=f"✗ {e}", fg=DANGER)
            except Exception:
                pass

    def _browse_erp_folder(self):
        folder = filedialog.askdirectory(title="اختيار مجلد ERP")
        if folder and hasattr(self, "_set_erp_folder"):
            self._set_erp_folder.set(folder)


    # ════════════════════════════════════════════════
    # مساعدات UI
    # ════════════════════════════════════════════════
    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=BG_DARK, fg=ACCENT2,
                 font=FONT_HEAD).pack(anchor="w", pady=(12,4))
        ttk.Separator(parent, orient="horizontal",
                      style="Dark.TSeparator").pack(fill="x", pady=(0,8))

    def _setting_row(self, parent, label, key, default, show=None):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=BG_DARK, fg=TEXT_SEC,
                 font=FONT_BODY, width=16, anchor="w").pack(side="left")
        var = tk.StringVar(value=self.settings.get(key, default))
        setattr(self, f"_set_{key}", var)
        kw = {"show": show} if show else {}
        tk.Entry(row, textvariable=var, bg="#0f1e2e", fg=TEXT_PRI,
                 font=FONT_BODY, bd=1, relief="solid",
                 insertbackground=TEXT_PRI, **kw).pack(side="left", fill="x",
                                                        expand=True, ipady=4)

    # ════════════════════════════════════════════════
    # منطق الأزرار
    # ════════════════════════════════════════════════
    def _pick_from_contacts(self):
        """نافذة اختيار موظف من جهات الاتصال"""
        emps = self.contacts_db.get_employees(active_only=True)
        if not emps:
            messagebox.showinfo("جهات الاتصال",
                "لا توجد جهات اتصال بعد.\nأضفها من تبويب 👥 جهات الاتصال")
            return

        win = tk.Toplevel(self)
        win.title("اختر موظفاً")
        win.configure(bg=BG_DARK)
        win.geometry("600x420")
        win.grab_set()

        tk.Label(win, text="👥 اختر موظفاً من جهات الاتصال",
                 bg=BG_DARK, fg=ACCENT2, font=FONT_HEAD).pack(pady=(12,8))

        # شريط بحث
        sv = tk.StringVar()
        def on_search(*_):
            q = sv.get().lower()
            lb.delete(0,"end")
            for e in emps:
                line = f"{e.get('name','')}  |  {e.get('sub_dept','')}  |  {e.get('email','')}  |  {e.get('whatsapp','')}"
                if q in line.lower():
                    lb.insert("end", line)
                    lb.itemdata.append(e)
        tk.Entry(win, textvariable=sv, bg=BG_INPUT, fg=TEXT_PRI,
                 font=FONT_BODY, bd=1, relief="solid",
                 insertbackground=TEXT_PRI).pack(fill="x", padx=16, ipady=5)
        sv.trace("w", on_search)

        # قائمة الموظفين
        lf = tk.Frame(win, bg=BG_CARD)
        lf.pack(fill="both", expand=True, padx=16, pady=8)
        sb2 = tk.Scrollbar(lf); sb2.pack(side="right", fill="y")
        lb = tk.Listbox(lf, bg=BG_CARD, fg=TEXT_PRI, font=FONT_SMALL,
                        selectbackground=ACCENT, selectforeground=WHITE,
                        borderwidth=0, highlightthickness=0,
                        yscrollcommand=sb2.set, activestyle="none")
        lb.itemdata = []
        lb.pack(fill="both", expand=True)
        sb2.config(command=lb.yview)

        # تعبئة القائمة
        for e in emps:
            line = f"{e.get('name','')}  |  {e.get('sub_dept','')}  |  {e.get('email','')}  |  {e.get('whatsapp','')}"
            lb.insert("end", line)
            lb.itemdata.append(e)

        def select_emp(event=None):
            sel = lb.curselection()
            if not sel: return
            idx = sel[0]
            if idx >= len(lb.itemdata): return
            emp = lb.itemdata[idx]
            # تعيين اسم المرسل
            self._from_var.set(f"{emp.get('name','')} — {emp.get('sub_dept','')}")
            # تعيين القسم تلقائياً
            dept_key = self.contacts_db._dept_to_key(emp.get("sub_dept",""))
            dept_map_rev = {v:k for k,v in {
                "ran":"فريق شبكة الراديو RAN","core":"فريق شبكة النواة Core",
                "ops":"إدارة العمليات","quality":"إدارة الجودة",
                "safety":"إدارة السلامة","civil":"الإدارة الإنشائية",
                "cost":"إدارة التكاليف","contract":"إدارة العقود",
                "procure":"إدارة المشتريات","supply":"المخازن وسلاسل التوريد والنقل",
                "hr":"الموارد البشرية","pmo":"مكتب إدارة المشاريع PMO",
                "risk":"إدارة المخاطر","it":"تقنية المعلومات"
            }.items()}
            if dept_key in dept_map_rev:
                self._dept_var.set(dept_map_rev[dept_key])
            win.destroy()

        lb.bind("<Double-Button-1>", select_emp)

        btn_row = tk.Frame(win, bg=BG_DARK)
        btn_row.pack(fill="x", padx=16, pady=(0,12))
        tk.Button(btn_row, text="✓ اختيار",
                  bg=SUCCESS, fg=WHITE, font=FONT_BODY,
                  bd=0, padx=16, pady=7, cursor="hand2",
                  command=select_emp).pack(side="right", padx=(6,0))
        tk.Button(btn_row, text="إلغاء",
                  bg=BG_MID, fg=TEXT_PRI, font=FONT_BODY,
                  bd=0, padx=16, pady=7, cursor="hand2",
                  command=win.destroy).pack(side="right")
        win.wait_window()

    def _resolve_dept(self, sender: str, current_dept: str) -> tuple:
        """
        التعرف التلقائي على قسم المرسل من جهات الاتصال.
        يُعيد (dept_key, employee_name) إذا وُجد، وإلا يبقى كما هو.
        """
        sender_clean = sender.strip().lower()
        # فحص البريد الإلكتروني
        emp = self.contacts_db.find_by_email(sender_clean)
        if not emp:
            # فحص الواتساب
            emp = self.contacts_db.find_by_whatsapp(sender_clean)
        if not emp:
            # فحص من خريطة البريد في الإعدادات
            email_map = self.settings.get("email_dept_map", {})
            for addr, dept_key in email_map.items():
                if addr.lower() in sender_clean or sender_clean in addr.lower():
                    return dept_key, sender
            # فحص من خريطة الواتساب
            wa_map = self.settings.get("whatsapp_groups", {})
            wa_clean = sender_clean.replace("+","").replace(" ","").replace("-","")
            for num, dept_key in wa_map.items():
                if num.replace("+","").replace(" ","") == wa_clean:
                    return dept_key, sender
            return current_dept, sender
        dept_key = self.contacts_db._dept_to_key(emp.get("sub_dept",""))
        display  = f"{emp.get('name',sender)} — {emp.get('sub_dept','')}"
        return dept_key, display

    def _add_report(self):
        content = self._content_box.get("1.0","end").strip()
        if not content:
            messagebox.showwarning("تنبيه","يرجى إدخال محتوى التقرير")
            return
        src      = self._src_var.get().split()[0] if self._src_var.get() else "manual"
        dept     = self._dept_var.get()
        sender   = self._from_var.get().strip()
        # محاولة التعرف التلقائي على القسم من جهات الاتصال
        auto_dept, auto_sender = self._resolve_dept(sender, dept)
        if auto_dept != dept and auto_dept != "unknown":
            dept   = auto_dept
            sender = auto_sender
            self._log(f"  🔍 تعرّف تلقائي: [{sender}] ← قسم [{dept}]")
        rep  = {
            "id"     : f"r_{datetime.datetime.now().strftime('%H%M%S%f')}",
            "source" : src,
            "dept"   : dept,
            "from"   : sender,
            "date"   : self._date_var.get(),
            "content": content,
        }
        self.reports.append(rep)
        self._content_box.delete("1.0","end")
        self._refresh_reports_list()
        self._log(f"✓ تمت إضافة تقرير [{dept}] من [{sender}]")

    def _import_file(self):
        path = filedialog.askopenfilename(
            title="استيراد ملف",
            filetypes=[("Text & PDF","*.txt *.pdf"),("All","*.*")]
        )
        if not path: return
        content = ""
        ext = Path(path).suffix.lower()
        if ext == ".pdf":
            try:
                import PyPDF2
                with open(path,"rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    content = "\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                content = f"[ملف PDF: {Path(path).name} — يحتاج مكتبة PyPDF2]"
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        rep = {
            "id"     : f"file_{datetime.datetime.now().strftime('%H%M%S')}",
            "source" : "file",
            "dept"   : self._dept_var.get(),
            "from"   : Path(path).name,
            "date"   : datetime.date.today().isoformat(),
            "content": content[:5000],
        }
        self.reports.append(rep)
        self._refresh_reports_list()
        self._log(f"✓ استُورد الملف: {Path(path).name}")

    def _delete_report(self):
        sel = self.reports_list.curselection()
        if not sel: return
        idx = sel[0]
        if idx < len(self.reports):
            del self.reports[idx]
            self._refresh_reports_list()

    def _view_report(self, event=None):
        sel = self.reports_list.curselection()
        if not sel: return
        idx = sel[0]
        if idx >= len(self.reports): return
        r = self.reports[idx]
        win = tk.Toplevel(self)
        win.title(f"عرض التقرير — {r.get('from','')}")
        win.configure(bg=BG_DARK)
        win.geometry("700x500")
        for k, v in [("المصدر",r.get("source","")),("القسم",r.get("dept","")),
                     ("من",r.get("from","")),("التاريخ",r.get("date",""))]:
            row = tk.Frame(win, bg=BG_DARK); row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{k}:", bg=BG_DARK, fg=TEXT_SEC,
                     font=FONT_SMALL, width=8, anchor="w").pack(side="left")
            tk.Label(row, text=v, bg=BG_DARK, fg=TEXT_PRI,
                     font=FONT_SMALL).pack(side="left")
        box = scrolledtext.ScrolledText(win, bg=BG_CARD, fg=TEXT_PRI,
                                         font=FONT_BODY, wrap="word")
        box.pack(fill="both", expand=True, padx=12, pady=8)
        box.insert("end", r.get("content",""))
        box.config(state="disabled")

    def _load_samples(self):
        samples = [
            {"id":"s1","source":"email","dept":"ran","from":"م. أحمد الورفلي — فريق RAN","date":"2026-05-15",
             "content":"اكتملت عملية تركيب 14 برجاً من أصل 23 في منطقة سرت. تأخر في توريد وحدات Massive MIMO بسبب مشكلة جمركية. المتوقع وصول الشحنة خلال 18 يوماً."},
            {"id":"s2","source":"whatsapp","dept":"core","from":"م. سالم المشري — فريق Core","date":"2026-05-16",
             "content":"اكتمل تثبيت خوادم MEC في مصراتة 100%. مشكلة في ضعف ترددات الباك هول بين سرت والجفرة. يحتاج مراجعة فورية."},
            {"id":"s3","source":"system","dept":"cost","from":"إدارة المالية — ERP","date":"2026-05-17",
             "content":"إجمالي المصروف 4.2 مليون دينار من أصل 7 مليون (60%). انحراف 8% بسبب تكاليف الشحن. دفعة 800 ألف مستحقة 2026-06-01."},
            {"id":"s4","source":"email","dept":"quality","from":"م. فاطمة الدغيلي — الجودة","date":"2026-05-18",
             "content":"فحص 10 محطات وفق 3GPP Release 16. 8 اجتازت. محطتان في الجفرة بحاجة إعادة معايرة."},
            {"id":"s5","source":"whatsapp","dept":"safety","from":"م. يوسف العريبي — السلامة","date":"2026-05-17",
             "content":"تسجيل حادثتين بسيطتين. موقع سرت برج 17 يحتاج سياج أمان. 3 تحذيرات لمقاولين. درجة السلامة 87%."},
            {"id":"s6","source":"system","dept":"supply","from":"م. خالد بوزيد — المخازن","date":"2026-05-18",
             "content":"مخزون مصراتة 72%. شحنة MIMO عالقة في الجمارك. 45 ألف دينار وقود إضافي في الجفرة."},
        ]
        self.reports.extend(samples)
        self._refresh_reports_list()
        self._log(f"✓ تم تحميل {len(samples)} تقارير نموذجية")

    def _refresh_reports_list(self):
        self.reports_list.delete(0,"end")
        for r in self.reports:
            src  = r.get("source","")
            icon = {"email":"📧","whatsapp":"💬","system":"🖥️","file":"📄"}.get(src,"✍️")
            self.reports_list.insert("end",
                f"{icon} [{r.get('dept',''):8}] {r.get('from','')[:30]} | {r.get('date','')}")
        if hasattr(self,"_info_lbl"):
            self._info_lbl.config(text=f"إجمالي التقارير: {len(self.reports)}")

    def _refresh_files_list(self):
        if not hasattr(self, "_files_list"): return
        self._files_list.delete(0,"end")
        for f in sorted(REPORTS.glob("*.json"), reverse=True)[:20]:
            self._files_list.insert("end", f"📋 {f.name}")
        for f in sorted(REPORTS.glob("*.pdf"), reverse=True)[:10]:
            self._files_list.insert("end", f"📄 {f.name}")
        for f in sorted(REPORTS.glob("*.xlsx"), reverse=True)[:10]:
            self._files_list.insert("end", f"📊 {f.name}")

    # ── تشغيل التحليل ──
    def _run_analysis(self):
        # مزامنة جهات الاتصال
        self._sync_contacts_to_config()
        # جمع التقارير الجديدة من المصادر الحقيقية أولاً
        self._log("🔄 جاري جمع البيانات من المصادر...")
        live = self.hub.collect_all()
        if live:
            self.reports.extend(live)
            self._refresh_reports_list()
            self._log(f"✓ وصل {len(live)} تقرير جديد من المصادر")
        if not self.reports:
            messagebox.showwarning("تنبيه",
                "لا توجد تقارير.\nأضف تقارير يدوياً أو تأكد من إعداد البريد/ERP")
            return
        self._run_btn.config(state="disabled", text="⏳ جاري التحليل...")
        self._reset_agent_cards()
        self.agents = AgentsEngine(self.ai_engine, log_fn=self._log)

        def worker():
            try:
                self.results = self.agents.run_all(
                    self.reports,
                    progress_cb=self._update_progress
                )
                self.after(0, self._on_analysis_done)
            except Exception as e:
                self.after(0, lambda: self._on_analysis_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_done(self):
        self._run_btn.config(state="normal", text="⚡ بدء التحليل الشامل")
        self._status_run.config(text="✓ اكتمل التحليل", fg=SUCCESS)
        self._refresh_dashboard()
        self._refresh_files_list()
        messagebox.showinfo("اكتمل","✓ اكتمل التحليل الشامل!\nالنتائج متاحة في لوحة التحكم.")

    def _on_analysis_error(self, err):
        self._run_btn.config(state="normal", text="⚡ بدء التحليل الشامل")
        self._log(f"✗ خطأ: {err}")
        messagebox.showerror("خطأ", f"فشل التحليل:\n{err}")

    def _update_progress(self, pct):
        self.after(0, lambda: [
            self._progress_var.set(pct),
            self._prog_lbl.config(text=f"{pct}%")
        ])

    def _reset_agent_cards(self):
        for aid, card in self._agent_cards.items():
            card["frame"].config(highlightbackground=BG_MID)
            card["status"].config(text="⏸", fg=TEXT_DIM)

    # ── لوحة التحكم ──
    def _refresh_dashboard(self):
        if not self.results:
            return
        chief = self.results.get("chief", {})
        health = chief.get("overall_health", "غير محدد")
        color  = {
            "جيد"    : SUCCESS,
            "متوسط"  : WARNING,
            "حرج"    : DANGER,
        }.get(health, TEXT_SEC)
        self._health_lbl.config(
            text=f"● الحالة العامة للمشروع: {health}",
            fg=color
        )

        # KPIs
        for w in self._kpi_frame.winfo_children():
            w.destroy()
        kpis = chief.get("kpis", [])[:6]
        for i, kpi in enumerate(kpis):
            c = {
                "جيد"   : SUCCESS,
                "تحذير" : WARNING,
                "حرج"   : DANGER,
            }.get(kpi.get("status",""), TEXT_SEC)
            card = tk.Frame(self._kpi_frame, bg=BG_CARD, bd=1,
                            highlightbackground=c, highlightthickness=1)
            card.grid(row=0, column=i, padx=4, pady=4, sticky="nsew")
            self._kpi_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=str(kpi.get("value","")),
                     bg=BG_CARD, fg=c,
                     font=("Arial",16,"bold")).pack(pady=(8,2))
            tk.Label(card, text=kpi.get("name",""),
                     bg=BG_CARD, fg=TEXT_SEC, font=FONT_SMALL).pack(pady=(0,4))
            tk.Label(card, text=str(kpi.get("trend","→")),
                     bg=BG_CARD, fg=c, font=("Arial",12)).pack(pady=(0,6))

        # الملخص
        self._summary_box.config(state="normal")
        self._summary_box.delete("1.0","end")
        self._summary_box.insert("end", chief.get("executive_summary","لا يوجد ملخص بعد"))
        self._summary_box.config(state="disabled")

        # خطة العمل
        self._actions_box.config(state="normal")
        self._actions_box.delete("1.0","end")
        for act in chief.get("top_actions", []):
            p = act.get("priority","-")
            self._actions_box.insert("end",
                f"[{p}] {act.get('action','')}\n"
                f"    المسؤول: {act.get('owner','')}\n"
                f"    الموعد: {act.get('deadline','')}\n"
                f"    التأثير: {act.get('impact','')}\n\n"
            )
        self._actions_box.config(state="disabled")

    # ── التصدير ──
    def _export_pdf(self):
        if not self.results:
            messagebox.showwarning("تنبيه","شغّل التحليل أولاً")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")],
            initialfile=f"LTT_Report_{datetime.date.today()}.pdf"
        )
        if not path: return
        self._log("⏳ جاري توليد PDF...")
        threading.Thread(target=self._do_export_pdf, args=(path,), daemon=True).start()

    def _do_export_pdf(self, path):
        try:
            from exporters import export_pdf
            export_pdf(self.results, path)
            self.after(0, lambda: [
                self._log(f"✓ PDF محفوظ: {path}"),
                messagebox.showinfo("تم","✓ تم حفظ التقرير PDF")
            ])
            # إرسال بالبريد تلقائياً إن كان مضبوطاً
            recip = self.settings.get("report_recipients", [])
            if recip and isinstance(recip, str):
                recip = [r.strip() for r in recip.split(",") if r.strip()]
            if recip:
                html = build_report_html(self.results)
                chief  = self.results.get("chief", {})
                health = chief.get("overall_health", "")
                subj   = f"تقرير LTT 4G/5G — {health} — {datetime.date.today()}"
                ok = self.hub.send_report(recip, subj, html, [path])
                if ok:
                    self.after(0, lambda: self._log(f"📧 أُرسل التقرير إلى: {recip}"))
        except ImportError:
            self.after(0, lambda: messagebox.showerror(
                "خطأ","يحتاج مكتبة reportlab\nشغّل: pip install reportlab"))
        except Exception as e:
            self.after(0, lambda: self._log(f"✗ خطأ PDF: {e}"))

    def _export_excel(self):
        if not self.results:
            messagebox.showwarning("تنبيه","شغّل التحليل أولاً")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel","*.xlsx")],
            initialfile=f"LTT_Report_{datetime.date.today()}.xlsx"
        )
        if not path: return
        self._log("⏳ جاري توليد Excel...")
        threading.Thread(target=self._do_export_excel, args=(path,), daemon=True).start()

    def _do_export_excel(self, path):
        try:
            from exporters.report_exporter import export_excel
            export_excel(self.results, path)
            self.after(0, lambda: [
                self._log(f"✓ Excel محفوظ: {path}"),
                messagebox.showinfo("تم","✓ تم حفظ تقرير Excel")
            ])
        except ImportError:
            self.after(0, lambda: messagebox.showerror(
                "خطأ","يحتاج مكتبة openpyxl\nشغّل: pip install openpyxl"))
        except Exception as e:
            self.after(0, lambda: self._log(f"✗ خطأ Excel: {e}"))

    # ── الإعدادات ──
    def _save_settings(self):
        for key in ["ollama_url","ollama_model","claude_api_key",
                   "email_user","email_password",
                   "report_recipients","erp_folder"]:
            var = getattr(self, f"_set_{key}", None)
            if var:
                self.settings[key] = var.get()
        self.settings["ai_backend"] = self._ai_var.get()
        with open(SETTINGS_F,"w",encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
        self.ai_engine = AIEngine(self.settings)
        self._conn_lbl.config(text="✓ حُفظت الإعدادات", fg=SUCCESS)

    def _test_connection(self):
        self._save_settings()
        self._conn_lbl.config(text="⏳ جاري الاختبار...", fg=WARNING)
        def worker():
            ok, msg = self.ai_engine.test_connection()
            self.after(0, lambda: self._conn_lbl.config(
                text=f"{'✓' if ok else '✗'} {msg}",
                fg=SUCCESS if ok else DANGER
            ))
            if ok:
                self.after(0, lambda: self.status_lbl.config(
                    text=f"● {self.settings.get('ai_backend','ollama')} متصل",
                    fg=SUCCESS
                ))
        threading.Thread(target=worker, daemon=True).start()

    def _pull_ollama_model(self):
        model = self.settings.get("ollama_model","llama3.2")
        if messagebox.askyesno("تأكيد",
            f"سيتم تحميل نموذج {model}\nقد يستغرق هذا بعض الوقت. هل تريد المتابعة؟"):
            self._log(f"⏳ جاري تحميل نموذج {model}...")
            def worker():
                try:
                    result = subprocess.run(
                        ["ollama", "pull", model],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        self.after(0, lambda: self._log(f"✓ تم تحميل {model}"))
                    else:
                        self.after(0, lambda: self._log(f"✗ فشل: {result.stderr}"))
                except FileNotFoundError:
                    self.after(0, lambda: self._log("✗ Ollama غير مثبت — حمّله من ollama.com"))
            threading.Thread(target=worker, daemon=True).start()

    # ── سجل التشغيل ──
    def _log(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.after(0, lambda: self._append_log(line))

    def _append_log(self, line: str):
        if not hasattr(self,"_log_box"): return
        self._log_box.config(state="normal")
        self._log_box.insert("end", line)
        self._log_box.see("end")
        self._log_box.config(state="disabled")
        # حفظ في ملف
        with open(LOGS/"app.log","a",encoding="utf-8") as f:
            f.write(line)

    def _clear_log(self):
        self._log_box.config(state="normal")
        self._log_box.delete("1.0","end")
        self._log_box.config(state="disabled")

    # ── فحص Ollama عند البدء ──
    def _check_ollama(self):
        import urllib.request, urllib.error
        url = self.settings.get("ollama_url","http://localhost:11434")
        try:
            with urllib.request.urlopen(f"{url}/api/tags", timeout=3):
                self.status_lbl.config(text="● Ollama متصل", fg=SUCCESS)
                self._log("✓ Ollama يعمل بنجاح")
        except Exception:
            backend = self.settings.get("ai_backend","ollama")
            if backend == "ollama":
                self.status_lbl.config(text="● Ollama غير متصل", fg=DANGER)
                self._log("⚠ Ollama غير مشغّل — شغّله أو اذهب للإعدادات")

    # ── مساعدات عامة ──
    def _open_url(self, url: str):
        import webbrowser
        webbrowser.open(url)

    def _load_settings(self) -> dict:
        if SETTINGS_F.exists():
            try:
                with open(SETTINGS_F,encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "ai_backend"   : "ollama",
            "ollama_url"   : "http://localhost:11434",
            "ollama_model" : "llama3.2",
            "claude_api_key": "",
        }

    def _load_sample_reports(self) -> list:
        sample = BASE_DIR / "data" / "sample_reports.json"
        if sample.exists():
            try:
                with open(sample,encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _load_latest_results(self) -> dict:
        latest = REPORTS / "latest.json"
        if latest.exists():
            try:
                with open(latest,encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


# ════════════════════════════════════════════════════
# نقطة الدخول
# ════════════════════════════════════════════════════
    def _sync_contacts_to_config(self):
        """مزامنة جهات الاتصال مع إعدادات النظام تلقائياً"""
        try:
            cfg = self.contacts_db.export_to_config()
            # دمج مع الإعدادات الحالية
            if cfg["email_dept_map"]:
                self.settings["email_dept_map"] = cfg["email_dept_map"]
            if cfg["whatsapp_groups"]:
                self.settings["whatsapp_groups"] = cfg["whatsapp_groups"]
            # تحديث محرك الذكاء الاصطناعي
            self.ai_engine = AIEngine(self.settings)
            count_e = len(cfg["email_dept_map"])
            count_w = len(cfg["whatsapp_groups"])
            if count_e or count_w:
                self._log(f"✓ مزامنة جهات الاتصال: {count_e} بريد, {count_w} واتساب")
        except Exception as e:
            self._log(f"⚠ تحذير مزامنة: {e}")

    def _identify_sender(self, sender_email: str) -> str:
        """تحديد قسم المرسل من قاعدة جهات الاتصال"""
        emp = self.contacts_db.find_by_email(sender_email)
        if emp:
            return self.contacts_db._dept_to_key(emp.get("sub_dept", ""))
        return "unknown"


# ════════════════════════════════════════════════════
# نافذة التثبيت المرئية
# ════════════════════════════════════════════════════
def show_installer():
    """
    نافذة صغيرة تظهر عند أول تشغيل وتثبّت المكتبات الناقصة
    مع شريط تقدم مرئي — تُغلق تلقائياً عند الانتهاء
    """
    PACKAGES = [
        ("openpyxl",        "openpyxl"),
        ("reportlab",       "reportlab"),
        ("arabic_reshaper", "arabic-reshaper"),
        ("bidi",            "python-bidi"),
        ("PyPDF2",          "PyPDF2"),
        ("PIL",             "Pillow"),
        ("dotenv",          "python-dotenv"),
        ("schedule",        "schedule"),
    ]

    missing = []
    for module, pkg in PACKAGES:
        try:
            __import__(module)
        except ImportError:
            missing.append((module, pkg))

    if not missing:
        return  # كل شيء مثبت — ابدأ مباشرة

    # نافذة التثبيت
    root = tk.Tk()
    root.title("جاري الإعداد...")
    root.configure(bg="#0D1B2A")
    root.geometry("480x320")
    root.resizable(False, False)
    try:
        root.eval("tk::PlaceWindow . center")
    except Exception:
        pass

    tk.Label(root, text="⚡ نظام LTT PM Intelligence",
             bg="#0D1B2A", fg="#38BDF8",
             font=("Arial", 15, "bold")).pack(pady=(20, 4))
    tk.Label(root, text="جاري تثبيت المكتبات المطلوبة...",
             bg="#0D1B2A", fg="#94A3B8",
             font=("Arial", 10)).pack(pady=(0, 12))

    # شريط التقدم
    prog_var = tk.IntVar(value=0)
    prog = ttk.Progressbar(root, variable=prog_var,
                           maximum=len(missing),
                           length=400)
    prog.pack(pady=4)

    # تسمية الحالة
    status_var = tk.StringVar(value="جاري الفحص...")
    status_lbl = tk.Label(root, textvariable=status_var,
                          bg="#0D1B2A", fg="#E2E8F0",
                          font=("Arial", 10))
    status_lbl.pack(pady=6)

    # سجل النصوص
    log_box = tk.Text(root, height=6, bg="#0f1e2e", fg="#6ee7b7",
                      font=("Courier New", 9), bd=0,
                      state="disabled", wrap="word")
    log_box.pack(fill="x", padx=20, pady=4)

    def log(msg):
        log_box.config(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.config(state="disabled")
        root.update()

    def do_install():
        success_all = True
        for i, (module, pkg) in enumerate(missing):
            status_var.set(f"تثبيت {pkg} ({i+1}/{len(missing)})...")
            log(f"⏳ {pkg}...")
            root.update()
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg,
                 "--quiet", "--no-warn-script-location"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                log(f"  ✓ {pkg} تم تثبيته")
            else:
                log(f"  ✗ {pkg} فشل: {result.stderr.strip()[:60]}")
                success_all = False
            prog_var.set(i + 1)
            root.update()

        if success_all:
            status_var.set("✓ اكتمل التثبيت — جاري تشغيل التطبيق...")
            status_lbl.config(fg="#10B981")
        else:
            status_var.set("⚠ بعض المكتبات فشلت — شغّل: pip install openpyxl reportlab")
            status_lbl.config(fg="#F59E0B")
        root.after(1800, root.destroy)

    # تشغيل التثبيت بعد ظهور النافذة
    root.after(300, do_install)
    root.mainloop()


if __name__ == "__main__":
    show_installer()   # تثبيت المكتبات الناقصة أولاً
    app = LTTApp()
    app.mainloop()
