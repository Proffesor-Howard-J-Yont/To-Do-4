import tkinter as tk
from PIL import Image
Image.CUBIC = Image.BICUBIC
from ttkbootstrap import *
from ttkbootstrap.widgets import ScrolledFrame
from ttkbootstrap.dialogs import Querybox
from ttkbootstrap.widgets import ToolTip
import sqlite3
from tkinter import filedialog
import time
import td4_sqlite_processes as sql_process
sql_process.migrate_corkboard_schema()
sql_process.migrate_corkboard_positions()
#from win10toast import ToastNotifier
import random as rd
from corkboard_freeform import FreeformCorkboard, PIN_WIDTH, PIN_HEIGHT
import json
from corkboard_rich_text import build_pin_preview, open_pin_view, open_pin_editor, delete_image_file
sql_process.migrate_corkboard_content()

#  COLORS
# Default, primary, success, info, warning, danger, light, dark

# STYLE
# inverse, outline, link, toolbutton

global return2_
return2_ = 'False'

undone_tasks = 0
root = Window(themename='darkly')
# vapor, cyborg, minty, lumen, darkly, superhero
root.title("To-Do 4.3 Beta - A new and innovative tasks organizer. - Corkboard Update 2.2.0")
root.geometry('1200x800+300+100')
root.iconbitmap('icon.ico')

jut_img          = PhotoImage(file='check_circle.png')
reg_img          = PhotoImage(file='check_circlereg.png')
reg_img_squ      = PhotoImage(file='check box.png')
jut_img_squ      = PhotoImage(file='check box jut.png')
circleimg        = PhotoImage(file='circle.png')

refreshimg       = PhotoImage(file='refresh.png')
infoimg          = PhotoImage(file='info.png')
homeimg          = PhotoImage(file='home.png')
settingsimg      = PhotoImage(file='settings.png')
newlistimg       = PhotoImage(file='new_list.png')
deletetask       = PhotoImage(file='delete.png')
renametaskimg    = PhotoImage(file='edit.png')
uncheckedtask    = PhotoImage(file='circle.png')
if sql_process.check_setting('ssi') == 'square':
    uncheckedtask    = PhotoImage(file='square.png')
uncheckedtasksqu = PhotoImage(file='square.png')

unstarredimg     = PhotoImage(file='unstarred.png')
starredimg       = PhotoImage(file='starred.png')
if sql_process.check_setting('ssi') == 'square':
    if sql_process.check_setting('check_icon') == 'jut':
        checkedtask  = PhotoImage(file='check box jut.png')
    elif sql_process.check_setting('check_icon') == 'reg':
        checkedtask  = PhotoImage(file='check box.png')
if sql_process.check_setting('ssi') == 'circle':
    if sql_process.check_setting('check_icon') == 'jut':
        checkedtask  = PhotoImage(file='check_circle.png')
    elif sql_process.check_setting('check_icon') == 'reg':
        checkedtask  = PhotoImage(file='check_circlereg.png')
threedotsimg     = PhotoImage(file='moreinfo.png')
notasksinlistimg = PhotoImage(file='notasksinlist.png')
toggle_onimg     = PhotoImage(file='toggle_on3.png')
toggle_offimg    = PhotoImage(file='toggle_off3.png')
toggle_onimg2    = PhotoImage(file='toggle_on2.png')
toggle_offimg2   = PhotoImage(file='toggle_off2.png')
toggle_onimgwords = PhotoImage(file='toggle_on words.png')
toggle_offimgwords = PhotoImage(file='toggle_off words.png')
paletteimg       = PhotoImage(file='palette.png')
noshowcomptasks  = PhotoImage(file='noshowcomptasks.png')
notaskstodayimg  = PhotoImage(file='notasksduetoday.png')

moreinfoimg      = PhotoImage(file='moreinfo.png')

unstarredsmall   = PhotoImage(file='unstarred small.png')
starredsmall     = PhotoImage(file='starred small.png')
uncheckedsmall   = PhotoImage(file='circle small.png')
checkedsmall     = PhotoImage(file='check_circle small.png')
deletesmall      = PhotoImage(file='delete small.png')
renametasksmall  = PhotoImage(file='edit small.png')
movetosmall      = PhotoImage(file='move_to small.png')
copysmall        = PhotoImage(file='copy small.png')
clock_small      = PhotoImage(file='clock small.png')
toggon_line_small = PhotoImage(file='toggle_on line small.png')
toggoff_line_small = PhotoImage(file='toggle_off line small.png')
calender_small   = PhotoImage(file='calendar_month small.png')
warning_small    = PhotoImage(file='warning small.png')
note_small    = PhotoImage(file='sticky_note small.png')

uncheckedtiny   = PhotoImage(file='circle tiny white.png')
checkedtiny     = PhotoImage(file='check_circle tiny white.png')
deletetiny      = PhotoImage(file='delete tiny white.png')
renametasktiny  = PhotoImage(file='edit tiny white.png')

global meter_alltasks, meter_undonetasks, comptasks
if sql_process.check_setting('auto_hct') == 'n': comptasks = 'showing'
else: comptasks = 'hidden'
meter_list = 'Nothing for now...'
meter_alltasks = 0
meter_undonetasks = 0

global firsttime, firsttime2, firsttime3, songs, tasks_frame, taskstopbarsize, current_design, homewidgetsize, delzoneVar_lists, delzoneVar_corkboard, smart_on
firsttime = 0
firsttime2 = 0
firsttime3 = 0
songs = []

smart_on = 'off'
current_design = 'home'

width = root.winfo_width()
if width >= 1700: homewidgetsize=5
elif width >= 1400 and width <= 1700: homewidgetsize=4
elif width >= 1000 and width <= 1400: homewidgetsize=3
elif width <= 1000 and width >= 700: homewidgetsize=2
elif width <= 700: homewidgetsize=1

delzoneVar_lists = IntVar()
delzoneVar_corkboard = IntVar()

taskstopbarsize = 'showall'
# ----------- Functions -----------
def meter_switchlist(display_name):
    global switchtolist, meter_switchsubheaderL
    meter_switchsubheaderL.config(text=f'to: {display_name}')
    if switchtolist.get() == 'customers':
        meter_switchsubheaderL.config(text=f'to: Default List')
def meter_switch_to():
    global all_lists, switchtolist, switchlistTK, meter_switchsubheaderL, currentlistname
    switchlistTK = Frame(root, bootstyle='default')
    switchlistTK.place(in_=root, anchor='c', relx=.5, rely=.5)
    meter_switchheaderL = Label(switchlistTK, text='Switch lists', font=('Calibri', 20, 'bold'))
    meter_switchheaderL.pack(pady=5, padx=20)
    meter_switchsubheaderL = Label(switchlistTK, text=f'to:', font=('Calibri', 15, 'bold'))
    meter_switchsubheaderL.pack(pady=5, padx=5)

    switch_listsscrl = ScrolledFrame(switchlistTK, bootstyle='default round')
    switch_listsscrl.pack(pady=5, padx=5)

    switchtolist = StringVar()
    switchtolist.set(currentlistname)
    for meter_switch in all_lists:
        switchlistbutton = Button(switch_listsscrl, text=meter_switch[0], bootstyle='info link', command=lambda meter_switch=meter_switch: (switchtolist.set(meter_switch[1]), meter_switchlist(meter_switch[0])))
        switchlistbutton.pack(pady=1, fill=X, padx=5)

    meter_switchokbuttonB = Button(switchlistTK, text='Ok!', command=lambda: (switchlistTK.destroy(), meterokchangeit()))
    meter_switchokbuttonB.pack(fill=X, padx=10, pady=5)
    meter_deleteswitchlistB = Button(switchlistTK, text='X', command=lambda: switchlistTK.destroy())
    meter_deleteswitchlistB.pack(fill=X, padx=10, pady=5)
def meterokchangeit():
    global currentlistname
    currentlistname = switchtolist.get()
    home_design()


def run_clock():
    global current_design, clock_hourL, clock_minuteL, clock_secondL, clock_dateL, clock_dayL
    if current_design == 'home':
        hour = time.strftime("%I")
        min =  time.strftime("%M")
        ampm = time.strftime("%p")
        day =  time.strftime("%A")
        mont = time.strftime("%b")
        daymont = time.strftime("%d")
        sec = time.strftime('%S')
        clock_hourL.config(text=hour)
        clock_minuteL.config(text=f':{min}')
        clock_secondL.config(text=sec)
        clock_dateL.config(text=f'{mont} {daymont}')
        clock_dayL.config(text=day)
        clock_hourL.after(1000, run_clock)


def clear_board():
    global backFrame, tasks_frame
    backFrame.destroy()
    backFrame = Frame(root, bootstyle='dark')
    backFrame.pack(fill=BOTH, expand=True)

    tasks_frame = ScrolledFrame(backFrame, bootstyle='default, round')

def get_tasks(typeofget, listnameget):
    global searchlist_titleE, searchingdot, comptasks, undone_tasks, items, item, hidedonetasksB, currentlistname, firsttime2, tasks_frame, lstnm_hidecomptasksB, lstnm_swilE
    typeofgetwas = 'nothing'
    if firsttime2 == 0:
        currentlistname = 'customers'
        firsttime2 += 1
    if typeofget == 'showhide':
        if comptasks == 'showing':
            comptasks = 'hidden'
            typeofgetwas = 'showhide'
        elif comptasks == 'hidden':
            comptasks='showing'
            typeofgetwas = 'showhide'
        typeofget='none'
    elif typeofget == 'search':
        searchbarlim = lstnm_swilE.get()
        if searchingdot == 'yes':
            searchbarlim = searchlist_titleE.get()
        clear_board()
        undone_tasks = 0
        comptasks = 'showing'
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        items = []
        c.execute("SELECT rowid, * FROM '{}' WHERE task LIKE '{}' ORDER BY checked DESC".format(listnameget, f'%{searchbarlim}%'))
        searchgrabber = c.fetchall()
        for each in searchgrabber:
            items.append(each)
    elif typeofget == 'none':
        clear_board()
        undone_tasks = 0
        items = []
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'y' AND checked = 'unchecked'".format(currentlistname))
        nonegrabberA = c.fetchall()
        for eachA in nonegrabberA:
            items.append(eachA)
        c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'unchecked' AND starred = 'n'".format(currentlistname))
        nonegrabberB = c.fetchall()
        for eachB in nonegrabberB:
            items.append(eachB)

        c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'y' AND checked = 'checked'".format(currentlistname))
        nonegrabberC = c.fetchall()
        for eachC in nonegrabberC:
            items.append(eachC)

        c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'n' AND checked = 'checked'".format(currentlistname))
        nonegrabberD = c.fetchall()
        for eachD in nonegrabberD:
            items.append(eachD)
    else: # List
        clear_board()
        undone_tasks = 0
        items = []
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'y'".format(currentlistname))
        nonegrabberA = c.fetchall()
        for eachA in nonegrabberA:
            items.append(eachA)
        c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'unchecked'".format(currentlistname))
        nonegrabberB = c.fetchall()
        for eachB in nonegrabberB:
            items.append(eachB)

        if comptasks == 'showing':
            c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'checked'".format(currentlistname))
            nonegrabberC = c.fetchall()
            for eachC in nonegrabberC:
                items.append(eachC)

    if typeofgetwas == 'showhide':
        refresh(return_='False')
    #items = c.fetchall()
    #conn.commit()
    #conn.close()
    global numotasks, firsttime3, displaying_something
    displaying_something = 'nothing so far'
    numotasks = 0
    tasks_design()

    '''ordered_items = []

    for thing in items:
        if thing[4] == 'None':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Extra Hard':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Hard':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Medium':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Easy':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Very Easy':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Tedious':
            ordered_items.append(thing)
    for thing in items:
        if thing[4] == 'Unsure':
            ordered_items.append(thing)'''

    for item in items:
        display_task(item, 'Normal List', currentlistname)

    if displaying_something == 'nothing so far':
        notaskshere2L = Label(tasks_frame, image=noshowcomptasks)
        notaskshere2L.pack()
    if items == []:
        notaskshereL = Label(tasks_frame, image=notasksinlistimg)
        notaskshereL.pack()
        notaskshere2L.destroy()
    firsttime3 += 1


def taskefocusin(e):
    global taskE
    if taskE.get() == '+ Add Task':
        taskE.config(justify='left', bootstyle='danger')
        taskE.delete(0, END)
    else:
        pass
def taskefocusout(e):
    global taskE
    if taskE.get() == '':
        taskE.config(justify='center', bootstyle='light')
        taskE.insert(0, '+ Add Task')
    else:
        pass


def tasks_design():
    clear_board()
    global current_design, smart_on, tasksleftL
    current_design = 'tasks'
    tasksleftL.config(text='               List')
    # ----------- Task Details Bar -----------
    global TDB_F, TDBnoshow, taskE, lstnmNameL, lstnmeditB, lstnmdeleteB, tasks_frame, currentlistname, lstnm_hidecomptasksB, lstnm_swilE
    TDB_F = ScrolledFrame(backFrame, bootstyle='Default, round', width=200, autohide=True)
    TDB_F.pack(fill=Y, side=RIGHT)

    TDBnoshow = Label(TDB_F, bootstyle='secondary', text="Click on a task to\nsee it's details.", font=('Calibri', 17, 'bold'), foreground='white')
    TDBnoshow.grid()

    # ----------- List Name Bar -----------
    global list_nameF, currentlistname
    list_nameF = Frame(backFrame, bootstyle='default')
    list_nameF.pack(fill=X)
    try:
        if currentlistname == 'hi':
            print('zimpa')
    except:
        currentlistname = 'customers'
    lstnmNameL = Label(list_nameF, text=sql_process.get_current_list_display(currentlistname)[0], bootstyle='default', font=('Calibri', 30, 'bold'))
    lstnmNameL.pack(side=LEFT, padx=15)


    global swilF, lstnm_hidecomptasksB, lstnmeditB, lstnmdeleteB, rando_sep, lstnmmoreinfoB
    rando_sep = Separator(list_nameF, orient='vertical', bootstyle='secondary')
    rando_sep.pack(side=LEFT)
        #swil = search within list
    swilF = Frame(list_nameF, bootstyle='default')
    swilF.pack(side=LEFT, padx=15)
    lstnm_swilE = Entry(swilF, bootstyle='secondary', font=('Calibri light', 10))
    lstnm_swilE.grid(row=0, column=0, padx=5)

    lstnm_swil_goB = Button(swilF, text='Go!', bootstyle='secondary outline', command=lambda: get_tasks('search', currentlistname))
    lstnm_swil_goB.grid(row=0, column=1, padx=0)

    lstnm_hidecomptasksB = Button(swilF, text='Show/hide completed tasks', bootstyle='primary outline', command=lambda: get_tasks('showhide', list))
    lstnm_hidecomptasksB.grid(row=0, column=2, padx=20)

    lstnmeditB = Button(list_nameF, image=renametaskimg, command=lambda: renamelist(), bootstyle='secondary outline')
    lstnmeditB.pack(side=RIGHT, padx=5)

    lstnmdeleteB = Button(list_nameF, image=deletetask, command=lambda: droplist(), bootstyle='secondary outline')
    lstnmdeleteB.pack(side=RIGHT, padx=5)

    lstnmmoreinfoB = Button(list_nameF, image=moreinfoimg, bootstyle='secondary outline', command=lambda: open_more_tasksmenu())

    if root.winfo_width() < 1200:
        global taskstopbarsize
        rando_sep.pack_forget()
        swilF.pack_forget()
        lstnm_hidecomptasksB.pack_forget()
        lstnmeditB.pack_forget()
        lstnmdeleteB.pack_forget()

        lstnmmoreinfoB.pack(side=RIGHT, padx=5)
        taskstopbarsize = 'showless'

    if currentlistname == 'customers':
        lstnmeditB.config(state=DISABLED)
        lstnmdeleteB.config(state=DISABLED)

    if smart_on != 'off':
        lstnm_hidecomptasksB.destroy()
        swilF.pack_forget()
        lstnmeditB.pack_forget()
        lstnmdeleteB.pack_forget()
        rando_sep.pack_forget()

    if smart_on == 'starred':
        lstnmNameL.config(text='Starred')
    if smart_on == 'everything':
        lstnmNameL.config(text='Everything')
    if smart_on == 'unchecked':
        lstnmNameL.config(text='Unchecked')
    if smart_on == 'duetoday':
        lstnmNameL.config(text='Due Today')

    # ----------- Frame for tasks -----------
    tasks_frame.pack(fill=BOTH, expand=True)

    # ----------- Add Task Bar -----------
    newtaskF = Frame(backFrame, bootstyle='default')
    newtaskF.pack(fill=X, side=BOTTOM)

    taskE = Entry(newtaskF, font=('Calibri', 20), bootstyle='light', justify='center')
    taskE.pack(side=RIGHT, fill=X, expand=True)
    taskE.bind('<Return>', add_task)
    taskE.bind('<FocusIn>', taskefocusin)
    taskE.bind('<FocusOut>', taskefocusout)
    taskE.insert(0, '+ Add Task')

# ---------- Home screen layout: fluid resize with column snapping ----------

HOME_WIDGETS_ORDER = ['meter', 'clock', 'alltasks', 'displist', 'quicksett']

def get_home_col_count(width, current_cols):
    """Decide how many columns the home grid should use.
    Uses different thresholds going up vs down (hysteresis) so it
    doesn't flicker back and forth right at the edge."""
    if current_cols is None:
        return 3 if width > 1150 else 2

    if current_cols == 2 and width > 1150:
        return 3
    if current_cols == 3 and width < 1000:
        return 2
    return current_cols


