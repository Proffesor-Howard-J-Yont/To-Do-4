import sqlite3
import random as rd

conn_user000 = sqlite3.connect('user000.db')
c_user000 = conn_user000.cursor()

conn = sqlite3.connect('info.db')
c = conn.cursor()

abcs = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
creepy_hidden_name = []

def create_table():
    print('Creating table "list_names"')
    c_user000.execute('''CREATE TABLE list_names (
    display_name text,
    hidden_name text,
    stack text,
    color text,
    hiarchy text
    )''')
    print('Command executed successfully!')
    conn_user000.commit()
def create_table2():
    print('Creating table "corkboard"')
    c_user000.execute('''CREATE TABLE corkboard (
    title text,
    actual text,
    color text,
    position_x real,
    position_y real,
    content_json text,
    image_path text
    )''')
    print('Command executed successfully!')
    conn_user000.commit()


def migrate_corkboard_positions():
    c_user000.execute("PRAGMA table_info(corkboard)")
    existing_cols = [col[1] for col in c_user000.fetchall()]
    if 'position_x' not in existing_cols:
        c_user000.execute("ALTER TABLE corkboard ADD COLUMN position_x REAL")
    if 'position_y' not in existing_cols:
        c_user000.execute("ALTER TABLE corkboard ADD COLUMN position_y REAL")
    conn_user000.commit()

def update_pin_position(rowid, x, y):
    c_user000.execute(
        "UPDATE corkboard SET position_x=?, position_y=? WHERE rowid=?",
        (x, y, rowid)
    )
    conn_user000.commit()

def migrate_corkboard_content():
    c_user000.execute("PRAGMA table_info(corkboard)")
    existing_cols = [col[1] for col in c_user000.fetchall()]
    if 'content_json' not in existing_cols:
        c_user000.execute("ALTER TABLE corkboard ADD COLUMN content_json TEXT")
    if 'image_path' not in existing_cols:
        c_user000.execute("ALTER TABLE corkboard ADD COLUMN image_path TEXT")
    conn_user000.commit()

def migrate_task_schedule_columns():
    """Adds schedule_date, schedule_start, schedule_duration to every task
    table (independent of due-date columns). Safe to call every startup --
    no-ops once present."""
    c.execute("SELECT * FROM sqlite_master WHERE type='table'")
    all_tables = c.fetchall()
    needed = {
        'schedule_date': 'TEXT',
        'schedule_start': 'TEXT',
        'schedule_duration': 'TEXT',
    }
    for table in all_tables:
        table_name = table[1]
        if table_name == 'sqlite_sequence':
            continue
        try:
            c.execute("PRAGMA table_info('{}')".format(table_name))
            existing_cols = [col[1] for col in c.fetchall()]
        except sqlite3.OperationalError:
            continue
        for col, coltype in needed.items():
            if col not in existing_cols:
                try:
                    c.execute("ALTER TABLE '{}' ADD COLUMN {} {}".format(table_name, col, coltype))
                except sqlite3.OperationalError:
                    continue
    conn.commit()

def migrate_task_block_color_column():
    """Adds block_color to every task table -- an optional custom hex
    color for how a task's My Day timeline block/all-day banner renders,
    independent of schedule/due-date columns. Null/empty means "use the
    default checked/starred/primary coloring". Safe to call every
    startup -- no-ops once present."""
    c.execute("SELECT * FROM sqlite_master WHERE type='table'")
    all_tables = c.fetchall()
    for table in all_tables:
        table_name = table[1]
        if table_name == 'sqlite_sequence':
            continue
        try:
            c.execute("PRAGMA table_info('{}')".format(table_name))
            existing_cols = [col[1] for col in c.fetchall()]
        except sqlite3.OperationalError:
            continue
        if 'block_color' not in existing_cols:
            try:
                c.execute("ALTER TABLE '{}' ADD COLUMN block_color TEXT".format(table_name))
            except sqlite3.OperationalError:
                continue
    conn.commit()

def ensure_setting(initials, default_yn):
    """Insert a Settings row with a default value if one doesn't already
    exist for this key. Safe to call every startup."""
    c_user000.execute("SELECT setyn FROM Settings WHERE setting_name=?", (initials,))
    if c_user000.fetchone() is None:
        add_setting(initials, default_yn)

def migrate_corkboard_schema():
    """Adds all corkboard columns introduced since the original 3-column
    version, if missing. Safe to call every startup -- no-ops once present."""
    c_user000.execute("PRAGMA table_info(corkboard)")
    existing_cols = [col[1] for col in c_user000.fetchall()]
    needed = {
        'position_x': 'REAL',
        'position_y': 'REAL',
        'content_json': 'TEXT',
        'image_path': 'TEXT',
    }
    for col, coltype in needed.items():
        if col not in existing_cols:
            #c_user000.execute(f"ALTER TABLE corkboard ADD COLUMN {col} {coltype}")
            pass
    conn_user000.commit()

def update_pin_position(rowid, x, y):
    c_user000.execute("UPDATE corkboard SET position_x=?, position_y=? WHERE rowid=?",(x, y, rowid))
    conn_user000.commit()

def update_pin_content(rowid, title, content_json, image_path):
    c_user000.execute(
        "UPDATE corkboard SET title=?, content_json=?, image_path=? WHERE rowid=?",
        (title, content_json, image_path, rowid)
    )
    conn_user000.commit()

