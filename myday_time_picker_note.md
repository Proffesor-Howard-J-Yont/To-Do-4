# My Day — Time Picker for Scheduling

Follow-up to the previous two My Day notes. Scoped fix to `_open_change_time_popup`
(and anywhere else in `main.py`/`myday_weekview.py` that lets a user set
`schedule_start`/`schedule_duration` by hand) — read the current code as
source of truth, this is decisions only.

## Problem

`_open_change_time_popup` currently asks the user to type a raw `HHMM`
string for start time and a raw number of minutes for duration. Not
usable — nobody thinks in "1430" or "duration: 90".

## Decision

Replace both free-text entries with two **scrolling wheel pickers**
(iOS-style) — one for start time, one for end time (not duration — duration
is computed, never entered directly). Each of the two pickers pairs its
wheel with its own AM/PM toggle (see mechanics below). Each wheel also
supports clicking in and typing a time directly as a fallback to scrolling.

**Wheel mechanics (two independent pickers — start and end, each identical in structure):**
- Each picker is a **12-hour wheel** (times in `DRAG_SNAP_MIN`-minute
  increments, so 48 entries: 12:00, 12:15, 12:30, ... 11:45) paired with its
  own separate **AM/PM toggle** next to it — not one combined 96-entry
  list covering the full day. The wheel cycles/wraps within the 12-hour
  range; the toggle picks which half of the day it means. This mirrors how
  iOS's native time picker splits the value into independent wheel(s) +
  meridiem control rather than one long list.
- Labels show just the time, no AM/PM suffix, since the toggle carries that
  ("9:00", "9:15", ...) — the toggle is the single source of truth for
  AM/PM, don't duplicate it into the wheel's own labels.
- The value vertically centered in the wheel's visible window is the
  selected one; scrolling (mouse wheel / trackpad, same
  `wheel.has_touchpad_scroll()` handling already used for the timeline
  canvas) snaps to the nearest entry and centers it, similar in spirit to
  the existing timeline's scroll/snap handling — that code is a reasonable
  starting reference for the scroll-and-snap feel, though this is a much
  shorter, single-column list rather than a 24-hour canvas.
- A `tk.Canvas` or a tall `Listbox`/`Frame`-of-labels inside a scrollable
  container both work; pick whichever is less code given the rest of the
  file already leans on `tk.Canvas` for the timeline — consistency isn't
  required here since this is a small, self-contained popup widget.

**Typed entry fallback:**
- Clicking directly on the centered/selected value (or a dedicated small
  "type instead" affordance) swaps it to an editable text entry pre-filled
  with the current selection, accepting flexible input (e.g. "2pm", "2:00
  PM", "1400") — parse leniently rather than demanding one exact format.
  If the typed value includes AM/PM (explicitly or implied, e.g. "1400"
  implies PM), update the toggle to match; if it's ambiguous (e.g. just
  "2:00" with the toggle already showing a state), leave the toggle as-is
  and only update the wheel's hour/minute. On confirm (Enter / blur), snap
  the typed value to the nearest `DRAG_SNAP_MIN` increment and update the
  wheel to reflect it, then revert to wheel display. Invalid input should
  not crash the popup — just ignore it and keep the previous value.

**Save behavior (unchanged from before):**
- Validate end time is after start time (reject/flag otherwise — don't
  silently allow a negative or zero duration).
- Compute `schedule_duration` as the difference in minutes between the two
  picks, and convert the start pick back to the existing `HHMM` storage
  format. **Storage format is unchanged** — `schedule_start` stays
  zero-padded `HHMM` text, `schedule_duration` stays integer minutes. This
  is purely a UI-input change; nothing downstream
  (`_layout_timed_blocks`, `_query_scheduled_tasks_for_date`, drag
  handlers) needs to change.
- Same treatment applies to the all-day date-only case (a task scheduled
  with no time) — that path shouldn't be affected, it still just sets
  `schedule_date` with start/duration left empty. The picker only appears
  when the user is setting a *timed* block, not an all-day one. (Check how
  the current popup handles that case — if it always shows start/duration
  fields, this is a good point to also add whatever toggle/omission logic
  makes "all-day, no specific time" a clean, obvious option rather than
  something achieved by leaving fields blank.)

## Error handling: end time before (or equal to) start time

- Validate live, not just on save — as soon as both wheels have a value,
  compare them on every change to either picker (wheel scroll, toggle
  flip, or typed entry) rather than only checking when Save is clicked.
- If end ≤ start: show an inline message near the pickers (e.g. "End time
  must be after start time") and disable the Save button — don't let the
  popup submit an invalid pair at all. Equal times count as invalid too
  (zero-duration blocks aren't meaningful here).
- Don't silently auto-correct (e.g. snapping the end time forward, or
  wrapping to "next day") — this schema has no concept of a block crossing
  midnight (`schedule_date` is a single day, `schedule_duration` is a
  plain minute count relative to `schedule_start` within that day), so an
  end time before start is simply invalid input, not a same-day-wraparound
  case to be cleverly resolved. Surface the error and let the user fix it.
- Once corrected (end > start), clear the message and re-enable Save
  automatically — don't require closing/reopening the popup.
- This replaces the earlier "reject/flag" note from the previous revision
  of this doc — same intent, just spelled out concretely now.

## Second instance: the task detail view (embedded, not popup)

There are two independent implementations of schedule-editing right now,
not one:

1. My Day's `_open_change_time_popup` (`myday_weekview.py`) — already opens
   as a `tk.Toplevel`. Structurally fine as-is; just needs the wheel-picker
   treatment described above instead of its current raw entries.
2. The task detail view's Schedule section (`main.py`, `allfnctnsF_status`,
   ~lines 1991–2020) — a `DateEntry` plus two plain `Entry` fields
   (placeholder text `'HHMM'` / `'mins'`) built **embedded directly into
   the persistent task-detail panel**, not popped up. Same underlying
   raw-entry problem as My Day's old popup, plus the added issue that it's
   permanently embedded rather than opened on demand.

**Fix both, and don't build the wheel picker twice.** Extract it into one
shared component (a function/class both `myday_weekview.py` and `main.py`
can call) so there's a single implementation to maintain, not two that
drift apart. The task detail view's Schedule section should become a
button (e.g. "Set schedule..." / "Change time...") that opens the shared
picker as a `tk.Toplevel`, the same way My Day's already does — not fields
sitting permanently in the panel.

**General rule going forward**: wherever a task's schedule becomes
editable — now or in any future addition — it opens as a modal popup
triggered by an explicit action (button/click), never as fields embedded
directly into a panel that's always on screen. If another such spot turns
up during this work that isn't listed here, apply the same rule to it too.

## Out of scope

No schema changes. No changes to drag-and-drop scheduling (dragging onto
the timeline is already a fine interaction and isn't what's broken here) —
this is specifically about the manual "change time" entry path.
