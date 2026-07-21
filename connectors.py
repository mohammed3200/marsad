"""
═══════════════════════════════════════════════════════════════
  موصّلات البيانات الحقيقية — Real Data Connectors
  LTT PM Intelligence Desktop

  يتضمن:
  1. EmailConnector  — سحب البريد (IMAP) وإرسال التقارير (SMTP)
  2. WhatsAppHelper  — دليل إعداد الواتساب خطوة بخطوة
  3. ERPConnector    — قراءة ملفات ERP من مجلد مشترك أو بريد
  4. ConnectorHub    — يجمع الكل في نقطة واحدة
═══════════════════════════════════════════════════════════════
"""

import imaplib
import smtplib
import email
import json
import os
import datetime
import threading
import time
import logging
import secrets
from email.header     import decode_header
from email.mime.text  import MIMEText
from email.mime.multipart   import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

try:
    from core.paths import DATA_DIR as _DATA_DIR
    LOG_DIR = _DATA_DIR / "logs"
except Exception:  # pragma: no cover — core not importable in isolation
    LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "connectors.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)
log = logging.getLogger(__name__)


# ════════════════════════════════════════════════════
# 1. موصّل البريد الإلكتروني
# ════════════════════════════════════════════════════
class EmailConnector:
    """
    يسحب الرسائل الجديدة من Gmail/Outlook تلقائياً
    ويُرسل التقارير النهائية لقائمة المسؤولين
    """

    def __init__(self, settings: dict, contacts_db=None):
        self.user       = settings.get("email_user", "")
        self.password   = settings.get("email_password", "")
        self.imap_host  = settings.get("imap_host", "imap.gmail.com")
        self.smtp_host  = settings.get("smtp_host", "smtp.gmail.com")
        self.smtp_port  = int(settings.get("smtp_port", 587))
        self.dept_map   = settings.get("email_dept_map", {})
        self.contacts   = contacts_db
        self._running   = False
        self._thread    = None
        self._callback  = None   # يُستدعى عند وصول رسائل جديدة

    def test_connection(self) -> tuple:
        """اختبار الاتصال — يُعيد (True/False, رسالة)"""
        if not self.user or not self.password:
            return False, "لم تُدخَل بيانات البريد في الإعدادات"
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, timeout=10)
            mail.login(self.user, self.password)
            mail.logout()
            return True, f"✓ الاتصال بـ {self.user} ناجح"
        except imaplib.IMAP4.error as e:
            return False, f"خطأ في تسجيل الدخول: {e}"
        except Exception as e:
            return False, f"خطأ في الاتصال: {e}"

    def fetch_new(self) -> list:
        """سحب الرسائل الجديدة غير المقروءة"""
        if not self.user:
            return []
        reports = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host)
            mail.login(self.user, self.password)
            mail.select("INBOX")
            _, ids = mail.search(None, "UNSEEN")
            for mid in ids[0].split():
                try:
                    _, data = mail.fetch(mid, "(RFC822)")
                    msg     = email.message_from_bytes(data[0][1])
                    sender  = self._decode_str(msg.get("From", ""))
                    subject = self._decode_str(msg.get("Subject", "بدون موضوع"))
                    date    = msg.get("Date", str(datetime.date.today()))
                    dept    = self._find_dept(sender)
                    body, attachments = self._extract_content(msg)
                    rep = {
                        "id"      : f"email_{mid.decode()}_{int(time.time())}",
                        "source"  : "email",
                        "dept"    : dept,
                        "from"    : sender,
                        "subject" : subject,
                        "date"    : date[:10],
                        "content" : f"الموضوع: {subject}\n\n{body}",
                    }
                    if attachments:
                        rep["content"] += "\n\n" + "\n".join(
                            f"[مرفق: {a['name']}]\n{a.get('text','')}"
                            for a in attachments
                        )
                    reports.append(rep)
                    mail.store(mid, "+FLAGS", "\\Seen")
                    log.info(f"بريد من [{sender}] ← قسم [{dept}]")
                except Exception as e:
                    log.warning(f"خطأ في معالجة رسالة: {e}")
            mail.close()
            mail.logout()
        except Exception as e:
            log.error(f"خطأ في البريد: {e}")
        return reports

    def send_report(self, recipients: list, subject: str,
                    html_body: str, attachments: list = None) -> bool:
        """إرسال التقرير النهائي بالبريد مع مرفقات"""
        if not recipients or not self.user:
            return False
        try:
            msg = MIMEMultipart("mixed")
            msg["From"]    = self.user
            msg["To"]      = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            for path in (attachments or []):
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        part = MIMEApplication(f.read())
                    part.add_header("Content-Disposition", "attachment",
                                    filename=os.path.basename(path))
                    msg.attach(part)
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as srv:
                srv.starttls()
                srv.login(self.user, self.password)
                srv.sendmail(self.user, recipients, msg.as_bytes())
            log.info(f"أُرسل التقرير إلى: {recipients}")
            return True
        except Exception as e:
            log.error(f"فشل الإرسال: {e}")
            return False

    def start_auto_fetch(self, interval_minutes: int, callback):
        """بدء السحب التلقائي كل X دقيقة"""
        self._callback = callback
        self._running  = True
        def loop():
            while self._running:
                try:
                    reports = self.fetch_new()
                    if reports and self._callback:
                        self._callback(reports)
                except Exception as e:
                    log.error(f"خطأ في الحلقة التلقائية: {e}")
                for _ in range(interval_minutes * 60):
                    if not self._running:
                        break
                    time.sleep(1)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        log.info(f"السحب التلقائي بدأ — كل {interval_minutes} دقيقة")

    def stop(self):
        self._running = False

    def _decode_str(self, s: str) -> str:
        parts = []
        for part, enc in decode_header(s):
            if isinstance(part, bytes):
                parts.append(part.decode(enc or "utf-8", errors="ignore"))
            else:
                parts.append(str(part))
        return " ".join(parts)

    def _find_dept(self, sender: str) -> str:
        """تحديد القسم من عنوان المرسل"""
        sl = sender.lower()
        # 1. من جهات الاتصال
        if self.contacts:
            emp = self.contacts.find_by_email(sl.split("<")[-1].strip(">").strip())
            if emp:
                from contacts_manager import DEPT_KEY_MAP
                return DEPT_KEY_MAP.get(emp.get("sub_dept", ""), "admin")
        # 2. من الخريطة الثابتة
        for addr, dept in self.dept_map.items():
            if addr.lower() in sl:
                return dept
        return "admin"

    def _extract_content(self, msg) -> tuple:
        """استخراج نص الرسالة والمرفقات"""
        body = ""
        attachments = []
        for part in msg.walk():
            ct   = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body    = part.get_payload(decode=True).decode(
                                  charset, errors="ignore")
                except Exception:
                    pass
            elif ct == "application/pdf":
                fname = part.get_filename() or f"attach_{int(time.time())}.pdf"
                data  = part.get_payload(decode=True)
                text  = self._pdf_to_text(data)
                attachments.append({"name": fname, "text": text, "type": "pdf"})
            elif fname := part.get_filename():
                data = part.get_payload(decode=True)
                attachments.append({"name": fname, "type": "file",
                                    "size": len(data) if data else 0})
        return body.strip(), attachments

    def _pdf_to_text(self, data: bytes) -> str:
        try:
            import PyPDF2, io
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            return "[PDF — تعذّر استخراج النص]"


