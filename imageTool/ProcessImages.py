# """-----------------------------------------------------------------------------
#  Script Name:      Process Images
#  Description:      This tool will process the images for the mapsets by
#                    performing the following steps:
#                        1. Mosaic to new raster
#                        2. Resample from 8cm pixels to 16cm pixels
#                        3. Reproject them to WGS84
#  Created By:       Bhekani Khumalo
#  Date:             2018-06-29
#  Last Revision:    2018-09-12
# -----------------------------------------------------------------------------"""

# Import arcpy module
import arcpy
import time
import ramm
import os

arcpy.env.overwriteOutput = True

try:
    # Load required toolboxes
    # arcpy.ImportToolbox("Model Functions")

    images_folder = arcpy.GetParameterAsText(0)
    source_projection = arcpy.GetParameterAsText(1)
    output_projection = arcpy.GetParameterAsText(2)
    mosaic_location = arcpy.GetParameterAsText(3)
    output_location = arcpy.GetParameterAsText(4)

    arcpy.env.workspace = images_folder
    logger = ramm.defineLogger(output_location)

    def log(message):
        ramm.showPyMessage(message, logger)

    for_mosaic1 = arcpy.ListRasters()

    log("Step 1: Mosaic To New Raster")
    for x in for_mosaic1:
        log("--- " + x)
        arcpy.MosaicToNewRaster_management(x, mosaic_location, os.path.basename(x).rstrip(os.path.splitext(
            x)[1]) + ".tif", source_projection, "8_BIT_UNSIGNED", "", "3", "LAST", "FIRST")
        arcpy.AddMessage("-- done.")

    arcpy.env.workspace = mosaic_location

    for_resample = arcpy.ListRasters()

    log("Step 2: Resampling ")
    for x in for_resample:
        log("--- " + x)
        arcpy.Resample_management(
            x, os.path.basename(x).rstrip(os.path.splitext(
                x)[1]) + "_16cm.tif", "0.16 0.16", "NEAREST")
        arcpy.Delete_management(x)
        arcpy.AddMessage("-- done.")

    arcpy.env.workspace = mosaic_location

    for_mosaic2 = arcpy.ListRasters()

    log("Step 3: Project to WGS84 ")
    for x in for_mosaic2:
        log("--- " + x)
        # arcpy.ProjectRaster_management(x, os.path.basename(x).rstrip(os.path.splitext(
        #     x)[1]) + "_wgs84.tif", output_projection, "", "", "Hartebeesthoek94_To_WGS_1984", "", source_projection)
        arcpy.MosaicToNewRaster_management(x, output_location, os.path.basename(x).rstrip(os.path.splitext(
            x)[1]) + "_wgs84.tif", output_projection, "8_BIT_UNSIGNED", "", "3", "LAST", "FIRST")
        arcpy.AddMessage("-- done.")

    log("Image Processing Completed Successfully.")

except:
    ramm.handleExcept(logger)
