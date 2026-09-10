"""
myday_time_wheel.py

Shared iOS-style scrolling wheel time picker, used by both myday_weekview.py
(My Day's "Change time..." context-menu action) and main.py (the task detail
view's Schedule section). Kept as its own standalone module -- like
corkboard_freeform.py / corkboard_rich_text.py -- so neither of those two
files has to import from the other.

Two independent 12-hour wheels (start, end -- never duration, which is always
computed), each paired with its own AM/PM toggle; the toggle is the sole
source of truth for AM/PM, never duplicated into a wheel's own labels. Each
wheel also accepts typed input as a fallback to scrolling.

TimeWheel is a fixed 5-row tk.Canvas that RETEXTURES its 5 create_text items
in place rather than panning a scrollregion -- the "selected" value is a
single self.selected_index (0-47) that is always the current, fully-settled
value (no separate in-flight/debounced state). This avoids both the wrap-seam
bookkeeping a true panning 48-item wheel would need, and the per-widget-image
lifetime gotcha documented in myday_weekview.py, since nothing is ever
destroyed/recreated on scroll -- only re-labeled.
"""

import re
import tkinter as tk
from datetime import date
from ttkbootstrap import DateEntry, Frame, Label, Button, Separator
from ttkbootstrap.style import Style as BSStyle
from ttkbootstrap.internal import wheel

VISIBLE_ROWS = 5
CENTER_ROW = 2
ITEM_HEIGHT_PX = 32
WHEEL_WIDTH_PX = 90
TOTAL_ITEMS = 48
DRAG_SNAP_MIN = 15

