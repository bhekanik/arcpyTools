""" -----------------------------------------------------------------------------
Tool Name:          Cadastre Identical Geometries Cleanup
Version:            1.0
Description:        Tool used to clean up the identical geometries layer from the 
                    cadastre layer.
Author:             Bhekani Khumalo
Date:               2019-01-28
Last Revision:      2019-01-28
------------------------------------------------------------------------------ """

import arcpy
import ramm

input_data = arcpy.GetParameterAsText(0)
output_location = arcpy.GetParameterAsText(1)

# Prepare environment
arcpy.env.overwriteOutput = True
arcpy.env.workspace = output_location

# initialize logger
logger = ramm.defineLogger(output_location)

# Simplify message generator


def log(message, messageType="Message"):
    ramm.showPyMessage(message, logger, messageType)


log("\t Starting Process")

log("\t Preparing Intemediates")
arcpy.CreateFileGDB_management(
    output_location, "Clean_Identical_Geometry_Results.gdb")
arcpy.MakeFeatureLayer_management(input_data, "input_data")
arcpy.FeatureClassToGeodatabase_conversion(
    ["input_data"], "Clean_Identical_Geometry_Results.gdb")
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/input_data", "lyr_input_data")

arcpy.CreateFeatureclass_management("Clean_Identical_Geometry_Results.gdb", "output_data", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/output_data", "lyr_output_data")
arcpy.CreateFeatureclass_management("Clean_Identical_Geometry_Results.gdb", "identicals_set", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/identicals_set", "lyr_identicals_set")
arcpy.CreateFeatureclass_management("Clean_Identical_Geometry_Results.gdb", "registered", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/registered", "lyr_registered")
arcpy.CreateFeatureclass_management("Clean_Identical_Geometry_Results.gdb", "confirmed", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/confirmed", "lyr_confirmed")
arcpy.CreateFeatureclass_management("Clean_Identical_Geometry_Results.gdb", "sg_approved", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/sg_approved", "lyr_sg_approved")
arcpy.CreateFeatureclass_management("Clean_Identical_Geometry_Results.gdb", "highest_liskey", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Clean_Identical_Geometry_Results.gdb/highest_liskey", "lyr_highest_liskey")

with arcpy.da.UpdateCursor("lyr_input_data", ["FEAT_SEQ", "SL_LAND_PR", "Total_BillCount", "LU_LGL_STS"]) as update_cursor:
    for row in update_cursor:
        # Get the minimum value in the Feat_Seq field
        # min_value = arcpy.da.SearchCursor("lyr_input_data", "FEAT_SEQ", sql_clause=(
        #     None, "ORDER BY FEAT_SEQ ASC")).next()[0]

        log("\t Checking Billing for feature sequence {}".format(row[0]))
        # CHECK BILLING
        # Select all features with a FEAT_SEQ of min_value and save them into a seperate layer
        arcpy.SelectLayerByAttribute_management(
            "lyr_input_data", "NEW_SELECTION", "\"FEAT_SEQ\" = " + str(row[0]))
        arcpy.Append_management(
            "lyr_input_data", "lyr_identicals_set", "NO_TEST")
        arcpy.DeleteFeatures_management("lyr_input_data")
        # Check if all the billings are the same
        arcpy.FindIdentical_management("lyr_identicals_set", "Clean_Identical_Geometry_Results.gdb/Identical_billings_Report",
                                       ["Total_BillCount"], "", "0", "ONLY_DUPLICATES")
        # If billings are not the same and there is only one feature being billed keep the feature being billed
        if (int(arcpy.GetCount_management("lyr_identicals_set").getOutput(0)) != int(arcpy.GetCount_management("Clean_Identical_Geometry_Results.gdb/Identical_billings_Report").getOutput(0))):
            arcpy.Delete_management(
                "Clean_Identical_Geometry_Results.gdb/Identical_billings_Report")
            arcpy.SelectLayerByAttribute_management(
                "lyr_identicals_set", "NEW_SELECTION", "\"Total_BillCount\" = 0")
            arcpy.DeleteFeatures_management("lyr_identicals_set")
            if (int(arcpy.GetCount_management("lyr_identicals_set").getOutput(0)) == 1):
                arcpy.Append_management(
                    "lyr_identicals_set", "lyr_output_data", "NO_TEST")
                arcpy.DeleteFeatures_management("lyr_identicals_set")
                continue

        log("\t Checking Legal Status for feature sequence {}".format(row[0]))
        # CHECK LEGAL STATUS
        # Check if the features all have the same legal status
        arcpy.FindIdentical_management("lyr_identicals_set", "Clean_Identical_Geometry_Results.gdb/Identical_lgl_sts_Report",
                                       ["LU_LGL_STS"], "", "0", "ONLY_DUPLICATES")
        # If the legal statuses are not the same then use the haerachy to select the one to keep
        if (int(arcpy.GetCount_management("lyr_identicals_set").getOutput(0)) != int(arcpy.GetCount_management("Clean_Identical_Geometry_Results.gdb/Identical_lgl_sts_Report").getOutput(0))):
            arcpy.Delete_management(
                "Clean_Identical_Geometry_Results.gdb/Identical_lgl_sts_Report")

            # Registered
            arcpy.SelectLayerByAttribute_management(
                "lyr_identicals_set", "NEW_SELECTION", "\"LU_LGL_STS\" = \'Registered\'")
            arcpy.Append_management(
                "lyr_identicals_set", "lyr_registered", "NO_TEST")
            registered_num = int(arcpy.GetCount_management(
                "lyr_registered").getOutput(0))
            if (registered_num == 1):
                arcpy.Append_management(
                    "lyr_registered", "lyr_output_data", "NO_TEST")
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
                        "lyr_confirmed", "lyr_output_data", "NO_TEST")
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
                            "lyr_sg_approved", "lyr_output_data", "NO_TEST")
                        arcpy.DeleteFeatures_management(
                            "lyr_sg_approved")
                        continue

        log("\t Checking LISKEY for feature sequence {}".format(row[0]))
        # CHECK LISKEY
        max_value = arcpy.da.SearchCursor("lyr_identicals_set", "SL_LAND_PR", sql_clause=(
            None, "ORDER BY SL_LAND_PR DESC")).next()[0]

        arcpy.SelectLayerByAttribute_management(
            "lyr_identicals_set", "NEW_SELECTION", "\"SL_LAND_PR\" = " + str(max_value))
        arcpy.Append_management(
            "lyr_identicals_set", "lyr_output_data", "NO_TEST")
        arcpy.DeleteFeatures_management(
            "lyr_identicals_set")
del update_cursor

arcpy.Delete_management("Clean_Identical_Geometry_Results.gdb/identicals_set")
arcpy.Delete_management("Clean_Identical_Geometry_Results.gdb/input_data")
arcpy.Delete_management("Clean_Identical_Geometry_Results.gdb/registered")
arcpy.Delete_management("Clean_Identical_Geometry_Results.gdb/confirmed")
arcpy.Delete_management("Clean_Identical_Geometry_Results.gdb/sg_approved")
arcpy.Delete_management("Clean_Identical_Geometry_Results.gdb/highest_liskey")
log("\t Process Complete")
