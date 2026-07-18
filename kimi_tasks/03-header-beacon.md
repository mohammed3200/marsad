# Task 03 — Header operations status beacon (signature element)

This is the app's signature: a persistent project-health beacon in the top header, visible on every
tab, driven by `chief.overall_health`. It turns the static header into a live vitals bar and is the
one memorable element — keep everything else quiet.

## Files & anchors

- `app.py`: `_build_ui` header block (~lines 394–411), `_refresh_dashboard` (~1177), `__init__`
  (~330) where `self.results` is loaded on startup.

## Current state

Header (`tk.Frame bg=BG_MID height=60`) holds the ⚡ icon, title, subtitle, and a right-aligned
`self.status_lbl` showing Ollama connection. Health is only shown inside the dashboard tab
(`self._health_lbl`), not globally.

## Changes

1. **Add a beacon** to the header, placed left of `status_lbl` (so, packed `side="right"` before it).
   Structure: a small colored dot label + a health text label, both `bg=BG_MID`:
   ```python
   self._beacon_dot = tk.Label(header, text="●", bg=BG_MID, fg=TEXT_DIM, font=("Arial",14))
   self._beacon_txt = tk.Label(header, text="الحالة العامة: —", bg=BG_MID, fg=TEXT_SEC, font=FONT_SMALL)
   self._beacon_txt.pack(side="right", padx=(0, SP_4))
   self._beacon_dot.pack(side="right", padx=(SP_3, SP_2))
   ```

2. **Add `_update_beacon(self)`** that reads `self.results["chief"]["overall_health"]` and sets dot +
   text color via `status_color(...)`:
   ```python
   def _update_beacon(self):
       health = (self.results or {}).get("chief", {}).get("overall_health")
       if not health:
           self._beacon_dot.config(fg=TEXT_DIM)
           self._beacon_txt.config(text="الحالة العامة: لم يُحلَّل بعد", fg=TEXT_SEC)
           return
       c = status_color(health)
       self._beacon_dot.config(fg=c)
       self._beacon_txt.config(text=f"الحالة العامة: {health}", fg=c)
   ```

3. **Call `_update_beacon()`**: once at the end of `_build_ui` (reflect any results loaded from
   `reports/latest.json` on startup), and at the end of `_refresh_dashboard` (so a new analysis
   updates the global beacon too).

4. Keep `status_lbl` (Ollama connection) as-is; the beacon is a **separate** indicator. Make sure the
   two don't visually collide — give the beacon text a trailing separator or spacing.

## Design rules

Global rules in `README.md`. The beacon is the **only** place boldness is spent in the chrome. Dot +
short Arabic label, color-coded. No animation beyond the discrete color change.

## Acceptance criteria

- On launch with an existing `reports/latest.json`, the header beacon shows the correct health word
  and color (green `جيد` / amber `متوسط` / red `حرج`), matching the dashboard status bar.
- With no results, it reads `الحالة العامة: لم يُحلَّل بعد` in a dim color.
- After running an analysis, the beacon updates without needing a tab switch.

## Out of scope

Dashboard tile formatting (task 06); the dashboard's own `_health_lbl` stays.
