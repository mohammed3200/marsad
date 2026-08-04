# Release checklist — مرصد (marsad)

Run this before tagging any version. Every automated item below was green on the
`fix/launch-readiness` branch; the manual items need a human and a real model.

## Automated

- [ ] `python3 -m unittest discover -s tests -v` — 177 tests, all pass
- [ ] `python3 tools/test_api.py` — 7 tests, all pass
- [ ] `QT_QPA_PLATFORM=offscreen python3 tools/capture_qt.py docs/screenshots` — six PNGs, and stderr free of `QML ERROR`, `ReferenceError`, `TypeError` and `Unable to assign`. Open `2-dashboard.png`: no toast across the bottom, and the lower half populated. `reports/latest.json` must be byte-identical afterwards — the harness seeds its demo result in memory only.
- [ ] `pyinstaller --noconfirm marsad.spec` — completes, `dist/marsad/` exists
- [ ] `git ls-files | grep -E "settings\.json$|contacts\.json$|^reports/|^logs/|^uploads/"` — no output
- [ ] Security probes, all true:
  - `connectors.SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED` and `check_hostname`
  - `build_report_html` with `<img src=x onerror=…>` yields no raw `<img`, no live `onerror="`, and contains `&lt;img`
  - `import api.app` without `MARSAD_API_ENABLE=1` raises
  - `GET /api/settings` returns every key in `SECRET_KEYS` as `""`
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
- [ ] **Run an analysis end to end against a real model** — the dashboard fills and the app
      navigates to it. *Needs: the same backend as «اختبار المحرّك».* On a backend where every
      agent times out, the run now reports failure honestly (red progress track, «لم ينجح أي
      وكيل», no navigation) instead of claiming success — that path is worth confirming too.
- [ ] **Export PDF and Excel** — both open, Arabic reads right-to-left, no `%%` or `None%`,
      no `;pma&`. *Needs: any completed analysis, including a failed one. Performable now.*
- [ ] **Email the report to a real address** — it arrives and renders. *Needs:* `email_user`,
      `email_password`, `smtp_host`, `smtp_port`, **and at least one recipient** — the Send button
      stays disabled while both `report_recipients` and `email_dept_map` are empty. Requires a
      completed analysis first. Run «اختبار البريد» before this: it now tests the SMTP login too,
      so a failure there explains the send failure in advance.
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

**The web API does not ship in this release.** `api/` remains in the tree but
`api/app.py` refuses to import without `MARSAD_API_ENABLE=1`. It is experimental,
**unauthenticated**, and not hardened. Do not expose it beyond loopback. These
defects are known and deferred with it:

- No authentication of any kind, and no CSRF protection on the no-body POST routes.
- Its guard flags are not lock-protected, so two concurrent `POST /api/analysis/run`
  calls can both start a full run — doubling model spend and interleaving writes to
  `reports/latest.json`.
- Its WebSocket fan-out schedules one send task per event, so ordering is not
  preserved and a client can be dropped mid-run.
- `save_settings` does an in-place update on the same dict `AIEngine` holds, and there
  is no busy gate on `PUT /api/settings`, so a settings change during a run switches
  the provider mid-analysis. The desktop side fixed this; the API side did not.
- Its `_rebuild_hub` drops buffered WhatsApp reports rather than handing them over.
- `sync_contacts` calls `_rebuild_hub()` with no busy gate, so syncing contacts
  during a run swaps the connectors under it. The desktop's `syncContacts` gained
  that gate; the API mirror did not.
- Upload size and count caps are enforced *after* Starlette has already buffered and
  spooled the whole request, so they bound the copy written to `uploads/`, not the
  disk and bandwidth consumed receiving it.
- `send_email_report` never got the desktop's async + snapshot + guard-flag
  treatment (see `AppController.sendEmailReport`/`_run_send_email`): it runs
  SMTP synchronously on the request thread instead of a background thread, and
  does not snapshot `self._results`/recipients/`self._hub` before the blocking
  call, so a concurrent `PUT /api/settings` or dashboard clear can rebind them
  mid-send.
- `switch_engine_profile` still mutates `self._settings` in place before calling
  `save_settings({})`, the exact anti-pattern the desktop's
  `switchEngineProfile` was rewritten to remove (building the changed-keys dict
  first and routing through `save_settings()` in one call) — a failed write here
  leaves the in-memory engine already switched while `settings.json` still holds
  the old profile.

**Desktop limitations:**

- Running the desktop app and the web API against the same data directory at the same
  time is not supported — there is no cross-process locking.
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
