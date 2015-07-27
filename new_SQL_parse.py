"""
SLIM SQL Script.

Reads the results of an SQL and JQL statement (that are stored as JSON) and
puts the results inside of a SQL database.

Date Last Updated: 7/17/15

Author: Ryan Kush (Ryan.Kush@garmin.com)
"""

import json  # Used to read JSON file from query
import os  # Used to execute command line commands in python.
import sqlite3  # Used to put data into the database
import time  # Used to sleep script for 5 seconds
import math  # Used to round up numbers
from query import query  # JIRA query file


import pprint
pp = pprint.PrettyPrinter(depth=6)


def collectLines(new_file, project_name, jiraNew, jiraDefects, lc_add, lc_sub):
    """Collect total lines changed for a JIRA issue."""
    data = {}
    with open(new_file) as f:
        for line in f:
            total_add = 0
            total_sub = 0
            keys_found = 0
            data.update(json.loads(line))
            if 'trackingIds' not in data:
                continue
            else:
                for x in data['trackingIds']:
                    g_key = x['id']
                    for x in (jiraNew + jiraDefects):
                        if x['key'] == g_key:
                            keys_found += 1
                            s = len(x)
                            for info in data['patchSets']:
                                total_add += info['sizeInsertions']/s
                                total_sub += info['sizeDeletions']/s
                    if g_key in lc_add and keys_found != 0:
                        lc_add[g_key] += total_add
                        lc_sub[g_key] += total_sub
                    elif keys_found != 0:
                        lc_add[g_key] = total_add
                        lc_sub[g_key] = total_sub
                    else:
                        continue
    f.close()


def jiraCollect(x, a_m, s_m):
    """Collect info from JIRA patch for insertion."""
    results_list = []
    do_want = True

    if (x['fields']['aggregatetimespent'] !=
            x['fields']['aggregatetimeestimate']):
        temp = x['fields']['aggregatetimespent']
        add_estimatedEffort = a_m * int(temp) / 3600
        sub_estimatedEffort = s_m * int(temp) / 3600
    else:
        add_estimatedEffort = -1
        sub_estimatedEffort = -1
        do_want = False

    if x['fields']['assignee']:
        if x['fields']['assignee']['name']:
            a = x['fields']['assignee']['name']
            results_list.append(a)
            if a is None:
                a = "NONE"
                results_list.append(a)
        else:
            a = "NONE"
            results_list.append(a)
    else:
        a = "NONE"
        results_list.append(a)
    if x['fields']['reporter']:
        if x['fields']['reporter']['name']:
            r = x['fields']['reporter']['name']
            results_list.append(r)
            if r is None:
                r = "NONE"
                results_list.append(r)
        else:
            r = "NONE"
            results_list.append(r)
    else:
        r = "NONE"
        results_list.append(r)
    if x['fields']['components']:
        c = x['fields']['components'][0]['name']
        results_list.append(c)
        if c is None:
            c = "NONE"
            results_list.append(c)
    else:
        c = "NONE"
        results_list.append(c)

    results_list.append(add_estimatedEffort)
    results_list.append(sub_estimatedEffort)
    results_list.append(do_want)
    return results_list


