# Task 04 — Input tab: RTL layout, empty state, factories, validation

## Files & anchors

- `app.py`: `_build_input_tab` (~lines 441–564), plus its helpers `_add_report` (~994),
  `_refresh_reports_list` (~1102), `_view_report` (~1060).

## Current state

Two-column layout built with `pack(side="left")`: **left** = reports `Listbox` + view/delete buttons;
**right** = the add-report form (source/dept comboboxes, from entry + contact picker, date entry,
content `ScrolledText`, action buttons, an info bar). Everything hand-built with inline colors; no
empty state on the list; combobox values mix emoji source labels with raw dept keys.

## Changes

1. **Mirror for RTL.** The reports list is the reference/primary column for an Arabic reader → move it
   to the **right** (`side="right"`), form to the **left**. Right-align section headings and field
   labels (`anchor="e"`). Order each button row so the primary action is **rightmost**.

2. **Empty state for the reports list.** When `self.reports` is empty, show a centered dim hint inside
   the list frame instead of a blank `Listbox`: e.g. `لا توجد تقارير بعد — أضِف تقريراً أو فعّل
   البريد/ERP في الإعدادات`. Implement by toggling a placeholder `tk.Label` over the list frame in
   `_refresh_reports_list` when the count is 0.

3. **Factory migration.** Replace the hand-built `tk.Button`s (add / import PDF / load samples / view /
   delete) with `self._btn(..., kind=...)`: add = accent, load samples = ghost, delete = danger, view =
   ghost. Wrap the form field rows to reuse `_setting_row` where the shape matches (label + entry).

4. **Dept combobox readability.** The dept combobox currently shows raw keys (`ran`, `cost`, …). Show
   an Arabic display label while keeping the key as the stored value — build a
   `(key → arabic_label)` map and set the combobox `values` to the labels, translating back to the key
   on `_add_report`. Do **not** change the underlying dept-key vocabulary.

5. **Validation on add.** In `_add_report`, if the content box is empty or no dept is chosen, show a
   clear Arabic `messagebox.showwarning` and don't append. Keep existing behavior otherwise.

6. **Info bar → count uses `FONT_MONO`** for the number.

## Design rules

Global rules in `README.md`. RTL is the headline of this task — verify the eye lands on the reports
list first (right side). No new hex outside tokens.

## Acceptance criteria

- Reports list sits on the right, form on the left; headings/labels right-aligned.
- Empty list shows the Arabic hint; adding a report replaces it with the list.
- Add/import/samples/view/delete are `_btn` factory buttons with hover; primary action is rightmost.
- Dept dropdown shows Arabic labels; a report added via the form still stores the correct dept **key**
  (verify the saved report's `dept` matches the old vocabulary).
- Submitting an empty form warns instead of adding a blank report.

## Out of scope

Analysis/agent visuals (task 05), dashboard (06).
