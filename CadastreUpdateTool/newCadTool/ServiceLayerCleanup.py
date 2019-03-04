""" -----------------------------------------------------------------------------
Tool Name:          Service Layer Cleanup
Version:            1.0
Description:        Tool used to clean up the cadastre in order to create a service
                    layer.
Author:             Bhekani Khumalo
Date:               2019-01-15
Last Revision:      2019-01-28
------------------------------------------------------------------------------ """

import arcpy
import time
import ramm

try:
    # Get inputs
    existing_cadastre = arcpy.GetParameterAsText(0)
    billing_data = arcpy.GetParameterAsText(1)
    roads = arcpy.GetParameterAsText(2)
    output_location = arcpy.GetParameterAsText(3)

    # Prepare environment
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = output_location
    arcpy.env.parallelProcessingFactor = "100%"

    # initialize logger
    logger = ramm.defineLogger(output_location)

    # Simplify message generator

    def log(message, messageType="Message"):
        ramm.showPyMessage(message, logger, messageType)

    log("\n \t \t \t Starting Process")
    log("\n \n \t \t Step 1 - Preparing the inputs")

    # Generating intemediary datasets
    log("\t Creating the results geodatabase")
    arcpy.CreateFileGDB_management(output_location, "results.gdb")

    # Add inputs into the geodatabase
    log("\t Adding inputs into the geodatabase")
    arcpy.MakeFeatureLayer_management(existing_cadastre,
                                      "existing_cadastre_mp")
    arcpy.MakeFeatureLayer_management(roads,
                                      "roads")
    arcpy.FeatureClassToGeodatabase_conversion(
        ["existing_cadastre_mp", "roads"], "results.gdb")
    arcpy.MultipartToSinglepart_management(
        "results.gdb/existing_cadastre_mp", "results.gdb/existing_cadastre_sp")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/existing_cadastre_sp", "lyr_existing_cadastre")
    arcpy.MakeFeatureLayer_management("results.gdb/roads", "lyr_roads")
    arcpy.AddSpatialIndex_management("lyr_existing_cadastre")
    arcpy.AddSpatialIndex_management("lyr_roads")
    arcpy.AddIndex_management("lyr_existing_cadastre",
                              "SL_LAND_PR", "UlKIndex", "UNIQUE")

    # Count the number of records in the new dataset
    no_existing_cadastre = int(arcpy.GetCount_management(
        "lyr_existing_cadastre").getOutput(0))
    log("\t Input cadastral dataset has {} records".format(
        no_existing_cadastre), "Warning")

    # Join the cadastre to the billing using the LISKEY field
    log("\t Joining the cadastre and billing datasets")
    arcpy.CopyRows_management(billing_data, "results.gdb/billing_data")
    arcpy.JoinField_management(
        "lyr_existing_cadastre", "SL_LAND_PR", "results.gdb/billing_data", "LISKEY", ["Total_BillCount"])

    log("\n \n \t \t Step 2 - Repairing Geometry")

    # Check and repair geometry errors if found
    arcpy.CheckGeometry_management(
        "lyr_existing_cadastre", "results.gdb/Geometry_Errors_Report")
    geometry_errors_num = int(arcpy.GetCount_management(
        "results.gdb/Geometry_Errors_Report").getOutput(0))
    if geometry_errors_num == 0:
        arcpy.Delete_management("results.gdb/Geometry_Errors_Report")
        log("\t ---No geometry errors were found")
    else:
        arcpy.RepairGeometry_management("lyr_existing_cadastre")
        log("\t ---{} geometry errors were found and repaired. See Geometry_Errors_Report for more information".format(
            geometry_errors_num), "Warning")

    log("\n \n \t \t Step 3 - Removing Road Reserves")

    # remove all the polygons that intersect with roads and being billed
    arcpy.SelectLayerByLocation_management(
        "lyr_existing_cadastre", "INTERSECT", "lyr_roads", selection_type="NEW_SELECTION")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/Road_Reserves_Intermediate")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Road_Reserves_Intermediate", "lyr_road_reserves")
    arcpy.AddSpatialIndex_management("lyr_road_reserves")
    arcpy.SelectLayerByAttribute_management(
        "lyr_road_reserves", "NEW_SELECTION", "\"Total_BillCount\" IS NULL")
    arcpy.DeleteFeatures_management("lyr_road_reserves")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")
    arcpy.Append_management("lyr_road_reserves", "lyr_existing_cadastre")
    arcpy.Delete_management("results.gdb/Road_Reserves_Intermediate")

    log("\n \n \t \t Step 4 - Removing Sliver Polygons")

    # remove from the feature layer the features where the Area < 15
    arcpy.AddField_management("lyr_existing_cadastre", "AREA", "DOUBLE")
    arcpy.CalculateField_management(
        "lyr_existing_cadastre", 'AREA', "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3")
    arcpy.AddIndex_management("lyr_existing_cadastre", "AREA", "aIndex")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "\"AREA\" < 15")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/Sliver_Polygons_Intermediate")
    arcpy.AddSpatialIndex_management(
        "results.gdb/Sliver_Polygons_Intermediate")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Sliver_Polygons_Intermediate", "lyr_small_area")
    arcpy.SelectLayerByAttribute_management(
        "lyr_small_area", "NEW_SELECTION", "\"Total_BillCount\" IS NULL")
    arcpy.DeleteFeatures_management("lyr_small_area")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")
    arcpy.Append_management("lyr_small_area", "lyr_existing_cadastre")
    arcpy.Delete_management("results.gdb/Sliver_Polygons_Intermediate")

    log("\n \n \t \t Step 5 - Cleaning based on Vested Description")

    # Remove from the feature layer the features where the VSTD_DECS is Substation, Waterway, Railway or Unset or Roadway that is also zoned as transport
    log("\t Removing features where Vested Description is Substation, Waterway, Railway or Unset or Roadway that is also zoned as transport")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "\"VSTD_DESC\" = \'Substation\' OR \"VSTD_DESC\" = \'Waterway\' OR \"VSTD_DESC\" = \'Railway\' OR \"VSTD_DESC\" = \'Unset\' OR (\"VSTD_DESC\" = \'Roadway\' AND \"ZONING\" LIKE \'%Transport%\') OR (\"VSTD_DESC\" = \'Roadway\' AND \"ZONING\" = \'\')")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/VD_Delete")
    arcpy.AddSpatialIndex_management("results.gdb/VD_Delete")
    vd_delete_num = int(arcpy.GetCount_management(
        "results.gdb/VD_Delete").getOutput(0))
    if vd_delete_num == 0:
        arcpy.Delete_management("results.gdb/VD_Delete")
        log("\t ---There are no features where Vested Description is Substation, Waterway, Railway or Unset or Roadway that is also zoned as transport")
    else:
        arcpy.Delete_management("results.gdb/VD_Delete")
        log("\t ---Found and deleted {} features where Vested Description is Substation, Waterway, Railway or Unset or Roadway that is also zoned as transport.".format(
            vd_delete_num), "Warning")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")

    log("\n \n \t \t Step 6 - Removing unwanted zonings")

    # Select from the feature layer the features where the zoning doesn't fall in the other categories but has Transport
    log("\t Deleting zoning cases that contain \"Transport\" but don't fall in ZoningCaseA or ZoningCaseB.")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "\"ZONING\" LIKE \'% Transport %\'")
    arcpy.DeleteFeatures_management(
        "lyr_existing_cadastre")
    arcpy.AddSpatialIndex_management("lyr_existing_cadastre")

    log("\n \n \t \t Step 7 - Removing Duplicates")

    # find any records that have the same LISKEY, SG26CODE and geometry
    log("\t Features with identical geometry, LISKEY and SG26 Code")
    arcpy.FindIdentical_management("lyr_existing_cadastre", "results.gdb/Identical_Geometry_LISKEY_And_SG26_Report",
                                   ["SHAPE", "SL_LAND_PR", "SG26_CODE"], "", "0", "ONLY_DUPLICATES")
    identical_records_geomLISSG26_num = int(arcpy.GetCount_management(
        "results.gdb/Identical_Geometry_LISKEY_And_SG26_Report").getOutput(0))
    if identical_records_geomLISSG26_num == 0:
        arcpy.Delete_management(
            "results.gdb/Identical_Geometry_LISKEY_And_SG26_Report")
        log("\t ---There are no features with identical geometry, LISKEY and SG26 Code.")
    else:
        arcpy.Delete_management(
            "results.gdb/Identical_Geometry_LISKEY_And_SG26_Report")
        arcpy.DeleteIdentical_management("lyr_existing_cadastre", [
            "SHAPE", "SL_LAND_PR", "SG26_CODE"], "", "0")
        log("\t ---Found {} features with identical geometry, LISKEY and SG26 Code and deleted duplicates.".format(
            identical_records_geomLISSG26_num))

    # find any records that have the same LISKEY and geometry
    log("\t Features with identical geometry and LISKEY.")
    arcpy.FindIdentical_management("lyr_existing_cadastre", "results.gdb/Identical_Geometry_And_LISKEY_Report", [
        "SHAPE", "SL_LAND_PR"], "", "0", "ONLY_DUPLICATES")
    identical_records_geomLIS_num = int(arcpy.GetCount_management(
        "results.gdb/Identical_Geometry_And_LISKEY_Report").getOutput(0))
    if identical_records_geomLIS_num == 0:
        arcpy.Delete_management(
            "results.gdb/Identical_Geometry_And_LISKEY_Report")
        log("\t ---There are no features with identical geometry and LISKEY.")
    else:
        arcpy.Delete_management(
            "results.gdb/Identical_Geometry_And_LISKEY_Report")
        arcpy.DeleteIdentical_management("lyr_existing_cadastre", [
            "SHAPE", "SL_LAND_PR"], "", "0")
        log("\t ---Found {} features with identical geometry and LISKEY and deleted duplicates.".format(
            identical_records_geomLIS_num))

    # find any records that have the same LISKEY
    log("\t Features with identical LISKEY.")
    arcpy.FindIdentical_management(
        "lyr_existing_cadastre", "results.gdb/Identical_LISKEY_Report", ["SL_LAND_PR"], "", "0", "ONLY_DUPLICATES")
    identical_records_LIS_num = int(arcpy.GetCount_management(
        "results.gdb/Identical_LISKEY_Report").getOutput(0))
    if identical_records_LIS_num == 0:
        arcpy.Delete_management("results.gdb/Identical_LISKEY_Report")
        log("\t ---There are no features with identical LISKEY.")
    else:
        arcpy.JoinField_management("lyr_existing_cadastre", "OBJECTID",
                                   "results.gdb/Identical_LISKEY_Report", "IN_FID", ["IN_FID", "FEAT_SEQ"])
        arcpy.SelectLayerByAttribute_management(
            "lyr_existing_cadastre", "NEW_SELECTION", "\"IN_FID\" IS NOT NULL")
        arcpy.CopyFeatures_management(
            "lyr_existing_cadastre", "results.gdb/Identical_LISKEY")
        arcpy.Delete_management("results.gdb/Identical_LISKEY_Report")
        log("\t ---Found {} features with identical LISKEY that need to be investigated. See Identical_LISKEY for details.".format(
            identical_records_LIS_num), "Warning")
        arcpy.DeleteFeatures_management("lyr_existing_cadastre")
        arcpy.DeleteField_management(
            "lyr_existing_cadastre", ["IN_FID", "FEAT_SEQ"])
        arcpy.MakeFeatureLayer_management(
            "results.gdb/Identical_LISKEY", "lyr_identical_liskey")

    # find any records that have the same geometry
    log("\t Features with identical geometry.")
    arcpy.FindIdentical_management("lyr_existing_cadastre", "results.gdb/Identical_geometry_Report",
                                   ["SHAPE"], "", "0", "ONLY_DUPLICATES")
    identical_records_geom_num = int(arcpy.GetCount_management(
        "results.gdb/Identical_geometry_Report").getOutput(0))
    if identical_records_geom_num == 0:
        arcpy.Delete_management("results.gdb/Identical_geometry_Report")
        log("\t ---There are no features with identical geometry.")
    else:
        arcpy.JoinField_management("lyr_existing_cadastre", "OBJECTID",
                                   "results.gdb/Identical_geometry_Report", "IN_FID", ["IN_FID", "FEAT_SEQ"])
        arcpy.SelectLayerByAttribute_management(
            "lyr_existing_cadastre", "NEW_SELECTION", "\"IN_FID\" IS NOT NULL")
        arcpy.CopyFeatures_management(
            "lyr_existing_cadastre", "results.gdb/Identical_Geometry")
        arcpy.Delete_management("results.gdb/Identical_geometry_Report")
        log("\t ---Found {} features with identical geometry that need to be investigated. See Identical_Geometry for details.".format(
            identical_records_geom_num), "Warning")
        arcpy.DeleteFeatures_management("lyr_existing_cadastre")
        arcpy.DeleteField_management(
            "lyr_existing_cadastre", ["IN_FID", "FEAT_SEQ"])
        arcpy.MakeFeatureLayer_management(
            "results.gdb/Identical_Geometry", "lyr_identical_geometry")

    log("\n \n \t \t Step 8 - Isolating remaining Road Reserves")

    # select all the polygons that intersect with roads and being billed and save them into a new feature class
    arcpy.SelectLayerByLocation_management(
        "lyr_existing_cadastre", "INTERSECT", "lyr_roads", selection_type="NEW_SELECTION")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/Road_Reserves")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Road_Reserves", "lyr_road_reserves")
    arcpy.AddSpatialIndex_management("lyr_road_reserves")
    road_reserves_num = int(arcpy.GetCount_management(
        "lyr_road_reserves").getOutput(0))
    if road_reserves_num == 0:
        arcpy.Delete_management("results.gdb/Road_Reserves")
        log("\t ---No road reserves were found.")
    else:
        log("\t ---Found {} features that are road reserves being billed that need to be investigated. See Road_Reserves for details.".format(
            road_reserves_num), "Warning")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")

    log("\n \n \t \t Step 9 - Isolating remaining Sliver Polygons")

    # select from the feature layer the features where the Area < 4 and save this to a new feature class
    arcpy.CalculateField_management(
        "lyr_existing_cadastre", 'AREA', "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3")
    arcpy.AddIndex_management("lyr_existing_cadastre", "AREA", "aIndex")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "\"AREA\" < 15")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/Sliver_Polygons")
    arcpy.AddSpatialIndex_management("results.gdb/Sliver_Polygons")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Sliver_Polygons", "lyr_small_area")
    sliver_polygons_num = int(arcpy.GetCount_management(
        "lyr_small_area").getOutput(0))
    if sliver_polygons_num == 0:
        arcpy.Delete_management("results.gdb/Sliver_Polygons")
        log("\t ---No sliver polygons were found.")
    else:
        log("\t ---Found {} features that are sliver polygons being billed that need to be investigated. See Sliver_Polygons for details.".format(
            sliver_polygons_num), "Warning")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")

    log("\n \n \t \t Step 10 - Isolating unwanted zonings")

    # Remove from the feature layer the features where the zoning starts with Transport
    log("\t Zoning cases that start with \"Transport\" and is being billed")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "\"ZONING\" LIKE \'Transport%\'")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/Zoning_Case_A")

    if identical_records_LIS_num > 0:
        arcpy.SelectLayerByAttribute_management(
            "lyr_identical_liskey", "NEW_SELECTION", "\"ZONING\" LIKE \'Transport%\'")
        arcpy.CopyFeatures_management(
            "lyr_identical_liskey", "results.gdb/Zoning_Case_A_LISKEY")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/Zoning_Case_A_LISKEY", "lyr_zoning_case_a_liskey")
        arcpy.Append_management(
            "lyr_zoning_case_a_liskey", "results.gdb/Zoning_Case_A", "NO_TEST")
        arcpy.DeleteFeatures_management("lyr_identical_liskey")
        arcpy.Delete_management("lyr_zoning_case_a_liskey")

    if identical_records_geom_num > 0:
        arcpy.SelectLayerByAttribute_management(
            "lyr_identical_geometry", "NEW_SELECTION", "\"ZONING\" LIKE \'Transport%\'")
        arcpy.CopyFeatures_management(
            "lyr_identical_geometry", "results.gdb/Zoning_Case_A_Geometry")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/Zoning_Case_A_Geometry", "lyr_zoning_case_a_geometry")
        arcpy.Append_management(
            "lyr_zoning_case_a_geometry", "results.gdb/Zoning_Case_A", "NO_TEST")
        arcpy.DeleteFeatures_management("lyr_identical_geometry")
        arcpy.Delete_management("lyr_zoning_case_a_geometry")

    arcpy.AddSpatialIndex_management("results.gdb/Zoning_Case_A")
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Zoning_Case_A", "lyr_zoning_case_a")
    arcpy.SelectLayerByAttribute_management(
        "lyr_zoning_case_a", "NEW_SELECTION", "\"Total_BillCount\" IS NULL")
    arcpy.DeleteFeatures_management("lyr_zoning_case_a")
    zoning_case_a_num = int(arcpy.GetCount_management(
        "lyr_zoning_case_a").getOutput(0))
    if zoning_case_a_num == 0:
        arcpy.Delete_management("results.gdb/Zoning_Case_A")
        log("\t ---There are no features that start with \"Transport\" and are being billed")
    else:
        log("\t ---Found {} features that start with \"Transport\" and are being billed. See Zoning_Case_A for more information".format(
            zoning_case_a_num), "Warning")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")

    # Select from the feature layer the features where the zoning contains Transport and any of community, mixed, residential, business, billing>1
    log("\t Zoning cases that contain \"Transport\" and any of Community, Mixed Use, Residential, Business or billing is greater than one.")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "(\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Community%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Mixed%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Residential%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Business%\' AND \"Total_BillCount\" IS NULL)")
    arcpy.CopyFeatures_management(
        "lyr_existing_cadastre", "results.gdb/Zoning_Case_B")

    if identical_records_LIS_num > 0:
        arcpy.SelectLayerByAttribute_management(
            "lyr_identical_liskey", "NEW_SELECTION", "(\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Community%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Mixed%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Residential%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Business%\' AND \"Total_BillCount\" IS NULL)")
        arcpy.CopyFeatures_management(
            "results.gdb/Identical_LISKEY", "results.gdb/Zoning_Case_B_LISKEY")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/Zoning_Case_B_LISKEY", "lyr_zoning_case_b_liskey")
        arcpy.Append_management(
            "lyr_zoning_case_b_liskey", "results.gdb/Zoning_Case_B", "NO_TEST")
        arcpy.DeleteFeatures_management("lyr_identical_liskey")
        arcpy.Delete_management("lyr_zoning_case_b_liskey")

    if identical_records_geom_num > 0:
        arcpy.SelectLayerByAttribute_management(
            "lyr_identical_geometry", "NEW_SELECTION", "(\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Community%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Mixed%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Residential%\' AND \"Total_BillCount\" IS NULL) OR (\"ZONING\" LIKE \'%Transport%\' AND \"ZONING\" LIKE \'%Business%\' AND \"Total_BillCount\" IS NULL)")
        arcpy.CopyFeatures_management(
            "results.gdb/Identical_Geometry", "results.gdb/Zoning_Case_B_Geometry")
        arcpy.MakeFeatureLayer_management(
            "results.gdb/Zoning_Case_B_Geometry", "lyr_zoning_case_b_geometry")
        arcpy.Append_management(
            "lyr_zoning_case_b_geometry", "results.gdb/Zoning_Case_B", "NO_TEST")
        arcpy.DeleteFeatures_management("lyr_identical_geometry")
        arcpy.Delete_management("lyr_zoning_case_b_geometry")

    arcpy.AddSpatialIndex_management("results.gdb/Zoning_Case_B")
    zoning_case_b_num = int(arcpy.GetCount_management(
        "results.gdb/Zoning_Case_B").getOutput(0))
    if zoning_case_b_num == 0:
        arcpy.Delete_management("results.gdb/Zoning_Case_B")
        log("\t ---There are no features that contain \"Transport\" and any of Community, Mixed Use, Residential, Business or billing is greater than one.")
    else:
        log("\t ---Found {} features that contain \"Transport\" and any of Community, Mixed Use, Residential, Business or billing is greater than one. See Zoning_Case_B for more information".format(
            zoning_case_b_num), "Warning")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")

    # Select from the feature layer the features where the zoning contains Transport
    log("\t Zoning cases that contain \"Transport\".")
    arcpy.SelectLayerByAttribute_management(
        "lyr_existing_cadastre", "NEW_SELECTION", "\"ZONING\" LIKE \'%Transport%\'")
    arcpy.DeleteFeatures_management("lyr_existing_cadastre")

    log("\n \n \t \t Step 11 - Cleaning the Identical Geometry layer")

    arcpy.CreateFeatureclass_management("results.gdb", "identical_geometry_output", "POLYGON", "lyr_identical_geometry",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_identical_geometry").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/identical_geometry_output", "lyr_identical_geometry_output")
    arcpy.CreateFeatureclass_management("results.gdb", "identicals_set", "POLYGON", "lyr_identical_geometry",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_identical_geometry").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/identicals_set", "lyr_identicals_set")
    arcpy.CreateFeatureclass_management("results.gdb", "registered", "POLYGON", "lyr_identical_geometry",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_identical_geometry").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/registered", "lyr_registered")
    arcpy.CreateFeatureclass_management("results.gdb", "confirmed", "POLYGON", "lyr_identical_geometry",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_identical_geometry").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/confirmed", "lyr_confirmed")
    arcpy.CreateFeatureclass_management("results.gdb", "sg_approved", "POLYGON", "lyr_identical_geometry",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_identical_geometry").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/sg_approved", "lyr_sg_approved")
    arcpy.CreateFeatureclass_management("results.gdb", "highest_liskey", "POLYGON", "lyr_identical_geometry",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_identical_geometry").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/highest_liskey", "lyr_highest_liskey")

    with arcpy.da.UpdateCursor("lyr_identical_geometry", ["FEAT_SEQ", "SL_LAND_PR", "Total_BillCount", "LU_LGL_STS"]) as update_cursor:
        for row in update_cursor:
            # CHECK BILLING
            # Select all features with a FEAT_SEQ of min_value and save them into a seperate layer
            arcpy.SelectLayerByAttribute_management(
                "lyr_identical_geometry", "NEW_SELECTION", "\"FEAT_SEQ\" = " + str(row[0]))
            arcpy.Append_management(
                "lyr_identical_geometry", "lyr_identicals_set", "NO_TEST")
            arcpy.DeleteFeatures_management("lyr_identical_geometry")
            # Check if all the billings are the same
            arcpy.FindIdentical_management("lyr_identicals_set", "results.gdb/Identical_billings_Report",
                                           ["Total_BillCount"], "", "0", "ONLY_DUPLICATES")
            # If billings are not the same and there is only one feature being billed keep the feature being billed
            if (int(arcpy.GetCount_management("lyr_identicals_set").getOutput(0)) != int(arcpy.GetCount_management("results.gdb/Identical_billings_Report").getOutput(0))):
                arcpy.Delete_management(
                    "results.gdb/Identical_billings_Report")
                arcpy.SelectLayerByAttribute_management(
                    "lyr_identicals_set", "NEW_SELECTION", "\"Total_BillCount\" = 0")
                arcpy.DeleteFeatures_management("lyr_identicals_set")
                if (int(arcpy.GetCount_management("lyr_identicals_set").getOutput(0)) == 1):
                    arcpy.Append_management(
                        "lyr_identicals_set", "lyr_identical_geometry_output", "NO_TEST")
                    arcpy.DeleteFeatures_management("lyr_identicals_set")
                    continue

            # CHECK LEGAL STATUS
            # Check if the features all have the same legal status
            arcpy.FindIdentical_management("lyr_identicals_set", "results.gdb/Identical_lgl_sts_Report",
                                           ["LU_LGL_STS"], "", "0", "ONLY_DUPLICATES")
            # If the legal statuses are not the same then use the haerachy to select the one to keep
            if (int(arcpy.GetCount_management("lyr_identicals_set").getOutput(0)) != int(arcpy.GetCount_management("results.gdb/Identical_lgl_sts_Report").getOutput(0))):
                arcpy.Delete_management(
                    "results.gdb/Identical_lgl_sts_Report")

                # Registered
                arcpy.SelectLayerByAttribute_management(
                    "lyr_identicals_set", "NEW_SELECTION", "\"LU_LGL_STS\" = \'Registered\'")
                arcpy.Append_management(
                    "lyr_identicals_set", "lyr_registered", "NO_TEST")
                registered_num = int(arcpy.GetCount_management(
                    "lyr_registered").getOutput(0))
                if (registered_num == 1):
                    arcpy.Append_management(
                        "lyr_registered", "lyr_identical_geometry_output", "NO_TEST")
                    arcpy.DeleteFeatures_management("lyr_registered")
                    continue
                elif (registered_num == 0):

                    # Confirmed
                    arcpy.SelectLayerByAttribute_management(
                        "lyr_identicals_set", "NEW_SELECTION", "\"LU_LGL_STS\" = \'Confirmed\'")
                    arcpy.Append_management(
                        "lyr_identicals_set", "lyr_confirmed", "NO_TEST")
                    confirmed_num = int(arcpy.GetCount_management(
                        "lyr_confirmed").getOutput(0))
                    if (confirmed_num == 1):
                        arcpy.Append_management(
                            "lyr_confirmed", "lyr_identical_geometry_output", "NO_TEST")
                        arcpy.DeleteFeatures_management(
                            "lyr_confirmed")
                        continue
                    elif (confirmed_num == 0):

                        # SG Approved
                        arcpy.SelectLayerByAttribute_management(
                            "lyr_identicals_set", "NEW_SELECTION", "\"LU_LGL_STS\" = \'SG Approved\'")
                        arcpy.Append_management(
                            "lyr_identicals_set", "lyr_sg_approved", "NO_TEST")
                        sg_approved_num = int(arcpy.GetCount_management(
                            "lyr_sg_approved").getOutput(0))
                        if (sg_approved_num == 1):
                            arcpy.Append_management(
                                "lyr_sg_approved", "lyr_identical_geometry_output", "NO_TEST")
                            arcpy.DeleteFeatures_management(
                                "lyr_sg_approved")
                            continue

            # CHECK LISKEY
            max_value = arcpy.da.SearchCursor("lyr_identicals_set", "SL_LAND_PR", sql_clause=(
                None, "ORDER BY SL_LAND_PR DESC")).next()[0]

            arcpy.SelectLayerByAttribute_management(
                "lyr_identicals_set", "NEW_SELECTION", "\"SL_LAND_PR\" = " + str(max_value))
            arcpy.Append_management(
                "lyr_identicals_set", "lyr_identical_geometry_output", "NO_TEST")
            arcpy.DeleteFeatures_management(
                "lyr_identicals_set")
            arcpy.Delete_management(
                "results.gdb/Identical_billings_Report")
            arcpy.Delete_management(
                "results.gdb/Identical_lgl_sts_Report")
    del update_cursor

    arcpy.Delete_management("results.gdb/identicals_set")
    arcpy.Delete_management("results.gdb/identical_geometry")
    arcpy.Delete_management("results.gdb/registered")
    arcpy.Delete_management("results.gdb/confirmed")
    arcpy.Delete_management("results.gdb/sg_approved")
    arcpy.Delete_management("results.gdb/highest_liskey")
    arcpy.Append_management(
        "lyr_identical_geometry_output", "lyr_existing_cadastre", "NO_TEST")
    arcpy.Delete_management("results.gdb/identical_geometry_output")

    log("\n \n \t \t Step 12 - Isolating Overlapping Polygons")

    arcpy.CreateFeatureclass_management("results.gdb", "Overlapping_Polygons", "POLYGON", "lyr_existing_cadastre",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_existing_cadastre").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Overlapping_Polygons", "lyr_Overlapping_Polygons")
    arcpy.CreateFeatureclass_management("results.gdb", "Remaining_Polygons", "POLYGON", "lyr_existing_cadastre",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_existing_cadastre").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/Remaining_Polygons", "lyr_Remaining_Polygons")
    arcpy.CreateFeatureclass_management("results.gdb", "row", "POLYGON", "lyr_existing_cadastre",
                                        "DISABLED", "DISABLED", arcpy.Describe("lyr_existing_cadastre").spatialReference)
    arcpy.MakeFeatureLayer_management(
        "results.gdb/row", "lyr_row")

    arcpy.AddSpatialIndex_management("lyr_existing_cadastre")

    with arcpy.da.SearchCursor("lyr_existing_cadastre", ["OBJECTID"]) as search_cursor:
        for row in search_cursor:
            log("\t {}".format(row[0]))
            # Get the OBJECTID of row and use it to select row
            arcpy.SelectLayerByAttribute_management("lyr_existing_cadastre", "NEW_SELECTION",
                                                    "\"OBJECTID\" = " + str(row[0]))

            # Copy row into a new feature class called row
            arcpy.Append_management(
                "lyr_existing_cadastre", "lyr_row", "NO_TEST")

            # Remove row from the input
            arcpy.DeleteFeatures_management("lyr_existing_cadastre")

            # Select all features that intersect with row and copy them into the row feature class
            arcpy.SelectLayerByLocation_management(
                "lyr_existing_cadastre", "WITHIN", "lyr_row", selection_type="NEW_SELECTION")
            arcpy.Append_management(
                "lyr_existing_cadastre", "lyr_row", "NO_TEST")

            # If there is more than one feature in the row feature class
            # meaning there was something else in addition to row then delete those overlaps
            # from the input and append everything in row into the output feature class
            if (int(arcpy.GetCount_management("lyr_row").getOutput(0)) > 1):
                arcpy.DeleteFeatures_management("lyr_existing_cadastre")
                arcpy.Append_management(
                    "lyr_row", "lyr_Overlapping_Polygons", "NO_TEST")
            else:
                arcpy.Append_management(
                    "lyr_row", "lyr_Remaining_Polygons", "NO_TEST")

            arcpy.SelectLayerByAttribute_management(
                "lyr_existing_cadastre", "CLEAR_SELECTION")
            arcpy.TruncateTable_management("lyr_row")
    del search_cursor

    # Count the numver of features in the overlapping polygons feature class and report
    overlapping_polygons_num = int(arcpy.GetCount_management(
        "lyr_Overlapping_Polygons").getOutput(0))

    if (overlapping_polygons_num > 0):
        log("\t Found {} features that overlap with other features.".format(
            overlapping_polygons_num))
    else:
        arcpy.Delete_management(
            "results.gdb/Overlapping_Polygons")
        log("\t No overlapping features were found")

    arcpy.Delete_management(
        "results.gdb/row")
    arcpy.Delete_management(
        "results.gdb/existing_cadastre_sp")

    log("\n \n \t \t Step 13 - Final Service layer")

    # count the number of records in final_service_layer
    final_service_layer_num = int(arcpy.GetCount_management(
        "lyr_Remaining_Polygons").getOutput(0))
    if final_service_layer_num == 0:
        arcpy.Delete_management("lyr_Remaining_Polygons")
        log("\t ---No features left.")
    else:
        log("\t ---{} features left after all the steps. See Remaining_Features for details.".format(
            final_service_layer_num), "Warning")

    arcpy.Delete_management("results.gdb/billing_data")
    arcpy.Delete_management("results.gdb/roads")
    arcpy.Delete_management("results.gdb/existing_cadastre_mp")
    arcpy.Delete_management("results.gdb/Zoning_Case_A_Geometry")
    arcpy.Delete_management("results.gdb/Zoning_Case_A_LISKEY")
    arcpy.Delete_management("results.gdb/Zoning_Case_B_Geometry")
    arcpy.Delete_management("results.gdb/Zoning_Case_B_LISKEY")

    log("\n \n \t \t \t Process Complete.")
except:
    ramm.handleExcept(logger)