def apply_home_layout(cols):
    global meterwidgetF, clockwidgetF, alltaskseqlF, displistF, quicksettF, home_middleF

    widget_map = {
        'meter': meterwidgetF,
        'clock': clockwidgetF,
        'alltasks': alltaskseqlF,
        'displist': displistF,
        'quicksett': quicksettF,
    }

    target = home_middleF.inner

    for i in range(5):
        target.grid_columnconfigure(i, weight=0, uniform='')

    for i in range(cols):
        target.grid_columnconfigure(i, weight=1, uniform='homecol')

    for i, key in enumerate(HOME_WIDGETS_ORDER):
        w = widget_map[key]
        w.grid(row=i // cols, column=i % cols, padx=15, pady=15, sticky='nsew')


_home_resize_job = None

def on_home_resize(e=None):
    """Debounced resize handler — waits for resizing to settle before
    recalculating, so dragging the window doesn't stutter."""
    global _home_resize_job
    if current_design != 'home':
        return
    if _home_resize_job:
        root.after_cancel(_home_resize_job)
    _home_resize_job = root.after(120, do_home_relayout)


def do_home_relayout():
    global homewidgetsize
    width = root.winfo_width()
    new_cols = get_home_col_count(width, homewidgetsize)
    if new_cols != homewidgetsize:
        homewidgetsize = new_cols
        apply_home_layout(new_cols)

def quick_toggle(rowid, listname):
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("SELECT checked FROM '{}' WHERE rowid=?".format(listname), (rowid,))
    status = c.fetchone()[0]
    new_status = 'checked' if status == 'unchecked' else 'unchecked'
    c.execute("UPDATE '{}' SET checked=? WHERE rowid=?".format(listname), (new_status, rowid))
    conn.commit()
    conn.close()
    home_design()

class VStretchScrollFrame(Frame):
    """Scrolls vertically only when content overflows; content stretches
    to fill the available width but keeps its natural height."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vscroll = Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.canvas.pack(side='left', fill='both', expand=True)

        self.inner = Frame(self.canvas, bootstyle='dark')
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')

        self.inner.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self._update_scrollbar()

    def _on_canvas_configure(self, event):
        # stretch inner frame to match canvas width -> horizontal fill
        self.canvas.itemconfig(self.inner_id, width=event.width)
        self._update_scrollbar()

    def _update_scrollbar(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox('all')
        if not bbox:
            return
        content_height = bbox[3] - bbox[1]
        visible_height = self.canvas.winfo_height()
        if content_height > visible_height:
            self.vscroll.pack(side='right', fill='y')
        else:
            self.vscroll.pack_forget()

def quick_add_task(text, listname):
    text = text.strip()
    if not text:
        return
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(listname),
              {'words': text, 'checked': 'unchecked', 'starred': 'n', 'difficulty': sql_process.check_setting('def_difficulty'),
               'duedateday': time.strftime("%x"), 'duedatetime': '1200', 'duedateonoff': sql_process.check_setting('def_duedateonoff'),
               'amiaministep': 'no', 'whichminiami': 'notamini', 'importance': '1', 'notes': sql_process.check_setting('def_note')})
    conn.commit()
    conn.close()
    home_design()

def home_design(e=None):
    clear_board()
    global current_design
    current_design = 'home'
    global song_detailsL, song_box, playB, song_timeL, currentlistname, meterwidgetF, song_nameL, tasksleftL, home_middleF
    tasksleftL.configure(text='             Home')

    if currentlistname == 'a':
        currentlistname = 'customers'
    home_header = Label(backFrame, text=sql_process.check_setting('hht'), bootstyle='dark inverse', font=('Calibri', 30, 'bold'))
    if sql_process.check_setting('hhto') == 'y':
        home_header.pack()

    home_middleF = VStretchScrollFrame(backFrame, bootstyle='dark')
    home_middleF.pack(fill=BOTH, expand=True)

    # -------- Widget #1: Meter Widget -------
    meterwidgetF = Frame(home_middleF.inner, bootstyle='default')
    meterwidgetF.grid(row=0, column=0, pady=30, padx=30, sticky='nsew')

    conn = sqlite3.connect('info.db')
    c = conn.cursor()

    c.execute("SELECT rowid, * FROM '{}' WHERE amiaministep='no' ".format(currentlistname))
    meteritems = c.fetchall()
    meter_undonetasks = 0
    meter_alltasks = 0
    for item in meteritems:
        meter_alltasks += 1
        if item[2] == 'unchecked':
            meter_undonetasks += 1


    if meter_alltasks > 0:
        actual_meter = Meter(meterwidgetF, bootstyle='info', subtext='Tasks Completed', interactive=False, amountused=meter_alltasks-meter_undonetasks, textright=f'/{meter_alltasks}', amounttotal=meter_alltasks, subtextstyle='light')
        actual_meter.pack(pady=15, padx=30)
    else:
        mw_notasksinlistErrorNotification = Label(meterwidgetF, text=f"No tasks in list '{sql_process.get_current_list_display(currentlistname)[0]}'", bootstyle='danger', font=('Calibri', 15, 'bold'))
        mw_notasksinlistErrorNotification.pack(pady=15, padx=30)

    toolbar_meterF = Frame(meterwidgetF, bootstyle='default')
    toolbar_meterF.pack(fill=X, pady=10)

    mw_listdisplaying = Label(toolbar_meterF, text=sql_process.get_current_list_display(currentlistname)[0], bootstyle='info', font=('Calibri', 15, 'bold'))
    mw_listdisplaying.grid(row=0, column=0, pady=15, padx=30)

    mw_change_list_displaying = Button(toolbar_meterF, text='Change...', bootstyle='info outline', command=lambda: meter_switch_to())
    mw_change_list_displaying.grid(row=0, column=1, pady=15, padx=30)

    if meter_undonetasks > 0:
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("SELECT task FROM '{}' WHERE checked='unchecked' AND amiaministep='no' ORDER BY starred DESC LIMIT 1".format(currentlistname))
        next_task = c.fetchone()
        if next_task:
            Label(meterwidgetF, text=f"Next task: {next_task[0]}", bootstyle='light', font=('Calibri', 12)).pack(pady=(0,10))

    # ----------- Widget #2: Clock Widget --------------
    global clockwidgetF, clock_hourL, clock_minuteL, clock_secondL, clock_dateL, clock_dayL
    clockwidgetF = Frame(home_middleF.inner, bootstyle='default')
    clockwidgetF.grid(row=0, column=1, pady=30, padx=0, sticky='nsew')

    clock_mainF = Frame(clockwidgetF, bootstyle='default')
    clock_mainF.pack()
    clock_hourL = Label(clock_mainF, text='......', bootstyle='info', font=('Calibri',  60))
    clock_hourL.grid(row=0, column=0)
    clock_minuteL = Label(clock_mainF, text='', bootstyle='info', font=('Calibri',  60))
    clock_minuteL.grid(row=0, column=1)
    clock_secondL = Label(clockwidgetF, text='Please hold while\nClock is loading...', bootstyle='light', font=('Calibri',  30))
    clock_secondL.pack(padx=50, pady=5)
    clock_dayL = Label(clockwidgetF, text='. .\nU', bootstyle='warning', font=('Calibri',  30, 'bold'))
    clock_dayL.pack(padx=50, pady=5)
    clock_dateL = Label(clockwidgetF, text='. .\nU', bootstyle='warning', font=('Calibri',  30))
    clock_dateL.pack(padx=70, pady=5)

    #---------- Widget #3: All tasks equal... -------------
    global alltaskseqlF
    alltaskseqlF = Frame(home_middleF.inner, bootstyle='default')
    alltaskseqlF.grid(row=0, column=2, pady=30, padx=30, sticky='nsew')

    alltaskseqlheaderL = Label(alltaskseqlF, text='Altogether', font=('Calibri', 30))
    alltaskseqlheaderL.pack(pady=10, padx=20)

    alltaskseql_listsF = ScrolledFrame(alltaskseqlF, bootstyle='default')
    alltaskseql_listsF.pack(pady=0, padx=20)
    tasksinlists = 0
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("SELECT * FROM sqlite_master WHERE type='table'")
    alltaskseql_listsgrabber = c.fetchall()
    for individ_list in alltaskseql_listsgrabber:
        taskinlist=0
        c.execute("SELECT rowid, * FROM '{}' WHERE checked='unchecked' AND amiaministep='no' ".format(individ_list[1]))
        alltaskseql_tasksgrabber = c.fetchall()
        for individ_task in alltaskseql_tasksgrabber:
            taskinlist+=1
            tasksinlists+=1
        #Label(alltaskseql_listsF, text=f'{sql_process.get_current_list_display(individ_list[1])[0]} - {taskinlist}', font=('Calibri', 15)).pack(padx=2, pady=2)
        listbtn = Button(alltaskseql_listsF, text=f'{sql_process.get_current_list_display(individ_list[1])[0]} - {taskinlist}',
                  bootstyle='link',
                  command=lambda ln=individ_list[1]: (globals().__setitem__('currentlistname', ln), home_design()))
        listbtn.pack(padx=2, pady=2, fill=X)

    Separator(alltaskseqlF, bootstyle='secondary').pack(fill=X, padx=10, pady=0)

    alltaskseqltotalL = Label(alltaskseqlF, text=f'Total: {tasksinlists} tasks to go!', font=('Calibri', 15))
    alltaskseqltotalL.pack(pady=10, padx=20)


    # --------- Widget #4: Display the list of your choice ---------
    global displistF
    displistF = Frame(home_middleF.inner, bootstyle='default')
    displistF.grid(row=1, column=0, pady=0, padx=30, sticky='nsew')

    displist_headerF = Frame(displistF, bootstyle='default')
    displist_headerF.pack(fill=X, expand=True)

    disp_list_Listname = Label(displist_headerF, text=sql_process.get_current_list_display(currentlistname)[0], font=('Calibri', 15, 'bold'))
    disp_list_Listname.pack(side=LEFT, padx=10, pady=10)

    disp_list_changename = Button(displist_headerF, text='Change...', bootstyle='info outline', command=lambda: meter_switch_to())
    disp_list_changename.pack(side=RIGHT, padx=10, pady=10)

    Separator(displistF, bootstyle='secondary').pack(fill=X, padx=10, pady=5)

    displist_tasksF = ScrolledFrame(displistF, bootstyle='default round')
    displist_tasksF.pack(fill=BOTH, expand=True)

    homeitems = []
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'y' and checked='unchecked' AND amiaministep='no' ".format(currentlistname))
    nonegrabberA = c.fetchall()
    for eachA in nonegrabberA:
        homeitems.append(eachA)
    c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'unchecked' and starred='n' AND amiaministep='no' ".format(currentlistname))
    nonegrabberB = c.fetchall()
    for eachB in nonegrabberB:
        homeitems.append(eachB)

    c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'checked' and starred='y' AND amiaministep='no' ".format(currentlistname))
    nonegrabberC = c.fetchall()
    for eachC in nonegrabberC:
        homeitems.append(eachC)

    c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'checked' and starred='n' AND amiaministep='no' ".format(currentlistname))
    nonegrabberD = c.fetchall()
    for eachD in nonegrabberD:
        homeitems.append(eachD)

    homedisplistgridrow = 0
    for single_homeitem in homeitems:
        home_listwidgetB = Button(displist_tasksF, image=uncheckedsmall, bootstyle='danger outline',
                           command=lambda rowid=single_homeitem[0]: quick_toggle(rowid, currentlistname))
        home_listwidgetB.grid(row=homedisplistgridrow, column=0, padx=2, pady=5)
        home_listwidgetL = Label(displist_tasksF, text=single_homeitem[1], bootstyle='danger', font=('Calibri', 15))
        home_listwidgetL.grid(row=homedisplistgridrow, column=1, sticky='w', padx=2, pady=10)

        homedisplistgridrow += 1

        if single_homeitem[2] == 'checked' and single_homeitem[3] == 'n':
            home_listwidgetB.config(bootstyle='success outline', image=checkedsmall)
            home_listwidgetL.config(bootstyle='success', font=('Calibri', 15, 'overstrike'))
        elif single_homeitem[2] == 'checked' and single_homeitem[3] == 'y':
            home_listwidgetB.config(bootstyle='warning outline', image=checkedsmall)
            home_listwidgetL.config(bootstyle='warning', font=('Calibri', 15, 'overstrike'))
        elif single_homeitem[2] == 'unchecked' and single_homeitem[3] == 'y':
            home_listwidgetB.config(bootstyle='info outline')
            home_listwidgetL.config(bootstyle='info')

    # --------- Widget #5: Quick Settings ---------
    global quicksettF
    quicksettF = Frame(home_middleF.inner, bootstyle='default')
    quicksettF.grid(row=1, column=1, pady=0, padx=0, sticky='nsew')

    quickadd_L = Label(quicksettF, text='Quick Add', font=('Calibri', 20, 'bold'))
    quickadd_L.pack(fill='y', pady=30, padx=20)

    quickadd_E = Entry(quicksettF, font=('Calibri', 16), justify='center', bootstyle='light')
    quickadd_E.pack(fill='both', padx=10, pady=0)
    quickadd_E.bind('<Return>', lambda e: quick_add_task(quickadd_E.get(), currentlistname))

    quickadd_adding_to_list_L = Label(quicksettF, text=f'Adding to list: {sql_process.get_current_list_display(currentlistname)[0]}', font=('Calibri', 12))
    quickadd_adding_to_list_L.pack(fill='y', pady=30, padx=20)

    # -- END OF WIDGETS --

    # -------- Sizings ----------
    global homewidgetsize
    width = root.winfo_width()
    homewidgetsize = get_home_col_count(width, None)
    apply_home_layout(homewidgetsize)

    run_clock()

def def_difficulty_edit(new_def):
    if new_def == 'None' or new_def == 'Very Easy' or new_def == 'Easy' or new_def == 'Medium' or new_def == 'Hard' or new_def == 'Extra Hard' or new_def == 'Tedious' or new_def == 'Unsure':
        sql_process.setting_configure('def_difficulty', new_def)
        settings()
def delzonego(listsyn, corkboardyn):
    print(f'Lists: {listsyn}\nCorkboard: {corkboardyn}')
    if listsyn == 1:
        print('Deleting Lists...')
        all_lists = sql_process.get_lists()
        for list in all_lists:
            if list[1] != 'customers':
                print(f'See ya around! {list[0]}')
                sql_process.delete_list(list[1])
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute('''DELETE FROM customers''')
        conn.commit()
        refresh(return_='False')
    if corkboardyn == 1:
        print('See ya around!')
        for path in sql_process.get_all_image_paths():
            delete_image_file(path)
        conn_user000 = sqlite3.connect('user000.db')
        c_user000 = conn_user000.cursor()
        c_user000.execute('''DELETE FROM corkboard''')
        conn_user000.commit()
        refresh(return_='False')


    deletionzone_responseF = Frame(root, bootstyle='default')
    deletionzone_responseF.place(in_=root, anchor='c', relx=.5, rely=.5)

    deletionzone_responseL = Label(deletionzone_responseF, text='Command(s) have been carried out successfully.', font=('Calibri', 20))
    deletionzone_responseL.pack(padx=20, pady=20)

    deletionzone_timeL = Label(deletionzone_responseF, text='(3)', font=('Calibri', 20))
    deletionzone_timeL.pack(padx=20, pady=20)

    xx = 4
    for xxx in range(3):
        xx -= 1
        deletionzone_timeL.config(text=f'({xx})')
        root.update()
        time.sleep(1)
    deletionzone_responseF.destroy()
def delcomptasksgo(list_name):
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("SELECT rowid FROM '{}' WHERE amiaministep='no' AND checked='checked'".format(list_name))
    grab_dct = c.fetchall()
    print(grab_dct)
    for task in grab_dct:
        c.execute("DELETE from '{}' WHERE rowid='{}'".format(list_name, task[0]))
        conn.commit()
        c.execute("DELETE from '{}' WHERE whichminiami='{}'".format(list_name, task[0]))
        conn.commit()
    conn.close()

    settings()

    dct_responseF = Frame(root, bootstyle='default')
    dct_responseF.place(in_=root, anchor='c', relx=.5, rely=.5)

    dct_responseL = Label(dct_responseF, text='Command executed successfully.', font=('Calibri', 20))
    dct_responseL.pack(padx=20, pady=20)

    dct_timeL = Label(dct_responseF, text='This message will close automatically in 3 seconds.', font=('Calibri', 15))
    dct_timeL.pack(padx=20, pady=20)

    xx = 4
    for xxx in range(3):
        xx -= 1
        dct_timeL.config(text=f'This message will close automatically in {xx} seconds.')
        root.update()
        time.sleep(1)
    dct_responseF.destroy()

def settings():
    global backFrame, tasks_frame, current_design, delzoneVar_lists, delzoneVar_corkboard, tasksleftL
    tasksleftL.configure(text='            Settings')
    clear_board()
    current_design = 'settings'

    tasks_frame.pack(fill=BOTH, expand=True)

    settingsheaderL = Label(tasks_frame, text='Settings', font=('Calibri', 40, 'bold'), bootstyle='danger')
    settingsheaderL.pack(fill=X, expand=True)

    # ---------- DELETING METHODS ----------
    deleteing_lblfrme = Labelframe(tasks_frame, text='Deleting Methods')
    deleteing_lblfrme.pack(fill=X, padx=10, pady=10)
    # ----- ABD: Ask before delete tasks -----
    abdB = Button(deleteing_lblfrme, image=toggle_offimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('abd', 'y'), settings()))
    abdB.grid(row=0, column=0)

    if sql_process.check_setting('abd') == 'y':
        abdB.config(image=toggle_onimg, command=lambda: (sql_process.setting_configure('abd', 'n'), settings()))

    abdL = Label(deleteing_lblfrme, text='Ask before delete (Tasks)', font=('Calibri', 16))
    abdL.grid(row=0, column=1)

    # ----- ABDL: Ask before delete lists -----
    abdlB = Button(deleteing_lblfrme, image=toggle_offimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('abdl', 'y'), settings()))
    abdlB.grid(row=1, column=0)

    if sql_process.check_setting('abdl') == 'y':
        abdlB.config(image=toggle_onimg, command=lambda: (sql_process.setting_configure('abdl', 'n'), settings()))

    abdlL = Label(deleteing_lblfrme, text='Ask before delete (Lists)', font=('Calibri', 16))
    abdlL.grid(row=1, column=1)


    # ----- DELZONE: Deletion Zone -----
    delzone_lblfrme = LabelFrame(deleteing_lblfrme, text='Deletion Zone')
    delzone_lblfrme.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

    delzone_subheaderL = Label(delzone_lblfrme, text="Check all which are to be permanently erased and click 'Delete.'.", font=('Calibri', 16))
    delzone_subheaderL.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

    delzone_lists_CheckB = Checkbutton(delzone_lblfrme, bootstyle='success', text='Lists/Tasks', variable=delzoneVar_lists, onvalue=1, offvalue=0)
    delzone_lists_CheckB.grid(row=1, column=0, sticky='w', padx=10, pady=5)


    delzone_corkboard_CheckB = Checkbutton(delzone_lblfrme, bootstyle='success', text='Corkboard', variable=delzoneVar_corkboard, onvalue=1, offvalue=0)
    delzone_corkboard_CheckB.grid(row=2, column=0, sticky='w', padx=10, pady=5)

    delzone_go1B = Button(delzone_lblfrme, bootstyle='info outline', text='Delete.', command=lambda: (delzone_go1B.destroy(), delzone_go2B.grid(row=1, column=1, rowspan=3, sticky='nsew', padx=10, pady=5)))
    delzone_go1B.grid(row=1, column=1, rowspan=3, sticky='nsew', padx=10, pady=5)

    delzone_go2B = Button(delzone_lblfrme, bootstyle='primary outline', text='Are you sure?', command=lambda: (delzone_go2B.destroy(), delzone_go3B.grid(row=1, column=1, rowspan=3, sticky='nsew', padx=10, pady=5)))

    delzone_go3B = Button(delzone_lblfrme, bootstyle='danger outline', text='Last chance!', command=lambda: delzonego(delzoneVar_lists.get(), delzoneVar_corkboard.get()))

    delzone_sep = Separator(delzone_lblfrme, bootstyle='info')
    delzone_sep.grid(row=3, column=0, columnspan=2, sticky='nsew', padx=10)

    delzone_subheader2L = Label(delzone_lblfrme, text="Delete completed tasks. Choose List.", font=('Calibri', 16))
    delzone_subheader2L.grid(row=4, column=0, columnspan=2, padx=10, pady=10)


    #delete completed tasks radiobutton frame
    delcomptasks_rbs_F = Frame(delzone_lblfrme)
    delcomptasks_rbs_F.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

    delcomptasksVar = StringVar()
    delcomptasksVar.set('-Select-')

    for list in sql_process.get_lists():
        Radiobutton(delcomptasks_rbs_F, bootstyle='warning', variable=delcomptasksVar, text=list[0], value=list[1]).grid(sticky='w', pady=3)

    delcompttasks_go1B = Button(delzone_lblfrme, bootstyle='primary outline', text='Delete completed tasks (Cannot be undone).', command=lambda: delcomptasksgo(delcomptasksVar.get()))
    delcompttasks_go1B.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')


    #delzone_chooselistDD
    #lists,corkboard

    # ---------- CORKBOARD ----------
    cork_lblfrme = Labelframe(tasks_frame, text='Corkboard')
    cork_lblfrme.pack(fill=X, padx=10, pady=10)

    # ----- CORK: Corkboard -----
    corkB = Button(cork_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('crk', 'n'), settings(), lock_crk()))
    corkB.grid(row=0, column=0)

    if sql_process.check_setting('crk') == 'n':
        corkB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('crk', 'y'), settings(), unlock_crk()))


    corkL = Label(cork_lblfrme, text='Corkboard', font=('Calibri', 16))
    corkL.grid(row=0, column=1)

    # ----- CORKSTART: Start on Corkboard -----
    start_corkB = Button(cork_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('socork', 'n'), settings()))
    start_corkB.grid(row=1, column=0)

    if sql_process.check_setting('socork') == 'n':
        start_corkB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('socork', 'y'), settings()))


    start_corkL = Label(cork_lblfrme, text='Open Corkboard on startup (Corkboard must be on)', font=('Calibri', 16))
    start_corkL.grid(row=1, column=1, columnspan=2)

    # ---------- OTHER ----------
    other_lblfrme = Labelframe(tasks_frame, text='Other')
    other_lblfrme.pack(fill=X, padx=10, pady=10)

    # ----- HHT: Home header text -----
    hhtB = Button(other_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('hhto', 'n'), settings()))
    hhtB.grid(row=0, column=0)

    if sql_process.check_setting('hhto') == 'n':
        hhtB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('hhto', 'y'), settings()))

    hhtL = Label(other_lblfrme, text='Home header text', font=('Calibri', 16))
    hhtL.grid(row=0, column=1)

    hhtE = Entry(other_lblfrme, font=('Calibri', 16))
    hhtE.grid(row=0, column=2, padx=10)
    hhtE.insert(0, sql_process.check_setting('hht'))

    hht2B = Button(other_lblfrme, text='Save', bootstyle='info link', command=lambda: (sql_process.setting_configure('hht', hhtE.get()), settings()))
    hht2B.grid(row=0, column=3)

    # ----- auto_hct: Automatically Hide Completed Tasks -----
    auto_hctB = Button(other_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('auto_hct', 'n'), settings()))
    auto_hctB.grid(row=1, column=0)

    if sql_process.check_setting('auto_hct') == 'n':
        auto_hctB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('auto_hct', 'y'), settings()))

    auto_hctL = Label(other_lblfrme, text='Automatically Hide Completed Tasks', font=('Calibri', 16))
    auto_hctL.grid(row=1, column=1, columnspan=2)

    # ----- tsd: Task Side Display -----
    '''tsdB = Button(other_lblfrme, text='Difficulty', bootstyle='success toolbutton', command=lambda: (sql_process.setting_configure('tsd', 'difficulty'), settings()))
    tsdB.grid(row=2, column=0, pady=10, padx=5)

    if sql_process.check_setting('tsd') == 'difficulty':
        tsdB.config(bootstyle='success outline')

    tsdL = Label(other_lblfrme, text='Task Side Display', font=('Calibri', 16))
    tsdL.grid(row=2, column=1, columnspan=2, pady=10)

    tsdB = Button(other_lblfrme, text='Due Date', bootstyle='success toolbutton', command=lambda: (sql_process.setting_configure('tsd', 'duedate'), settings()))
    tsdB.grid(row=2, column=3, pady=10)

    if sql_process.check_setting('tsd') == 'duedate':
        tsdB.config(bootstyle='success outline')'''

    # ----- ctcm: Completing task completes minis -----
    ctcmB = Button(other_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('ctcm', 'n'), settings()))
    ctcmB.grid(row=2, column=0, pady=10)

    if sql_process.check_setting('ctcm') == 'n':
        ctcmB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('ctcm', 'y'), settings()))

    ctcmL = Label(other_lblfrme, text='Completing task completes mini steps', font=('Calibri', 16))
    ctcmL.grid(row=2, column=1, pady=10, columnspan=2)


    # ----- check_icon: Choose the appearence of the checked icon -----
    check_iconB = Button(other_lblfrme, image=jut_img, bootstyle='success toolbutton', command=lambda: (sql_process.setting_configure('check_icon', 'jut'), refresh(return_='False'), settings()))
    check_iconB.grid(row=3, column=0, pady=10, padx=5)
    if sql_process.check_setting('check_icon') == 'jut':
        check_iconB.config(bootstyle='success outline')

    check_iconL = Label(other_lblfrme, text='Choose the appearence of the checked icon', font=('Calibri', 16))
    check_iconL.grid(row=3, column=1, columnspan=2, pady=10)

    check_icon2B = Button(other_lblfrme, image=reg_img, bootstyle='success toolbutton', command=lambda: (sql_process.setting_configure('check_icon', 'reg'), refresh(return_='False'), settings()))
    check_icon2B.grid(row=3, column=3, pady=10)

    if sql_process.check_setting('check_icon') == 'reg':
        check_icon2B.config(bootstyle='success outline')

    if sql_process.check_setting('ssi') == 'square':
        check_iconB.config(image=jut_img_squ)
        check_icon2B.config(image=reg_img_squ)

    # ----- ssi: Shape Status Icon -----
    status_circle_B = Button(other_lblfrme, image=circleimg, bootstyle='success toolbutton', command=lambda: (sql_process.setting_configure('ssi', 'circle'), refresh(return_='False'), settings()))
    status_circle_B.grid(row=4, column=0, pady=10, padx=5)
    if sql_process.check_setting('ssi') == 'circle':
        status_circle_B.config(bootstyle='success outline')

    check_iconL = Label(other_lblfrme, text='Choose the shape of the checked/unchecked icon', font=('Calibri', 16))
    check_iconL.grid(row=4, column=1, columnspan=2, pady=10)

    status_square_B = Button(other_lblfrme, image=uncheckedtasksqu, bootstyle='success toolbutton', command=lambda: (sql_process.setting_configure('ssi', 'square'), refresh(return_='False'), settings()))
    status_square_B.grid(row=4, column=3, pady=10)

    if sql_process.check_setting('ssi') == 'square':
        status_square_B.config(bootstyle='success outline')


    # ---------- SMART LISTS ----------
    smartlist_lblfrme = Labelframe(tasks_frame, text='Smart Lists')
    smartlist_lblfrme.pack(fill=X, padx=10, pady=10)

    # ----- sl_str: Starred -----
    sl_strB = Button(smartlist_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('sl_str', 'n'), lock_sl_str(), settings()))
    sl_strB.grid(row=0, column=0)

    if sql_process.check_setting('sl_str') == 'n':
        sl_strB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('sl_str', 'y'), unlock_sl_str(), settings()))

    sl_strL = Label(smartlist_lblfrme, text='Starred', font=('Calibri', 16))
    sl_strL.grid(row=0, column=1)

    # ----- sl_evr: Starred -----
    sl_evrB = Button(smartlist_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('sl_evr', 'n'), lock_sl_evr(), settings()))
    sl_evrB.grid(row=1, column=0)

    if sql_process.check_setting('sl_evr') == 'n':
        sl_evrB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('sl_evr', 'y'), unlock_sl_evr(), settings()))

    sl_evrL = Label(smartlist_lblfrme, text='Everything', font=('Calibri', 16))
    sl_evrL.grid(row=1, column=1)

    # ----- sl_unch: Starred -----
    sl_unchB = Button(smartlist_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('sl_unch', 'n'), lock_sl_unch(), settings()))
    sl_unchB.grid(row=2, column=0)

    if sql_process.check_setting('sl_unch') == 'n':
        sl_unchB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('sl_unch', 'y'), unlock_sl_unch(), settings()))

    sl_unchL = Label(smartlist_lblfrme, text='Unchecked', font=('Calibri', 16))
    sl_unchL.grid(row=2, column=1)

    # ----- sl_dtdy: Due Today -----
    sl_dtdyB = Button(smartlist_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('sl_dtdy', 'n'), lock_sl_dtdy(), settings()))
    sl_dtdyB.grid(row=3, column=0)

    if sql_process.check_setting('sl_dtdy') == 'n':
        sl_dtdyB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('sl_dtdy', 'y'), unlock_sl_dtdy(), settings()))

    sl_dtdyL = Label(smartlist_lblfrme, text='Due Today', font=('Calibri', 16))
    sl_dtdyL.grid(row=3, column=1)


    # ---------- ADD TASK DEFAULTS ----------
    addtaskdefaults_lblfrme = Labelframe(tasks_frame, text='Add Task Defaults')
    addtaskdefaults_lblfrme.pack(fill=X, padx=10, pady=10)

    addtaskdefaultssubheader = Label(addtaskdefaults_lblfrme, text="When adding a task, set a default for a specific thing. Example: If you set the default for difficulty to be 'Hard', then when you add a task the difficulty will be 'Hard'.", wraplength=500)
    addtaskdefaultssubheader.grid(row=0, column=0, columnspan=3)

    # ----- def_difficulty: Default (of) Difficulty -----
    def_difficultyL = Label(addtaskdefaults_lblfrme, text='Difficulty', font=('Calibri', 16))
    def_difficultyL.grid(row=1, column=0, pady=5, sticky='e')

    def_difficulty_combobox = Combobox(addtaskdefaults_lblfrme, bootstyle='secondary', width=17, font=('Calibri', 17), values=['None', 'Very Easy', 'Easy', 'Medium', 'Hard', 'Extra Hard', 'Tedious', 'Unsure'])
    def_difficulty_combobox.grid(row=1, column=1, padx=10, pady=5)
    def_difficulty_combobox.insert(0, sql_process.check_setting('def_difficulty'))

    def_difficultyB = Button(addtaskdefaults_lblfrme, text='Save', bootstyle='info link', command=lambda: def_difficulty_edit(def_difficulty_combobox.get()))
    def_difficultyB.grid(row=1, column=2, pady=5)

    # ----- def_duedateonoff: Default (of) Due date on/off -----
    def_duedateonoffB = Button(addtaskdefaults_lblfrme, image=toggle_onimgwords, bootstyle='success link', command=lambda: (sql_process.setting_configure('def_duedateonoff', 'off'), settings()))
    def_duedateonoffB.grid(row=2, column=1, pady=5, sticky='w')
    if sql_process.check_setting('def_duedateonoff') == 'off':
        def_duedateonoffB.config(image=toggle_offimgwords, command=lambda: (sql_process.setting_configure('def_duedateonoff', 'on'), settings()))

    def_duedateonoffL = Label(addtaskdefaults_lblfrme, text='Due Date On/Off', font=('Calibri', 16))
    def_duedateonoffL.grid(row=2, column=0, pady=5, sticky='e')

    # ----- def_note: Default (of) Note -----
    def_noteL = Label(addtaskdefaults_lblfrme, text='Note', font=('Calibri', 16))
    def_noteL.grid(row=3, column=0, pady=5, sticky='e')

    def_noteE = Entry(addtaskdefaults_lblfrme, font=('Calibri', 16))
    def_noteE.grid(row=3, column=1, padx=10, pady=5)
    def_noteE.insert(0, sql_process.check_setting('def_note'))

    def_noteB = Button(addtaskdefaults_lblfrme, text='Save', bootstyle='info link', command=lambda: (sql_process.setting_configure('def_note', def_noteE.get()), settings()))
    def_noteB.grid(row=3, column=2, pady=5)

    # ---------- PASSWORD ----------
    psswrd_lblfrme = Labelframe(tasks_frame, text='Password')
    psswrd_lblfrme.pack(fill=X, padx=10, pady=10)

    # ----- pin: Pin -----
    # ----- pino: Pin On -----
    pswdmanageB = Button(psswrd_lblfrme, text='Manage passwords', bootstyle='info link', command=lambda: password_manager())
    pswdmanageB.grid(row=0, column=3)
    '''pswdB = Button(psswrd_lblfrme, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('pin', 'off'), settings()))
    pswdB.grid(row=0, column=0)

    if sql_process.check_setting('pino') == 'off':
        pswdB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('pino', 'on'), settings()))

    pswdL = Label(psswrd_lblfrme, text='Password', font=('Calibri', 16))
    pswdL.grid(row=0, column=1)

    pswdE = Entry(psswrd_lblfrme, font=('Calibri', 16), show='#')
    pswdE.grid(row=0, column=2, padx=10)
    pswdE.insert(0, sql_process.check_setting('pin'))
    pswdE.config(state='readonly')

    pswd2B = Button(psswrd_lblfrme, text='Save', bootstyle='info link', command=lambda: (sql_process.setting_configure('pino', pswdE.get()), settings()))
    pswd2B.grid(row=0, column=3)'''

CARD_WIDTH = 240
CARD_PADDING = 12

CARD_MIN_WIDTH = 220
CARD_PADDING = 12

class CardsContainer(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.cards = []
        self._cols_configured = 0
        self.bind("<Configure>", self.on_resize)

    def add_card(self, title, text, color='secondary'):
        card = Frame(self, bootstyle=color, padding=10)
        Label(card, text=title, bootstyle=f'{color} inverse', font=('Calibri', 16, 'bold'),
              wraplength=CARD_MIN_WIDTH - 20).pack(anchor="w", fill=X)
        Label(card, text=text, bootstyle=f'{color} inverse', font=('Calibri', 15),
              wraplength=CARD_MIN_WIDTH - 20).pack(anchor="w", pady=(5, 0), fill=X)

        self.cards.append(card)
        self.relayout()

    def on_resize(self, event):
        self.relayout()

    def relayout(self):
        if not self.cards:
            return

        self.update_idletasks()
        width = self.winfo_width()
        if width < CARD_MIN_WIDTH:
            return

        cols = max(1, width // (CARD_MIN_WIDTH + CARD_PADDING))

        # clear old column weights before applying new ones
        for i in range(max(self._cols_configured, cols)):
            self.grid_columnconfigure(i, weight=0, uniform='')
        for i in range(cols):
            self.grid_columnconfigure(i, weight=1, uniform='cardcol')
        self._cols_configured = cols

        for i, card in enumerate(self.cards):
            card.grid(row=i // cols, column=i % cols, padx=CARD_PADDING // 2,
                      pady=CARD_PADDING // 2, sticky='nsew')

class display_pin:
    def __init__(self, pin):
        global cork_pinsF, root
        self.rowid = pin[0]
        self.title = pin[1]
        self.actual = pin[2]
        self.color = pin[3]
        self.position_x = pin[4]
        self.position_y = pin[5]
        self.content_json = pin[6]
        self.image_path = pin[7]

        if not self.content_json:  # one-time backfill for pins from before this update
            backfilled = json.dumps({'text': self.actual or '', 'runs': []})
            sql_process.update_pin_content(self.rowid, self.title, backfilled, self.image_path)
            self.content_json = backfilled

        def build(parent):
            return build_pin_preview(
                parent, root, cork_pinsF, self.rowid, self.title, self.color,
                self.content_json, self.image_path, PIN_WIDTH, PIN_HEIGHT
            )

        frame, placed_x, placed_y = cork_pinsF.add_pin(
            self.rowid, build, x=self.position_x, y=self.position_y,
            on_click=self.open_view
        )
        if self.position_x is None or self.position_y is None:
            sql_process.update_pin_position(self.rowid, placed_x, placed_y)

    def open_view(self, rowid):
        open_pin_view(root, self.rowid, self.title, self.content_json, self.image_path,
                       on_edit=self.open_edit)

    def open_edit(self, rowid):
        open_pin_editor(root, self.rowid, self.title, self.content_json, self.image_path,
                         self.color, on_save=self._save, on_delete=self._delete)

    def _save(self, rowid, new_title, new_content_json, new_image_path, new_color):
        sql_process.update_pin_content(rowid, new_title, new_content_json, new_image_path)
        sql_process.update_pin_color(rowid, new_color)
        corkboard_design()

    def _delete(self, rowid, image_path):
        delete_image_file(image_path)
        sql_process.delete_pin(rowid)
        corkboard_design()
def corkboard_design():
    global backFrame, current_design, tasksleftL, cork_pinsF
    tasksleftL.configure(text='          Corkboard')
    clear_board()
    current_design = 'corkboard'

    cork_topF = Frame(backFrame, bootstyle='default')
    cork_topF.pack(fill=X)

    corkboardheaderL = Label(cork_topF, text='C o r k b o a r d', font=('Calibri', 40, 'bold'), bootstyle='warning')
    corkboardheaderL.pack()

    corkboardsubheaderL = Label(cork_topF, text='Organize your miscellanous thoughts quickly & easily.', font=('Calibri', 20), bootstyle='light')
    corkboardsubheaderL.pack()

    cork_toolbarF = Frame(cork_topF, bootstyle='dark')
    cork_toolbarF.pack(fill=X, padx=20, pady=20)

    corkboardaddpinL = Button(cork_toolbarF, text='+ Add Pin', bootstyle='light outline', command=lambda: add_pin())
    corkboardaddpinL.grid(row=0, column=0, padx=10, pady=10)

    Separator(cork_topF, bootstyle='warning').pack(fill=X)

    cork_pinsF = FreeformCorkboard(backFrame, on_position_change=sql_process.update_pin_position)
    cork_pinsF.pack(fill="both", expand=True, padx=8, pady=8)

    conn_user000 = sqlite3.connect('user000.db')
    c_user000 = conn_user000.cursor()
    c_user000.execute("""SELECT rowid,* FROM corkboard""")
    cork_grabber = c_user000.fetchall()

    for pin in cork_grabber:
        display_pin(pin)
def add_pin():
    global add_pinF
    add_pinF = Frame(root, bootstyle='default')
    add_pinF.place(in_=root, anchor='c', relx=.5, rely=.5)

    Label(add_pinF, text='New Pin', font=('Calibri', 20, 'bold')).pack(padx=20, pady=10)
    Label(add_pinF, text='Title:', font=('Calibri', 14)).pack(padx=10)
    title_E = Entry(add_pinF, font=('Calibri', 15), width=20)
    title_E.pack(padx=10, pady=10)
    title_E.focus_force()

    def confirm(event=None):
        add_pin_go(title_E.get().strip() or 'Untitled')

    title_E.bind('<Return>', confirm)
    Button(add_pinF, text='Create', bootstyle='primary', command=confirm).pack(fill=X, padx=20, pady=5)
    Button(add_pinF, text='X Close', bootstyle='primary outline',
           command=lambda: add_pinF.destroy()).pack(fill=X, padx=20, pady=5)

def add_pin_go(title):
    global add_pinF
    conn_user000 = sqlite3.connect('user000.db')
    c_user000 = conn_user000.cursor()
    content_json = json.dumps({'text': '', 'runs': []})
    c_user000.execute(
        "INSERT INTO corkboard (title, actual, color, content_json) VALUES (?,?,?,?)",
        (title, '', 'secondary', content_json)
    )
    conn_user000.commit()
    new_rowid = c_user000.lastrowid
    add_pinF.destroy()
    corkboard_design()

    def save(rid, t, cj, ip, col):
        sql_process.update_pin_content(rid, t, cj, ip)
        sql_process.update_pin_color(rid, col)
        corkboard_design()

    def delete(rid, ip):
        delete_image_file(ip)
        sql_process.delete_pin(rid)
        corkboard_design()

    open_pin_editor(root, new_rowid, title, content_json, None, 'secondary',
                     on_save=save, on_delete=delete)
global searchingdot
searchingdot = 'no'
def searchthroughlistopen():
    global searchingdot, searchlistF, searchlist_titleE
    searchlistF = Frame(root, bootstyle='default')
    searchlistF.place(in_=root, anchor='c', relx=.5, rely=.5)

    searchlist_titleE = Entry(searchlistF, font=('Calibri', 15), width=15)
    searchlist_titleE.pack(padx=15, pady=15, fill=X)

    searchlist_goL = Button(searchlistF, text='Go', bootstyle='primary', command=lambda: (get_tasks('search', currentlistname), searchthroughlistclose()))
    searchlist_goL.pack(padx=15, pady=0, fill=X)

    searchlist_closeL = Button(searchlistF, text='X Close', bootstyle='primary outline', command=lambda: searchthroughlistclose())
    searchlist_closeL.pack(padx=15, pady=15, fill=X)
    searchingdot = 'yes'
def searchthroughlistclose():
    global searchingdot, searchlistF
    searchlistF.destroy()
    searchingdot = 'no'

def gonewithlistmenuF(e):
    global listmenuF
    listmenuF.destroy()
def open_more_tasksmenu():
    global backFrame, listmenuF, currentlistname
    posx = backFrame.winfo_pointerx() - backFrame.winfo_rootx()
    posy = backFrame.winfo_pointery() - backFrame.winfo_rooty()
    listmenuF = Frame(backFrame, bootstyle='dark')
    listmenuF.place(x=posx, y=posy)
    listmenuF.after(5000, gonewithlistmenuF)

    deletelistB = Button(listmenuF, text='🗑 Delete List                      ', command=lambda: droplist(), bootstyle='info outline')
    deletelistB.pack(fill=X, pady=4, padx=6)
    renamelistB = Button(listmenuF, text='🖊 Rename List                    ', command=lambda: renamelist(), bootstyle='info outline')
    renamelistB.pack(fill=X, pady=4, padx=6)
    shcomptasksB = Button(listmenuF, text='🕶 Show/hide comp tasks', command=lambda: get_tasks('showhide', list), bootstyle='info outline')
    shcomptasksB.pack(fill=X, pady=4, padx=6)
    searchlistB = Button(listmenuF, text='🔎 Search                             ', command=lambda: searchthroughlistopen(), bootstyle='info outline')
    searchlistB.pack(fill=X, pady=4, padx=6)

    if currentlistname == 'customers':
        deletelistB.config(state='disabled')
        renamelistB.config(state='disabled')



def announcer_more(header, subheader, tellmemoreheader, tellmemorewords):
    announceTK = Toplevel()
    announceTK.iconbitmap('icon.ico')
    announceTK.title(header)
    announceTK.focus_force()
    announceTK.geometry('600x500')

    announce_more_headerL = Label(announceTK, text=tellmemoreheader, font=('Calibri', 40, 'bold'), bootstyle='danger')
    announce_more_headerL.pack(pady=15)

    announce_more_headerL = Label(announceTK, text=subheader, font=('Calibri', 15, 'bold'), bootstyle='info')
    announce_more_headerL.pack(pady=15)

    announce_more_blahblahL = Label(announceTK, text=tellmemorewords, font=('Calibri', 15), bootstyle='light', wraplength=550)
    announce_more_blahblahL.pack(pady=15)

    announce_closebuttonB = Button(announceTK, text='Close window', bootstyle='light outline', command=lambda: announceTK.destroy())
    announce_closebuttonB.pack(fill=X, padx=50, pady=20, side=BOTTOM)
def announcer(header, subheader, tellmemoreheader, tellmemorewords):

    # ----------- Announcement Banner ------------
    announcementF = Frame(root, bootstyle='dark')
    announcementF.pack(fill=X, padx=20, pady=20)
    annouunceheaderL = Label(announcementF, text=header, font=('Calibri light', 20), bootstyle='danger', background='#303030')
    annouunceheaderL.grid(row=0, column=0, padx=5)
    annouuncesubheaderL = Label(announcementF, text=subheader, font=('Calibri', 15, 'bold'), bootstyle='dark inverse', foreground='white')
    annouuncesubheaderL.grid(row=0, column=1, padx=5)
    annouuncewhyB = Button(announcementF, text='Tell me more', bootstyle='success outline', command=lambda: announcer_more(header, subheader, tellmemoreheader, tellmemorewords))
    annouuncewhyB.grid(row=0, column=2, padx=5)
    annouuncecloseB = Button(announcementF, text='X Close', bootstyle='success outline', command=lambda: (announcementF.destroy()))
    annouuncecloseB.grid(row=0, column=3, padx=5)

global displaying_something
displaying_something = 'nothing so far'

class display_lists:
    def __init__(self, list):
        self.listBstyle = Style()
        self.listBstyle.configure('secondary.TButton', font=('Calibri light', 15), foreground='black')
        self.listBselectedstyle = Style()
        self.listBselectedstyle.configure('dark.Outline.TButton', font=('Calibri', 15), foreground='white')

        self.listB = Button(listsF, text=list[0], style='secondary.TButton', command=lambda: (self.switchlists(), get_tasks('none', list)))
        if len(list[0]) > 15:
            self.listB.config(text=f"""{list[0][0:13]}...""")#{list[0][1]}{list[0][2]}{list[0][3]}{list[0][4]}{list[0][5]}{list[0][6]}{list[0][7]}{list[0][8]}{list[0][9]}{list[0][10]}{list[0][11]}{list[0][12]}...""")

        if list[0] != 'wEIHFWUITEUIRTERUIdfghdughdgeiurhriuhaejbejhgaasfasdfgafsdgadfgjdfghjdfgdajfgh':
            self.listB.pack(fill=X, pady=2)
            self.listbToolTip = ToolTip(self.listB, text=list[0], bootstyle='dark inverse')
        self.personallistvar = list
        global firsttime, taskE, lstnmNameL, lstnmeditB, lstnmdeleteB
        if firsttime == 0:
            get_tasks('none', ('customers',))
            self.switchlists()
            firsttime += 1
        elif firsttime < 0:
            get_tasks('none', currentlistname)

        lstnmNameL.config(text=sql_process.get_current_list_display(currentlistname)[0])
        lstnmeditB.config(state='normal')
        lstnmdeleteB.config(state='normal')
        if currentlistname == 'customers':
            lstnmeditB.config(state=DISABLED)
            lstnmdeleteB.config(state=DISABLED)
    def switchlists(self):
        global currentlistname, lstnmNameL, lstnmeditB, lstnmdeleteB, firsttime, smart_on
        smart_on = 'off'
        tasks_design()

        currentlistname = self.personallistvar[1]
        lstnmNameL.config(text=self.personallistvar[0])
        lstnmeditB.config(state=NORMAL)
        lstnmdeleteB.config(state=NORMAL)
        if currentlistname == 'customers':
            lstnmeditB.config(state=DISABLED)
            lstnmdeleteB.config(state=DISABLED)

