import numpy, os
import random
from osgeo import osr, gdal
import math
import csv

rows = []

with open("allentown_heatmap_spreadsheet.csv") as csv_file:
    csvfr = csv.DictReader(csv_file)
    for row in csvfr:
        rows.append(row)

# Set file vars
output_file = "out.tif"

# Create gtif
driver = gdal.GetDriverByName("GTiff")

max_lon = -79.96990
max_lat = 40.43235

min_lon = -80.00625
min_lat = 40.40250

res = 0.001

x_size = int((max_lon - min_lon) / res)
y_size = int((max_lon - min_lon) / res) 
dst_ds = driver.Create(output_file, x_size, y_size, 1, gdal.GDT_Byte )
raster = numpy.zeros( (x_size, y_size) ) 

def dist(x1,y1,x2,y2):
    return math.sqrt(pow(x2-x1,2) + pow(y2-y1,2))

def sum_sqr_dist(x,y):
    ttl = 0
    for row in rows:
        ttl += dist(x,y, float(row['Lat']), float(row['Lon']))
    return ttl

def x(i):
    return min_lat + (i * res)

def y(i):
    return min_lon + (i * res)

for i in range(x_size):
    for j in range(y_size):
        p = ((1+i)*(1+j))/(x_size*y_size)
        print ((i*y_size) + j),(x_size*y_size)
        print p
        print i,j

        ttl = sum_sqr_dist(x(i),y(j))
        for row in rows:
            d = dist(x(i),y(j), float(row['Lat']), float(row['Lon']))
            t = (1 - (d/ttl) ) * (1/pow(math.log(d),2)) * int(row['Strength'])
            raster[i,j] += (1 - (d/ttl) ) * (1/pow(math.log(d),2)) * int(row['Strength'])
        print raster[i,j]
print raster

max_val = raster.max()
for i in range(x_size):
    for j in range(y_size):
        raster[i,j] = 255 * raster[i,j]/max_val

print raster

# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
dst_ds.SetGeoTransform( [ min_lon, res, 0, min_lat, 0, res ] )
  
# set the reference info 
srs = osr.SpatialReference()
srs.SetWellKnownGeogCS("WGS84")
dst_ds.SetProjection( srs.ExportToWkt() )

# write the band
dst_ds.GetRasterBand(1).WriteArray(raster)
