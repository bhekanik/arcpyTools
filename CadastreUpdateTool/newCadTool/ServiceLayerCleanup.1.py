""" -----------------------------------------------------------------------------
Tool Name:          Service Layer Cleanup
Version:            1.0
Description:        Put description here
Author:             Bhekani Khumalo
Date:               2019-01-15
Last Revision:      2019-01-15
------------------------------------------------------------------------------ """

import arcpy
import time
import ramm

try:
    # get inputs
    existing_dataset = arcpy.GetParameterAsText(0)
    update_dataset = arcpy.GetParameterAsText(1)
    current_master_cad = arcpy.GetParameterAsText(2)
    output_location = arcpy.GetParameterAsText(3)
    roads_dataset = arcpy.GetParameterAsText(4)
    cad_schema_template = arcpy.GetParameterAsText(5)
    fieldMap = arcpy.GetParameterAsText(6)
    spatial_lmun = arcpy.GetParameterAsText(7)
    spatial_dmun = arcpy.GetParameterAsText(8)
    spatial_prov = arcpy.GetParameterAsText(9)
    city_name = arcpy.GetParameterAsText(10)
    provcode = arcpy.GetParameterAsText(11)
    country = arcpy.GetParameterAsText(12)

    arcpy.env.overwriteOutput = True

    rec = 0

    # initialize logger
    logger = ramm.defineLogger(output_location)

    # simplify messege generator
    def log(message):
        ramm.showPyMessage(message, logger)

    # set the workspace
    log("\t Step 1 - Finding changes")
    log("\t ...Setting the workspace and generating intemediary datasets")

    arcpy.env.workspace = output_location

    # create temporary geodatabase for temporary geoprocessing tasks
    log("\t ...Creating the results geodatabase")
    arcpy.CreateFileGDB_management(output_location, "results.gdb")

    # make feature layer from the existing dataset
    arcpy.MakeFeatureLayer_management(existing_dataset, "existing_dataset")
    arcpy.MakeFeatureLayer_management(update_dataset, "update_dataset")

    # add the datasets to the geodatabase
    log("\t ...Adding the existing and update datasets into the geodatabase")
    arcpy.FeatureClassToGeodatabase_conversion(["existing_dataset", "update_dataset"],
                                               "results.gdb")

    # make feature layer from the existing dataset
    arcpy.MakeFeatureLayer_management(
        "results.gdb/existing_dataset", "lyr_existing_gp")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/update_dataset", "lyr_update_gp")
    arcpy.AddSpatialIndex_management("lyr_update_gp")
    arcpy.AddIndex_management(
        "lyr_update_gp", "SL_LAND_PR", "UlkIndex", "UNIQUE")
    arcpy.AddSpatialIndex_management("lyr_existing_gp")
    arcpy.AddIndex_management(
        "lyr_existing_gp", "SL_LAND_PR", "ElkIndex", "UNIQUE")

    # create an empty feature class in the temporary geodatabase
    arcpy.CreateFeatureclass_management("results.gdb", "changes_formated", "POLYGON", cad_schema_template,
                                        "DISABLED", "DISABLED", arcpy.Describe(cad_schema_template).spatialReference)

    # join existing_data's data into update_data's data using the LISKEY field
    log("\t ...Joining the existing and update datasets based on the LIS Key")
    arcpy.JoinField_management("lyr_update_gp", "SL_LAND_PR", "lyr_existing_gp",
                               "SL_LAND_PR", ["SL_LAND_PR"])

    # select from the feature layer the features where the LISKEY is null
    log("\t ...Selecting the records from the joined layer where the existing LIS Key is null")
    arcpy.SelectLayerByAttribute_management(
        "lyr_update_gp", "NEW_SELECTION", "\"SL_LAND_PR_1\" IS NULL")

    # save selection to new feature class
    log("\t ...Saving the selection to a new feature class called changes")
    arcpy.CopyFeatures_management(
        "lyr_update_gp", "results.gdb/changes_unformated")

    # make layer from the changes_unformated feature class
    arcpy.MakeFeatureLayer_management(
        "results.gdb/changes_unformated", "lyr_changes_unformated")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/changes_formated", "lyr_changes_formated")
    arcpy.AddSpatialIndex_management("lyr_changes_unformated")
    arcpy.AddSpatialIndex_management("lyr_changes_formated")

    # count the number of records in changes_unformated
    no_of_records = int(arcpy.GetCount_management(
        "lyr_changes_unformated").getOutput(0))

    # only continue if the number of records in changes is greater than 0
    if no_of_records == 0:
        arcpy.ClearWorkspaceCache_management()
        arcpy.Delete_management("results.gdb")
        log("\t Process completed. No changes were found")
    else:
        log("\t Step 1 completed successfully. {} changes found.".format(no_of_records))
        log("\t Step 2 - Processing Changes.")

        identicalLIS = False
        identicalGeom = False

        # check the geometry of the changes_unformated feature class
        log("\t ...Checking and repairing the geometry")
        arcpy.CheckGeometry_management(
            "lyr_changes_unformated", "results.gdb/geomErrorReport")

        # get the number of records in the geometry errors report and if there are no features then delete the report
        no_of_geom_errors = int(arcpy.GetCount_management(
            "results.gdb/geomErrorReport").getOutput(0))
        if no_of_geom_errors == 0:
            # delete the empty report
            arcpy.Delete_management("results.gdb/geomErrorReport")
        else:
            # repair geometry errors on the changes_unformated feature class
            arcpy.RepairGeometry_management("lyr_changes_unformated")

        # find any records that have the same LISKEY, SG26CODE and geometry
        log("\t ...Identifying and removing duplicates")
        arcpy.FindIdentical_management("lyr_changes_unformated", "results.gdb/identicalGeomLISSG26Report",
                                       ["SHAPE", "SL_LAND_PR", "SG26_CODE"], "", "0", "ONLY_DUPLICATES")

        # get the number of records in the identical features report and if there are no features then delete the report
        no_of_identical_records_geomLISSG26 = int(arcpy.GetCount_management(
            "results.gdb/identicalGeomLISSG26Report").getOutput(0))
        if no_of_identical_records_geomLISSG26 == 0:
            # delete empty report
            arcpy.Delete_management("results.gdb/identicalGeomLISSG26Report")
        else:
            # delete the duplicates
            arcpy.DeleteIdentical_management("lyr_changes_unformated", [
                "SHAPE", "SL_LAND_PR", "SG26_CODE"], "", "0")

        # find any records that have the same LISKEY and geometry
        arcpy.FindIdentical_management("lyr_changes_unformated", "results.gdb/identicalGeomLISReport",
                                       ["SHAPE", "SL_LAND_PR"], "", "0", "ONLY_DUPLICATES")

        # get the number of records in the identical features report and if there are no features then delete the report
        no_of_identical_records_geomLIS = int(arcpy.GetCount_management(
            "results.gdb/identicalGeomLISReport").getOutput(0))
        if no_of_identical_records_geomLIS == 0:
            # delete empty report
            arcpy.Delete_management("results.gdb/identicalGeomLISReport")
        else:
            # delete the duplicates
            arcpy.DeleteIdentical_management("lyr_changes_unformated", [
                "SHAPE", "SL_LAND_PR"], "", "0")

        # find any records that have the same LISKEY
        arcpy.FindIdentical_management("lyr_changes_unformated", "results.gdb/identicalLISReport",
                                       ["SL_LAND_PR"], "", "0", "ONLY_DUPLICATES")

        # get the number of records in the identical features report and if there are no features then delete the report
        no_of_identical_records_LIS = int(arcpy.GetCount_management(
            "results.gdb/identicalLISReport").getOutput(0))
        if no_of_identical_records_LIS == 0:
            # delete empty report
            arcpy.Delete_management("results.gdb/identicalLISReport")
        else:
            identicalLIS = True

        arcpy.FindIdentical_management("lyr_changes_unformated", "results.gdb/identicalGeomReport",
                                       ["SHAPE"], "", "0", "ONLY_DUPLICATES")

        # get the number of records in the identical features report and if there are no features then delete the report
        no_of_identical_records_geom = int(arcpy.GetCount_management(
            "results.gdb/identicalGeomReport").getOutput(0))
        if no_of_identical_records_geom == 0:
            # delete empty report
            arcpy.Delete_management("results.gdb/identicalGeomReport")
        else:
            identicalGeom = True

        # build field mappings and append the data into lyr_changes_formated
        log(
            "\t ...Creating field mappings and formating table")
        ramm.mapFields("lyr_changes_unformated",
                       "lyr_changes_formated", fieldMap)
        arcpy.AddSpatialIndex_management("lyr_changes_formated")

        # count the number of records in changes_formated
        no_of_records_formated = int(arcpy.GetCount_management(
            "lyr_changes_formated").getOutput(0))

        # capitalise the Street Suffix data
        arcpy.CalculateField_management(
            "lyr_changes_formated", "STREETSUFF", "!STREETSUFF!.upper()", "PYTHON_9.3")

        # polulate fields using spatial joins
        log("\t ...Populating the Local Municipality, District "
            "Municipality, Admin District Code and Province fields based on a spatial join.")

        ramm.populateUsingSpatialJoin(
            "lyr_changes_formated", spatial_lmun, "LOCALMUN", "FULLNAME", "INTERSECT")
        ramm.populateUsingSpatialJoin(
            "lyr_changes_formated", spatial_dmun, "DISTRICTMU", "FULLNAME", "INTERSECT")
        ramm.populateUsingSpatialJoin(
            "lyr_changes_formated", spatial_dmun, "ADMINDISCO", "DISTRICTCO", "INTERSECT")
        ramm.populateUsingSpatialJoin(
            "lyr_changes_formated", spatial_prov, "PROVINCE", "PROVNAME", "INTERSECT")

        # generate calculated fields, ie Area, Perimeter, Cent_x and Cent_y
        log(
            "\t ...Calculating the Area, Perimeter, Centroid X and Centroid Y fields")
        arcpy.CalculateField_management(
            "lyr_changes_formated", 'AREA', "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3")
        arcpy.CalculateField_management(
            "lyr_changes_formated", 'PERIMETER', "!SHAPE.LENGTH@METERS!", "PYTHON_9.3")
        arcpy.CalculateField_management(
            "lyr_changes_formated", 'CENT_X', "!SHAPE.CENTROID.X!", "PYTHON_9.3")
        arcpy.CalculateField_management(
            "lyr_changes_formated", 'CENT_Y', "!SHAPE.CENTROID.Y!", "PYTHON_9.3")

        # fields for the update cursor
        log("\t ...Populating the DESC_, TOWNSHIPCO, COUNTRY, PROVINCECO, EXTENTCO, ERFNO, "
            "PORTIONNO, REMAINDER and CITYNAME fields")
        fields = ['DESC_', 'TOWNSHIPCO', 'EXTENTCO', 'ERFNO',
                  'PORTIONNO', 'REMAINDER', 'CITYSG26CO',
                  'STREETNO', 'STREETNAME', 'STREETSUFF',
                  'SUBURBNAME', 'CENT_X', 'CENT_Y',
                  'COUNTRY', 'PROVINCECO', 'CITYNAME']

        # main code
        with arcpy.da.UpdateCursor("lyr_changes_formated", fields) as update_cursor:
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

        # select all the polygons that intersect with roads and save them into a new feature class called changes_rr
        log(
            "\t ...Selecting all the polygons that intersection with roads and saving them into a new feature class called changes_rr")
        arcpy.MakeFeatureLayer_management(roads_dataset, "lyr_roads_dataset")
        arcpy.AddSpatialIndex_management("lyr_roads_dataset")
        arcpy.SelectLayerByLocation_management(
            "lyr_changes_formated", "INTERSECT", "lyr_roads_dataset", selection_type="NEW_SELECTION")
        arcpy.CopyFeatures_management(
            "lyr_changes_formated", "results.gdb/changes_rr")
        arcpy.AddSpatialIndex_management("results.gdb/changes_rr")
        no_of_records_changes_rr = int(arcpy.GetCount_management(
            "results.gdb/changes_rr").getOutput(0))

        # save the remaining polygons into a new feature class called changes_xrr
        arcpy.SelectLayerByLocation_management(
            "lyr_changes_formated", "INTERSECT", "lyr_roads_dataset", "", "NEW_SELECTION", "INVERT")
        arcpy.CopyFeatures_management(
            "lyr_changes_formated", "results.gdb/changes_xrr")

        # select from the feature layer the features where the Area < 3 and save this to a new feature class called changes_xrr_area3
        log(
            "\t ...Selecting the records from the joined layer where the Area < 3")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/changes_xrr", "lyr_changes_xrr")
        arcpy.AddSpatialIndex_management("lyr_changes_xrr")
        arcpy.AddIndex_management("lyr_changes_xrr", "AREA", "aIndex")
        arcpy.SelectLayerByAttribute_management(
            "lyr_changes_xrr", "NEW_SELECTION", "\"AREA\" < 3")
        log(
            "\t ...Saving the selection to a new feature class called changes_xrr_area3")
        arcpy.CopyFeatures_management(
            "lyr_changes_xrr", "results.gdb/changes_xrr_area3")
        arcpy.AddSpatialIndex_management("results.gdb/changes_xrr_area3")
        no_of_records_changes_xrr_area3 = int(arcpy.GetCount_management(
            "results.gdb/changes_xrr_area3").getOutput(0))

        # save the remaining polygons into a new feature class called changes_xrr_xarea3
        arcpy.SelectLayerByAttribute_management(
            "lyr_changes_xrr", "SWITCH_SELECTION")
        arcpy.CopyFeatures_management(
            "lyr_changes_formated", "results.gdb/changes_xrr_xarea3")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/changes_xrr_xarea3", "lyr_changes_xrr_xarea3")
        arcpy.AddSpatialIndex_management("lyr_changes_xrr_xarea3")

        # get polygons that intersect the current master and save them into a new feature class called changes_overlap
        arcpy.MakeFeatureLayer_management(
            current_master_cad, "lyr_current_master_cad")
        arcpy.AddSpatialIndex_management("lyr_current_master_cad")
        arcpy.SelectLayerByLocation_management(
            "lyr_changes_xrr_xarea3", "INTERSECT", "lyr_current_master_cad", selection_type="NEW_SELECTION")
        arcpy.CopyFeatures_management(
            "lyr_changes_xrr_xarea3", "results.gdb/changes_overlap")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/changes_overlap", "lyr_changes_overlap")
        arcpy.AddSpatialIndex_management("lyr_changes_overlap")
        no_of_records_changes_overlap = int(arcpy.GetCount_management(
            "lyr_changes_overlap").getOutput(0))
        arcpy.SelectLayerByAttribute_management(
            "lyr_changes_xrr_xarea3", "SWITCH_SELECTION")
        arcpy.CopyFeatures_management(
            "lyr_changes_xrr_xarea3", "results.gdb/changes_xrr_xarea3_xoverlap")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/changes_xrr_xarea3_xoverlap", "lyr_changes_xrr_xarea3_xoverlap")
        arcpy.AddSpatialIndex_management("lyr_changes_xrr_xarea3_xoverlap")
        no_of_records_changes_xrr_xarea3_xoverlap = int(arcpy.GetCount_management(
            "lyr_changes_xrr_xarea3_xoverlap").getOutput(0))

        log(
            "\t Step 2 completed successfully.")
        log("\t Step 3 - Preparing Outputs.")

        # delete intermetiate files and prepare output files and give them meaningful names
        log("\t ...Deleting intermediary files")
        arcpy.Delete_management("results.gdb/changes_formated")
        arcpy.Delete_management("results.gdb/changes_unformated")
        arcpy.Delete_management("results.gdb/changes_xrr")
        arcpy.Delete_management("results.gdb/changes_xrr_xarea3")
        arcpy.Delete_management("results.gdb/existing_dataset")
        arcpy.Delete_management("results.gdb/update_dataset")

        log("\t Step 3 completed successfully.")

        log("\t Process completed successfully! \n \n{} changes were found and are summarised as follows:".format(
            no_of_records))

        if no_of_records_changes_rr == 0:
            arcpy.Delete_management("results.gdb/changes_rr")
        else:
            log("-- {} features intersect with roads and are therefore most likely road reserves, verify whether each of these is indeed a road reserve if so delete them.".format(no_of_records_changes_rr))
            arcpy.Rename_management("results.gdb/changes_rr",
                                    "Changes_roadreserves_{}".format(time.strftime("%Y%m%d", time.gmtime())))

        if no_of_records_changes_xrr_area3 == 0:
            arcpy.Delete_management("results.gdb/changes_xrr_area3")
        else:
            log("-- {} features were found to have areas less than 3 sqrmetres so they are most likely slivers or other errors, verify whether each of these are suppose to be part of the dataset, if not proceede to delete.".format(no_of_records_changes_xrr_area3))
            arcpy.Rename_management("results.gdb/changes_xrr_area3",
                                    "Changes_arealessthan3_{}".format(time.strftime("%Y%m%d", time.gmtime())))

        if no_of_records_changes_overlap == 0:
            arcpy.Delete_management("results.gdb/changes_overlap")
        else:
            log("-- {} features overlap with the Current Master Cadastre and need to be investigated.".format(
                no_of_records_changes_overlap))
            arcpy.Rename_management("results.gdb/changes_overlap",
                                    "Changes_overlap_{}".format(time.strftime("%Y%m%d", time.gmtime())))

        if no_of_records_changes_xrr_xarea3_xoverlap == 0:
            arcpy.Delete_management("results.gdb/changes_xrr_xarea3_xoverlap")
        else:
            log("-- {} features are most likely legitimate changes, proceed with the rest of the checks on these before appending them to the master cadastre".format(
                no_of_records_changes_xrr_xarea3_xoverlap))
            arcpy.Rename_management("results.gdb/changes_xrr_xarea3_xoverlap",
                                    "Changes_{}".format(time.strftime("%Y%m%d", time.gmtime())))

        log("\n \n The following reports were generated: ")
        if identicalLIS:
            log("-- {} features were found with identical LIS Keys. Run the Find Identicals tool to regenerate this report for each of the output datasets and use the OBJECTID to create a relationship between the report and the dataset to locate the identicals and rectify them. ".format(no_of_identical_records_LIS))

        if identicalGeom:
            log("-- {} features were found with identical Geometry. Run the Find Identicals tool to regenerate this report for each of the output datasets and use the OBJECTID to create a relationship between the report and the dataset to locate the identicals and rectify them.".format(no_of_identical_records_geom))

        arcpy.ClearWorkspaceCache_management()
except:
    ramm.handleExcept(logger)