def addToDB(filename, project_name, db, jira, new_or_defect,
            key_count, lc_add, lc_sub, key_exist):
    """Add query information to database."""
    # Metric variables.
    insert = 0  # How many inserts we process
    total_gerrit = 0  # How many Gerrit patches we process
    duplicate_jira = 0  # How many duplicate JIRA ID's we find.

    conn = sqlite3.connect(db)

    data = {}  # Dictionary for us to put our data into

    with open(filename) as f:
        for line in f:
            total_gerrit += 1
            data.update(json.loads(line))

            #  If we can't find a JIRA associated with this gerrit patch, skip
            #  it. We have no purpose for this data.
            if 'trackingIds' not in data:
                continue

            #  If we can find an associated JIRA in our patch set, we can
            #  begin to extract the relevant data for insertion into the
            #  database.
            else:
                for issue in data['trackingIds']:
                    do_want = True  # We start out wanting this JIRA in our set
                    total_add = 0  # How many insertions from the gerrit patch?
                    total_sub = 0  # How many deletions from this gerrit patch?
                    gerrit_key = issue['id']  # Define the JIRA in the gerrit.

                    if gerrit_key in key_exist:
                        continue

                    if gerrit_key not in lc_add:
                        continue
                    else:
                        total_add = math.ceil(lc_add[gerrit_key])
                        total_sub = math.ceil(lc_sub[gerrit_key])

                    #  If we find that we have no lines changed, go to the next
                    #  gerrit patch, this is a useless patch.
                    if total_add == 0 and total_sub == 0:
                        continue

                    #  Calculate the effort modifiers for lines of code.
                    #  Allows us to differentiate how much effort should
                    #  go to new/modified or defect/modified.
                    add_modifier = total_add / (total_add + abs(total_sub))
                    sub_modifier = total_sub / (total_add + abs(total_sub))

                    for x in jira:
                        jira_key = x['key']
                        # Found a match? Fetch our info from the JIRA
                        if gerrit_key == jira_key:
                            if jira_key in key_count:
                                key_count[jira_key] += 1
                            else:
                                key_count[jira_key] = 1
                            do_want = True
                            jira_payload = jiraCollect(x,
                                                       add_modifier,
                                                       sub_modifier)

                            # Pop everything from our payload into the
                            # appropriate variable that we want to store the
                            # data into.
                            do_want = jira_payload.pop()
                            sub_estimatedEffort = math.ceil(jira_payload.pop())
                            add_estimatedEffort = math.ceil(jira_payload.pop())
                            comp = jira_payload.pop()
                            reporter = jira_payload.pop()
                            assignee = jira_payload.pop()

                            # If we find that we have 0 hours and 0 lines the
                            # data does not really matter, so lets remove it
                            # from the database.
                            if add_estimatedEffort == 0 and total_add == 0:
                                do_want = False

                            if sub_estimatedEffort == 0 and total_sub == 0:
                                do_want = False

                            if do_want:
                                if new_or_defect == 0:
                                    s = "insert into estimates " + \
                                        "VALUES(\'NEW\'," + \
                                        str(abs(add_estimatedEffort)) + "," + \
                                        str(abs(total_add)) + \
                                        ",\'" + assignee + \
                                        "\',\'" + reporter + "\',\'" + comp + \
                                        "\',\'" + jira_key + "\')"
                                    print(s)
                                    key_exist[jira_key] = 1
                                else:
                                    s = "insert into estimates " + \
                                        "VALUES(\'DEFECTS\'," + \
                                        str(abs(add_estimatedEffort)) + "," + \
                                        str(abs(total_add)) + \
                                        ",\'" + assignee + \
                                        "\',\'" + reporter + "\',\'" + comp + \
                                        "\',\'" + jira_key + "\')"
                                    print(s)
                                    key_exist[jira_key] = 1

                                conn.execute(s)
                                conn.commit()
                                s = "insert into estimates " + \
                                    "VALUES(\'MODIFIED\'," + \
                                    str(abs(sub_estimatedEffort)) + "," + \
                                    str(abs(total_sub)) + \
                                    ",\'" + assignee + \
                                    "\',\'" + reporter + "\',\'" + comp + \
                                    "\',\'" + jira_key + "\')"
                                print(s)
                                key_exist[jira_key] = 1
                                insert += 1
                                conn.execute(s)
                            break
                        else:
                            continue

    print(filename + " Summary:")
    print("\nTotal of " + str(insert) + " rows were inserted\n" +
          "Total of " + str(duplicate_jira) + " have keys in database.")

    #  "Total of " + str(noMatchingKey) +
    #  " went unmatched due to not finding JIRA issue inside query.\n" +

    # Commits our changes to the database. Running this so late ensures
    # that if there is an error in the middle of a query, there will be
    # no error data in the database.
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# MAIN METHOD
# -----------------------------------------------------------------------------

# Open the projects.txt file, which contains all the info we need for
# gathering data from JIRA and Gerrit.

A = open("new_projects.txt", 'rt')
PROJ_NUMBER = A.readline().rstrip('\n')
print(PROJ_NUMBER + " projects detected to scan\n\nIf this is incorrect, " +
      "press CONTROL + C to end the program immediately to fix your issues\n" +
      "\nExecution will pause for 5 seconds, then begin.\n")

