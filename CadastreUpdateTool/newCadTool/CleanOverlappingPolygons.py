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
    output_location, "Extract_Overlapping_Polygons_Results.gdb")
arcpy.MakeFeatureLayer_management(input_data, "input_data")
arcpy.FeatureClassToGeodatabase_conversion(
    ["input_data"], "Extract_Overlapping_Polygons_Results.gdb")
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/input_data", "lyr_input_data")

arcpy.CreateFeatureclass_management("Extract_Overlapping_Polygons_Results.gdb", "Remaining_Polygons", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/Overlapping_Polygons", "lyr_Remaining_Polygons")

arcpy.CreateFeatureclass_management("Extract_Overlapping_Polygons_Results.gdb", "row", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/row", "lyr_row")

arcpy.CreateFeatureclass_management("Extract_Overlapping_Polygons_Results.gdb", "parent", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/parent", "lyr_parent")
arcpy.CreateFeatureclass_management("Extract_Overlapping_Polygons_Results.gdb", "children", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/children", "lyr_children")

arcpy.AddSpatialIndex_management("lyr_input_data")

log("\t Cleaning overlapping polygons")
with arcpy.da.SearchCursor("lyr_input_data", ["OBJECTID", "FEAT_SEQ", "SL_LAND_PR", "Total_BillCount", "LU_LGL_STS"]) as search_cursor:
    for row in search_cursor:
        log("\t {}".format(row[0]))
        # Get the OBJECTID of row and use it to select row
        arcpy.SelectLayerByAttribute_management("lyr_input_data", "NEW_SELECTION",
                                                "\"OBJECTID\" = " + str(row[0]))

        # Copy row into a new feature class called row
        arcpy.Append_management(
            "lyr_input_data", "lyr_parent", "NO_TEST")

        # Remove row from the input
        arcpy.DeleteFeatures_management("lyr_input_data")

        # Select all features that intersect with row and copy them into the row feature class
        arcpy.SelectLayerByLocation_management(
            "lyr_input_data", "COMPLETELY_WITHIN", "lyr_row", selection_type="NEW_SELECTION")
        arcpy.Append_management(
            "lyr_input_data", "lyr_children", "NO_TEST")

        # If there is more than one feature in the row feature class
        # meaning there was something else in addition to row then delete those overlaps
        # from the input and append everything in row into the output feature class
        if (int(arcpy.GetCount_management("lyr_children").getOutput(0)) > 0):
            arcpy.DeleteFeatures_management("lyr_input_data")

            # Check if the billings in the children are all the same
            arcpy.FindIdentical_management("lyr_children", "results.gdb/Identical_billings_Report",
                                           ["Total_BillCount"], "", "0", "ONLY_DUPLICATES")

            if (int(arcpy.GetCount_management("lyr_children").getOutput(0)) != int(arcpy.GetCount_management("results.gdb/Identical_billings_Report").getOutput(0))):

            arcpy.Append_management(
                "lyr_row", "lyr_Remaining_Polygons", "NO_TEST")

        else:
            arcpy.Append_management(
                "lyr_parent", "lyr_Remaining_Polygons", "NO_TEST")

        arcpy.TruncateTable_management("lyr_parent")
        arcpy.TruncateTable_management("lyr_children")
del search_cursor

# Count the number of features in the overlapping polygons feature class and report
overlapping_polygons_num = int(arcpy.GetCount_management(
    "lyr_Remaining_Polygons").getOutput(0))

if (overlapping_polygons_num > 0):
    log("\t Found {} features that overlap with other features.".format(
        overlapping_polygons_num))
else:
    arcpy.Delete_management(
        "Extract_Overlapping_Polygons_Results.gdb/Remaining_Polygons")
    log("\t No overlapping features were found")

arcpy.Delete_management(
    "Extract_Overlapping_Polygons_Results.gdb/input_data")
arcpy.Delete_management(
    "Extract_Overlapping_Polygons_Results.gdb/row")

log("\t Process Complete")
