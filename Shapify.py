import numpy as np
from osgeo import ogr,gdal
from skimage import io
import copy
import subprocess
import os
import shutil
import sys
import time

def gdalcopyproj(input,output):

	dataset = gdal.Open( input )
	if dataset is None:
	    print('Unable to open', input, 'for reading')
	    sys.exit(1)

	projection   = dataset.GetProjection()
	geotransform = dataset.GetGeoTransform()

	if projection is None and geotransform is None:
	    print('No projection or geotransform found on file' + input)
	    sys.exit(1)

	dataset2 = gdal.Open( output, gdal.GA_Update )

	if dataset2 is None:
	    print('Unable to open', output, 'for writing')
	    sys.exit(1)

	if geotransform is not None and geotransform != (0,1,0,0,0,1):
	    dataset2.SetGeoTransform( geotransform )

	if projection is not None and projection != '':
	    dataset2.SetProjection( projection )

	gcp_count = dataset.GetGCPs()
	if gcp_count != 0:
	    dataset2.SetGCPs( gcp_count, dataset.GetGCPProjection() )

	dataset = None
	dataset2 = None

if __name__ == "__main__":

    main()

def main():

	print "HELLO"