class display_task:
    # Plain displaying and editing task
    def __init__(self, item, list_type, current_list):
        global comptasks, numotasks, undone_tasks, displaying_something
        self.number = item[0]
        self.name = item[1]
        self.status = item[2]
        self.star = item[3]
        self.comingfrom = list_type
        self.listname = current_list
        self.difficulty = item[4]
        self.duedateday = item[5]
        self.duedatetime = item[6]
        self.duedateonoff = item[7]
        self.amiaministep = item[8]
        self.whichminiami = item[9]
        self.importance = item[10]
        self.notes = item[11]

        if self.amiaministep == 'no':
            numotasks += 1
            if self.status == 'checked' and comptasks == 'hidden':
                pass
            else:
                self.disp_normaltask(list_type, current_list)
                displaying_something = 'disping stuffs!'
    def disp_normaltask(self, list_type, current_list):
        global items, undone_tasks, thmgrabber, numotasks, currentlistname, tasks_frame, lstnmNameL, smart_on

        if self.comingfrom == 'Smart: Starred':
            lstnmNameL.config(text='Starred')
        if self.comingfrom == 'Smart: Everything':
            lstnmNameL.config(text='Everything')
        if self.comingfrom == 'Smart: Unchecked':
            lstnmNameL.config(text='Unchecked')
        if self.comingfrom == 'Smart: Due Today':
            lstnmNameL.config(text='Due Today')

        self.single_taskF = Frame(tasks_frame, bootstyle='dark')
        self.single_taskF.pack(padx=15, pady=10, fill=BOTH, expand=True)

        self.single_taskF_rowA = Frame(self.single_taskF, bootstyle='dark')
        self.single_taskF_rowA.pack(padx=10, fill=X, expand=True)
        self.single_taskF_rowA.bind('<Button-1>', self.allfunctions)

        self.startaskB = Button(self.single_taskF_rowA, image=unstarredimg, command=lambda: self.startask('no'), bootstyle='danger outline')
        self.startaskB.pack(side='left', padx=5, pady=5)
        self.checktaskB = Button(self.single_taskF_rowA, image=uncheckedtask, command=lambda: self.checkofftask('no'), bootstyle='danger outline')
        self.checktaskB.pack(side='left', padx=0, pady=5)

        self.taskT = Entry(self.single_taskF_rowA, bootstyle='danger', font=('Calibri', 30), foreground='#e74c3c')
        self.taskT.pack(fill=X, expand=True, padx=5, side='right', pady=5)
        self.taskT.insert(0, self.name)

        self.single_taskF_rowB = Frame(self.single_taskF, bootstyle='dark')
        self.single_taskF_rowB.pack(padx=10, fill=X, expand=True)
        self.single_taskF_rowB.bind('<Button-1>', self.allfunctions)

        self.tsdL = Label(self.single_taskF_rowB, text=self.difficulty, bootstyle='danger', background='#303030')
        self.tsdL.grid(row=0, column=0, pady=5)
        self.tsdL.bind('<Button-1>', self.allfunctions)
        self.tsdL.bind('<Enter>', self.tsdL_mo_open)
        self.tsdL.bind('<Leave>', self.tsdL_mo_close)

        self.sep1L = Label(self.single_taskF_rowB, text='w', bootstyle='danger', font=('Wingdings'), background='#303030')
        self.sep1L.grid(row=0, column=1, pady=5)
        self.sep1L.bind('<Button-1>', self.allfunctions)

        self.tsddL = Label(self.single_taskF_rowB, text=self.duedateday, bootstyle='danger', background='#303030')
        self.tsddL.grid(row=0, column=2, pady=5)
        self.tsddL.bind('<Button-1>', self.allfunctions)
        self.tsddL.bind('<Enter>', self.tsddL_mo_open)
        self.tsddL.bind('<Leave>', self.tsddL_mo_close)
        if self.duedateonoff == 'off':
            self.tsddL.config(text='Due Date Off')

        self.sep2L = Label(self.single_taskF_rowB, text='w', bootstyle='danger', font=('Wingdings'), background='#303030')
        self.sep2L.grid(row=0, column=3, pady=5)
        self.sep2L.bind('<Button-1>', self.allfunctions)

        self.notesL = Label(self.single_taskF_rowB, text=self.notes, bootstyle='danger', background='#303030')
        self.notesL.grid(row=0, column=4, pady=5)
        self.notesL.bind('<Button-1>', self.allfunctions)
        self.notesL.bind('<Enter>', self.notesL_mo_open)
        self.notesL.bind('<Leave>', self.notesL_mo_close)


        if smart_on != 'off':
            self.sep3L = Label(self.single_taskF_rowB, text='w', bootstyle='danger', font=('Wingdings'), background='#303030')
            self.sep3L.grid(row=0, column=5, pady=5)
            self.sep3L.bind('<Button-1>', self.allfunctions)

            self.mylistL = Label(self.single_taskF_rowB, text=sql_process.get_current_list_display(self.listname)[0], bootstyle='danger', background='#303030')
            self.mylistL.grid(row=0, column=6, pady=5)
            self.mylistL.bind('<Button-1>', self.allfunctions)
            self.mylistL.bind('<Enter>', self.mylistL_mo_open)
            self.mylistL.bind('<Leave>', self.mylistL_mo_close)
            tasksleftL.config(text='           Smart List', foreground='orange')
        self.taskT.bind('<Button-1>', self.allfunctions)
        self.taskT.bind('<Button-3>', self.expand_3_dots)

        self.taskT.config(state='disabled')
        if self.status == 'unchecked':
            root.title(f'To-Do 4.3 Beta - A new and innovative tasks organizer. - Corkboard Update 2.2.0')
        if self.status == 'checked' and self.star == 'n':
            self.checktaskB.config(image=checkedtask)
            self.taskT.config(font=('Calibri', 30, 'overstrike'), bootstyle='success', foreground='#00bc8c')
            self.startaskB.config(bootstyle='success outline')
            self.checktaskB.config(bootstyle='success outline')
            self.tsdL.config(bootstyle='success')
            self.sep1L.config(bootstyle='success')
            self.tsddL.config(bootstyle='success')
            self.sep2L.config(bootstyle='success')
            self.notesL.config(bootstyle='success')
            if smart_on != 'off':
                self.sep3L.config(bootstyle='success')
                self.mylistL.config(bootstyle='success')

        elif self.star == 'y' and self.status == 'unchecked':
            self.taskT.config(bootstyle='info', foreground='#3498db')
            self.startaskB.config(bootstyle='info outline', image=starredimg)
            self.checktaskB.config(bootstyle='info outline')
            self.tsdL.config(bootstyle='info')
            self.sep1L.config(bootstyle='info')
            self.tsddL.config(bootstyle='info')
            self.sep2L.config(bootstyle='info')
            self.notesL.config(bootstyle='info')
            self.tsdL.config(bootstyle='info')
            if smart_on != 'off':
                self.sep3L.config(bootstyle='info')
                self.mylistL.config(bootstyle='info')
        elif self.star == 'y' and self.status == 'checked':
            self.taskT.config(font=('Calibri', 30, 'overstrike'), bootstyle='warning', foreground='#f39c12')
            self.startaskB.config(image=starredimg, bootstyle='warning outline')
            self.checktaskB.config(image=checkedtask, bootstyle='warning outline')
            self.tsdL.config(bootstyle='warning')
            self.tsdL.config(bootstyle='warning')
            self.sep1L.config(bootstyle='warning')
            self.tsddL.config(bootstyle='warning')
            self.sep2L.config(bootstyle='warning')
            self.notesL.config(bootstyle='warning')
            if smart_on != 'off':
                self.sep3L.config(bootstyle='warning')
                self.mylistL.config(bootstyle='warning')

        global return2_
        if return2_ != 'False':
            if self.number == int(return2_): self.allfunctions()

        global firsttime3
        '''if firsttime3 != 0:
            for y in range(0,5):
                self.single_taskF.pack(padx=10, pady=y, fill=BOTH, expand=True)
                root.update()
                time.sleep(.001)'''
    def checkofftask(self, returnyesno):
        global currentlistname
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        if self.status == 'checked':
            c.execute("""UPDATE '{}' SET checked = 'unchecked' WHERE rowid='{}'""".format(self.listname, self.number))
            conn.commit()
        elif self.status == 'unchecked':
            c.execute("""UPDATE '{}' SET checked = 'checked' WHERE rowid='{}'""".format(self.listname, self.number))
            conn.commit()
            if sql_process.check_setting('ctcm') == 'y':
                c.execute("""UPDATE '{}' SET checked = 'checked' WHERE whichminiami='{}'""".format(self.listname, self.number))

        conn.commit()
        conn.close()
        if returnyesno == 'no':
            refresh(return_='False')
        elif returnyesno == 'yes':
            refresh(return_=self.number)
    def deletetask(self):
        global currentlistname
        def okdelete():
            conn = sqlite3.connect('info.db')
            c = conn.cursor()
            c.execute("DELETE from '{}' WHERE rowid='{}'".format(self.listname, self.number))
            conn.commit()
            c.execute("DELETE from '{}' WHERE rowid='{}'".format(self.listname, self.number))
            conn.commit()
            conn.close()
            deletetaskF.destroy()
            refresh(return_='False')
        if sql_process.check_setting('abd') == 'n':
            c.execute("DELETE from '{}' WHERE rowid='{}'".format(self.listname, self.number))
            conn.commit()
            c.execute("DELETE from '{}' WHERE whichminiami='{}'".format(self.listname, self.number))
            conn.commit()
            refresh(return_='False')
        elif sql_process.check_setting('abd') == 'y':
            deletetaskF = Frame(root, bootstyle='default')
            deletetaskF.place(in_=root, anchor='c', relx=.5, rely=.5)
            delheaderL = Label(deletetaskF, text=f'Delete task: {self.name}?', font=('Calibri', 20, 'bold'), bootstyle='danger')
            delheaderL.pack(pady=10, padx=10)
            delokB = Button(deletetaskF, text='Yes!', command=lambda: okdelete(), bootstyle='danger outline')
            delokB.pack(fill=X, padx=10, pady=10) # Delete ok button
            closedeltaskB = Button(deletetaskF, text='X', command=lambda: deletetaskF.destroy(), bootstyle='danger outline')
            closedeltaskB.pack(fill=X, padx=10, pady=5)
    def renametask(self, returnyesno):
        def okrename(e=None):
            global currentlistname
            reme_tasks_words = self.taskT.get().strip(' ')
            if reme_tasks_words != '':
                conn = sqlite3.connect('info.db')
                c = conn.cursor()
                c.execute("""UPDATE '{}' SET task = (?) WHERE rowid=(?)""".format(self.listname), (reme_tasks_words, self.number))
                conn.commit()
                conn.close()
                if returnyesno == 'no':
                    refresh(return_='False')
                elif returnyesno == 'yes':
                    refresh(return_=self.number)
            else:
                pass
        self.taskT.config(state='normal', bootstyle='light', foreground='white')
        try: self.miF.destroy()
        except: pass
        self.taskT.focus_force()
        self.taskT.bind('<Return>', okrename)
    def startask(self, returnyesno):
        global currentlistname
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        if self.star == 'n':
            c.execute("""UPDATE '{}' SET starred = 'y' WHERE rowid='{}'""".format(self.listname, self.number))
        elif self.star == 'y':
            c.execute("""UPDATE '{}' SET starred = 'n' WHERE rowid='{}'""".format(self.listname, self.number))
        conn.commit()
        conn.close()
        if returnyesno == 'no':
            refresh(return_='False')
        elif returnyesno == 'yes':
            refresh(return_=self.number)
    def edit_difficulty(self, e=None):
        global currentlistname, allfnctns_difficulty_combobox
        if allfnctns_difficulty_combobox.get() == 'None' or allfnctns_difficulty_combobox.get() == 'Very Easy' or allfnctns_difficulty_combobox.get() == 'Easy' or allfnctns_difficulty_combobox.get() == 'Medium' or allfnctns_difficulty_combobox.get() == 'Hard' or allfnctns_difficulty_combobox.get() == 'Extra Hard' or allfnctns_difficulty_combobox.get() == 'Tedious' or allfnctns_difficulty_combobox.get() == 'Unsure':
            conn = sqlite3.connect('info.db')
            c = conn.cursor()
            c.execute("""UPDATE '{}' SET difficulty = '{}' WHERE rowid='{}'""".format(self.listname, allfnctns_difficulty_combobox.get(), self.number))
            conn.commit()
            conn.commit()
            conn.close()
            refresh(return_=self.number)
        else:
            difficultyerror_responseF = Frame(root, bootstyle='default')
            difficultyerror_responseF.place(in_=root, anchor='c', relx=.5, rely=.5)

            difficultyerror_responseL = Label(difficultyerror_responseF, text='Please input a valid difficulty level.', font=('Calibri', 20))
            difficultyerror_responseL.pack(padx=20, pady=20)

            difficultyerror_response_subL = Label(difficultyerror_responseF, text='Err:Diff-Assignment-Not-Recognized', font=('Calibri', 10))
            difficultyerror_response_subL.pack(padx=20, pady=20)

            difficultyerror_timeL = Label(difficultyerror_responseF, text='(3)', font=('Calibri', 20))
            difficultyerror_timeL.pack(padx=20, pady=20)

            xx = 4
            for xxx in range(3):
                xx -= 1
                difficultyerror_timeL.config(text=f'({xx})')
                root.update()
                time.sleep(1)
            difficultyerror_responseF.destroy()
    def edit_note(self, e=None):
        global currentlistname, allfnctns_notes_entry
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("""UPDATE '{}' SET notes = '{}' WHERE rowid='{}'""".format(self.listname, allfnctns_notes_entry.get(), self.number))
        conn.commit()
        conn.commit()
        conn.close()
        refresh(return_=self.number)


    # Move to's
    def okmoveit(self):
        global currentlistname
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(self.switchtolist.get()), {'words':self.name, 'checked':self.status, 'starred':self.star, 'difficulty':self.difficulty, 'duedateday':self.duedateday, 'duedatetime':self.duedatetime, 'duedateonoff':self.duedateonoff, 'amiaministep':self.amiaministep, 'whichminiami':self.whichminiami, 'importance':self.importance, 'notes':self.notes})

        c.execute("DELETE from '{}' WHERE rowid='{}'".format(currentlistname, self.number))
        conn.commit()

        c.execute('''SELECT rowid FROM '{}' WHERE task='{}' AND checked='{}' AND difficulty='{}' AND notes='{}' '''.format(self.switchtolist.get(), self.name, self.status, self.difficulty, self.notes))
        oidgrabber = c.fetchone()[0]

        for step in sql_process.get_ministeps(self.number, currentlistname):
            c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(self.switchtolist.get()), {'words':step[1], 'checked':step[2], 'starred':step[3], 'difficulty':step[4], 'duedateday':step[5], 'duedatetime':step[6], 'duedateonoff':step[7], 'amiaministep':step[8], 'whichminiami':oidgrabber, 'importance':step[10], 'notes':step[11]})

        c.execute("DELETE from '{}' WHERE whichminiami='{}'".format(currentlistname, self.number))
        conn.commit()
        conn.close()
        self.miF_move.destroy()
        refresh(return_='False')
    def open_move(self, e=None):
        self.miF_move = Frame(root, bootstyle='default')
        self.miF_move.place(in_=root, anchor='c', relx=.5, rely=.5)
        self.switchtolist = StringVar()
        self.switchtolist.set(currentlistname)
        self.miF_headerL = Label(self.miF_move, text=f'Move task: {self.name}', font=('Calibri', 20), wrap=300)
        self.miF_headerL.pack(padx=20, pady=5)
        self.mif_move_listF = ScrolledFrame(self.miF_move, bootstyle='default')
        self.mif_move_listF.pack(padx=0, pady=20)
        for mvlist in all_lists:
            self.movelistbutton = Button(self.mif_move_listF, text=mvlist[0], command=lambda mvlist=mvlist: (self.switchtolist.set(mvlist[1]), self.okmoveit()))
            self.movelistbutton.pack(pady=1, fill=X, padx=5)
        self.mif_move_closeB = Button(self.miF_move, text='Close', command=lambda: self.miF_move.destroy(), bootstyle='primary outline')
        self.mif_move_closeB.pack(pady=1, fill=X, padx=5)

    # Copy to's
    def copy_to(self):
        global all_lists, switchtolistcopy, copytaskTK, cptsksubheaderL, currentlistname
        self.copytaskF = Frame(root, bootstyle='default')
        self.copytaskF.place(in_=root, anchor='c', relx=.5, rely=.5)

        self.cptskheaderL = Label(self.copytaskF, text=f'Copy task: {self.name}', font=('Calibri', 20, 'bold'))
        self.cptskheaderL.pack(pady=5, padx=5)
        self.switchtolistcopy = StringVar()
        self.switchtolistcopy.set(currentlistname)
        for cplist in all_lists:
            self.copylistbutton = Button(self.copytaskF, text=cplist[0], command=lambda cplist=cplist: (self.switchtolistcopy.set(cplist[1]), self.okcopyit()))
            self.copylistbutton.pack(pady=1, fill=X, padx=5)

        self.cptskclosebuttonB = Button(self.copytaskF, text='Close', bootstyle='primary outline', command=lambda: self.copytaskF.destroy())
        self.cptskclosebuttonB.pack(fill=X, padx=10, pady=5)
    def okcopyit(self):
        global switchtolist
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("SELECT * from '{}' WHERE rowid='{}'".format(currentlistname, self.number))
        copygrabber = c.fetchone()
        c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(self.switchtolistcopy.get()), {'words':self.name, 'checked':self.status, 'starred':self.star, 'difficulty':self.difficulty, 'duedateday':self.duedateday, 'duedatetime':self.duedatetime, 'duedateonoff':self.duedateonoff, 'amiaministep':self.amiaministep, 'whichminiami':self.whichminiami, 'importance':self.importance, 'notes':self.notes})

        c.execute('''SELECT rowid FROM '{}' WHERE task='{}' AND checked='{}' AND difficulty='{}' AND notes='{}' '''.format(self.switchtolistcopy.get(), self.name, self.status, self.difficulty, self.notes))
        oidgrabber = c.fetchone()[0]

        for step in sql_process.get_ministeps(self.number, currentlistname):
            c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(self.switchtolistcopy.get()), {'words':step[1], 'checked':step[2], 'starred':step[3], 'difficulty':step[4], 'duedateday':step[5], 'duedatetime':step[6], 'duedateonoff':step[7], 'amiaministep':step[8], 'whichminiami':oidgrabber, 'importance':step[10], 'notes':step[11]})


        conn.commit()
        conn.close()
        self.copytaskF.destroy()
        refresh(return_='False')

    # Due Date
    def setduedate(self, date_day):
        global currentlistname
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("""UPDATE '{}' SET duedateday = '{}' WHERE rowid='{}' """.format(currentlistname, date_day, self.number))
        conn.commit()
        conn.close()

        refresh(return_=self.number)
    def duedateonoff_fun(self):
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        if self.duedateonoff == 'off': c.execute("""UPDATE '{}' SET duedateonoff = (?) WHERE rowid=(?)""".format(currentlistname), ('on', self.number))
        elif self.duedateonoff == 'on': c.execute("""UPDATE '{}' SET duedateonoff = (?) WHERE rowid=(?)""".format(currentlistname), ('off', self.number))
        conn.commit()
        conn.close()

    # Options for task
    def expand_3_dots(self, e=None):
        def gonewithmif(E=None):
            self.miF.destroy()

        #MoreInfoFrame
        self.posx = self.single_taskF.winfo_pointerx() - self.single_taskF.winfo_rootx()
        self.posy = self.single_taskF.winfo_pointery() - self.single_taskF.winfo_rooty()
        self.miF = Frame(backFrame, bootstyle='dark')
        self.miF.place(x=self.posx, y=self.posy)
        self.deletetaskB = Button(self.miF, text='🗑 Delete Task          ', command=lambda: self.deletetask(), bootstyle='info outline')
        self.deletetaskB.pack(fill=X, pady=4, padx=2)
        self.renametaskB = Button(self.miF, text='🖊 Rename Task        ', command=lambda: self.renametask('no'), bootstyle='info outline')
        self.renametaskB.pack(fill=X, pady=4, padx=2)
        self.mifchecktaskB = Button(self.miF, text='✔ Check Task          ', command=lambda: self.checkofftask('no'), bootstyle='info outline')
        self.mifchecktaskB.pack(fill=X, pady=4, padx=2)
        self.mifstartaskB = Button(self.miF, text='⭐ Star Task             ', command=lambda: self.startask('no'), bootstyle='info outline')
        self.mifstartaskB.pack(fill=X, pady=4, padx=2)
        self.mifmovetaskB = Button(self.miF, text='[-> Move Task          ', command=lambda: self.open_move(), bootstyle='info outline')
        self.mifmovetaskB.pack(fill=X, pady=4, padx=2)
        self.mifmoreB = Button(self.miF, text='💬 Open Large View  ', command=lambda: self.allfunctions(), bootstyle='info outline')
        self.mifmoreB.pack(fill=X, pady=4, padx=2)

        self.miF.after(5000, gonewithmif)
    def allfunctions(self, e=None):
        global allfnctns_notes_entry, allfnctns_ministepsF, ms_count, allfncts_ministeps_add_msE, currentlistname, backFrame, tasks_frame, comingfrom, TDB_F, TDBnoshow, allfnctnsSEP, allfnctnsF_status_specialty, allfnctns_labelname, allfnctns_listname, allfnctnsF_status, allfnctns_status_button, allfnctns_difficulty_combobox, allfnctns_status_label, allfnctns_starred_button, allfnctns_starred_label, allfnctns_rename_button, allfnctns_rename_label, allfnctns_moveto_button, allfnctns_moveto_label, allfnctns_copyto_button, allfnctns_copyto_label, allfnctns_deltask_button, allfnctns_deltask_label, allfnctns_closeoverviewB
        try:
            self.closeallfunctions()
        except Exception as e:
            print(e)
        TDBnoshow.config(text='')
        TDB_F.config(width=200)
        allfnctns_labelname = Label(TDB_F, text=self.name, font=('Calibri', 20, 'bold'), wraplength=160)
        allfnctns_labelname.grid(row=1, column=0, pady=10, padx=10)
        allfnctns_listname = Label(TDB_F, text=sql_process.get_current_list_display(self.listname)[0], font=('Calibri', 15), wraplength=160)
        allfnctns_listname.grid(row=2, column=0)

        allfnctnsSEP = Separator(TDB_F, orient='horizontal')
        allfnctnsSEP.grid(row=3, column=0, sticky='nsew', padx=5, pady=10)

        allfnctnsF_status = Frame(TDB_F)
        allfnctnsF_status.grid(row=4, column=0)

        allfnctnsF_status_specialty = Frame(allfnctnsF_status)
        allfnctnsF_status_specialty.grid(row=0, column=0, columnspan=2, pady=10)

        allfnctns_status_button = Button(allfnctnsF_status_specialty, image=checkedsmall, command=lambda: (self.checkofftask('yes')), bootstyle='success')
        allfnctns_status_button.grid(row=0, column=0, padx=5)

        if self.status == 'unchecked':
            allfnctns_status_button.config(image=uncheckedsmall, bootstyle='danger')

        allfnctns_starred_button = Button(allfnctnsF_status_specialty, image=starredsmall, command=lambda: (self.startask('yes')), bootstyle='info')
        allfnctns_starred_button.grid(row=0, column=1, padx=5)

        if self.star == 'n':
            allfnctns_starred_button.config(image=unstarredsmall, bootstyle='light')

        Separator(allfnctnsF_status).grid(row=1, column=0, columnspan=2, sticky='nsew', pady=10)
        # Over here goes the mini steps
        allfnctns_ministepsF = Frame(allfnctnsF_status)
        allfnctns_ministepsF.grid(row=2, column=0, columnspan=2)

        allfnctns_ministeps_headerL = Label(allfnctns_ministepsF, text='Mini Steps', font=('Calibri', 12), bootstyle='primary')
        allfnctns_ministeps_headerL.grid(row=0, column=0, columnspan=4, pady=5)

        ms_count = 1
        for mini_step in sql_process.get_ministeps(taskid=self.number, list_name=currentlistname):
            disp_ministep(mini_step)

        allfncts_ministeps_add_msE = Entry(allfnctns_ministepsF, width=17, bootstyle='primary', font=('Calibri', 13), justify='center')
        allfncts_ministeps_add_msE.grid(row=ms_count, column=0, columnspan=4, pady=5)
        allfncts_ministeps_add_msE.insert(0, '+ Add mini step')
        allfncts_ministeps_add_msE.bind('<Return>', self.ministep_add)
        allfncts_ministeps_add_msE.bind('<FocusIn>', self.ministepentry_focusin)
        allfncts_ministeps_add_msE.bind('<FocusOut>', self.ministepentry_focusout)


        Separator(allfnctnsF_status).grid(row=3, column=0, columnspan=2, sticky='nsew', pady=10)

        allfnctns_difficulty_button = Button(allfnctnsF_status, image=warning_small, bootstyle='secondary outline')
        allfnctns_difficulty_button.grid(row=4, column=0, pady=5, padx=5)
        allfnctns_difficulty_combobox = Combobox(allfnctnsF_status, text=self.difficulty, bootstyle='secondary', width=8, font=('Calibri', 17), values=['None', 'Very Easy', 'Easy', 'Medium', 'Hard', 'Extra Hard', 'Tedious', 'Unsure'])
        allfnctns_difficulty_combobox.grid(row=4, column=1, pady=5, padx=5)
        if self.difficulty == 'None': insertcurrentdiff = 0
        elif self.difficulty == 'Very Easy': insertcurrentdiff = 1
        elif self.difficulty == 'Easy': insertcurrentdiff = 2
        elif self.difficulty == 'Medium': insertcurrentdiff = 3
        elif self.difficulty == 'Hard': insertcurrentdiff = 4
        elif self.difficulty == 'Extra Hard': insertcurrentdiff = 5
        elif self.difficulty == 'Tedious': insertcurrentdiff = 6
        elif self.difficulty == 'Unsure': insertcurrentdiff = 7
        allfnctns_difficulty_combobox.current(insertcurrentdiff)
        #allfnctns_difficulty_combobox.bind('<<ComboboxSelected>>', self.edit_difficulty)
        allfnctns_difficulty_savebutton = Button(allfnctnsF_status, text='Save', command=lambda: self.edit_difficulty(), bootstyle='secondary outline')
        allfnctns_difficulty_savebutton.grid(row=5, column=0, columnspan=2, pady=5, padx=5)

        Separator(allfnctnsF_status).grid(row=6, column=0, columnspan=2, sticky='nsew')

        allfnctns_duedateonoff_button = Button(allfnctnsF_status, image=toggon_line_small, command=lambda: (self.duedateonoff_fun(), refresh(return_=self.number)), bootstyle='secondary outline')
        allfnctns_duedateonoff_button.grid(row=7, column=0, pady=20, padx=5)
        allfnctns_duedateonoff_label = Label(allfnctnsF_status, text=f'Due Date {self.duedateonoff}', font=('Calibri', 15))
        allfnctns_duedateonoff_label.grid(row=7, column=1, pady=20, padx=5)

        #allfnctns_duedateday_button = Button(allfnctnsF_status, image=calender_small, command=lambda: (self.setduedate()), bootstyle='secondary outline')
        #allfnctns_duedateday_button.grid(row=8, column=0, pady=20, padx=5)
        #allfnctns_duedateday_label = Label(allfnctnsF_status, text=self.duedateday, font=('Calibri', 15))
        #allfnctns_duedateday_label.grid(row=8, column=1, pady=20, padx=5)

        allfnctns_duedateday_de = DateEntry(allfnctnsF_status, bootstyle='secondary', firstweekday=6)
        allfnctns_duedateday_de.grid(row=8, column=0, pady=5, padx=5, columnspan=2)
        allfnctns_duedateday_de.entry.delete(0, END)
        allfnctns_duedateday_de.entry.insert(0, self.duedateday)

        allfnctns_duedateday_savebutton = Button(allfnctnsF_status, text='Save', command=lambda: (self.setduedate(allfnctns_duedateday_de.entry.get())), bootstyle='secondary outline')
        allfnctns_duedateday_savebutton.grid(row=9, column=0, columnspan=2, pady=5, padx=5)
        if self.duedateonoff == 'off':
            allfnctns_duedateonoff_button.config(image=toggoff_line_small)
            allfnctns_duedateday_de.grid_forget()
            allfnctns_duedateday_savebutton.grid_forget()

        Separator(allfnctnsF_status).grid(row=10, column=0, columnspan=2, sticky='nsew')

        allfnctns_notes_button = Button(allfnctnsF_status, image=note_small, bootstyle='secondary outline')
        allfnctns_notes_button.grid(row=11, column=0, pady=20, padx=5)
        allfnctns_notes_entry = Entry(allfnctnsF_status, font=('Calibri', 15), width=11)
        allfnctns_notes_entry.grid(row=11, column=1, pady=20, padx=5)
        allfnctns_notes_entry.insert(0, self.notes)
        allfnctns_notes_entry.bind('<Return>', self.edit_note)


        Separator(allfnctnsF_status).grid(row=12, column=0, columnspan=2, sticky='nsew')

        allfnctns_rename_button = Button(allfnctnsF_status, image=renametasksmall, command=lambda: (self.renametask('yes')), bootstyle='secondary outline')
        allfnctns_rename_button.grid(row=13, column=0, pady=20, padx=5)
        allfnctns_rename_label = Label(allfnctnsF_status, text='Rename Task', font=('Calibri', 15))
        allfnctns_rename_label.grid(row=13, column=1, pady=20, padx=5)

        allfnctns_moveto_button = Button(allfnctnsF_status, image=movetosmall, command=lambda: (self.open_move()), bootstyle='secondary outline')
        allfnctns_moveto_button.grid(row=14, column=0, pady=20, padx=5)
        allfnctns_moveto_label = Label(allfnctnsF_status, text='Move to...', font=('Calibri', 15))
        allfnctns_moveto_label.grid(row=14, column=1, pady=20, padx=5)

        allfnctns_copyto_button = Button(allfnctnsF_status, image=copysmall, command=lambda: (self.copy_to()), bootstyle='secondary outline')
        allfnctns_copyto_button.grid(row=15, column=0, pady=20, padx=5)
        allfnctns_copyto_label = Label(allfnctnsF_status, text='Copy to...', font=('Calibri', 15))
        allfnctns_copyto_label.grid(row=15, column=1, pady=20, padx=5)

        allfnctns_deltask_button = Button(allfnctnsF_status, image=deletesmall, command=lambda: (self.deletetask()), bootstyle='secondary outline')
        allfnctns_deltask_button.grid(row=16, column=0, pady=20, padx=5)
        allfnctns_deltask_label = Label(allfnctnsF_status, text='Delete task', font=('Calibri', 15))
        allfnctns_deltask_label.grid(row=16, column=1, pady=20, padx=5)

        allfnctns_closeoverviewB = Button(TDB_F, text='❌ Close Overview', command=lambda: (self.closeallfunctions()), bootstyle='secondary outline')
        allfnctns_closeoverviewB.grid(row=0, column=0, columnspan=2, pady=5, padx=5)

        #  ...  ...  ...  ...  ...  ...  ...  ...  ...
    def closeallfunctions(self, e=None):
        global TDB_F, allfnctns_labelname, allfnctns_listname, allfnctnsSEP, allfnctnsF_status_specialty, allfnctnsF_status, allfnctns_status_button, allfnctns_starred_button, allfnctns_rename_button, allfnctns_rename_label, allfnctns_moveto_button, allfnctns_moveto_label, allfnctns_copyto_button, allfnctns_copyto_label, allfnctns_deltask_button, allfnctns_deltask_label, allfnctns_closeoverviewB
        try:
            allfnctns_labelname.destroy()
            allfnctns_listname.destroy()
            allfnctnsF_status.destroy()
            allfnctns_status_button.destroy()
            allfnctns_starred_button.destroy()
            allfnctns_rename_button.destroy()
            allfnctns_rename_label.destroy()
            allfnctns_moveto_button.destroy()
            allfnctns_moveto_label.destroy()
            allfnctns_deltask_button.destroy()
            allfnctns_deltask_label.destroy()
            allfnctnsSEP.destroy()
            allfnctnsF_status_specialty.destroy()
            allfnctns_closeoverviewB.destroy()
        except:
            pass
        TDBnoshow.config(text="Click on a task to\nsee it's details.")
        TDB_F.config(width=1000)

    # Mini Steps
    def ministep_add(self, e):
        global allfncts_ministeps_add_msE
        self.new_ministep_words = allfncts_ministeps_add_msE.get().strip(' ')
        if self.new_ministep_words != '':
            conn = sqlite3.connect('info.db')
            c = conn.cursor()
            c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(currentlistname), {'words':self.new_ministep_words, 'checked':'unchecked', 'starred':'n', 'difficulty':'Medium', 'duedateday':time.strftime("%x"), 'duedatetime':'1200', 'duedateonoff':'off', 'amiaministep':'yes', 'whichminiami':self.number, 'importance':'1', 'notes':'Add a note...'})
            conn.commit()
            conn.close()
            refresh(return_=self.number)

    def tsdL_mo_open(self, e=None):
        self.tsdL.config(text=f'Difficulty: {self.difficulty}')
    def tsdL_mo_close(self, e=None):
        self.tsdL.config(text=self.difficulty)

    def tsddL_mo_open(self, e=None):
        self.tsddL.config(text=f'Due Date: {self.duedateday}')
        if self.duedateonoff == 'off':
            self.tsddL.config(text=f'Due Date Off')
    def tsddL_mo_close(self, e=None):
        self.tsddL.config(text=self.duedateday)
        if self.duedateonoff == 'off':
            self.tsddL.config(text=f'Due Date Off')

    def notesL_mo_open(self, e=None):
        self.notesL.config(text=f'Notes: {self.notes}')
    def notesL_mo_close(self, e=None):
        self.notesL.config(text=self.notes)

    def mylistL_mo_open(self, e=None):
        self.mylistL.config(text=f'In list: {sql_process.get_current_list_display(self.listname)[0]}')
    def mylistL_mo_close(self, e=None):
        self.mylistL.config(text=sql_process.get_current_list_display(self.listname)[0])

    def ministepentry_focusin(self, e):
        global allfncts_ministeps_add_msE
        if allfncts_ministeps_add_msE.get() == '+ Add mini step':
            allfncts_ministeps_add_msE.config(justify='left')
            allfncts_ministeps_add_msE.delete(0, END)
        else:
            pass
    def ministepentry_focusout(self, e):
        global allfncts_ministeps_add_msE
        if allfncts_ministeps_add_msE.get() == '':
            allfncts_ministeps_add_msE.config(justify='center')
            allfncts_ministeps_add_msE.insert(0, '+ Add mini step')
        else:
            pass


