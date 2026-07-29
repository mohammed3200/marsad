# api/ — marsad web backend + web UI host

Qt-free FastAPI layer over the proven Python core (`core/`, `connectors.py`,
`backend/settings_bridge.py`). Replaces the QML shell's `AppController` with
`AppService` (`api/services.py`) — same slot semantics, same Arabic notify
strings, same guard flags, same daemon-thread model — exposed as REST + a
WebSocket event stream (`api/app.py`). The React web UI lives in `web/`
(builds to `web/dist`, served at `/`).

## Run

```bash
python -m api            # 127.0.0.1:$MARSAD_PORT (default 8765)
```

## REST surface (prefix `/api`, JSON in/out)

| Method & path | Purpose |
|---|---|
| `GET /api/meta` | `{today_label, backend, engine_online, engine_status, reports_dir}` |
| `GET /api/settings` / `PUT /api/settings` | read / merge-save settings (+ hub rebuild) |
| `POST /api/settings/test/engine` · `.../test/email` | start async test → `{started}`; result over WS |
| `POST /api/settings/models` | start async provider model-list fetch → `{started}`; result over WS as `models_fetched` |
| `GET /api/engine/profiles` | `{profiles: [{name, ai_backend}]}` |
| `POST /api/engine/profiles/save` · `.../switch` | `{name}` → `{ok}` (save snapshots ENGINE_KEYS; switch copies them live) |
| `DELETE /api/engine/profiles/{name}` | → `{ok}` |
| `GET /api/reports` | `{count, reports}` |
| `POST /api/reports` | add manual report dict (400 if no `content`) |
| `DELETE /api/reports/{index}` · `DELETE /api/reports` | remove one / clear all |
| `POST /api/reports/samples` | load bundled demo reports → `{loaded}` |
| `POST /api/reports/collect` | start async connector collection → `{started}` |
| `POST /api/reports/files` | multipart upload(s); saved under `DATA_DIR/uploads/`, parsed async → `{started, saved}` |
| `POST /api/analysis/run` | start the agent fleet → `{started}` (400 no reports, 409 busy) |
| `GET /api/dashboard` | `{chief, date, has_results}` · `DELETE` clears it |
| `GET /api/contacts/structure` · `GET /api/contacts/employees?dept=&sub_dept=` | org structure / employee list |
| `POST`/`PUT`/`DELETE /api/contacts/employees[/{id}]` | contacts CRUD |
| `POST /api/contacts/sync` | contacts → settings routing maps (+ hub rebuild) |
| `POST /api/export/pdf` · `POST /api/export/excel` | file download (400 JSON when no results) |
| `GET /api/exports` | `{exports: [{name, sizeKb, date}]}` — generated PDF/XLSX in the reports dir, newest first |
| `GET /api/exports/{name}` | download one export (basename + `.pdf`/`.xlsx` only, reports-dir confined) |
| `GET /api/recipients` | `{recipients: [...]}` — `report_recipients` or `email_dept_map` keys |
| `POST /api/email/send` | → `{ok, message}` |
| `POST /api/whatsapp/bridge` | generate Node bridge → `{path}` |
| `GET /api/whatsapp/node` | → `{ok, msg}` |
| `POST /api/whatsapp/link` | start the bridge (npm install on first run, then `node whatsapp_bridge.js`) → `{started}`; QR + link state over WS |

Interactive docs at `/api/docs`.

## WebSocket `/ws`

On connect: one `state_snapshot` event, then every `AppService` event is
broadcast to all clients (JSON, `ensure_ascii=False`). Event shapes:

- `state_snapshot` — `{dash, date, has_results, reports, reports_count, agents:[{id,name,state}], busy, engine_online, engine_status, testing:{engine,email,active}, models, models_busy, wa:{linked,phone,starting,qr}}`
- `notify` — `{message}` (Arabic user-facing string)
- `log` — `{message}`
- `progress` — `{percent}` 0..100
- `agent_state` — `{agent_id, state}` state ∈ `running|done|error`
- `reports_changed` — `{count, reports}`
- `dash_changed` — `{dash, date, has_results}`
- `analysis_done` / `analysis_failed{error}`
- `connection_tested` / `email_tested` — `{ok, message}`
- `export_done{path}` / `export_failed{error}`
- `testing` — `{engine, email, active}`
- `busy` — `{busy}` · `engine_changed{online,status}` · `settings_changed`
- `models_fetched` — `{ok, models, message}`
- `wa_qr` — `{matrix}` (rows of "0/1" chars) · `wa_status` — `{linked, phone, starting}`

## Static frontend

`web/dist` (the React app in `web/`, `npm run build`) is served at `/` when
`web/dist/index.html` exists; absence is tolerated.

Constraints: no Qt imports in this package; binds 127.0.0.1 only; engine and
network failures surface as structured errors / events, never raised to clients.
