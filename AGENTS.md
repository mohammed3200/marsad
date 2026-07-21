# AGENTS.md

Guidance for AI coding agents working in this repository. Assumes no prior knowledge of the project.

## Project overview

**مرصد (marsad)** — an Arabic-language (RTL) **Qt Quick / QML** desktop application (PySide6, Python 3.10+) for construction/telecom project management (LTT 4G/5G rollout). It ingests field reports from email (IMAP), WhatsApp, an ERP folder, file upload, or manual entry; runs them through a fleet of 11 LLM "agents" (10 domain workers + 1 `chief` coordinator); and produces an executive dashboard plus branded PDF / Excel / HTML reports.

Key facts that shape every change:

- UI text, agent prompts, and output JSON keys/values are **all in Arabic — preserve Arabic strings verbatim when editing**. Qt shapes and orders Arabic natively (HarfBuzz + BiDi); no reshaper/bidi libraries are used.
- Data flows one direction: **connectors → AgentsEngine → `results` dict → exporters/UI**. The `results` dict (keyed by agent id: `chief`, `risk`, `cost`, `schedule`, …) is the single contract every layer reads. Changing an agent's output schema means updating its consumers (`core/exporters.py`, `connectors.build_report_html`, and the QML that reads it) too.
- Design language: **Light Executive Report** — white paper, near-black ink, one deep teal-green accent (`#0E6E60`), no cards, structure by hairline rules, right-hand RTL sidebar nav. Colour is rationed: status shows as a small dot, never a wall of tint. Keep it calm.

