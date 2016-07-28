import numpy as np
import matplotlib.pyplot as plt
from skimage import transform,filters,morphology
from skimage.future import graph
from scipy import ndimage
import copy

def maxelem(a,b):
	if a>b:
		return a
	return b

def normalizeRange(img,newMin,newMax):
	
	const = (newMax - newMin)/(img.max()-img.min()) 
	img2 = (img - img.min())*const  + newMin 
	return img2.astype(np.uint8)

def generateInitialMask(ndsm,classified,slope,numret):

	print "Preparing Watershed base..."
	ndsm_gray = normalizeRange(ndsm,0,255)

	# Prepare Watershed Base

	# Remove Vegetation
	ndsm_noveg = copy.deepcopy(ndsm_gray)
	ndsm_noveg[classified==5] = 0

	# Perform Morphology

	ndsm_noveg_open = morphology.opening(ndsm_noveg,morphology.square(3))

	slope_thresh = slope > 60

	edges = copy.deepcopy(ndsm_gray)
	edges[~slope_thresh] = 0

	wshed_base = copy.deepcopy(ndsm_noveg_open)

	for y in xrange(len(ndsm_noveg_open)):
		for x in xrange(len(ndsm_noveg_open[0])):

			if slope_thresh[y][x] == True:
				# print "HERE"
				wshed_base[y][x] = ndsm_noveg_open[y][x]

	# Prepare Markers

	print "Preparing markers..."


	ndsm_thresh = ndsm > 2

	slope_thresh = slope > 30
	slope_morph = morphology.closing(slope_thresh,morphology.square(4))

	markers_level1 = ndsm_thresh & ~slope_morph

	vegetation = classified == 5
	markers_level2 = markers_level1 & ~vegetation

	markers_thresh = markers_level2!=0
	markers_small_removed = morphology.remove_small_objects(markers_thresh,10)
	markers_level3,num_labels = ndimage.label(markers_small_removed)

	markers_level3[ndsm<1] = -1
	markers_level3[classified==5] = -1

	# Perform Watershed segmentation

	print "Performing region growing..."

	wshed = ndimage.watershed_ift(input=wshed_base,markers=markers_level3)
	wshed[wshed==-1] = 0

	# Remove river artifacts

	print "Removing river artifacts..."

	returns = numret > 0

	labels =  list(np.unique(wshed))
	labels = labels[1:]

	#1454, 741
	# labels = [1454]

	area_thresh = 30

	for label in labels:

		print label
		clone = copy.deepcopy(wshed)

		obj_slice = ndimage.find_objects(clone==label)	

		# print obj_slice
		obj = clone[obj_slice[0][0],obj_slice[0][1]]
		obj[obj!=label] = 0

		obj = obj.astype(bool)

		area_orig = np.bincount(obj.flatten())[1]

		if area_orig < area_thresh:
			wshed[wshed==label] = 0

		returns_slice = returns[obj_slice[0][0],obj_slice[0][1]]
		intersect = returns_slice & obj
		intersect = intersect*1

		area_intersect = np.count_nonzero(intersect)

		ratio = float(area_intersect)/float(area_orig)

		if ratio <0.2:

			wshed[wshed==label] = 0

	return wshed

def buildFinalMask(results,labeledMask,circle_radius=5):

	vecMaxElem = np.vectorize(maxelem)

	paddedMask = np.zeros((len(labeledMask)+(circle_radius*2),len(labeledMask[0])+(circle_radius*2)),dtype=np.int)

	# print paddedMask.shape 

	for result in results:

		y_slice = result[2][0]
		x_slice = result[2][1]

		y_start = y_slice.start
		y_stop = y_slice.stop
		x_start = x_slice.start
		x_stop = x_slice.stop

		processedResults = paddedMask[y_start:y_stop+(circle_radius*2),x_start:x_stop+(circle_radius*2)]	
		processedResults[processedResults==result[0]] = 0
		tapal = vecMaxElem(processedResults,result[1])

		paddedMask[y_start:y_stop+(circle_radius*2),x_start:x_stop+(circle_radius*2)] = tapal

	return paddedMask[5:len(labeledMask)+5,5:len(labeledMask[0])+5]

	# io.imsave("putback000002_regularized_talaga.tif",paddedMask[circle_radius:len(labeledMask)+circle_radius,circle_radius:len(labeledMask[0])+circle_radius])