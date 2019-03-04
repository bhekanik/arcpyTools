# Tool for creating 10m buffers around collection points
# Developed by Bhekani Khumalo

import arcpy
import ramm

arcpy.env.overwriteOutput = True
try:
    # Get inputs
    points_table = arcpy.GetParameterAsText(0)
    x_field = arcpy.GetParameterAsText(1)
    y_field = arcpy.GetParameterAsText(2)
    buffer_dist = arcpy.GetParameterAsText(3)
    boundary = arcpy.GetParameterAsText(4)
    output_location = arcpy.GetParameterAsText(5)
    filename = arcpy.GetParameterAsText(6)

    # Set the workspace
    arcpy.env.workspace = output_location
    logger = ramm.defineLogger(output_location)

    def log(message):
        ramm.showPyMessage(message, logger)

    # convert table to points layer
    log("\t - Beginning Process.")
    arcpy.MakeXYEventLayer_management(
        points_table, x_field, y_field, "lyr_col_points")
    arcpy.CopyFeatures_management("lyr_col_points", "points.shp")
    arcpy.MakeFeatureLayer_management("points.shp", "lyr_points")
    #arcpy.XYTableToPoint_management(points_table, "col_points.shp", x_field, y_field)

    # Use the boundary dataset to clip the relevant features
    log("\t --- Clipping Features.")
    arcpy.MakeFeatureLayer_management(boundary, "lyr_boundary")
    arcpy.Clip_analysis("lyr_points", "lyr_boundary", "col_points_clipped.shp")

    # Repair the geometry
    log("\t --- Repairing Geometry.")
    arcpy.MakeFeatureLayer_management(
        "col_points_clipped.shp", "lyr_col_points_clipped")
    arcpy.CheckGeometry_management(
        "lyr_col_points_clipped", "geomErrorReport.dbf")
    no_of_errors = int(arcpy.GetCount_management(
        "geomErrorReport.dbf").getOutput(0))
    arcpy.RepairGeometry_management("lyr_col_points_clipped")
    log(
        "\t ----- {} geometry errors were found and repaired. Check geomErrorReport.dbf for details.".format(no_of_errors))

    # Create Buffers
    log("\t --- Creating Buffers")
    buffer_dist_wunits = buffer_dist + " Meters"
    arcpy.Buffer_analysis("lyr_col_points_clipped", "col_points_buffered.shp",
                          buffer_dist_wunits, "FULL", "ROUND", "ALL")

    log("\t --- Deagreggating Buffers")
    arcpy.MultipartToSinglepart_management(
        "col_points_buffered.shp", "col_points_buffered_split.shp")
    no_of_buffers = int(arcpy.GetCount_management(
        "col_points_buffered_split.shp").getOutput(0))

    arcpy.Rename_management("col_points_buffered_split.shp",
                            "{}.shp".format(filename))
    arcpy.Delete_management("col_points_buffered.shp")

    log(
        "\t - Process Complete. {} buffers were created.".format(no_of_buffers))
except Exception as e:
    ramm.handleExcept(logger)
