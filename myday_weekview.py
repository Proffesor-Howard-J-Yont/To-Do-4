"""
myday_weekview.py

The "My Day" screen -- a horizontal week-strip date picker (inspired by
Structured's week view) showing the user's explicit *plan* for the
selected day: timed tasks on an hourly timeline, and date-only tasks as
all-day banners above it. This is driven entirely by the schedule_date /
schedule_start / schedule_duration columns, which are independent of due
date (duedateday/duedatetime/duedateonoff) -- a task can be scheduled for
today with no due date, due before/after today, or due today but
scheduled for a different day entirely. Nothing appears here unless it
has been explicitly scheduled; there is no due-date matching.

Kept as its own module (same pattern as corkboard_freeform /
corkboard_rich_text) so main.py just has to import WeekView and drop it
into my_day_launch(). It manages its own DB reads/writes for checking
tasks off and for scheduling suggestions, and calls back into main.py for
anything it needs (getting a list's display name, refreshing the sidebar
counts).

Design notes:
- No hardcoded colors -- everything uses ttkbootstrap bootstyles/live
  theme colors so it follows whichever theme the app is running (darkly
  by default), same as the rest of the app.
- Today is marked with a yellow border even when it's not the selected
  day, so you never lose track of "where you are" while browsing other
  days. The day-strip cells are plain tkinter widgets (colored from the
  live ttkbootstrap theme palette) rather than ttk/bootstyle widgets,
  since they get destroyed and rebuilt on every date change and
  ttkbootstrap's outline styles carry per-widget images that don't
  survive that cycle. The same caution applies to the timeline blocks and
  all-day banners below, since those are rebuilt at least as often.
- schedule_start is stored as zero-padded 24-hour 'HHMM' text and
  schedule_duration as plain integer minutes -- both written by main.py's
  per-task Schedule control. A task is "timed" iff both are set; if only
  schedule_date is set, it's "all-day".
"""

import sqlite3
import tkinter as tk
from datetime import date, timedelta
from ttkbootstrap import Frame, Label, Button, ScrolledFrame, Separator, Scrollbar
from ttkbootstrap.style import Style as BSStyle
from ttkbootstrap.internal import wheel
from ttkbootstrap.dialogs import Querybox
from myday_time_wheel import open_schedule_popup

DAY_STRIP_SPAN = 3  # days shown on either side of the selected date (3 -> 7-day strip)
CELL_HEIGHT_PX = 50
HOUR_HEIGHT_PX = 60  # 1 pixel == 1 minute, so duration math is a direct pixel count
TIMELINE_LABEL_WIDTH = 55
TIMELINE_BLOCK_WIDTH = 420
TIMELINE_WIDTH = TIMELINE_LABEL_WIDTH + TIMELINE_BLOCK_WIDTH
DEFAULT_TIMED_DURATION_MIN = 60  # used when an all-day task is dragged into the timeline
DRAG_SNAP_MIN = 15
AUTOSCROLL_MARGIN_PX = 30  # how close to the canvas top/bottom edge triggers auto-scroll
AUTOSCROLL_STEP_UNITS = 12  # px per auto-scroll tick (yscrollincrement=1, so this is pixels)
AUTOSCROLL_INTERVAL_MS = 30

# Fixed positions in a `SELECT rowid, *` row tuple for the columns added by
# migrations after the original 11-column task schema. Deliberately
# absolute (not row[-N]) so adding another trailing column later (as
# block_color itself just was, after schedule_duration) can never silently
# shift these -- row[-1] meant schedule_duration before block_color
# existed and would silently mean something else after, without every
# read site erroring, just quietly reading the wrong field.
IDX_SCHEDULE_DATE = 12
IDX_SCHEDULE_START = 13
IDX_SCHEDULE_DURATION = 14
IDX_BLOCK_COLOR = 15

PRESET_BLOCK_COLORS = [
    '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#1abc9c',
    '#3498db', '#9b59b6', '#e84393', '#7f8c8d', '#34495e',
]


def _row_get(row, index, default=''):
    return row[index] if len(row) > index else default


def _readable_text_color(hex_color):
    """Picks black or white text for legibility against an arbitrary
    custom block_color -- unlike the theme's finite color tokens (already
    paired with colors.selectfg by the theme itself), a user-chosen hex
    color could be anywhere on the brightness spectrum."""
    try:
        h = hex_color.lstrip('#')
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError, AttributeError):
        return '#ffffff'
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#000000' if luminance > 0.6 else '#ffffff'


def _iter_task_tables(cursor):
    """Yields hidden table names for every task table, skipping
    sqlite_sequence. Shared by every My Day query so the sqlite_master
    enumeration + guard isn't duplicated three times."""
    cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
    for table in cursor.fetchall():
        name = table[1]
        if name == 'sqlite_sequence':
            continue
        yield name


def _query_scheduled_tasks_for_date(selected_date):
    """Returns (timed, allday) -- each a list of (row, list_hidden_name)
    pairs -- for every task across every list whose schedule_date matches
    selected_date. row = (rowid, task, checked, starred, difficulty,
    duedateday, duedatetime, duedateonoff, amiaministep, whichminiami,
    importance, notes, schedule_date, schedule_start, schedule_duration).
    No due-date filtering at all -- schedule_date is the only criterion."""
    target = selected_date.strftime('%x')
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    timed, allday = [], []
    for table_name in _iter_task_tables(c):
        try:
            c.execute(
                "SELECT rowid, * FROM '{}' WHERE schedule_date=? AND amiaministep='no'".format(table_name),
                (target,)
            )
        except sqlite3.OperationalError:
            continue
        for row in c.fetchall():
            sched_start, sched_duration = _row_get(row, IDX_SCHEDULE_START), _row_get(row, IDX_SCHEDULE_DURATION)
            if sched_start and sched_duration:
                timed.append((row, table_name))
            else:
                allday.append((row, table_name))
    conn.close()
    timed.sort(key=lambda pair: _row_get(pair[0], IDX_SCHEDULE_START))  # zero-padded 'HHMM' sorts correctly as text
    return timed, allday


