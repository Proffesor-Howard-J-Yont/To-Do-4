# My Day — Design Note

**Context for whoever (whichever Claude) picks this up:** this is a design spec
distilled from a long brainstorm about the "My Day" feature in the To-Do 4 app
(inspired by the Structured app's day/week view). No code has been written
against this final spec yet — a rougher prototype exists (`myday_weekview.py`,
described below) but the design direction changed significantly after it was
built, so treat the prototype as a UI-mechanics reference, not the target
architecture. Read this whole note before touching code; several early ideas
in the prototype were explicitly reversed later in the brainstorm.

---

## 1. Where this started, and where it ended up

The initial idea was: My Day shows "everything due today," pulled from the
existing `duedateday`/`duedatetime`/`duedateonoff` columns every list table
already has, with a day-strip navigator on top (see `myday_weekview.py`).

Through the brainstorm, this shifted hard: **My Day is moving away from due
date entirely and toward explicit scheduling.** Due date answers "when does
this need to be done by." Scheduling answers "when do I plan to actually work
on this." Those are different questions, they don't have to have the same
answer, and conflating them is what made the original design fuzzy. This note
describes the scheduling-based version.

---

## 2. What already exists (don't break this)

**Due date is a real, independent subsystem elsewhere in the app.** It is
NOT being removed. It has its own home:

- Every list's task table has `duedateday`, `duedatetime`, `duedateonoff`
  columns (see `td4_sqlite_processes.py` / `add_list`'s `CREATE TABLE`).
- `duedatetime` is currently a dead field in practice — every insert path
  hardcodes it to `'1200'` and there is no UI anywhere that lets a user
  actually set it. Don't assume it's a working "due time" feature; it isn't,
  yet. (Whether it's worth reviving for due-date purposes is out of scope for
  this note — My Day will not use it either way.)
- There's a per-task on/off toggle for whether a task has a due date at all
  (`duedateonoff_fun` in `main.py`, around line 1782).
- There's a global default setting for whether new tasks get a due date
  (`def_duedateonoff` setting, editable in the settings screen).
- There's a dedicated **"Due Today" sidebar button** (`smart_duetoday()` in
  `main.py`, ~line 2521) that queries `duedateday = today AND duedateonoff =
  'on'` across every list table and shows a smart-list view. This is a
  completely separate feature from My Day and must keep working exactly as it
  does now.

**Conclusion: due date keeps its existing role everywhere it currently has
one. My Day is simply going to stop consulting it.** This is a scoping
decision, not a deprecation of due dates app-wide.

---

## 3. The prototype that already exists

`myday_weekview.py` contains a `WeekView` class: a 7-day strip navigator
(prev/next/today arrows, day cells) plus a task list below driven by
`duedateday`. It was built and iterated on before the due-date-vs-scheduling
distinction became clear, so **its data source (querying by `duedateday`) is
now the wrong model** — the day-strip navigation UI/UX itself may still be
useful conceptually (browsing which day you're looking at), but what it
displays underneath needs to change to scheduling-driven content per this
spec, not due-date-driven content.

A few hard-won technical gotchas from building it, worth knowing before
touching this code again so they don't get reintroduced:

- **Don't destroy-and-rebuild `ttkbootstrap` widgets that use `outline` or
  rounded bootstyles on every navigation/re-render.** `ttkbootstrap`
  generates a `PhotoImage` per such style that's tied to the Python widget's
  lifetime. Destroying and recreating these widgets repeatedly (e.g. on every
  date change) eventually garbage-collects an image a shared style still
  references, crashing with `_tkinter.TclError: image "pyimageNN" does not
  exist`. The fix used in the prototype: render the day-strip cells as plain
  `tkinter.Frame`/`tkinter.Label` (no ttk styling, no images at all), pulling
  colors live from `ttkbootstrap.style.Style().colors` (`.info`, `.warning`,
  `.secondary`, `.bg`, `.fg`, `.selectfg`) so it still tracks the active theme
  without touching ttk's image-based styling engine.
- **This version of `ttkbootstrap`'s `Button` does not accept a `font=`
  constructor kwarg** — it raises `_tkinter.TclError: unknown option "-font"`.
  If a ttk/bootstrap button's font needs to be forced, configure it on the
  resolved ttk style name via `ttk.Style().configure(widget.cget('style'),
  font=(...))` instead — though note this affects every widget sharing that
  style name app-wide, so it's a blunt instrument; prefer plain `tk` widgets
  (as above) wherever the content is rebuilt frequently.
- **A container can't mix `pack` and `grid` for its children.** To make the
  day-strip row stretch to fill the window width, all children of that row's
  frame were switched to `grid` with the day-cell columns given
  `weight=1` and the nav buttons given `weight=0`, with a fixed
  `grid_rowconfigure(..., minsize=...)` to keep height stable while width
  scales with the window.
- **Claude (the AI) does not have write access to this repo from claude.ai
  chat** — only a read-only snapshot. Every file handed over in that context
  was a manual copy-paste, which is exactly the kind of friction this note
  and the switch to Claude Code is meant to fix. If you're Claude Code reading
  this: you have real filesystem access, use it directly.

---

## 4. Target design

### 4.1 Core principle

**My Day shows your plan for today. Nothing more.** It is not "everything
relevant to today" (that was the old, rejected design). If something hasn't
been explicitly scheduled, it does not appear in My Day, full stop — no
due-date matching, no implicit inclusion of incomplete tasks.

### 4.2 New data model — fully independent of due date

Add three new nullable columns to the task schema (every list's table),
following the existing migration pattern in `td4_sqlite_processes.py` (see
`migrate_corkboard_schema` for the `ALTER TABLE ... ADD COLUMN` style used
elsewhere — apply the same idea to task tables):

| Column              | Type | Meaning                                                   |
|---------------------|------|-------------------------------------------------------------|
| `schedule_date`     | TEXT | The date the task is planned for. Independent of `duedateday`. Null/empty = not scheduled. |
| `schedule_start`    | TEXT | Start time of the block, if timed. Null/empty = all-day.  |
| `schedule_duration` | TEXT | Length of the block (e.g. minutes), if timed. Null/empty = all-day. |

Important: since a task can be scheduled for today with **no** due date, due
**before** today, due **after** today, or due today but scheduled for a
different day entirely — `schedule_date` must be its own field, never derived
from or written alongside `duedateday`. These two concepts must be able to
diverge freely.

A task is "on today's schedule" iff `schedule_date == today`. That's the
entire query My Day needs — no join against due-date fields.

### 4.3 Rendering rules for a scheduled task

- `schedule_date` set, `schedule_start` **and** `schedule_duration` both set
  → render as a timed block on the timeline at that slot/length.
- `schedule_date` set, `schedule_start`/`schedule_duration` empty → render as
  an **all-day banner** above the timeline (same idea as the all-day row in
  Google/Apple Calendar sitting above the hourly grid).
- `schedule_date` not set → does not appear in My Day at all.

### 4.4 Suggestions panel

A separate panel/area (off to the side of the main My Day view) proposes
candidates worth scheduling. This is the on-ramp into My Day — since nothing
appears there automatically, suggestions are how a user discovers what to
add.

**Trigger logic, decided scope for the initial build: starred tasks that are
not yet scheduled (`schedule_date` empty).** That's it for now. Each
suggestion gets a one-tap "add to My Day" action that sets `schedule_date`
(and optionally prompts for a time) right there, without navigating away.

**Explicitly deferred, do not build yet** (flagged during the brainstorm as
worth doing later, but risky to bundle into this same change since it adds
heuristic complexity on top of a data model that's still new):
- Due-today / overdue tasks also feeding the suggestions panel.
- "Staleness" — a task unscheduled for N days in a row surfacing as a nudge.

Leave a clear extension point (e.g. a single function that returns the
candidate list) so these can be added later without restructuring the panel.

### 4.5 Due-date badge (open, low priority)

Floated but not firmly decided: a scheduled block could optionally show a
small due-date badge in the corner if that task also happens to have a due
date set — purely informational, not used to decide what appears in My Day.
Leaning toward this being unnecessary/going away entirely. Not blocking —
build without it first, add only if it turns out to be missed.

---

## 5. Explicitly rejected approaches (don't reintroduce these)

For context on why the design landed here, three earlier framings were
considered and rejected:

1. **"Full integration"** — folding scheduling into the existing due-date
   fields/editor, making duration an extension of `duedatetime`. Rejected
   because due date and "when I plan to work on it" are genuinely different
   questions with different answers, and reusing the same fields would make
   them impossible to diverge (e.g. a task due Friday you want to work on
   Tuesday).
2. **"Due-today drives My Day"** — the original prototype's model. Rejected
   because it's not what the user actually wants to plan around; a task
   being due today doesn't mean they've decided when to work on it today.
3. **"Unscheduled tray of everything"** — a catch-all tray showing every
   incomplete task until manually scheduled. Rejected as too noisy; replaced
   by the suggestions panel (starred-only, curated) plus the principle that
   My Day only shows what's actually been scheduled.

---

## 6. Suggested build order

1. Schema migration: add `schedule_date`, `schedule_start`,
   `schedule_duration` to task tables (nullable, safe no-op if already
   present — mirror `migrate_corkboard_schema`'s pattern).
2. Query layer: a function to fetch all tasks across all lists where
   `schedule_date == <given date>`, split into timed vs. all-day.
3. My Day layout: all-day banner area + timeline area, rendering from the
   query above. (Decide separately whether to keep/adapt the existing
   day-strip navigator from `myday_weekview.py` for browsing which day is
   shown — the navigation UI is likely still fine, only the underlying query
   needs to change from due-date-based to schedule-based.)
4. A minimal "schedule this" control (time + duration pickers) — start
   simple (e.g. text/dropdown entry), defer drag-and-drop/resize on the
   timeline to a later pass.
5. Suggestions panel: starred + `schedule_date` empty, with one-tap add.
6. Leave due-date logic (sidebar Due Today, per-task toggle, default
   setting) completely untouched throughout.
