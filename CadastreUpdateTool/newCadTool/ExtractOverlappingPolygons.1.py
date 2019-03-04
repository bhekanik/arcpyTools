
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

input_geometries = arcpy.CopyFeatures_management("lyr_existing_cadastre", arcpy.Geometry())

with arcpy.da.SearchCursor("lyr_existing_cadastre", ["OBJECTID"]) as search_cursor:
    for row in search_cursor:
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
            "lyr_existing_cadastre", "INTERSECT", "lyr_row", selection_type="NEW_SELECTION")
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
        "results.gdb/lyr_Overlapping_Polygons")
    log("\t No overlapping features were found")

arcpy.Delete_management(
    "results.gdb/row")





arcpy.CreateFeatureclass_management("results.gdb", "Overlapping_Polygons", "POLYGON", "lyr_existing_cadastre", "DISABLED", "DISABLED", arcpy.Describe("lyr_existing_cadastre").spatialReference)
arcpy.MakeFeatureLayer_management("results.gdb/Overlapping_Polygons", "lyr_Overlapping_Polygons")
arcpy.CreateFeatureclass_management("results.gdb", "Remaining_Polygons", "POLYGON", "lyr_existing_cadastre", "DISABLED", "DISABLED", arcpy.Describe("lyr_existing_cadastre").spatialReference)
arcpy.MakeFeatureLayer_management("results.gdb/Remaining_Polygons", "lyr_Remaining_Polygons")
arcpy.CreateFeatureclass_management("in_memory", "row", "POLYGON", "lyr_existing_cadastre", "DISABLED", "DISABLED", arcpy.Describe("lyr_existing_cadastre").spatialReference)
arcpy.MakeFeatureLayer_management("row", "lyr_row")

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