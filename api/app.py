"""FastAPI app — REST (/api) + WebSocket (/ws) over AppService.

Local-only: binds 127.0.0.1 (see api/__main__.py). All blocking service calls
run in FastAPI's threadpool (sync `def` endpoints); long-running operations
start daemon threads inside AppService and report back over the WebSocket.

Not shipped in this release (see "Release scope: desktop only" in
docs/superpowers/plans/2026-07-28-launch-readiness.md): this module refuses
to import unless MARSAD_API_ENABLE=1 is set. There is no authentication
layer — do not expose this beyond loopback.
"""
import os

if os.environ.get("MARSAD_API_ENABLE") != "1":
    raise RuntimeError(
        "الواجهة البرمجية غير مفعّلة في هذا الإصدار — "
        "شغّلها بـ MARSAD_API_ENABLE=1 على مسؤوليتك (تجريبية، بلا مصادقة)."
    )

import asyncio
import datetime
import json
import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.paths import BUNDLE_DIR, DATA_DIR

from .services import AppService, ENGINE_KEYS

service = AppService()
app = FastAPI(title="marsad API", docs_url="/api/docs")

# Settings keys never sent to an HTTP client — GET redacts them to "" and
# reports only whether each is set; PUT treats a blank value as "unchanged".
# api_token is not introduced in this release (no auth layer ships), so it is
# not part of this tuple.
SECRET_KEYS = ("claude_api_key", "openai_api_key", "gemini_api_key",
               "azure_api_key", "email_password", "whatsapp_token")

# The subset of SECRET_KEYS that also gets copied verbatim into every saved
# engine profile (ENGINE_KEYS, api/services.py) — "save current engine config
# as a named profile" snapshots these into settings["engine_profiles"][i], so
# each profile needs the exact same redact-on-GET / blank-means-unchanged-on-
# PUT treatment as the top-level settings, or a saved profile's real provider
# keys leak straight through GET /api/settings one level down.
PROFILE_SECRET_KEYS = tuple(k for k in SECRET_KEYS if k in ENGINE_KEYS)

# Upload bounds. Without these a single request could stream an unbounded file
# into memory, and every byte of it ends up in an LLM prompt downstream.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024   # per file
MAX_UPLOAD_FILES = 20                 # per request
_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|]')
_CONTROL_CHARS = re.compile(r'[\x00-\x1f]')


def _safe_upload_name(raw: str) -> str:
    """A filename that is safe to join onto the uploads directory.

    Path(...).name already strips client-side directories, but leaves "." and
    ".." intact — both name an existing directory, so opening them for write
    raises IsADirectoryError and the endpoint 500s. Control characters
    (including an embedded null byte) are stripped too: Path(...).name lets
    them through unmodified, and a null byte reaching open() raises
    ValueError, not OSError, so it would otherwise bypass the except clause
    below and surface as an unhandled 500.
    """
    name = Path(raw or "").name
    name = _CONTROL_CHARS.sub("", name)
    if name in ("", ".", ".."):
        name = "upload"
    name = _UNSAFE_NAME.sub("_", name)
    # Truncate the stem, not the whole name — otherwise a long filename loses
    # its extension, and read_file_to_report dispatches on fpath.suffix, so
    # the upload would silently be dropped downstream instead of processed.
    stem, suffix = os.path.splitext(name)
    suffix = suffix[:120]
    stem = stem[:max(0, 120 - len(suffix))]
    return stem + suffix


def _profile_list(value) -> list:
    """Coerce a possibly-malformed engine_profiles value into a clean list of
    profile dicts. settings.json is hand-editable and engine_profiles arrives
    over an unauthenticated PUT, so it cannot be trusted to already be
    well-shaped — a non-list value (None, a string, ...) degrades to "no
    profiles", and non-dict entries within an otherwise-valid list are
    skipped, the same "degrade, never raise" rule every other path in this
    module follows."""
    if not isinstance(value, list):
        return []
    return [p for p in value if isinstance(p, dict)]


