# -*- coding: utf-8 -*-
"""
Support library to create and access the users personal history database
"""

import sqlite3, os

try:
    import json
except ImportError, ie:
    import simplejson as json

import settings

USERS_HOME = settings.YABISTORE_HOME
    
HISTORY_FILE = "history.sqlite3"

DB_CREATE = """
CREATE TABLE "yabistoreapp_tag" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "value" varchar(255) NOT NULL UNIQUE
)
;
CREATE TABLE "yabistoreapp_workflow" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(255) NOT NULL,
    "json" text NOT NULL,
    "last_modified_on" datetime,
    "created_on" datetime NOT NULL,
    "archived_on" datetime NOT NULL,
    "status" text NOT NULL
)
;
CREATE TABLE "yabistoreapp_workflowtag" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "workflow_id" integer NOT NULL REFERENCES "yabistoreapp_workflow" ("id"),
    "tag_id" integer NOT NULL REFERENCES "yabistoreapp_tag" ("id")
)
;
CREATE INDEX "yabistoreapp_workflowtag_workflow_id" ON "yabistoreapp_workflowtag" ("workflow_id");
CREATE INDEX "yabistoreapp_workflowtag_tag_id" ON "yabistoreapp_workflowtag" ("tag_id");
"""

VALID_USERNAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@"

WORKFLOW_VARS = ['id','name','json','last_modified_on','created_on','status']
WORKFLOW_QUERY_LINE = "id,name,json,date(last_modified_on),date(created_on),status"

##
## Errors
##
class NoSuchWorkflow(Exception): pass

def user_fs_home(username):
    """Return users home directory path. creates it if it doesn't exist"""
    
    # sanity check username. Just to catch any problems that might rise defesively
    assert False not in [c in VALID_USERNAME_CHARS for c in username], "Invalid username '%s'"%username
    
    dir = os.path.join(USERS_HOME,username)
    if not os.path.exists(dir):
        os.mkdir(dir)
    return dir

def create_user_db(username):
    """Create the sqlite database to store the users history in"""
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
    
    conn = sqlite3.connect(db)
    
    c = conn.cursor()
    for command in DB_CREATE.split(';'):
        c.execute(command)
    conn.commit()
    c.close()

    # now chmod the file to make it writable by celeryd
    # TODO: Fix this permissions issue. Celeryd is running as user and yabiadmin is running as 'apache' and both need to write to this database
    os.chmod(db,0777)                   # we need to write to the file as another user
    os.chmod(home,0777)                 # AND we need to write to the directory as another user for the -journal sqlite file
    
def ensure_user_db(username):
    """if the users db doesn't exist, create it"""
    if not does_db_exist(username):
        create_user_db(username)
    
def does_db_exist(username):
    """does the users database exist. 0 byte files don't count"""
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
    
    if not os.path.exists(db):
        return False
    
    st = os.stat(db)
    if not st.st_size:
        # zero size
        os.unlink(db)
        return False
    
    return True

def does_workflow_exist(username, **kwargs):
    assert len(kwargs) == 1
    assert kwargs.keys()[0] in ('id', 'name')

    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
        
    conn = sqlite3.connect(db)
    c = conn.cursor()

    field = kwargs.keys()[0]
    c.execute('SELECT * FROM yabistoreapp_workflow WHERE %s = ?' % field,
              (kwargs[field],))
    data = c.fetchall()

    c.close()
    return (len(data) >= 0)

def workflow_names_starting_with(username, base):
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
        
    conn = sqlite3.connect(db)
    c = conn.cursor()

    c.execute('SELECT name FROM yabistoreapp_workflow WHERE name like ?',
              (base + '%',))
    result = [r[0] for r in c]

    c.close()
    return result
   
    
