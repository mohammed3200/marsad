# Task 05 — Agent telemetry: live per-agent card states

The 11 agent cards on the Analysis tab are currently **static decoration** — nothing updates them
during a run; only the aggregate progress bar moves. This task wires them to real per-agent state
(idle → running → done → error), the second half of the "instrument panel" signature.

## Files & anchors

- `app.py`: `_build_analysis_tab` agent grid (~lines 579–599), `_reset_agent_cards` (~1171),
  `_run_analysis` (~1123) and its `worker()` (~1141), `_update_progress` (~1165).
- `app.py`: `class AgentsEngine.run_all` (~272) and `run_agent` (~263) — needs a new per-agent
  callback param.

## Current state

`self._agent_cards[aid] = {"frame": card, "status": st}` built once. `run_all(reports, progress_cb)`
loops `WORKER_AGENTS` then runs `chief`, calling only `progress_cb(pct)`. No per-agent signal reaches
the UI.

## Changes

1. **Add a per-agent callback to the engine.** Extend `run_all(self, reports, progress_cb=None,
   agent_cb=None)`. Around each agent:
   ```python
   if agent_cb: agent_cb(ag_id, "running")
   result = self.run_agent(ag_id, text)
   if agent_cb: agent_cb(ag_id, "error" if "error" in result else "done")
   ```
   Do the same for the `chief` agent (running before, done/error after). Keep `progress_cb` behavior.

2. **Add `_set_agent_state(self, aid, state)`** on `LTTApp`, marshalled to the UI thread:
   ```python
   def _set_agent_state(self, aid, state):
       card = self._agent_cards.get(aid)
       if not card: return
       spec = {
           "idle":    ("⏸", TEXT_DIM,  BG_MID),
           "running": ("⏳", ACCENT2,   ACCENT),
           "done":    ("✓",  SUCCESS,   SUCCESS),
           "error":   ("✗",  DANGER,    DANGER),
       }[state]
       glyph, fg, border = spec
       self.after(0, lambda: (
           card["status"].config(text=glyph, fg=fg),
           card["frame"].config(highlightbackground=border),
       ))
   ```

3. **Pass it through.** In `_run_analysis`'s `worker()`, call
   `self.agents.run_all(self.reports, progress_cb=self._update_progress, agent_cb=self._set_agent_state)`.

4. **Reset** in `_reset_agent_cards`: set every card to the `idle` spec (reuse `_set_agent_state(aid,
   "idle")` or inline the same values) so a re-run clears prior ✓/✗.

5. **Status pills on the run row.** Replace the plain `self._status_run` text with a `_pill`-style
   indicator during the run: show `⏳ جاري التحليل` (accent) while running, `✓ اكتمل` (success) on done,
   `✗ فشل` (danger) on error. (Use the pill factory or match its look.)

6. **Log readability.** Keep the log box, but ensure the running/done lines already emitted by the
   engine remain — this task adds the visual card layer on top, it does not remove the log.

## Design rules

Global rules in `README.md`. The card state colors reuse the semantic tokens. The `⏳`→`✓` change is
the only motion. Card icons/labels/Arabic unchanged.

## Acceptance criteria

- Running an analysis makes each card visibly transition: idle `⏸`(dim) → running `⏳`(accent border)
  → done `✓`(green border), left-to-right through ops…chief; a failing agent shows `✗`(red).
- A second run resets all cards to idle first.
- The run-status indicator reads `⏳ جاري التحليل` then `✓ اكتمل` (or `✗ فشل`).
- Engine still saves `reports/results_*.json` + `latest.json` and the dashboard still refreshes.

## Verification note

Test with the locally-installed Ollama model (`metatron-qwen:latest`) or point `settings.json`
`ollama_model` at whatever `ollama list` shows. A model must respond for `done` states to appear.

## Out of scope

Dashboard tile formatting (task 06).
