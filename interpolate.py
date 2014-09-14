import os
import numpy as np
import random
from osgeo import osr, gdal
import math
import csv

rows = []


# Set file vars
output_file = "out.tif"


input_file = "../allentown_heatmap_spreadsheet.csv"
#input_file = "../south-side_20140913.csv"

max_lon = -180
min_lon =  180

max_lat = 0
min_lat = 90

sq_size = 5
deg_per_block = 0.0001

with open(input_file) as csv_file:
    csvfr = csv.DictReader(csv_file)
    for row in csvfr:
        lat = row['Lat'] = float(row['Lat'])
        lon = row['Lon'] = float(row['Lon'])
        row['Strength'] = float(row['Strength'])

        if lat < min_lat: min_lat = lat
        if lat > max_lat: max_lat = lat
        if lon < min_lon: min_lon = lon
        if lon > max_lon: max_lon = lon

        rows.append(row)

extra_size = ((5+sq_size) * deg_per_block)

min_lat -= extra_size
max_lat += extra_size

min_lon -= extra_size
max_lon += extra_size

# Compute the image size in blocks
lon_size = int((max_lon - min_lon) / deg_per_block)
lat_size = int((max_lat - min_lat) / deg_per_block) 

def decay(x):
    return math.pow(0.75, x)

def x(lon):
    return int((lon - min_lon)/deg_per_block)
def y(lat):
    return int((lat - min_lat)/deg_per_block)



processed = {}
cntr = {}
for row in rows:
    lon = x(float(row['Lon']))
    lat = y(float(row['Lat']))

    idx = (lon,lat)

    if idx not in processed:
        processed[idx] = 0
        cntr[idx] = 0

    # Average all readings that belong in this cell
    n = ((cntr[idx] * processed[idx]) + row['Strength']) / (1 + cntr[idx]);
    processed[idx] = n
    cntr[idx] += 1


# So why are we using lat, lon for matrix indecis?
# Good question
# In a matrix, the first index refers to rows; the second to the column
# i.e rows get bigger as you move "down" them 
#     and columns get bigger as you move "across" them
# as such, they are interpreted as y-coordinates and then x-coordinates

cntr = np.zeros( (lat_size, lon_size) ) 
raster = np.zeros( (lat_size, lon_size) ) 
cnt = 0
for lon,lat in processed:
    cnt += 1
    if cnt % 150 == 0: print cnt

    # Loop through the quare size around the reading and add the reading's
    # decay values to the raster

    for j in range(max(lat-sq_size,0), min(lat+sq_size, lat_size-1)):
        for i in range(max(lon-sq_size,0), min(lon+sq_size, lon_size-1)):
            r = math.hypot(j-lat, i-lon)
            v = decay(r) * processed[(lon,lat)]

            # Computes the running average for the current value of the cell
            n = ((cntr[j,i]*raster[j,i]) + v) / (1 + cntr[j,i])
            raster[j,i] = n
            cntr[j,i] += 1

# Normalize valus from 0 to 255
max_val = raster.max()
raster /=  max_val
raster *=  255

# Create gtif
driver = gdal.GetDriverByName("GTiff")
dst_ds = driver.Create(output_file, lon_size, lat_size, 1, gdal.GDT_Byte )

# Don't ask, I don't know why the order is like this
# top left x, w-e pixel resolution, rotation, 
# top left y, rotation, n-s pixel resolution
dst_ds.SetGeoTransform([ min_lon, deg_per_block, 0, 
                         min_lat, 0, deg_per_block])
  
# set the reference info 
srs = osr.SpatialReference()
srs.SetWellKnownGeogCS("WGS84")
dst_ds.SetProjection( srs.ExportToWkt() )

# write the band
dst_ds.GetRasterBand(1).WriteArray(raster)
