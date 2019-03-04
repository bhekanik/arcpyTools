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

arcpy.CreateFeatureclass_management("Extract_Overlapping_Polygons_Results.gdb", "Overlapping_Polygons", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.CreateFeatureclass_management("Extract_Overlapping_Polygons_Results.gdb", "row", "POLYGON", "lyr_input_data",
                                    "DISABLED", "DISABLED", arcpy.Describe("lyr_input_data").spatialReference)
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/Overlapping_Polygons", "lyr_Overlapping_Polygons")
arcpy.MakeFeatureLayer_management(
    "Extract_Overlapping_Polygons_Results.gdb/row", "lyr_row")

log("\t Extracting overlapping polygons")
with arcpy.da.SearchCursor("lyr_input_data", ["OBJECTID"]) as search_cursor:
    for row in search_cursor:
        log("\t {}".format(row[0]))
        # Get the OBJECTID of row and use it to select row
        arcpy.SelectLayerByAttribute_management("lyr_input_data", "NEW_SELECTION",
                                                "\"OBJECTID\" = " + str(row[0]))

        # Copy row into a new feature class called row
        arcpy.Append_management(
            "lyr_input_data", "lyr_row", "NO_TEST")

        # Remove row from the input
        arcpy.DeleteFeatures_management("lyr_input_data")

        # Select all features that intersect with row and copy them into the row feature class
        arcpy.SelectLayerByLocation_management(
            "lyr_input_data", "INTERSECT", "lyr_row", selection_type="NEW_SELECTION")
        arcpy.Append_management(
            "lyr_input_data", "lyr_row", "NO_TEST")

        # If there is more than one feature in the row feature class
        # meaning there was something else in addition to row then delete those overlaps
        # from the input and append everything in row into the output feature class
        if (int(arcpy.GetCount_management("lyr_row").getOutput(0)) > 1):
            arcpy.DeleteFeatures_management("lyr_input_data")
            arcpy.Append_management(
                "lyr_row", "lyr_Overlapping_Polygons", "NO_TEST")
        else:
            arcpy.Append_management(
                "lyr_row", "lyr_Remaining_Polygons", "NO_TEST")

        arcpy.SelectLayerByAttribute_management(
            "lyr_input_data", "CLEAR_SELECTION")
        arcpy.TruncateTable_management("lyr_row")
del search_cursor

# Count the number of features in the overlapping polygons feature class and report
overlapping_polygons_num = int(arcpy.GetCount_management(
    "lyr_Overlapping_Polygons").getOutput(0))

if (overlapping_polygons_num > 0):
    log("\t Found {} features that overlap with other features.".format(
        overlapping_polygons_num))
else:
    arcpy.Delete_management(
        "Extract_Overlapping_Polygons_Results.gdb/lyr_Overlapping_Polygons")
    log("\t No overlapping features were found")

arcpy.Delete_management(
    "Extract_Overlapping_Polygons_Results.gdb/input_data")
arcpy.Delete_management(
    "Extract_Overlapping_Polygons_Results.gdb/row")

log("\t Process Complete")
