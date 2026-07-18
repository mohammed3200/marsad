# Task 02 — ttk styles pass

Bring the ttk widgets (notebook, buttons, entries, comboboxes, treeview, scrollbars) up to the same
polish as the token system, and fix the inconsistency where some widgets are ttk-styled and most are
raw `tk` with inline args.

## Files & anchors

- `app.py`: `_setup_styles` (~line 352–389).

## Current state (from review)

`clam` theme; styles defined for `Dark.TFrame`, `Card.TFrame`, `Accent/Success/Danger.TButton`,
several `*.TLabel`, `Dark.TNotebook(.Tab)`, `Dark.Horizontal.TProgressbar`, `Dark.TEntry`,
`Dark.TCombobox`, `Dark.TSeparator`. Rough edges: only `Accent.TButton` has a hover `map`; no disabled
state; no `Treeview` style (the contacts table + reports lists look unstyled); combobox popdown list
is default-white.

## Changes

1. **Buttons:** add `style.map` hover/pressed/disabled for `Success.TButton` and `Danger.TButton`
   (mirror `Accent`). Add a `Ghost.TButton` (bg `BG_MID`, fg `TEXT_PRI`) with hover → `BG_CARD`. Add
   `disabled` foreground `TEXT_DIM` to all four.

2. **Notebook tabs:** increase selected-tab contrast — keep selected fg `ACCENT2` but add a subtle
   top accent by setting `padding=(SP_4, SP_2)` and `borderwidth=0`; give unselected tabs
   `foreground=TEXT_SEC` (already) and `active` (hover) foreground `TEXT_PRI`.

3. **Entry / Combobox:** unify `fieldbackground` to one token (introduce `INPUT_BG = "#0f1e2e"` in the
   token block if you prefer, or reuse the existing literal consistently). Style the combobox
   **popdown** list dark: after creating the style, set the option DB:
   ```python
   self.option_add("*TCombobox*Listbox.background", BG_CARD)
   self.option_add("*TCombobox*Listbox.foreground", TEXT_PRI)
   self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
   self.option_add("*TCombobox*Listbox.selectForeground", WHITE)
   ```

4. **Treeview** (used by the contacts table and any ttk lists): add
   `style.configure("Dark.Treeview", background=BG_CARD, fieldbackground=BG_CARD,`
   `foreground=TEXT_PRI, borderwidth=0, rowheight=26)` and
   `style.configure("Dark.Treeview.Heading", background=BG_MID, foreground=TEXT_PRI,`
   `font=FONT_SMALL)`, plus `style.map("Dark.Treeview", background=[("selected", ACCENT)])`. (Task 08
   applies `style="Dark.Treeview"` to the contacts tree; just define it here.)

5. **Scrollbars:** add a `Dark.Vertical.TScrollbar` (troughcolor `BG_DARK`, background `BG_MID`,
   arrow/border 0) so scrollbars stop rendering as light native widgets.

6. **Progressbar:** keep, but add an indeterminate-friendly bg — no change needed if thickness reads
   well; bump `thickness` to 12.

## Design rules

Global rules in `README.md`. Do not restyle by adding inline colors on widgets — everything here is in
`_setup_styles`. Migration of raw `tk.Button` → `_btn` happens in the per-tab tasks, not here.

## Acceptance criteria

- App launches; all buttons show hover feedback; disabled run-button text is dimmed, not invisible.
- Comboboxes (source/dept on the input tab) open a **dark** dropdown list, not white.
- No traceback from the new `Treeview`/`Scrollbar` styles even before task 08 applies them.

## Out of scope

Per-tab layout and factory migration (tasks 04–08).