class disp_ministep:
    def __init__(self, mini_step):
        global allfnctns_ministepsF, ms_count
        self.mini_stepid = mini_step[0]
        self.mini_stepname = mini_step[1]
        self.mini_stepstatus = mini_step[2]
        self.whichminiami = mini_step[9]

        self.ms_statusB = Button(allfnctns_ministepsF, image=uncheckedtiny, bootstyle='info link', command=lambda: self.ministep_checkoff(self.mini_stepid))
        self.ms_statusB.grid(row=ms_count, column=0, sticky='e')
        if self.mini_stepstatus == 'checked':
            self.ms_statusB.config(image=checkedtiny)
        if  self.mini_stepstatus == 'checked': self.ms_statusB.config(image=checkedtiny)

        Label(allfnctns_ministepsF, text=self.mini_stepname, wraplength=80).grid(row=ms_count, column=1, sticky='w')

        self.ms_deleteB = Button(allfnctns_ministepsF, image=deletetiny, bootstyle='info link', command=lambda: self.ministep_delete(self.mini_stepid))
        self.ms_deleteB.grid(row=ms_count, column=2, sticky='w')

        self.ms_renameB = Button(allfnctns_ministepsF, image=renametasktiny, bootstyle='info link', command=lambda: self.ministep_rename(self.mini_stepid))
        self.ms_renameB.grid(row=ms_count, column=3, sticky='w')

        ms_count += 1

    def ministep_delete(self, ms_id):
        global currentlistname
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("DELETE FROM '{}' WHERE rowid='{}' ".format(currentlistname, ms_id))
        conn.commit()
        conn.close()
        refresh(return_=self.whichminiami)
    def ministep_rename(self, ms_id):
        def ministep_rename_go(reme_ms_words):
            global currentlistname
            conn = sqlite3.connect('info.db')
            c = conn.cursor()
            c.execute("UPDATE '{}' SET task='{}' WHERE rowid='{}' ".format(currentlistname, reme_ms_words, ms_id))
            conn.commit()
            conn.close()
            refresh(return_=self.whichminiami)
            ms_nameF_rename.destroy()

        ms_nameF_rename = Frame(root, bootstyle='default')
        ms_nameF_rename.place(in_=root, anchor='c', relx=.5, rely=.5)
        rnmms_newnameE = Entry(ms_nameF_rename, bootstyle='primary', font=('Calibri light', 20), width=20)
        rnmms_newnameE.pack(fill=X, padx=10, pady=5)
        rnmms_newnameE.insert(0, self.mini_stepname)
        rnmms_okbuttonB = Button(ms_nameF_rename, text='Ok!', bootstyle='primary', command=lambda: ministep_rename_go(rnmms_newnameE.get()))
        rnmms_okbuttonB.pack(fill=X, padx=10, pady=5)
        rnmms_closebuttonB = Button(ms_nameF_rename, text='X', bootstyle='primary', command=lambda: ms_nameF_rename.destroy())
        rnmms_closebuttonB.pack(fill=X, padx=10, pady=5)
    def ministep_checkoff(self, ms_id):
        global currentlistname
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        if self.mini_stepstatus == 'checked':
            c.execute("""UPDATE '{}' SET checked = 'unchecked' WHERE rowid='{}'""".format(currentlistname, ms_id))
        elif self.mini_stepstatus == 'unchecked':
            c.execute("""UPDATE '{}' SET checked = 'checked' WHERE rowid='{}'""".format(currentlistname, ms_id))

        conn.commit()
        conn.close()
        refresh(return_=self.whichminiami)


