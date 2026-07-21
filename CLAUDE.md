# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**مرصد (marsad)** — an Arabic-language (RTL) **Qt Quick / QML** desktop app (PySide6) for
construction/telecom project management (LTT 4G/5G rollout). It ingests field reports from multiple
sources, runs them through a fleet of LLM "agents," and produces an executive dashboard plus branded
PDF/Excel/HTML reports. UI text, agent prompts, and output JSON keys/values are all in Arabic —
**preserve Arabic strings verbatim when editing**. Qt shapes/orders Arabic natively (HarfBuzz + BiDi),
so no reshaper/bidi libraries are used.

Design language: **Light Executive Report** — white paper, near-black ink, one deep teal-green accent
(`#0E6E60`), no cards, structure by hairline rules, right-hand RTL sidebar nav. Colour is rationed:
status shows as a small dot, never a wall of tint. Keep it calm.

## Running

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt                      # PySide6, reportlab, openpyxl, PyPDF2, python-docx
python app.py
```

Requires an LLM backend — `ai_backend` in `settings.json` picks one of five: **ollama** (default;
`ollama_url`/`ollama_model`), **claude** (`claude_api_key`/`claude_model`), **openai**
(`openai_api_key`/`openai_base_url`/`openai_model` — OpenAI-compatible: OpenRouter/Groq/Together/
DeepSeek/LM Studio), **gemini** (`gemini_api_key`/`gemini_model`), **azure** (`azure_endpoint`/
`azure_api_key`/`azure_deployment`/`azure_api_version`). No test suite/linter.

## Architecture

Data flows one direction: **connectors → AgentsEngine → results dict → exporters/UI**. The `results`
dict (keyed by agent id: `chief`, `risk`, `cost`, `schedule`, …) is the single contract passed between
every layer. Changing an agent's output schema means updating its consumers (`core/exporters.py`,
`connectors.build_report_html`, and the QML that reads it) too.

**`core/`** — UI-agnostic logic (no Qt import):
- `engine.py` — `AIEngine.ask()` dispatches to five backends (`ai_backend` ∈ ollama·claude·openai·gemini·
  azure; `openai` is an OpenAI-compatible adapter — editable `openai_base_url` covers OpenRouter/Groq/
  Together/DeepSeek/LM Studio). `AGENT_PROMPTS` (11 agents), `WORKER_AGENTS`
  (10 domain agents), `AgentsEngine.run_all(reports, progress_cb, agent_cb)`. Runs each worker over the
  formatted report text, feeds only the **successful** worker outputs into the `chief` coordinator, saves
  `reports/results_<ts>.json` + `reports/latest.json`. `_ensure_chief_schema()` guarantees the chief dict
  always has `overall_health`/`executive_summary`/`kpis`/`top_actions`/`dept_scores`/`achievements` (even
  on LLM failure) so the dashboard + exporters never break. Request timeout is `ai_timeout` (settings,
  default 180s); `AIEngine._parse_json` strips ```json fences + extracts the first `{…}` across all backends.
  `agent_cb(agent_id, state)` with state ∈ {running, done, error} drives live UI telemetry.
- `contacts.py` — `ContactsDB` (JSON org chart in `data/contacts.json`) + `export_to_config()`
  (email→dept / whatsapp→dept maps the connectors route on).
- `hijri.py` — self-contained Gregorian→Hijri conversion (no dependency); `dual_label()` →
  «٥ صفر ١٤٤٨ هـ · 2026-07-21» (Arabic-Indic numerals + Arabic month names). Exposed as
  `app.todayLabel`.
- `exporters.py` — `export_pdf(results, path)` + `export_excel(results, path)` (reportlab/openpyxl, RTL).

**`connectors.py`** — report ingestion + outbound email: `EmailConnector` (IMAP/SMTP), `ERPConnector`
(folder watch), `WhatsAppHelper` (generates the Baileys bridge JS), `WhatsAppReceiver` (stdlib
`http.server` on `127.0.0.1:<whatsapp_port>/wa_message` — the Node bridge POSTs here with a per-session
`X-WA-Token` header; each message becomes
a `whatsapp` report), `ConnectorHub` (`collect_all()` facade + `start_whatsapp(port)`),
`build_report_html()`. Shared module-level `read_file_to_report(path, source, dept, from_label)` +
`guess_dept()` + `DOC_PATTERNS` turn one file into a report dict — used by both the ERP watcher and the
input-page upload button. Supported: `.xlsx/.xls/.csv/.json/.txt/.pdf/.docx` (Word needs `python-docx`;
Excel `openpyxl`; PDF `PyPDF2` — each degrades to an Arabic placeholder string if its lib is missing).

**`backend/`** — the Qt/QML bridge:
- `theme.py` — `Theme(QObject)`: design tokens as `colors`/`fonts`/`fs` QVariantMaps (`fs` = the Arabic
  type scale: hero/display/title/section/body/small/caption px) + `statusColor(literal)` mapping the fixed
  Arabic status words to colours. Exposed to QML as the `Theme` context property.
