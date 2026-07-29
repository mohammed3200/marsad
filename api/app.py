"""FastAPI app — REST (/api) + WebSocket (/ws) over AppService.

Local-only: binds 127.0.0.1 (see api/__main__.py). All blocking service calls
run in FastAPI's threadpool (sync `def` endpoints); long-running operations
start daemon threads inside AppService and report back over the WebSocket.
"""
import asyncio
import datetime
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.paths import BUNDLE_DIR, DATA_DIR

from .services import AppService

service = AppService()
app = FastAPI(title="marsad API", docs_url="/api/docs")


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
    return service.settings


@app.put("/api/settings")
def put_settings(values: dict):
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


@app.post("/api/reports/files")
async def upload_files(files: list[UploadFile] = File(...)):
    """Save uploads under DATA_DIR, then hand them to the async add-files path."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = DATA_DIR / "uploads" / f"api_{ts}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        name = Path(f.filename or "file").name  # strip any client-side dirs
        dest = dest_dir / name
        dest.write_bytes(await f.read())
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
