# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

LTT PM Intelligence Desktop — an Arabic-language (RTL) Tkinter desktop app for construction/telecom project management (LTT 4G/5G rollout). It ingests field reports from multiple sources, runs them through a fleet of LLM "agents," and produces an executive dashboard plus branded PDF/Excel/HTML reports. UI text, agent prompts, and output JSON keys/values are all in Arabic — preserve Arabic strings verbatim when editing.

## Running

```bash
python app.py          # launches GUI; auto-installs missing pip deps on first run
```

There is no `requirements.txt` despite the docstring referencing one. Dependencies are auto-installed by `_auto_install()` / `show_installer()` at startup: `openpyxl`, `reportlab`, `arabic-reshaper`, `python-bidi`, `PyPDF2`, `Pillow`, `python-dotenv`, `schedule`. No test suite, linter, or build step exists.

Requires a running LLM backend — either **Ollama** local (`http://localhost:11434`, model `llama3.2`, the default) or **Claude API** (set `ai_backend: "claude"` + `claude_api_key` in `settings.json`). WhatsApp ingestion additionally needs Node.js + a separately-generated `whatsapp_bridge.js` (Baileys).

## Architecture

Data flows in one direction: **connectors → AgentsEngine → results dict → exporters/UI**. The `results` dict (keyed by agent id, e.g. `chief`, `risk`, `cost`, `schedule`) is the single contract passed between every layer. Changing an agent's output JSON schema means updating consumers in `__init__.py` (PDF/Excel) and `connectors.py` (`build_report_html`) too.

**`app.py`** — everything UI + the AI core (~1500 lines, single file):
- `AIEngine.ask()` dispatches to Ollama or Claude, always returning a dict (parses JSON out of the model response).
- `AGENT_PROMPTS` — dict of `agent_id → (arabic_description, json_schema_example)`. This is the heart of the system. Each entry defines one specialist agent's role and the exact JSON shape it must return.
- `WORKER_AGENTS` — the 10 domain agents (ops, quality, safety, civil, cost, contract, procure, supply, risk, schedule). `AgentsEngine.run_all()` runs each over the formatted report text, then feeds all their outputs into the `chief` coordinator agent which produces `overall_health`, `executive_summary`, `kpis`, and `top_actions`. Results saved to `reports/results_<ts>.json` and `reports/latest.json`.
- `LTTApp(tk.Tk)` — the whole GUI: tabbed interface (input / analysis / dashboard / reports / settings / contacts). Agent cards, progress, dashboard refresh live here.

**`connectors.py`** — report ingestion + outbound email:
- `EmailConnector` — IMAP fetch of UNSEEN mail, maps sender→department via `email_dept_map`, extracts PDF attachments to text; SMTP send of final report.
- `ERPConnector` — watches a folder for Excel/CSV/JSON/PDF files, guesses department from filename.
- `WhatsAppHelper` — does NOT connect directly; it emits `whatsapp_bridge.js` (Node/Baileys) which POSTs messages to a local Python endpoint. Setup is manual/QR-based.
- `ConnectorHub` — single facade the app uses: `collect_all()` drains email + ERP + buffered WhatsApp into one `reports` list.
- `build_report_html()` — HTML email body from the `results` dict.

**`contacts_manager.py`** — `ContactsDB` (JSON-backed org chart in `data/contacts.json`: 3 top departments → sub-departments → employees) and `ContactsTab`/`EmployeeDialog` Tkinter widgets. `export_to_config()` syncs employee email/WhatsApp→department mappings back into `settings.json`, which is how connectors learn routing.

**`__init__.py`** — `export_pdf()` and `export_excel()`. Standalone functions taking `(results, output_path)`. Heavy manual reportlab/openpyxl layout with a fixed color palette and RTL sheets. Both read the same `results` dict keys as the dashboard.

## Configuration & data

- `settings.json` — backend choice, Ollama/Claude config, `email_dept_map` (email→dept string), `whatsapp_groups` (phone→dept). Department strings here (e.g. `"ran"`, `"cost"`) must match the agent/routing logic.
- `data/contacts.json` — org structure + employees (authoritative contact source; syncs to settings).
- `reports/latest.json` — most recent analysis, loaded on startup to repopulate the dashboard.
- `sample_reports.json` / `contacts.json` (repo root) — demo data loaded via the "load samples" UI action.

## Conventions

- The department id vocabulary is shared across `AGENT_PROMPTS`, `WORKER_AGENTS`, `settings.json` maps, and connector `_find_dept`/`_guess_dept` — keep them consistent when adding a department.
- Agent output values that drive color/status in reports use fixed Arabic literals: health `"جيد"`/`"متوسط"` (else danger), risk levels `"عالية"`/`"متوسطة"`/`"منخفضة"`, statuses `"مكتمل"`/`"متأخر"`. Exporters branch on these exact strings.
- Long-running work (analysis, email fetch, ollama pull) runs in `threading.Thread` workers that marshal back to Tkinter via `self.after(...)`.
