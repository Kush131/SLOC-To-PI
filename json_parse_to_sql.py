'''
# Summary: Reads a file of project names taken from gerrit and stores the
# results of the query to a database created locally.
#
# Date Last Updated: 6/3/15
#
# Author: Ryan Kush (Ryan.Kush@garmin.com)
'''

import json  # Used to read JSON file from query
import os  # Used to execute command line commands in python.
import sqlite3  # Used to put data into the database
import time  # Used to sleep script for 5 seconds
import re
from query import query

# Open the projects.txt file, which contains all the info we need for
# gathering data from JIRA and Gerrit.
A = open("projects.txt", 'rt')
PROJ_NUMBER = A.readline().rstrip('\n')
print(PROJ_NUMBER + " projects detected to scan\nIf this is incorrect, " +
      "press CONTROL + C to end the program immediately to fix your issues\n" +
      "Execution will pause for 5 seconds, then begin.\n")

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

    print(jira_name)

    # Format the file name and strip the newline and slashes from the name.
    filename = project_name+".json"
    filename = filename.rstrip('\n')
    filename = filename.replace('/', '')

    # Terminal command to be executed to grab JSON data from the gerrit
    # server. Utilizes SSH attached to my username, so make sure you
    # replace the username with your username and create an SSH key for
    # your computer if you do not currently have it set up. Confluence
    # should have answers about this if you are confused.
    term_command = "ssh -p 29418 kush@gerrit.consumer.garmin.com " + \
        "gerrit query " + "project:" + project_name + \
        " limit:10000 status:merged --format json " + \
        "--patch-sets --files --submit-records > " + filename

    # Print out our terminal command just as a syntax check for user.
    print(term_command)

    # Create the database project name and strip out slashes + new lines.
    db_filename = project_name+".db"
    db_filename = db_filename.rstrip('\n')
    db_filename = db_filename.replace('/', '')

    # Execute our terminal command that we created above. At this point,
    # we have a valid .JSON file with all of our project data without the
    # time estimates. We will pull this info from JIRA later.
    os.system(term_command)

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

    count = 0  # Counts how many queries we run.
    data = {}  # Dictionary for us to put our data into

    jiraQuery = query(jira_name)

    # The next few lines open the .JSON file, puts one JSON object into
    # the data variable, and then runs an insert query against the database
    # we created earlier. It will run until we hit the end of the file.
    with open(filename) as f:
        for line in f:
            data.update(json.loads(line))
            for info in data['patchSets']:
                if ('trackingIds' not in data or info['sizeInsertions'] == 0
                        and info['sizeDeletions'] == 0):
                    pass
                else:
                    estimatedEffort = -1
                    for x in jiraQuery:
                        gerritKey = data['trackingIds'][0]['id']
                        jiraKey = x['key']
                        #  print("Comparing " + jiraKey + " and " + gerritKey)
                        if gerritKey == jiraKey and estimatedEffort == -1:
                            print("Comparing " + jiraKey + " and " + gerritKey)
                            estimatedEffort = int(
                                x['fields']['aggregatetimespent'])
                            print("True Comparison")
                            break

                    s = "insert into estimates VALUES('" + str(
                        data['trackingIds'][0]['id']) + \
                        "','" + str(data['project']) + \
                        "','" + str(data['branch']) + \
                        "'," + str(data['createdOn']) + \
                        "," + str(data['lastUpdated']) + \
                        "," + str(info['sizeInsertions']) + \
                        "," + str(info['sizeDeletions']) + \
                        "," + str(estimatedEffort) + ")"

                    print(s)
                    count += 1
                    conn.execute(s)  # Execute the string built above

    print("\nTotal of " + str(count) +
          " rows were parsed and possibly entered\n" +
          "This does not account for duplicates.\n")
    # Commits our changes to the database. Running this so late ensures
    # that if there is an error in the middle of a query, there will be
    # no error data in the database.
    conn.commit()
