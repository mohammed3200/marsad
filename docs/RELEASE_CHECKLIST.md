# Release checklist — مرصد (marsad)

Run this before tagging any version. Every automated item below was green on the
`fix/launch-readiness` branch; the manual items need a human and a real model.

## Automated

- [ ] `python3 -m unittest discover -s tests -v` — 185 tests, all pass
- [ ] `QT_QPA_PLATFORM=offscreen python3 tools/capture_qt.py docs/screenshots` — six PNGs, and stderr free of `QML ERROR`, `ReferenceError`, `TypeError` and `Unable to assign`. Open `2-dashboard.png`: no toast across the bottom, and the lower half populated. `reports/latest.json` must be byte-identical afterwards — the harness seeds its demo result in memory only.
- [ ] `pyinstaller --noconfirm marsad.spec` — completes, `dist/marsad/` exists
- [ ] `git ls-files | grep -E "settings\.json$|contacts\.json$|^reports/|^logs/|^uploads/"` — no output
- [ ] Security probes, all true:
  - `connectors.SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED` and `check_hostname`
  - `build_report_html` with `<img src=x onerror=…>` yields no raw `<img`, no live `onerror="`, and contains `&lt;img`
- [ ] Regression spot-checks: `AIEngine._parse_json('[{"a":1}]')` returns an error dict, not a list; `export_excel` succeeds with `"priority": "1"`; `export_pdf` succeeds with `"deviation_pct": "12%"`
- [ ] `grep -nP '[\x{2190}-\x{21FF}]' qml/*.qml` — matches only comment lines. The bundled Arabic fonts carry no arrows, so one in a rendered string means a system-fallback dependency or a tofu box.
- [ ] Honesty probe — run `AgentsEngine.run_all` with an AI stub that errors on every call: the log must **not** end with `✓ اكتمل التحليل الشامل`, and `AppController._on_analysis_done` must emit `analysisFailed`, not `analysisDone`. PDF, Excel and HTML must still export with no English or traceback leaking into the Arabic output.

## Manual, on a clean machine

Each item lists what it needs. Three of them cannot be performed on hardware that
cannot run a model fast enough, or without a second device — plan for that rather
than discovering it mid-pass.

- [ ] **App starts.** Fresh `python3 -m venv` + `pip install -r requirements.txt`, then `python app.py`.
      *Needs: nothing else.*
- [ ] **«اختبار المحرّك» reports success.** *Needs: a backend that answers within `ai_timeout`
      (default 180s).* A CPU-only local model will not — measured on the dev machine at
      ~0.33 tok/s, where a single agent's JSON would take 25–75 minutes. The test is two-stage,
      so even when it fails it distinguishes an unreachable server from a model that is merely
      too slow; only the second is a hardware problem rather than a config one.
- [ ] **Upload one `.docx`, one `.xlsx` and one `.pdf`** — all three appear with the right department.
      *Needs: nothing else. Performable now.*
- [x] **Run an analysis end to end against a real model** — done 2026-08-05: 11/11 agents,
      159s, no errors; PDF/Excel/HTML exported from that result and inspected. It caught a
      real defect no fixture could — multi-line Arabic in the PDF rendered bottom-to-top.
      Re-run this on any release that touches the engine or the exporters.
      *Needs: a backend that answers within `ai_timeout`.* On a backend where every
      agent times out, the run now reports failure honestly (red progress track, «لم ينجح أي
      وكيل», no navigation) instead of claiming success — that path is worth confirming too.
- [ ] **Export PDF and Excel** — both open, Arabic reads right-to-left, no `%%` or `None%`,
      no `;pma&`. *Needs: any completed analysis, including a failed one. Performable now.*
- [ ] **Email the report to a real address** — it arrives and renders. *Needs:* `email_user`,
      `email_password`, `smtp_host`, `smtp_port`, **and at least one recipient** — the Send button
      stays disabled while both `report_recipients` and `email_dept_map` are empty. Requires a
      completed analysis first. Run «اختبار البريد» before this: it tests the SMTP login too, so a
      failure there explains the send failure in advance.
      The *message* is already verified — `SentMessageWireFormatTests` captures the bytes handed to
      sendmail and parses them back the way a receiving server would: Arabic subject round-trips,
      HTML body byte-identical in UTF-8, attachments byte-intact, certificates verified. What this
      manual item still adds is only the network hop and the recipient's renderer.
- [ ] **Link WhatsApp, send one group message, collect** — it appears as a report.
      *Needs:* Node.js on `PATH`; a first run that installs the Baileys bridge deps (allow up to
      600s); **a second device** — a phone with WhatsApp to scan the QR; and the group's JID mapped
      in `whatsapp_groups`, or the message routes to `admin`. The bridge is **receive-only**; "send
      one group message" means sending *from your phone into the group*, then pressing
      «جمع من المصادر».
- [ ] **Close the window mid-analysis** — the process exits cleanly, no crash dialog, and
      reopening works. *Needs: nothing else. Performable now* (start a run against any backend,
      even a failing one, and close while it is in flight).

## Known accepted limitations — state these in the release notes

**Desktop limitations:**

- Closing the window during an analysis waits up to `ai_timeout + 5s` for the current
  agent call to finish. The window closes immediately and the connectors and WhatsApp
  port are released first, so a relaunch works right away, but a background process can
  linger for that period. If that wait expires the process can still hit the original
  `QThread: Destroyed while thread is still running` abort — reduced from certain to
  near-zero, not eliminated.
- `_run_collect`'s error branch still emits `notify` on its worker thread, and
  `_run_bridge_start` writes `self._wa_log`/`self._wa_proc` directly. Same class as the
  four workers converted to the private-signal hop, deliberately left out of that scope.
- Some run-log lines use symbols the bundled fonts do not carry: `✓ ✗` (present only in
  JetBrains Mono, but the log panel renders in Noto Sans Arabic) and `⏳ ⏹ 📥 📧 🖥️`
  (absent from all three). They reach the Analysis page through `logMessage` and depend
  on a system fallback font, which `CLAUDE.md` forbids. The two Unicode arrows in QML
  were fixed; this set was not.
- Department creation and employee editing are not available in the Contacts UI; the
  seeded default org structure is what ships.
- Filename-based department routing is best-effort. `5Gcore_report.csv` does not route
  (the `g` stays glued to `core`), and `العقد` is a genuine homograph — "the contract"
  and "the decade" are identical, so `عقد`/`عقود` match only bare tokens. Unmatched
  files land in `admin` for manual triage, which is the safe direction.

## Do not

- Do not create or move a git tag, or publish a GitHub release, without the owner's
  explicit say-so. That permission has been withheld throughout this work.
- Do not commit `settings.json`, `data/contacts.json`, `reports/`, `logs/` or `uploads/`.
