"""-----------------------------------------------------------------------------
     Script Name:      Generate CP IDs
     Version:          1.1
     Description:      This tool will create a field called CPID and populate it
                       with the CPIDs in the format CPXXXXXXXXX whete XXXXXXXXX is
                       a 9 digit number starting from the start number given as input.
     Created By:       Bhekani Khumalo
     Date:             2018-06-29
     Last Revision:    2018-10-31
-----------------------------------------------------------------------------"""

import arcpy
import ramm

arcpy.env.overwriteOutput = True
try:
    input_data = arcpy.GetParameterAsText(0)
    startNumber = arcpy.GetParameterAsText(1)
    output_location = arcpy.GetParameterAsText(3)

    rec = 0

    # initialize logger
    logger = ramm.defineLogger(output_location)

    # simplify messege generator
    def log(message):
        ramm.showPyMessage(message, logger)

    log("- Starting Process")
    arcpy.MakeFeatureLayer_management(input_data, "lyr_input_data")
    arcpy.AddField_management("lyr_input_data", "CPID", "TEXT")

    with arcpy.da.UpdateCursor("lyr_input_data", 'CPID') as update_cursor:
        for x in update_cursor:
            # generate CPID
            x[0] = ramm.populateCPID(startNumber)

            update_cursor.updateRow(x)
    del update_cursor

    log("- Process Complete")
except:
    ramm.handleExcept(logger)
