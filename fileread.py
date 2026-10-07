import rasterio

path = "Nairobi_Data/nairobi_pluvial_proxy_common.tif"
with rasterio.open(path) as src:
    band = src.read(1)          # 2D array, values 0–1
    print(src.width, src.height, src.crs)
    print(band.min(), band.max())