def get_myday_suggestions():
    """Extension point (design note 4.4): candidates worth scheduling.
    Initial scope: starred, unchecked, not-a-ministep, and not yet
    scheduled. Add due-today/overdue/staleness heuristics later by
    extending only this function -- the panel UI never needs to change."""
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    results = []
    for table_name in _iter_task_tables(c):
        try:
            c.execute(
                "SELECT rowid, * FROM '{}' WHERE starred='y' AND checked='unchecked' "
                "AND amiaministep='no' AND (schedule_date IS NULL OR schedule_date='')".format(table_name)
            )
        except sqlite3.OperationalError:
            continue
        for row in c.fetchall():
            results.append((row, table_name))
    conn.close()
    return results


class WeekView(Frame):
    """Self-contained: header + day-strip navigator on top, an all-day
    banner row and an hourly timeline below, plus a toggleable
    suggestions overlay.

    get_list_display(hidden_name) -> display name string, so this widget
    doesn't need to import td4_sqlite_processes directly.
    on_task_toggle() is an optional callback fired after a task is
    checked/unchecked or scheduled, so the host app can refresh sidebar
    counters etc.
    open_task_detail(rowid, list_name) is an optional callback for the
    right-click menu's "Open full task view" action -- everything not
    related to scheduling (due date, notes, move, copy) lives there
    rather than being duplicated in this module.
    """

    def __init__(self, parent, get_list_display, on_task_toggle=None, open_task_detail=None, **kwargs):
        kwargs.setdefault('bootstyle', 'default')
        super().__init__(parent, **kwargs)
        self.get_list_display = get_list_display
        self.on_task_toggle = on_task_toggle
        self.open_task_detail = open_task_detail
        self.selected_date = date.today()
        # The 7-day window shown in the strip is tracked separately from
        # the selected day -- only the arrow buttons (and Today) move
        # this. Clicking a day within the strip just selects it in place.
        self.strip_start_date = date.today() - timedelta(days=DAY_STRIP_SPAN)
        self.suggestions_visible = False
        self._allday_widgets = []
        self._timeline_blocks = []

        # ---- Header: big date + weekday + suggestions toggle ----
        self.header_F = Frame(self, bootstyle='default')
        self.header_F.pack(fill='x', pady=(10, 15), padx=15)

        self.header_dateL = Label(self.header_F, font=('Calibri', 28, 'bold'), bootstyle='default', foreground='pink')
        self.header_dateL.pack(side='left')

        self.header_dowL = Label(self.header_F, font=('Calibri', 16, 'bold'), bootstyle='info')
        self.header_dowL.pack(side='left', padx=15)

        self.suggestionsToggleB = Button(self.header_F, text='⭐ Suggestions', bootstyle='info outline',
                                          command=self._toggle_suggestions)
        self.suggestionsToggleB.pack(side='right')

        # ---- Day strip navigation ----
        self.strip_F = Frame(self, bootstyle='default')
        self.strip_F.pack(fill='x', pady=(0, 15), padx=15)

        # ---- Seperator for clerer nav ----
        self.sep = Separator(self, bootstyle='secondary')
        self.sep.pack(fill='x', padx=15, pady=(0, 15))

        # ---- Schedule area: all-day banners + hourly timeline ----
        self.schedule_outerF = Frame(self, bootstyle='default')
        self.schedule_outerF.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        self.allday_F = Frame(self.schedule_outerF, bootstyle='default')
        self.allday_sep = Separator(self.schedule_outerF, bootstyle='secondary')

        self.timeline_container_F = Frame(self.schedule_outerF, bootstyle='default')
        self.timeline_container_F.pack(fill='both', expand=True, pady=(8, 0))

        self.timeline_canvas = tk.Canvas(self.timeline_container_F, width=TIMELINE_WIDTH,
                                          highlightthickness=0)
        self.timeline_canvas.pack(side='left', fill='both', expand=True)

        self.timeline_vscroll = Scrollbar(self.timeline_container_F, orient='vertical',
                                           command=self.timeline_canvas.yview, bootstyle='secondary-round')
        self.timeline_vscroll.pack(side='right', fill='y')
        self.timeline_canvas.config(yscrollcommand=self.timeline_vscroll.set,
                                     scrollregion=(0, 0, TIMELINE_WIDTH, 24 * HOUR_HEIGHT_PX),
                                     yscrollincrement=1)
        # Bound directly on the canvas -- an Enter/Leave-based "only while
        # hovering" toggle doesn't work here, because each block is a
        # genuine embedded child *window* (create_window), not just drawn
        # pixels: the moment the pointer crosses onto one, X11/Tk deliver
        # <Leave> to the canvas and <Enter> to the block instead, so a
        # canvas-only Enter/Leave toggle disables scrolling the instant
        # the cursor is over any block -- exactly where it usually is.
        # Every block's widgets get this same binding individually at
        # creation time in _render_timeline/_render_allday_banners.
        #
        # Both <MouseWheel> AND <TouchpadScroll> are bound: on Tk 9 (this
        # app's Tk), every Apple trackpad/Magic Mouse/Magic Trackpad fires
        # ONLY <TouchpadScroll>, never <MouseWheel> at all -- a real
        # two-finger gesture wouldn't have triggered a <MouseWheel>-only
        # binding no matter how correct its handler was.
        self.timeline_canvas.bind('<MouseWheel>', self._on_timeline_scroll)
        if wheel.has_touchpad_scroll():
            self.timeline_canvas.bind(wheel.TOUCHPAD_SCROLL, self._on_timeline_touchpad_scroll)

        self._drag = None
        self._last_drag_event = None

        # ---- Suggestions overlay (built once, hidden until toggled) ----
        self.suggestions_F = Frame(self, bootstyle='dark', width=320)

        self._draw_timeline_grid()
        self._render_strip()
        self._render_header()
        self._render_schedule()

    # ------------------------------------------------------------------
    def _render_header(self):
        self.header_dateL.config(text=self.selected_date.strftime('%B %d, %Y'))
        if self.selected_date == date.today():
            self.header_dowL.config(text='Today', bootstyle='success')
        else:
            self.header_dowL.config(text=self.selected_date.strftime('%A'), bootstyle='info')

    def _render_strip(self):
        for w in self.strip_F.winfo_children():
            w.destroy()

        start = self.strip_start_date
        today = date.today()
        colors = BSStyle().colors
        n_days = DAY_STRIP_SPAN * 2 + 1

        # Grid instead of pack: columns 1..n_days get weight so they
        # stretch to fill the row's width as the window resizes. The
        # nav buttons (col 0, and the last two) stay a fixed natural
        # size -- only the day cells themselves grow.
        for col in range(n_days + 3):
            weight = 1 if 1 <= col <= n_days else 0
            self.strip_F.grid_columnconfigure(col, weight=weight)
        self.strip_F.grid_rowconfigure(0, minsize=CELL_HEIGHT_PX)

        prevB = Button(self.strip_F, text='◀', bootstyle='secondary outline', width=3,
                        command=self._go_prev_week)
        prevB.grid(row=0, column=0, padx=(0, 8), sticky='ns')

        for i in range(n_days):
            day = start + timedelta(days=i)
            is_selected = (day == self.selected_date)
            is_today = (day == today)

            # Plain tkinter widgets on purpose here (not ttk/bootstyle):
            # ttkbootstrap generates a PhotoImage per outline/rounded
            # style tied to the widget's Python lifetime, and destroying
            # + rebuilding these every time you change dates eventually
            # garbage-collects an image a shared style still points at,
            # crashing with "image ... does not exist". Plain tk widgets
            # have no such image, so they're safe to rebuild freely --
            # colors are still pulled live from the active ttkbootstrap
            # theme so this stays on-theme rather than hardcoded.
            if is_selected:
                bg, fg, border = colors.info, colors.selectfg, colors.info
            elif is_today:
                bg, fg, border = colors.bg, colors.fg, colors.warning
            else:
                bg, fg, border = colors.bg, colors.fg, colors.secondary

            cellF = tk.Frame(self.strip_F, height=CELL_HEIGHT_PX,
                              bg=bg, highlightthickness=2, highlightbackground=border,
                              highlightcolor=border)
            cellF.grid(row=0, column=i + 1, padx=3, sticky='nsew')
            cellF.grid_propagate(False)  # keep the height fixed; width is set by the column

            dayL = tk.Label(cellF, text=day.strftime('%a\n%d'), bg=bg, fg=fg,
                             font=('Calibri', 11), justify='center')
            dayL.pack(fill='both', expand=True)

            for widget in (cellF, dayL):
                widget.bind('<Button-1>', lambda e, d=day: self._select(d))

        nextB = Button(self.strip_F, text='▶', bootstyle='secondary outline', width=3,
                        command=self._go_next_week)
        nextB.grid(row=0, column=n_days + 1, padx=(8, 12), sticky='ns')

        todayB = Button(self.strip_F, text='Today', bootstyle='light outline',
                         command=self._go_today)
        todayB.grid(row=0, column=n_days + 2, sticky='ns')

    # ------------------------------------------------------------------
    # Schedule rendering: all-day banners + hourly timeline
    def _render_schedule(self):
        timed, allday = _query_scheduled_tasks_for_date(self.selected_date)
        self._render_allday_banners(allday)
        self._render_timeline(timed)

    def _render_allday_banners(self, allday_results):
        for w in self._allday_widgets:
            w.destroy()
        self._allday_widgets = []

        if not allday_results:
            self.allday_F.pack_forget()
            self.allday_sep.pack_forget()
            return

        self.allday_F.pack(fill='x', before=self.timeline_container_F)
        self.allday_sep.pack(fill='x', pady=(8, 0), before=self.timeline_container_F)

        colors = BSStyle().colors
        for row, list_name in allday_results:
            rowid, task, checked, starred = row[0], row[1], row[2], row[3]
            block_color = _row_get(row, IDX_BLOCK_COLOR)
            if block_color:
                bg, fg = block_color, _readable_text_color(block_color)
            else:
                bg = colors.success if checked == 'checked' else (colors.info if starred == 'y' else colors.secondary)
                fg = colors.selectfg
            chipF = tk.Frame(self.allday_F, bg=bg, highlightthickness=0)
            chipF.pack(side='left', padx=4, pady=4)

            check_glyph = '✓' if checked == 'checked' else '○'
            checkL = tk.Label(chipF, text=check_glyph, bg=bg, fg=fg, font=('Calibri', 9),
                               padx=4, pady=2, cursor='hand2')
            checkL.pack(side='left')
            checkL.bind('<Button-1>', lambda e, rid=rowid, ln=list_name, cur=checked: self._toggle(rid, ln, cur))
            checkL.bind('<Button-3>', lambda e, rid=rowid, ln=list_name, r=row: self._open_block_menu(e, rid, ln, r))

            text = task + ('  ★' if starred == 'y' else '')
            font = ('Calibri', 12, 'overstrike') if checked == 'checked' else ('Calibri', 12)
            chipL = tk.Label(chipF, text=text, bg=bg, fg=fg, font=font, padx=4, pady=4, cursor='fleur')
            chipL.pack(side='left')
            chipLN = tk.Label(chipF, text=self.get_list_display(list_name), bg=bg, fg=fg,
                               font=('Calibri', 9), padx=4, cursor='fleur')
            chipLN.pack(side='left')
            for w in (chipL, chipLN):
                w.bind('<Button-3>', lambda e, rid=rowid, ln=list_name, r=row: self._open_block_menu(e, rid, ln, r))

            # Dragging the chip's text (not the checkmark, same reasoning
            # as the timeline blocks) down onto the timeline converts this
            # all-day task into a timed block.
            for w in (chipL, chipLN):
                w.bind('<ButtonPress-1>', lambda e, rid=rowid, ln=list_name: self._drag_start_allday(e, rid, ln))
                w.bind('<B1-Motion>', self._drag_motion)
                w.bind('<ButtonRelease-1>', self._drag_release)

            self._allday_widgets.append(chipF)

    def _draw_timeline_grid(self):
        colors = BSStyle().colors
        self.timeline_canvas.config(bg=colors.bg)
        for hour in range(25):
            y = hour * HOUR_HEIGHT_PX
            self.timeline_canvas.create_line(TIMELINE_LABEL_WIDTH, y, TIMELINE_WIDTH, y,
                                              fill=colors.secondary, tags='gridline')
            if hour < 24:
                self.timeline_canvas.create_text(TIMELINE_LABEL_WIDTH - 6, y + 2, text=_format_hour_label(hour),
                                                  anchor='ne', fill=colors.fg, font=('Calibri', 9), tags='gridline')

    @staticmethod
    def _layout_timed_blocks(timed_results):
        """Assigns each timed task an (x_offset, width) within the block
        column so tasks whose time ranges overlap render side-by-side
        instead of stacking on top of each other (standard calendar-style
        interval layout). Returns
        [(row, list_name, start_min, duration_min, x_offset, width), ...]."""
        parsed = []
        for row, list_name in timed_results:
            sched_start, sched_duration = _row_get(row, IDX_SCHEDULE_START), _row_get(row, IDX_SCHEDULE_DURATION)
            try:
                hour = int(sched_start[:2])
                minute = int(sched_start[2:])
                duration = int(sched_duration)
            except (ValueError, TypeError):
                continue
            parsed.append((row, list_name, hour * 60 + minute, duration))
        parsed.sort(key=lambda p: p[2])

        results = []
        cluster = []      # (row, list_name, start_min, duration, column)
        columns_end = []  # end time (minutes) of the block currently in each column

        def flush():
            if not cluster:
                return
            width = TIMELINE_BLOCK_WIDTH / len(columns_end)
            for row, list_name, start_min, duration, col in cluster:
                results.append((row, list_name, start_min, duration, col * width, width))
            cluster.clear()
            columns_end.clear()

        for row, list_name, start_min, duration in parsed:
            if columns_end and start_min >= max(columns_end):
                flush()
            end_min = start_min + duration
            placed_col = None
            for i, col_end in enumerate(columns_end):
                if col_end <= start_min:
                    columns_end[i] = end_min
                    placed_col = i
                    break
            if placed_col is None:
                columns_end.append(end_min)
                placed_col = len(columns_end) - 1
            cluster.append((row, list_name, start_min, duration, placed_col))
        flush()
        return results

    def _render_timeline(self, timed_results):
        for w in self._timeline_blocks:
            w.destroy()
        self._timeline_blocks = []
        self.timeline_canvas.delete('block')

        colors = BSStyle().colors
        for row, list_name, start_min, duration_minutes, x_offset, width in self._layout_timed_blocks(timed_results):
            rowid, task, checked, starred = row[0], row[1], row[2], row[3]
            y = start_min
            height = max(duration_minutes, 18)

            block_color = _row_get(row, IDX_BLOCK_COLOR)
            if block_color:
                bg, fg = block_color, _readable_text_color(block_color)
            else:
                bg = colors.success if checked == 'checked' else (colors.info if starred == 'y' else colors.primary)
                fg = colors.selectfg
            blockF = tk.Frame(self.timeline_canvas, bg=bg, highlightthickness=1, highlightbackground=colors.bg)

            check_glyph = '✓' if checked == 'checked' else '○'
            checkL = tk.Label(blockF, text=check_glyph, bg=bg, fg=fg, font=('Calibri', 11, 'bold'),
                               cursor='hand2')
            checkL.pack(side='left', padx=(4, 2), pady=2)
            checkL.bind('<Button-1>', lambda e, rid=rowid, ln=list_name, cur=checked: self._toggle(rid, ln, cur))
            checkL.bind('<Button-3>', lambda e, rid=rowid, ln=list_name, r=row: self._open_block_menu(e, rid, ln, r))

            textF = tk.Frame(blockF, bg=bg)
            textF.pack(side='left', fill='both', expand=True)
            font = ('Calibri', 11, 'overstrike') if checked == 'checked' else ('Calibri', 11, 'bold')
            text = task + ('  ★' if starred == 'y' else '')
            textL1 = tk.Label(textF, text=text, bg=bg, fg=fg, font=font,
                               anchor='w', justify='left', cursor='fleur')
            textL1.pack(fill='x', padx=2, pady=(2, 0))
            textL2 = tk.Label(textF, text=self.get_list_display(list_name), bg=bg, fg=fg,
                               font=('Calibri', 9), anchor='w', cursor='fleur')
            textL2.pack(fill='x', padx=2)

            item_id = self.timeline_canvas.create_window(TIMELINE_LABEL_WIDTH + 4 + x_offset, y, window=blockF,
                                                           width=max(width - 8, 20), height=height,
                                                           anchor='nw', tags='block')

            # Drag-to-reschedule and the right-click menu are bound on the
            # text surface (frame + both labels) -- deliberately not on
            # checkL, which already owns plain <Button-1> for toggling,
            # so the two gestures can never fight over the same click.
            for w in (textF, textL1, textL2):
                w.bind('<ButtonPress-1>', lambda e, iid=item_id, rid=rowid, ln=list_name, dur=duration_minutes:
                       self._drag_start_timeline(e, iid, rid, ln, dur))
                w.bind('<B1-Motion>', self._drag_motion)
                w.bind('<ButtonRelease-1>', self._drag_release)
                w.bind('<Button-3>', lambda e, rid=rowid, ln=list_name, r=row: self._open_block_menu(e, rid, ln, r))

            # Every block widget also needs its own wheel/touchpad binding
            # -- see the note by self.timeline_canvas's own binds in
            # __init__ for why the canvas's binding alone isn't enough.
            for w in (blockF, checkL, textF, textL1, textL2):
                w.bind('<MouseWheel>', self._on_timeline_scroll)
                if wheel.has_touchpad_scroll():
                    w.bind(wheel.TOUCHPAD_SCROLL, self._on_timeline_touchpad_scroll)

            self._timeline_blocks.append(blockF)

    # ------------------------------------------------------------------
    # Timeline scrolling
    def _on_timeline_scroll(self, event):
        self.timeline_canvas.yview_scroll(int(-1 * event.delta), 'units')

    def _on_timeline_touchpad_scroll(self, event):
        # yscrollincrement=1 on this canvas, so a precise pixel delta maps
        # directly to a 'units' scroll amount with no accumulation needed.
        _, dy = wheel.precise_deltas(event)
        if dy:
            self.timeline_canvas.yview_scroll(-dy, 'units')

    # ------------------------------------------------------------------
    # Drag-to-reschedule. Two entry points feed one shared state machine:
    #   - _drag_start_timeline: dragging an existing timed block. Moves
    #     schedule_start (snapped to DRAG_SNAP_MIN), duration stays fixed,
    #     so the block moves as one unit.
    #   - _drag_start_allday: dragging an all-day chip. Nothing moves in
    #     place (there's no timeline position yet); a floating ghost
    #     follows the cursor, and dropping it over the timeline schedules
    #     the task as a new DEFAULT_TIMED_DURATION_MIN-long block there.
    # Dropping a timeline-sourced drag above the canvas (in/near the
    # all-day row) converts it back to all-day. Near the top/bottom edges
    # of the visible canvas, the view auto-scrolls for as long as the
    # cursor stays there; reaching the very top of the day (nothing left
    # to scroll) is what lets the cursor "escape" upward into the all-day
    # row to drop there.
    def _drag_start_timeline(self, event, item_id, rowid, list_name, duration_minutes):
        orig_x, orig_y = self.timeline_canvas.coords(item_id)
        canvas_top = self.timeline_canvas.winfo_rooty()
        mouse_y_in_canvas = self.timeline_canvas.canvasy(0) + (event.y_root - canvas_top)
        self._drag = {
            'source': 'timeline', 'item_id': item_id, 'rowid': rowid, 'list_name': list_name,
            'duration': duration_minutes, 'orig_x': orig_x, 'grab_offset': mouse_y_in_canvas - orig_y,
            'new_y': orig_y, 'moved': False, 'tooltip': None, 'ghost': None,
            'start_y_root': event.y_root, 'autoscroll_dir': 0, 'autoscroll_job': None,
        }

    def _drag_start_allday(self, event, rowid, list_name):
        colors = BSStyle().colors
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes('-topmost', True)
        tk.Label(ghost, text='Drop on timeline to schedule (1 hr)', bg=colors.info, fg=colors.selectfg,
                 font=('Calibri', 10, 'bold'), padx=8, pady=4).pack()
        ghost.geometry('+{}+{}'.format(event.x_root + 12, event.y_root + 12))
        self._drag = {
            'source': 'allday', 'item_id': None, 'rowid': rowid, 'list_name': list_name,
            'duration': DEFAULT_TIMED_DURATION_MIN, 'orig_x': None, 'grab_offset': DEFAULT_TIMED_DURATION_MIN / 2,
            'new_y': None, 'moved': False, 'tooltip': None, 'ghost': ghost,
            'start_y_root': event.y_root, 'autoscroll_dir': 0, 'autoscroll_job': None,
        }

    def _point_over_timeline(self, event):
        x0 = self.timeline_canvas.winfo_rootx()
        y0 = self.timeline_canvas.winfo_rooty()
        return (x0 <= event.x_root <= x0 + self.timeline_canvas.winfo_width()
                and y0 <= event.y_root <= y0 + self.timeline_canvas.winfo_height())

    def _drag_motion(self, event):
        d = self._drag
        if d is None:
            return
        self._last_drag_event = event
        if not d['moved'] and abs(event.y_root - d['start_y_root']) < 4:
            return
        d['moved'] = True

        if d['source'] == 'allday':
            d['ghost'].geometry('+{}+{}'.format(event.x_root + 12, event.y_root + 12))

        if self._point_over_timeline(event):
            self._drag_update_canvas_position(event)
        elif d['tooltip'] is not None:
            d['tooltip'].destroy()
            d['tooltip'] = None

        self._update_edge_autoscroll(event)

    def _drag_update_canvas_position(self, event):
        d = self._drag
        canvas_top = self.timeline_canvas.winfo_rooty()
        mouse_y_in_canvas = self.timeline_canvas.canvasy(0) + (event.y_root - canvas_top)
        raw_y = mouse_y_in_canvas - d['grab_offset']
        max_y = 24 * HOUR_HEIGHT_PX - d['duration']
        snapped_y = max(0, min(round(raw_y / DRAG_SNAP_MIN) * DRAG_SNAP_MIN, max_y))
        d['new_y'] = snapped_y
        if d['source'] == 'timeline':
            self.timeline_canvas.coords(d['item_id'], d['orig_x'], snapped_y)
        self._update_drag_tooltip(event, snapped_y, d['duration'])

    def _update_edge_autoscroll(self, event):
        d = self._drag
        canvas_top = self.timeline_canvas.winfo_rooty()
        canvas_bottom = canvas_top + self.timeline_canvas.winfo_height()
        if event.y_root > canvas_bottom - AUTOSCROLL_MARGIN_PX and self._point_over_timeline(event):
            d['autoscroll_dir'] = 1
        elif (event.y_root < canvas_top + AUTOSCROLL_MARGIN_PX and self.timeline_canvas.canvasy(0) > 0
              and event.x_root >= self.timeline_canvas.winfo_rootx()):
            d['autoscroll_dir'] = -1
        else:
            d['autoscroll_dir'] = 0
        if d['autoscroll_dir'] != 0 and d['autoscroll_job'] is None:
            d['autoscroll_job'] = self.after(AUTOSCROLL_INTERVAL_MS, self._autoscroll_tick)

    def _autoscroll_tick(self):
        d = self._drag
        if d is None:
            return
        d['autoscroll_job'] = None
        if d['autoscroll_dir'] == 0:
            return
        self.timeline_canvas.yview_scroll(d['autoscroll_dir'] * AUTOSCROLL_STEP_UNITS, 'units')
        if d['autoscroll_dir'] == -1 and self.timeline_canvas.canvasy(0) <= 0:
            d['autoscroll_dir'] = 0  # hit the top of the day -- nothing left to scroll, cursor is free
        if self._last_drag_event is not None:
            self._drag_update_canvas_position(self._last_drag_event)
        if d['autoscroll_dir'] != 0:
            d['autoscroll_job'] = self.after(AUTOSCROLL_INTERVAL_MS, self._autoscroll_tick)

    def _update_drag_tooltip(self, event, start_min, duration_minutes):
        d = self._drag
        if d['tooltip'] is None:
            tip = tk.Toplevel(self)
            tip.overrideredirect(True)
            tip.attributes('-topmost', True)
            colors = BSStyle().colors
            lbl = tk.Label(tip, font=('Calibri', 11, 'bold'), padx=8, pady=4,
                            bg=colors.info, fg=colors.selectfg)
            lbl.pack()
            d['tooltip'] = tip
            d['tooltip_label'] = lbl
        text = '{} – {}'.format(_format_clock(start_min), _format_clock(start_min + duration_minutes))
        d['tooltip_label'].config(text=text)
        d['tooltip'].geometry('+{}+{}'.format(event.x_root + 16, event.y_root + 12))

    def _drag_release(self, event):
        d = self._drag
        if d is None:
            return
        self._last_drag_event = None
        if d['autoscroll_job'] is not None:
            self.after_cancel(d['autoscroll_job'])
        if d['tooltip'] is not None:
            d['tooltip'].destroy()
        if d['ghost'] is not None:
            d['ghost'].destroy()

        if d['moved']:
            over_timeline = self._point_over_timeline(event)
            above_timeline = event.y_root < self.timeline_canvas.winfo_rooty()
            if over_timeline:
                start_min = int(d['new_y'])
                hour, minute = divmod(start_min, 60)
                new_start = '{:02d}{:02d}'.format(hour, minute)
                if d['source'] == 'timeline':
                    self._reschedule_task(d['rowid'], d['list_name'], new_start)
                else:  # all-day chip dropped onto the timeline -> becomes a new timed block
                    self._schedule_task(d['rowid'], d['list_name'], self.selected_date.strftime('%x'),
                                         new_start, str(d['duration']))
            elif above_timeline and d['source'] == 'timeline':
                # dragged an existing timed block up past the (already
                # scrolled-to-top) timeline into the all-day row
                self._schedule_task(d['rowid'], d['list_name'], self.selected_date.strftime('%x'), '', '')
            elif d['source'] == 'timeline':
                # dropped somewhere else entirely -- cancel, re-render to
                # snap the live-dragged position back to the real DB state
                self._render_schedule()
            # an all-day-sourced drag dropped anywhere else (e.g. back on
            # the all-day row) never touched the DB or the real chip
            # widget (only the ghost moved), so there's nothing to undo

        self._drag = None

    def _reschedule_task(self, rowid, list_name, new_start):
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("UPDATE '{}' SET schedule_start=? WHERE rowid=?".format(list_name), (new_start, rowid))
        conn.commit()
        conn.close()
        self._render_schedule()
        if self.on_task_toggle:
            self.on_task_toggle()

    # ------------------------------------------------------------------
    # Right-click quick-actions menu (mirrors main.py's expand_3_dots:
    # a plain, cursor-positioned Frame of buttons with a 5s auto-dismiss)
    def _open_block_menu(self, event, rowid, list_name, row):
        checked, starred = row[2], row[3]
        colors = BSStyle().colors
        menuF = tk.Frame(self, bg=colors.dark, highlightthickness=1, highlightbackground=colors.secondary)
        menuF.place(x=event.x_root - self.winfo_rootx(), y=event.y_root - self.winfo_rooty())

        def close_menu():
            menuF.destroy()

        def action(fn):
            return lambda: (fn(), close_menu())

        def make_btn(text, fn):
            Button(menuF, text=text, bootstyle='info outline', command=action(fn)).pack(fill='x', pady=2, padx=2)

        make_btn('✔ Check / Uncheck', lambda: self._toggle(rowid, list_name, checked))
        make_btn('⭐ Star / Unstar', lambda: self._toggle_star(rowid, list_name, starred))
        make_btn('🕐 Change time...', lambda: self._open_change_time_popup(rowid, list_name, row))
        make_btn('🎨 Change color...', lambda: self._open_color_popup(rowid, list_name, _row_get(row, IDX_BLOCK_COLOR)))
        make_btn('🗓 Remove from My Day', lambda: self._schedule_task(rowid, list_name, '', '', ''))
        make_btn('🖊 Rename task', lambda: self._open_rename_popup(rowid, list_name, row[1]))
        make_btn('🗑 Delete task', lambda: self._delete_task(rowid, list_name))
        make_btn('💬 Open full task view', lambda: self._open_full_task_view(rowid, list_name))

        menuF.after(5000, close_menu)

    def _toggle_star(self, rowid, list_name, current_star):
        new_star = 'n' if current_star == 'y' else 'y'
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("UPDATE '{}' SET starred=? WHERE rowid=?".format(list_name), (new_star, rowid))
        conn.commit()
        conn.close()
        self._render_schedule()
        if self.on_task_toggle:
            self.on_task_toggle()

    def _set_block_color(self, rowid, list_name, hex_color):
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("UPDATE '{}' SET block_color=? WHERE rowid=?".format(list_name), (hex_color, rowid))
        conn.commit()
        conn.close()
        self._render_schedule()
        if self.on_task_toggle:
            self.on_task_toggle()

    def _open_color_popup(self, rowid, list_name, current_color):
        colors = BSStyle().colors
        popup = tk.Toplevel(self)
        popup.title('Change color')
        popup.configure(bg=colors.bg)

        contentF = Frame(popup, bootstyle='dark')
        contentF.pack(fill='both', expand=True)

        Label(contentF, text='Choose a color', bootstyle='dark inverse',
              font=('Calibri', 12, 'bold')).pack(pady=(14, 8), padx=16)

        def apply_and_close(hex_value):
            self._set_block_color(rowid, list_name, hex_value)
            popup.destroy()

        swatchF = tk.Frame(contentF, bg=colors.bg)
        swatchF.pack(padx=16, pady=(0, 10))
        swatch_size, cols = 32, 5
        for i, hexcol in enumerate(PRESET_BLOCK_COLORS):
            row_i, col_i = divmod(i, cols)
            border = colors.selectfg if hexcol == current_color else colors.bg
            sw = tk.Frame(swatchF, width=swatch_size, height=swatch_size, bg=hexcol,
                          highlightthickness=2, highlightbackground=border, cursor='hand2')
            sw.grid(row=row_i, column=col_i, padx=4, pady=4)
            sw.grid_propagate(False)
            sw.bind('<Button-1>', lambda e, h=hexcol: apply_and_close(h))

        Separator(contentF, bootstyle='secondary').pack(fill='x', padx=16, pady=(4, 10))

        def open_colorwheel():
            result = Querybox.get_color(popup, title='Custom color', initialcolor=current_color or None)
            if result is not None:
                apply_and_close(result.hex)

        Button(contentF, text='Custom color...', bootstyle='secondary outline',
               command=open_colorwheel).pack(pady=(0, 8), padx=16, fill='x')
        Button(contentF, text='Reset to default', bootstyle='secondary outline',
               command=lambda: apply_and_close('')).pack(pady=(0, 8), padx=16, fill='x')
        Button(contentF, text='Cancel', bootstyle='secondary',
               command=popup.destroy).pack(pady=(0, 14), padx=16, fill='x')

    def _delete_task(self, rowid, list_name):
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("DELETE FROM '{}' WHERE rowid=?".format(list_name), (rowid,))
        conn.commit()
        conn.close()
        self._render_schedule()
        if self.on_task_toggle:
            self.on_task_toggle()

    def _rename_task(self, rowid, list_name, new_name):
        new_name = new_name.strip()
        if not new_name:
            return
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("UPDATE '{}' SET task=? WHERE rowid=?".format(list_name), (new_name, rowid))
        conn.commit()
        conn.close()
        self._render_schedule()

    def _open_rename_popup(self, rowid, list_name, current_name):
        popup = tk.Toplevel(self)
        popup.title('Rename task')
        popup.geometry('300x130')
        tk.Label(popup, text='New name:').pack(pady=(12, 2))
        nameE = tk.Entry(popup, width=30)
        nameE.insert(0, current_name)
        nameE.pack(pady=2)

        def save():
            self._rename_task(rowid, list_name, nameE.get())
            popup.destroy()

        tk.Button(popup, text='Save', command=save).pack(pady=12)

    def _open_change_time_popup(self, rowid, list_name, row):
        sched_date = _row_get(row, IDX_SCHEDULE_DATE)
        sched_start = _row_get(row, IDX_SCHEDULE_START)
        sched_duration = _row_get(row, IDX_SCHEDULE_DURATION)
        open_schedule_popup(
            self, sched_date or self.selected_date.strftime('%x'), sched_start, sched_duration,
            on_save=lambda d, s, dur: self._schedule_task(rowid, list_name, d, s, dur),
            title='Change time',
        )

    def _open_full_task_view(self, rowid, list_name):
        if self.open_task_detail:
            self.open_task_detail(rowid, list_name)

    # ------------------------------------------------------------------
    # Suggestions overlay
    def _toggle_suggestions(self):
        self.suggestions_visible = not self.suggestions_visible
        if self.suggestions_visible:
            self.suggestions_F.place(in_=self, relx=1.0, rely=0, relheight=1.0, anchor='ne')
            self.suggestions_F.lift()
            self._render_suggestions()
        else:
            self.suggestions_F.place_forget()

    def _render_suggestions(self):
        for w in self.suggestions_F.winfo_children():
            w.destroy()

        headerF = Frame(self.suggestions_F, bootstyle='dark')
        headerF.pack(fill='x', padx=10, pady=10)
        Label(headerF, text='Suggestions', font=('Calibri', 16, 'bold'), bootstyle='dark inverse').pack(side='left')
        Button(headerF, text='✕', bootstyle='dark outline', width=3,
               command=self._toggle_suggestions).pack(side='right')

        candidates = get_myday_suggestions()
        listF = ScrolledFrame(self.suggestions_F, bootstyle='dark-round')
        listF.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        if not candidates:
            Label(listF, text='No starred tasks waiting to be scheduled.', bootstyle='secondary',
                  font=('Calibri', 12), wraplength=260, justify='left').pack(pady=20, padx=5)
            return

        for row, list_name in candidates:
            rowid, task = row[0], row[1]
            cardF = Frame(listF, bootstyle='secondary', padding=8)
            cardF.pack(fill='x', pady=4)
            Label(cardF, text='★ ' + task, font=('Calibri', 13), bootstyle='secondary inverse',
                  wraplength=220, justify='left').pack(anchor='w')
            Label(cardF, text=self.get_list_display(list_name), font=('Calibri', 10),
                  bootstyle='secondary inverse').pack(anchor='w')
            Button(cardF, text='+ Add to My Day', bootstyle='info outline',
                   command=lambda rid=rowid, ln=list_name: self._schedule_task(
                       rid, ln, self.selected_date.strftime('%x'))
                   ).pack(anchor='e', pady=(6, 0))

    def _schedule_task(self, rowid, list_name, sched_date, sched_start='', sched_duration=''):
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("UPDATE '{}' SET schedule_date=?, schedule_start=?, schedule_duration=? WHERE rowid=?".format(list_name),
                  (sched_date, sched_start, sched_duration, rowid))
        conn.commit()
        conn.close()
        self._render_schedule()
        self._render_suggestions()
        if self.on_task_toggle:
            self.on_task_toggle()

    # ------------------------------------------------------------------
    def _select(self, new_date):
        self.selected_date = new_date
        self._render_strip()
        self._render_header()
        self._render_schedule()

    def _go_prev_week(self):
        self.strip_start_date -= timedelta(days=7)
        self._render_strip()

    def _go_next_week(self):
        self.strip_start_date += timedelta(days=7)
        self._render_strip()

    def _go_today(self):
        self.strip_start_date = date.today() - timedelta(days=DAY_STRIP_SPAN)
        self._select(date.today())

    def _toggle(self, rowid, list_name, current_status):
        new_status = 'unchecked' if current_status == 'checked' else 'checked'
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("UPDATE '{}' SET checked=? WHERE rowid=?".format(list_name), (new_status, rowid))
        conn.commit()
        conn.close()
        self._render_schedule()
        if self.on_task_toggle:
            self.on_task_toggle()

    def refresh(self):
        """Public hook -- call this after external changes (e.g. a task
        was scheduled elsewhere) if My Day is currently on screen."""
        self._render_strip()
        self._render_header()
        self._render_schedule()


def _format_hour_label(hour):
    suffix = 'AM' if hour < 12 else 'PM'
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return '{} {}'.format(display_hour, suffix)


def _format_clock(total_minutes):
    """Formats a minutes-since-midnight value (may exceed 1439 if a drag
    is snapped near the end of the day) as e.g. '9:45 AM'."""
    total_minutes = max(0, int(total_minutes))
    hour, minute = divmod(total_minutes, 60)
    hour %= 24
    suffix = 'AM' if hour < 12 else 'PM'
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return '{}:{:02d} {}'.format(display_hour, minute, suffix)
