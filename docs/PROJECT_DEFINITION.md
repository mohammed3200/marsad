# مرصد (marsad) — Complete Project Definition

> **What this document is:** the authoritative definition of the marsad project as it exists
> today — its purpose, structure, functionality, work mechanism, data flow, and contracts.
> It is framework-neutral: it describes *what the system is and does*, not what it should be
> rebuilt with. Every claim references the source file it was verified against.
>
> Audience: anyone (human or AI agent) who needs to understand, maintain, port, or rebuild
> any part of this system without reading the entire codebase first.

---

## 1. Purpose & context

**مرصد (marsad)** is an Arabic-language (RTL) project-intelligence application for LTT's
4G/5G network rollout. It solves one problem: turning scattered field reports into an
executive status brief.

1. **Ingest** field reports from five sources: email (IMAP), WhatsApp group messages, an
   ERP drop folder, direct file upload, and manual entry.
2. **Analyze** them with a fleet of 11 LLM "agents" — 10 domain workers (operations,
   quality, safety, civil works, cost, contracts, procurement, supply chain, risk, schedule)
   plus one `chief` coordinator that synthesizes an executive summary.
3. **Present** the result as an executive dashboard and export it as branded PDF, Excel,
   and HTML-email reports.

Hard context facts that shape everything else:

- **Arabic-first.** UI copy, agent prompts, and output JSON keys/values are Arabic and are
  part of the product contract. The app relies on the platform's native Arabic shaping
  (HarfBuzz/BiDi in Qt; the browser's own shaping on web) — no reshaper/bidi libraries
  on screen. The PDF exporter is the exception: reportlab shapes nothing itself, so
  `core/exporters.py` requires `arabic-reshaper` + `python-bidi`.
- **Local-first.** Everything runs on one machine: the LLM can be a local Ollama server
  (the default) or a cloud API key; the WhatsApp receiver binds to `127.0.0.1`.
  The one exception is the optional WhatsApp bridge, a Baileys client that connects out to
  WhatsApp's own servers — see README's Data & privacy section.
- **Single-user desktop app.** There is no auth, no multi-tenancy,
  no database — JSON files on disk are the store.

## 2. Architecture map

One UI-agnostic core, with **three presentation layers** around it. The rule that keeps the
system portable: **`core/` and `connectors.py` never import Qt** — any UI (Qt, web, CLI) can
sit on top.

```
┌──────────────────────────── Presentation layers ───────────────────────────┐
│  app.py + backend/ + qml/   PySide6 / Qt Quick (QML) desktop UI — production│
├──────────────────────────── UI-agnostic core ──────────────────────────────┤
│  core/engine.py      AIEngine (5 LLM backends) + AgentsEngine (11 agents)   │
│  core/exporters.py   PDF (reportlab) + Excel (openpyxl) report generation   │
│  core/contacts.py    ContactsDB — org chart + employee directory (JSON)     │
│  core/hijri.py       Gregorian→Hijri conversion, dual date label            │
│  core/errors.py      friendly_error()/friendly_fs_error() → Arabic errors   │
│  core/status.py      tier() — one status-tier table for every output        │
│  core/paths.py       BUNDLE_DIR (read-only) vs DATA_DIR (writable) split    │
│  connectors.py       Email / ERP / WhatsApp ingestion + outbound email      │
├──────────────────────────── Support ───────────────────────────────────────┤
│  backend/ (Qt bridge) · qml/ (declarative UI) · assets/fonts (bundled TTFs) │
│  tests/ (stdlib unittest) — isolated_state() keeps it off real user data    │
│  tools/ (screenshots, API smoke test, deb build) · packaging/ (deb, NSIS)   │
│  marsad.spec (PyInstaller) · .github/workflows (CI)                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Repository layout (verified against the tree)

| Path | Role |
|---|---|
| `app.py` | Qt entry point: `QApplication` (RTL) → bundled fonts → `Theme` + `AppController` context props → `QQuickView` loads `qml/Main.qml` |
| `core/` | UI-agnostic logic. **No Qt imports allowed** |
| `connectors.py` | All ingestion + outbound email (also UI-agnostic) |
| `backend/` | Qt bridge: `theme.py` (design tokens), `controller.py` (`AppController` — the object QML talks to), `analysis_worker.py` (QThread), `models.py` (list models), `settings_bridge.py` (settings load/save) |
| `qml/` | Flat QML tree: `Main.qml` shell + 6 pages + flat primitives; files auto-import each other by filename |
| `tests/` | Unit + integration test suite (stdlib `unittest`, no extra dependency). `_isolation.py::isolated_state()` redirects every writable-state module global into a temp dir — every test file uses it so the suite never touches the real `settings.json`, `reports/`, or `data/` |
| `assets/fonts/` | Bundled Noto Kufi Arabic / Noto Sans Arabic / JetBrains Mono (OFL) |
| `assets/marsad.png`, `marsad.ico` | Brand mark |
| `data/contacts.json` | Authoritative org chart + employee directory (gitignored) |
| `reports/` | Analysis output: `results_<ts>.json`, `latest.json`, exported PDF/XLSX (gitignored) |
| `uploads/`, `logs/` | Runtime output (gitignored) |
| `settings.json` / `settings.example.json` | Live config (gitignored) / shipped template |
| `whatsapp_bridge.js` + `package.json` | **Generated** Node bridge (gitignored) + its npm manifest |
| `tools/` | `capture_qt.py` (offscreen QML screenshots), `capture_wa_dialog.py`, `build_linux.sh` |
| `packaging/linux`, `packaging/windows` | `.deb` build script + `.desktop` file; NSIS installer script (CI-only) |
| `docs/screenshots/` | Captured UI screenshots |

## 3. Functionality inventory

The product surface is six pages plus background services. (QML page names given; the API
exposes the same capabilities over REST — see §7.)

### 3.1 إدخال البيانات (Data input) — `qml/InputPage.qml`
- Upload files (`.xlsx/.csv/.json/.txt/.pdf/.docx`); each parsed into a report dict.
  An unreadable file is rejected outright rather than entering the queue as an error string.
- «جمع من المصادر» — one-shot collection from email + ERP folder + buffered WhatsApp.
- Manual entry form: department combo, author, date, free-text content.
- Queue list with per-row delete and «مسح الكل»; live count «{n} تقرير في القائمة».

### 3.2 التحليل والوكلاء (Analysis & agents) — `qml/AnalysisPage.qml`
- «بدء التحليل» runs the whole agent fleet on the queued reports (blocked while busy or
  when the queue is empty).
- Live progress bar (0–100%), per-agent state list (11 agents:
  قيد التشغيل/تم/خطأ/بالانتظار), and a scrolling run log (capped at 200 lines).

### 3.3 لوحة التحكم (Dashboard) — `qml/DashboardPage.qml`
- Empty state: 3-step quick start (configure engine → add reports → run analysis).
- With results: overall-health word + status dot, KPI grid, executive summary, numbered
  immediate action plan (owner · deadline · impact), «مسح اللوحة» to clear.

### 3.4 التقارير (Reports) — `qml/ReportsPage.qml`
- Export the current results to PDF or Excel (saved under `DATA_DIR/reports/`).
- List of previously exported files (name, size, date) with open-file action.
- Recipient list (from settings) + «إرسال بالبريد» — sends the HTML report via SMTP.

### 3.5 الإعدادات (Settings) — `qml/SettingsPage.qml`
- Engine profiles: save/switch/delete named engine-config snapshots (default = Ollama).
- AI backend configuration for five providers: Ollama, Claude, OpenAI-compatible (editable
  base URL covers OpenRouter/Groq/Together/DeepSeek/LM Studio), Gemini, Azure OpenAI;
  request timeout; per-provider model pickers with «جلب قائمة النماذج».
- «اختبار المحرّك» and «اختبار البريد» — save-then-test with inline (non-toast) results.
- Email account (IMAP/SMTP, app password), report recipients, ERP folder path.
- WhatsApp: enable toggle, receiver port, Node.js check/install, bridge-file generation,
  QR-code linking dialog (renders the QR matrix natively, shows linked phone).

### 3.6 جهات الاتصال (Contacts) — `qml/ContactsPage.qml`
- Org chart (departments → sub-departments) browsing with cascading filters.
- Employee directory: list, add, delete (fields: name, position, dept, sub_dept, email,
  whatsapp, active).
- «مزامنة مع الإعدادات» — exports email→dept and whatsapp→dept routing maps back into
  `settings.json` so the connectors route incoming reports correctly.

### 3.7 Background services
- **WhatsApp receiver** (active when `whatsapp_enabled`): stdlib HTTP server on
  `127.0.0.1:<whatsapp_port>` (default 5051), token-gated, receives messages/QR/status from
  the generated Node bridge.
- **Auto-fetch loops** (email poll every 30 min, ERP scan every 5 min) exist as
  `ConnectorHub.start_all()` (`connectors.py:769`) but are **currently never started** by
  either UI — collection is on-demand only («جمع من المصادر»).

## 4. Work mechanism

### 4.1 The analysis pipeline (`core/engine.py`)

The heart of the product. `AgentsEngine.run_all(reports, progress_cb, agent_cb)`:

1. Formats the queued report dicts into one Arabic text block (`_format_reports`,
   `core/engine.py:447`): each report becomes `[SOURCE][dept] من: from | date\ncontent`.
2. Runs the 10 worker agents **sequentially** (`WORKER_AGENTS`, `core/engine.py:359`). Each
   worker call is `AIEngine.ask(system_prompt, reports_text)` where the system prompt is the
   agent's Arabic role description + "أجب بـ JSON فقط" + its JSON schema (`run_agent`,
   `core/engine.py:386`). Before/after each agent it fires `agent_cb(agent_id, state)` with
   `state ∈ running|done|error`, and `progress_cb(percent)` — this is what drives the live
   telemetry in both UIs.
3. Runs the `chief` coordinator (`core/engine.py:422-438`). The chief receives the formatted
   reports **plus only the successful worker outputs** (`clean = {k:v for k,v in results if
   "error" not in v}`) — worker errors are never forwarded.
4. `_ensure_chief_schema()` (`core/engine.py:362`) **guarantees** the chief dict always has
   `overall_health / executive_summary / kpis / top_actions / dept_scores / achievements`,
   even on LLM failure — the dashboard and exporters can never break on a missing key.
5. Persists: `reports/results_<YYYYMMDD_HHMMSS>.json` + `reports/latest.json`
   (`_save`, `core/engine.py:459`). `latest.json` is what repopulates the dashboard on the
   next app start.

### 4.2 AIEngine — the five LLM backends (`core/engine.py:23`)

`AIEngine.ask()` dispatches on `settings["ai_backend"]` to `_ask_ollama` (default),
`_ask_claude`, `_ask_openai` (OpenAI-compatible — also covers Azure via `_ask_azure` URL
shape), `_ask_gemini`. All HTTP is stdlib `urllib` through `_http_json()` / `_http_get_json()`
(`core/engine.py:45,74`), which **never raise** — every failure returns `{"error": …}`.
Raw HTTP bodies and exception strings are mapped to short actionable Arabic by
`core/errors.py::friendly_error()` (auth failures → "فشل تسجيل الدخول…", 429/quota →
"تجاوزت حصة المزوّد…", timeouts, DNS, SSL, etc.); Arabic input passes through untouched.
Request timeout is `ai_timeout` (default 180s). `test_connection()` asks the model to echo
a fixed JSON; `list_models()` queries the provider's model list (Ollama `/api/tags`,
OpenAI `/models`) for the Settings pickers.

### 4.3 Ingestion pipeline (`connectors.py`)

Every source normalizes into the same **report dict** and lands in one queue:

- **`EmailConnector`** (`connectors.py:53`): IMAP over SSL, fetches `UNSEEN` messages,
  decodes sender/subject, extracts plain-text body + supported attachments, routes the
  department by sender address via `email_dept_map` (`_find_dept`), marks messages `\Seen`.
  Also sends outbound reports: SMTP STARTTLS, `MIMEMultipart` with the HTML report +
  attachments (`send_report`, `connectors.py:131`). `test_connection()` = IMAP login probe.
  A dormant auto-fetch loop exists (`start_auto_fetch`, wired in `ConnectorHub.start_all`
  but never started by either UI — collection is on-demand).
- **`ERPConnector`** (`connectors.py:650`): scans `erp_folder` for `DOC_PATTERNS`
  (`*.xlsx *.xls *.csv *.json *.txt *.pdf *.docx`) and turns each new file into a report via
  the shared `read_file_to_report()`.
- **File parsing** (`connectors.py:549-648`): `_read_excel` (openpyxl), `_read_csv`,
  `_read_json`, `_read_pdf` (PyPDF2), `_read_docx` (python-docx) — each degrades to an
  Arabic placeholder string when its library is missing. `guess_dept()` infers the
  department from the filename. **`is_internal_file()`** (`connectors.py:498`) refuses
  app-internal files (`settings.json`, `settings.example.json`, `sample_reports.json`,
  `whatsapp_bridge.js`, `data/contacts.json`, `reports/*.json`) on *every* path (upload
  picker, ERP watch, API upload) so config/credentials never enter the report queue.
- **`WhatsAppReceiver`** (`connectors.py:401`): stdlib `http.server` on `127.0.0.1`, three
  token-gated POST paths: `/wa_message` (→ report dict via `whatsapp_groups` routing),
  `/wa_qr` and `/wa_status` (→ forwarded to the UI through `set_event_handler`).
- **`ConnectorHub`** (`connectors.py:715`): the facade. `collect_all()` = immediate email
  fetch + ERP scan + drain of the WhatsApp/auto-fetch buffer. It owns the per-install
  `whatsapp_token` (generated once, persisted into `settings.json` so a previously generated
  bridge keeps working across hub rebuilds, `connectors.py:736-739`).
- **WhatsApp bridge** (`WhatsAppHelper`, `connectors.py:243`): generates
  `whatsapp_bridge.js` — a Baileys (WhatsApp Web) Node script that POSTs incoming group
  messages, the QR string, and link state to the receiver with the `X-WA-Token` header.
  The app can also prepare packages (`npm install`) and spawn the bridge process itself.

### 4.4 Threading & event model

Both UIs follow the same rule: **no blocking I/O on the UI/main thread.**

- Guard flags: `_busy` (analysis), `_testing_engine`, `_testing_email`, `_collecting`,
  `_adding`. A second trigger while a flag is set is refused.
- Long-running work runs on daemon threads (or a `QThread` for `AnalysisWorker` in the Qt
  app) and reports back asynchronously.
- **Qt app**: results cross back as Qt signals (`notify`, `progress`, `logMessage`,
  `agentState`, `dashModelChanged`, …) which are thread-safe queued deliveries
  (`backend/controller.py`).

### 4.5 Settings lifecycle

- `backend/settings_bridge.py`: `load_settings()` merges `settings.json` →
  `settings.example.json` → built-in `_DEFAULTS` (first existing file wins); `save_settings()`
  writes the merged dict back to `DATA_DIR/settings.json`.
- **Connectors snapshot settings at construction.** Therefore both UIs rebuild the
  `ConnectorHub` on every save (`saveSettings`) so new credentials
  take effect immediately; the WhatsApp receiver restarts only if enabled.
- **Engine profiles**: named snapshots of the 15 engine keys (`ENGINE_KEYS` —
  `backend/controller.py:27`): `ai_backend, ai_timeout, ollama_url, ollama_model,
  claude_api_key, claude_model, openai_api_key, openai_base_url, openai_model,
  gemini_api_key, gemini_model, azure_endpoint, azure_api_key, azure_deployment,
  azure_api_version`. Switching copies the profile's keys into the flat live settings and
  saves; the default profile is Ollama.
- After any settings save, the cached provider model list is invalidated (it belonged to
  the previous provider config).

### 4.6 Contacts ↔ settings sync

`ContactsDB` (`core/contacts.py`) owns the org chart and employees in
`data/contacts.json`. `export_to_config()` (`core/contacts.py:174`) walks **active**
employees and builds the two routing maps the connectors consume:
`email_dept_map {email → dept-key}` and `whatsapp_groups {whatsapp → dept-key}`, mapping
Arabic sub-department names to engine dept keys via `DEPT_KEY_MAP`. Sync writes them into
`settings.json` and rebuilds the hub.

## 5. Data flow

### 5.1 Main pipeline (the one-directional rule)

```
Sources                          Queue                 Analysis                Consumers
─────────                        ─────                 ────────                ─────────
Email (IMAP UNSEEN)          ┌───────────────┐    ┌──────────────────┐     ┌─────────────────┐
ERP folder scan              │ report dicts  │    │ AgentsEngine     │     │ Dashboard (UI)  │
WhatsApp bridge POST    ───► │ (in-memory    ───►│ 10 workers ──────┼────►│ export_pdf      │
File upload (picker/API)     │  list, UI/     │    │  chief           │     │ export_excel    │
Manual entry                 │  service-owned)│   │ results dict     │     │ build_report_   │
                            └───────────────┘    └──────┬───────────┘     │  html → SMTP    │
                                                         │                 └─────────────────┘
                                                         ▼
                                          reports/results_<ts>.json
                                          reports/latest.json ──► reload on startup
```

The `results` dict (keyed by agent id) is **the single contract** every consumer reads:
the dashboard model, the PDF/Excel exporters, and the HTML email builder. Nothing else
flows backward.

### 5.2 Settings flow

`settings.json` ⇄ Settings page (load/save) → save triggers hub rebuild + model-list
invalidation → connectors + engine read the new values on next use. Engine profiles are a
named-copy layer on top of the flat keys.

### 5.3 Contacts flow

`data/contacts.json` ⇄ Contacts page (CRUD) → «مزامنة مع الإعدادات» →
`export_to_config()` → `settings.json` (`email_dept_map`, `whatsapp_groups`) → hub rebuild
→ connectors route new reports by sender/group.

### 5.4 WhatsApp flow

WhatsApp Web (phone) ⇄ Baileys bridge (`node whatsapp_bridge.js`, generated with the
current port+token) → POST `/wa_message|/wa_qr|/wa_status` with `X-WA-Token` → receiver →
messages become report dicts in the buffer; QR/status events reach the UI (Qt signal or WS
`wa_qr`/`wa_status`), where the QR string is rendered as a "0/1" matrix (via the `qrcode`
package) drawn with rectangles — no image files.

## 6. Data contracts (verbatim)

### 6.1 Report dict (the queue item)

Produced by every ingestion path (`EmailConnector.fetch_new`, `read_file_to_report`,
WhatsApp receiver, manual entry). Example from `sample_reports.json`:

```json
{
  "id": "r1", "source": "email", "dept": "ran",
  "from": "م. أحمد الورفلي — فريق RAN",
  "date": "2026-05-15",
  "content": "اكتملت عملية تركيب 14 برجاً من أصل 23 في منطقة سرت. ..."
}
```

- `source` is a free-form label: `email` (IMAP), `whatsapp` (receiver), `erp` (folder
  scan), `ملف` (uploads), `system` (some samples), or an Arabic label from the manual-entry
  combo (`يدوي / بريد إلكتروني / واتساب / ERP`); it is only uppercased when formatting the
  agent input. Email reports also carry `subject`.
- `content` is the only required field for manual entry (the API 400s with
  «أدخل نص التقرير أولاً» when empty).

### 6.2 The `results` dict (agent output contract)

`results[<agent_id>]` for the 10 workers + `results["chief"]`. Schemas are embedded in the
Arabic prompts (`AGENT_PROMPTS`, `core/engine.py:312-357`) — the LLM is instructed to answer
with exactly these shapes:

| Agent | Arabic role | JSON schema |
|---|---|---|
| `ops` | العمليات الميدانية | `{completion_pct, active_sites, issues[], team_status, recommendations[]}` |
| `quality` | الجودة والامتثال | `{inspected, passed, failed, pass_rate, issues[], recommendations[]}` |
| `safety` | السلامة المهنية | `{incidents, near_misses, safety_score, violations[], corrective_actions[], status:"آمن"}` |
| `civil` | الأعمال الإنشائية | `{towers_built, towers_total, civil_pct, pending_permits, issues[], materials_status}` |
| `cost` | التكاليف والميزانية | `{total_budget, spent, remaining, spent_pct, deviation_pct, forecast, alerts[]}` |
| `contract` | العقود والقانونية | `{active_contracts, total_value, pending_payments, claims[], expiring_soon[]}` |
| `procure` | المشتريات والموردين | `{pending_orders, approved_vendors, total_po_value, critical_shortages[], recommendations[]}` |
| `supply` | المخازن وسلاسل التوريد | `{warehouse_fill_pct, in_transit_shipments, delayed_shipments, critical_items[], logistics_issues[]}` |
| `risk` | إدارة المخاطر | `{risks:[{title, level:"عالية", category, description, solution, owner}]}` |
| `schedule` | الجدول الزمني | `{delay_days, original_end, new_end, phases:[{name, status, completion_pct}], critical_path[]}` |
| `chief` | التنسيق المركزي | `{overall_health, executive_summary, dept_scores:[{dept, score, status, key_issue}], top_actions:[{priority, action, owner, deadline, impact}], kpis:[{name, value, trend, status}], achievements[]}` |

**Guaranteed minimum** (`_ensure_chief_schema`): `overall_health` (default "غير محدد"),
`executive_summary` (failure-aware Arabic fallback), `kpis`, `top_actions`, `dept_scores`,
`achievements` — always present, even on total LLM failure. A failed agent's entry is
`{"error": "<arabic message>"}`.

### 6.3 Fixed vocabularies (shared across prompts, routing, and UI colors)

- **Agent ids / order**: `ops, quality, safety, civil, cost, contract, procure, supply,
  risk, schedule` + `chief` (`WORKER_AGENTS` in `core/engine.py`).
  Arabic display names are fixed (`AGENT_NAMES`, `backend/models.py`).
- **Dept keys**: `ran, core, quality, safety, civil, supply, cost, pmo, contract, procure,
  hr, risk, it, admin` (see `settings.example.json` maps and `DEPT_KEY_MAP` in
  `core/contacts.py`).
- **Status literals → colors** (`backend/theme.py:56`): `جيد/آمن/منخفضة/مكتمل` → green;
  `متوسط/تحذير/متوسطة` → amber; `حرج/خطر/عالية/متأخر` → red; `في الموعد` → info blue.
  Branching logic everywhere keys on these exact strings.

### 6.4 `settings.json` keys

Full reference (defaults in `backend/settings_bridge.py:13-48`, template in
`settings.example.json`):

- Engine: `ai_backend` (`ollama|claude|openai|gemini|azure`), `ai_timeout` (180),
  `ollama_url`, `ollama_model`, `claude_api_key`, `claude_model`, `openai_api_key`,
  `openai_base_url`, `openai_model`, `gemini_api_key`, `gemini_model`, `azure_endpoint`,
  `azure_api_key`, `azure_deployment`, `azure_api_version`.
- Email/ERP: `email_user`, `email_password` (app password), `imap_host`, `smtp_host`,
  `smtp_port` (587), `report_recipients[]`, `erp_folder`.
- WhatsApp: `whatsapp_enabled` (false), `whatsapp_port` (5051), `whatsapp_token`
  (auto-generated per install, persisted).
- Routing: `email_dept_map {email → dept-key}`, `whatsapp_groups {group-id → dept-key}`.
- `engine_profiles[]`: `[{name, <ENGINE_KEYS…>}]`.

### 6.5 `data/contacts.json`

```json
{
  "structure": { "<dept name>": { "color": "#…", "subs": { "<sub-dept name>": [] } } },
  "employees": [ { "id": 1, "name": "…", "position": "…", "dept": "…",
                   "sub_dept": "…", "email": "…", "whatsapp": "…", "active": true } ]
}
```

Seed structure: three top departments (الإدارة الفنية / التشغيلية، الإدارة المالية،
الإدارة الإدارية) with their sub-departments (`data/contacts.json`).

## 7. External integrations

| Integration | How | Where |
|---|---|---|
| **Ollama** (default) | `POST <ollama_url>/api/generate` (127.0.0.1:11434, stream=false), `GET /api/tags` | `core/engine.py:171` |
| **Claude** | `POST https://api.anthropic.com/v1/messages`, `x-api-key` + `anthropic-version: 2023-06-01` | `core/engine.py:203` |
| **OpenAI-compatible** | `POST <openai_base_url>/chat/completions` (Bearer); `response_format` JSON with 400-retry fallback | `core/engine.py:257` |
| **Azure OpenAI** | `POST <endpoint>/openai/deployments/<deployment>/chat/completions?api-version=…`, `api-key` header | `core/engine.py:267` |
| **Gemini** | `POST generativelanguage.googleapis.com/v1beta/models/<model>:generateContent?key=…` | `core/engine.py:278` |
| **Email** | IMAP4_SSL (fetch UNSEEN, mark \Seen) + SMTP STARTTLS (send) | `connectors.py:53` |
| **ERP** | Folder scan for `DOC_PATTERNS` | `connectors.py:650` |
| **WhatsApp** | Generated Baileys Node bridge ↔ loopback token-gated POSTs | `connectors.py:243,401` |
| **File formats** | openpyxl (xlsx), PyPDF2 (pdf), python-docx (docx) — optional, degrade gracefully | `connectors.py:549-607` |
| **Node.js** | Required only for the WhatsApp bridge (`npm install`, `node whatsapp_bridge.js`) | `connectors.py:243` |

## 8. Storage & paths (`core/paths.py`)

Two roots, split so an installed app never writes next to its executable:

- **`BUNDLE_DIR`** — read-only bundled assets (qml, fonts, seeds). `sys._MEIPASS` when
  frozen (PyInstaller), else the repo root.
- **`DATA_DIR`** — writable per-user state. When frozen: `%APPDATA%/marsad` (Windows),
  `~/Library/Application Support/marsad` (macOS), `$XDG_DATA_HOME/marsad` or
  `~/.local/share/marsad` (Linux). When run from source: the repo root.

Everything mutable lives under `DATA_DIR`: `settings.json`, `reports/` (results, latest,
exports), `data/contacts.json`, `logs/`, `uploads/`, `whatsapp_bridge.js`, `wa_session/`.
`seed()` copies bundled defaults into `DATA_DIR` on first run. All of these are gitignored —
only blank templates ship in git.

## 9. Security model

- **Loopback only**: the WhatsApp receiver binds `127.0.0.1` —
  nothing is exposed to the LAN. That covers *inbound* only. Outbound, the app reaches
  the configured LLM provider, the configured mail server, and — once the user starts the
  WhatsApp bridge — WhatsApp's own servers, since the bridge is a Baileys WhatsApp Web
  client. See README's Data & privacy section.
- **WhatsApp token**: per-install `whatsapp_token` (`secrets.token_hex(16)`), required as
  the `X-WA-Token` header on all three receiver paths; injected into the generated bridge.
- **Credential hygiene**: `settings.json` (API keys, email app password, WA token),
  `data/contacts.json` (personal data), `whatsapp_bridge.js` + `wa_session/` (live session),
  and `reports/ logs/ uploads/` are gitignored and must never be committed; only
  `settings.example.json` (blank) ships.
- **Internal-file guard**: `is_internal_file()` keeps config/credential files out of the
  report queue on every ingestion path.
- **Export download confinement**: `AppController.openFile` validates basename + extension and
  resolves inside the reports dir (no traversal); the Qt `openFile` is likewise confined.
- **Error hygiene**: raw provider HTTP bodies / exception strings never reach the UI —
  they are classified into short Arabic by `friendly_error()`; raw detail goes to `logs/`.
- **API keys** are sent only to their configured provider endpoint; `openai_base_url` is
  user-editable (no hardcoded host).

## 10. Design system (`backend/theme.py`)

**"Light Executive Report"** — white paper, near-black ink, one deep telecom teal-green
accent (`#0E6E60`) used sparingly. No cards: structure comes from hairline rules and
generous whitespace. Color is rationed — status shows as a small dot or a single word.

- **Colors**: bg/panel `#FFFFFF`, fill `#F4F6F8`, border `#E4E8EC`, borderHi `#CFD6DD`,
  ink `#141A22`, ink2 `#5A6675`, ink3 `#8A94A1`, accent `#0E6E60` (+Lo/Bg/Soft variants),
  status green `#1E7A52`, amber `#946200`, red `#B4232A`, info `#1F5F8B`.
- **Type**: Noto Kufi Arabic (display), Noto Sans Arabic (body), JetBrains Mono
  (numbers/paths/dates — always LTR runs). Scale: hero 34 · display 26 · title 20 ·
  section 17 · body 14 · small 13 · caption 11.
- **RTL**: the shell mirrors globally; LTR islands (emails, paths, numbers) opt out
  explicitly. Arabic-Indic numerals (١٢٣) for ordered items.
- **No Unicode symbol glyphs in UI** — the bundled fonts carry none; markers/icons are
  drawn shapes (`Glyph.qml`: bars, diamond, grid, square, dial, trigram).
- **UX patterns**: transient toast for `notify` messages; test results appear inline next
  to their button (never duplicated as toasts); empty states guide the next action.

## 11. Invariants for any future rebuild

A new UI or framework must preserve these, or the system breaks:

1. **Arabic strings verbatim** — UI copy, agent prompts, and output literals are contracts.
2. **The `results` dict shape** (§6.2) — change an agent's output schema and you must update
   `core/exporters.py`, `connectors.build_report_html`, and every UI that reads it.
3. **Fixed status literals** (§6.3) drive color and branching everywhere.
4. **Dept-key vocabulary** is shared across prompts, settings maps, connector routing, and
   `DEPT_KEY_MAP` — keep them consistent when adding a department.
5. **`core/` and `connectors.py` stay UI-agnostic** — no Qt (or any UI toolkit) imports.
6. **Never raise from network paths** — degrade to `{"error": …}` / Arabic placeholders;
   the dashboard must survive any backend being offline.
7. **Threading rules** — no blocking I/O on the UI thread; guard flags; results cross
   threads only via signals/events.
8. **Write only under `DATA_DIR`**; keep the loopback + token-gated receivers; keep the
   internal-file guard; never commit secrets.
9. **`_ensure_chief_schema` semantics** — consumers may assume the six chief keys exist.

## 12. Current state summary

| Component | State |
|---|---|
| `core/` + `connectors.py` | Complete, production-proven |
| Qt/QML desktop app (`app.py` + `backend/` + `qml/`) | Complete — the production UI |
| Web frontend | **Does not exist.** A React web UI was considered and dropped; no `web/` directory has ever existed in this repository |
| Tests | `python3 -m unittest discover -s tests -v` — 112 tests, stdlib `unittest`, isolated from real user data by `tests/_isolation.py`. Plus `python3 tools/test_api.py` (7) and `tools/capture_qt.py` for QML screenshots. No linter; CI does not yet run the suite |
| Packaging | PyInstaller specs (desktop `marsad.spec`, API `marsad_api.spec`), Linux `.deb`, Windows NSIS (CI on `v*` tags) |
| LLM backends | 5 implemented; runtime requires a reachable provider (local Ollama by default) |

---

*Verified against the codebase on 2026-07-23. When the code changes, update this document
in the same commit.*
