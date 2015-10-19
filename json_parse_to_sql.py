"""
SLIM SQL Script.

Reads the results of an SQL and JQL statement (that are stored as JSON) and
puts the results inside of a SQL database.

Date Last Updated: 7/14/15

Author: Ryan Kush (Ryan.Kush@garmin.com)
"""

import json  # Used to read JSON file from query
import os  # Used to execute command line commands in python.
import sqlite3  # Used to put data into the database
import time  # Used to sleep script for 5 seconds
from query import query  # JIRA query file


def addToDB(filename, project_name, jiraQuery, keyExists):
    """Add query information to database."""
    noTrackID = 0  # Gerrit does not have a JIRA ID
    estimateSame = 0  # Estimated time + work time is same
    noMatchingKey = 0  # If we cannot find a JIRA that matches our ID
    update = 0  # How many updates we process
    insert = 0  # How many inserts we process
    totalGerrit = 0  # How many Gerrit patches we process

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
        with open("schema.ini", 'rt') as f:
            schema = f.read()
            conn.executescript(schema)

    # Block for creating Gerrit patch dictionary.
    data = {}  # Dictionary for us to put our data into

    with open(filename) as f:
        for line in f:
            totalGerrit += 1
            data.update(json.loads(line))
            if 'trackingIds' not in data:
                noTrackID += 1
            else:
                doWant = True
                totalAdd = 0
                totalSub = 0
                for info in data['patchSets']:
                    totalAdd = + info['sizeInsertions']
                    totalSub = + info['sizeDeletions']

                estimatedEffort = -1
                for x in jiraQuery:
                    gerritKey = data['trackingIds'][0]['id']
                    jiraKey = x['key']
                    if gerritKey == jiraKey:
                        if (x['fields']['aggregatetimespent'] !=
                                x['fields']['aggregatetimeestimate']):
                            estimatedEffort = (
                                int(x['fields']['aggregatetimespent']))
                        else:
                            estimateSame += 1
                            doWant = False

                if estimatedEffort == -1:
                    noMatchingKey += 1
                    doWant = False

                if data['trackingIds'][0]['id'] not in keyExists and doWant:
                    s = "insert into estimates VALUES('" + str(
                        data['trackingIds'][0]['id']) + \
                        "','" + str(data['project']) + \
                        "','" + str(data['branch']) + \
                        "'," + str(data['createdOn']) + \
                        "," + str(data['lastUpdated']) + \
                        "," + str(totalAdd) + \
                        "," + str(totalSub) + \
                        "," + str(estimatedEffort) + ")"

                    print(s)
                    insert += 1
                    conn.execute(s)  # Execute the string built above
                    keyExists[data['trackingIds'][0]['id']] = 1

                #  Add up patch changes and update SQL entry.
                elif data['trackingIds'][0]['id'] in keyExists and doWant:
                    s = "update estimates SET " + \
                        "insertions = insertions + " + str(totalAdd) + \
                        " AND " + \
                        "deletions = deletions + " + str(totalSub) + \
                        " where id = \'" + \
                        str(data['trackingIds'][0]['id']) + \
                        "\'"

                    update += 1
                    print(s)
                    conn.execute(s)  # Execute the string built above
                    keyExists[data['trackingIds'][0]['id']] = 1

                else:
                    pass

    print(filename + " Summary:\n")
    print("\nTotal of " + str(insert) + " rows were inserted\nTotal of " +
          str(update) + " were updated\n Total of " + str(noTrackID) +
          " went unmatched due to lack of matching JIRA ID in Gerrit\n" +
          " Total of " + str(estimateSame) + " went unmatched due to " +
          " estimate matching time worked\n Total of " +
          str(noMatchingKey) + " went unmatched due to not finding JIRA " +
          "issue inside JIRA query.")

    # Commits our changes to the database. Running this so late ensures
    # that if there is an error in the middle of a query, there will be
    # no error data in the database.
    conn.commit()

# -----------------------------------------------------------------------------
# MAIN METHOD
# -----------------------------------------------------------------------------

# Open the projects.txt file, which contains all the info we need for
# gathering data from JIRA and Gerrit.

A = open("projects.txt", 'rt')
PROJ_NUMBER = A.readline().rstrip('\n')
print(PROJ_NUMBER + " projects detected to scan\n\nIf this is incorrect, " +
      "press CONTROL + C to end the program immediately to fix your issues\n" +
      "\nExecution will pause for 5 seconds, then begin.\n")

time.sleep(5)  # Give user a chance to cancel command if error is detected.

for _ in range(int(PROJ_NUMBER)):

    # Read the project name from the file and strip the newline and slashes
    # out of the file name. This is done so when files are created we avoid
    # errors of our files looking like directories and erroring out our
    # program.
    project_name = A.readline()
    project_name = project_name.rstrip('\n')

    # Reads in the JIRA query keyword used in our query script. Should not
    # contain slashes off the bat, so we should not need to edit this.
    jira_name = "project=" + A.readline()
    jira_name = jira_name.rstrip('\n')
    jira_name = jira_name + " AND statusCategory=Complete"  # Optimization
    jira_name = jira_name.rstrip('\n')
    jira_name = jira_name + " AND timespent != NULL"  # Optimization
    jira_name = jira_name.rstrip('\n')

    # Format the file name and strip the newline and slashes from the name.
    filename = project_name.rstrip('\n')
    filename = filename.replace('/', '')

    jiraQuery = query(jira_name)
    totalJIRA = len(jiraQuery)

    # To future programmer: Dear lord change this. We are in crunch time for
    # results for this project and this is a terrible terrible way to get them.
    # Please find a more efficient way to detect when we are out of gerrit
    # patches. The result of the system command returns a JSON object with rows
    # parsed so that is a good start.

    keyExists = {}  # Does the JIRA issue already exist?

    queryTotal = 0
    while queryTotal < totalJIRA:

        # Terminal command to be executed to grab JSON data from the gerrit
        # server. Utilizes SSH attached to my username, so make sure you
        # replace the username with your username and create an SSH key for
        # your computer if you do not currently have it set up. Confluence
        # should have answers about this if you are confused.

        new_file = filename + str(queryTotal) + ".json"

        term_command = "ssh -p 29418 kush@gerrit.consumer.garmin.com " + \
            "gerrit query " + "project:" + project_name + \
            " status:merged --format=json --patch-sets --files" + \
            " --submit-records >> " + new_file

        # Print out our terminal command just as a syntax check for user.
        print(term_command)

        # Execute our terminal command that we created above. At this point,
        # we have a valid .JSON file with all of our project data without the
        # time estimates. We will pull this info from JIRA later.
        os.system(term_command)
        addToDB(new_file, project_name, jiraQuery, keyExists)
        queryTotal += 500

# pylama:ignore=C901
