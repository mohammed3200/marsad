<div align="center">

# مرصد · marsad

**LTT 4G/5G Project-Management Intelligence — Arabic (RTL) desktop app**

Ingests field reports from email · WhatsApp · ERP, runs them through a fleet of LLM agents,
and produces an executive status brief plus branded PDF / Excel / HTML reports.

Qt Quick / QML · PySide6 · Ollama or Claude

</div>

---

## Screens

| لوحة التحكم — Dashboard | إدخال البيانات — Input |
|:--:|:--:|
| ![Dashboard](docs/screenshots/2-dashboard.png) | ![Input](docs/screenshots/0-input.png) |
| **التحليل والوكلاء — Analysis** | **جهات الاتصال — Contacts** |
| ![Analysis](docs/screenshots/1-analysis.png) | ![Contacts](docs/screenshots/5-contacts.png) |
| **التقارير — Reports** | **الإعدادات — Settings** |
| ![Reports](docs/screenshots/3-reports.png) | ![Settings](docs/screenshots/4-settings.png) |

The interface reads as a light executive brief: white paper, near-black ink, one deep teal-green
accent, a right-hand RTL sidebar, and colour rationed to a single status dot per metric. Arabic is
shaped and ordered correctly by Qt (HarfBuzz + BiDi).

## How it works

```mermaid
flowchart RL
    subgraph Sources["مصادر التقارير"]
        E["البريد الإلكتروني<br/>Email · IMAP"]
        W["واتساب<br/>WhatsApp"]
        R["ERP<br/>ملفات Excel/CSV/PDF"]
    end

    E --> HUB
    W --> HUB
    R --> HUB
    HUB["ConnectorHub<br/>collect_all()"] --> ENG

    subgraph Engine["AgentsEngine"]
        direction RL
        WORK["١٠ وكلاء متخصّصين<br/>ops · quality · safety · civil ·<br/>cost · contract · procure ·<br/>supply · risk · schedule"] --> CHIEF["وكيل التنسيق<br/>chief"]
    end

    ENG["AIEngine<br/>Ollama / Claude"] --> Engine
    CHIEF --> RESULTS["results dict<br/>reports/latest.json"]

    RESULTS --> DASH["لوحة التحكم<br/>QML Dashboard"]
    RESULTS --> PDF["export_pdf()"]
    RESULTS --> XLS["export_excel()"]
    RESULTS --> MAIL["build_report_html()<br/>→ email"]
```

The `results` dict — keyed by agent id (`chief`, `risk`, `cost`, `schedule`, …) — is the single
contract every layer reads. Ten domain agents analyse the reports; the `chief` agent aggregates their
output into `overall_health`, `executive_summary`, `kpis`, and `top_actions`.

## Install & run

Needs **Python 3.10+** and a running LLM backend (Ollama or Claude).

### Source (Windows · macOS · Linux)

```bash
git clone https://github.com/<you>/marsad.git
cd marsad
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp settings.example.json settings.json                   # then edit it
python app.py
```

### Installers (from the Releases page)

Grab a prebuilt package from the [latest release](https://github.com/mohammed3200/marsad/releases/latest):

- **Windows:** `marsad-setup-<version>.exe` (NSIS installer) or `marsad-<version>-portable.exe` (portable, no install).
- **Debian / Ubuntu:** `marsad_<version>_amd64.deb` — `sudo apt install ./marsad_<version>_amd64.deb`.

Build them yourself with **PyInstaller**:

```bash
pip install -r requirements.txt pyinstaller
pyinstaller marsad.spec                       # → dist/marsad/
bash packaging/linux/build_deb.sh 1.0.0       # → dist/marsad_1.0.0_amd64.deb  (needs dpkg-deb)
```

Windows installers are built in CI: pushing a `v*` tag runs `.github/workflows/build.yml`, which builds
the NSIS installer + portable `.exe` (Windows) and the `.deb` (Linux) and attaches them to the release.
An installed app keeps its config, reports, and contacts under a per-user data dir
(`%APPDATA%/marsad`, `~/.local/share/marsad`).

## Connect a backend

Edit `settings.json`:

**Ollama (local, default)** — install [Ollama](https://ollama.com), pull a model, then:
```json
{ "ai_backend": "ollama", "ollama_url": "http://localhost:11434", "ollama_model": "llama3.2" }
```
```bash
ollama pull llama3.2      # or any instruct model that returns JSON
```

**Claude API**
```json
{ "ai_backend": "claude", "claude_api_key": "sk-ant-…", "claude_model": "claude-opus-4-5" }
```

Test the connection from the **الإعدادات** (Settings) tab. Analysis speed depends on the model and
hardware — large local models may need a longer timeout.

## Data & privacy

`settings.json`, `data/contacts.json`, `reports/`, and `logs/` are **gitignored** — they hold live
config and output and never ship. `settings.example.json` (blank credentials) is the template. Contacts
entered in the app sync their email/WhatsApp → department routing back into `settings.json` via the
**مزامنة مع الإعدادات** button.

## Project layout

```
app.py                 Qt entry — loads qml/Main.qml
core/                  UI-agnostic logic (engine, contacts, exporters)
connectors.py          email / ERP / WhatsApp ingestion + outbound email
backend/               Qt bridge — theme, controller, worker, models, settings
qml/                   Light-report UI — Main + 6 pages + flat primitives
assets/fonts/          bundled Arabic + mono fonts (OFL)
tools/                 capture_qt.py (screenshots) · build_linux.sh
```

See [CLAUDE.md](CLAUDE.md) for the full architecture and conventions.

## License

Code: see [LICENSE](LICENSE). Bundled fonts: SIL Open Font License 1.1 — see
[assets/fonts/LICENSES.md](assets/fonts/LICENSES.md).
