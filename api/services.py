"""AppService — UI-agnostic singleton mirroring the Qt AppController.

Same state (settings, contacts, connector hub, AI engine, report queue, latest
results), same guard flags, same Arabic notify/log strings as
backend/controller.py — but Qt-free. State changes are broadcast to subscribers
as plain event dicts; long-running work (collect / file parsing / engine+email
tests / analysis) runs on daemon threads exactly like the controller.

Event names: notify, log, progress, agent_state, reports_changed, dash_changed,
analysis_done, analysis_failed, connection_tested, email_tested, export_done,
export_failed, testing, busy, engine_changed, settings_changed, models_fetched,
wa_qr, wa_status.
"""
import datetime
import json
import logging
import threading
from pathlib import Path

from core import (AIEngine, AgentsEngine, ContactsDB, WORKER_AGENTS,
                  export_pdf, export_excel)
from core.errors import friendly_error, friendly_fs_error
from core.hijri import dual_label
from core.paths import DATA_DIR, BUNDLE_DIR
from connectors import (ConnectorHub, WhatsAppHelper, build_report_html,
                        read_file_to_report)
from backend.settings_bridge import load_settings, save_settings

log = logging.getLogger(__name__)

REPORTS   = DATA_DIR / "reports"                  # writable output
SAMPLES_F = BUNDLE_DIR / "sample_reports.json"    # shipped demo input
LATEST_F  = REPORTS / "latest.json"

# agent id -> Arabic display name (worker agents + chief coordinator)
# — copied verbatim from backend/models.py (which is Qt-bound).
AGENT_NAMES = {
    "ops":      "العمليات الميدانية",
    "quality":  "الجودة والامتثال",
    "safety":   "السلامة المهنية",
    "civil":    "الأعمال الإنشائية",
    "cost":     "التكاليف والميزانية",
    "contract": "العقود والشؤون القانونية",
    "procure":  "المشتريات والموردين",
    "supply":   "المخازن وسلاسل التوريد",
    "risk":     "إدارة المخاطر",
    "schedule": "الجدول الزمني",
    "chief":    "التنسيق المركزي",
}
AGENT_ORDER = ["ops", "quality", "safety", "civil", "cost", "contract",
               "procure", "supply", "risk", "schedule", "chief"]

# settings keys that make up an engine-profile snapshot
# — copied verbatim from backend/controller.py (ENGINE_KEYS).
ENGINE_KEYS = ("ai_backend", "ai_timeout", "ollama_url", "ollama_model",
               "claude_api_key", "claude_model", "openai_api_key",
               "openai_base_url", "openai_model", "gemini_api_key",
               "gemini_model", "azure_endpoint", "azure_api_key",
               "azure_deployment", "azure_api_version")


