# Task 00 — Foundation (non-visual plumbing)

Small, safe changes that later tasks build on. No visual redesign here.

## Goal

Make the app configuration-clean and cross-platform, and add a guarded RTL text helper that later
tasks may use for widgets Tk mis-renders.

## Files & anchors

- `app.py`: `_load_settings` (~line 1389), `_build_reports_tab` open-folder button (~line 693–725,
  the button calling `os.startfile`), top-of-file imports (~66–76).
- `settings.example.json` (already exists at repo root — do not overwrite; read it as the shape).

## Changes

1. **Cross-platform "open folder".** In the reports tab there is a button that opens the reports
   folder via `os.startfile(...)` — Windows-only, raises `AttributeError` on Linux/macOS. Add a
   helper method on `LTTApp`:

   ```python
   def _open_path(self, path):
       import subprocess, sys, os
       path = str(path)
       try:
           if sys.platform.startswith("win"):
               os.startfile(path)                       # noqa: only exists on Windows
           elif sys.platform == "darwin":
               subprocess.Popen(["open", path])
           else:
               subprocess.Popen(["xdg-open", path])
       except Exception as e:
           messagebox.showerror("خطأ", f"تعذّر فتح المجلد:\n{e}")
   ```
   Replace the `os.startfile(...)` call with `self._open_path(REPORTS)`.

2. **Guarded RTL helper.** Add a module-level function near the top of `app.py` (after imports):

   ```python
   def rtl(text: str) -> str:
       """Reshape + reorder Arabic for widgets Tk renders incorrectly.
       Guarded: if the shaping libs are missing, returns text unchanged."""
       try:
           import arabic_reshaper
           from bidi.algorithm import get_display
           return get_display(arabic_reshaper.reshape(text))
       except Exception:
           return text
   ```
   **Do not** apply `rtl()` anywhere yet. Later tasks decide per-widget after visual testing, because
   Tk on many systems already shapes Arabic and double-applying reverses it. This task only defines it.

3. **Settings example parity.** Confirm `_load_settings` tolerates the keys present in
   `settings.example.json` (`email_user`, `email_password`, `imap_host`, `smtp_host`, `smtp_port`,
   `report_recipients`, `erp_folder`). It already uses `.get(...)` with defaults elsewhere, so no
   schema change is needed — just verify no `KeyError` path exists when a fresh
   `settings.json` (copied from the example) is loaded.

4. **Model-name note.** Add a one-line comment above the `ollama_model` default in `_load_settings`
   (or wherever the default dict lives) noting the model must be pulled (`ollama pull <model>`) or
   changed to a locally-installed one. No behavior change.

## Design rules

Follow the Global design rules in `README.md`. No visual output changes expected from this task.

## Acceptance criteria

- On Linux, clicking "open reports folder" opens the file manager (or shows a clean Arabic error),
  never an `AttributeError` traceback.
- `rtl("مرحبا")` is importable and returns a string; app still launches if `arabic_reshaper`/`bidi`
  are absent.
- Copying `settings.example.json` to `settings.json` and launching the app produces no `KeyError`.

## Out of scope

Styling, layout, colors, factories (those are tasks 01+).
