# """-----------------------------------------------------------------------------
# Script Name:    Generate Ekhaya ID
# Description:    Generates a unique ID called the EkhayaID based on the
#                   CENT_X, CENT_Y and whole RECNO field
# Created By:     Bhekani Khumalo
# Date:           2018-06-21
# Last Revision:  2018-10-19
# -----------------------------------------------------------------------------"""

import arcpy
import ramm

try:
    input_data = arcpy.GetParameterAsText(0)
    log_output = arcpy.GetParameterAsText(1)

    logger = ramm.defineLogger(log_output)

    def log(message):
        ramm.showPyMessage(message, logger)

    log("\t Starting Process")

    fields = ['CENT_X', 'CENT_Y', 'RECNO', 'EKHAYAID']

    for data in input_data.split(';'):
        log("Generating EkhayaIDs for {}".format(data))
        with arcpy.da.UpdateCursor(data, fields) as update_cursor:
            for x in update_cursor:
                x[3] = ramm.populateEkhayaID(x[0], x[1], x[2])

                update_cursor.updateRow(x)
        del update_cursor

    log("New EkhayaIDs Generated Successfully!")
except:
    ramm.handleExcept(logger)