def _redact_profile(profile: dict) -> dict:
    """Blank a saved engine profile's secret fields; report which were set."""
    safe = dict(profile)
    secrets_set = {k: bool(safe.get(k)) for k in PROFILE_SECRET_KEYS}
    for key in PROFILE_SECRET_KEYS:
        if key in safe:
            safe[key] = ""
    safe["secrets_set"] = secrets_set
    return safe


def _restore_profile_secrets(new_profiles, old_profiles) -> list:
    """Blank secret fields in an incoming PUT mean 'unchanged' — fill them
    back in from the matching stored profile (matched by name), the same
    rule the top-level settings already follow. Both arguments are coerced
    through _profile_list first, so malformed shapes degrade instead of
    raising (see _profile_list)."""
    old_by_name = {p.get("name"): p for p in _profile_list(old_profiles)}
    merged = []
    for profile in _profile_list(new_profiles):
        profile = dict(profile)
        profile.pop("secrets_set", None)
        prior = old_by_name.get(profile.get("name"), {})
        for key in PROFILE_SECRET_KEYS:
            if key in profile and profile[key] == "":
                profile[key] = prior.get(key, "")
        merged.append(profile)
    return merged


# ───────────────────────── websocket ─────────────────────────
class WSManager:
    def __init__(self):
        self.clients = []
        self.loop = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, event: dict):
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(json.dumps(event, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = WSManager()


def _broadcast_from_service(event: dict):
    """Service events fire on daemon threads — hop onto the event loop."""
    loop = ws_manager.loop
    if loop and not loop.is_closed():
        loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(ws_manager.broadcast(event)))


service.subscribe(_broadcast_from_service)


@app.on_event("startup")
def _capture_loop():
    ws_manager.loop = asyncio.get_event_loop()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        snapshot = {"type": "state_snapshot", **service.snapshot()}
        await ws.send_text(json.dumps(snapshot, ensure_ascii=False))
        while True:
            # keep the connection alive; clients don't send commands (yet)
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(ws)


# ───────────────────────── settings / meta ─────────────────────────
@app.get("/api/meta")
def get_meta():
    return {
        "today_label":   service.today_label,
        "backend":       service.settings.get("ai_backend"),
        "engine_online": service.engine_online,
        "engine_status": service.engine_status,
        "reports_dir":   service.reports_dir,
    }


@app.get("/api/settings")
def get_settings():
    """Secrets are never sent to the client — only whether each one is set."""
    raw = service.settings
    safe = {k: v for k, v in raw.items() if k not in SECRET_KEYS}
    for key in SECRET_KEYS:
        safe[key] = ""
    safe["secrets_set"] = {k: bool(raw.get(k)) for k in SECRET_KEYS}
    safe["engine_profiles"] = [_redact_profile(p)
                               for p in _profile_list(raw.get("engine_profiles"))]
    return safe


@app.put("/api/settings")
def put_settings(values: dict):
    """A blank secret means 'unchanged' — the client never had the real value."""
    values = {k: v for k, v in values.items() if k != "secrets_set"}
    for key in SECRET_KEYS:
        if key in values and values[key] == "":
            values.pop(key)
    if "engine_profiles" in values:
        incoming = values["engine_profiles"]
        # A non-empty list that filters down to zero valid entries (all
        # garbage) is malformed, not an instruction to clear every saved
        # profile — drop it the same as a non-list value, below. Only a
        # list that was *already* empty is a genuine "clear my profiles".
        garbage_only = isinstance(incoming, list) and incoming and not _profile_list(incoming)
        if isinstance(incoming, list) and not garbage_only:
            values["engine_profiles"] = _restore_profile_secrets(
                incoming, service.settings.get("engine_profiles"))
        else:
            # Not a list at all, or a list of nothing but garbage — degrade
            # the same way a malformed *stored* value does (treat as
            # absent) rather than writing an empty profile list over
            # whatever is actually saved, or 500ing.
            values.pop("engine_profiles")
    if values:  # a PUT of only blanked secrets is a no-op, not a full rewrite
        service.save_settings(values)
    return {"ok": True}


@app.post("/api/settings/test/engine")
def test_engine():
    return {"started": service.test_connection()}


@app.post("/api/settings/test/email")
def test_email():
    return {"started": service.test_email()}


@app.post("/api/settings/models")
def fetch_models():
    """Start async model-list fetch; result arrives over WS as `models_fetched`."""
    return {"started": service.fetch_models()}


# ───────────────────────── engine profiles ─────────────────────────
@app.get("/api/engine/profiles")
def engine_profiles():
    return {"profiles": service.engine_profiles}


@app.post("/api/engine/profiles/save")
def save_engine_profile(body: dict):
    # feedback goes through the WS `notify` toast — ok flag drives inline logic
    return {"ok": service.save_engine_profile(str(body.get("name") or ""))}


@app.post("/api/engine/profiles/switch")
def switch_engine_profile(body: dict):
    return {"ok": service.switch_engine_profile(str(body.get("name") or ""))}


@app.delete("/api/engine/profiles/{name}")
def delete_engine_profile(name: str):
    service.delete_engine_profile(name)
    return {"ok": True}


# ───────────────────────── reports (input queue) ─────────────────────────
@app.get("/api/reports")
def get_reports():
    return {"count": service.report_count, "reports": service.reports}


@app.post("/api/reports", status_code=201)
def post_report(report: dict):
    r = service.add_report(report)
    if r is None:
        raise HTTPException(status_code=400, detail="أدخل نص التقرير أولاً")
    return r


@app.delete("/api/reports/{index}")
def delete_report(index: int):
    if not service.remove_report(index):
        raise HTTPException(status_code=404, detail="تقرير غير موجود")
    return {"ok": True}


@app.delete("/api/reports")
def clear_reports():
    service.clear_reports()
    return {"ok": True}


@app.post("/api/reports/samples")
def load_samples():
    return {"loaded": service.load_samples()}


@app.post("/api/reports/collect")
def collect_reports():
    return {"started": service.collect_reports()}


# KNOWN ACCEPTED LIMITATION (launch-readiness Task 7, fix round 1, Important 2):
# `files: list[UploadFile] = File(...)` below makes FastAPI's dependency
# resolution fully drain the ASGI stream and spool every part to a
# SpooledTemporaryFile — spilling to disk past 1 MiB, with no per-file ceiling
# — *before* this function body runs. So MAX_UPLOAD_BYTES / MAX_UPLOAD_FILES
# bound only the secondary copy this function writes into uploads/, not the
# disk, time or bandwidth spent receiving the request in the first place. The
# streaming loop below does correctly stop issuing reads once its own running
# total crosses the cap, but by then the request was already fully received.
# Real enforcement needs Request.stream()-level parsing (an architecture
# change beyond this task) or a reverse-proxy body-size limit in front of this
# service. Not a regression from this task's fix — a pre-existing gap this
# task's review surfaced. The web API does not ship this release, so this is
# accepted for now; move this note into the "Known accepted limitations"
# section of docs/RELEASE_CHECKLIST.md once Task 24 creates that file.
@app.post("/api/reports/files")
async def upload_files(files: list[UploadFile] = File(...)):
    """Save uploads under DATA_DIR, then hand them to the async add-files path."""
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(413, f"عدد الملفات يتجاوز الحد ({MAX_UPLOAD_FILES})")
    # %f: two uploads in the same second used to collide into one directory
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
                    chunk = await f.read(1 << 20)   # stream, never whole-file
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            413,
                            f"حجم الملف يتجاوز الحد ({MAX_UPLOAD_BYTES // (1024 * 1024)} ميغابايت)")
                    out.write(chunk)
        except HTTPException:
            dest.unlink(missing_ok=True)   # no partial file left behind
            raise
        except (OSError, ValueError) as e:
            # ValueError alongside OSError: open() raises ValueError (not
            # OSError) for a path containing an embedded null byte. The
            # sanitiser above strips control characters, so this is a
            # residual-defense catch, not the primary fix.
            dest.unlink(missing_ok=True)
            raise HTTPException(
                400, f"تعذّر حفظ الملف: {_safe_upload_name(f.filename)}") from e
        paths.append(str(dest))
    return {"started": service.add_files(paths), "saved": len(paths)}