def add_task(E=None):
    global undone_tasks, listnameget, currentlistname, taskE
    new_tasks_words = taskE.get().strip(' ')
    if new_tasks_words != '':
        conn = sqlite3.connect('info.db')
        c = conn.cursor()
        c.execute("INSERT INTO '{}' VALUES (:words, :checked, :starred, :difficulty, :duedateday, :duedatetime, :duedateonoff, :amiaministep, :whichminiami, :importance, :notes)".format(currentlistname), {'words':new_tasks_words, 'checked':'unchecked', 'starred':'n', 'difficulty':sql_process.check_setting('def_difficulty'), 'duedateday':time.strftime("%x"), 'duedatetime':'1200', 'duedateonoff':sql_process.check_setting('def_duedateonoff'), 'amiaministep':'no', 'whichminiami':'notamini', 'importance':'1', 'notes':sql_process.check_setting('def_note')})
        conn.commit()
        conn.close()
        refresh(return_='False')
    #x = ["INSERT INTO list VALUES (?"]
    #for column in list:
    #    x.append(',?')
    #x.remove(1)
    #x.append(')')
    #x.smashy()

    #c.execute(x.format y)

    else:
        pass
    taskE.focus_force()



def refresh(return_):
    global listsF, smart_on, checkedtask, uncheckedtask
    listsF.destroy()
    listsF = Frame(side_barF)
    listsF.grid(row=15, column=0, columnspan=2, sticky='nsew', padx=1, pady=2)

    if sql_process.check_setting('ssi') == 'square':
        uncheckedtask  = PhotoImage(file='square.png')
        if sql_process.check_setting('check_icon') == 'jut':
            checkedtask  = PhotoImage(file='check box jut.png')
        elif sql_process.check_setting('check_icon') == 'reg':
            checkedtask  = PhotoImage(file='check box.png')

    elif sql_process.check_setting('ssi') == 'circle':
        uncheckedtask  = PhotoImage(file='circle.png')
        if sql_process.check_setting('check_icon') == 'jut':
            checkedtask  = PhotoImage(file='check_circle.png')
        elif sql_process.check_setting('check_icon') == 'reg':
            checkedtask  = PhotoImage(file='check_circlereg.png')
    global return2_
    return2_ = return_

    if smart_on == 'off':
        tasks_design()
    get_lists()
    if smart_on == 'off':
        get_tasks('none', ('customers',))
    elif smart_on == 'starred':
        smart_starred()
    elif smart_on == 'everything':
        smart_everything()
    elif smart_on == 'unchecked':
        smart_unchecked()
    elif smart_on == 'duetoday':
        smart_duetoday()



