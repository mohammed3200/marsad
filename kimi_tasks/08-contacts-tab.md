# Task 08 — Contacts tab styling pass

The contacts UI lives in a **separate file** (`contacts_manager.py`) as its own `ContactsTab` /
`EmployeeDialog` classes. Without this pass the app looks half-restyled: five polished tabs and one
default-gray one.

## Files & anchors

- `contacts_manager.py`: `ContactsTab` (class ~342, `_build` ~349, `_refresh_tree` ~460,
  `_refresh_table` ~514, right-click menus ~490/549, dept/employee button handlers ~566–706),
  `EmployeeDialog` (~204, `_build` ~219, `_save` ~309).
- Tokens/factories from `app.py` are **not importable cleanly** without care — see Change 1.

## Changes

1. **Share the design tokens.** `contacts_manager.py` currently hardcodes its own colors (e.g. dept
   colors in `data/contacts.json`, inline widget colors). Import the palette from `app.py`:
   ```python
   from app import (BG_DARK, BG_MID, BG_CARD, ACCENT, ACCENT2, SUCCESS, WARNING, DANGER,
                    TEXT_PRI, TEXT_SEC, TEXT_DIM, WHITE, FONT_TITLE, FONT_HEAD, FONT_BODY,
                    FONT_SMALL, FONT_MONO, SP_2, SP_3, SP_4)
   ```
   ⚠️ Guard against a circular import: `app.py` does `from contacts_manager import ContactsDB,
   ContactsTab` at module top. Importing `app` names at the **top** of `contacts_manager.py` will
   deadlock. Instead import inside `__init__`/`_build` methods (local import), or move the shared
   tokens into a tiny new module `theme.py` that both files import. **Prefer creating `theme.py`**
   (move the color/font/spacing constants there, and have `app.py` do `from theme import *`). This is
   the clean fix and also helps the exporters later. If you create `theme.py`, update `app.py`'s token
   block to import from it and keep the names identical so nothing else breaks.

2. **Treeview.** Apply `style="Dark.Treeview"` (defined in task 02) to the contacts tree in
   `_build`/`_refresh_tree`. Remove any inline light backgrounds.

3. **Buttons.** Migrate the add/edit/delete/export/dept buttons to the same look as `app._btn`
   (accent/ghost/danger). Since `ContactsTab` isn't `LTTApp`, either add a small local `_btn` helper
   mirroring task 01's, or (if `theme.py` exists) a `make_button(parent, ...)` in `theme.py` both use.
   Delete = danger, export-to-system = accent, add = accent, others = ghost.

4. **EmployeeDialog.** Style the dialog to match: `bg=BG_DARK`, labels `TEXT_PRI` right-aligned, dark
   entries, factory buttons for save/cancel (save = accent rightmost). Keep the placeholder-hint
   behavior and all Arabic labels.

5. **RTL.** Right-align labels and headings; primary buttons rightmost; table column headings in
   Arabic stay as-is.

6. **Search box empty/placeholder** already exists (placeholder in/out handlers ~404) — just ensure
   its colors use tokens.

## Design rules

Global rules in `README.md`. The contacts tab must be visually indistinguishable in style from the
other five. Preserve all Arabic strings and the `ContactsDB` / `export_to_config` logic untouched.

## Acceptance criteria

- Contacts tab uses the dark palette throughout (tree, buttons, dialog) — no gray native widgets.
- No circular-import error on launch (`python app.py` starts clean).
- If `theme.py` was introduced, `app.py` and `contacts_manager.py` both import from it and all token
  names are unchanged elsewhere.
- Add/edit/delete an employee still works and still syncs via `export_to_config`.

## Out of scope

Exporter (`__init__.py`) restyling — out of scope for this UI pass (PDFs already have their own fixed
palette).