# ════════════════════════════════════════════════════
# 2. دليل إعداد الواتساب
# ════════════════════════════════════════════════════
class WhatsAppHelper:
    """
    يوفر تعليمات وأدوات لإعداد تكامل الواتساب
    الاتصال الفعلي يتم عبر Node.js Baileys (ملف منفصل)
    """

    SETUP_STEPS = [
        "① تأكد من تثبيت Node.js من nodejs.org",
        "② في مجلد التطبيق شغّل: npm install @whiskeysockets/baileys express pino",
        "③ شغّل: node whatsapp_bridge.js",
        "④ ستظهر QR Code في نافذة CMD",
        "⑤ افتح واتساب → ⋮ → الأجهزة المرتبطة → ربط جهاز",
        "⑥ امسح QR Code بكاميرا هاتفك",
        "⑦ الاتصال يبقى نشطاً طالما الهاتف متصل بالإنترنت",
    ]

    GROUP_SETUP = [
        "① أنشئ مجموعة واتساب لكل قسم (RAN, Core, الجودة...)",
        "② أضف رقم الهاتف المرتبط بالنظام لكل مجموعة",
        "③ عند وصول أي رسالة في المجموعة يستقبلها النظام",
        "④ يمكن إرسال: نص عادي، صورة ميدانية، ملف PDF",
        "⑤ النظام يتعرف على القسم من اسم المجموعة أو رقم المرسل",
    ]

    WHATSAPP_BRIDGE_JS = """\
// whatsapp_bridge.js
// شغّله بـ: node whatsapp_bridge.js
const { default: makeWASocket, useMultiFileAuthState,
        DisconnectReason } = require('@whiskeysockets/baileys')
const express = require('express')
const P       = require('pino')

const app  = express()
app.use(express.json())
const PORT = 5050

let sock = null

async function start() {
    const { state, saveCreds } = await useMultiFileAuthState('./wa_session')
    sock = makeWASocket({
        auth: state,
        logger: P({ level: 'silent' }),
        printQRInTerminal: true
    })
    sock.ev.on('creds.update', saveCreds)
    sock.ev.on('connection.update', ({ connection, qr }) => {
        if (qr)         console.log('[WA] امسح QR Code الآن...')
        if (connection === 'open')  console.log('[WA] متصل!')
        if (connection === 'close') setTimeout(start, 3000)
    })
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return
        for (const msg of messages) {
            if (msg.key.fromMe) continue
            const gid  = msg.key.remoteJid
            const text = msg.message?.conversation
                      || msg.message?.extendedTextMessage?.text || ''
            let image_b64 = null
            if (msg.message?.imageMessage) {
                try {
                    const buf  = await sock.downloadMediaMessage(msg, 'buffer')
                    image_b64  = buf.toString('base64')
                } catch(e) {}
            }
            // إرسال للـ Python
            try {
                const fetch = (await import('node-fetch')).default
                await fetch('http://localhost:5051/wa_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-WA-Token': '__WA_TOKEN__' },
                    body: JSON.stringify({
                        group_id : gid,
                        sender   : msg.pushName || '',
                        text     : text,
                        image_b64: image_b64,
                        ts       : new Date().toISOString()
                    })
                })
            } catch(e) { console.error('[WA] فشل إرسال للـ Python:', e.message) }
        }
    })
}

start()
app.get('/status', (_, res) => res.json({ connected: !!sock }))
app.listen(PORT, () => console.log('[WA Bridge] يعمل على', PORT))
"""

    @staticmethod
    def save_bridge_file(port: int = 5051, token: str = ""):
        """حفظ ملف Node.js Bridge في مجلد البيانات مع حقن منفذ المستقبِل
        ورمز X-WA-Token المشترك (إن وُجد)."""
        from core.paths import DATA_DIR
        out = DATA_DIR / "whatsapp_bridge.js"
        js = WhatsAppHelper.WHATSAPP_BRIDGE_JS.replace(
            "localhost:5051", f"localhost:{int(port)}")
        if token:
            js = js.replace("__WA_TOKEN__", token)
        else:
            js = js.replace(", 'X-WA-Token': '__WA_TOKEN__'", "")
        out.write_text(js, encoding="utf-8")
        return str(out)

    @staticmethod
    def check_nodejs() -> tuple:
        """التحقق من تثبيت Node.js"""
        import subprocess
        try:
            r = subprocess.run(["node", "--version"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return True, r.stdout.strip()
            return False, "Node.js غير مثبت"
        except FileNotFoundError:
            return False, "Node.js غير مثبت — حمّله من nodejs.org"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def install_packages() -> bool:
        """تثبيت حزم Node.js المطلوبة"""
        import subprocess
        bridge_dir = Path(__file__).parent
        pkg_json   = bridge_dir / "package.json"
        if not pkg_json.exists():
            with open(pkg_json, "w") as f:
                json.dump({
                    "name": "ltt-wa-bridge",
                    "version": "1.0.0",
                    "type": "module",
                    "dependencies": {
                        "@whiskeysockets/baileys": "^6.7.0",
                        "express"               : "^4.18.0",
                        "node-fetch"            : "^3.3.0",
                        "pino"                  : "^8.0.0"
                    }
                }, f, indent=2)
        r = subprocess.run(["npm", "install"],
                           cwd=str(bridge_dir),
                           capture_output=True, text=True)
        return r.returncode == 0


# ════════════════════════════════════════════════════
# مستقبِل رسائل واتساب — خادم HTTP محلي يستقبل من جسر Baileys
# WhatsApp receiver — local HTTP server the Node/Baileys bridge POSTs to
# ════════════════════════════════════════════════════
class WhatsAppReceiver:
    """يستمع على 127.0.0.1:<port>/wa_message ويحوّل كل رسالة إلى تقرير عبر
    on_message([report]). stdlib فقط — لا تبعيات جديدة."""

    def __init__(self, port: int, on_message, dept_fn=None, logger=print,
                 token: str = ""):
        self.port       = int(port)
        self.on_message = on_message
        self.dept_fn    = dept_fn or (lambda gid: "admin")
        self.log        = logger
        self.token      = token
        self._server    = None
        self._thread    = None

    def start(self):
        import http.server
        recv = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):   # اكتم سجل الوصول
                pass

            def _ok(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def do_GET(self):
                self._ok()

            def do_POST(self):
                if self.path.rstrip("/") != "/wa_message":
                    self.send_response(404); self.end_headers(); return
                if recv.token and self.headers.get("X-WA-Token") != recv.token:
                    self.send_response(403); self.end_headers(); return
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    data   = json.loads(self.rfile.read(length) or b"{}")
                except Exception:
                    self.send_response(400); self.end_headers(); return
                text = (data.get("text") or "").strip()
                gid  = data.get("group_id", "")
                if text:
                    rep = {
                        "id"     : f"whatsapp_{int(time.time()*1000)}",
                        "source" : "whatsapp",
                        "dept"   : recv.dept_fn(gid),
                        "from"   : data.get("sender") or gid or "واتساب",
                        "date"   : datetime.date.today().isoformat(),
                        "content": text,
                    }
                    try:
                        recv.on_message([rep])
                        log.info(f"واتساب: رسالة من [{rep['from']}] ← [{rep['dept']}]")
                    except Exception as e:
                        log.warning(f"واتساب: خطأ في المعالجة: {e}")
                self._ok()

        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.log(f"[WA] المستقبِل يعمل على 127.0.0.1:{self.port}")

    def stop(self):
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None


# ════════════════════════════════════════════════════
# قارئ الملفات المشترك — يُستخدم من ERP ومن رفع الملفات اليدوي
# Shared file reader — used by the ERP watcher and manual upload
# ════════════════════════════════════════════════════
# الامتدادات المدعومة كتقارير ميدانية
DOC_PATTERNS = ["*.xlsx", "*.xls", "*.csv", "*.json", "*.txt", "*.pdf", "*.docx"]


def guess_dept(filename: str) -> str:
    """محاولة تخمين القسم من اسم الملف"""
    fl = filename.lower()
    mapping = {
        "ran"      : "ran",   "radio"   : "ran",
        "core"     : "core",  "network" : "core",
        "quality"  : "quality","جودة"   : "quality",
        "safety"   : "safety", "سلامة"  : "safety",
        "civil"    : "civil",  "انشاء"  : "civil",
        "cost"     : "cost",   "تكالف"  : "cost",
        "finance"  : "cost",   "مالية"  : "cost",
        "contract" : "contract","عقود"  : "contract",
        "procure"  : "procure","مشتريات": "procure",
        "supply"   : "supply", "مخازن"  : "supply",
        "schedule" : "schedule","جدول"  : "schedule",
    }
    for key, dept in mapping.items():
        if key in fl:
            return dept
    return "admin"


def _read_excel(fpath: Path) -> str:
    try:
        import openpyxl
        wb   = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        rows = []
        for ws in wb.worksheets[:3]:   # أول 3 أوراق فقط
            rows.append(f"=== ورقة: {ws.title} ===")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i > 200: break        # أول 200 صف
                cells = [str(c) if c is not None else "" for c in row]
                line  = " | ".join(cells).strip(" |")
                if line:
                    rows.append(line)
        return "\n".join(rows)
    except ImportError:
        return "[يحتاج مكتبة openpyxl — pip install openpyxl]"
    except Exception as e:
        return f"[خطأ في قراءة Excel: {e}]"


def _read_csv(fpath: Path) -> str:
    import csv
    rows = []
    with open(fpath, encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i > 500: break
            rows.append(" | ".join(row))
    return "\n".join(rows)


def _read_json(fpath: Path) -> str:
    data = json.loads(fpath.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)[:5000]


def _read_pdf(fpath: Path) -> str:
    try:
        import PyPDF2
        with open(fpath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(p.extract_text() or "" for p in reader.pages)
    except ImportError:
        return "[يحتاج مكتبة PyPDF2 — pip install PyPDF2]"
    except Exception as e:
        return f"[خطأ في PDF: {e}]"


def _read_docx(fpath: Path) -> str:
    try:
        import docx
        doc = docx.Document(str(fpath))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "[يحتاج مكتبة python-docx — pip install python-docx]"
    except Exception as e:
        return f"[خطأ في Word: {e}]"


def read_file_to_report(fpath, source: str = "upload",
                        dept: str = None, from_label: str = None) -> dict | None:
    """قراءة ملف واحد وتحويله إلى تقرير — يدعم xlsx/xls/csv/json/txt/pdf/docx.
    يُعيد None للامتدادات غير المدعومة أو المحتوى الفارغ."""
    fpath = Path(fpath)
    ext   = fpath.suffix.lower()
    dept  = dept or guess_dept(fpath.name)

    if ext in (".xlsx", ".xls"):
        content = _read_excel(fpath)
    elif ext == ".csv":
        content = _read_csv(fpath)
    elif ext == ".json":
        content = _read_json(fpath)
    elif ext == ".txt":
        content = fpath.read_text(encoding="utf-8", errors="ignore")
    elif ext == ".pdf":
        content = _read_pdf(fpath)
    elif ext == ".docx":
        content = _read_docx(fpath)
    else:
        return None

    if not content:
        return None

    return {
        "id"     : f"{source}_{fpath.stem}_{int(time.time())}",
        "source" : source,
        "dept"   : dept,
        "from"   : from_label or fpath.name,
        "date"   : datetime.date.today().isoformat(),
        "content": content,
    }


# ════════════════════════════════════════════════════
# 3. موصّل ERP — يقرأ ملفات Excel/CSV من مجلد
# ════════════════════════════════════════════════════
class ERPConnector:
    """
    يراقب مجلداً محدداً ويقرأ ملفات ERP تلقائياً
    يدعم: Excel (.xlsx/.xls), CSV, JSON, TXT, PDF, Word (.docx)
    """

    def __init__(self, watch_folder: str = "", dept_map: dict = None):
        self.folder   = Path(watch_folder) if watch_folder else None
        self.dept_map = dept_map or {}
        self._seen    = set()   # ملفات تمت معالجتها
        self._running = False

    def set_folder(self, folder: str):
        self.folder = Path(folder)

    def scan_folder(self) -> list:
        """فحص المجلد وإرجاع ملفات جديدة كتقارير"""
        if not self.folder or not self.folder.exists():
            return []
        reports = []
        for pattern in DOC_PATTERNS:
            for fpath in self.folder.glob(pattern):
                if fpath.name in self._seen:
                    continue
                try:
                    rep = self._read_file(fpath)
                    if rep:
                        reports.append(rep)
                        self._seen.add(fpath.name)
                        log.info(f"ERP: قُرئ {fpath.name}")
                except Exception as e:
                    log.warning(f"ERP: خطأ في {fpath.name}: {e}")
        return reports

    def _read_file(self, fpath: Path) -> dict | None:
        # خريطة الأقسام المُعدّة أولاً — مفاتيحها عناوين بريد، لذا نطابق
        # الجزء المحلي (قبل @) ككلمة مستقلة مع اسم الملف — ثم التخمين
        import re
        fname = fpath.name.lower()
        for key, dept in self.dept_map.items():
            kw = key.lower().split("@", 1)[0].strip()
            if kw and re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", fname):
                return read_file_to_report(fpath, source="erp", dept=dept,
                                           from_label=f"ERP: {fpath.name}")
        return read_file_to_report(fpath, source="erp",
                                   from_label=f"ERP: {fpath.name}")

    def start_watching(self, interval_seconds: int, callback):
        """مراقبة المجلد باستمرار"""
        self._running = True
        def loop():
            while self._running:
                reports = self.scan_folder()
                if reports and callback:
                    callback(reports)
                time.sleep(interval_seconds)
        threading.Thread(target=loop, daemon=True).start()

    def stop(self):
        self._running = False


# ════════════════════════════════════════════════════
# 4. المحور المركزي — يجمع كل المصادر
# ════════════════════════════════════════════════════
class ConnectorHub:
    """
    نقطة تحكم واحدة تجمع: البريد + ERP + الواتساب
    استخدامه من التطبيق الرئيسي:
        hub = ConnectorHub(settings, contacts_db)
        hub.start(on_new_reports)
        reports = hub.collect_all()
    """

    def __init__(self, settings: dict, contacts_db=None):
        self.settings = settings
        self.email    = EmailConnector(settings, contacts_db)
        self.erp      = ERPConnector(
            watch_folder=settings.get("erp_folder", ""),
            dept_map=settings.get("email_dept_map", {})
        )
        self._buffer  = []
        self._lock    = threading.Lock()
        self._log_fn  = print
        self.whatsapp = None
        # الرمز يُحفظ في الإعدادات حتى يبقى ثابتاً عند إعادة بناء المحور —
        # وإلا توقف ملف الجسر المولَّد سابقاً عن العمل (403)
        self.wa_token = settings.get("whatsapp_token") or secrets.token_hex(16)
        settings["whatsapp_token"] = self.wa_token

    def set_logger(self, fn):
        self._log_fn = fn

    # ── واتساب ──
    def _wa_dept(self, group_id: str) -> str:
        groups = self.settings.get("whatsapp_groups", {})
        return groups.get(group_id) or groups.get(str(group_id), "admin")

    def start_whatsapp(self, port: int = 5051):
        """بدء مستقبِل واتساب — الرسائل الواردة تدخل نفس الـ buffer الذي يفرّغه
        collect_all()، تماماً مثل البريد و ERP."""
        if self.whatsapp:
            self.whatsapp.stop()
        self.whatsapp = WhatsAppReceiver(port, self._append, self._wa_dept,
                                         self._log_fn, token=self.wa_token)
        self.whatsapp.start()

    def _append(self, reports: list):
        with self._lock:
            self._buffer.extend(reports)
        if reports:
            self._log_fn(f"📥 {len(reports)} تقرير جديد وصل")

    def start_all(self, interval_email: int = 30, interval_erp: int = 5):
        """بدء جميع المصادر في الخلفية"""
        # البريد
        if self.settings.get("email_user"):
            self.email.start_auto_fetch(interval_email, self._append)
            self._log_fn(f"📧 البريد نشط — كل {interval_email} دقيقة")

        # ERP
        if self.settings.get("erp_folder"):
            self.erp.start_watching(interval_erp * 60, self._append)
            self._log_fn(f"🖥️ ERP نشط — كل {interval_erp} دقيقة")

    def collect_all(self) -> list:
        """جمع كل التقارير المتراكمة وتفريغ الـ buffer"""
        # بريد فوري
        try:
            email_now = self.email.fetch_new()
            if email_now:
                self._log_fn(f"📧 {len(email_now)} رسالة جديدة من البريد")
        except Exception:
            email_now = []

        # ERP فوري
        try:
            erp_now = self.erp.scan_folder()
            if erp_now:
                self._log_fn(f"🖥️ {len(erp_now)} ملف جديد من ERP")
        except Exception:
            erp_now = []

        # Buffer (واتساب + تلقائي)
        with self._lock:
            buffered = list(self._buffer)
            self._buffer.clear()

        all_reports = email_now + erp_now + buffered
        if all_reports:
            self._log_fn(f"✓ إجمالي التقارير المُجمَّعة: {len(all_reports)}")
        return all_reports

    def stop_all(self):
        targets = [("البريد", self.email), ("ERP", self.erp)]
        if self.whatsapp:
            targets.append(("واتساب", self.whatsapp))
        for name, conn in targets:
            try:
                conn.stop()
            except Exception as e:
                log.warning(f"فشل إيقاف {name}: {e}")
                self._log_fn(f"فشل إيقاف {name}: {e}")

    def test_email(self) -> tuple:
        return self.email.test_connection()

    def send_report(self, recipients, subject, html, attachments=None) -> bool:
        return self.email.send_report(recipients, subject, html, attachments)


# ════════════════════════════════════════════════════
# بناء HTML للتقرير المُرسَل بالبريد
# ════════════════════════════════════════════════════
def build_report_html(results: dict) -> str:
    chief  = results.get("chief", {})
    health = chief.get("overall_health", "غير محدد")
    color  = "#10b981" if health == "جيد" else \
             "#f59e0b" if health == "متوسط" else "#ef4444"
    date   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    actions_rows = ""
    for act in chief.get("top_actions", [])[:5]:
        actions_rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #e2e8f0;text-align:center;
                     font-weight:bold;">{act.get('priority','')}</td>
          <td style="padding:8px;border:1px solid #e2e8f0;">{act.get('action','')}</td>
          <td style="padding:8px;border:1px solid #e2e8f0;">{act.get('owner','')}</td>
          <td style="padding:8px;border:1px solid #e2e8f0;">{act.get('deadline','')}</td>
        </tr>"""

    kpi_cards = ""
    for kpi in chief.get("kpis", [])[:6]:
        sc = "#10b981" if kpi.get("status") == "جيد" else \
             "#f59e0b" if kpi.get("status") == "تحذير" else "#ef4444"
        kpi_cards += f"""
        <div style="background:#f8fafc;border:1px solid {sc};border-radius:8px;
                    padding:12px;text-align:center;min-width:100px;">
          <div style="font-size:20px;font-weight:bold;color:{sc};">{kpi.get('value','')}</div>
          <div style="font-size:11px;color:#64748b;">{kpi.get('name','')}</div>
          <div style="font-size:14px;">{kpi.get('trend','→')}</div>
        </div>"""

    return f"""
    <html dir="rtl">
    <body style="font-family:Arial,sans-serif;background:#f8fafc;padding:24px;direction:rtl;">
      <div style="max-width:700px;margin:auto;background:white;border-radius:12px;
                  padding:28px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

        <h1 style="color:#0d1f3c;border-bottom:3px solid #2563eb;padding-bottom:12px;
                   font-size:20px;">
          تقرير مشروع LTT 4G/5G — المنطقة الوسطى
        </h1>
        <p style="color:#64748b;font-size:12px;">{date}</p>

        <div style="background:{color}20;border:2px solid {color};border-radius:10px;
                    padding:14px;text-align:center;margin:16px 0;">
          <span style="font-size:18px;font-weight:bold;color:{color};">
            الحالة العامة: {health}
          </span>
        </div>

        <h2 style="color:#1e3a5f;font-size:15px;">مؤشرات الأداء</h2>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;">
          {kpi_cards}
        </div>

        <h2 style="color:#1e3a5f;font-size:15px;">الملخص التنفيذي</h2>
        <p style="line-height:1.8;color:#334155;font-size:13px;">
          {chief.get('executive_summary', '')}
        </p>

        <h2 style="color:#1e3a5f;font-size:15px;">خطة العمل الفورية</h2>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr style="background:#1e3a5f;color:white;">
            <th style="padding:10px;border:1px solid #e2e8f0;">الأولوية</th>
            <th style="padding:10px;border:1px solid #e2e8f0;">الإجراء</th>
            <th style="padding:10px;border:1px solid #e2e8f0;">المسؤول</th>
            <th style="padding:10px;border:1px solid #e2e8f0;">الموعد</th>
          </tr>
          {actions_rows}
        </table>

        <p style="margin-top:24px;color:#94a3b8;font-size:11px;border-top:1px solid #e2e8f0;
                  padding-top:12px;">
          LTT PM Intelligence System — تقرير مولَّد تلقائياً |
          {date}
        </p>
      </div>
    </body>
    </html>"""