def get_lists():
    global all_lists
    all_lists = sql_process.get_lists()
    for list in all_lists:
        display_lists(list)


def resize_side(e=None):
    global lstnmmoreinfoB, alltaskseqlF, homewidgetsize, meterwidgetF, smart_on, clockwidgetF, displistF, quicksettF, taskstopbarsize, swilF, lstnm_hidecomptasksB, lstnmeditB, lstnmdeleteB, rando_sep, taskstopbarsize
    height = root.winfo_height()
    width = root.winfo_width()
    try:
        if current_design == 'home':
            on_home_resize()
        elif current_design == 'tasks':
            if width > 1201:
                if taskstopbarsize != 'showall':
                    # swilF, lstnm_hidecomptasksB, lstnmeditB, lstnmdeleteB, rando_sep
                    if smart_on == 'off':
                        lstnmmoreinfoB.pack_forget()
                        rando_sep.pack(side=LEFT)
                        swilF.pack(side=LEFT, padx=15)
                        lstnm_hidecomptasksB.grid(row=0, column=2, padx=20)
                        lstnmeditB.pack(side=RIGHT, padx=5)
                        lstnmdeleteB.pack(side=RIGHT, padx=5)
                    taskstopbarsize = 'showall'

            elif width < 1200:
                if taskstopbarsize != 'showless':
                    # swilF, lstnm_hidecomptasksB, lstnmeditB, lstnmdeleteB, rando_sep
                    rando_sep.pack_forget()
                    swilF.pack_forget()
                    lstnm_hidecomptasksB.pack_forget()
                    lstnmeditB.pack_forget()
                    lstnmdeleteB.pack_forget()
                    if smart_on == 'off':
                        lstnmmoreinfoB.pack(side=RIGHT, padx=5)
                    taskstopbarsize = 'showless'
    except Exception as e:
        print(e)


