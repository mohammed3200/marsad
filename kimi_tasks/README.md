# Kimi task specs — marsad UI/UX polish

These are self-contained work orders for the **Kimi CLI** to execute, one at a time, **in numeric
order**. Each file has: Goal, Files & anchors, Changes, Design rules, Acceptance criteria, Out of
scope. Run them in order because later tasks depend on the token system and factories added in 01.

## Workflow

1. Open the lowest-numbered unchecked task in `PROGRESS.md`.
2. Feed that single `.md` file to Kimi as the task. Do **not** batch multiple specs into one run.
3. When Kimi finishes, run the app (`python app.py`) and check the task's **Acceptance criteria**.
4. Tick it in `PROGRESS.md`, commit, move to the next.

## Project facts Kimi must respect

- Single-file GUI: `app.py` (class `LTTApp`, ~1500 lines). Exporters in `__init__.py`. Connectors in
  `connectors.py`. Contacts UI in `contacts_manager.py`.
- The app is **Arabic / RTL**. Preserve every Arabic string verbatim; never translate or reorder the
  characters inside a string literal.
- The `results` dict (keys `chief`, `risk`, `cost`, `schedule`, `quality`, `safety`, …) is the data
  contract. Status **values are fixed Arabic literals** and drive color everywhere:
  health `جيد`/`متوسط`/`حرج`, risk `عالية`/`متوسطة`/`منخفضة`, KPI status `جيد`/`تحذير`/`حرج`,
  phase `مكتمل`/`متأخر`/(else in-progress), safety `آمن`/`خطر`. Branch on these exact strings.
- Do not change agent prompts, JSON schemas, connector logic, or export logic. This is a **UI pass**.

## Global design rules (apply to every task)

- **Keep the committed dark "operations console" identity.** Palette lives at `app.py` lines ~86–104
  (`BG_DARK #0D1B2A`, `BG_MID #1E3A5F`, `BG_CARD #162032`, `ACCENT #2563EB`, `ACCENT2 #38BDF8`,
  `SUCCESS/WARNING/DANGER`, `TEXT_PRI/SEC/DIM`). Do not introduce a new palette or new one-off hex
  values in widget calls — pull from tokens (task 01 centralizes them).
- **Numbers use the monospace font** (`FONT_MONO`) — KPI values, counts, percentages, budgets, delay
  days. Arabic labels stay Arial.
- **Contrast:** body text ≥ 4.5:1 on its background. Never put `TEXT_DIM` on `BG_CARD` for anything a
  user must read; `TEXT_DIM` is for disabled/idle only.
- **No gratuitous motion.** Tkinter can't animate smoothly. The only allowed "motion" is discrete
  state changes (beacon color, agent-card state, a `⏳` glyph while running).
- **Every list/panel gets an empty state** — a short Arabic hint when there's no data yet, not a bare
  empty box.
- **RTL:** right-align label text (`anchor="e"`, `justify="right"`); mirror two-column layouts so the
  primary column sits on the **right**; order button rows so the primary action is rightmost.
  **Note (verified by screenshot):** Tk on this system already shapes and orders Arabic glyphs
  correctly inside labels — RTL here is about *layout direction* (which side columns/buttons sit on),
  **not** character reshaping. Do **not** blanket-apply the `rtl()` helper; only reach for it if a
  specific widget visibly renders Arabic backwards, which is rare.
- Reuse the factories from task 01 (`_pill`, `_card`, `_kpi_tile`, `_btn`) instead of hand-building
  styled `tk.Button`/`tk.Label`/`tk.Frame` with inline `bg=/fg=/font=`.

## Review contract (Claude checks each diff for)

- No Arabic string altered; no data-contract literal changed.
- No new raw hex outside the token block; factories used.
- App launches with no traceback and the task's acceptance criteria pass.