def update_pin_color(rowid, color):
    c_user000.execute(
        "UPDATE corkboard SET color=? WHERE rowid=?",
        (color, rowid)
    )
    conn_user000.commit()

def delete_pin(rowid):
    c_user000.execute("DELETE FROM corkboard WHERE rowid=?", (rowid,))
    conn_user000.commit()

def get_all_image_paths():
    c_user000.execute("SELECT image_path FROM corkboard WHERE image_path IS NOT NULL")
    return [row[0] for row in c_user000.fetchall()]



def add_list(displayname):
    newdisplayname1 = displayname.strip(' ')
    if newdisplayname1 != '':# and len(newdisplayname1) < 16:
        creepy_hidden_nameL = []
        for add_a_letter in range(0, 10):
            creepy_hidden_nameL.append(rd.choice(abcs))
        r10l_result = ''.join(creepy_hidden_nameL)
        c_user000.execute('''INSERT INTO list_names VALUES ('{}','{}','{}','{}','{}')'''.format(newdisplayname1, r10l_result, 'This list is not in a stack.', 'Standard', 'Medium'))
        conn_user000.commit()
        c.execute("""CREATE TABLE '{}' (task text, checked text, starred text, difficulty text, duedateday text, duedatetime text, duedateonoff text, amiaministep text, whichminiami text, importance text, notes text, schedule_date text, schedule_start text, schedule_duration text, block_color text)""".format(r10l_result))
        conn.commit()
        return ['List has been created successfully.', r10l_result]
    else:
        return ['An error has occured: Input is either over 15 letters, or is just spaces.', 'customers']
        # list_names: display_name, hidden_name, stack, color, hiarchy
def delete_list(deletee):
    if deletee != 'customers':
        c.execute("DROP TABLE '{}'".format(deletee))
        conn.commit()
        c_user000.execute("DELETE from list_names WHERE hidden_name='{}'".format(deletee))
        conn_user000.commit()
    else:
        print("You can't delete the Default List.")
def rename_list(current, renamee):
    newlistrename = renamee.strip(' ')
    if newlistrename != '':
        c_user000.execute("""UPDATE list_names SET display_name='{}' WHERE hidden_name='{}'""".format(newlistrename, current))
        conn_user000.commit()
    else:
        print('nice try.')
def get_lists():
    global all_lists
    c_user000.execute("""SELECT * FROM list_names""")
    all_the_lists = c_user000.fetchall()

    return all_the_lists
def get_current_list_display(current):
    c_user000.execute('''SELECT display_name FROM list_names WHERE hidden_name='{}' '''.format(current))
    currentdisplaycatcher = c_user000.fetchone()
    if currentdisplaycatcher != None:
        return currentdisplaycatcher
    else:
        return 'Unrecognized'

def get_list_color(hidden_name):
    """Returns (hex_color,) -- '' (not the dead 'Standard' sentinel every
    list is created with) when no real color has been set, so callers
    never need to special-case that string themselves."""
    c_user000.execute("SELECT color FROM list_names WHERE hidden_name=?", (hidden_name,))
    row = c_user000.fetchone()
    if row is None or row[0] in (None, 'Standard'):
        return ('',)
    return row

def set_list_color(hidden_name, hex_color):
    """hex_color='' resets to the same 'Standard' sentinel fresh lists
    already have, rather than introducing a second "unset" convention."""
    c_user000.execute("UPDATE list_names SET color=? WHERE hidden_name=?", (hex_color or 'Standard', hidden_name))
    conn_user000.commit()

def get_columns(table_name):
    c.execute("""PRAGMA table_info('{}')""".format(table_name))
    column_names = c.fetchall()
    for single_column_name in column_names:
        print(single_column_name[1])

def add_setting(initials, yn):
    c_user000.execute("""INSERT INTO Settings VALUES('{}','{}')""".format(initials, yn))
    conn_user000.commit()

    c_user000.execute("""SELECT * FROM Settings""")
    collection = c_user000.fetchall()

    for artifact in collection:
        print(artifact)
def check_setting(initials):
    c_user000.execute("""SELECT setyn FROM Settings WHERE setting_name='{}'""".format(initials))
    return c_user000.fetchone()[0]
def setting_configure(initials, switchto):
    c_user000.execute("""UPDATE Settings SET setyn='{}' WHERE setting_name='{}'""".format(switchto, initials))
    conn_user000.commit()

def get_ministeps(taskid, list_name):
    c.execute("""SELECT rowid,* FROM '{}' WHERE amiaministep='yes' AND whichminiami = '{}' """.format(list_name, taskid))
    return c.fetchall()
def delete_setting(initials):
    c_user000.execute("""DELETE FROM Settings WHERE setting_name='{}'""".format(initials))
    conn_user000.commit()

    c_user000.execute("""SELECT * FROM Settings""")
    collection = c_user000.fetchall()

    for artifact in collection:
        print(artifact)


#c.execute('''ALTER TABLE customers RENAME TO `{}`'''.format())
#conn.commit()
#c_user000.execute('''SELECT * FROM sqlite_master WHERE type='table' ''')
#sdfh = c_user000.fetchall()
#for asdf in sdfh:
#    print(asdf[4])
#    print('yooo')
#def_folder, customers

#print('Welcome to the To-Do 4 Sqlite3 Processes Hub!\nYou can reach me at dovidstahler9@gmail.com.')
