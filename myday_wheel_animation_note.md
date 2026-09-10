# My Day — Fluid TimeWheel Scrolling

Follow-up to `myday_time_wheel.py`. Read the current code as source of
truth — this is the one decision, not a restatement of the file.

## Problem

`TimeWheel._step()` (and `_redraw()`) instantly retextures the 5 visible
`create_text` items on every scroll notch / row click / confirmed typed
value. Functionally correct, but it reads as the label just changing
rather than the wheel actually scrolling.

## Decision

Animate the transition instead of snapping to it. On `_step(direction)`:
instead of calling `_redraw()` immediately, tween all 5 items' y-positions
by one `ITEM_HEIGHT_PX` in the scroll direction over roughly 120–150ms
(a short `tkinter.after`-driven animation loop with some ease-out is
plenty — doesn't need to be physically accurate), then snap to the final
resting position and call the existing `_redraw()`/relabeling logic to
settle into the new state. This is the *transition-animation* version, not
full continuous drag-with-momentum scrolling — mouse-wheel/trackpad notch
input doesn't really call for touch-drag inertia the way an actual iOS
wheel's drag gesture does, so don't build that; just make each discrete
step glide instead of jump.

Guard against notches arriving faster than the animation completes (rapid
scrolling) — either queue steps and play them in sequence, or let a new
step interrupt/restart the in-flight animation from wherever it currently
is, rather than stacking overlapping `.after()` calls that fight each
other. Either approach is fine; just pick one deliberately rather than
letting it happen by accident.

Typed-entry confirm (`_confirm_type`) and row clicks should get the same
animated treatment as scroll notches — anything that changes
`selected_index` should animate, not just wheel/trackpad input.

`set_index()` (programmatic prefill) should stay instant, no animation —
it's explicitly documented as not firing `on_change` for the same reason
(prefilling a popup shouldn't visibly "scroll" into place).

## Out of scope

No changes to validation, typed-parsing, the AM/PM toggle, or the popup's
save/date/all-day logic — this is purely the wheel's visual scroll
transition.
