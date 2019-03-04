# Tool for creating 10m buffers around collection points
# Developed by Bhekani Khumalo

import arcpy
import ramm

arcpy.env.overwriteOutput = True
try:
    # Get inputs
    col_points = arcpy.GetParameterAsText(0)
    boundary = arcpy.GetParameterAsText(1)
    buff_dist = arcpy.GetParameterAsText(2)
    output_location = arcpy.GetParameterAsText(3)
    filename = arcpy.GetParameterAsText(4)

    # Set the workspace
    arcpy.env.workspace = output_location
    logger = ramm.defineLogger(output_location)

    def log(message):
        ramm.showPyMessage(message, logger)

    # Make feature layers from the input datasets
    log("\t - Beginning Process.")
    arcpy.MakeFeatureLayer_management(col_points, "lyr_col_points")

    # Use the boundary dataset to clip the relevant features
    log("\t --- Clipping Features.")
    arcpy.MakeFeatureLayer_management(boundary, "lyr_boundary")
    arcpy.Clip_analysis("lyr_col_points", "lyr_boundary",
                        "col_points_clipped.shp")

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
    buff_dist_wunits = buff_dist + " Meters"
    arcpy.Buffer_analysis("lyr_col_points_clipped",
                          "col_points_buffered.shp", buff_dist_wunits, "FULL", "ROUND", "ALL")

    log("\t --- Deagreggating Buffers")
    arcpy.MultipartToSinglepart_management(
        "col_points_buffered.shp", "col_points_buffered_split.shp")
    no_of_buffers = int(arcpy.GetCount_management(
        "col_points_buffered_split.shp").getOutput(0))

    arcpy.Rename_management(
        "col_points_buffered_split.shp", "{}.shp".format(filename))
    arcpy.Delete_management("col_points_buffered.shp")

    log(
        "\t - Process Complete. {} buffers were created.".format(no_of_buffers))
except Exception as e:
    ramm.handleExcept(logger)
