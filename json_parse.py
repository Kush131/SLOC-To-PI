'''
# Summary: Reads a file of project names taken from gerrit and stores the
# results of the query to a database created locally.
#
# WARNING: This could most likely be a lot more efficient! Writing right
# now to attempt quick functionality. If time permits, optimizations will
# occur.
#
# Date Last Updated: 6/16/15
#
# Author: Ryan Kush (Ryan.Kush@garmin.com)
'''

import json  # Used to read JSON file from query
import os  # Used to execute command line commands in python.
import sqlite3  # Used to put data into the database

A = open("projects.txt", 'rt')
PROJ_NUMBER = A.readline().rstrip('\n')
print(PROJ_NUMBER)

for _ in range(int(PROJ_NUMBER)):

    project_name = A.readline()
    project_name = project_name.rstrip('\n')

    filename = project_name+".json"
    filename = filename.rstrip('\n')
    filename = filename.replace('/', '')

    term_command = "ssh -p 29418 kush@gerrit.consumer.garmin.com " + \
        "gerrit query " + "project:" + project_name + \
        " status:merged --format json " + \
        "--patch-sets --files --submit-records > " + filename
    print(term_command)

    db_filename = project_name+".db"
    db_filename = db_filename.rstrip('\n')
    db_filename = db_filename.replace('/', '')

    os.system(term_command)
    db_is_new = not os.path.exists(db_filename)
    conn = sqlite3.connect(db_filename)

    # If timeEstimates.db does not exist we are going to setup the database.
    # Use the schema.ini file to feed a database schema to the database.

    if db_is_new:
        print('Need to create schema')
        with open("schema.ini", 'rt') as f:
            schema = f.read()
            conn.executescript(schema)

    count = 0
    data = {}
    database = {}
    with open(filename) as f:
        for line in f:
            data.update(json.loads(line))
            for info in data['patchSets']:
                s = "insert into estimates VALUES('" + str(data['id']) + \
                    "','" + str(data['project']) + \
                    "','" + str(data['branch']) + \
                    "'," + str(data['createdOn']) + \
                    "," + str(data['lastUpdated']) + \
                    "," + str(info['sizeInsertions']) + \
                    "," + str(info['sizeDeletions']) + ")"
                count += 1
                conn.execute(s)  # Execute the string built above

        print("Total of " + str(count) + " entries inserted into the database")
        # Up until this point no changes have been made to the database.
        conn.commit()
        # This line commits the changes. Waits until all inserst are
        # made to ensure no half-updates are completed.

    # -----------------------------------------------------------------------#
    total_db_filename = "totalProjects.db"
    total_db_is_new = not os.path.exists(db_filename)
    total_conn = sqlite3.connect(db_filename)

    if total_db_is_new:
        print('Need to create schema')
        with open("total_schema.ini", 'rt') as g:
            total_schema = g.read()
            total_conn.executescript(total_schema)

    total_conn = sqlite3.connect('test.db')

    with total_conn:
        cur = total_conn.cursor()
        cur.execute("SELECT * FROM Issues")

    conn.close()  # Close the connection with the DB and finish up.
    total_conn.close()  # Close the connection with the total DB.
