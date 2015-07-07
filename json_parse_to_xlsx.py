'''
# Summary: Reads a file of project names taken from gerrit and stores the
# results of the query to an excel file created locally.
#
# WARNING: This could most likely be a lot more efficient! Writing right
# now to attempt quick functionality. If time permits, optimizations will
# occur.
#
# Date Last Updated: 6/25/15
#
# Author: Ryan Kush (Ryan.Kush@garmin.com)
'''

import json  # Used to read JSON file from query.
import xlsxwriter  # Used to put data into the excel file.
import os  # Used to execute the terminal command.
import datetime  # Unix time into y/m/w/d format
import pprint  # Pretty printer for formatting (can remove once dev is done)

A = open("projects.txt", 'rt')
PROJ_NUMBER = A.readline().rstrip('\n')
print(PROJ_NUMBER + " projects detected to scan\n")

for _ in range(int(PROJ_NUMBER)):

    project_name = A.readline()
    project_name = project_name.rstrip('\n')

    filename = project_name+".json"
    filename = filename.rstrip('\n')
    filename = filename.replace('/', '')

    term_command = "ssh -p 29418 kush@gerrit.consumer.garmin.com " + \
        "gerrit query " + "project:" + project_name + \
        " limit:10000 status:merged --format json " + \
        "--patch-sets --files --submit-records > " + filename
    print(term_command)

    os.system(term_command)

    with open(filename) as f:
        data = {}
        COL = 0
        ROW = 0
        SPREADSHEET_NAME = project_name + '.xlsx'
        SPREADSHEET_NAME = SPREADSHEET_NAME.rstrip('\n')
        SPREADSHEET_NAME = SPREADSHEET_NAME.replace('/', '')
        WORKBOOK = xlsxwriter.Workbook(SPREADSHEET_NAME)
        WORKSHEET = WORKBOOK.add_worksheet()
        pp = pprint.PrettyPrinter(depth=6)
        for line in f:
            data.update(json.loads(line))
            pp.pprint(data)
            print("\n\n\n")
            '''
            if 'trackingIds' not in data:
                pass
            else:
                for info in data['patchSets']:
                    WORKSHEET.write(ROW, COL,
                                    str(data['trackingIds'][0]['id']))
                    WORKSHEET.write(ROW, COL + 1, str(data['project']))
                    COL += 1
                    WORKSHEET.write(ROW, COL + 1, str(data['branch']))
                    COL += 1
                    WORKSHEET.write(ROW, COL + 1,
                                    str(datetime.datetime.fromtimestamp(
                                        int(data['createdOn'])).strftime(
                                            '%Y-%m-%d %H:%M:%S')))
                    COL += 1
                    WORKSHEET.write(ROW, COL + 1,
                                    str(datetime.datetime.fromtimestamp(
                                        int(data['lastUpdated'])).strftime(
                                            '%Y-%m-%d %H:%M:%S')))
                    COL += 1
                    WORKSHEET.write(ROW, COL + 1, str(info['sizeInsertions']))
                    COL += 1
                    WORKSHEET.write(ROW, COL + 1, str(info['sizeDeletions']))
                    ROW += 1
                    COL = 0

        print("\nTotal of " + str(ROW) +
              " rows were parsed and possibly entered\n")
        '''
        WORKBOOK.close()
