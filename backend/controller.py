"""AppController — the single QObject QML talks to.

Owns settings, the contacts DB, the connector hub, and the AI engine; exposes
app state (dashboard model, health, connection) as properties and actions as
slots. Analysis runs on a worker thread; results flow back via signals.
"""
import json
import datetime
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Property, QThread, QUrl
from PySide6.QtGui import QDesktopServices

from core import AIEngine, AgentsEngine, ContactsDB, export_pdf, export_excel, WORKER_AGENTS
from core.paths import DATA_DIR, BUNDLE_DIR
from connectors import ConnectorHub, build_report_html, read_file_to_report
from .settings_bridge import load_settings, save_settings
from .models import AgentsModel, ReportsModel
from .analysis_worker import AnalysisWorker

REPORTS    = DATA_DIR / "reports"                  # writable output
SAMPLES_F  = BUNDLE_DIR / "sample_reports.json"    # shipped demo input
LATEST_F   = REPORTS / "latest.json"


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
    exportDone        = Signal(str)          # path
    exportFailed      = Signal(str)
    reportsChanged    = Signal()
    notify            = Signal(str)          # transient user message
    navRequested      = Signal(int)          # page index to switch to
    settingsChanged   = Signal()
    _collected        = Signal("QVariant")   # reports gathered off the GUI thread
    _filesAdded       = Signal("QVariant")   # files parsed off the GUI thread

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
        self._thread   = None
        self._worker   = None
        self._collected.connect(self._on_collected)
        self._filesAdded.connect(self._on_files_added)
        self._hub.set_logger(lambda m: self.logMessage.emit(str(m)))
        self._load_latest()
        self._start_whatsapp_if_enabled()

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
            self.notify.emit(f"تعذّر تحميل النماذج: {e}")

    @Slot()
    def collectReports(self):
        if self._collecting:
            return
        self._collecting = True
        threading.Thread(target=self._run_collect, daemon=True).start()

    def _run_collect(self):
        """جمع التقارير (IMAP/ERP/HTTP) على خيط منفصل حتى لا تتجمّد الواجهة."""
        try:
            self._collected.emit(self._hub.collect_all())
        except Exception as e:
            self.notify.emit(f"تعذّر الجمع: {e}")
            self._collecting = False

    @Slot("QVariant")
    def _on_collected(self, reps):
        self._collecting = False
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

    @Slot("QVariant")
    def _on_files_added(self, res):
        self._adding = False
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
        r = dict(report) if report else {}
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

        engine = AgentsEngine(self._ai)
        self._thread = QThread(self)
        self._worker = AnalysisWorker(engine, self._reports.reports())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.agentState.connect(self._agents.set_state)
        self._worker.progress.connect(self.progress)
        self._worker.log.connect(self.logMessage)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
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
            self._thread = None
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
            self.exportDone.emit(out)
            self.notify.emit(f"حُفظ الملف: {out}")
        except Exception as e:
            self.exportFailed.emit(str(e))
            self.notify.emit(f"تعذّر التصدير: {e}")

    @Slot()
    def openReportsFolder(self):
        REPORTS.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(REPORTS)))

    @Slot()
    def sendEmailReport(self):
        if not self._results:
            self.notify.emit("لا توجد نتائج لإرسالها")
            return
        recipients = (self._settings.get("report_recipients")
                      or list(self._settings.get("email_dept_map", {}).keys()))
        if not recipients:
            self.notify.emit("لا يوجد مستلمون مضبوطون في الإعدادات")
            return
        try:
            html = build_report_html(self._results)
            ok = self._hub.send_report(recipients, "تقرير حالة المشروع — مرصد", html)
            self.notify.emit("أُرسل التقرير بالبريد" if ok else "تعذّر إرسال البريد")
        except Exception as e:
            self.notify.emit(f"خطأ في الإرسال: {e}")

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
            ok, msg = self._ai.test_connection()
        except Exception as e:
            ok, msg = False, str(e)
        self._online = ok
        self._status = "متصل" if ok else "غير متصل"
        self.engineChanged.emit()
        self.connectionTested.emit(ok, msg)
        self._set_testing_engine(False)

    @Slot("QVariant")
    def saveSettings(self, values):
        if values:
            self._settings.update(dict(values))
        save_settings(self._settings)
        self._ai.settings = self._settings
        # الموصّلات تلتقط الإعدادات عند الإنشاء — أعد بناء الـ hub حتى تسري
        # بيانات البريد / مجلد ERP / واتساب الجديدة فوراً.
        self._rebuild_hub()
        self.settingsChanged.emit()
        self.notify.emit("حُفظت الإعدادات")

    def _rebuild_hub(self):
        try:
            self._hub.stop_all()
        except Exception as e:
            self.logMessage.emit(f"تعذّر إيقاف الموصّلات السابقة — {e}")
        self._hub = ConnectorHub(self._settings, self._contacts)
        self._hub.set_logger(lambda m: self.logMessage.emit(str(m)))
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
            ok, msg = self._hub.test_email()
        except Exception as e:
            ok, msg = False, str(e)
        self.emailTested.emit(ok, msg)
        self.notify.emit(msg)
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
        self._contacts.add_employee(dict(emp))

    @Slot(int, "QVariant")
    def updateEmployee(self, emp_id, fields):
        self._contacts.update_employee(emp_id, dict(fields))

    @Slot(int)
    def deleteEmployee(self, emp_id):
        self._contacts.delete_employee(emp_id)

    @Slot()
    def syncContacts(self):
        maps = self._contacts.export_to_config()
        self._settings["email_dept_map"] = maps["email_dept_map"]
        self._settings["whatsapp_groups"] = maps["whatsapp_groups"]
        save_settings(self._settings)
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
            self.logMessage.emit(f"واتساب: تعذّر بدء المستقبِل — {e}")

    @Slot()
    def generateWhatsAppBridge(self):
        from connectors import WhatsAppHelper
        try:
            port = int(self._settings.get("whatsapp_port", 5051))
            token = getattr(self._hub, "wa_token", "")
            path = WhatsAppHelper.save_bridge_file(port, token=token)
            self.notify.emit(f"أُنشئ ملف الجسر: {path}")
        except Exception as e:
            self.notify.emit(f"تعذّر إنشاء الجسر: {e}")

    @Slot()
    def checkNode(self):
        from connectors import WhatsAppHelper
        ok, msg = WhatsAppHelper.check_nodejs()
        self.notify.emit(f"Node.js: {msg}" if ok else msg)

    # ───────────────────────── dashboard ─────────────────────────
    @Slot()
    def clearDashboard(self):
        """مسح لوحة التحكم — يحذف latest.json ويُفرّغ النتائج المعروضة."""
        try:
            if LATEST_F.exists():
                LATEST_F.unlink()
        except Exception as e:
            self.logMessage.emit(f"تعذّر حذف ملف النتائج الأخيرة — {e}")
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
        self.testingChanged.emit()

    def _set_testing_email(self, v):
        self._testing_email = v
        self.testingChanged.emit()

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