## Build and run commands

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt                      # PySide6, reportlab, openpyxl, PyPDF2, python-docx
cp settings.example.json settings.json               # then edit it (or configure via the UI)
python app.py
```

Requires a running LLM backend — a local **Ollama** server (`ollama pull llama3.2`, default) or an API key for Claude / OpenAI-compatible / Gemini / Azure OpenAI. All providers and all data sources (email, ERP folder, WhatsApp) are configured from the **الإعدادات (Settings)** tab in the app — no hand-editing of `settings.json` is needed at runtime.

**No test suite and no linter exist in this project.** Verification is manual: run the app (`python app.py`) or render pages offscreen with the screenshot harness (below). There is no CI test job — CI only builds installers.

### Build installers

```bash
pip install -r requirements.txt pyinstaller
pyinstaller marsad.spec                        # → dist/marsad/  (onedir)
MARSAD_ONEFILE=1 pyinstaller marsad.spec       # → portable single-file exe
bash tools/build_linux.sh 1.0.0                # → dist/marsad/ + dist/marsad_1.0.0_amd64.deb (needs dpkg-deb)
```

Windows installers (`packaging/windows/marsad.nsi`, NSIS) are built only in CI.

### Screenshot harness

```bash
QT_QPA_PLATFORM=offscreen python tools/capture_qt.py [out_dir]
```

Renders each page to a PNG using the real `AppController` (dashboard shows whatever is in `reports/latest.json`). Useful for visual verification of QML changes.

## Architecture

```
app.py                 Qt entry — QApplication (RTL) → bundled fonts → Theme + app context props → QQuickView loads qml/Main.qml
core/                  UI-agnostic logic (no Qt import allowed)
connectors.py          Email / ERP / WhatsApp ingestion + outbound email
backend/               Qt bridge — theme, controller, worker, models, settings
qml/                   Flat QML tree — Main + 6 pages + flat primitives
assets/fonts/          Bundled Noto Kufi Arabic / Noto Sans Arabic / JetBrains Mono (OFL)
tools/                 capture_qt.py (screenshots) · build_linux.sh
packaging/             linux/build_deb.sh + marsad.desktop · windows/marsad.nsi
```

### `core/` — UI-agnostic logic (must not import Qt)

- `engine.py` — `AIEngine.ask()` dispatches to five backends (`ai_backend` ∈ `ollama`·`claude`·`openai`·`gemini`·`azure`; `openai` is an OpenAI-compatible adapter — the editable `openai_base_url` covers OpenRouter/Groq/Together/DeepSeek/LM Studio). All HTTP goes through stdlib `urllib` via `_http_json()`, which **never raises** — failures return `{"error": …}`. `AGENT_PROMPTS` (11 agents), `WORKER_AGENTS` (10 domain agents: ops, quality, safety, civil, cost, contract, procure, supply, risk, schedule), `AgentsEngine.run_all(reports, progress_cb, agent_cb)`. Only **successful** worker outputs feed the `chief` coordinator. Results are saved to `reports/results_<ts>.json` + `reports/latest.json`. `_ensure_chief_schema()` guarantees the chief dict always has `overall_health`/`executive_summary`/`kpis`/`top_actions`/`dept_scores`/`achievements` even on LLM failure, so the dashboard and exporters never break. Request timeout is `ai_timeout` (settings, default 180s). `agent_cb(agent_id, state)` with state ∈ {running, done, error} drives live UI telemetry.
- `contacts.py` — `ContactsDB` (JSON org chart in `data/contacts.json`) + `export_to_config()` (email→dept / whatsapp→dept maps the connectors route on).
- `hijri.py` — self-contained Gregorian→Hijri conversion (no dependency); `dual_label()` produces the dual Hijri · Gregorian date shown in the sidebar.
- `exporters.py` — `export_pdf(results, path)` (reportlab, RTL) + `export_excel(results, path)` (openpyxl).
- `paths.py` — **frozen-paths split:** `BUNDLE_DIR` (read-only bundled assets) vs `DATA_DIR` (writable per-user state: `%APPDATA%/marsad`, `~/.local/share/marsad`). All mutable state (settings, reports, contacts, logs) goes under `DATA_DIR`; **never write next to the executable**. When run from source both are the repo root.

### `connectors.py` — ingestion + outbound email

`EmailConnector` (IMAP/SMTP), `ERPConnector` (folder watch), `WhatsAppHelper` (generates the Baileys bridge JS), `WhatsAppReceiver` (stdlib `http.server` on `127.0.0.1:<whatsapp_port>/wa_message` — the Node bridge POSTs here), `ConnectorHub` (`collect_all()` facade + `start_whatsapp(port)`), `build_report_html()`. Module-level `read_file_to_report(path, source, dept, from_label)` + `guess_dept()` + `DOC_PATTERNS` turn one file into a report dict — used by both the ERP watcher and the input-page upload button. Supported: `.xlsx/.xls/.csv/.json/.txt/.pdf/.docx` (Excel needs openpyxl, PDF needs PyPDF2, Word needs python-docx — each degrades to an Arabic placeholder string if its lib is missing). **Connectors snapshot settings at construction** — the controller rebuilds the `ConnectorHub` on `saveSettings`.

### `backend/` — the Qt/QML bridge

- `theme.py` — `Theme(QObject)`: design tokens as `colors`/`fonts`/`fs` QVariantMaps (`fs` = the Arabic type scale: hero/display/title/section/body/small/caption px) + `statusColor(literal)` mapping the fixed Arabic status words to colours. Exposed to QML as the `Theme` context property.
- `controller.py` — `AppController(QObject)`: the single object QML talks to (context property `app`). Owns settings, `ContactsDB`, `ConnectorHub`, `AIEngine`/`AgentsEngine`. Exposes notifying properties (`dashModel`, `reportDate`, `engineOnline/Status`, `busy`, `testing`/`testingEngine`/`testingEmail`, `settings`, `agentCount`, `agentsModel`, `reportsModel`, `reportCount`) and slots (`runAnalysis`, `loadSamples`, `collectReports`, `addReport`, `addFiles`, `clearDashboard`, `pickReportFiles`/`pickErpFolder`, `goTo`, `exportPdf/Excel`, `sendEmailReport`, `testConnection`, `testEmail`, `generateWhatsAppBridge`, `checkNode`, `saveSettings`, contacts CRUD + `syncContacts`). **Blocking calls run off the GUI thread:** `testConnection`/`testEmail`/`collectReports` spawn daemon threads (guarded by `_testing_engine`/`_testing_email`/`_collecting` flags) and cross results back via signals — never call IMAP/HTTP synchronously from a slot. File/folder pickers use native `QFileDialog` (the app uses `QApplication`) — do **not** use the fragile `QtQuick.Dialogs` QML module.
- `analysis_worker.py` — `AnalysisWorker` on a `QThread`; wraps `run_all`, re-emits agent/progress/log as signals. The worker never touches QML.
- `models.py` — `AgentsModel` (11 agents + live state) and `ReportsModel` (`QAbstractListModel`s).
- `settings_bridge.py` — load/save `settings.json`.

### `qml/` — flat directory (files auto-import each other by filename)

`Main.qml` (sidebar shell + `StackLayout` + a transient toast bound to `app.notify`), six pages (`DashboardPage`, `InputPage`, `AnalysisPage`, `ReportsPage`, `SettingsPage`, `ContactsPage`), and flat primitives (`ReportSection`, `MetricRow`, `ListRow`, `FormField`, `FormCombo`, `AppButton`, `EmptyState`, `PageFrame`, `Glyph`). Navigation switches pages via `app.goTo(index)` + the `navRequested` signal. All font sizes come from `Theme.fs` — no hardcoded `pixelSize`.

## Configuration & data files

- `settings.json` — backend/provider keys + `email_dept_map` / `whatsapp_groups`. **Gitignored** (holds real credentials); `settings.example.json` ships as the template.
- `data/contacts.json` — org structure + employees (authoritative; gitignored). Contacts entered in the app sync email/WhatsApp → department routing back into `settings.json` via the **مزامنة مع الإعدادات** button.
- `reports/latest.json` — most recent analysis, loaded on startup to repopulate the dashboard. `reports/`, `logs/`, `uploads/` are gitignored runtime output.
- `sample_reports.json` — demo input loaded via «تحميل نماذج».
- `whatsapp_bridge.js` — **generated** by the app (gitignored, holds a live session); the Node bridge requires `npm install && node whatsapp_bridge.js`.

## Code style and conventions

- **Preserve Arabic strings verbatim** — UI copy, agent prompts, and output literals are part of the contract.
- **Department id vocabulary is shared** across `AGENT_PROMPTS`, `WORKER_AGENTS`, `settings.json` maps, connector `_find_dept`/`_guess_dept`, and `DEPT_KEY_MAP` — keep them consistent when adding a department.
- **Fixed Arabic status literals drive colour and branching:** health `جيد`/`متوسط` (else danger), risk `عالية`/`متوسطة`/`منخفضة`, status `مكتمل`/`متأخر`, safety `آمن`/`خطر`, `تحذير`. `Theme.statusColor` and the exporters branch on these exact strings.
- **QML delegate gotcha:** model roles named like an `Item`/component property (`state`, `content`) are shadowed — qualify them as `model.state` / `model.content`.
- **Reactivity:** bind QML to notifying properties (e.g. `app.reportCount`), not one-shot method calls like `model.rowCount()`, or the UI won't refresh.
- **Threading:** long-running work runs on a `QThread` worker or a daemon thread (`testConnection`/`testEmail`/`collectReports`); all UI updates cross back via signals.
- **No Unicode symbol glyphs in the UI** — the bundled fonts contain none (they render as tofu or random fallbacks on minimal systems). Use `Glyph.qml` shapes for markers/icons.
- `core/` must stay UI-agnostic (no Qt imports).
- Network calls must degrade gracefully (return `{"error": …}`, never raise) — the UI and dashboard must survive any backend being offline.

## Testing instructions

There is **no automated test suite**. Verify changes by:

1. `python app.py` — app launches with no QML errors printed to stderr (QML load errors are printed explicitly by `app.py`).
2. For QML changes: `QT_QPA_PLATFORM=offscreen python tools/capture_qt.py` and inspect the PNGs.
3. For engine/connector changes: exercise the flow via «تحميل نماذج» (load samples) + «تشغيل التحليل» (run analysis) with a live LLM backend, or use «اختبار المحرّك» / «اختبار البريد» in Settings to test the engine and email independently.
4. For packaging changes: `pyinstaller marsad.spec` then run `dist/marsad/marsad`.

## Deployment / release process

- `.github/workflows/build.yml` (needs `permissions: contents: write`) triggers on a `v*` tag push (or `workflow_dispatch`): builds the Windows NSIS installer + portable `.exe` and the Linux `.deb`, and attaches them to the GitHub release.
- `packaging/linux/build_deb.sh <version>` produces `dist/marsad_<version>_amd64.deb`; `packaging/windows/marsad.nsi` is the NSIS script (run only in CI).
- `marsad.spec` bundles `qml/` + `assets/` + seed configs and trims `collect_all('PySide6')` with an exclude filter (drops WebEngine/Quick3D/Charts/Multimedia/…), taking the bundle from ~880 MB to ~200 MB. If you add a dependency, add it to the spec's `hiddenimports`/`collect_submodules` loop.

## Security considerations

- `settings.json` (API keys, email passwords), `data/contacts.json` (personal contact data), `whatsapp_bridge.js` + `wa_session/` (live WhatsApp session), and `reports/`/`logs/`/`uploads/` are **gitignored — never commit them**. Only `settings.example.json` (blank credentials) ships.
- An installed app must only write under `DATA_DIR` (per-user), never next to the executable (`Program Files`, `/opt`) — see `core/paths.py`.
- The WhatsApp receiver binds to `127.0.0.1` only and requires the per-session `X-WA-Token` header (generated by `ConnectorHub`, injected into the bridge JS by `save_bridge_file`); keep it loopback and token-gated.
- LLM API keys are sent only to the configured provider endpoint; the OpenAI-compatible adapter's `openai_base_url` is user-editable, so don't hardcode a host.