_HOURS_ORDER = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
_MINUTES = [0, 15, 30, 45]
TIME_LABELS = ['{}:{:02d}'.format(_HOURS_ORDER[i // 4], _MINUTES[i % 4]) for i in range(TOTAL_ITEMS)]


def _index_to_hour12_minute(index):
    return _HOURS_ORDER[index // 4], _MINUTES[index % 4]


def _hour12_minute_to_index(hour12, minute):
    hour_slot = _HOURS_ORDER.index(hour12)
    minute_slot = round(minute / DRAG_SNAP_MIN) % 4
    return (hour_slot * 4 + minute_slot) % TOTAL_ITEMS


def hhmm_to_index_and_meridiem(hhmm):
    """'1430' -> (index for the 2:30 slot, 'PM')."""
    hour24 = int(hhmm[:2])
    minute = int(hhmm[2:])
    meridiem = 'AM' if hour24 < 12 else 'PM'
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return _hour12_minute_to_index(hour12, minute), meridiem


_TIME_RE_SUFFIX = re.compile(r'^\s*(\d{1,4})(?::(\d{2}))?\s*([ap])\.?m?\.?\s*$', re.IGNORECASE)
_TIME_RE_PLAIN = re.compile(r'^\s*(\d{1,4})(?::(\d{2}))?\s*$')


def parse_lenient_time(text):
    """Returns (hour12: 1-12, minute: 0-59, meridiem: 'AM'|'PM'|None) or None
    if unparseable. meridiem is None when the input is genuinely ambiguous
    (e.g. "2:00" or "2") -- callers should leave the paired toggle alone in
    that case; it's only returned when explicit (a suffix) or derivable
    (a 24-hour/military value like "1400" or "14")."""
    text = text.strip()
    if not text:
        return None

    m = _TIME_RE_SUFFIX.match(text)
    if m:
        digits, minute_str, ampm = m.group(1), m.group(2), m.group(3).lower()
        hour = int(digits)
        minute = int(minute_str) if minute_str is not None else 0
        if not (1 <= hour <= 12) or not (0 <= minute <= 59):
            return None
        return (hour, minute, 'AM' if ampm == 'a' else 'PM')

    m = _TIME_RE_PLAIN.match(text)
    if not m:
        return None
    digits, minute_str = m.group(1), m.group(2)

    if minute_str is not None:
        hour, minute = int(digits), int(minute_str)
        if not (0 <= minute <= 59) or not (0 <= hour <= 23):
            return None
    else:
        if len(digits) in (3, 4):
            hour = int(digits[:-2])
            minute = int(digits[-2:])
        elif len(digits) in (1, 2):
            hour, minute = int(digits), 0
        else:
            return None
        if not (0 <= minute <= 59) or not (0 <= hour <= 23):
            return None

    if hour == 0:
        return (12, minute, 'AM')
    if hour <= 12:
        return (hour, minute, None)  # ambiguous -- caller leaves the toggle as-is
    return (hour - 12, minute, 'PM')  # unambiguous 24-hour/military value


def _format_clock_12(total_minutes):
    total_minutes = max(0, int(total_minutes)) % (24 * 60)
    hour, minute = divmod(total_minutes, 60)
    suffix = 'AM' if hour < 12 else 'PM'
    display_hour = hour % 12 or 12
    return '{}:{:02d} {}'.format(display_hour, minute, suffix)


def format_time_range(start_hhmm, duration_min):
    """'1430', '60' -> '2:30 PM - 3:30 PM'. Returns '' if either is empty
    or unparseable (the all-day / unscheduled case)."""
    if not start_hhmm or not duration_min:
        return ''
    try:
        start_total = int(start_hhmm[:2]) * 60 + int(start_hhmm[2:])
        end_total = start_total + int(duration_min)
    except (ValueError, TypeError):
        return ''
    return '{} - {}'.format(_format_clock_12(start_total), _format_clock_12(end_total))


class TimeWheel(tk.Frame):
    """One 12-hour, 15-minute-increment scrolling wheel (48 entries,
    "12:00" .. "11:45", no AM/PM suffix -- pair with an AmPmToggle for that).

    on_change(index) fires synchronously after every value mutation caused
    by scrolling, clicking a row, or confirming typed input -- never by
    set_index() (programmatic prefill shouldn't trigger validation).
    on_meridiem_hint(meridiem) fires only when a typed confirm carries an
    explicit or 24-hour-derivable AM/PM, so the caller can update its
    paired AmPmToggle; never fired by scroll/click (neither implies a
    meridiem change)."""

    def __init__(self, parent, on_change=None, on_meridiem_hint=None, initial_index=0, **kwargs):
        colors = BSStyle().colors
        kwargs.setdefault('bg', colors.bg)
        super().__init__(parent, **kwargs)
        self.on_change = on_change
        self.on_meridiem_hint = on_meridiem_hint
        self.selected_index = initial_index % TOTAL_ITEMS
        self._typing = False
        self._entry = None
        self._entry_var = None
        self._pixel_accum = wheel.PixelAccumulator()

        self.canvas = tk.Canvas(self, width=WHEEL_WIDTH_PX, height=VISIBLE_ROWS * ITEM_HEIGHT_PX,
                                 highlightthickness=0, bg=colors.bg)
        self.canvas.pack()

        band_top = CENTER_ROW * ITEM_HEIGHT_PX
        band_bottom = band_top + ITEM_HEIGHT_PX
        self._band_ids = (
            self.canvas.create_line(0, band_top, WHEEL_WIDTH_PX, band_top, fill=colors.info),
            self.canvas.create_line(0, band_bottom, WHEEL_WIDTH_PX, band_bottom, fill=colors.info),
        )

        self._row_ids = []
        for row in range(VISIBLE_ROWS):
            y = row * ITEM_HEIGHT_PX + ITEM_HEIGHT_PX // 2
            font = ('Calibri', 15, 'bold') if row == CENTER_ROW else ('Calibri', 12)
            fill = colors.fg if row == CENTER_ROW else colors.secondary
            item_id = self.canvas.create_text(WHEEL_WIDTH_PX // 2, y, text='', font=font, fill=fill)
            self._row_ids.append(item_id)

        self.canvas.bind('<MouseWheel>', self._on_wheel_scroll)
        if wheel.has_touchpad_scroll():
            self.canvas.bind(wheel.TOUCHPAD_SCROLL, self._on_touchpad_scroll)

        for row in (0, 1, 3, 4):
            self.canvas.tag_bind(self._row_ids[row], '<Button-1>', lambda e, r=row: self._click_row(r))
            self.canvas.tag_bind(self._row_ids[row], '<Enter>', lambda e: self.canvas.config(cursor='hand2'))
            self.canvas.tag_bind(self._row_ids[row], '<Leave>', lambda e: self.canvas.config(cursor=''))

        self.canvas.tag_bind(self._row_ids[CENTER_ROW], '<Button-1>', self._enter_type_mode)
        for band_id in self._band_ids:
            self.canvas.tag_bind(band_id, '<Button-1>', self._enter_type_mode)

        self._redraw()

    def _redraw(self):
        for row in range(VISIBLE_ROWS):
            idx = (self.selected_index + (row - CENTER_ROW)) % TOTAL_ITEMS
            self.canvas.itemconfigure(self._row_ids[row], text=TIME_LABELS[idx])

    def _fire_change(self):
        if self.on_change:
            self.on_change(self.selected_index)

    def _step(self, direction):
        self.selected_index = (self.selected_index + direction) % TOTAL_ITEMS
        self._redraw()
        self._fire_change()

    def _on_wheel_scroll(self, event):
        if self._typing:
            return
        notches = wheel.wheel_notches(self.canvas, event)
        if notches:
            self._step(-1 if notches > 0 else 1)
        return 'break'

    def _on_touchpad_scroll(self, event):
        if self._typing:
            return
        dx, dy = wheel.precise_deltas(event)
        _, steps_y = self._pixel_accum.add(dx, dy, 1, ITEM_HEIGHT_PX)
        for _ in range(abs(steps_y)):
            self._step(-1 if steps_y > 0 else 1)

    def _click_row(self, row):
        if self._typing:
            return
        self._step(row - CENTER_ROW)

    def _enter_type_mode(self, event=None):
        if self._typing:
            return
        self._typing = True
        colors = BSStyle().colors
        self._entry_var = tk.StringVar(value=TIME_LABELS[self.selected_index])
        self._entry = tk.Entry(self, textvariable=self._entry_var, font=('Calibri', 15, 'bold'),
                                justify='center', bg=colors.bg, fg=colors.fg,
                                insertbackground=colors.fg, relief='flat',
                                highlightthickness=1, highlightbackground=colors.info,
                                highlightcolor=colors.info)
        self._entry.place(x=0, y=CENTER_ROW * ITEM_HEIGHT_PX, width=WHEEL_WIDTH_PX, height=ITEM_HEIGHT_PX)
        self._entry.select_range(0, 'end')
        self._entry.focus_set()
        self._entry.bind('<Return>', self._confirm_type)
        self._entry.bind('<FocusOut>', self._confirm_type)
        self._entry.bind('<Escape>', lambda e: self._exit_type_mode())

    def _exit_type_mode(self):
        # Guarded re-entrant-safe: destroying a focused Entry can itself
        # synthesize a <FocusOut> that would otherwise call back in here
        # (or into _confirm_type) a second time.
        if not self._typing:
            return
        self._typing = False
        entry, self._entry = self._entry, None
        if entry is not None:
            entry.destroy()

    def _confirm_type(self, event=None):
        if not self._typing:
            return
        text = self._entry_var.get()
        self._exit_type_mode()
        parsed = parse_lenient_time(text)
        if parsed is None:
            return  # invalid input -- silently keep the previous value
        hour12, minute, meridiem = parsed
        self.selected_index = _hour12_minute_to_index(hour12, minute)
        if meridiem is not None and self.on_meridiem_hint is not None:
            self.on_meridiem_hint(meridiem)  # before _redraw/_fire_change, so validation sees it
        self._redraw()
        self._fire_change()

    def get_index(self):
        return self.selected_index

    def get_label(self):
        return TIME_LABELS[self.selected_index]

    def get_hour_minute_24(self, meridiem):
        hour12, minute = _index_to_hour12_minute(self.selected_index)
        if meridiem == 'AM':
            hour24 = 0 if hour12 == 12 else hour12
        else:
            hour24 = 12 if hour12 == 12 else hour12 + 12
        return hour24, minute

    def set_index(self, index):
        """Programmatic prefill/reset -- redraws immediately, does NOT
        fire on_change (prefilling shouldn't trigger a validation pass
        before the popup has finished wiring everything up)."""
        self.selected_index = index % TOTAL_ITEMS
        self._redraw()


class AmPmToggle(tk.Frame):
    """Two-state AM/PM control, external to TimeWheel by design -- the
    toggle is meant to be the single source of truth for a wheel's
    meridiem, so it isn't owned/duplicated by the wheel itself.

    on_change(meridiem) fires only on a genuine user click."""

    def __init__(self, parent, on_change=None, initial='AM', **kwargs):
        self._colors = BSStyle().colors
        kwargs.setdefault('bg', self._colors.bg)
        super().__init__(parent, **kwargs)
        self.on_change = on_change
        self.meridiem = initial

        self.am_label = tk.Label(self, text='AM', font=('Calibri', 11, 'bold'), padx=8, pady=4, cursor='hand2')
        self.am_label.pack(side='left')
        self.pm_label = tk.Label(self, text='PM', font=('Calibri', 11, 'bold'), padx=8, pady=4, cursor='hand2')
        self.pm_label.pack(side='left')
        self.am_label.bind('<Button-1>', lambda e: self._select('AM'))
        self.pm_label.bind('<Button-1>', lambda e: self._select('PM'))
        self._redraw()

    def _redraw(self):
        colors = self._colors
        for label, value in ((self.am_label, 'AM'), (self.pm_label, 'PM')):
            active = self.meridiem == value
            label.config(bg=colors.info if active else colors.bg,
                         fg=colors.selectfg if active else colors.fg)

    def _select(self, value):
        if value == self.meridiem:
            return
        self.meridiem = value
        self._redraw()
        if self.on_change:
            self.on_change(self.meridiem)

    def get_meridiem(self):
        return self.meridiem

    def set_meridiem(self, value):
        """Programmatic -- redraws, does NOT fire on_change."""
        if value not in ('AM', 'PM') or value == self.meridiem:
            return
        self.meridiem = value
        self._redraw()


def open_schedule_popup(parent, initial_date, initial_start, initial_duration, on_save, title='Schedule'):
    """Shared modal popup for setting a task's schedule_date/start/duration.
    on_save(date_str, start_str, duration_str) is called on Save (start and
    duration are '' for the all-day case) -- storage format is unchanged,
    this is purely a UI-input change."""
    popup = tk.Toplevel(parent)
    popup.title(title)
    colors = BSStyle().colors
    popup.configure(bg=colors.bg)

    # Everything lives inside one bootstyle='dark' Frame filling the
    # Toplevel -- same convention used for every other popup/menu in this
    # app (main.py's expand_3_dots' self.miF, myday_weekview.py's
    # suggestions_F, backFrame, etc.). Without this, a plain Toplevel and
    # plain tk chrome default to the OS's native light-mode colors, which
    # clash badly against the dark-themed wheel/toggle widgets floating
    # inside it -- that mismatch is a real bug this fixes, not a
    # theme choice being made here for the first time.
    contentF = Frame(popup, bootstyle='dark')
    contentF.pack(fill='both', expand=True)

    is_timed = bool(initial_start and initial_duration)
    state = {'all_day': not is_timed}

    # ---- All-day / Timed toggle ----
    modeF = tk.Frame(contentF, bg=colors.bg)
    modeF.pack(pady=(14, 6))
    alldayL = tk.Label(modeF, text='All day', font=('Calibri', 11, 'bold'), padx=10, pady=4, cursor='hand2')
    alldayL.pack(side='left')
    timedL = tk.Label(modeF, text='Timed', font=('Calibri', 11, 'bold'), padx=10, pady=4, cursor='hand2')
    timedL.pack(side='left')

    # ---- Date field ----
    Label(contentF, text='Date:', bootstyle='dark inverse').pack(pady=(6, 2))
    date_entry = DateEntry(contentF, bootstyle='secondary', firstweekday=6, width=9)
    date_entry.pack()
    date_entry.entry.delete(0, 'end')
    date_entry.entry.insert(0, initial_date or date.today().strftime('%x'))

    Separator(contentF, bootstyle='secondary').pack(fill='x', padx=16, pady=(12, 0))

    # ---- Bottom chrome, built before the timed section so it can be
    # reliably anchored with before= regardless of toggle history ----
    error_label = Label(contentF, text='', bootstyle='danger')
    error_label.pack(pady=(6, 0))
    save_btn = Button(contentF, text='Save', bootstyle='success')
    save_btn.pack(pady=(10, 4))
    Button(contentF, text='Cancel', bootstyle='secondary outline', command=popup.destroy).pack(pady=(0, 12))

    # ---- Timed section (start wheel+toggle, end wheel+toggle) ----
    timedF = tk.Frame(contentF, bg=colors.bg)

    def recompute_validation():
        if state['all_day']:
            error_label.config(text='')
            save_btn.config(state='normal')
            return
        sh, sm = start_wheel.get_hour_minute_24(start_toggle.get_meridiem())
        eh, em = end_wheel.get_hour_minute_24(end_toggle.get_meridiem())
        if (eh * 60 + em) <= (sh * 60 + sm):
            error_label.config(text='End time must be after start time')
            save_btn.config(state='disabled')
        else:
            error_label.config(text='')
            save_btn.config(state='normal')

    Label(timedF, text='Start', bootstyle='dark inverse').grid(row=0, column=0, columnspan=2, pady=(4, 2))
    start_toggle = AmPmToggle(timedF, on_change=lambda v: recompute_validation())
    start_wheel = TimeWheel(timedF, on_change=lambda i: recompute_validation(),
                             on_meridiem_hint=start_toggle.set_meridiem)
    start_wheel.grid(row=1, column=0, padx=6)
    start_toggle.grid(row=1, column=1, padx=6)

    Label(timedF, text='End', bootstyle='dark inverse').grid(row=2, column=0, columnspan=2, pady=(14, 2))
    end_toggle = AmPmToggle(timedF, on_change=lambda v: recompute_validation())
    end_wheel = TimeWheel(timedF, on_change=lambda i: recompute_validation(),
                           on_meridiem_hint=end_toggle.set_meridiem)
    end_wheel.grid(row=3, column=0, padx=6)
    end_toggle.grid(row=3, column=1, padx=6)

    # ---- Prefill ----
    if is_timed:
        s_idx, s_mer = hhmm_to_index_and_meridiem(initial_start)
        start_wheel.set_index(s_idx)
        start_toggle.set_meridiem(s_mer)
        start_total = int(initial_start[:2]) * 60 + int(initial_start[2:])
        end_total = start_total + int(initial_duration)
        end_hhmm = '{:02d}{:02d}'.format((end_total // 60) % 24, end_total % 60)
        e_idx, e_mer = hhmm_to_index_and_meridiem(end_hhmm)
        end_wheel.set_index(e_idx)
        end_toggle.set_meridiem(e_mer)
    else:
        s_idx, s_mer = hhmm_to_index_and_meridiem('0900')
        start_wheel.set_index(s_idx)
        start_toggle.set_meridiem(s_mer)
        e_idx, e_mer = hhmm_to_index_and_meridiem('1000')
        end_wheel.set_index(e_idx)
        end_toggle.set_meridiem(e_mer)

    def set_mode(all_day):
        state['all_day'] = all_day
        if all_day:
            timedF.pack_forget()
            alldayL.config(bg=colors.info, fg=colors.selectfg)
            timedL.config(bg=colors.bg, fg=colors.fg)
        else:
            timedF.pack(before=error_label, pady=(4, 0))
            alldayL.config(bg=colors.bg, fg=colors.fg)
            timedL.config(bg=colors.info, fg=colors.selectfg)
        recompute_validation()

    alldayL.bind('<Button-1>', lambda e: set_mode(True))
    timedL.bind('<Button-1>', lambda e: set_mode(False))

    def do_save():
        date_str = date_entry.entry.get().strip()
        if state['all_day']:
            on_save(date_str, '', '')
        else:
            sh, sm = start_wheel.get_hour_minute_24(start_toggle.get_meridiem())
            eh, em = end_wheel.get_hour_minute_24(end_toggle.get_meridiem())
            duration = (eh * 60 + em) - (sh * 60 + sm)
            start_hhmm = '{:02d}{:02d}'.format(sh, sm)
            on_save(date_str, start_hhmm, str(duration))
        popup.destroy()

    save_btn.config(command=do_save)
    set_mode(state['all_day'])
    return popup
