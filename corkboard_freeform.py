"""
corkboard_freeform.py

A scrollable, freeform pin board for To-Do 4's Corkboard feature.

Design (agreed with user):
- Pins live at ABSOLUTE pixel coordinates in a fixed "board space" that is
  independent of the window/viewport size. Resizing the window (or moving to
  a smaller monitor) never moves a pin -- it only changes how much of the
  board is currently visible.
- The board starts at a default size and GROWS on demand (rightward/downward
  only) whenever a pin needs room that doesn't exist yet. It never shrinks.
  Top/left are hard boundaries (no negative coordinates).
- No zoom. Pins are always rendered at a fixed pixel size, so text never
  needs to be rescaled.
- Dragging a pin that would overlap a neighbor SLIDES along whichever axis
  is still free, rather than freezing dead or overlapping.
- Position is only ever changed by: (a) initial placement/backfill, or
  (b) the user dragging the pin. Nothing else touches it.

This module is intentionally decoupled from the rest of the app: it doesn't
know about sqlite, ttkbootstrap styles, or what a "pin" looks like. You pass
in a `build_frame_fn` per pin that builds whatever visual content you want,
and a callback that gets called (rowid, x, y) whenever a pin's position
changes and should be persisted.
"""

import tkinter as tk
from ttkbootstrap import Frame, Scrollbar

PIN_WIDTH = 240
PIN_HEIGHT = 140
PIN_MARGIN = 12          # min gap enforced between pins during collision checks
BOARD_DEFAULT_W = 2400
BOARD_DEFAULT_H = 1600
BOARD_GROW_STEP = 600    # how much extra room to add each time the board grows