time.sleep(5)  # Give user a chance to cancel command if error is detected.
old_data = True  # Use old JSON files (1) or collect new ones (0)
debug = False

for _ in range(int(PROJ_NUMBER)):

    # Read the project name from the file and strip the newline and slashes
    # out of the file name. This is done so when files are created we avoid
    # errors of our files looking like directories and erroring out our
    # program.
    project_name = A.readline()
    project_name = project_name.rstrip('\n')

    # Reads in the JIRA query keyword used in our query script. Should not
    # contain slashes off the bat, so we should not need to edit this.
    jira_new = A.readline()
    jira_new = jira_new.rstrip('\n')

    # Reads in the JIRA query keyword used in our query script. Should not
    # contain slashes off the bat, so we should not need to edit this.
    jira_defects = A.readline()
    jira_defects = jira_defects.rstrip('\n')

    # Format the file name and strip the newline and slashes from the name.
    filename = project_name.rstrip('\n')
    filename = filename.replace('/', '')

    if old_data is False:
        print("\nCollecting NEW Queries...\n")
        jiraNew = query(jira_new)
        with open('jiraNew.json', 'w') as fp:
            json.dump(jiraNew, fp)
        print("\nCollecting DEFECT Queries...\n")
        jiraDefects = query(jira_defects)
        with open('jiraDefects.json', 'w') as fp:
            json.dump(jiraDefects, fp)
    else:
        with open('jiraNew.json', 'r') as fp:
            jiraNew = json.load(fp)
        with open('jiraDefects.json', 'r') as fp:
            jiraDefects = json.load(fp)

    total_new_JIRA = 0  # How many new JIRA's we process.
    total_defects_JIRA = 0  # How many defect JIRA's we process.

    # Create the database project name and strip out slashes + new lines.
    db_filename = project_name + ".db"
    db_filename = db_filename.rstrip('\n')
    db_filename = db_filename.replace('/', '')

    # Create a boolean that will tell us if we have already created the file.
    db_is_new = not os.path.exists(db_filename)
    conn = sqlite3.connect(db_filename)

    # If timeEstimates.db does not exist we are going to setup the database.
    # Use the schema.ini file to feed a database schema to the database.

    if db_is_new:
        print('Need to create schema')
        with open("new_schema.ini", 'rt') as f:
            schema = f.read()
            conn.executescript(schema)

    # Initial setup of database table
    conn.close()

    key_exist = {}
    key_count = {}  # Does the JIRA issue already exist?
    lc_add = {}
    lc_sub = {}

    total_new_JIRA = len(jiraNew)
    total_defects_JIRA = len(jiraDefects)

    queryTotal = 0
    while queryTotal < total_new_JIRA + total_defects_JIRA:

        # Terminal command to be executed to grab JSON data from the gerrit
        # server. Utilizes SSH attached to my username, so make sure you
        # replace the username with your username and create an SSH key for
        # your computer if you do not currently have it set up. Confluence
        # should have answers about this if you are confused.

        new_file = filename + str(queryTotal) + ".json"

        term_command = "ssh -p 29418 kush@gerrit.consumer.garmin.com " + \
            "gerrit query " + "project:" + project_name + \
            " status:merged --format=json --patch-sets --files" + \
            " --submit-records -S " + str(queryTotal) + " > " + new_file

        # Execute our terminal command that we created above. At this point,
        # we have a valid .JSON file with all of our project data without the
        # time estimates. We will pull this info from JIRA later. Also looks
        # at old data flag to avoid time wastes.

        if old_data is False:
            print(term_command)
            os.system(term_command)

        collectLines(new_file, project_name, jiraNew,
                     jiraDefects, lc_add, lc_sub)

        queryTotal += 500

    queryTotal = 0
    while queryTotal < total_new_JIRA + total_defects_JIRA:
        new_file = filename + str(queryTotal) + ".json"
        addToDB(new_file, project_name, db_filename,
                jiraNew, 0, key_count, lc_add, lc_sub, key_exist)
        addToDB(new_file, project_name, db_filename,
                jiraDefects, 1, key_count, lc_add, lc_sub, key_exist)
        queryTotal += 500

if debug is True:
    for x in key_count:
        print(x)
        print(key_count[x])
# pylama:ignore=C901, E501