def save_workflow(username, workflow, taglist=[]):
    """place a row in the workflow table"""
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
    
    conn = sqlite3.connect(db)
   
    c = conn.cursor()
    c.execute('INSERT INTO "yabistoreapp_workflow" ' +
            '(id, name, json, status, created_on, last_modified_on, archived_on) ' +
            'VALUES (?,?,?,?,?,?,julianday("now"))',
            (workflow.id, workflow.name, workflow.json, workflow.status, workflow.created_on, workflow.last_modified_on))
        
    for tag in taglist:
        # see if the tag already exists
        c.execute('SELECT id FROM yabistoreapp_tag WHERE value = ?', (tag,) )
        data = c.fetchall()
        
        if len(data)==0:
            c.execute('INSERT INTO "yabistoreapp_tag" (value) VALUES (?)',(tag,) )
        
            # link the many to many
            c.execute('INSERT INTO "yabistoreapp_workflowtag" (workflow_id, tag_id) VALUES (?, last_insert_rowid())', (workflow.id,))
        else:
            # link the many to many
            c.execute('INSERT INTO "yabistoreapp_workflowtag" (workflow_id, tag_id) VALUES (?, ?)', (workflow.id,data[0][0]))
    
    conn.commit()
    c.close()

def change_workflow_tags(username, id, taglist=None):
    """Change the tags of a given workflow"""
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
    
    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    if taglist is not None:
        c.execute("""SELECT DISTINCT yabistoreapp_tag.value 
                    FROM yabistoreapp_workflowtag, yabistoreapp_tag 
                    WHERE yabistoreapp_tag.id = yabistoreapp_workflowtag.tag_id 
                    AND yabistoreapp_workflowtag.workflow_id = ?""", (id,) )
    
        oldtaglist=[]
        for row in c:
            oldtaglist.append(row[0])
            
        # delete the old taglist
        detag_workflow(username, id, oldtaglist, cursor=c)
        
        # now add the new taglist in
        tag_workflow(username, id, taglist, cursor=c)
        
    conn.commit()
    c.close()
    
def tag_workflow(username,workflow_id,taglist=[], cursor=None):
    """add tags to an existing workflow"""
    if cursor is None:
        home = user_fs_home(username)
        db = os.path.join(home, HISTORY_FILE)
        
        conn = sqlite3.connect(db)
        
        c = conn.cursor()
    else:
        c = cursor
        conn = None
        
    c.execute('SELECT * FROM yabistoreapp_workflow WHERE id=?',(workflow_id,))
    
    data = c.fetchall()
    
    # check for no workflow
    if len(data)==0:
        raise NoSuchWorkflow, "Workflow id %d not found for user %s"%(workflow_id,username)
    
    for tag in taglist:
        # see if the tag already exists
        c.execute('SELECT id FROM yabistoreapp_tag WHERE value = ?', (tag,) )
        data = c.fetchall()
        
        if len(data)==0:
            c.execute('INSERT INTO "yabistoreapp_tag" (value) VALUES (?)',(tag,) )
        
            # link the many to many
            c.execute('INSERT INTO "yabistoreapp_workflowtag" (workflow_id, tag_id) VALUES (?, last_insert_rowid())', (workflow_id,))
        else:
            # link the many to many
            c.execute('INSERT INTO "yabistoreapp_workflowtag" (workflow_id, tag_id) VALUES (?, ?)', (workflow_id,data[0][0]))
        
    if conn is not None:
        conn.commit()
        c.close()
    