def droplist():
    global currentlistname
    def okdroptable():
        global currentlistname
        sql_process.delete_list(currentlistname)
        currentlistname = 'customers'
        refresh(return_='False')
        if sql_process.check_setting('abdl') == 'y': list_nameF_drplst.destroy()

    if sql_process.check_setting('abdl') == 'y':
        list_nameF_drplst = Frame(root, bootstyle='default')
        list_nameF_drplst.place(in_=root, anchor='c', relx=.5, rely=.5)
        drplst_headerL = Label(list_nameF_drplst, text=f'Delete List: {sql_process.get_current_list_display(currentlistname)[0]}', font=('Calibri', 20, 'bold'), bootstyle='danger')
        drplst_headerL.pack(pady=10, padx=20)
        drplst_warningL = Label(list_nameF_drplst, text='This action cannot be undone.', font=('Calibri', 10), bootstyle='danger')
        drplst_warningL.pack(pady=5, padx=20)
        drplst_okbuttonB = Button(list_nameF_drplst, text='Ok!', bootstyle='danger outline', command=lambda: okdroptable())
        drplst_okbuttonB.pack(fill=X, padx=20, pady=5)
        drplst_closebuttonB = Button(list_nameF_drplst, text='X', bootstyle='danger outline', command=lambda: list_nameF_drplst.destroy())
        drplst_closebuttonB.pack(fill=X, padx=20, pady=5)
    else:
        okdroptable()

def add_new_list_go(e=None):
    global nwlstnewnameE, nwlstwarningL, nwlstcloseB, currentlistname
    newlistresponse = sql_process.add_list(nwlstnewnameE.get())
    nwlstwarningL.destroy()
    nwlstnewnameE.destroy()
    nwlstcloseB.destroy()
    add_listB.config(state='normal')
    refresh(return_='False')

    add_list_responseF = Frame(root, bootstyle='default')
    add_list_responseF.place(in_=root, anchor='c', relx=.5, rely=.5)

    add_list_responseL = Label(add_list_responseF, text=newlistresponse, font=('Calibri', 20))
    add_list_responseL.pack(padx=20, pady=20)

    add_list_timeL = Label(add_list_responseF, text='(3)', font=('Calibri', 20))
    add_list_timeL.pack(padx=20, pady=20)

    xx = 4
    for xxx in range(3):
        xx -= 1
        add_list_timeL.config(text=f'({xx})')
        root.update()
        time.sleep(1)
    add_list_responseF.destroy()
def add_new_list():
    global nwlstnewnameE, nwlstwarningL, nwlstcloseB
    add_listB.config(state='disabled')
    nwlstnewnameE = Entry(side_barF, bootstyle='light', font=('Calibri light', 15), width=10)
    nwlstnewnameE.grid(row=17, column=0, columnspan=2, sticky='nsew')
    nwlstwarningL = Label(side_barF, text='Limit 15 chars', font=('Calibri', 10))
    #nwlstwarningL.grid(row=16, column=0, sticky='nsew', columnspan=2)
    nwlstnewnameE.bind('<Return>', add_new_list_go)
    nwlstcloseB = Button(side_barF, text='X Close', command=lambda: (nwlstnewnameE.destroy(), nwlstwarningL.destroy(), nwlstcloseB.destroy(), add_listB.config(state='normal')))
    nwlstcloseB.grid(row=18, column=0, columnspan=2, pady=2)

def renamelist():
    global currentlistname, lstnmNameL, rnmlst_newnameE
    def okrename_list():
        global currentlistname, rnmlst_newnameE
        rnmlst_newnameE.config(state='readonly')
        sql_process.rename_list(currentlistname, rnmlst_newnameE.get().strip(' '))
        refresh(return_='False')
        list_nameF_rename.destroy()

    list_nameF_rename = Frame(root, bootstyle='default')
    list_nameF_rename.place(in_=root, anchor='c', relx=.5, rely=.5)
    rnmlst_newnameE = Entry(list_nameF_rename, bootstyle='primary', font=('Calibri light', 20), width=20)
    rnmlst_newnameE.pack(fill=X, padx=10, pady=5)
    rnmlst_newnameE.insert(0, sql_process.get_current_list_display(currentlistname)[0])
    rnmlst_warningL = Label(list_nameF_rename, text='Limit 15 charachters', bootstyle='primary', font=('Calibri', 10))
    rnmlst_warningL.pack(pady=5)
    rnmlst_okbuttonB = Button(list_nameF_rename, text='Ok!', bootstyle='primary', command=lambda: okrename_list())
    rnmlst_okbuttonB.pack(fill=X, padx=10, pady=5)
    rnmlst_closebuttonB = Button(list_nameF_rename, text='X', bootstyle='primary', command=lambda: list_nameF_rename.destroy())
    rnmlst_closebuttonB.pack(fill=X, padx=10, pady=5)


def about():
    global backFrame, tasks_frame, current_design, tasksleftL
    tasksleftL.configure(text='             About')
    clear_board()
    current_design = 'about'

    tasks_frame.pack(fill=BOTH, expand=True)

    aboutheaderL = Label(tasks_frame, text='About', font=('Calibri', 50, 'bold'), bootstyle='danger')
    aboutheaderL.pack()

    aboutlatestversion_text = ScrolledText(tasks_frame, font=('Calibri', 10), wrap='word')
    aboutlatestversion_text.pack(padx=30, pady=15)
    aboutlatestversion_text.insert(END, f'Latest Version: {sql_process.check_setting("version")}')
    aboutlatestversion_text.config(state='disabled')

    aboutsubheaderL = Label(tasks_frame, text='Created by: Dovid Stahler', font=('Calibri', 20), bootstyle='info')
    aboutsubheaderL.pack()

    aboutbodyL = Label(tasks_frame, text='        Made with Python and ttkbootstrap. And grit.\n\nSpecial shout out to Binyamin Stahler & Yosef Stahler.\n\n     You can reach me at dovidstahler9@gmail.com.', font=('Calibri', 15), bootstyle='light')
    aboutbodyL.pack(pady=10)

    aboutsubheader2L = Label(tasks_frame, text='Modules', font=('Calibri', 30, 'bold', 'underline'), bootstyle='info')
    aboutsubheader2L.pack(pady=10)

    aboutbody2L = Label(tasks_frame, text='''
Tkinter
Pillow
Ttkbootstrap
Sqlite3
Time
Random''', font=('Calibri', 25), bootstyle='info')
    aboutbody2L.pack()


def lock_crk():
    corkSEP.grid_forget()
    corkB.grid_forget()
def unlock_crk():
    corkSEP.grid(row=5, pady=5, sticky='nsew', columnspan=2)
    corkB.grid(row=6, pady=5, sticky='nsew', columnspan=2)

def lock_sl_str():
    sl_str_realB.grid_forget()
    if sql_process.check_setting('sl_evr') == 'n' and sql_process.check_setting('sl_unch') == 'n' and sql_process.check_setting('sl_dtdy') == 'n':
        smartySEP.grid_forget()
        smartlists_headerL.grid_forget()
    else:
        pass
