# Task 07 — Reports + Settings tabs

Two tabs, one task: both are form/list heavy and share the same rough edges.

## Files & anchors

- `app.py`: `_build_reports_tab` (~693–725), `_build_settings_tab` (~730–821), helpers `_section`
  (~857), `_setting_row` (~863), `_test_email_conn` (~824), `_test_connection` (~1314),
  `_refresh_files_list` (~1112).

## Reports tab changes

1. **Empty state** for the generated-files `Listbox` (`_files_list`): when empty, show
   `لا توجد تقارير مُصدَّرة بعد — شغّل التحليل ثم صدّر PDF/Excel`.
2. **Factory buttons.** Migrate export-PDF / export-Excel / open-folder to `self._btn`: PDF = accent,
   Excel = success, open = ghost. Remove the hardcoded `#7C3AED` purple (not in the palette).
3. **Open folder** already fixed in task 00 (`self._open_path`); confirm the button calls it.
4. Primary action (export) rightmost per RTL.

## Settings tab changes

1. **Make it scrollable.** The settings form is a plain `tk.Frame` with no scroll; on smaller windows
   the Claude-API / recipients rows overflow off-screen. Wrap the content in a `tk.Canvas` +
   `Dark.Vertical.TScrollbar` (styled in task 02) + inner frame, with mousewheel binding. Pattern:
   ```python
   canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
   vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview, style="Dark.Vertical.TScrollbar")
   inner = tk.Frame(canvas, bg=BG_DARK)
   inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
   canvas.create_window((0,0), window=inner, anchor="nw")
   canvas.configure(yscrollcommand=vsb.set)
   canvas.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")
   # bind_all("<MouseWheel>") + <Button-4/5> for Linux
   ```
   Build all existing sections into `inner` instead of `parent`. Keep `_section`/`_setting_row`.
3. **Align label columns.** `_setting_row` uses `width=16`; the inline AI-engine row uses `width=14` —
   unify to one constant so rows line up.
4. **Connection-test feedback as a pill.** `_test_email_conn` and `_test_connection` currently set a
   plain label (`conn_lbl`). Show a `_pill`-style result: green `✓ متصل` / red `✗ فشل الاتصال` with the
   detail text beside it. Keep the existing test logic; only change how the result renders.
5. **Factory buttons** for test/save/install/pull/browse (accent for save/test, ghost for
   browse/install).
6. RTL: right-align section titles and field labels.

## Design rules

Global rules in `README.md`. No new hex outside tokens (delete the purple). Numbers (smtp port) in
`FONT_MONO` is optional, not required.

## Acceptance criteria

- Settings tab scrolls (wheel + scrollbar); no row is clipped at a 1000×700 window.
- Reports and files lists show empty-state hints when empty.
- Export/test/save buttons are factory buttons; no `#7C3AED` remains (`grep -n "#7C3AED" app.py`
  returns nothing).
- Email/connection test shows a color-coded pill result, not a bare gray label.
- Label columns align between `_setting_row` rows and the AI-engine row.

## Out of scope

Contacts tab (task 08).
