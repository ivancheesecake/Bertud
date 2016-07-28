import numpy as np
from scipy import ndimage
from skimage import io
import subprocess
import os
import shutil
import multiprocessing as mp

def slopeFilter(x):

	a = x[0]
	b = x[1]
	c = x[2]
	d = x[3]
	e = x[4]
	f = x[5]
	g = x[6]
	h = x[7]
	i = x[8]
	
	dzdx = ((c + 2*f + i) - (a + 2*d + g)) /4	# cellsize is 0.5
	dzdy = ((g + 2*h + i) - (a + 2*b + c))/4


	rise_run = np.sqrt(dzdx*dzdx + dzdy*dzdy)  
	slope_degrees = np.arctan(rise_run) * 57.29578
	return slope_degrees


def prepareInputs():

	lastoolsPath = "C:/lastools/bin/"

	# Run lasground
	# Note: Nasa laszip dapat
	os.chdir(lastoolsPath)

	print "Running LASground..."

	subprocess.call(["lasground_new", "-i", "C:/bertud_temp/pointcloud.laz","-metro", "-compute_height","-odir", "C:/bertud_temp/", "-o","ground.laz"], stdout=subprocess.PIPE)

	print "Running LASClassify..."

	# Prepare file_list.txt

	# subprocess.call(["lasclassify", "-i", "C:/bertud_temp/ground.laz","-odir", "C:/bertud_temp/", "-o","classified.laz"], stdout=subprocess.PIPE)
	
	# Added fine tuning parameter -planar
	subprocess.call(["lasclassify", "-i", "C:/bertud_temp/ground.laz","-planar","0.15","-odir", "C:/bertud_temp/", "-o","classified.laz"], stdout=subprocess.PIPE)

	print "Running LASGrid for classification raster..."

	# Prepare file_list.txt
	# subprocess.call(["lasgrid", "-i", "C:/bertud_temp/classified.laz","-step","0.5","-classification","-odir", "C:/bertud_temp/", "-o","classified.tif"], stdout=subprocess.PIPE)
	
	# Added fine tuning parameter -subsample 8
	subprocess.call(["lasgrid", "-i", "C:/bertud_temp/classified.laz","-step","0.5","-classification","-subsample","8","-odir", "C:/bertud_temp/", "-o","classified.tif"], stdout=subprocess.PIPE)

	print "Running LASGrid for number of returns raster..."
	subprocess.call(["lasgrid", "-i", "C:/bertud_temp/classified.laz","-step","0.5","-number_returns","-lowest","-subsample","8","-odir", "C:/bertud_temp/", "-o","numret.tif"], stdout=subprocess.PIPE)

	print "Running blast2DEM..."
	
	subprocess.call(["blast2dem", "-i", "C:/bertud_temp/classified.laz", "-first_only","-step","0.5","-elevation","-odir", "C:/bertud_temp/", "-o","dsm.tif"], stdout=subprocess.PIPE)
	subprocess.call(["blast2dem", "-i", "C:/bertud_temp/classified.laz", "-keep_classification","2","-keep_classification","8","-step","0.5","-elevation","-odir", "C:/bertud_temp/", "-o","dtm.tif"], stdout=subprocess.PIPE)

	dsm = io.imread("C:/bertud_temp/dsm.tif")
	dtm = io.imread("C:/bertud_temp/dtm.tif")

	# nDSM

	dtm[dtm<0] = 9999
	dsm[dsm<0] = 0

	ndsm = dsm-dtm

	# Revised nDSM generation
	# ndsm[ndsm<2] = 0
	ndsm[ndsm<0] = 0

	io.imsave("C:/bertud_temp/ndsm.tif",ndsm)
	
	# Slope 

	slope = ndimage.generic_filter(ndsm,slopeFilter,size=3)
	io.imsave("C:/bertud_temp/slope.tif",slope)

	slopeslope = ndimage.generic_filter(slope,slopeFilter,size=3)
	io.imsave("C:/bertud_temp/slopeslope.tif",slopeslope)