- `controller.py` — `AppController(QObject)`: the single object QML talks to (context property `app`).
  Owns settings, `ContactsDB`, `ConnectorHub`, `AIEngine`/`AgentsEngine`. Properties: `dashModel`,
  `reportDate`, `engineOnline/Status`, `busy`, `testing`/`testingEngine`/`testingEmail`, `agentCount`,
  `settings` (notifying — `settingsChanged`),
  `agentsModel`, `reportsModel`, `reportCount`. Slots:
  `runAnalysis`, `loadSamples`, `collectReports`, `addReport`, `addFiles` (upload picked files),
  `clearDashboard`, `pickReportFiles`/`pickErpFolder` (native `QFileDialog` — the app uses `QApplication`
  so file/folder pickers work without the fragile `QtQuick.Dialogs` QML module), `goTo(index)` (+
  `navRequested` signal so empty-state quick-actions switch pages), `exportPdf/Excel`, `openReportsFolder`,
  `sendEmailReport`, `testConnection`, `testEmail`, `generateWhatsAppBridge`, `checkNode`, `saveSettings`,
  contacts CRUD + `syncContacts`.
  `saveSettings` rebuilds the `ConnectorHub` so new email/ERP/WhatsApp config takes effect immediately
  (connectors snapshot settings at construction). The Settings page configures **all** sources from the
  UI — no hand-editing `settings.json`.
- `analysis_worker.py` — `AnalysisWorker` on a `QThread`; wraps `run_all`, re-emits agent/progress/log
  as signals. The worker never touches QML.
- `models.py` — `AgentsModel` (11 agents + live state) and `ReportsModel` (`QAbstractListModel`s).
- `settings_bridge.py` — load/save `settings.json`.

**`app.py`** — entry point: `QApplication` (RTL) → load bundled fonts → set `Theme` + `app` context
properties → `QQuickView` loads `qml/Main.qml`.

**`qml/`** — flat directory (files auto-import each other by filename). `Main.qml` (sidebar shell +
`StackLayout` + toast bound to `app.notify`), six pages (`DashboardPage`, `InputPage`, `AnalysisPage`,
`ReportsPage`, `SettingsPage`, `ContactsPage`), and flat primitives (`ReportSection`, `MetricRow`,
`ListRow`, `FormField`, `FormCombo`, `AppButton`, `EmptyState`, `PageFrame`, `Glyph` — drawn shape
markers; the bundled fonts contain no symbol glyphs, so never use Unicode symbol characters in the UI).

## Configuration & data

- `settings.json` — backend keys for all five providers (ollama / claude / openai-compatible /
  gemini / azure; see the Running section) + `email_dept_map` / `whatsapp_groups` / `whatsapp_token`.
  **Gitignored** (holds real addresses); `settings.example.json` ships as the template.
- `data/contacts.json` — org structure + employees (authoritative; gitignored).
- `reports/latest.json` — most recent analysis, loaded on startup to repopulate the dashboard.
- `sample_reports.json` — demo input loaded via "تحميل نماذج".
- `assets/fonts/` — bundled Noto Kufi Arabic / Noto Sans Arabic / JetBrains Mono (OFL), loaded at startup.

## Conventions

- Department id vocabulary is shared across `AGENT_PROMPTS`, `WORKER_AGENTS`, `settings.json` maps,
  `EmailConnector._find_dept()` + the module-level `guess_dept()` in `connectors.py`, and `DEPT_KEY_MAP`
  — keep them consistent.
- Agent output values that drive colour use fixed Arabic literals: health `جيد`/`متوسط` (else danger),
  risk `عالية`/`متوسطة`/`منخفضة`, status `مكتمل`/`متأخر`, safety `آمن`/`خطر`, `تحذير`. `Theme.statusColor`
  and the exporters branch on these exact strings.
- **QML delegate gotcha:** model roles named like an `Item`/component property (`state`, `content`) are
  shadowed — qualify them as `model.state` / `model.content`.
- **Reactivity:** bind QML to notifying properties (e.g. `app.reportCount`), not one-shot method calls
  like `model.rowCount()`, or the UI won't refresh.
- Long-running work runs on a `QThread` worker or a daemon thread; all UI updates cross back via signals.
- **No Unicode symbol glyphs in the UI** (nav markers, empty-state icons, chevrons) — the bundled fonts
  carry none. Draw them with `Glyph.qml`.

## Packaging

**PyInstaller** (`marsad.spec`) builds `dist/marsad/` bundling `qml/` + `assets/` + seed configs;
`collect_all('PySide6')` is trimmed by an exclude filter (drops WebEngine/Quick3D/Charts/… to keep the
bundle ~200 MB). Onefile portable via `MARSAD_ONEFILE=1 pyinstaller marsad.spec`.
`packaging/windows/marsad.nsi` (NSIS) → installer `.exe`; `packaging/linux/build_deb.sh` → `.deb`.
`.github/workflows/build.yml` (needs `permissions: contents: write`) builds the Windows NSIS installer +
portable `.exe` and the Linux `.deb` on a `v*` tag and attaches them to the release.
`tools/capture_qt.py` renders per-page PNGs offscreen (`QT_QPA_PLATFORM=offscreen`).

**Frozen paths:** `core/paths.py` splits `BUNDLE_DIR` (read-only bundled assets) from `DATA_DIR`
(writable per-user state — `%APPDATA%/marsad`, `~/.local/share/marsad`). All state (settings, reports,
contacts, logs) uses `DATA_DIR`; never write next to the executable.
