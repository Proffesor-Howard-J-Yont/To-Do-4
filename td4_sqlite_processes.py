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
        color text
        )''')
    print('Command executed successfully!')
    conn_user000.commit()
def add_list(displayname):
    newdisplayname1 = displayname.strip(' ')
    if newdisplayname1 != '':# and len(newdisplayname1) < 16:
        creepy_hidden_nameL = []
        for add_a_letter in range(0, 10):
            creepy_hidden_nameL.append(rd.choice(abcs))
        r10l_result = ''.join(creepy_hidden_nameL)
        c_user000.execute('''INSERT INTO list_names VALUES ('{}','{}','{}','{}','{}')'''.format(newdisplayname1, r10l_result, 'This list is not in a stack.', 'Standard', 'Medium'))
        conn_user000.commit()
        c.execute("""CREATE TABLE '{}' (task text, checked text, starred text, difficulty text, duedateday text, duedatetime text, duedateonoff text, amiaministep text, whichminiami text, importance text, notes text)""".format(r10l_result))
        conn.commit()
        return 'List has been created successfully.'
    else:
        return 'An error has occured: Input is either over 15 letters, or is just spaces.'
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
#c.execute('''SELECT * FROM sqlite_master WHERE type='table' ''')
#sdfh = c.fetchall()
#for asdf in sdfh:
#    print(asdf[4])
#def_folder, customers
print('Welcome to the To-Do 4 Sqlite3 Processes Hub!\nYou can reach me at dovidstahler9@gmail.com.')
