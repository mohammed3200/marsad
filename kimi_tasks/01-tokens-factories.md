# Task 01 — Design tokens + widget factories

The single most important task: it removes the duplicated inline styling that makes every later task
expensive. Centralize spacing/type tokens and add four widget factories every other tab will reuse.

## Goal

One source of truth for spacing/radius/type, plus `_pill`, `_card`, `_kpi_tile`, `_btn` so a restyle
touches factories, not dozens of call sites.

## Files & anchors

- `app.py`: token block (~lines 86–104), class `LTTApp` (add factory methods near `_setup_styles`,
  ~line 352). Existing helpers `_section` (~857) and `_setting_row` (~863) are the pattern to follow.

## Changes

1. **Extend the token block** (after the existing color/font constants, ~line 104) with spacing and a
   semantic status→color map. Keep names UPPER_SNAKE, module-level:

   ```python
   # ── spacing scale (px) ──
   SP_1, SP_2, SP_3, SP_4, SP_5, SP_6 = 4, 8, 12, 16, 24, 32
   RADIUS = 8            # visual target; Tk frames are square, used for padding rhythm

   # ── semantic status → color (branch on the fixed Arabic literals) ──
   STATUS_COLORS = {
       "جيد": SUCCESS, "متوسط": WARNING, "حرج": DANGER,
       "تحذير": WARNING, "آمن": SUCCESS, "خطر": DANGER,
       "عالية": DANGER, "متوسطة": WARNING, "منخفضة": SUCCESS,
       "مكتمل": SUCCESS, "متأخر": DANGER,
   }
   def status_color(value, default=TEXT_SEC):
       return STATUS_COLORS.get(value, default)
   ```

2. **Add factory methods** on `LTTApp` (place them right after `_setup_styles`):

   - `_btn(parent, text, command, kind="accent", **kw)` → a styled `tk.Button`. `kind` ∈
     `{"accent","success","danger","ghost"}` maps to
     `{ACCENT, SUCCESS, DANGER, BG_MID}` background with `WHITE`/`TEXT_PRI` fg, `bd=0`,
     `cursor="hand2"`, `padx=SP_4, pady=SP_2`, `font=FONT_BODY`. Add a hover via `bind("<Enter>"/"<Leave>")`
     that lightens the bg (accent→`#1D4ED8`, success→`#059669`, danger→`#DC2626`, ghost→`BG_CARD`).
     Return the button so callers can `.pack/.grid`.

   - `_card(parent, **kw)` → a `tk.Frame(bg=BG_CARD, bd=0, highlightthickness=1,`
     `highlightbackground=BG_MID)`. Accepts a `border` kwarg to override the highlight color
     (used by KPI/agent states). Return it.

   - `_pill(parent, text, value)` → a small chip `tk.Label` colored by `status_color(value)`:
     background = a dark tint (use `BG_CARD`), foreground = `status_color(value)`,
     `font=FONT_SMALL`, `padx=SP_2, pady=1`, text shows the Arabic `value`. Return it. (Tk labels are
     rectangular; that's fine — the color is the signal.)

   - `_kpi_tile(parent, value, name, trend="→", status="")` → a `_card` containing: value in
     `FONT_MONO` bold sized ~16 colored by `status_color(status)`, `name` in `FONT_SMALL`/`TEXT_SEC`,
     `trend` arrow colored by status. Return the card. (Task 06 uses this.)

3. **Refactor `_section` and `_setting_row`** to use `SP_*` for their paddings instead of literal
   numbers, so spacing is consistent. Keep their signatures unchanged.

## Design rules

Global rules in `README.md`. Factories must not hard-code any hex not already in the token block.
Numbers (KPI values, pill counts) use `FONT_MONO`.

## Acceptance criteria

- `_btn`, `_card`, `_pill`, `_kpi_tile`, `status_color`, and the `SP_*` tokens all exist and are
  importable/usable; app launches unchanged (nothing calls the factories yet, so the UI looks the
  same — this task only adds capability).
- Calling each factory in a scratch window renders without error and applies hover on `_btn`.

## Out of scope

Migrating existing widgets to the factories — that happens per-tab in tasks 02–08.