class AppService:
    """The single object the web layer talks to (mirrors AppController)."""

    def __init__(self):
        self._lock     = threading.RLock()
        self._settings = load_settings()
        self._contacts = ContactsDB()
        self._hub      = ConnectorHub(self._settings, self._contacts)
        self._ai       = AIEngine(self._settings)
        self._reports  = []            # in-memory queue of report dicts
        self._agents   = {a: "idle" for a in AGENT_ORDER}
        self._results  = {}
        self._dash     = {}
        self._date     = ""
        self._busy     = False
        self._online   = False
        self._status   = "غير متصل"
        self._testing_engine = False
        self._testing_email  = False
        self._collecting = False
        self._adding     = False
        self._models      = []
        self._models_busy = False
        self._wa_linked    = False
        self._wa_phone     = ""
        self._wa_starting  = False
        self._wa_qr_matrix = []
        self._wa_proc      = None
        self._subscribers = []
        self._hub.set_logger(lambda m: self._emit("log", message=str(m)))
        self._hub.set_event_handler(self._on_wa_event)
        self._load_latest()
        self._start_whatsapp_if_enabled()

    # ───────────────────────── events ─────────────────────────
    def subscribe(self, cb):
        """Register cb(event_dict). Returns an unsubscribe function."""
        with self._lock:
            self._subscribers.append(cb)

        def unsubscribe():
            with self._lock:
                if cb in self._subscribers:
                    self._subscribers.remove(cb)
        return unsubscribe

    def _emit(self, event_type, **payload):
        event = {"type": event_type, **payload}
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(event)
            except Exception:
                pass

    # ───────────────────────── read-only state ─────────────────────────
    @property
    def settings(self):
        return self._settings

    @property
    def ai(self):
        return self._ai

    @property
    def reports(self):
        with self._lock:
            return list(self._reports)

    @property
    def report_count(self):
        with self._lock:
            return len(self._reports)

    @property
    def agents(self):
        with self._lock:
            return [{"id": a, "name": AGENT_NAMES[a], "state": self._agents[a]}
                    for a in AGENT_ORDER]

    @property
    def agent_count(self):
        return len(WORKER_AGENTS) + 1

    @property
    def results(self):
        return self._results

    @property
    def dash(self):
        return self._dash

    @property
    def report_date(self):
        return self._date

    @property
    def busy(self):
        return self._busy

    @property
    def engine_online(self):
        return self._online

    @property
    def engine_status(self):
        return self._status

    @property
    def testing_engine(self):
        return self._testing_engine

    @property
    def testing_email(self):
        return self._testing_email

    @property
    def models(self):
        with self._lock:
            return list(self._models)

    @property
    def models_busy(self):
        return self._models_busy

    @property
    def wa_state(self):
        with self._lock:
            return {"linked":   self._wa_linked,
                    "phone":    self._wa_phone,
                    "starting": self._wa_starting,
                    "qr":       list(self._wa_qr_matrix)}

    @property
    def engine_profiles(self):
        """ملفات المحرّك المحفوظة: [{name, ai_backend}]."""
        return [{"name": p.get("name", ""),
                 "ai_backend": p.get("ai_backend", "ollama")}
                for p in self._settings.get("engine_profiles", [])]

    @property
    def exports(self):
        """ملفات التقارير المُصدَّرة (PDF/XLSX) — الأحدث أولاً."""
        items = []
        try:
            REPORTS.mkdir(exist_ok=True)
            files = [p for p in REPORTS.iterdir()
                     if p.suffix.lower() in (".pdf", ".xlsx")]
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for p in files[:20]:
                st = p.stat()
                items.append({
                    "name":   p.name,
                    "sizeKb": max(1, int(st.st_size / 1024)),
                    "date":   datetime.datetime.fromtimestamp(
                        st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
        except Exception:
            pass
        return items

    @property
    def recipients(self):
        """مستلمو التقرير الحاليون — report_recipients أو مفاتيح email_dept_map."""
        recips = (self._settings.get("report_recipients")
                  or list(self._settings.get("email_dept_map", {}).keys()))
        return list(recips or [])

    @property
    def today_label(self):
        return dual_label()

    @property
    def reports_dir(self):
        return str(REPORTS)

    def snapshot(self):
        """Full state for a freshly connected client."""
        with self._lock:
            return {
                "dash":          self._dash,
                "date":          self._date,
                "has_results":   bool(self._results),
                "reports":       list(self._reports),
                "reports_count": len(self._reports),
                "agents":        self.agents,
                "busy":          self._busy,
                "engine_online": self._online,
                "engine_status": self._status,
                "testing": {
                    "engine": self._testing_engine,
                    "email":  self._testing_email,
                    "active": self._testing_engine or self._testing_email,
                },
                "models":      self.models,
                "models_busy": self._models_busy,
                "wa":          self.wa_state,
            }

    # ───────────────────────── input actions ─────────────────────────
    def load_samples(self):
        try:
            with open(SAMPLES_F, encoding="utf-8") as f:
                data = json.load(f)
            reps = data.get("reports", data) if isinstance(data, dict) else data
            with self._lock:
                self._reports.extend(reps)
            self._emit_reports_changed()
            self._emit("notify", message=f"حُمّلت {len(reps)} تقارير نموذجية")
            return len(reps)
        except Exception as e:
            log.warning("sample load failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر تحميل النماذج: {friendly_fs_error(e)}")
            return 0

    def collect_reports(self):
        """Start async collection (IMAP/ERP/WhatsApp). Returns False if already running."""
        if self._collecting:
            return False
        self._collecting = True
        threading.Thread(target=self._run_collect, daemon=True).start()
        return True

    def _run_collect(self):
        """جمع التقارير (IMAP/ERP/HTTP) على خيط منفصل حتى لا تتجمّد الواجهة."""
        try:
            reps = self._hub.collect_all()
        except Exception as e:
            log.warning("report collection failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر الجمع: {friendly_error(str(e))}")
            self._collecting = False
            return
        self._collecting = False
        reps = list(reps or [])
        with self._lock:
            self._reports.extend(reps)
        self._emit_reports_changed()
        self._emit("notify", message=(f"جُمِّع {len(reps)} تقرير من المصادر"
                                      if reps else "لا توجد تقارير جديدة"))

    def add_files(self, paths):
        """Parse files off-thread, then queue the parsed reports. False if busy."""
        paths = [str(p) for p in (paths or []) if p]
        if not paths:
            self._emit("notify", message="لم تُختَر ملفات")
            return False
        if self._adding:
            return False
        self._adding = True
        threading.Thread(target=self._run_add_files, args=(paths,),
                         daemon=True).start()
        return True

    def _run_add_files(self, paths):
        """تفكيك الملفات (Word/Excel/PDF/CSV/TXT/JSON) خارج الخيط الرئيسي."""
        added, failed = [], []
        for p in paths:
            try:
                rep = read_file_to_report(p, source="ملف")
                if rep:
                    added.append(rep)
                else:
                    failed.append(Path(p).name)
            except Exception:
                failed.append(Path(p).name)
        self._adding = False
        if added:
            with self._lock:
                self._reports.extend(added)
            self._emit_reports_changed()
        if added and failed:
            msg = f"أُضيف {len(added)} ملف — تعذّر: {'، '.join(failed)}"
        elif added:
            msg = f"أُضيف {len(added)} ملف"
        elif failed:
            msg = f"تعذّرت قراءة: {'، '.join(failed)}"
        else:
            msg = "لم تُختَر ملفات"
        self._emit("notify", message=msg)

    def add_report(self, report):
        """Manual entry. Returns the queued dict, or None when content is empty."""
        r = dict(report or {})
        if not r.get("content"):
            self._emit("notify", message="أدخل نص التقرير أولاً")
            return None
        r.setdefault("date", datetime.date.today().isoformat())
        with self._lock:
            self._reports.append(r)
        self._emit_reports_changed()
        return r

    def remove_report(self, row):
        with self._lock:
            if not 0 <= row < len(self._reports):
                return False
            self._reports.pop(row)
        self._emit_reports_changed()
        return True

    def clear_reports(self):
        with self._lock:
            self._reports.clear()
        self._emit_reports_changed()

    # ───────────────────────── analysis ─────────────────────────
    def run_analysis(self):
        """Start the agent fleet off-thread. False when busy / no reports."""
        if self._busy:
            return False
        with self._lock:
            if not self._reports:
                self._emit("notify",
                           message="لا توجد تقارير للتحليل — حمّل النماذج أو أضف تقريراً")
                return False
            reps = list(self._reports)
            for a in self._agents:
                self._agents[a] = "idle"
        self._set_busy(True)
        self._emit("progress", percent=0)
        threading.Thread(target=self._run_analysis, args=(reps,),
                         daemon=True).start()
        return True

    def _run_analysis(self, reps):
        try:
            engine = AgentsEngine(self._ai)
            engine.log = lambda m: self._emit("log", message=str(m))
            results = engine.run_all(
                reps,
                progress_cb=lambda p: self._emit("progress", percent=int(p)),
                agent_cb=self._on_agent_state,
            )
        except Exception as e:  # surface any failure like analysisFailed
            self._set_busy(False)
            log.warning("analysis failed: %s", e, exc_info=True)
            msg = friendly_error(str(e))
            self._emit("analysis_failed", error=msg)
            self._emit("notify", message=f"فشل التحليل: {msg}")
            return
        with self._lock:
            self._results = results or {}
            self._dash = self._results.get("chief", {})
            self._date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self._set_busy(False)
        self._emit_dash_changed()
        self._emit("analysis_done")
        self._emit("notify", message="اكتمل التحليل — عُرضت النتائج في لوحة التحكم")

    def _on_agent_state(self, agent_id, state):
        with self._lock:
            self._agents[agent_id] = state
        self._emit("agent_state", agent_id=agent_id, state=state)

    # ───────────────────────── dashboard / export ─────────────────────────
    def clear_dashboard(self):
        """مسح لوحة التحكم — يحذف latest.json ويُفرّغ النتائج المعروضة."""
        try:
            if LATEST_F.exists():
                LATEST_F.unlink()
        except Exception as e:
            log.warning("latest-results delete failed: %s", e, exc_info=True)
            self._emit("log", message=f"تعذّر حذف ملف النتائج الأخيرة — {friendly_fs_error(e)}")
        with self._lock:
            self._results, self._dash = {}, {}
            self._date = ""
        self._emit_dash_changed()
        self._emit("notify", message="مُسحت لوحة التحكم")

    def export_pdf(self, path=None):
        return self._export(export_pdf, path, ".pdf")

    def export_excel(self, path=None):
        return self._export(export_excel, path, ".xlsx")

    def _export(self, fn, path, ext):
        """Returns (ok, path_or_error)."""
        if not self._results:
            err = "لا توجد نتائج للتصدير — شغّل التحليل أولاً"
            self._emit("export_failed", error=err)
            return False, err
        p = str(path) if path else ""
        if not p:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            p = str(REPORTS / f"marsad_{ts}{ext}")
        try:
            out = fn(self._results, p)
            self._emit("export_done", path=out)
            self._emit("notify", message=f"حُفظ الملف: {out}")
            return True, out
        except Exception as e:
            log.warning("export failed: %s", e, exc_info=True)
            msg = friendly_fs_error(e)
            self._emit("export_failed", error=msg)
            self._emit("notify", message=f"تعذّر التصدير: {msg}")
            return False, msg

    def send_email_report(self):
        """Returns (ok, message)."""
        if not self._results:
            self._emit("notify", message="لا توجد نتائج لإرسالها")
            return False, "لا توجد نتائج لإرسالها"
        recipients = (self._settings.get("report_recipients")
                      or list(self._settings.get("email_dept_map", {}).keys()))
        if not recipients:
            self._emit("notify", message="لا يوجد مستلمون مضبوطون في الإعدادات")
            return False, "لا يوجد مستلمون مضبوطون في الإعدادات"
        try:
            html = build_report_html(self._results)
            ok, detail = self._hub.send_report(
                recipients, "تقرير حالة المشروع — مرصد", html)
            msg = detail or ("أُرسل التقرير بالبريد" if ok else "تعذّر إرسال البريد")
            self._emit("notify", message=msg)
            return ok, msg
        except Exception as e:
            log.warning("email send failed: %s", e, exc_info=True)
            msg = friendly_error(str(e))
            self._emit("notify", message=f"خطأ في الإرسال: {msg}")
            return False, msg

    # ───────────────────────── settings / connection ─────────────────────────
    def save_settings(self, values):
        """Merge + persist settings, rebuild the hub so they take effect at once.

        Persists only the keys the caller actually sent (`changed_keys`) —
        e.g. a PUT that had blank secrets stripped from it — so the write
        never clobbers a key the caller never touched.
        """
        if values:
            self._settings.update(dict(values))
        try:
            save_settings(self._settings,
                          changed_keys=set(values.keys()) if values else None)
        except Exception as e:
            log.warning("settings save failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر حفظ الإعدادات: {friendly_fs_error(e)}")
            return
        self._ai.settings = self._settings
        # الموصّلات تلتقط الإعدادات عند الإنشاء — أعد بناء الـ hub حتى تسري
        # بيانات البريد / مجلد ERP / واتساب الجديدة فوراً.
        self._rebuild_hub()
        with self._lock:
            self._models = []          # القائمة كانت لمزوّد سابق — أعد الجلب
        self._emit("settings_changed")
        self._emit("notify", message="حُفظت الإعدادات")

    def _rebuild_hub(self):
        try:
            self._hub.stop_all()
        except Exception as e:
            log.warning("connector hub stop failed: %s", e, exc_info=True)
            self._emit("log", message=f"تعذّر إيقاف الموصّلات السابقة — {friendly_fs_error(e)}")
        self._hub = ConnectorHub(self._settings, self._contacts)
        self._hub.set_logger(lambda m: self._emit("log", message=str(m)))
        self._hub.set_event_handler(self._on_wa_event)
        self._start_whatsapp_if_enabled()

    def test_connection(self):
        """Start async engine test. False if one is already in flight."""
        if self._testing_engine:
            return False
        self._set_testing(engine=True, value=True)
        threading.Thread(target=self._run_connection_test, daemon=True).start()
        return True

    def _run_connection_test(self):
        """اختبار المحرّك على خيط منفصل — النداء قد يستغرق حتى ai_timeout."""
        try:
            ok, msg = self._ai.test_connection()
        except Exception as e:
            log.warning("connection test failed: %s", e, exc_info=True)
            ok, msg = False, friendly_error(str(e))
        self._online = ok
        self._status = "متصل" if ok else "غير متصل"
        self._emit("engine_changed", online=self._online, status=self._status)
        self._emit("connection_tested", ok=ok, message=msg)
        self._set_testing(engine=True, value=False)

    def test_email(self):
        """Start async email test. False if one is already in flight."""
        if self._testing_email:
            return False
        self._set_testing(engine=False, value=True)
        threading.Thread(target=self._run_email_test, daemon=True).start()
        return True

    def _run_email_test(self):
        """اختبار البريد على خيط منفصل — اتصال IMAP/SMTP قد يحجب الواجهة."""
        try:
            ok, msg = self._hub.test_email()
        except Exception as e:
            log.warning("email test failed: %s", e, exc_info=True)
            ok, msg = False, friendly_error(str(e))
        # الرسالة تظهر في موضعها (email_tested) — لا تُكرَّر كحدث notify فوقها
        self._emit("email_tested", ok=ok, message=msg)
        self._set_testing(engine=False, value=False)

    # ───────────────────────── contacts ─────────────────────────
    def contacts_structure(self):
        return self._contacts.get_structure()

    def employees_for(self, dept=None, sub_dept=None):
        return self._contacts.get_employees(dept or None, sub_dept or None)

    def add_employee(self, emp):
        try:
            return self._contacts.add_employee(dict(emp or {}))
        except Exception as e:
            log.warning("add employee failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر إضافة الموظف: {friendly_fs_error(e)}")
            raise

    def update_employee(self, emp_id, fields):
        try:
            return self._contacts.update_employee(emp_id, dict(fields or {}))
        except Exception as e:
            log.warning("update employee failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر تحديث الموظف: {friendly_fs_error(e)}")
            raise

    def delete_employee(self, emp_id):
        try:
            return self._contacts.delete_employee(emp_id)
        except Exception as e:
            log.warning("delete employee failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر حذف الموظف: {friendly_fs_error(e)}")
            raise

    def sync_contacts(self):
        maps = self._contacts.export_to_config()
        merged = dict(self._settings)
        merged["email_dept_map"] = maps["email_dept_map"]
        merged["whatsapp_groups"] = maps["whatsapp_groups"]
        try:
            save_settings(merged)
        except Exception as e:
            log.warning("contacts sync save failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر مزامنة جهات الاتصال: {friendly_fs_error(e)}")
            return
        self._settings = merged
        self._emit("settings_changed")
        # أعد بناء المحور حتى تسري خرائط التوجيه الجديدة على الموصّلات فوراً
        self._rebuild_hub()
        self._emit("notify", message="تمت مزامنة جهات الاتصال مع الإعدادات")

    # ───────────────────────── whatsapp ─────────────────────────
    def _start_whatsapp_if_enabled(self):
        if not self._settings.get("whatsapp_enabled"):
            return
        try:
            port = int(self._settings.get("whatsapp_port", 5051))
            self._hub.start_whatsapp(port)
            self._emit("log", message=f"واتساب: مستقبِل الرسائل يعمل على المنفذ {port}")
        except Exception as e:
            log.warning("whatsapp receiver bind failed: %s", e, exc_info=True)
            self._emit("log", message=f"واتساب: تعذّر بدء المستقبِل — {friendly_fs_error(e)}")

    def generate_whatsapp_bridge(self):
        """Returns (ok, path_or_error)."""
        try:
            port = int(self._settings.get("whatsapp_port", 5051))
            token = getattr(self._hub, "wa_token", "")
            path = WhatsAppHelper.save_bridge_file(port, token=token)
            self._emit("notify", message=f"أُنشئ ملف الجسر: {path}")
            return True, path
        except Exception as e:
            log.warning("whatsapp bridge file generation failed: %s", e, exc_info=True)
            msg = friendly_fs_error(e)
            self._emit("notify", message=f"تعذّر إنشاء الجسر: {msg}")
            return False, msg

    def check_node(self):
        """Returns (ok, message)."""
        ok, msg = WhatsAppHelper.check_nodejs()
        self._emit("notify", message=f"Node.js: {msg}" if ok else msg)
        return ok, msg

    # ───────────────────────── engine profiles ─────────────────────────
    def save_engine_profile(self, name):
        """احفظ مفاتيح المحرّك الحالية كملف مُسمّى (الافتراضي يبقى Ollama)."""
        name = (name or "").strip()
        if not name:
            self._emit("notify", message="أدخل اسماً للملف أولاً")
            return False
        profiles = [p for p in self._settings.get("engine_profiles", [])
                    if p.get("name") != name]
        snap = {k: self._settings.get(k) for k in ENGINE_KEYS}
        snap["name"] = name
        profiles.append(snap)
        # Write a copy, not self._settings in place: a failed write must
        # leave self._settings exactly as it was — matching save_settings()'s
        # own merge-then-write-then-assign shape.
        merged = dict(self._settings)
        merged["engine_profiles"] = profiles
        try:
            save_settings(merged)
        except Exception as e:
            log.warning("engine profile save failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر حفظ الملف: {friendly_fs_error(e)}")
            return False
        self._settings = merged
        self._emit("settings_changed")
        self._emit("notify", message=f"حُفظ الملف «{name}»")
        return True

    def switch_engine_profile(self, name):
        """فعّل ملفاً محفوظاً — تُنسخ مفاتيحه إلى الإعدادات وتسري فوراً."""
        for p in self._settings.get("engine_profiles", []):
            if p.get("name") == name:
                for k in ENGINE_KEYS:
                    if k in p:
                        self._settings[k] = p[k]
                self.save_settings({})
                return True
        self._emit("notify", message="الملف غير موجود")
        return False

    def delete_engine_profile(self, name):
        profiles = [p for p in self._settings.get("engine_profiles", [])
                    if p.get("name") != name]
        merged = dict(self._settings)
        merged["engine_profiles"] = profiles
        try:
            save_settings(merged)
        except Exception as e:
            log.warning("engine profile delete failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر حذف الملف: {friendly_fs_error(e)}")
            return False
        self._settings = merged
        self._emit("settings_changed")
        self._emit("notify", message=f"حُذف الملف «{name}»")
        return True

    # ───────────────────────── model list ─────────────────────────
    def fetch_models(self):
        """Start async model-list fetch. False if one is already in flight."""
        if self._models_busy:
            return False
        self._models_busy = True
        threading.Thread(target=self._run_fetch_models, daemon=True).start()
        return True

    def _run_fetch_models(self):
        """جلب النماذج على خيط منفصل — قد يستغرق حتى ai_timeout."""
        try:
            ok, out = self._ai.list_models()
        except Exception as e:
            log.warning("model list fetch failed: %s", e, exc_info=True)
            ok, out = False, friendly_error(str(e))
        models = list(out) if ok and isinstance(out, list) else []
        with self._lock:
            self._models = models
        self._models_busy = False
        msg = (f"جُلبت {len(models)} نموذجاً" if models
               else (out if isinstance(out, str) else "تعذّر جلب النماذج"))
        self._emit("models_fetched", ok=bool(models), models=models, message=msg)
        self._emit("notify", message=msg)

    # ── ربط واتساب برمز QR داخل الواجهة ──
    def start_whatsapp_bridge(self):
        """جهّز الحزم (أول مرة) وشغّل whatsapp_bridge.js على خيط منفصل."""
        if self._wa_proc or self._wa_starting:
            return False
        # الجسر يُرسل الرمز والحالة عبر HTTP إلى المستقبِل — شغّله أولاً حتى لو
        # كان استقبال واتساب معطّلاً في الإعدادات، وإلا ضاعت الأحداث وانتظرت النافذة بلا نهاية
        if not self._hub.whatsapp:
            try:
                port = int(self._settings.get("whatsapp_port", 5051))
                self._hub.start_whatsapp(port)
                self._emit("log", message=f"واتساب: مستقبِل الرسائل يعمل على المنفذ {port}")
            except Exception as e:
                log.warning("whatsapp receiver bind failed: %s", e, exc_info=True)
                self._emit("log", message=f"واتساب: تعذّر بدء المستقبِل — {friendly_fs_error(e)}")
        self._wa_starting = True
        self._emit_wa_status()
        threading.Thread(target=self._run_bridge_start, daemon=True).start()
        return True

    def _run_bridge_start(self):
        import subprocess
        try:
            bridge = DATA_DIR / "whatsapp_bridge.js"
            if not bridge.exists():
                self.generate_whatsapp_bridge()
            if not (DATA_DIR / "node_modules").exists():
                self._emit("log", message="واتساب: تثبيت حزم Node (أول مرة فقط)…")
                pkg = DATA_DIR / "package.json"
                if not pkg.exists():
                    pkg.write_text(json.dumps({
                        "name": "marsad-wa-bridge", "version": "1.0.0",
                        "type": "commonjs",
                        "dependencies": {
                            "@whiskeysockets/baileys": "^7.0.0-rc13",
                            "express": "^4.18.0", "node-fetch": "^3.3.0",
                            "pino": "^8.0.0",
                        }}, indent=2), encoding="utf-8")
                r = subprocess.run(["npm", "install"], cwd=str(DATA_DIR),
                                   capture_output=True, text=True, timeout=600)
                if r.returncode != 0:
                    self._emit("notify",
                               message="تعذّر تثبيت حزم Node — شغّل npm install يدوياً في مجلد البيانات")
                    self._wa_starting = False
                    self._emit_wa_status()
                    return
            log_dir = DATA_DIR / "logs"
            log_dir.mkdir(exist_ok=True)
            # وجّه خرج الجسر إلى ملف بدل إخفائه — أي فشل مستقبلي يُشخَّص من السجل
            self._wa_log = open(log_dir / "bridge.log", "a", encoding="utf-8")
            self._wa_proc = subprocess.Popen(
                ["node", "whatsapp_bridge.js"], cwd=str(DATA_DIR),
                stdout=self._wa_log, stderr=subprocess.STDOUT)
            self._emit("log", message="واتساب: الجسر يعمل — بانتظار رمز الربط")
        except FileNotFoundError:
            self._emit("notify", message="Node.js غير مثبّت — ثبّته أولاً")
        except Exception as e:
            log.warning("whatsapp bridge start failed: %s", e, exc_info=True)
            self._emit("notify", message=f"تعذّر تشغيل الجسر: {friendly_fs_error(e)}")
        self._wa_starting = False
        self._emit_wa_status()

    def stop_whatsapp_bridge(self):
        p, self._wa_proc = self._wa_proc, None
        if p:
            try:
                p.terminate()
            except Exception:
                pass
        log, self._wa_log = getattr(self, "_wa_log", None), None
        if log:
            try:
                log.close()
            except Exception:
                pass

    def _on_wa_event(self, kind, payload):
        """يُستدعى من خيط مستقبِل واتساب — حوّله إلى أحداث واجهة."""
        payload = dict(payload or {})
        if kind == "qr":
            qr = payload.get("qr") or ""
            if qr:
                self._wa_qr_matrix = self._qr_matrix(qr)
                self._emit("wa_qr", matrix=self._wa_qr_matrix)
        elif kind == "status":
            linked = bool(payload.get("linked"))
            if linked and not self._wa_linked:
                self._wa_linked = True
                self._wa_phone = str(payload.get("phone") or "")
                self._wa_qr_matrix = []
                self._emit("notify", message="تم ربط واتساب بنجاح")
            elif not linked:
                self._wa_linked = False
            self._emit_wa_status()

    def _emit_wa_status(self):
        self._emit("wa_status", linked=self._wa_linked, phone=self._wa_phone,
                   starting=self._wa_starting)

    def _qr_matrix(self, payload):
        """حوّل نص QR إلى صفوف "0/1" تُرسم في الواجهة — بلا ملفات صور."""
        try:
            import qrcode
            q = qrcode.QRCode(border=0)
            q.add_data(payload)
            q.make(fit=True)
            return ["".join("1" if c else "0" for c in row)
                    for row in q.get_matrix()]
        except ImportError:
            # لا تدع النافذة تنتظر بلا نهاية — أظهر السبب للمستخدم
            self._emit("log", message="حزمة qrcode غير مثبّتة في بايثون الذي يشغّل التطبيق")
            self._emit("notify", message="حزمة qrcode غير مثبّتة — ثبّت متطلبات التطبيق: pip install -r requirements.txt")
            return []
        except Exception as e:
            log.warning("QR matrix generation failed: %s", e, exc_info=True)
            self._emit("log", message=f"تعذّر توليد رمز QR: {friendly_fs_error(e)}")
            return []

    # ───────────────────────── internals ─────────────────────────
    def _emit_reports_changed(self):
        with self._lock:
            reps = list(self._reports)
        self._emit("reports_changed", count=len(reps), reports=reps)

    def _emit_dash_changed(self):
        with self._lock:
            self._emit("dash_changed", dash=self._dash, date=self._date,
                       has_results=bool(self._results))

    def _set_busy(self, v):
        self._busy = v
        self._emit("busy", busy=v)

    def _set_testing(self, engine, value):
        if engine:
            self._testing_engine = value
        else:
            self._testing_email = value
        self._emit("testing", engine=self._testing_engine,
                   email=self._testing_email,
                   active=self._testing_engine or self._testing_email)

    def _load_latest(self):
        if LATEST_F.exists():
            try:
                with open(LATEST_F, encoding="utf-8") as f:
                    self._results = json.load(f)
                self._dash = self._results.get("chief", {})
                ts = datetime.datetime.fromtimestamp(LATEST_F.stat().st_mtime)
                self._date = ts.strftime("%Y-%m-%d %H:%M")
            except Exception:
                self._results, self._dash = {}, {}
