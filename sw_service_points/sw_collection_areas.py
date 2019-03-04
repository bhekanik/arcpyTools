import arcpy
import logging

arcpy.env.overwriteOutput = True

# Get inputs
col_points = arcpy.GetParameterAsText(0)
grid = arcpy.GetParameterAsText(1)
output_location = arcpy.GetParameterAsText(2)

logger = ramm.defineLogger(output_location)


def log(message):
    ramm.showPyMessage(message, logger)


# Set the workspace
arcpy.env.workspace = output_location


# Make feature layers from the input datasets
log("\t --- Beginning Process")
arcpy.MakeFeatureLayer_management(col_points, "lyr_col_points")
arcpy.MakeFeatureLayer_management(grid, "lyr_grid")

search_cursor = arcpy.SearchCursor("lyr_grid")
for row in search_cursor:
    arcpy.SelectLayerByAttribute_management("lyr_grid", "NEW_SELECTION",
                                            "\"FID\" = " + str(row.getValue("FID")))
    arcpy.SelectLayerByLocation_management("lyr_col_points", "INTERSECT", "lyr_grid", "",
                                           "NEW_SELECTION")
    arcpy.CopyFeatures_management("lyr_col_points", "points_grid.shp")

    arcpy.MakeFeatureLayer_management("points_grid.shp", "lyr_pointsGrid")

    arcpy.Buffer_analysis("lyr_pointsGrid", "points_grid_buffered.shp",
                          "10 Meters", "FULL", "ROUND", "ALL")

    arcpy.MultipartToSinglepart_management(
        "points_grid_buffered.shp", "points_grid_buffered_Split.shp")

    arcpy.AddField_management("points_grid_buffered_Split.shp", "SPID", "LONG")

    arcpy.Rename_management("points_grid_buffered_Split.shp",
                            "PointsFromGrid_FID{}.shp".format(str(row.getValue("FID"))))

    log(
        "\t --- Completed Grid FID = {}".format(str(row.getValue("FID"))))

del search_cursor

log("\t --- Process Complete")