def detag_workflow(username, workflow_id, taglist=[], delete_empty=True, cursor=None):
    """Unlinks the list of tags from a workflow.
    if delete_empty is True (default), then the tag will be deleted if it tags nothing
    """
    if cursor is None:
        home = user_fs_home(username)
        db = os.path.join(home, HISTORY_FILE)
        
        conn = sqlite3.connect(db)
        
        c = conn.cursor()
    else:
        c = cursor
        conn = None
        
    c.execute('SELECT * FROM yabistoreapp_workflow WHERE id=?',(workflow_id,))
    
    data = c.fetchall()
    
    # check for no workflow
    if len(data)==0:
        raise NoSuchWorkflow, "Workflow id %d not found for user %s"%(workflow_id,username)
    
    
    for tag in taglist:
        # see if the tag  exists
        c.execute('SELECT id FROM yabistoreapp_tag WHERE value = ?', (tag,) )
        data = c.fetchall()

        if len(data)==1:
            tag_id = data[0][0]
            # delete any many to many links
            c.execute('DELETE FROM yabistoreapp_workflowtag WHERE workflow_id = ? AND tag_id = ?', (workflow_id, tag_id) )
            
            if delete_empty:
                # is the tag now empty
                c.execute('SELECT count() FROM yabistoreapp_workflowtag WHERE yabistoreapp_workflowtag.tag_id = ?',(tag_id,))
                data = c.fetchall()
        
                if data[0][0]==0:
                    # no more tag links left. delete.
                    c.execute('DELETE FROM yabistoreapp_tag WHERE id = ?',(tag_id,))
        
    if conn is not None:
        conn.commit()
        c.close()
            
def get_tags_for_workflow(username, id, cursor=None):
    if cursor is None:
        home = user_fs_home(username)
        db = os.path.join(home, HISTORY_FILE)
        
        conn = sqlite3.connect(db)
        
        c = conn.cursor()
    else:
        c = cursor
        conn = None
    
    c.execute('SELECT yabistoreapp_tag.value FROM yabistoreapp_tag, yabistoreapp_workflowtag WHERE yabistoreapp_workflowtag.tag_id = yabistoreapp_tag.id AND yabistoreapp_workflowtag.workflow_id = ?',(id,))
    
    data = [X[0] for X in c]
    
    if conn is not None: 
        conn.commit()
        c.close()
    
    return data

def find_workflow_by_date(username, start, end='now', sort="created_on", dir="DESC", get_tags=True):
    """find all the users workflows between the 'start' date and the 'end' date
    sort is an optional parameter to sort by
    if end is ommitted, it refers to now.
    returns a list of workflow hashes
    """
    assert sort in WORKFLOW_VARS
    assert dir in ('ASC','DESC')
    
    # TODO: sanity check julianday field 'start' and 'end'
    
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
    
    conn = sqlite3.connect(db)
    
    c = conn.cursor()
    c.execute("""SELECT %s FROM yabistoreapp_workflow
        WHERE created_on >= date(?)
        AND created_on <= date(?)
        ORDER BY %s %s"""%(WORKFLOW_QUERY_LINE,sort,dir),
        (start,end) )
    
    rows = []
    for row in c:
        rows.append( dict( zip( WORKFLOW_VARS, row ) ) )

    if get_tags:
        for row in rows:
            row['tags'] = get_tags_for_workflow(username, int(row['id']), cursor = c)
            # AH When I successfully broke admin and put broken workflows in the store
            # this code was exploding when trying to json.loads, so try/catch/pass
            try:
                row['json'] = json.loads(row['json'])
            except ValueError:
                pass

    conn.commit()
    c.close()
    
    return rows

def get_workflow(username, id, get_tags=True):
    """Return workflow with id 'id'
    """
    home = user_fs_home(username)
    db = os.path.join(home, HISTORY_FILE)
    
    conn = sqlite3.connect(db)
    
    c = conn.cursor()
    c.execute("""SELECT %s FROM yabistoreapp_workflow
        WHERE id = ? """%WORKFLOW_QUERY_LINE,
        (id,) )
    
    rows = c.fetchall()
    
    if len(rows)==0:
        raise NoSuchWorkflow, "Workflow %d for user %s does not exist"%(id,username)
        
    result = dict( zip( WORKFLOW_VARS, rows[0] ) )
    if get_tags:
        result['tags'] = get_tags_for_workflow(username, int(result['id']), cursor = c)
    
    # decode the json object
    result['json']=json.loads(result['json'])
    
    conn.commit()
    c.close()
    
    return result


