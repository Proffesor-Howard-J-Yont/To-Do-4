"""
corkboard_freeform.py

Scrollable, freeform pin board.

Changes in this version:
- Pins distinguish a CLICK (opens the pin) from a DRAG (moves the pin) using
  a small movement threshold measured from mouse-down to mouse-up.
- The board's logical size is no longer grow-only. It's recalculated after
  every add/move/delete as: max(current viewport size, bounding box of all
  pins + margin). This means it can shrink back down once pins that were
  pushing the boundary out are deleted or dragged inward -- but an existing
  pin's position is NEVER changed by this recalculation. Only the boundary
  (and therefore how much can be scrolled) changes.
- Small directional arrow indicators float over the canvas (fixed to the
  screen, not the scrollable board) on any edge that currently has a pin
  positioned outside the visible viewport. Clicking one scrolls toward it.
"""

import math
import tkinter as tk
from ttkbootstrap import Frame, Scrollbar, Label

PIN_WIDTH = 240
PIN_HEIGHT = 140
PIN_MARGIN = 12
CLICK_MOVE_THRESHOLD = 6  # px of movement before a press+release counts as a drag, not a click


class FreeformCorkboard(Frame):
    def __init__(self, master, on_position_change=None, **kwargs):
        """
        on_position_change: callback(rowid, x, y), called on drag release.
        Per-pin on_click callbacks are supplied individually via add_pin().
        """
        super().__init__(master, **kwargs)
        self.on_position_change = on_position_change

        self.board_w = 0
        self.board_h = 0

        self.canvas = tk.Canvas(self, highlightthickness=0, background='#222222')
        self.vbar = Scrollbar(self, orient='vertical', command=self._yview)
        self.hbar = Scrollbar(self, orient='horizontal', command=self._xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.vbar.grid(row=0, column=1, sticky='ns')
        self.hbar.grid(row=1, column=0, sticky='ew')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # rowid -> {'frame','window_id','x','y','on_click'}
        self.pins = {}
        self._drag = {'rowid': None, 'start_x': 0, 'start_y': 0,
                       'orig_x': 0, 'orig_y': 0, 'moved': 0}

        self._arrows = {}  # side -> Label widget
        self._suppress_click = set()  # rowids whose next release shouldn't open the pin

        self.canvas.bind('<Configure>', lambda e: self._recompute_board_bounds())

    def suppress_click(self, rowid):
        """
        Call this from a child widget's own click handler (e.g. a hyperlink
        tag inside a pin's Text widget) BEFORE it does its own thing, so the
        pin-level on_click (open the pin) doesn't also fire for that same
        click. Consumed automatically on the next release for that pin.
        """
        self._suppress_click.add(rowid)

    # ---------------- scroll wrappers (so arrows refresh on manual scroll) ----------------

    def _yview(self, *args):
        self.canvas.yview(*args)
        self._update_edge_arrows()

    def _xview(self, *args):
        self.canvas.xview(*args)
        self._update_edge_arrows()

    # ---------------- board sizing ----------------

    def _recompute_board_bounds(self):
        viewport_w = self.canvas.winfo_width() or 800
        viewport_h = self.canvas.winfo_height() or 600
        max_x = viewport_w
        max_y = viewport_h
        for pin in self.pins.values():
            max_x = max(max_x, pin['x'] + PIN_WIDTH + PIN_MARGIN)
            max_y = max(max_y, pin['y'] + PIN_HEIGHT + PIN_MARGIN)
        self.board_w = max_x
        self.board_h = max_y
        self.canvas.configure(scrollregion=(0, 0, self.board_w, self.board_h))
        self._update_edge_arrows()

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
        step_x = PIN_WIDTH + PIN_MARGIN
        step_y = PIN_HEIGHT + PIN_MARGIN
        search_h = max(self.board_h, self.canvas.winfo_height() or 600)
        search_w = max(self.board_w, self.canvas.winfo_width() or 800)
        y = PIN_MARGIN
        while True:
            x = PIN_MARGIN
            while x + PIN_WIDTH <= search_w:
                if not self._overlaps(x, y, PIN_WIDTH, PIN_HEIGHT):
                    return x, y
                x += step_x
            y += step_y
            if y + PIN_HEIGHT > search_h * 4:  # generous safety cap, avoids any infinite loop
                return PIN_MARGIN, search_h + PIN_MARGIN

    def _resolve_slide(self, rowid, cur_x, cur_y, target_x, target_y):
        if not self._overlaps(target_x, target_y, PIN_WIDTH, PIN_HEIGHT, ignore_rowid=rowid):
            return target_x, target_y
        if not self._overlaps(target_x, cur_y, PIN_WIDTH, PIN_HEIGHT, ignore_rowid=rowid):
            return target_x, cur_y
        if not self._overlaps(cur_x, target_y, PIN_WIDTH, PIN_HEIGHT, ignore_rowid=rowid):
            return cur_x, target_y
        return cur_x, cur_y

    # ---------------- pin management ----------------

    def add_pin(self, rowid, build_frame_fn, x=None, y=None, on_click=None):
        if x is None or y is None:
            x, y = self._find_free_spot()

        frame = build_frame_fn(self.canvas)
        frame.configure(width=PIN_WIDTH, height=PIN_HEIGHT)
        window_id = self.canvas.create_window(
            x, y, anchor='nw', window=frame, width=PIN_WIDTH, height=PIN_HEIGHT
        )
        self.pins[rowid] = {'frame': frame, 'window_id': window_id, 'x': x, 'y': y,
                             'on_click': on_click}

        self._bind_drag(frame, rowid)
        self._recompute_board_bounds()
        return frame, x, y

    def remove_pin(self, rowid):
        pin = self.pins.pop(rowid, None)
        if pin:
            self.canvas.delete(pin['window_id'])
            self._recompute_board_bounds()

    def _bind_drag(self, widget, rowid):
        widget.bind('<ButtonPress-1>', lambda e: self._on_press(e, rowid))
        widget.bind('<B1-Motion>', lambda e: self._on_drag(e, rowid))
        widget.bind('<ButtonRelease-1>', lambda e: self._on_release(e, rowid))
        for child in widget.winfo_children():
            self._bind_drag(child, rowid)

    def _on_press(self, event, rowid):
        pin = self.pins[rowid]
        self._drag['rowid'] = rowid
        self._drag['start_x'] = event.x_root
        self._drag['start_y'] = event.y_root
        self._drag['orig_x'] = pin['x']
        self._drag['orig_y'] = pin['y']
        self._drag['moved'] = 0
        self.canvas.tag_raise(pin['window_id'])

    def _on_drag(self, event, rowid):
        pin = self.pins[rowid]
        dx = event.x_root - self._drag['start_x']
        dy = event.y_root - self._drag['start_y']
        self._drag['moved'] = max(self._drag['moved'], math.hypot(dx, dy))

        target_x = max(0, self._drag['orig_x'] + dx)
        target_y = max(0, self._drag['orig_y'] + dy)

        new_x, new_y = self._resolve_slide(rowid, pin['x'], pin['y'], target_x, target_y)
        pin['x'], pin['y'] = new_x, new_y
        self.canvas.coords(pin['window_id'], new_x, new_y)
        self._recompute_board_bounds()

    def _on_release(self, event, rowid):
        pin = self.pins.get(rowid)
        if not pin:
            return
        was_click = self._drag['moved'] < CLICK_MOVE_THRESHOLD
        self._drag['rowid'] = None

        if rowid in self._suppress_click:
            self._suppress_click.discard(rowid)
            return

        if was_click:
            if pin['on_click']:
                pin['on_click'](rowid)
        else:
            if self.on_position_change:
                self.on_position_change(rowid, pin['x'], pin['y'])

    # ---------------- off-screen edge arrows ----------------

    def _update_edge_arrows(self):
        if self.board_w == 0 or self.board_h == 0:
            return
        x0, x1 = self.canvas.xview()
        y0, y1 = self.canvas.yview()
        vis_left = x0 * self.board_w
        vis_right = x1 * self.board_w
        vis_top = y0 * self.board_h
        vis_bottom = y1 * self.board_h

        needed = {'up': False, 'down': False, 'left': False, 'right': False}
        for pin in self.pins.values():
            px, py = pin['x'], pin['y']
            if py + PIN_HEIGHT < vis_top:
                needed['up'] = True
            if py > vis_bottom:
                needed['down'] = True
            if px + PIN_WIDTH < vis_left:
                needed['left'] = True
            if px > vis_right:
                needed['right'] = True

        specs = {
            'up': ('\u25B2', dict(relx=0.5, rely=0.0, anchor='n')),
            'down': ('\u25BC', dict(relx=0.5, rely=1.0, anchor='s')),
            'left': ('\u25C0', dict(relx=0.0, rely=0.5, anchor='w')),
            'right': ('\u25B6', dict(relx=1.0, rely=0.5, anchor='e')),
        }
        for side, need in needed.items():
            if need and side not in self._arrows:
                symbol, place_kwargs = specs[side]
                lbl = Label(self, text=symbol, bootstyle='warning inverse', font=('Calibri', 16, 'bold'))
                lbl.place(**place_kwargs)
                lbl.bind('<Button-1>', lambda e, s=side: self._scroll_toward(s))
                self._arrows[side] = lbl
            elif not need and side in self._arrows:
                self._arrows[side].destroy()
                del self._arrows[side]

    def _scroll_toward(self, side):
        if side == 'up':
            self.canvas.yview_scroll(-1, 'pages')
        elif side == 'down':
            self.canvas.yview_scroll(1, 'pages')
        elif side == 'left':
            self.canvas.xview_scroll(-1, 'pages')
        elif side == 'right':
            self.canvas.xview_scroll(1, 'pages')
        self._update_edge_arrows()

    def clear(self):
        self.canvas.delete('all')
        self.pins = {}
        for lbl in self._arrows.values():
            lbl.destroy()
        self._arrows = {}