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

DAY_STRIP_SPAN = 3  # days shown on either side of the selected date (3 -> 7-day strip)
CELL_HEIGHT_PX = 50
HOUR_HEIGHT_PX = 60  # 1 pixel == 1 minute, so duration math is a direct pixel count
TIMELINE_LABEL_WIDTH = 55
TIMELINE_BLOCK_WIDTH = 420
TIMELINE_WIDTH = TIMELINE_LABEL_WIDTH + TIMELINE_BLOCK_WIDTH


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
            sched_start, sched_duration = row[-2], row[-1]
            if sched_start and sched_duration:
                timed.append((row, table_name))
            else:
                allday.append((row, table_name))
    conn.close()
    timed.sort(key=lambda pair: pair[0][-2])  # zero-padded 'HHMM' sorts correctly as text
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
    """

    def __init__(self, parent, get_list_display, on_task_toggle=None, **kwargs):
        kwargs.setdefault('bootstyle', 'default')
        super().__init__(parent, **kwargs)
        self.get_list_display = get_list_display
        self.on_task_toggle = on_task_toggle
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

        self.header_dateL = Label(self.header_F, font=('Calibri', 28, 'bold'), bootstyle='default inverse')
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
                                     scrollregion=(0, 0, TIMELINE_WIDTH, 24 * HOUR_HEIGHT_PX))
        self.timeline_canvas.bind('<MouseWheel>', lambda e: self.timeline_canvas.yview_scroll(int(-1 * e.delta), 'units'))

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
            bg = colors.success if checked == 'checked' else (colors.info if starred == 'y' else colors.secondary)
            chipF = tk.Frame(self.allday_F, bg=bg, highlightthickness=0)
            chipF.pack(side='left', padx=4, pady=4)
            text = task + ('  ★' if starred == 'y' else '')
            font = ('Calibri', 12, 'overstrike') if checked == 'checked' else ('Calibri', 12)
            chipL = tk.Label(chipF, text=text, bg=bg, fg=colors.selectfg, font=font, padx=8, pady=4)
            chipL.pack(side='left')
            chipLN = tk.Label(chipF, text=self.get_list_display(list_name), bg=bg, fg=colors.selectfg,
                               font=('Calibri', 9), padx=4)
            chipLN.pack(side='left')
            chipF.bind('<Button-1>', lambda e, rid=rowid, ln=list_name, cur=checked: self._toggle(rid, ln, cur))
            chipL.bind('<Button-1>', lambda e, rid=rowid, ln=list_name, cur=checked: self._toggle(rid, ln, cur))
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

    def _render_timeline(self, timed_results):
        for w in self._timeline_blocks:
            w.destroy()
        self._timeline_blocks = []
        self.timeline_canvas.delete('block')

        colors = BSStyle().colors
        for row, list_name in timed_results:
            rowid, task, checked, starred = row[0], row[1], row[2], row[3]
            sched_start, sched_duration = row[-2], row[-1]
            try:
                hour = int(sched_start[:2])
                minute = int(sched_start[2:])
                duration_minutes = int(sched_duration)
            except (ValueError, TypeError):
                continue
            y = hour * HOUR_HEIGHT_PX + minute
            height = max(duration_minutes, 18)

            bg = colors.success if checked == 'checked' else (colors.info if starred == 'y' else colors.primary)
            blockF = tk.Frame(self.timeline_canvas, bg=bg, highlightthickness=1, highlightbackground=colors.bg)
            font = ('Calibri', 11, 'overstrike') if checked == 'checked' else ('Calibri', 11, 'bold')
            text = task + ('  ★' if starred == 'y' else '')
            tk.Label(blockF, text=text, bg=bg, fg=colors.selectfg, font=font,
                     anchor='w', justify='left').pack(fill='x', padx=6, pady=(2, 0))
            tk.Label(blockF, text=self.get_list_display(list_name), bg=bg, fg=colors.selectfg,
                     font=('Calibri', 9), anchor='w').pack(fill='x', padx=6)
            blockF.bind('<Button-1>', lambda e, rid=rowid, ln=list_name, cur=checked: self._toggle(rid, ln, cur))

            self.timeline_canvas.create_window(TIMELINE_LABEL_WIDTH + 4, y, window=blockF,
                                                width=TIMELINE_BLOCK_WIDTH - 8, height=height,
                                                anchor='nw', tags='block')
            self._timeline_blocks.append(blockF)

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
