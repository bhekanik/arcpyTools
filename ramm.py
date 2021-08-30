import arcpy
import time
import logging
import traceback
import os
import sys

rec = 0


def defineLogger(log_location=""):
    logger = logging.getLogger(__name__)
    x = list(logger.handlers)
    for i in x:
        logger.removeHandler(i)
        i.flush()
        i.close()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s : %(message)s')
    file_handler = logging.FileHandler(log_location + '/log.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.debug(
        "\n \n ********************** {} ************************\n \n".format(str(time.ctime())))
    return logger


def populateCPID(id_start):
    pinterval = 1
    pStart = int(id_start)
    global rec

    if rec == 0:
        rec = id_start
    else:
        rec += pinterval

    ans = str(rec)

    finans = ans.rjust(8, '0')

    return 'CP' + finans


def populateRecNo(recno_prefix, startNumber):
    pinterval = 1
    pStart = int(startNumber)
    global rec

    if rec == 0:
        rec = pStart
    else:
        rec += pinterval

    ans = str(rec)

    finans = ans.rjust(11, '0')

    return recno_prefix + finans


def populateEkhayaID(cent_x, cent_y, recno):
    lat = int(cent_x * 1100000)
    lon = int(cent_y * 1100000)
    rec_string = recno[:4]

    finlat = hex(lat)[2:].rjust(8, '0')
    finlon = hex(lon)[2:].rjust(8, '0')

    return rec_string.upper() + finlat.upper() + finlon.upper()


def populateNewEkhayaID(cent_x, cent_y, recno):
    lat = int(cent_x * 1100000)
    lon = int(cent_y * 1100000)
    rec_string1 = recno[:9]
    rec_string2 = int(recno[-11:])

    finlat = hex(lat)[2:].rjust(8, '0')
    finlon = hex(lon)[2:].rjust(8, '0')
    finrec_string2 = hex(rec_string2)[2:].rjust(10, '0')

    return rec_string1.upper() + finrec_string2.upper() + finlat.upper() + finlon.upper()


def populateUsingSpatialJoin(input_dataset, spatialjoin_dataset, update_field, source_field, spatialjoin_type):
    arcpy.MakeFeatureLayer_management(
        spatialjoin_dataset, "lyr_spatialjoin_dataset")
    search_cursor = arcpy.SearchCursor("lyr_spatialjoin_dataset")
    for row in search_cursor:
        arcpy.SelectLayerByAttribute_management("lyr_spatialjoin_dataset", "NEW_SELECTION",
                                                "\"FID\" = " + str(row.getValue("FID")))
        arcpy.SelectLayerByLocation_management(input_dataset, spatialjoin_type, "lyr_spatialjoin_dataset", "",
                                               "NEW_SELECTION")
        arcpy.CalculateField_management(input_dataset, update_field,
                                        "'{0}'".format(str(row.getValue(source_field))), "PYTHON_9.3", "")
    del search_cursor


def populateUsingSpatialJoinFC(input_dataset, spatialjoin_dataset, update_field, source_field, spatialjoin_type):
    arcpy.MakeFeatureLayer_management(
        spatialjoin_dataset, "lyr_spatialjoin_dataset")
    search_cursor = arcpy.SearchCursor("lyr_spatialjoin_dataset")
    for row in search_cursor:
        arcpy.SelectLayerByAttribute_management("lyr_spatialjoin_dataset", "NEW_SELECTION",
                                                "\"OBJECTID\" = " + str(row.getValue("OBJECTID")))
        arcpy.SelectLayerByLocation_management(input_dataset, spatialjoin_type, "lyr_spatialjoin_dataset", "",
                                               "NEW_SELECTION")
        arcpy.CalculateField_management(input_dataset, update_field,
                                        "'{0}'".format(str(row.getValue(source_field))), "PYTHON_9.3", "")
    del search_cursor


def mapFields(input_dataset, output_dataset, field_map_table):
    # list the fields which contain the field map info.
    fields = ["SourceFieldname", "DestinationFieldName"]

    # define function to get unique field values from a table
    def GetUniqueFieldValues(table, field):
        """
        Retrieves and prints a list of unique values in a user-specified field

        Args:
            table (str): path or name of a feature class, layer, table, or table view
            field (str): name of the field for which the user wants unique values

        Returns:
            uniqueValues (list): a list of the unique values in the field
        """
        # get the values
        with arcpy.da.SearchCursor(table, [field]) as cursor:
            return sorted({row[0] for row in cursor})

    # get a list of unique output fields
    output_fields = GetUniqueFieldValues(
        field_map_table, "DestinationFieldName")

    # create an empty field mappings object
    fm = arcpy.FieldMappings()

    # build the field mappings object
    for f in output_fields:
        # create a field map object
        fMap = arcpy.FieldMap()
        with arcpy.da.SearchCursor(field_map_table, fields,
                                   """{0} = '{1}'""".format("DestinationFieldName", f)) as cursor:
            for row in cursor:
                # add the input field to the field map
                fMap.addInputField(input_dataset, row[0])
        # set the output name
        output_field_name = fMap.outputField
        output_field_name.name = f
        fMap.outputField = output_field_name

        # add the field map to the field mappings object
        fm.addFieldMap(fMap)

    # perform the append
    arcpy.Append_management(input_dataset, output_dataset, "NO_TEST", fm)


def decodeCitySG26Code(citySG26Code_field):
    townshipCode_field = citySG26Code_field[:4]
    extentCode_field = citySG26Code_field[4:8]
    erfNumber_field = citySG26Code_field[8:16].lstrip('0')
    portionNumber_field = citySG26Code_field[16:21]
    remainder_field = citySG26Code_field[24:]

    return [townshipCode_field, extentCode_field, erfNumber_field, portionNumber_field, remainder_field]


def prepareOutput(gdbFeatureClass, outputLocation, shapefileName):
    arcpy.FeatureClassToShapefile_conversion(gdbFeatureClass, outputLocation)
    arcpy.DeleteField_management(gdbFeatureClass, "SHAPE_Leng")
    arcpy.DeleteField_management(gdbFeatureClass, "Shape_Area")
    arcpy.DeleteField_management(gdbFeatureClass, "OBJECTID")
    arcpy.Rename_management(gdbFeatureClass + ".shp",
                            shapefileName + "_{}.shp".format(time.strftime("%Y%m%d")))


def showPyMessage(message, logger, messageType="Message"):
    if (messageType == "Message"):
        arcpy.AddMessage(str(time.ctime()) + " - " + message)
        logger.debug(message)
    if (messageType == "Warning"):
        arcpy.AddWarning(str(time.ctime()) + " - " + message)
        logger.warning(message)
    if (messageType == "Error"):
        arcpy.AddError(str(time.ctime()) + " - " + message)
        logger.error(message)


def handleExcept(logger):
    message = "\n*** PYTHON ERRORS *** "
    showPyMessage(message, logger, "Error")
    message = "Python Traceback Info: " + \
        traceback.format_tb(sys.exc_info()[2])[0]
    showPyMessage(message, logger, "Error")
    message = "Python Error Info: " + \
        str(sys.exc_type) + ": " + str(sys.exc_value) + "\n"
    showPyMessage(message, logger, "Error")
