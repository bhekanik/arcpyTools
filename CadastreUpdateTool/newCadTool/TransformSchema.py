""" -----------------------------------------------------------------------------
Tool Name:          Transform Cadastral Dataset Schema
Version:            1.0
Description:        This tool will change the schema of the cadastral                            dataset from
                    the city into the one used at RAMM
Author:             Bhekani Khumalo
Date:               2018-11-29
Last Revision:      2018-11-29
------------------------------------------------------------------------------ """

import arcpy
import time
import ramm

try:
    # get inputs
    input_dataset = arcpy.GetParameterAsText(0)
    output_location = arcpy.GetParameterAsText(1)
    cad_schema_template = arcpy.GetParameterAsText(2)
    fieldMap = arcpy.GetParameterAsText(3)
    spatial_lmun = arcpy.GetParameterAsText(4)
    spatial_dmun = arcpy.GetParameterAsText(5)
    spatial_prov = arcpy.GetParameterAsText(6)
    city_name = arcpy.GetParameterAsText(7)
    provcode = arcpy.GetParameterAsText(8)
    country = arcpy.GetParameterAsText(9)

    arcpy.env.overwriteOutput = True

    rec = 0

    # initialize logger
    logger = ramm.defineLogger(output_location)

    # simplify messege generator
    def log(message):
        ramm.showPyMessage(message, logger)

    # set the workspace
    log("\t Step 1 - Preparing Environment")
    log("\t ...Setting the workspace and generating intemediary datasets")

    arcpy.env.workspace = output_location

    # create temporary geodatabase for temporary geoprocessing tasks
    log("\t ...Creating the results geodatabase")
    arcpy.CreateFileGDB_management(output_location, "results.gdb")

    # make feature layer from the dataset
    arcpy.MakeFeatureLayer_management(input_dataset, "input_dataset")

    # add the dataset to the geodatabase
    log("\t ...Adding the existing dataset into the geodatabase")
    arcpy.FeatureClassToGeodatabase_conversion(
        ["input_dataset"], "results.gdb")

    # make feature layer from the existing dataset
    arcpy.MakeFeatureLayer_management(
        "results.gdb/input_dataset", "lyr_input_dataset_gp")
    arcpy.AddSpatialIndex_management("lyr_input_dataset_gp")

    # create an empty feature class in the temporary geodatabase
    arcpy.CreateFeatureclass_management("results.gdb", "formatted_input", "POLYGON", cad_schema_template,
                                        "DISABLED", "DISABLED", arcpy.Describe(cad_schema_template).spatialReference)

    # make layer from the formatted_input feature class
    arcpy.MakeFeatureLayer_management(
        "results.gdb/formatted_input", "lyr_formatted_input")
    arcpy.AddSpatialIndex_management("lyr_formatted_input")

    log("\t Step 2 - Reformatting Dataset")

    # build field mappings and append the data into lyr_formatted_input
    log("\t ...Creating field mappings and formating table")
    ramm.mapFields("lyr_input_dataset_gp", "lyr_formatted_input", fieldMap)
    arcpy.AddSpatialIndex_management("lyr_formatted_input")

    # check the geometry of the formatted_input feature class
    log("\t ...Checking and repairing the geometry")
    arcpy.CheckGeometry_management(
        "lyr_formatted_input", "results.gdb/geomErrorReport")

    # get the number of records in the geometry errors report and if there are no features then delete the report
    no_of_geom_errors = int(arcpy.GetCount_management(
        "results.gdb/geomErrorReport").getOutput(0))
    if no_of_geom_errors == 0:
        # delete the empty report
        arcpy.Delete_management("results.gdb/geomErrorReport")
    else:
        # repair geometry errors on the changes_unformated feature class
        arcpy.RepairGeometry_management("lyr_formatted_input")

    # count the number of records in formatted_input
    no_of_records_formated = int(arcpy.GetCount_management(
        "lyr_formatted_input").getOutput(0))

    # capitalise the Street Suffix data
    arcpy.CalculateField_management(
        "lyr_formatted_input", "STREETSUFF", "!STREETSUFF!.upper()", "PYTHON_9.3")

    # populate fields
    log("\t ...Populating the Local Municipality, District "
        "Municipality, Admin District Code and Province fields based on a spatial join.")

    ramm.populateUsingSpatialJoin(
        "lyr_formatted_input", spatial_lmun, "LOCALMUN", "FULLNAME", "INTERSECT")
    ramm.populateUsingSpatialJoin(
        "lyr_formatted_input", spatial_dmun, "DISTRICTMU", "FULLNAME", "INTERSECT")
    ramm.populateUsingSpatialJoin(
        "lyr_formatted_input", spatial_dmun, "ADMINDISCO", "DISTRICTCO", "INTERSECT")
    ramm.populateUsingSpatialJoin(
        "lyr_formatted_input", spatial_prov, "PROVINCE", "PROVNAME", "INTERSECT")

    # generate calculated fields, ie Area, Perimeter, Cent_x and Cent_y
    log(
        "\t ...Calculating the Area, Perimeter, Centroid X and Centroid Y fields")
    arcpy.CalculateField_management(
        "lyr_formatted_input", 'AREA', "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3")
    arcpy.CalculateField_management(
        "lyr_formatted_input", 'PERIMETER', "!SHAPE.LENGTH@METERS!", "PYTHON_9.3")
    arcpy.CalculateField_management(
        "lyr_formatted_input", 'CENT_X', "!SHAPE.CENTROID.X!", "PYTHON_9.3")
    arcpy.CalculateField_management(
        "lyr_formatted_input", 'CENT_Y', "!SHAPE.CENTROID.Y!", "PYTHON_9.3")

    # fields for the update cursor
    log("\t ...Populating the DESC_, TOWNSHIPCO, COUNTRY, PROVINCECO, EXTENTCO, ERFNO, "
        "PORTIONNO, REMAINDER and CITYNAME fields")
    fields = ['DESC_', 'TOWNSHIPCO', 'EXTENTCO', 'ERFNO', 'PORTIONNO', 'REMAINDER', 'CITYSG26CO', 'STREETNO',
              'STREETNAME', 'STREETSUFF', 'SUBURBNAME', 'CENT_X', 'CENT_Y', 'COUNTRY', 'PROVINCECO', 'CITYNAME']

    # main code
    with arcpy.da.UpdateCursor("lyr_formatted_input", fields) as update_cursor:
        for x in update_cursor:
            # description
            x[0] = x[7] + ', ' + x[8] + ', ' + x[9] + ', ' + x[10]

            # decoding the SG26 Code
            [x[1], x[2], x[3], x[4], x[5]] = ramm.decodeCitySG26Code(x[6])

            x[13] = country
            x[14] = provcode
            x[15] = city_name

            update_cursor.updateRow(x)
    del update_cursor

    log(
        "\t Step 2 completed successfully.")

    log("\t Process completed successfully!")

    arcpy.ClearWorkspaceCache_management()
except:
    ramm.handleExcept(logger)
