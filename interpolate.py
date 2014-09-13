import os
import numpy as np
import random
from osgeo import osr, gdal
import math
import csv

import collections
import functools

rows = []


# Set file vars
output_file = "out.tif"

# Create gtif
driver = gdal.GetDriverByName("GTiff")

max_lon = -79.96990
max_lat = 40.430
 
min_lon = -80.00625
min_lat = 40.40250


res = 0.0001

x_size = int((max_lon - min_lon) / res)
y_size = int((max_lon - min_lon) / res) 
dst_ds = driver.Create(output_file, x_size, y_size, 1, gdal.GDT_Byte )
raster = np.zeros( (x_size, y_size) ) 
final_raster = np.zeros( (x_size, y_size) ) 
cntr = np.zeros( (x_size, y_size) ) 


with open("../allentown_heatmap_spreadsheet.csv") as csv_file:
   csvfr = csv.DictReader(csv_file)
   for row in csvfr:
      row['Lat'] = float(row['Lat'])
      row['Lon'] = float(row['Lon'])
      row['Strength'] = 10*float(row['Strength'])

      rows.append(row)

#max_val = sorted([row['Strength'] for i in range(len(rows))])
#max_val = filter(lambda x : x != 0, max_val)
#s = len(max_val)
#max_val = max_val[int(s - (s*0.05))]
#
#for i in xrange(len(rows)):
#   r = rows[i]
#   r['Strength'] = r['Strength'] / max_val
#   rows[i] = r

sigma = 5

m = 1./math.hypot(sigma, sigma)
b = 1

def decay(x):
    return math.pow(0.9, x)
    return (-m*x) + b
    return math.cos(x * m/2. * math.pi / 4)
    return 1 - 1 / (1 + math.exp((x-(sigma/2.))))


def x(lon):
   return int((lon - min_lon)/res)
def y(lat):
   return int((lat - min_lat)/res)


processed = []
cntr = np.zeros( (x_size, y_size) ) 
cnt = 0
for row in rows:
  cnt += 1
  if cnt % 10 == 0: print cnt
  i = x(float(row['Lon']))
  j = y(float(row['Lat']))
  n = ((cntr[j,i] * raster[j,i]) + row['Strength']) / (1 + cntr[j,i]);
  print cntr[j,i], raster[j,i],  row['Strength'], n
  raster[j,i] = n
  cntr[j,i] += 1
  pair = (j,i)
  if pair not in processed: processed.append(pair)

values = []
for pair in processed:
  (j,i) = pair
  values.append(raster[j,i])

values = sorted(values)

print values
ptile = 20
ptiles = []
s = len(values)
for i in range(ptile-1):
   ptiles.append(values[int(s * float(1)/float(ptile) * (i+1))])
print ptiles

for pair in processed:
  (j,i) = pair
  qile = ptile
  for q in range(len(ptiles)):
    if ptiles[q] > raster[j,i]:
      qile = q
      break 
  raster[j,i] = 10 + ((100./ptile)*qile)

cntr = np.zeros( (x_size, y_size) ) 
cnt = 0
for pair in processed:
  cnt += 1
  if cnt % 150 == 0: print cnt
  (rj, ri) = pair
  for i in range(max(ri-sigma,0), min(ri+sigma, x_size-1)):
     for j in range(max(rj-sigma,0), min(rj+sigma, y_size-1)):
         #if i == ri and j == rj: continue
         dx = abs(ri-i)
         dy = abs(rj-j)
         r = math.hypot(dx,dy)
         g = decay(r)
         s = raster[rj,ri]
         v = g * s
         #print dx,dy,r,s,g,v
         #raster[j,i] += v

         #raster[j,i] = max(raster[j,i], v)
         #v = (raster[j,i] + v)/2
         #raster[j,i] = raster[j,i] + v
         final_raster[j,i] = ((cntr[j,i]*final_raster[j,i]) + v) / (1 + cntr[j,i])
         cntr[j,i] += 1

#final_raster += raster

print final_raster.max();

#max_val = final_raster.max()
#final_raster /=  max_val
#final_raster *=  200
#
#print final_raster.max()

# top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution
dst_ds.SetGeoTransform( [ min_lon, res, 0, min_lat, 0, res ] )
  
# set the reference info 
srs = osr.SpatialReference()
srs.SetWellKnownGeogCS("WGS84")
dst_ds.SetProjection( srs.ExportToWkt() )

# write the band
dst_ds.GetRasterBand(1).WriteArray(final_raster)
