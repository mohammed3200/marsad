"""AppController — the single QObject QML talks to.

Owns settings, the contacts DB, the connector hub, and the AI engine; exposes
app state (dashboard model, health, connection) as properties and actions as
slots. Analysis runs on a worker thread; results flow back via signals.
"""
import json
import datetime
import logging
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QThread, QUrl
from PySide6.QtGui import QDesktopServices

from core import AIEngine, AgentsEngine, ContactsDB, export_pdf, export_excel, WORKER_AGENTS
from core.paths import DATA_DIR, BUNDLE_DIR
from core.errors import friendly_error, friendly_fs_error
from connectors import ConnectorHub, build_report_html, read_file_to_report
from .settings_bridge import load_settings, save_settings
from .models import AgentsModel, ReportsModel
from .analysis_worker import AnalysisWorker

log = logging.getLogger(__name__)

REPORTS    = DATA_DIR / "reports"                  # writable output
SAMPLES_F  = BUNDLE_DIR / "sample_reports.json"    # shipped demo input
LATEST_F   = REPORTS / "latest.json"

# مفاتيح المحرّك التي تُلتقط في ملفات الإعداد (engine profiles)
ENGINE_KEYS = ("ai_backend", "ai_timeout", "ollama_url", "ollama_model",
               "claude_api_key", "claude_model", "openai_api_key",
               "openai_base_url", "openai_model", "gemini_api_key",
               "gemini_model", "azure_endpoint", "azure_api_key",
               "azure_deployment", "azure_api_version")


