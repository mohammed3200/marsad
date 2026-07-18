# marsad UI polish — progress

Run in order. Tick when the task's Acceptance criteria pass in a live `python app.py` run.

- [ ] 00 — Foundation (settings.example wiring, rtl() helper, cross-platform open, model note)
- [ ] 01 — Design tokens + widget factories (`_pill`, `_card`, `_kpi_tile`, `_btn`)
- [ ] 02 — ttk styles pass (notebook, buttons, entry, combobox, treeview, scrollbars)
- [ ] 03 — Header operations status beacon (signature element)
- [ ] 04 — Input tab: RTL layout, empty state, factories, validation
- [ ] 05 — Agent telemetry: live per-agent card states + status pills
- [ ] 06 — Dashboard: KPI instrument tiles + empty state + formatted panels
- [ ] 07 — Reports + Settings: scrollable settings, cross-platform open, empty states
- [ ] 08 — Contacts tab styling pass (contacts_manager.py)

## Notes / decisions log

_(Kimi or reviewer append per-task notes here: what changed, anything deferred.)_

### Findings from baseline capture (before any task ran)

- **Tk renders Arabic RTL natively** on this system (confirmed by screenshot). RTL work = layout
  mirroring only; do not blanket-apply `rtl()`. (Folded into task 00 + the global rules.)
- **Pre-existing crash** in `contacts_manager.py` `_build`: search-var trace fires before `self._tbl`
  exists → `AttributeError`. Now Change 0 of task 08 — fix first.
- `reports/latest.json` currently holds placeholder `...` KPI values, so the dashboard looks empty.
  Good dashboard screenshots need a real analysis run with a working Ollama model (see repo README
  troubleshooting: installed model is `metatron-qwen:latest`, not the configured `llama3.2`).
- Screenshots are captured by `tools/capture_screenshots.py` (Xlib direct-window grab; needs
  `pip install python-xlib` — a root-framebuffer grab returns black on this headless X server).
