# Release checklist — مرصد (marsad)

Run this before tagging any version. Every automated item below was green on the
`fix/launch-readiness` branch; the manual items need a human and a real model.

## Automated

- [ ] `python3 -m unittest discover -s tests -v` — 112 tests, all pass
- [ ] `python3 tools/test_api.py` — 7 tests, all pass
- [ ] `QT_QPA_PLATFORM=offscreen python3 tools/capture_qt.py docs/screenshots` — six PNGs, and stderr free of `QML ERROR`, `ReferenceError`, `TypeError` and `Unable to assign`
- [ ] `pyinstaller --noconfirm marsad.spec` — completes, `dist/marsad/` exists
- [ ] `git ls-files | grep -E "settings\.json$|contacts\.json$|^reports/|^logs/|^uploads/"` — no output
- [ ] Security probes, all true:
  - `connectors.SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED` and `check_hostname`
  - `build_report_html` with `<img src=x onerror=…>` yields no raw `<img`, no live `onerror="`, and contains `&lt;img`
  - `import api.app` without `MARSAD_API_ENABLE=1` raises
  - `GET /api/settings` returns every key in `SECRET_KEYS` as `""`
- [ ] Regression spot-checks: `AIEngine._parse_json('[{"a":1}]')` returns an error dict, not a list; `export_excel` succeeds with `"priority": "1"`; `export_pdf` succeeds with `"deviation_pct": "12%"`

## Manual, on a clean machine

- [ ] Fresh `python3 -m venv` + `pip install -r requirements.txt`, then `python app.py` starts
- [ ] Settings: enter a provider key, «اختبار المحرّك» reports success
- [ ] Input: upload one `.docx`, one `.xlsx` and one `.pdf` — all three appear with the right department
- [ ] Run an analysis end to end against a real model — the dashboard fills and the app navigates to it
- [ ] Export PDF and Excel — both open, Arabic reads right-to-left, no `%%` or `None%`, no `;pma&`
- [ ] Email the report to a real address — it arrives and renders
- [ ] Link WhatsApp, send one group message, collect — it appears as a report
- [ ] Close the window mid-analysis — the process exits cleanly, no crash dialog, and reopening works

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
- Upload size and count caps are enforced *after* Starlette has already buffered and
  spooled the whole request, so they bound the copy written to `uploads/`, not the
  disk and bandwidth consumed receiving it.

**Desktop limitations:**

- Running the desktop app and the web API against the same data directory at the same
  time is not supported — there is no cross-process locking.
- Closing the window during an analysis waits up to `ai_timeout + 5s` for the current
  agent call to finish. The window closes immediately and the connectors and WhatsApp
  port are released first, so a relaunch works right away, but a background process can
  linger for that period. If that wait expires the process can still hit the original
  `QThread: Destroyed while thread is still running` abort — reduced from certain to
  near-zero, not eliminated.
- Department creation and employee editing are not available in the Contacts UI; the
  seeded default org structure is what ships.
- Filename-based department routing is best-effort. `5Gcore_report.csv` does not route
  (the `g` stays glued to `core`), and `العقد` is a genuine homograph — "the contract"
  and "the decade" are identical, so `عقد`/`عقود` match only bare tokens. Unmatched
  files land in `admin` for manual triage, which is the safe direction.
- `core/errors.py::friendly_error()` falls back to «تعذّر الاتصال: …» with a truncated
  raw tail for any error it does not recognise. That names the wrong cause for a
  non-network failure — e.g. a programming error reads as a connection failure.

## Do not

- Do not create or move a git tag, or publish a GitHub release, without the owner's
  explicit say-so. That permission has been withheld throughout this work.
- Do not commit `settings.json`, `data/contacts.json`, `reports/`, `logs/` or `uploads/`.