class AppController(QObject):
    dashModelChanged  = Signal()
    reportDateChanged = Signal()
    engineChanged     = Signal()
    busyChanged       = Signal()
    testingChanged    = Signal()
    progress          = Signal(int)
    logMessage        = Signal(str)
    analysisDone      = Signal()
    analysisFailed    = Signal(str)
    connectionTested  = Signal(bool, str)
    emailTested       = Signal(bool, str)
    emailSent         = Signal(bool, str)
    emailSendingChanged = Signal()
    collectingChanged  = Signal()
    exportDone        = Signal(str)          # path
    exportFailed      = Signal(str)
    reportsChanged    = Signal()
    notify            = Signal(str)          # transient user message
    navRequested      = Signal(int)          # page index to switch to
    settingsChanged   = Signal()
    exportsChanged    = Signal()
    recipientsChanged = Signal()
    nodeStatusChanged = Signal()
    engineProfilesChanged = Signal()
    modelsChanged       = Signal()
    waChanged         = Signal()
    _waEvent          = Signal(str, "QVariant")  # receiver thread → GUI thread
    _collected        = Signal("QVariant")   # reports gathered off the GUI thread
    _filesAdded       = Signal("QVariant")   # files parsed off the GUI thread
    _emailSent        = Signal(bool, str)    # SMTP result, worker thread → GUI thread

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = load_settings()
        self._contacts = ContactsDB()
        self._hub      = ConnectorHub(self._settings, self._contacts)
        self._ai       = AIEngine(self._settings)
        self._agents   = AgentsModel(self)
        self._reports  = ReportsModel(self)
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
        self._sending_email = False
        self._thread   = None
        self._worker   = None
        self._run_settings = None   # settings snapshot for the in-flight run, if any
        self._shutting_down = False
        self._collected.connect(self._on_collected)
        self._filesAdded.connect(self._on_files_added)
        self._emailSent.connect(self._on_email_sent)
        self._hub.set_logger(lambda m: self.logMessage.emit(str(m)))
        self._exports    = []
        self._recipients = []
        self._node_status = ""
        self._wa_qr_matrix = []
        self._wa_linked    = False
        self._wa_phone     = ""
        self._wa_dialog_open = False
        self._wa_starting  = False
        self._wa_proc      = None
        self._models       = []
        self._models_busy  = False
        self._waEvent.connect(self._on_wa_event)
        self._hub.set_event_handler(self._wa_event_from_thread)
        self._load_latest()
        self._start_whatsapp_if_enabled()
        self._refresh_exports()
        self._refresh_recipients()

    # ───────────────────────── properties ─────────────────────────
    @Property("QVariant", notify=dashModelChanged)
    def dashModel(self):
        return self._dash

    @Property(str, notify=reportDateChanged)
    def reportDate(self):
        return self._date

    @Property(bool, notify=engineChanged)
    def engineOnline(self):
        return self._online

    @Property(str, notify=engineChanged)
    def engineStatus(self):
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(bool, notify=testingChanged)
    def testing(self):
        """True while a connection/email test is in flight."""
        return self._testing_engine or self._testing_email

    @Property(bool, notify=testingChanged)
    def testingEngine(self):
        """True while an engine connection test is in flight."""
        return self._testing_engine

    @Property(bool, notify=testingChanged)
    def testingEmail(self):
        """True while an email test is in flight."""
        return self._testing_email

    @Property(bool, notify=emailSendingChanged)
    def sendingEmail(self):
        """صحيح أثناء إرسال تقرير البريد على خيط منفصل."""
        return self._sending_email

    @Property(bool, notify=collectingChanged)
    def collecting(self):
        """صحيح أثناء جمع التقارير (IMAP/ERP/HTTP) على خيط منفصل."""
        return self._collecting

    @Property(int, constant=True)
    def agentCount(self):
        return len(WORKER_AGENTS) + 1

    @Property(QObject, constant=True)
    def agentsModel(self):
        return self._agents

    @Property(QObject, constant=True)
    def reportsModel(self):
        return self._reports

    @Property(int, notify=reportsChanged)
    def reportCount(self):
        return self._reports.count()

    @Property("QVariant", notify=settingsChanged)
    def settings(self):
        return self._settings

    @Property("QVariant", notify=exportsChanged)
    def exportsModel(self):
        """ملفات التقارير المُصدَّرة (PDF/XLSX) — الأحدث أولاً."""
        return self._exports

    @Property("QVariant", notify=recipientsChanged)
    def recipientsModel(self):
        """مستلمو التقرير الحاليون — report_recipients أو مفاتيح email_dept_map."""
        return self._recipients

    @Property(str, notify=nodeStatusChanged)
    def nodeStatus(self):
        """"" أو رقم الإصدار (v…) أو "missing" — حالة تثبيت Node.js."""
        return self._node_status

    @Property("QVariant", notify=waChanged)
    def waQrMatrix(self):
        """مصفوفة رمز QR الحالية (صفوف من "0/1") — فارغة بلا رمز."""
        return self._wa_qr_matrix

    @Property(bool, notify=waChanged)
    def waLinked(self):
        return self._wa_linked

    @Property(str, notify=waChanged)
    def waPhone(self):
        return self._wa_phone

    @Property(bool, notify=waChanged)
    def waStarting(self):
        """True أثناء تجهيز/تشغيل جسر واتساب."""
        return self._wa_starting

    @Property(bool, notify=waChanged)
    def waDialogOpen(self):
        return self._wa_dialog_open

    @waDialogOpen.setter
    def waDialogOpen(self, v):
        self._wa_dialog_open = bool(v)
        self.waChanged.emit()

    @Property("QVariant", notify=engineProfilesChanged)
    def engineProfilesModel(self):
        """ملفات المحرّك المحفوظة: [{name, ai_backend}]."""
        return [{"name": p.get("name", ""),
                 "ai_backend": p.get("ai_backend", "ollama")}
                for p in self._settings.get("engine_profiles", [])]

    @Property("QVariant", notify=modelsChanged)
    def modelsModel(self):
        """قائمة النماذج المجلوبة من المزوّد الحالي."""
        return self._models

    @Property(bool, notify=modelsChanged)
    def modelsBusy(self):
        return self._models_busy

    @Property(str, constant=True)
    def todayLabel(self):
        from core.hijri import dual_label
        return dual_label()

    @Slot(int)
    def goTo(self, index):
        self.navRequested.emit(index)

    # ───────────────────────── input actions ─────────────────────────
    @Slot()
    def loadSamples(self):
        try:
            with open(SAMPLES_F, encoding="utf-8") as f:
                data = json.load(f)
            reps = data.get("reports", data) if isinstance(data, dict) else data
            self._reports.extend(reps)
            self.reportsChanged.emit()
            self.notify.emit(f"حُمّلت {len(reps)} تقارير نموذجية")
        except Exception as e:
            log.warning("sample load failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر تحميل النماذج: {friendly_fs_error(e)}")

    @Slot()
    def collectReports(self):
        if self._collecting:
            return
        self._set_collecting(True)
        threading.Thread(target=self._run_collect, daemon=True).start()

    def _run_collect(self):
        """جمع التقارير (IMAP/ERP/HTTP) على خيط منفصل حتى لا تتجمّد الواجهة."""
        try:
            self._collected.emit(self._hub.collect_all())
        except Exception as e:
            self.notify.emit(f"تعذّر الجمع: {friendly_error(str(e))}")
        finally:
            self._set_collecting(False)

    @Slot("QVariant")
    def _on_collected(self, reps):
        reps = list(reps or [])
        self._reports.extend(reps)
        self.reportsChanged.emit()
        self.notify.emit(f"جُمِّع {len(reps)} تقرير من المصادر"
                         if reps else "لا توجد تقارير جديدة")

    @Slot()
    def pickReportFiles(self):
        """فتح مربّع اختيار ملفات أصلي (native) وإضافة المختار — لا يعتمد على
        QtQuick.Dialogs حتى يعمل في كل البيئات."""
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            None, "اختر ملفات التقارير", "",
            "مستندات (*.xlsx *.xls *.csv *.pdf *.txt *.json *.docx);;كل الملفات (*)")
        if paths:
            self.addFiles(paths)

    @Slot(result=str)
    def pickErpFolder(self):
        """اختيار مجلد ERP عبر مربّع أصلي — يُعيد المسار أو نصاً فارغاً."""
        from PySide6.QtWidgets import QFileDialog
        return QFileDialog.getExistingDirectory(None, "اختر مجلد ملفات ERP") or ""

    @Slot("QVariant")
    def addFiles(self, urls):
        """قراءة ملفات مختارة على خيط منفصل (حتى لا تتجمّد الواجهة) ثم إضافتها."""
        if self._adding:
            return
        paths = []
        for u in (urls or []):
            p = self._localfile(str(u))
            if p:
                paths.append(p)
        if not paths:
            self.notify.emit("لم تُختَر ملفات")
            return
        self._adding = True
        threading.Thread(target=self._run_add_files, args=(paths,),
                         daemon=True).start()

    def _run_add_files(self, paths):
        """تفكيك الملفات (Word/Excel/PDF/CSV/TXT/JSON) خارج خيط الواجهة."""
        added, failed = [], []
        try:
            for p in paths:
                try:
                    rep = read_file_to_report(p, source="ملف")
                    if rep:
                        added.append(rep)
                    else:
                        failed.append(Path(p).name)
                except Exception:
                    failed.append(Path(p).name)
            self._filesAdded.emit({"added": added, "failed": failed})
        finally:
            self._adding = False

    @Slot("QVariant")
    def _on_files_added(self, res):
        added  = list(res.get("added", []))
        failed = list(res.get("failed", []))
        for rep in added:
            self._reports.add(rep)
        if added:
            self.reportsChanged.emit()
        if added and failed:
            self.notify.emit(f"أُضيف {len(added)} ملف — تعذّر: {'، '.join(failed)}")
        elif added:
            self.notify.emit(f"أُضيف {len(added)} ملف")
        elif failed:
            self.notify.emit(f"تعذّرت قراءة: {'، '.join(failed)}")
        else:
            self.notify.emit("لم تُختَر ملفات")

    @Slot("QVariant")
    def addReport(self, report):
        r = dict(self._to_py(report) or {})
        if not r.get("content"):
            self.notify.emit("أدخل نص التقرير أولاً")
            return
        r.setdefault("date", datetime.date.today().isoformat())
        self._reports.add(r)
        self.reportsChanged.emit()

    @Slot(int)
    def removeReport(self, row):
        self._reports.remove(row)
        self.reportsChanged.emit()

    @Slot()
    def clearReports(self):
        self._reports.clear()
        self.reportsChanged.emit()

    # ───────────────────────── analysis ─────────────────────────
    @Slot()
    def runAnalysis(self):
        if self._busy:
            return
        if self._reports.count() == 0:
            self.notify.emit("لا توجد تقارير للتحليل — حمّل النماذج أو أضف تقريراً")
            return
        self._set_busy(True)
        self._agents.reset_states()
        self.progress.emit(0)

        # Snapshot settings into a fresh engine so a later saveSettings() cannot
        # switch the provider mid-run — self._ai/self._settings can be rebound
        # while this run is still in flight, and the running engine must not
        # see that change (agents 1..k on one provider, k+1..11 on another).
        # Stash the same snapshot as self._run_settings so
        # _shutdown_wait_budget_ms() waits on *this* run's ai_timeout: without
        # it, a shorter ai_timeout typed into Settings after the run started
        # (and saved via one of the still-ungated test/fetch buttons) would
        # shrink shutdown()'s wait budget below what the in-flight call can
        # actually block for, reintroducing the "wait() times out, thread
        # left running" failure task 12 removed.
        run_settings = dict(self._settings)
        engine = AgentsEngine(AIEngine(run_settings))
        self._run_settings = run_settings
        self._thread = QThread(self)
        self._worker = AnalysisWorker(engine, self._reports.reports())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.agentState.connect(self._agents.set_state)
        self._worker.progress.connect(self.progress)
        self._worker.log.connect(self.logMessage)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
        # Canonical Qt worker-thread cleanup: connecting to the *thread's*
        # finished (not the worker's own) guarantees the deleteLater lands
        # while QThreadPrivate::finish() is still flushing the thread's event
        # queue. Doing it any later (e.g. an explicit worker.deleteLater()
        # call after wait() returns) posts to a queue nothing will ever drain
        # again — the worker outlives every analysis run.
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    @Slot("QVariant")
    def _on_analysis_done(self, results):
        self._results = results or {}
        self._dash = self._results.get("chief", {})
        self._date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self._teardown_thread()
        self._set_busy(False)
        self.dashModelChanged.emit()
        self.reportDateChanged.emit()
        # Derive the verdict from the results dict we already hold — no new
        # signal, and nothing Qt-shaped pushed down into core/. Only the worker
        # agents are counted: _ensure_chief_schema strips the chief's own
        # "error" key, and a chief fed by zero successful workers is worthless
        # anyway. An empty `workers` means a cancelled run, not a failed one.
        workers = [v for k, v in self._results.items()
                   if k != "chief" and isinstance(v, dict)]
        if workers and not any("error" not in v for v in workers):
            msg = "لم ينجح أي وكيل — راجع إعدادات المحرّك وسجلّ التشغيل"
            self.analysisFailed.emit(msg)
            self.notify.emit(f"تعذّر إكمال التحليل: {msg}")
            return
        self.analysisDone.emit()
        self.notify.emit("اكتمل التحليل — عُرضت النتائج في لوحة التحكم")

    @Slot(str)
    def _on_analysis_failed(self, msg):
        self._teardown_thread()
        self._set_busy(False)
        self.analysisFailed.emit(msg)
        self.notify.emit(f"فشل التحليل: {msg}")

    def _teardown_thread(self):
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None
        # No explicit self._worker.deleteLater() here: runAnalysis() already
        # connected thread.finished -> worker.deleteLater(), which by the
        # time wait() above returns has already run (and deleted the C++
        # object) — calling deleteLater() again on it raises
        # "Internal C++ object already deleted". Just drop the Python ref.
        self._worker = None
        self._run_settings = None

    def _shutdown_wait_budget_ms(self) -> int:
        """How long shutdown() will block waiting for a live analysis thread
        to notice it's been interrupted.

        Cancellation is cooperative (AnalysisWorker passes should_stop into
        AgentsEngine.run_all, checked between agents) — quit() can only take
        effect once the in-flight agent call returns, and that call is a
        synchronous urlopen bounded by ai_timeout, not by anything shorter.
        So the budget must be at least one full ai_timeout, not the original
        code's flat 5s (which timed out on essentially every quit during a
        live analysis — see task-12-findings-r1.md, Critical 1).

        Prefer self._run_settings (the snapshot runAnalysis() built the live
        engine from) over self._settings while a run is in flight: since that
        snapshot decouples the running engine from later settings saves, the
        two can now legitimately disagree on ai_timeout — waiting on the
        *live* settings' value here would size the budget for a timeout the
        in-flight call was never bound by, under- or over-shooting the wait
        needed to observe should_stop actually take effect."""
        settings = self._run_settings if (self._busy and self._run_settings) else self._settings
        try:
            ai_timeout = int(settings.get("ai_timeout", 180))
        except (TypeError, ValueError):
            ai_timeout = 180
        return (max(ai_timeout, 5) + 5) * 1000

    @Slot()
    def shutdown(self):
        """Stop every background worker before the app object is destroyed.

        Without this the QThread is torn down while still running and Qt
        calls qFatal — closing the window during an analysis aborted the
        process.

        There is deliberately no terminate() fallback. Nothing in the
        pipeline could poll for interruption before should_stop existed, so
        terminate() was not a rare last resort — it fired on essentially
        every quit during a live analysis. Forcibly cancelling a thread that
        may be mid network I/O or inside a CPU-bound stretch (json.dumps,
        _parse_json) can unwind it while it still holds the GIL's internal
        mutex, hanging the whole process forever — worse than the abort this
        fixes. Cooperative cancellation makes quit() actually work once the
        thread notices, so there is nothing left for terminate() to do that
        wouldn't risk that deadlock for no benefit."""
        if self._shutting_down:
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
        thread_stopped = True
        if self._thread:
            self._thread.requestInterruption()
            self._thread.quit()
            thread_stopped = self._thread.wait(self._shutdown_wait_budget_ms())
            if thread_stopped:
                self._thread = None
            else:
                # Checked and acted on, not dropped: a still-running thread
                # stays referenced (and un-terminated) rather than being
                # silently forgotten, which would only defer the original
                # "Destroyed while thread is still running" qFatal to
                # whenever the controller itself is torn down.
                self.logMessage.emit(
                    "تعذّر إيقاف خيط التحليل خلال المهلة المحددة — قد يستمر "
                    "بالعمل في الخلفية حتى تنتهي المكالمة الشبكية الحالية")
        if thread_stopped:
            self._worker = None

    # ───────────────────────── reports / export ─────────────────────────
    @Slot(str)
    def exportPdf(self, path):
        self._export(export_pdf, path, ".pdf")

    @Slot(str)
    def exportExcel(self, path):
        self._export(export_excel, path, ".xlsx")

    def _export(self, fn, path, ext):
        if not self._results:
            self.exportFailed.emit("لا توجد نتائج للتصدير — شغّل التحليل أولاً")
            return
        p = self._localfile(path)
        if not p:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            p = str(REPORTS / f"marsad_{ts}{ext}")
        try:
            out = fn(self._results, p)
            self._refresh_exports()
            self.exportDone.emit(out)
            self.notify.emit(f"حُفظ الملف: {out}")
        except Exception as e:
            log.warning("export failed: %s", e, exc_info=True)
            msg = friendly_fs_error(e)
            self.exportFailed.emit(msg)
            self.notify.emit(f"تعذّر التصدير: {msg}")

    @Slot()
    def openReportsFolder(self):
        REPORTS.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(REPORTS)))

    def _refresh_exports(self):
        """أعد قراءة ملفات التقارير المُصدَّرة (PDF/XLSX) — الأحدث أولاً."""
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
                    "path":   str(p),
                    "sizeKb": max(1, int(st.st_size / 1024)),
                    "date":   datetime.datetime.fromtimestamp(
                                  st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
        except Exception:
            items = []
        self._exports = items
        self.exportsChanged.emit()

    def _refresh_recipients(self):
        recips = (self._settings.get("report_recipients")
                  or list(self._settings.get("email_dept_map", {}).keys()))
        if isinstance(recips, str):
            recips = [recips]
        self._recipients = list(recips or [])
        self.recipientsChanged.emit()

    @Slot(str)
    def openFile(self, path):
        """افتح ملفاً مُصدَّراً — مقصور على ملفات داخل مجلد التقارير."""
        try:
            p = Path(path).resolve()
            p.relative_to(REPORTS.resolve())
        except Exception:
            self.notify.emit("مسار غير مسموح به")
            return
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    @Slot()
    def installNode(self):
        """افتح صفحة تنزيل Node.js الرسمية — التثبيت يتم من عندها."""
        QDesktopServices.openUrl(QUrl("https://nodejs.org/en/download"))
        self.notify.emit("افتحنا صفحة تنزيل Node.js — ثبّته ثم أعد الفحص")

    @Slot()
    def sendEmailReport(self):
        if not self._results:
            self.notify.emit("لا توجد نتائج لإرسالها")
            return
        if self._sending_email:
            return
        self._set_sending_email(True)
        # Snapshot on the GUI thread — the worker must not re-read self._results,
        # self._settings or self._hub later, since clearDashboard()/analysis-done/
        # saveSettings() can all rebind them to new objects while the SMTP call
        # is in flight (saveSettings() → _rebuild_hub() rebinds self._hub itself).
        # self._recipients is already the resolved two-tier (report_recipients,
        # falling back to email_dept_map) list — reusing it here also keeps that
        # resolution to one source of truth, the same one that drives the Send
        # button's enabled state in ReportsPage.qml.
        snapshot = dict(self._results)
        recipients = list(self._recipients)
        hub = self._hub
        threading.Thread(target=self._run_send_email,
                         args=(snapshot, recipients, hub), daemon=True).start()

    def _run_send_email(self, results, recipients, hub):
        """SMTP on a worker thread — smtplib blocks for the OS TCP timeout."""
        try:
            if not recipients:
                if not self._shutting_down:
                    self._emailSent.emit(False, "لا يوجد مستلمون مضبوطون — اضبطهم في الإعدادات")
                return
            html = build_report_html(results)
            ok, detail = hub.send_report(recipients, "تقرير حالة المشروع — مرصد", html)
            if not self._shutting_down:
                # Keep the old generic line as the fallback: send_report only
                # returns a cause when it has one worth showing.
                self._emailSent.emit(
                    bool(ok),
                    detail or ("أُرسل التقرير بالبريد" if ok
                               else "تعذّر إرسال البريد — راجع الإعدادات"))
        except Exception as e:
            # Never let a second emit — against a controller that may already be
            # torn down if this fires after quit — raise out of a daemon thread.
            try:
                if not self._shutting_down:
                    self._emailSent.emit(False, friendly_error(str(e)))
            except Exception:
                pass
        finally:
            self._set_sending_email(False)

    @Slot(bool, str)
    def _on_email_sent(self, ok, message):
        self.emailSent.emit(ok, message)
        self.notify.emit(message)

    # ───────────────────────── settings / connection ─────────────────────────
    @Slot()
    def testConnection(self):
        if self._testing_engine:
            return
        self._set_testing_engine(True)
        threading.Thread(target=self._run_connection_test, daemon=True).start()

    def _run_connection_test(self):
        """اختبار المحرّك على خيط منفصل — النداء قد يستغرق حتى ai_timeout."""
        try:
            try:
                ok, msg = self._ai.test_connection()
            except Exception as e:
                log.warning("connection test failed: %s", e, exc_info=True)
                ok, msg = False, friendly_error(str(e))
            self._online = ok
            self._status = "متصل" if ok else "غير متصل"
            self.engineChanged.emit()
            self.connectionTested.emit(ok, msg)
        finally:
            self._set_testing_engine(False)

    @Slot("QVariant")
    def saveSettings(self, values):
        # Gated here, not just in QML: the sticky-footer save button is not
        # the only caller — "حفظ كملف"، "جلب قائمة النماذج"، «اختبار المحرّك»
        # and «اختبار البريد» all call app.saveSettings() first (so the test
        # reflects what's on screen), and switchEngineProfile() calls it too.
        # A single gate here covers every current and future caller instead
        # of five separate QML `enabled:` bindings that are easy to miss one of.
        if self._busy:
            self.notify.emit("التحليل قيد التشغيل — تعذّر الحفظ الآن")
            return
        values = self._to_py(values)
        merged = dict(self._settings)
        if values:
            merged.update(dict(values))
        try:
            save_settings(merged, changed_keys=set(values.keys()) if values else None)
        except Exception as e:
            log.warning("settings save failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر حفظ الإعدادات: {friendly_fs_error(e)}")
            return
        self._settings = merged
        self._ai.settings = self._settings
        # الموصّلات تلتقط الإعدادات عند الإنشاء — أعد بناء الـ hub حتى تسري
        # بيانات البريد / مجلد ERP / واتساب الجديدة فوراً.
        self._rebuild_hub()
        self._refresh_recipients()
        self._models = []          # قائمة النماذج كانت لمزوّد سابق — أعد الجلب
        self.modelsChanged.emit()
        self.settingsChanged.emit()
        self.notify.emit("حُفظت الإعدادات")

    # ── ملفات المحرّك (engine profiles) ──
    @Slot(str)
    def saveEngineProfile(self, name):
        """احفظ مفاتيح المحرّك الحالية كملف مُسمّى (الافتراضي يبقى Ollama)."""
        # Same gate as saveSettings(), and for the same reason: this writes
        # settings.json directly (save_settings(), not through saveSettings())
        # and its snapshot of the *current* engine keys would otherwise be
        # taken and persisted while a run is in flight — mid-run, that's a
        # stale-data write, not just an untimely one.
        if self._busy:
            self.notify.emit("التحليل قيد التشغيل — تعذّر الحفظ الآن")
            return
        name = (name or "").strip()
        if not name:
            self.notify.emit("أدخل اسماً للملف أولاً")
            return
        profiles = [p for p in self._settings.get("engine_profiles", [])
                    if p.get("name") != name]
        snap = {k: self._settings.get(k) for k in ENGINE_KEYS}
        snap["name"] = name
        profiles.append(snap)
        # Build the write on a copy, not self._settings in place: a failed
        # write must leave self._settings exactly as it was, or the
        # profiles list shown by engineProfilesModel silently disagrees
        # with what's actually on disk until the next restart — the same
        # merge-then-write-then-assign shape saveSettings() already uses.
        merged = dict(self._settings)
        merged["engine_profiles"] = profiles
        try:
            save_settings(merged)
        except Exception as e:
            log.warning("engine profile save failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر حفظ الملف: {friendly_fs_error(e)}")
            return
        self._settings = merged
        self.engineProfilesChanged.emit()
        self.notify.emit(f"حُفظ الملف «{name}»")

    @Slot(str)
    def switchEngineProfile(self, name):
        """فعّل ملفاً محفوظاً — تُنسخ مفاتيحه إلى الإعدادات وتسري فوراً.

        Routed entirely through saveSettings() rather than mutating
        self._settings in place first: self._ai holds self._settings by
        reference, so an in-place mutation followed by a saveSettings({})
        that saveSettings's own busy-gate then refuses left the interactive
        engine, the visible form fields and settings.json disagreeing —
        engine already switched, file still holding the old profile, and no
        dirty indicator ever warned about it. Building the changed-keys dict
        first and handing it to saveSettings() in one call makes the whole
        switch atomic: either it all lands (settings.json, self._settings,
        self._ai) or none of it does."""
        for p in self._settings.get("engine_profiles", []):
            if p.get("name") == name:
                self.saveSettings({k: p[k] for k in ENGINE_KEYS if k in p})
                return
        self.notify.emit("الملف غير موجود")

    @Slot(str)
    def deleteEngineProfile(self, name):
        # Same as saveEngineProfile(): this writes settings.json directly,
        # bypassing saveSettings()'s gate entirely, so it needs its own.
        if self._busy:
            self.notify.emit("التحليل قيد التشغيل — تعذّر الحفظ الآن")
            return
        profiles = [p for p in self._settings.get("engine_profiles", [])
                    if p.get("name") != name]
        merged = dict(self._settings)
        merged["engine_profiles"] = profiles
        try:
            save_settings(merged)
        except Exception as e:
            log.warning("engine profile delete failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر حذف الملف: {friendly_fs_error(e)}")
            return
        self._settings = merged
        self.engineProfilesChanged.emit()
        self.notify.emit(f"حُذف الملف «{name}»")

    @Slot()
    def fetchModels(self):
        """اجلب قائمة النماذج من المزوّد الحالي على خيط منفصل."""
        if self._models_busy:
            return
        self._set_models_busy(True)
        threading.Thread(target=self._run_fetch_models, daemon=True).start()

    def _run_fetch_models(self):
        try:
            try:
                ok, out = self._ai.list_models()
            except Exception as e:
                log.warning("model list fetch failed: %s", e, exc_info=True)
                ok, out = False, friendly_error(str(e))
            self._models = list(out) if ok and isinstance(out, list) else []
            if self._models:
                self.notify.emit(f"جُلبت {len(self._models)} نموذجاً")
            else:
                self.notify.emit(out if isinstance(out, str) else "تعذّر جلب النماذج")
        finally:
            # Guarded setter, not a raw emit: this runs in a finally block
            # on a daemon thread that can easily outlive QCoreApplication
            # teardown (the fetch itself can block for ai_timeout) — the
            # same class of bug tests/test_shutdown.py's guard-flag test
            # exists for (see _set_sending_email et al.).
            self._set_models_busy(False)

    def _rebuild_hub(self):
        # Stop the old hub's listeners *before* draining its buffer, not
        # after: WhatsAppReceiver runs on ThreadingHTTPServer with
        # daemon_threads=True, so stop()/server_close() does not join
        # in-flight request handler threads — a request already accepted can
        # still call on_message() and append to the buffer after stop()
        # returns. Draining first would miss that append entirely (it lands
        # in the buffer *after* the snapshot, and the old hub is then
        # discarded with it still holding that report). Stopping first
        # closes that window: any report appended while the listener is
        # shutting down still lands in the old hub's buffer, which is still
        # reachable, and the drain below still recovers it.
        pending = []
        if self._hub:
            try:
                self._hub.stop_all()
            except Exception as e:
                log.warning("connector hub stop failed: %s", e, exc_info=True)
                self.logMessage.emit(f"تعذّر إيقاف الموصّلات السابقة — {friendly_fs_error(e)}")
            try:
                pending = self._hub.take_buffer()
            except Exception as e:
                log.warning("connector hub buffer handoff failed: %s", e, exc_info=True)
                self.logMessage.emit(f"تعذّر نقل التقارير المعلّقة — {friendly_fs_error(e)}")
                pending = []
        self._hub = ConnectorHub(self._settings, self._contacts)
        self._hub.set_logger(lambda m: self.logMessage.emit(str(m)))
        self._hub.set_event_handler(self._wa_event_from_thread)
        if pending:
            self._hub.extend_buffer(pending)
        self._start_whatsapp_if_enabled()

    @Slot()
    def testEmail(self):
        if self._testing_email:
            return
        self._set_testing_email(True)
        threading.Thread(target=self._run_email_test, daemon=True).start()

    def _run_email_test(self):
        """اختبار البريد على خيط منفصل — اتصال IMAP/SMTP قد يحجب الواجهة."""
        try:
            try:
                ok, msg = self._hub.test_email()
            except Exception as e:
                log.warning("email test failed: %s", e, exc_info=True)
                ok, msg = False, friendly_error(str(e))
            # الرسالة تظهر بجانب الزر (emailTested) — لا تُكرَّر كتنبيه منبثق فوقها
            self.emailTested.emit(ok, msg)
        finally:
            self._set_testing_email(False)

    @Slot(result="QVariant")
    def getSettings(self):
        return self._settings

    # ───────────────────────── contacts ─────────────────────────
    @Slot(result="QVariant")
    def contactsStructure(self):
        return self._contacts.get_structure()

    @Slot(str, str, result="QVariant")
    def employeesFor(self, dept, sub_dept):
        return self._contacts.get_employees(dept or None, sub_dept or None)

    @Slot("QVariant")
    def addEmployee(self, emp):
        try:
            self._contacts.add_employee(dict(self._to_py(emp) or {}))
        except Exception as e:
            log.warning("add employee failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر إضافة الموظف: {friendly_fs_error(e)}")

    @Slot(int, "QVariant")
    def updateEmployee(self, emp_id, fields):
        try:
            self._contacts.update_employee(emp_id, dict(self._to_py(fields) or {}))
        except Exception as e:
            log.warning("update employee failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر تحديث الموظف: {friendly_fs_error(e)}")

    @Slot(int)
    def deleteEmployee(self, emp_id):
        try:
            self._contacts.delete_employee(emp_id)
        except Exception as e:
            log.warning("delete employee failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر حذف الموظف: {friendly_fs_error(e)}")

    @Slot()
    def syncContacts(self):
        # Same gate as saveSettings()/saveEngineProfile(): this writes
        # settings.json directly and calls _rebuild_hub(), which tears down
        # and recreates every connector — doing that mid-analysis would
        # kill the in-flight run's IMAP/ERP/WhatsApp listeners out from
        # under it, unlike the other three writers which only race the
        # write itself.
        if self._busy:
            self.notify.emit("التحليل قيد التشغيل — تعذّر الحفظ الآن")
            return
        maps = self._contacts.export_to_config()
        merged = dict(self._settings)
        merged["email_dept_map"] = maps["email_dept_map"]
        merged["whatsapp_groups"] = maps["whatsapp_groups"]
        try:
            save_settings(merged)
        except Exception as e:
            log.warning("contacts sync save failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر مزامنة جهات الاتصال: {friendly_fs_error(e)}")
            return
        self._settings = merged
        self.settingsChanged.emit()
        # أعد بناء المحور حتى تسري خرائط التوجيه الجديدة على الموصّلات فوراً
        self._rebuild_hub()
        self.notify.emit("تمت مزامنة جهات الاتصال مع الإعدادات")

    # ───────────────────────── whatsapp ─────────────────────────
    def _start_whatsapp_if_enabled(self):
        if not self._settings.get("whatsapp_enabled"):
            return
        try:
            port = int(self._settings.get("whatsapp_port", 5051))
            self._hub.start_whatsapp(port)
            self.logMessage.emit(f"واتساب: مستقبِل الرسائل يعمل على المنفذ {port}")
        except Exception as e:
            log.warning("whatsapp receiver bind failed: %s", e, exc_info=True)
            self.logMessage.emit(f"واتساب: تعذّر بدء المستقبِل — {friendly_fs_error(e)}")

    @Slot()
    def generateWhatsAppBridge(self):
        from connectors import WhatsAppHelper
        try:
            port = int(self._settings.get("whatsapp_port", 5051))
            token = getattr(self._hub, "wa_token", "")
            path = WhatsAppHelper.save_bridge_file(port, token=token)
            self.notify.emit(f"أُنشئ ملف الجسر: {path}")
        except Exception as e:
            log.warning("whatsapp bridge file generation failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر إنشاء الجسر: {friendly_fs_error(e)}")

    @Slot()
    def checkNode(self):
        from connectors import WhatsAppHelper
        ok, msg = WhatsAppHelper.check_nodejs()
        self._node_status = msg if ok else "missing"
        self.nodeStatusChanged.emit()
        self.notify.emit(f"Node.js: {msg}" if ok else msg)

    # ── ربط واتساب برمز QR داخل التطبيق ──
    @Slot()
    def showWhatsAppQr(self):
        """افتح نافذة الرمز وشغّل الجسر إن لم يكن مربوطاً بعد."""
        self._wa_dialog_open = True
        self.waChanged.emit()
        if not self._wa_linked:
            self.startWhatsAppBridge()

    @Slot()
    def startWhatsAppBridge(self):
        """جهّز الحزم (أول مرة) وشغّل whatsapp_bridge.js على خيط منفصل."""
        if self._wa_starting:
            return
        if self._wa_proc is not None and self._wa_proc.poll() is None:
            return          # still running
        self._wa_proc = None  # it exited — allow a fresh attempt
        # الجسر يُرسل الرمز والحالة عبر HTTP إلى المستقبِل — شغّله أولاً حتى لو
        # كان استقبال واتساب معطّلاً في الإعدادات، وإلا ضاعت الأحداث وانتظرت النافذة بلا نهاية
        if not self._hub.whatsapp:
            try:
                port = int(self._settings.get("whatsapp_port", 5051))
                self._hub.start_whatsapp(port)
                self.logMessage.emit(f"واتساب: مستقبِل الرسائل يعمل على المنفذ {port}")
            except Exception as e:
                log.warning("whatsapp receiver bind failed: %s", e, exc_info=True)
                self.logMessage.emit(f"واتساب: تعذّر بدء المستقبِل — {friendly_fs_error(e)}")
        self._set_wa_starting(True)
        threading.Thread(target=self._run_bridge_start, daemon=True).start()

    def _run_bridge_start(self):
        import subprocess
        try:
            bridge = DATA_DIR / "whatsapp_bridge.js"
            if not bridge.exists():
                self.generateWhatsAppBridge()
            if not (DATA_DIR / "node_modules").exists():
                self.logMessage.emit("واتساب: تثبيت حزم Node (أول مرة فقط)…")
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
                    self.notify.emit("تعذّر تثبيت حزم Node — شغّل npm install يدوياً في مجلد البيانات")
                    return
            log_dir = DATA_DIR / "logs"
            log_dir.mkdir(exist_ok=True)
            # وجّه خرج الجسر إلى ملف بدل إخفائه — أي فشل مستقبلي يُشخَّص من السجل
            self._wa_log = open(log_dir / "bridge.log", "a", encoding="utf-8")
            self._wa_proc = subprocess.Popen(
                ["node", "whatsapp_bridge.js"], cwd=str(DATA_DIR),
                stdout=self._wa_log, stderr=subprocess.STDOUT)
            import atexit
            atexit.register(self.stopWhatsAppBridge)
            self.logMessage.emit("واتساب: الجسر يعمل — بانتظار رمز الربط")
        except FileNotFoundError:
            self.notify.emit("Node.js غير مثبّت — ثبّته أولاً من الخطوة 2")
        except Exception as e:
            log.warning("whatsapp bridge start failed: %s", e, exc_info=True)
            self.notify.emit(f"تعذّر تشغيل الجسر: {friendly_fs_error(e)}")
        finally:
            # Guarded setter, not a raw emit: this finally block runs on a
            # daemon thread (npm install / node startup) that can easily
            # outlive QCoreApplication teardown — see _set_models_busy above.
            self._set_wa_starting(False)

    @Slot()
    def stopWhatsAppBridge(self):
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

    def _wa_event_from_thread(self, kind, payload):
        """يُستدعى من خيط المستقبِل — مرّره إلى خيط الواجهة عبر إشارة."""
        self._waEvent.emit(kind, dict(payload or {}))

    @Slot(str, "QVariant")
    def _on_wa_event(self, kind, payload):
        payload = self._to_py(payload) or {}
        if kind == "qr":
            qr = payload.get("qr") or ""
            if qr:
                self._wa_qr_matrix = self._qr_matrix(qr)
                self.waChanged.emit()
        elif kind == "status":
            linked = bool(payload.get("linked"))
            if linked and not self._wa_linked:
                self._wa_linked = True
                self._wa_phone = str(payload.get("phone") or "")
                self._wa_qr_matrix = []
                self.notify.emit("تم ربط واتساب بنجاح")
            elif not linked:
                self._wa_linked = False
            self.waChanged.emit()

    def _qr_matrix(self, payload: str):
        """حوّل نص QR إلى صفوف "0/1" تُرسم في QML — بلا ملفات صور."""
        try:
            import qrcode
            q = qrcode.QRCode(border=0)
            q.add_data(payload)
            q.make(fit=True)
            return ["".join("1" if c else "0" for c in row)
                    for row in q.get_matrix()]
        except ImportError:
            # لا تدع النافذة تنتظر بلا نهاية — أظهر السبب للمستخدم
            self.logMessage.emit("حزمة qrcode غير مثبّتة في بايثون الذي يشغّل التطبيق")
            self.notify.emit("حزمة qrcode غير مثبّتة — ثبّت متطلبات التطبيق: pip install -r requirements.txt")
            return []
        except Exception as e:
            log.warning("QR matrix generation failed: %s", e, exc_info=True)
            self.logMessage.emit(f"تعذّر توليد رمز QR: {friendly_fs_error(e)}")
            return []

    # ───────────────────────── dashboard ─────────────────────────
    @Slot()
    def clearDashboard(self):
        """مسح لوحة التحكم — يحذف latest.json ويُفرّغ النتائج المعروضة."""
        try:
            if LATEST_F.exists():
                LATEST_F.unlink()
        except Exception as e:
            log.warning("latest-results delete failed: %s", e, exc_info=True)
            self.logMessage.emit(f"تعذّر حذف ملف النتائج الأخيرة — {friendly_fs_error(e)}")
        self._results, self._dash = {}, {}
        self._date = ""
        self.dashModelChanged.emit()
        self.reportDateChanged.emit()
        self.notify.emit("مُسحت لوحة التحكم")

    # ───────────────────────── internals ─────────────────────────
    def _set_busy(self, v):
        self._busy = v
        self.busyChanged.emit()

    def _set_testing_engine(self, v):
        self._testing_engine = v
        if self._shutting_down:
            return
        try:
            self.testingChanged.emit()
        except RuntimeError:
            pass          # C++ half already gone — nothing left to notify

    def _set_testing_email(self, v):
        self._testing_email = v
        if self._shutting_down:
            return
        try:
            self.testingChanged.emit()
        except RuntimeError:
            pass          # C++ half already gone — nothing left to notify

    def _set_sending_email(self, v):
        self._sending_email = v
        if self._shutting_down:
            return
        try:
            self.emailSendingChanged.emit()
        except RuntimeError:
            pass          # C++ half already gone — nothing left to notify

    def _set_collecting(self, v):
        self._collecting = v
        if self._shutting_down:
            return
        try:
            self.collectingChanged.emit()
        except RuntimeError:
            pass          # C++ half already gone — nothing left to notify

    def _set_models_busy(self, v):
        self._models_busy = v
        if self._shutting_down:
            return
        try:
            self.modelsChanged.emit()
        except RuntimeError:
            pass          # C++ half already gone — nothing left to notify

    def _set_wa_starting(self, v):
        self._wa_starting = v
        if self._shutting_down:
            return
        try:
            self.waChanged.emit()
        except RuntimeError:
            pass          # C++ half already gone — nothing left to notify

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

    @staticmethod
    def _localfile(path):
        if not path:
            return ""
        if path.startswith("file://"):
            return QUrl(path).toLocalFile()
        return path

    @staticmethod
    def _to_py(v):
        """كائنات JS القادمة من QML تصل كـ QJSValue في PySide6 — حوّلها إلى
        قيم بايثون قبل dict() وإلا انهار الاستدعاء بـ TypeError."""
        return v.toVariant() if hasattr(v, "toVariant") else v
