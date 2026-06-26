hill = os.path.join(root_output_folder, "hillshading.tif")
aspect = os.path.join(root_output_folder, "aspect.tif")
slope = os.path.join(root_output_folder, "slope.tif")

pcs_array = gt.generate_img(
    pcs,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Elevation Data for TN @ 1 Arc-Second/30m Resolution",
    zunit="Meter",
    xyunit="Degree",
    ztype="Elevation",
    crop_shp=True,
)
aspect_array = gt.generate_img(
    aspect,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Aspect Data for Rhode TN @ 1 Arc-Second/30m Resolution",
    zunit="Degree",
    xyunit="Degree",
    ztype="Aspect",
    crop_shp=True,
)
hill_array = gt.generate_img(
    hill,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Hillshading Data for TN @ 1 Arc-Second/30m Resolution",
    zunit="Level",
    xyunit="Degree",
    ztype="Hillshading",
    crop_shp=True,
)
slope_array = gt.generate_img(
    slope,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Slope Data for TN @ 1 Arc-Second/30m Resolution",
    zunit="Degree",
    xyunit="Degree",
    ztype="Slope",
    crop_shp=True,
)
hill = os.path.join("./Materials/files/tif_files/", "hillshading.tif")
pcs = os.path.join("./Materials/files/tif_files/", "elevation.tif")
aspect = os.path.join("./Materials/files/tif_files/", "aspect.tif")
slope = os.path.join("./Materials/files/tif_files/", "slope.tif")
pcs_array = gt.generate_img(
    pcs,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Elevation Data for TN @ 1 Arc-Second/30m Resolution",
    zunit="Meter",
    xyunit="Degree",
    ztype="Elevation",
    crop_shp=True,
)
hill_array = gt.generate_img(
    hill,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Hillshading Data for TN @ 1 Arc-Second/30m Resolution",
    zunit="Level",
    xyunit="Degree",
    ztype="Hillshading",
    crop_shp=True,
)
aspect_array = gt.generate_img(
    aspect,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Aspect Data for Rhode TN @ 1 Arc-Second/30m Resolution",
    zunit="Degree",
    xyunit="Degree",
    ztype="Aspect",
    crop_shp=True,
)
slope_array = gt.generate_img(
    slope,
    downsample=5,
    reproject_gcs=True,
    shp_files=shapefile,
    title="Slope Data for TN @ 1 Arc-Second/30m Resolution",
    zunit="Degree",
    xyunit="Degree",
    ztype="Slope",
    crop_shp=True,
)



# Replace endpoint/creds for your gateway
aws s3api head-object --bucket scientistcloud --key utk/conus/10m/CA/aspect.tif --endpoint-url https://us-east-1.gw.future-tech-holdings.com

aws s3 cp s3://scientistcloud/utk/conus/10m/CA/aspect.tif /tmp/test.tif --endpoint-url https://us-east-1.gw.future-tech-holdings.com