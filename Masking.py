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

# Using only classification from lastools
# A little cleaning
def generateInitialMask(ndsm,classified,slope,ndsmThreshold,slopeThreshold,smallObjectsThresh=60):

	ndsmThresh = ndsm > ndsmThreshold
	vegetation = classified == 5

	level0 = ~vegetation & ndsmThresh
	level1 = morphology.remove_small_objects(level0,smallObjectsThresh)
	
	slopeThresh = slope > slopeThreshold
	level2 = level1 & ~slopeThresh
	level3 = morphology.remove_small_objects(level2,smallObjectsThresh)

	clean = morphology.opening(level3,morphology.square(3))
	initialMask,num_labels = ndimage.label(clean)

	return level1,initialMask

# Use slope of slope para paghiwalayin ang dapat magkakahiwalay

def generateInitialMarkers(slopeslope,veggieMask,slopeThreshold=84,smallObjectsThresh=30):

	slopeThresh = slopeslope >slopeThreshold
	slopeThresh2 = morphology.opening(slopeThresh,morphology.square(2))
	slopeThresh2 = morphology.remove_small_objects(slopeThresh2,smallObjectsThresh)
	level2 = veggieMask & ~slopeThresh2
	level3 = morphology.remove_small_objects(level2,smallObjectsThresh)

	clean = morphology.opening(level3,morphology.square(3))
	initialMarkers,num_labels = ndimage.label(clean)

	return initialMarkers

def watershed(ndsm, initialMask,initialMarkers,veggieMask):

	# remove vegetation from ndsm

	veggieMask2 = morphology.opening(veggieMask,morphology.square(3))
	# veggieMask3 = morphology.erosion(veggieMask2,morphology.square(2))
	ndsm[veggieMask2==0] = 0 

	# watershed needs grayscale images
	ndsmNorm = normalizeRange(ndsm,0,255)

	initialMarkers[initialMask==0]=0

	# Look for first 0 pixel, mark with -1 for background
	for y in xrange(len(ndsm)):
		for x in xrange(len(ndsm)):
			if (ndsm[y][x]==0):
				break
	initialMarkers[y][x] = -1	

	wshed = ndimage.watershed_ift(input=ndsmNorm, markers=initialMarkers)
	# wshed[ndsm<3] = 0
	# wshed[veggieMask==0] = 0
	# wshed[wshed<0] = 0

	return wshed


def watershed2(ndsm, initialMask,initialMarkers,veggieMask):

	veggieMask2 = morphology.opening(veggieMask,morphology.square(3))
	# veggieMask3 = morphology.erosion(veggieMask2,morphology.square(2))
	ndsm[veggieMask2==0] = 0 

	ndsmNorm = normalizeRange(ndsm,0,255)

	initialMarkers[initialMask==0]=0

	# Bigger background markers
	initialMarkers[ndsm<2] = -1	

	wshed = ndimage.watershed_ift(input=ndsmNorm, markers=initialMarkers)
	wshed[ndsm<3] = 0
	wshed[veggieMask==0] = 0
	wshed[wshed<0] = 0

	return wshed	

def mergeRegionsBasic(labeledMask,mergeThreshold=0.15):

	newMask =copy.deepcopy(labeledMask)

	count = np.bincount(labeledMask.flatten())
	count = count.tolist()
	count = filter(lambda a: a != 0, count)

	rag = graph.rag_mean_color(labeledMask,labeledMask)

	nodes= rag.nodes()
	areas = dict(zip(nodes,count))

	for node in nodes:

		if node==0:
			continue
		
		area = areas[node]
		neighbors = rag.neighbors(node)
		
		# print node,area,neighbors

		# Case 1: Object is totally surrounded by another

		if len(neighbors) == 1 and neighbors!= [0]:
		
			if 0 in neighbors:
				neighbors.remove(0)

			biggestNeighbor = neighbors[0]

			for n in neighbors:
				if areas[n] > areas[biggestNeighbor]:
					biggestNeighbor = n
			# Modify Image
			newMask[newMask==node] = biggestNeighbor
			# Modify Area
			areas[biggestNeighbor] += areas[node]

			# Modify Graph
			for n in neighbors:
				rag.add_edge(n,biggestNeighbor)
			
			rag.remove_node(node)		
			continue

		if len(neighbors)>1:
			
			# Identify biggest neighbor
			if 0 in neighbors:
				neighbors.remove(0)

			biggestNeighbor = neighbors[0]

			for n in neighbors:
				if areas[n] > areas[biggestNeighbor]:
					biggestNeighbor = n

			# Modify Image
			ratio = float(areas[node])/areas[biggestNeighbor]
			
			if ratio<mergeThreshold:
				newMask[newMask==node] = biggestNeighbor

				# Modify Area
				areas[biggestNeighbor] += areas[node]
				
				# Modify Graph
				for n in neighbors:
					rag.add_edge(n,biggestNeighbor)
				rag.remove_node(node)
			continue

	return newMask

def mergeRegionsBasicV2(labeledMask,mergeThreshold=0.15,iterations=10):

	newMask =copy.deepcopy(labeledMask)

	count = np.bincount(labeledMask.flatten())
	count = count.tolist()
	count = filter(lambda a: a != 0, count)

	rag = graph.rag_mean_color(labeledMask,labeledMask)

	nodes= rag.nodes()
	areas = dict(zip(nodes,count))


	for i in xrange(iterations):
		nodes= rag.nodes()

		for node in nodes:

			if node==0:
				continue
			
			area = areas[node]
			neighbors = rag.neighbors(node)
			
			# print node,area,neighbors

			# Case 1: Object is totally surrounded by another

			if len(neighbors) == 1 and neighbors!= [0]:
			
				if 0 in neighbors:
					neighbors.remove(0)

				biggestNeighbor = neighbors[0]

				for n in neighbors:
					if areas[n] > areas[biggestNeighbor]:
						biggestNeighbor = n
				# Modify Image
				newMask[newMask==node] = biggestNeighbor
				# Modify Area
				areas[biggestNeighbor] += areas[node]

				# Modify Graph
				for n in neighbors:
					rag.add_edge(n,biggestNeighbor)
				
				rag.remove_node(node)		
				continue

			if len(neighbors)>1 and 0 not in neighbors:
				
				# Identify biggest neighbor
				if 0 in neighbors:
					neighbors.remove(0)

				biggestNeighbor = neighbors[0]

				for n in neighbors:
					if areas[n] > areas[biggestNeighbor]:
						biggestNeighbor = n

				# Modify Image
				# ratio = float(areas[node])/areas[biggestNeighbor]
				
				# if ratio<mergeThreshold:
				newMask[newMask==node] = biggestNeighbor

				# Modify Area
				areas[biggestNeighbor] += areas[node]
				
				# Modify Graph
				for n in neighbors:
					rag.add_edge(n,biggestNeighbor)
				rag.remove_node(node)
				continue

	return newMask

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