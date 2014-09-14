import os
import numpy as np
import random
from osgeo import osr, gdal
import math
import csv
import argparse


parser = argparse.ArgumentParser(description="converts Lat/Lon, values." + 
                                 "to a heatmap")
parser.add_argument("-i", "--in-file", dest="input_file",
    help="Gets data from FILE", metavar="FILE")
parser.add_argument("-o", "--out-file", dest="output_file",
    help="write image to FILE", metavar="FILE")
parser.add_argument("-r", "--radius", dest="radius", type=int,
    help="Radius to bleed over", metavar="RADIUS", default=5)
parser.add_argument("-d", "--decay", dest="decay", type=float,
    help="Exponent for the decay function. If not specified will be " +
         "generated basd on the radius", metavar="DECAY")
parser.add_argument("-p", "--degrees-per-pixel", dest="dpp", type=float,
    help="Resolution of the image in degrees per pixes" + 
         "If not specified will be generated based on radius", 
    metavar="DEGPERPIX")


options = parser.parse_args()

print options

if options.input_file is None:
    parser.print_help()
    parser.error("input file is required")
if options.output_file is None:
    parser.print_help()
    parser.error("output file is required")

rows = []


max_lon = -180
min_lon =  180

max_lat = 0
min_lat = 90


with open(options.input_file) as csv_file:
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

sq_size = options.radius

deg_per_block = options.dpp
if deg_per_block is None:
    deg_per_block = 0.0001 * 5 / sq_size

decay_factor = options.decay
if decay_factor is None:
    decay_factor = math.exp( math.log(0.75) * 5. / float(sq_size))

extra_size = ((5+sq_size) * deg_per_block)

min_lat -= extra_size
max_lat += extra_size

min_lon -= extra_size
max_lon += extra_size

# Compute the image size in blocks
lon_size = int((max_lon - min_lon) / deg_per_block)
lat_size = int((max_lat - min_lat) / deg_per_block) 


def decay(x):
    return math.pow(decay_factor, x)

def x(lon):
    return int((lon - min_lon)/deg_per_block)
def y(lat):
    return int((lat - min_lat)/deg_per_block)



# Groups all the readings into their cell on the map
# This is done for 2 reasons:
#  1. Cuts down on the number of runs needed during the more expensive
#     part of the program
#  2. Helps combat oversampling by averaging the readings taken near each
#     other
# It's placed into an array instead of a raster matrix because the number
# of readings is much less than the number of pixels
processed = {}
cntr = {}
for row in rows:
    lon = x(float(row['Lon']))
    lat = y(float(row['Lat']))

    idx = (lon,lat)

    if idx not in processed:
        processed[idx] = 0
        cntr[idx] = 0

    # Running average of all readings that belong in this cell
    n = ((cntr[idx] * processed[idx]) + row['Strength']) / (1 + cntr[idx])
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
dst_ds = driver.Create(options.output_file, lon_size, lat_size, 1, gdal.GDT_Byte )

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