def unlock_sl_str():
    sl_str_realB.grid(row=9, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    if sql_process.check_setting('sl_evr') == 'n' and sql_process.check_setting('sl_unch') == 'n' and sql_process.check_setting('sl_dtdy') == 'n':
        smartySEP.grid(row=7, pady=5, sticky='nsew', columnspan=2)
        smartlists_headerL.grid(row=8, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    else:
        pass

def lock_sl_evr():
    sl_evr_realB.grid_forget()
    if sql_process.check_setting('sl_str') == 'n' and sql_process.check_setting('sl_unch') == 'n' and sql_process.check_setting('sl_dtdy') == 'n':
        smartySEP.grid_forget()
        smartlists_headerL.grid_forget()
    else:
        pass
def unlock_sl_evr():
    sl_evr_realB.grid(row=10, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    if sql_process.check_setting('sl_str') == 'n' or sql_process.check_setting('sl_unch') == 'n' and sql_process.check_setting('sl_dtdy') == 'n':
        smartySEP.grid(row=7, pady=5, sticky='nsew', columnspan=2)
        smartlists_headerL.grid(row=8, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    else:
        pass

def lock_sl_unch():
    sl_unch_realB.grid_forget()
    if sql_process.check_setting('sl_str') == 'n' and sql_process.check_setting('sl_evr') == 'n' and sql_process.check_setting('sl_dtdy') == 'n':
        smartySEP.grid_forget()
        smartlists_headerL.grid_forget()
    else:
        pass
def unlock_sl_unch():
    sl_unch_realB.grid(row=11, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    if sql_process.check_setting('sl_evr') == 'n' and sql_process.check_setting('sl_str') == 'n' and sql_process.check_setting('sl_dtdy') == 'n':
        smartySEP.grid(row=7, pady=5, sticky='nsew', columnspan=2)
        smartlists_headerL.grid(row=8, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    else:
        pass

def lock_sl_dtdy():
    sl_dtdy_realB.grid_forget()
    if sql_process.check_setting('sl_str') == 'n' and sql_process.check_setting('sl_evr') == 'n' and sql_process.check_setting('sl_unch') == 'n':
        smartySEP.grid_forget()
        smartlists_headerL.grid_forget()
    else:
        pass
def unlock_sl_dtdy():
    sl_dtdy_realB.grid(row=12, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    if sql_process.check_setting('sl_evr') == 'n' and sql_process.check_setting('sl_str') == 'n' and sql_process.check_setting('sl_unch') == 'n':
        smartySEP.grid(row=7, pady=5, sticky='nsew', columnspan=2)
        smartlists_headerL.grid(row=8, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
    else:
        pass
def the_nothing(e):
    pass

def welcome():
    place='welcome'
    welcomeF = Frame(root, bootstyle='default')
    welcomeF.place(in_=root, anchor='c', relx=.5, rely=.5)

    Separator(welcomeF).pack(padx=2000, side=TOP, pady=1000)

    welcomeheader2L = Label(welcomeF, text='Welcome to To-Do 4!', font=('Calibri', 25))
    welcomeheader2L.pack(padx=20, pady=20)

    welcomesubheader2L = Label(welcomeF, text='A new and innovative tasks organizer.', font=('Calibri', 15))
    welcomesubheader2L.pack(padx=20, pady=0)

    welcomeprogressPB = Progressbar(welcomeF, bootstyle='info striped', maximum=100, mode='determinate', length=300, value=0)
    welcomeprogressPB.pack(padx=20, pady=50)
    welcomeprogressPB.start(25)

    welcomehintL = Label(welcomeF, text=rd.choice(['From asking before doing an action to changing the shape of an icon, To-do 4 is highly customizable to your needs.', 'Break up your task efficiently with mini steps!', 'Did you know you can change the text on the Home Screen?', 'A Smart List takes all the tasks from any list which have a certain common attribute.', 'Corkboard puts all your random miscellanous bits in your mind into an organized pile.']), bootstyle='danger', font=('Calibri', 13))
    welcomehintL.pack(padx=20, pady=0)

    Separator(welcomeF).pack(padx=2000, side=BOTTOM, pady=1000)


    while place=='welcome':
        root.update()
        if welcomeprogressPB['value'] == 99:
            time.sleep(.8)
            welcomeF.destroy()
            place='other'

global unlocked
unlocked = 'no'
def potential_unlock_td4():
    global lockscreenE, lockscreenF, lockscreenerrormessageL, unlocked
    if lockscreenE.get() == sql_process.check_setting('pin'):
        lockscreenF.destroy()
        unlocked = 'yes'
        root.bind('<Return>', the_nothing)
    else:
        lockscreenerrormessageL.pack(padx=2000, pady=10)
def checkunlocked(e=None):
    global unlocked, lockscreenF
    potential_unlock_td4()
    if unlocked == 'no':
        lockscreenF.destroy()
        password()
def password(e=None):
    global lockscreenE, lockscreenF, lockscreenerrormessageL
    try:
        lockscreenF.destroy()
    except:
        pass
    lockscreenF = Frame(root, bootstyle='default')
    lockscreenF.place(in_=root, anchor='c', relx=.5, rely=.5)

    Separator(lockscreenF).pack(padx=2000, side=TOP, pady=1000)

    lockscreenFheader2L = Label(lockscreenF, text='To-Do 4 Security', font=('Calibri', 45), bootstyle='light')
    lockscreenFheader2L.pack(padx=2000, pady=10)

    lockscreenFsubheader2L = Label(lockscreenF, text='Enter pin.', font=('Calibri', 25), bootstyle='light')
    lockscreenFsubheader2L.pack(padx=2000, pady=10)

    lockscreenE = Entry(lockscreenF, show='l', font=('Wingdings'), width=5, bootstyle='light')
    lockscreenE.pack(padx=2000, pady=10)

    lockscreengoB = Button(lockscreenF, text='Go...', bootstyle='light outline', command=lambda: potential_unlock_td4())
    lockscreengoB.pack(padx=2000, pady=10)

    lockscreenerrormessageL = Label(lockscreenF, text='Incorrect. Try again.', font=('Calibri', 15), bootstyle='danger')

    Separator(lockscreenF).pack(padx=2000, side=BOTTOM, pady=1000)

def smart_starred():
    global smart_on
    clear_board()
    undone_tasks = 0
    smart_on = 'starred'
    items_starred = []
    tasks_design()

    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM sqlite_master WHERE type='table' """)
    starredgrabber_list = c.fetchall()
    for each_list in starredgrabber_list:
        c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'y' AND checked = 'unchecked'".format(each_list[1]))
        starredgrabber_taskA = c.fetchall()
        for each_taskA in starredgrabber_taskA:
            items_starred.append(each_taskA)
            display_task(each_taskA, 'Smart: Starred', each_list[1])

    for each_list in starredgrabber_list:
        if comptasks == 'showing':
            c.execute("SELECT rowid, * FROM '{}' WHERE starred = 'y' AND checked = 'checked'".format(each_list[1]))
            starredgrabber_taskB = c.fetchall()
            for each_taskB in starredgrabber_taskB:
                items_starred.append(each_taskB)
                display_task(each_taskB, 'Smart: Starred', each_list[1])
def smart_everything():
    global smart_on
    clear_board()
    undone_tasks = 0
    smart_on = 'everything'
    items_starred = []
    tasks_design()

    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM sqlite_master WHERE type='table' """)
    starredgrabber_list = c.fetchall()
    for each_list in starredgrabber_list:
        c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'unchecked' and amiaministep='no' ".format(each_list[1]))
        starredgrabber_taskA = c.fetchall()
        for each_taskA in starredgrabber_taskA:
            items_starred.append(each_taskA)
            display_task(each_taskA, 'Smart: Everything', each_list[1])

    for each_list in starredgrabber_list:
        c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'checked' and amiaministep='no' ".format(each_list[1]))
        starredgrabber_taskB = c.fetchall()
        for each_taskB in starredgrabber_taskB:
            items_starred.append(each_taskB)
            display_task(each_taskB, 'Smart: Everything', each_list[1])
def smart_unchecked():
    global smart_on
    clear_board()
    undone_tasks = 0
    smart_on = 'unchecked'
    items_starred = []
    tasks_design()

    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM sqlite_master WHERE type='table' """)
    starredgrabber_list = c.fetchall()
    for each_list in starredgrabber_list:
        c.execute("SELECT rowid, * FROM '{}' WHERE checked = 'unchecked' and amiaministep='no' ".format(each_list[1]))
        starredgrabber_taskA = c.fetchall()
        for each_taskA in starredgrabber_taskA:
            items_starred.append(each_taskA)
            display_task(each_taskA, 'Smart: Unchecked', each_list[1])
def smart_duetoday():
    global smart_on
    clear_board()
    undone_tasks = 0
    smart_on = 'duetoday'
    items_duetoday = []
    tasks_design()
    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM sqlite_master WHERE type='table' """)
    duetoday_notasks = 'No tasks'
    duetodaygrabber_list = c.fetchall()
    for each_list in duetodaygrabber_list:
        c.execute("SELECT rowid, * FROM '{}' WHERE duedateday='{}' AND duedateonoff='on'".format(each_list[1], time.strftime('%x')))
        duetodaygrabber_taskA = c.fetchall()
        for each_taskA in duetodaygrabber_taskA:
            items_duetoday.append(each_taskA)
            display_task(each_taskA, 'Smart: Due Today', each_list[1])
            duetoday_notasks = 'There ARE thingiesuuuuuh!!'
    if duetoday_notasks == 'No tasks':
        notaskstodayL = Label(tasks_frame, image=notaskstodayimg)
        notaskstodayL.pack()


def overarchingsearch_go(search_input):
    # Search through Lists and add to a [list]
    search_lists_list = []

    conn = sqlite3.connect('info.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM sqlite_master WHERE type='table' """)
    searchgrabber_list = c.fetchall()
    for each_list in searchgrabber_list:
        c.execute("SELECT rowid, * FROM '{}' WHERE task LIKE '{}'".format(each_list[1], f'%{search_input}%'))
        searchgrabber_taskA = c.fetchall()
        for each_taskA in searchgrabber_taskA:
            search_lists_list.append((each_taskA, each_list[1]))

    # Search through corkboard and add to a [list]
    search_corkboard_list = []

    conn_user000 = sqlite3.connect('user000.db')
    c_user000 = conn_user000.cursor()
    c_user000.execute("SELECT rowid, * FROM corkboard WHERE title LIKE '{}'".format(f'%{search_input}%'))
    searchgrabber_taskA = c_user000.fetchall()
    for each_taskA in searchgrabber_taskA:
        search_corkboard_list.append(each_taskA)
    c_user000.execute("SELECT rowid, * FROM corkboard WHERE actual LIKE '{}'".format(f'%{search_input}%'))
    searchgrabber_taskB = c_user000.fetchall()
    for each_taskB in searchgrabber_taskB:
        search_corkboard_list.append(each_taskB)

    # Display both lists
    clear_board()
    global current_design, tasks_frame
    tasks_frame.pack(fill=BOTH, expand=True)
    current_design = 'overarch search'

    search_headerL = Label(tasks_frame, text=f'Search: {search_input}', font=('Calibri', 30, 'bold'))
    search_headerL.pack(pady=5)

    search_results_numL = Label(tasks_frame, text=f'Search Results: {len(search_lists_list) + len(search_corkboard_list)}', font=('Calibri', 20))
    search_results_numL.pack(pady=5)

    Separator(tasks_frame).pack(fill=X, pady=5)

    search_subheader_lists_L = Label(tasks_frame, text='Tasks', font=('Calibri', 20))
    search_subheader_lists_L.pack(pady=5)

    search_subheader_lists_F = Frame(tasks_frame)
    search_subheader_lists_F.pack(fill=X)

    for search_task in search_lists_list:
        search_number = search_task[0][0]
        search_name = search_task[0][1]
        search_status = search_task[0][2]
        search_star = search_task[0][3]
        search_difficulty = search_task[0][4]
        search_duedateday = search_task[0][5]
        search_duedatetime = search_task[0][6]
        search_duedateonoff = search_task[0][7]
        search_list = search_task[1]

        search_single_taskF = Frame(tasks_frame, bootstyle='default')
        search_single_taskF.pack(padx=10, pady=5, fill=BOTH, expand=True)

        search_startaskB = Label(search_single_taskF, image=unstarredimg, bootstyle='danger')
        search_startaskB.pack(side='left', padx=5)
        search_checktaskB = Label(search_single_taskF, image=uncheckedtask, bootstyle='danger')
        search_checktaskB.pack(side='left', padx=0)

        search_tsdL = Label(search_single_taskF, text=sql_process.get_current_list_display(search_list)[0], bootstyle='danger')
        search_tsdL.pack(side='right', padx=5)

        search_taskT = Entry(search_single_taskF, bootstyle='danger', font=('Calibri', 30), foreground='#e74c3c')
        search_taskT.pack(fill=X, expand=True, padx=5, side='right')
        search_taskT.insert(0, search_name)
        search_taskT.config(state='disabled')

        if search_status == 'checked':
            search_checktaskB.config(image=checkedtask)
            search_taskT.config(font=('Calibri', 30, 'overstrike'), bootstyle='success', foreground='#00bc8c')
            search_startaskB.config(bootstyle='success')
            search_checktaskB.config(bootstyle='success')
            search_tsdL.config(bootstyle='success')
        if search_star == 'y' and search_status == 'unchecked':
            search_taskT.config(bootstyle='info', foreground='#3498db')
            search_startaskB.config(bootstyle='info', image=starredimg)
            search_checktaskB.config(bootstyle='info')
            search_tsdL.config(bootstyle='info')
        elif search_star == 'y' and search_status == 'checked':
            search_taskT.config(bootstyle='warning', foreground='#f39c12')
            search_startaskB.config(image=starredimg, bootstyle='warning')
            search_checktaskB.config(bootstyle='warning')
            search_tsdL.config(bootstyle='warning')

        for y in range(0,5):
            search_single_taskF.pack(padx=10, pady=y, fill=BOTH, expand=True)
            root.update()
            time.sleep(.001)

    Separator(tasks_frame).pack(fill=X, pady=5)

    search_subheader_cork_L = Label(tasks_frame, text='Corkboard', font=('Calibri', 20))
    search_subheader_cork_L.pack(pady=5)

    search_subheader_cork_F = Frame(tasks_frame)
    search_subheader_cork_F.pack(fill=X, pady=5)

    for search_pin in search_corkboard_list:
        search_rowid = search_pin[0]
        search_title = search_pin[1]
        search_actual = search_pin[2]
        search_color = search_pin[3]

        search_pin_frameF = Frame(search_subheader_cork_F, bootstyle=search_color)
        #search_pin_frameF.pack(fill=X, padx=10, pady=10)

        search_pin_titleL = Label(search_pin_frameF, text=search_title, font=('Calibri', 18, 'bold'), bootstyle=f'{search_color} inverse')
        search_pin_titleL.pack(pady=5)

        search_pin_actualL = Label(search_pin_frameF, text=search_actual, font=('Calibri', 15), bootstyle=f'{search_color} inverse')
        search_pin_actualL.pack(pady=5)

        for y in range(0,10):
            search_pin_frameF.pack(padx=10, pady=y, fill=BOTH, expand=True)
            root.update()
            time.sleep(.001)

def pswdshowF():
    global pswdE, pswdshow
    if pswdshow == 'not showing':
        pswdE.config(show='')
        pswdshow = 'showing'
    elif pswdshow == 'showing':
        pswdE.config(show='*')
        pswdshow = 'not showing'
def update_psswdonoff_btn():
    global pswdB
    if sql_process.check_setting('pino') == 'off':
        pswdB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('pino', 'on'), update_psswdonoff_btn()))
    elif sql_process.check_setting('pino') == 'on':
        pswdB.config(image=toggle_onimg, command=lambda: (sql_process.setting_configure('pino', 'off'), update_psswdonoff_btn()))
def unlock_pswd_manager():
    global pswdwin, pswdmanL, pswdman2L, pswdmanE, pswdman2B, pswdshow, pswdE, pswdB
    #pswdmanL.destroy()
    pswdman2L.config(text='Turn password on/off')
    pswdmanE.destroy()
    pswdman2B.destroy()

    pswdB = Button(pswdwin, image=toggle_onimg, bootstyle='success link', command=lambda: (sql_process.setting_configure('pino', 'off'), update_psswdonoff_btn()))
    pswdB.pack(padx=20, pady=10)

    if sql_process.check_setting('pino') == 'off':
        pswdB.config(image=toggle_offimg, command=lambda: (sql_process.setting_configure('pino', 'on'), update_psswdonoff_btn()))


    pswdE = Entry(pswdwin, font=('Calibri', 16), show='*')
    pswdE.pack(padx=20, pady=10)
    pswdE.insert(0, sql_process.check_setting('pin'))

    pswdshow = 'not showing'
    pswdtoggleB = Button(pswdwin, text='Show/Hide Password', bootstyle='info link', command=lambda: pswdshowF())
    pswdtoggleB.pack(padx=20, pady=10)

    pswd2B = Button(pswdwin, text='Save password', bootstyle='info link', command=lambda: (sql_process.setting_configure('pin', pswdE.get()), settings()))
    pswd2B.pack(padx=20, pady=10)
def password_manager():
    global pswdwin, pswdmanL, pswdman2L, pswdmanE, pswdman2B
    pswdwin = Toplevel()
    pswdwin.title('Password Manager')
    pswdwin.iconbitmap('icon.ico')

    pswdmanL = Label(pswdwin, text='Password Manager', font=('Calibri', 16))
    pswdmanL.pack(padx=20, pady=10)

    pswdman2L = Label(pswdwin, text='Enter current password to continue.', font=('Calibri', 10))
    pswdman2L.pack(padx=20, pady=10)

    pswdmanE = Entry(pswdwin, font=('Calibri', 16), show='*')
    pswdmanE.pack(padx=20, pady=10)
    pswdmanE.focus_force()

    pswdman2B = Button(pswdwin, text='Unlock Password Manager', bootstyle='info link', command=lambda: (attemptunlockpswdman(pswdmanE.get())))
    pswdman2B.pack(padx=20, pady=10)

    if sql_process.check_setting('pino') == 'off':
        unlock_pswd_manager()
def attemptunlockpswdman(attempt):
    if attempt == sql_process.check_setting('pin'):
        unlock_pswd_manager()

# ----------- Top Bar -----------
main_headerF = Frame(bootstyle='default')
main_headerF.pack(fill=X)

welcomeheaderL = Label(main_headerF, text='Good to see ya!', font=('Calibri', 40, 'bold'), bootstyle='Default')
welcomeheaderL.grid(row=0, column=0, padx=5)

search_style = Style()
search_style.configure('warning.Outline.TButton', font=('Calibri', 25))

searchbar = Entry(main_headerF, bootstyle='warning', font=('Calibri light', 25), width=11)
searchbar.grid(row=0, column=4, padx=6, sticky='e')

searchbargoB = Button(main_headerF, text='Go', style='warning.Outline.TButton', command=lambda: overarchingsearch_go(searchbar.get()))
searchbargoB.grid(row=0, column=5, sticky='e')

# ----------- Side Bar -----------
side_barF = ScrolledFrame(bootstyle='Default round', width=157, autohide=True)
side_barF.pack(fill=Y, side=LEFT)

tasksleftL = Label(side_barF, text='To Do 4.3 Beta', font=('Calibri', 12), bootstyle='warning')
tasksleftL.grid(row=0, column=0, columnspan=2, pady=1, sticky='nsew', padx=1)

Separator(side_barF).grid(row=1, pady=5, sticky='nsew', columnspan=2)

homeL = Button(side_barF, image=homeimg, command=lambda: home_design(), bootstyle='secondary')
homeL.grid(row=2, column=0, sticky='nsew', pady=1, padx=1)

refreshtasksL = Button(side_barF, image=refreshimg, command=lambda: refresh(return_='False'), bootstyle='secondary')
refreshtasksL.grid(row=3, column=0, sticky='nsew', pady=1, padx=1)

aboutL = Button(side_barF, image=infoimg, command=lambda: about(), bootstyle='secondary')
aboutL.grid(row=2, column=1, sticky='nsew', pady=1, padx=1)

settingsL = Button(side_barF, image=settingsimg, command=lambda: settings(), bootstyle='secondary')
settingsL.grid(row=3, column=1, sticky='nsew', pady=1, padx=1)

# ---------------- CORKBOARD ----------------
corkBstyle = Style()
corkBstyle.configure('light.Outline.TButton', font=('Calibri', 15, 'bold'))

corkSEP = Separator(side_barF)
corkB = Button(side_barF, text='Corkboard', style='light.Outline.TButton', command=lambda: corkboard_design())
if sql_process.check_setting('crk') == 'y':
    corkSEP.grid(row=5, pady=5, sticky='nsew', columnspan=2)
    corkB.grid(row=6, pady=5, sticky='nsew', columnspan=2)

# ---------------- SMART LISTS ----------------
smartySEP = Separator(side_barF)

smartlists_headerL = Label(side_barF, text='Smart Lists', font=('Calibri', 15, 'bold'), bootstyle='dark inverse')

if sql_process.check_setting('sl_str') == 'y' or sql_process.check_setting('sl_evr') == 'y' or sql_process.check_setting('sl_unch') == 'y' or sql_process.check_setting('sl_dtdy') == 'y':
    smartySEP.grid(row=7, pady=5, sticky='nsew', columnspan=2)
    smartlists_headerL.grid(row=8, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)

sl_str_realB = Button(side_barF, text='Starred', bootstyle='dark', command=lambda: smart_starred())
if sql_process.check_setting('sl_str') == 'y':
    sl_str_realB.grid(row=9, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
sl_evr_realB = Button(side_barF, text='Everything', bootstyle='dark', command=lambda: smart_everything())
if sql_process.check_setting('sl_evr') == 'y':
    sl_evr_realB.grid(row=10, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
sl_unch_realB = Button(side_barF, text='Unchecked', bootstyle='dark', command=lambda: smart_unchecked())
if sql_process.check_setting('sl_unch') == 'y':
    sl_unch_realB.grid(row=11, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)
sl_dtdy_realB = Button(side_barF, text='Due Today', bootstyle='dark', command=lambda: smart_duetoday())
if sql_process.check_setting('sl_dtdy') == 'y':
    sl_dtdy_realB.grid(row=12, column=0, pady=1, sticky='nsew', padx=1, columnspan=2)

# ----------------- LISTS -----------------
Separator(side_barF).grid(row=13, pady=5, sticky='nsew', columnspan=2)

lists_headerL = Label(side_barF, text='Lists', font=('Calibri', 30), bootstyle='secondary inverse', foreground='black')
lists_headerL.grid(row=14, column=0, pady=1, sticky='nsew', padx=1)

add_listB = Button(side_barF, image=newlistimg, command=lambda: add_new_list(), bootstyle='secondary')
add_listB.grid(row=14, column=1, sticky='nsew', pady=1, padx=1)

global listsF
listsF = Frame(side_barF)
listsF.grid(row=15, column=0, columnspan=2, sticky='nsew', padx=1, pady=2)

conn = sqlite3.connect('info.db')
c = conn.cursor()

# ----------- All Tasks Section -----------
global backFrame, tasks_frame
backFrame = Frame(root, bootstyle='dark')
backFrame.pack(fill=BOTH, expand=True)

tasks_frame = ScrolledFrame(backFrame, bootstyle='Default, round', width=190)

root.bind('<Configure>', resize_side, add='+')
root.bind('<Home>', home_design)
# ------------------------------------------
#announcer('Introducing Corkboard!', "For miscellaneous notes which don't belong in a list!", 'Corkboard', "Corkboard is your new every day companion for notes which don't exactly fit in a list.\n\n'Pick up kids from school at 4.'\n\nThat may not fit in any list, and that's why Corkboard is here.")
#announcer('Nearing Completion!', "To-Do 4 is almost at the finish line!", "Almost there!", "There are very few things left to do (no pun intended) until this beautiful program is complete.\n\nPlease email dovidstahler9@gmail.com for any suggestions or technical errors.")
#announcer('FINISHED!!!', "To-Do 4 is finally at the finish line!!!!!", "WOO-HOO!!!!", "The long awaited moment has arrived! To-Do 4 is ready for rollout!!!\n\nPlease email dovidstahler9@gmail.com for any suggestions or technical errors.")
#announcer('HOT OFF THE PRESS!!!', "Introducing mini-steps!!!", "Is it true??", "Yes it is!! you can add, delete, and edit mini steps in the task sidebar!!\n\n As we are still in the experimental stages of mini steps, if you encounter any errors, please email dovidstahler9@gmail.com.")
#announcer('COMING SOON!', "It's a mystery! Detective YOU is on the case!", "Coming soon to To-do 4!", "We'll give you a hint. The initials for this exciting new feature are D.A.D.\n\nStay tuned to find out more about this revolutionary new feature!")
#announcer("IT'S A... IT'S A...!", "It's Drag and Drop!!!", "Coming NOW to To-do 4!", "Try dragging a task into another list!! It will move that task and all it's substeps!!")
#announcer('REVOLUTIONARY!!', "Imagine being able to locate settings and help faster than ever!", "Introducing Assistant.", "Simply press Alt + z to activate the assistant! It's so easy I could cry! Just kidding. It's so easy I could burst with joy! Fooled you! I can't burst with joy. But I could be overjoyed!! And I am!!")
announcer('CORKBOARD 2.0 has arrived!', "Corkboard has been completely redesigned!", "Corkboard 2.0 is here!", "Corkboard has been completely redesigned. Pins are now easier to read, and the corkboard is more organized than ever! Get ready for draggable pins, pictures, font customization, and more! Check it out now!")
refresh(return_='False')
home_design()
if sql_process.check_setting('socork') == 'y' and sql_process.check_setting('crk') == 'y':
    corkboard_design()

welcome()
if sql_process.check_setting('pino') == 'on':
    password()
    checkunlocked()
    root.bind('<Return>', checkunlocked)

# ---------------------------------
root.mainloop()