class FreeformCorkboard(Frame):
    """
    Scrollable freeform board. Pins are widgets embedded in a tk.Canvas via
    create_window, positioned at absolute board-space coordinates.
    """

    def __init__(self, master, on_position_change=None, **kwargs):
        """
        on_position_change: callback(rowid, x, y) invoked on drag release,
        so the caller can persist the new position (e.g. to sqlite).
        """
        super().__init__(master, **kwargs)
        self.on_position_change = on_position_change

        self.board_w = BOARD_DEFAULT_W
        self.board_h = BOARD_DEFAULT_H

        self.canvas = tk.Canvas(self, highlightthickness=0, background='#222222')
        self.vbar = Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.hbar = Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.vbar.grid(row=0, column=1, sticky='ns')
        self.hbar.grid(row=1, column=0, sticky='ew')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas.configure(scrollregion=(0, 0, self.board_w, self.board_h))

        # rowid -> {'frame': Frame, 'window_id': int, 'x': int, 'y': int}
        self.pins = {}
        self._drag = {'rowid': None, 'start_x': 0, 'start_y': 0, 'orig_x': 0, 'orig_y': 0}

    # ---------------- board sizing ----------------

    def _grow_board(self, need_w=None, need_h=None):
        """Extend the board rightward/downward if the given need exceeds
        current bounds. Never shrinks, never touches existing pin positions."""
        grew = False
        if need_w is not None and need_w > self.board_w:
            self.board_w = need_w + BOARD_GROW_STEP
            grew = True
        if need_h is not None and need_h > self.board_h:
            self.board_h = need_h + BOARD_GROW_STEP
            grew = True
        if grew:
            self.canvas.configure(scrollregion=(0, 0, self.board_w, self.board_h))
        return grew

    # ---------------- collision ----------------

    def _overlaps(self, x, y, w, h, ignore_rowid=None):
        for rowid, pin in self.pins.items():
            if rowid == ignore_rowid:
                continue
            px, py = pin['x'], pin['y']
            if (x < px + PIN_WIDTH + PIN_MARGIN and x + w + PIN_MARGIN > px and
                    y < py + PIN_HEIGHT + PIN_MARGIN and y + h + PIN_MARGIN > py):
                return True
        return False

    def _find_free_spot(self):
        """Scan the board for the first non-overlapping spot (row-major).
        Grows the board downward if nothing is found."""
        step_x = PIN_WIDTH + PIN_MARGIN
        step_y = PIN_HEIGHT + PIN_MARGIN
        y = PIN_MARGIN
        while y + PIN_HEIGHT <= self.board_h:
            x = PIN_MARGIN
            while x + PIN_WIDTH <= self.board_w:
                if not self._overlaps(x, y, PIN_WIDTH, PIN_HEIGHT):
                    return x, y
                x += step_x
            y += step_y
        # board is full: grow downward and place there
        new_y = self.board_h + PIN_MARGIN
        self._grow_board(need_h=new_y + PIN_HEIGHT)
        return PIN_MARGIN, new_y

    def _resolve_slide(self, rowid, cur_x, cur_y, target_x, target_y):
        """
        Try the full diagonal move first; if blocked, try each axis alone,
        producing a "slide along the free axis" feel. If both axes are
        blocked, try growing the board in the blocked direction; only if
        that's not applicable (e.g. blocked by another pin, not an edge)
        does the pin stay put.
        """
        if not self._overlaps(target_x, target_y, PIN_WIDTH, PIN_HEIGHT, ignore_rowid=rowid):
            return target_x, target_y

        if not self._overlaps(target_x, cur_y, PIN_WIDTH, PIN_HEIGHT, ignore_rowid=rowid):
            return target_x, cur_y

        if not self._overlaps(cur_x, target_y, PIN_WIDTH, PIN_HEIGHT, ignore_rowid=rowid):
            return cur_x, target_y

        return cur_x, cur_y

    # ---------------- pin management ----------------

    def add_pin(self, rowid, build_frame_fn, x=None, y=None):
        """
        build_frame_fn(parent) -> Frame: builds the pin's visual content.
        x, y: pass explicit board-space coords (e.g. loaded from the DB) or
        leave None to auto-place in the first free spot (new pin / backfill).
        """
        if x is None or y is None:
            x, y = self._find_free_spot()

        frame = build_frame_fn(self.canvas)
        frame.configure(width=PIN_WIDTH, height=PIN_HEIGHT)
        window_id = self.canvas.create_window(
            x, y, anchor='nw', window=frame, width=PIN_WIDTH, height=PIN_HEIGHT
        )
        self.pins[rowid] = {'frame': frame, 'window_id': window_id, 'x': x, 'y': y}

        self._grow_board(need_w=x + PIN_WIDTH + PIN_MARGIN, need_h=y + PIN_HEIGHT + PIN_MARGIN)

        self._bind_drag(frame, rowid)
        return frame, x, y

    def _bind_drag(self, widget, rowid):
        widget.bind('<ButtonPress-1>', lambda e: self._on_press(e, rowid))
        widget.bind('<B1-Motion>', lambda e: self._on_drag(e, rowid))
        widget.bind('<ButtonRelease-1>', lambda e: self._on_release(e, rowid))
        # bind children too, so grabbing a label/title inside the pin also drags it
        for child in widget.winfo_children():
            self._bind_drag(child, rowid)

    def _on_press(self, event, rowid):
        pin = self.pins[rowid]
        self._drag['rowid'] = rowid
        self._drag['start_x'] = event.x_root
        self._drag['start_y'] = event.y_root
        self._drag['orig_x'] = pin['x']
        self._drag['orig_y'] = pin['y']
        self.canvas.tag_raise(pin['window_id'])

    def _on_drag(self, event, rowid):
        pin = self.pins[rowid]
        dx = event.x_root - self._drag['start_x']
        dy = event.y_root - self._drag['start_y']
        target_x = self._drag['orig_x'] + dx
        target_y = self._drag['orig_y'] + dy

        # hard boundary: no negative coordinates (top/left out of scope for growth)
        target_x = max(0, target_x)
        target_y = max(0, target_y)

        new_x, new_y = self._resolve_slide(rowid, pin['x'], pin['y'], target_x, target_y)

        pin['x'], pin['y'] = new_x, new_y
        self.canvas.coords(pin['window_id'], new_x, new_y)

        self._grow_board(
            need_w=new_x + PIN_WIDTH + PIN_MARGIN,
            need_h=new_y + PIN_HEIGHT + PIN_MARGIN,
        )

    def _on_release(self, event, rowid):
        pin = self.pins.get(rowid)
        self._drag['rowid'] = None
        if pin and self.on_position_change:
            self.on_position_change(rowid, pin['x'], pin['y'])

    def clear(self):
        """Wipe all pins (call before rebuilding the board, e.g. on refresh)."""
        self.canvas.delete('all')
        self.pins = {}