# ───────────────────────── analysis / dashboard ─────────────────────────
@app.post("/api/analysis/run")
def run_analysis():
    if service.busy:
        raise HTTPException(status_code=409, detail="التحليل قيد التشغيل")
    if service.report_count == 0:
        raise HTTPException(
            status_code=400,
            detail="لا توجد تقارير للتحليل — حمّل النماذج أو أضف تقريراً")
    service.run_analysis()
    return {"started": True}


@app.get("/api/dashboard")
def get_dashboard():
    return {"chief": service.dash, "date": service.report_date,
            "has_results": bool(service.results)}


@app.delete("/api/dashboard")
def clear_dashboard():
    service.clear_dashboard()
    return {"ok": True}


# ───────────────────────── exports / recipients ─────────────────────────
_REPORTS_DIR = DATA_DIR / "reports"


@app.get("/api/exports")
def get_exports():
    return {"exports": service.exports}


@app.get("/api/exports/{name}")
def download_export(name: str):
    """Download one generated report — confined to the reports dir, pdf/xlsx only."""
    safe = Path(name).name
    if safe != name or Path(safe).suffix.lower() not in (".pdf", ".xlsx"):
        raise HTTPException(status_code=400, detail="اسم ملف غير صالح")
    path = (_REPORTS_DIR / safe).resolve()
    if path.parent != _REPORTS_DIR.resolve() or not path.exists():
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    return FileResponse(path, filename=safe)


