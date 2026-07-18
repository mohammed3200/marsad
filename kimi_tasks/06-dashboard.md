# Task 06 — Dashboard: KPI instrument tiles, empty state, formatted panels

## Files & anchors

- `app.py`: `_build_dashboard_tab` (~lines 646–688), `_refresh_dashboard` (~1177–1231).

## Current state

Title, a `BG_MID` status bar with `_health_lbl` + refresh button, `_kpi_frame` (rebuilt each refresh
into up to 6 bordered KPI cards), and two disabled `ScrolledText` boxes (summary, actions). No empty
state before the first analysis; KPI cards and action list are plain text, values not monospaced.

## Changes

1. **Empty state.** When `self.results` is falsy, show a centered dim panel in the KPI area and a hint
   in the summary/action boxes: `شغّل التحليل من تبويب "التحليل والوكلاء" لعرض المؤشرات`. Add an
   `_render_dashboard_empty()` and call it from `_build_dashboard_tab` when there are no results
   (instead of leaving `_kpi_frame` blank).

2. **KPI tiles via factory.** In `_refresh_dashboard`, replace the hand-built KPI `tk.Frame`+labels
   loop with `self._kpi_tile(self._kpi_frame, value=kpi["value"], name=kpi["name"],
   trend=kpi.get("trend","→"), status=kpi.get("status",""))`. The value must render in `FONT_MONO`
   (the factory already does this). Keep the 6-max and the `columnconfigure(weight=1)` grid.

3. **Formatted summary panel.** Keep the summary `ScrolledText` but give the executive summary a small
   header row above it that repeats the health as a `_pill` (color-coded), so the dashboard body
   restates status without re-reading the top bar.

4. **Actions as structured rows, not a text dump.** Replace the `_actions_box` text concatenation with
   a small scrollable frame of rows, each row = a `_card` containing: a monospace priority badge
   (`[1]`), the action text (`TEXT_PRI`, right-aligned), and a second line with owner / deadline /
   impact in `TEXT_SEC`/`FONT_SMALL`. If a full rewrite is risky, at minimum: right-align the text,
   put the priority number in `FONT_MONO`, and add spacing between actions. Preserve every Arabic
   label (`المسؤول`, `الموعد`, `التأثير`).

5. **Health bar + beacon sync.** At the end of `_refresh_dashboard`, call `self._update_beacon()`
   (added in task 03) so the header stays in sync.

## Design rules

Global rules in `README.md`. Numbers in `FONT_MONO`. Colors strictly from `status_color(...)`. Don't
nest cards inside cards (a KPI tile is one card; don't wrap it in another).

## Acceptance criteria

- Fresh clone with no `reports/latest.json` (or empty results): dashboard shows the Arabic empty-state
  hint, not blank boxes.
- With results: up to 6 KPI tiles render with monospaced values and status-colored borders/trends;
  the summary shows a color-coded health pill; the action plan reads as spaced structured rows.
- The header beacon matches the dashboard health after a refresh.

## Out of scope

Reports/settings tabs (task 07).
