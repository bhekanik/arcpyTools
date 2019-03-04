# """-----------------------------------------------------------------------------
#  Script Name:      Generate Record Number
#  Description:      Generates the record number for any dataset given the prefix
#                    and the start number
#  Created By:       Bhekani Khumalo
#  Date:             2018-06-21
#  Last Revision:    2018-09-13
# -----------------------------------------------------------------------------"""

import arcpy
import ramm

try:
    # input data
    input_data = arcpy.GetParameterAsText(0)
    recno_prefix = arcpy.GetParameterAsText(1)
    startNumber = arcpy.GetParameterAsText(2)
    log_output = arcpy.GetParameterAsText(3)

    # define the logger
    logger = ramm.defineLogger(log_output)

    def log(message):
        ramm.showPyMessage(message, logger)

    log("Starting Process")

    arcpy.MakeFeatureLayer_management(input_data, "input_data")

    with arcpy.da.UpdateCursor("input_data", 'RECNO') as update_cursor:
        for x in update_cursor:
            # generate record number
            x[0] = ramm.populateRecNo(recno_prefix, startNumber)

            update_cursor.updateRow(x)
    del update_cursor

    log("Record Numbers Generated Successfully!")
except:
    ramm.handleExcept(logger)