@app.get("/api/recipients")
def get_recipients():
    return {"recipients": service.recipients}


# ───────────────────────── contacts ─────────────────────────
@app.get("/api/contacts/structure")
def contacts_structure():
    return service.contacts_structure()


@app.get("/api/contacts/employees")
def employees(dept: str = "", sub_dept: str = ""):
    return service.employees_for(dept or None, sub_dept or None)


@app.post("/api/contacts/employees", status_code=201)
def add_employee(emp: dict):
    emp_id = service.add_employee(emp)
    return {"id": emp_id}


@app.put("/api/contacts/employees/{emp_id}")
def update_employee(emp_id: int, fields: dict):
    service.update_employee(emp_id, fields)
    return {"ok": True}


@app.delete("/api/contacts/employees/{emp_id}")
def delete_employee(emp_id: int):
    service.delete_employee(emp_id)
    return {"ok": True}


@app.post("/api/contacts/sync")
def sync_contacts():
    service.sync_contacts()
    return {"ok": True}


# ───────────────────────── export / email / whatsapp ─────────────────────────
@app.post("/api/export/pdf")
def export_pdf_endpoint():
    ok, out = service.export_pdf()
    if not ok:
        raise HTTPException(status_code=400, detail=out)
    return FileResponse(out, filename=Path(out).name,
                        media_type="application/pdf")


@app.post("/api/export/excel")
def export_excel_endpoint():
    ok, out = service.export_excel()
    if not ok:
        raise HTTPException(status_code=400, detail=out)
    return FileResponse(
        out, filename=Path(out).name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/api/email/send")
def send_email():
    ok, msg = service.send_email_report()
    return {"ok": ok, "message": msg}


@app.post("/api/whatsapp/bridge")
def whatsapp_bridge():
    ok, out = service.generate_whatsapp_bridge()
    if not ok:
        raise HTTPException(status_code=500, detail=out)
    return {"path": out}


@app.get("/api/whatsapp/node")
def whatsapp_node():
    ok, msg = service.check_node()
    return {"ok": ok, "msg": msg}


@app.post("/api/whatsapp/link")
def whatsapp_link():
    """Start the Node bridge; QR matrix / link status arrive over WS (`wa_qr`/`wa_status`)."""
    return {"started": service.start_whatsapp_bridge()}


# ───────────────────────── static frontend (Phase 2) ─────────────────────────
_WEB_DIST = BUNDLE_DIR / "web" / "dist"
if (_WEB_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_WEB_DIST), html=True),
              name="web")
