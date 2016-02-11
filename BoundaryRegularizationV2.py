import networkx as nx
import math
import numpy as np
from scipy import ndimage
from skimage.draw import circle_perimeter,line
from skimage.segmentation import find_boundaries
from skimage import morphology
import copy
import multiprocessing as mp
import time
import cmath
from scipy.interpolate import interp1d
from scipy.misc import derivative
import matplotlib.pyplot as plt
import matplotlib

#Simulated Annealing Parameters
SM_START_TEMP = 1.0
SM_MAX_TEMP = 3.5
SM_TEMP_RATE = 0.5

#Number of iterations
LEARN_ITR = 40

#Depends on the training data
TRAINING_MIN_AREA = 60			#MINIMUM AREA IN TRAINING DATA
TRAINING_MAX_AREA = 20576		#MAXIMUM AREA IN TRAINING DATA

def uniqify(seq): # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

#function for getting the boundaries' ordered points
def moore_neighbor_tracing(points, obj):
	#define the starting point
	ordered_points = [points[0]]
	start = point = points[0]
	start_pos = pos = 0
	flag = True

	#Loop until ordered points were found
	while(flag):
		#apply moore neighbor tracing
		for itr in xrange(0, 8):

			if(pos == 1):
				mask_point = (point[0]-1, point[1]-1)
			elif(pos == 2):
				mask_point = (point[0]-1, point[1])
			elif(pos == 3):
				mask_point = (point[0]-1, point[1]+1)
			elif(pos == 4):
				mask_point = (point[0], point[1]+1)
			elif(pos == 5):
				mask_point = (point[0]+1, point[1]+1)
			elif(pos == 6):
				mask_point = (point[0]+1, point[1])
			elif(pos == 7):
				mask_point = (point[0]+1, point[1]-1)
			elif(pos == 0):
				mask_point = (point[0], point[1]-1)

			if obj[mask_point[0]][mask_point[1]] != 0:
				point = mask_point
				ordered_points.append(point)
				break

			pos = (pos + 1) % 8

		if pos == 0 or pos == 1:
			pos = 6
		elif pos == 2 or pos == 3:
			pos = 0
		elif pos == 4 or pos == 5:
			pos = 2
		elif pos == 6 or pos == 7:
			pos = 4

		#if the current point is equal to the starting point
		if point == start:
			#and if the len of ordered points = number of given points
			if len(uniqify(ordered_points)) == len(points):
				#found the correct ordered points -> terminate
				flag = False

	return uniqify(ordered_points)

# ------ Start of Allen's Madness ------- >

#function for getting the angle -> given three points
def get_angle(PoI, index, footprint):
	point1 = footprint[index - 1]
	point2 = footprint[(index + 1) % len(footprint)]
	P01_dist = np.linalg.norm(PoI - point1)
	P02_dist = np.linalg.norm(PoI - point2)
	P12_dist = np.linalg.norm(point1 - point2)
	angle = np.degrees(np.arccos((P01_dist ** 2 + P02_dist ** 2 - P12_dist ** 2) / (2 * P01_dist * P02_dist)))

	return angle

#compute total cost of every point
def compute_total_cost(prior, distances, spline, temperature):
	prior_cost = 0
	dist_cost = 0
	slope = []

	for idx, angle in enumerate(prior):
		prior_cost += spline(angle)
		dist_cost += distances[idx]**2

	return ((prior_cost)) + (1.0 / ((2 * (temperature ** 2))) * dist_cost)

#compute cost of the current location of the point
def compute_cost(prior, distance, spline, temperature):
	penalty = spline(prior)
	return math.log(penalty) + (1.0 / ((2 * (temperature ** 2))) * distance)

#function for finding the new coordinate of a point
def find_new_coordinate(boundary, index, footprint_point, possible_points, temperature, spline):

	best_cost = "notset"
	#iterate through every possible points and compute evry cost
	for point in possible_points:
		angle = get_angle(point, index, boundary)
		distance = np.linalg.norm(point - footprint_point)
		cost = compute_cost(angle, distance, spline, temperature)
	
		if best_cost == "notset" or best_cost > cost:
			best_angle = angle
			best_dist = distance
			best_cost = cost
			best_point = point

	#return the new coordinate with the lowest cost
	return best_point, best_angle, best_dist

#creates mask for possible points
def form_mask_BR(start_temp, max_temp, temp_rate):
	dtype = [('temp', float), ('mask', np.ndarray)]
	masks = []
	#IMPROVEMENT!!!
	#MINUS LAST COORDINATES TO NEXT TEMPERATURE
	#LESS POINTS TO CHECK
	while (start_temp <= max_temp):
		coordinates = []
		distance = int(round(start_temp))
		array_size = distance * 2 + 1
		img = np.zeros((array_size, array_size), dtype=np.uint8)
		rr, cc = circle_perimeter(distance, distance, distance)
		img[rr, cc] = 1
		rr,cc = np.nonzero(ndimage.binary_fill_holes(img).astype(int))
		img[rr, cc] = 1

		for idx in xrange(0, len(rr)):
			if np.linalg.norm(np.array([rr[idx], cc[idx]]) - np.array([distance, distance])) <= start_temp:
				coordinates.append([rr[idx], cc[idx]])

		# coordinates.remove([distance, distance])
		coordinates = coordinates - np.array([distance, distance])
		masks.append((start_temp, coordinates))
		start_temp += temp_rate

	return np.array(masks, dtype=dtype)	

def adjust_route(footprint, masks, temperature = SM_START_TEMP, temp_rate = SM_TEMP_RATE, max_temp = SM_MAX_TEMP):

	# print temperature
	# print max_temp

	angle_x = [0,20,45,75,90,105,120,135,150,165,180]
	penalty_y = [1.1,1.0,0.6,0.7,0.1,0.7,0.6,0.5,0.6,0.5,0.1]
	# temperature = 1.0
	# temp_rate = 0.5
	# learning_rate = 10
	# d = 1.5

	#FOOTPRINT = ORIGINAL
	#BOUNDARY = MODIFIED
	len_points = len(footprint)
	f = interp1d(angle_x, penalty_y, kind='cubic')
	boundary = copy.deepcopy(footprint)
	distances = np.zeros(len_points)
	point_costs = np.zeros(len_points)
	boundary_angle = []

	for idx, point in enumerate(footprint):
		boundary_angle.append(get_angle(point, idx, footprint))

	boundary_angle = np.array(boundary_angle)

	dtype = [('index', int), ('penalty', float)]
	penalties = []
	for idx, angle in enumerate(boundary_angle):
		penalties.append((idx, float(f(angle))))		#CHANGE THIS
		# print angle, f(angle)
	# print penalties
	penalties = np.array(penalties, dtype=dtype)       # create a structured array
	penalties = np.sort(penalties, order='penalty')
	# print penalties

	best_boundary = copy.deepcopy(boundary)
	best_boundary_angle = copy.deepcopy(boundary_angle)
	best_distances = copy.deepcopy(distances)
	best_cost = "notset"

	#START OF LOOP FOR CONVERGENCE
	for i in xrange(0,LEARN_ITR):

		for idx in xrange(0, len_points):
		
			focus_point = penalties[idx][0]				#USE THIS INDEX
			new_point, new_angle, new_dist = find_new_coordinate(boundary, focus_point, footprint[focus_point], footprint[focus_point] - masks[masks["temp"] == temperature]["mask"][0], temperature, f)
			boundary[focus_point] = new_point
			boundary_angle[focus_point] = new_angle
			distances[focus_point] = new_dist

			boundary_angle[focus_point - 1] = get_angle(boundary[focus_point - 1], focus_point - 1, boundary)
			boundary_angle[(focus_point + 1) % len_points] = get_angle(boundary[(focus_point + 1) % len_points], (focus_point + 1) % len_points, boundary)

		cost = compute_total_cost(boundary_angle, distances, f, temperature)


		if best_cost > cost or best_cost == "notset" or math.isnan(best_cost):
			best_boundary = copy.deepcopy(boundary)
			best_boundary_angle = copy.deepcopy(boundary_angle)
			best_distances = copy.deepcopy(distances)
			best_cost = cost


		if temperature < max_temp:
			temperature += temp_rate

	return best_boundary

def regularizeBoundary(indexedObject):

	t0 = time.time()
	obj = indexedObject[1]

	CIRCLE_RADIUS = 5
	MINIMUM_BOUNDARY = 70
	MAXIMUM_DISTANCE = 15
	MINIMUM_SIDES = 4

	obj_length = obj.shape
	obj_area = len(obj[obj != 0])

	lin_area = [60,86,113,137,140,146,152,155,158,176,183,187,191,194,198,202,209,221,231,240,247,254,265,280,289,290,293,294,299,307,317,332,344,369,386,398,415,424,446,256,472,485,517,532,571,590,611,634,671,689,713,722,755,781,796,893,938,970,1004,1050,1050,1107,1114,1153,1164,1226,1518,1598,1762,1830,1875,1985,2045,2212,2574,2829,2895,3038,3610,4299,5088,5261,5312,5961,10616,12586,20576]
	lin_min_e = [0.4,0.4,0.4,0.4,0.6,0.4,0.425,0.5,0.425,0.4,0.475,0.5,0.475,0.475,0.5,0.6,0.625,0.7,0.6,0.6,0.6,0.725,0.725,0.7,0.7,0.7,0.6,0.6,0.7,0.7,0.75,0.75,0.75,0.775,0.76,0.75,0.8,0.775,0.7,0.725,0.725,0.8,0.83,0.805,0.82,0.8,0.85,0.85,0.9,0.87,0.9,0.9,0.9,0.92,1.0,1.0,1.0,0.95,1.0,0.9,0.95,1.0,1.0,1.0,1.0,1.0,0.9,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0]
	lin_temp = [1.0,1.0,1.0,1.0,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,1.5,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.5,2.5,2.5,2.5,2.5,2.5,2.5,2.5,2.5,2.5,3.0,3.0,3.0,3.0,3.0,3.0,3.5,3.5,3.5,3.5]

	f1_min_e = interp1d(lin_area, lin_min_e)
	f2_temp = interp1d(lin_area, lin_temp)

	if obj_area < TRAINING_MIN_AREA:
		obj_area = TRAINING_MIN_AREA
	elif obj_area > TRAINING_MAX_AREA:
		obj_area = TRAINING_MAX_AREA

	MIN_E_DISTANCE = f1_min_e(obj_area)
	CURR_MAX_TEMP = f2_temp(obj_area)

	if CURR_MAX_TEMP % 0.5 != 0.0:
		CURR_MAX_TEMP = round(CURR_MAX_TEMP * 2.0) / 2.0


	original_image = np.zeros((obj_length[0]+CIRCLE_RADIUS*2,obj_length[1]+CIRCLE_RADIUS*2),dtype=np.uint)
	original_image[CIRCLE_RADIUS:obj_length[0]+CIRCLE_RADIUS,CIRCLE_RADIUS:obj_length[1]+CIRCLE_RADIUS] = obj

	boundary_image = find_boundaries(original_image, mode='inner').astype(np.uint8) #value = 1

	nonzero_x, nonzero_y = np.nonzero(boundary_image)
	zip_nonzero = zip(nonzero_x, nonzero_y)
	ordered_points = moore_neighbor_tracing(zip_nonzero, boundary_image)

	for point in zip_nonzero:
		segments = []
		circle_x, circle_y = circle_perimeter(point[0],point[1],CIRCLE_RADIUS)
		circle_points = np.array(list(sorted(set(zip(circle_x,circle_y)))))

		sortedpoints = np.empty([len(circle_points), 2], dtype=int)

		test1 = circle_points[circle_points[:,0] == point[0] - CIRCLE_RADIUS]
		start = len(test1)
		end = len_cpoints = len(sortedpoints)
		sortedpoints[0:start] = test1

		for x in xrange(point[0] - CIRCLE_RADIUS + 1, point[0] + CIRCLE_RADIUS):
			test1 = circle_points[circle_points[:,0] == x]
			testlen = len(test1)
			if x <= point[0]:
				sortedpoints[start:start+testlen/2] = test1[testlen/2:]
				sortedpoints[end-testlen/2:end] = test1[:testlen/2]
			else:
				sortedpoints[start:start+testlen/2] = test1[testlen/2:][::-1]
				sortedpoints[end-testlen/2:end] = test1[:testlen/2][::-1]
			start += testlen/2
			end -= testlen/2

		test1 = circle_points[circle_points[:,0] == point[0] + CIRCLE_RADIUS]
		sortedpoints[start:start + len(test1)] = test1[::-1]

		for c_perimeter in sortedpoints:
			segments.append(True)
			line_x, line_y = line(point[0], point[1], c_perimeter[0], c_perimeter[1])
			for line_points in zip(line_x,line_y)[1:]:
				if original_image[line_points[0]][line_points[1]] != 0:
					segments[-1] = False
					break

		min_boundpoints = (MINIMUM_BOUNDARY / 360.0) * len_cpoints

		seg_sizes = []
		new_segment = True
		for segment in segments:
			if segment:
				if new_segment:
					seg_sizes.append(1)
					new_segment = False
				else:
					seg_sizes[-1] += 1
			else:
				new_segment = True

		if segments[0] == True and segments[-1] == True and len(seg_sizes) > 1:
			seg_sizes[0] = seg_sizes[0] + seg_sizes[-1]
			seg_sizes.pop()
		
		if(len(seg_sizes) == 0 or max(seg_sizes) < min_boundpoints):
			boundary_image[point[0]][point[1]] = 0

			if (point[0],point[1]) in ordered_points:  ## IDENTIFY KUNG BAKIT NAGKA-ERRROR, EXAMPLE pt000120_merged4.py obj 1301
				ordered_points.remove((point[0],point[1]))


	# print "Obtaining All Possible Edges..."
	G=nx.DiGraph()
	len_ordered_points = len(ordered_points)

	for idx in xrange(0,len_ordered_points):

		
		next_idx = (idx+1) % len_ordered_points
		dist = math.hypot(ordered_points[idx][0] - ordered_points[next_idx][0], ordered_points[idx][1] - ordered_points[next_idx][1])
		G.add_edge(idx,next_idx,weight=dist)
		G.add_edge(idx,str(next_idx),weight=dist)

		# idx2 = idx - 2
		idx2 = (idx + 2) % len_ordered_points
		fail_counter = 0

		while((idx2 + 1) % len_ordered_points != idx and fail_counter < 20):  #?

			counter = 0
			total_distance = 0.0
			average_distance = 0.0
			base   = math.hypot(ordered_points[idx][0] - ordered_points[idx2][0], ordered_points[idx][1] - ordered_points[idx2][1])
			idx3 = (idx + 1) % len_ordered_points

			while(idx2 != idx3): #?

				side_1 = math.hypot(ordered_points[idx][0] - ordered_points[idx3][0], ordered_points[idx][1] - ordered_points[idx3][1])
				side_2 = math.hypot(ordered_points[idx2][0] - ordered_points[idx3][0], ordered_points[idx2][1] - ordered_points[idx3][1])
				semi_perimeter = (side_1 + side_2 + base) / 2.0
				temp = semi_perimeter * (semi_perimeter - side_1) * (semi_perimeter - side_2) * (semi_perimeter - base)
				if temp < 0:
					temp = 0
				area   = math.sqrt(temp)
				height = (2.0 * area) / base
				Ax = ordered_points[idx][0]           
				Ay = ordered_points[idx][1]
				Bx = ordered_points[idx2][0]
				By = ordered_points[idx2][1]
				Cx = ordered_points[idx3][0]
				Cy = ordered_points[idx3][1]
				position = np.sign((Bx-Ax)*(Cy-Ay) - (By-Ay)*(Cx-Ax))
				total_distance += height * position
				average_distance += height
				counter += 1
				idx3 = (idx3 + 1) % len_ordered_points

			average_distance /= counter

			if average_distance <= MIN_E_DISTANCE and total_distance >= -MIN_E_DISTANCE and total_distance < 30:
				G.add_edge(idx,idx2,weight=base)
				G.add_edge(idx,str(idx2),weight=base)
				fail_counter = 0
			else:
				fail_counter += 1

			idx2 = (idx2 + 1) % len_ordered_points


	F = nx.floyd_warshall_predecessor_and_distance(G)

	best_route = []
	count = 0
	for target in xrange(0,len_ordered_points):
		pointer = str(target)
		route = []
		route.append(pointer)

		while pointer != target:
			pointer = F[0][target][pointer]
			route.append(pointer)
		if len(route) == 7:
			count += 1
		if len(best_route) == 0 or len(best_route) > len(route):
			best_route = copy.deepcopy(route)

	mask_BR = form_mask_BR(SM_START_TEMP, SM_MAX_TEMP, SM_TEMP_RATE)# Pwede ilabas ito, actually ilabas mo agad tanga

	footprint = []

	for point in best_route:
		 footprint.append(list(ordered_points[int(point)]))

	footprint.pop()

	adjusted_route = adjust_route(np.array(footprint),mask_BR, max_temp = CURR_MAX_TEMP) 		

	approx_image = copy.deepcopy(boundary_image)
	approx_image[approx_image > 0] = 0

	len_points = len(adjusted_route)
	for idx in xrange(0,len_points-1):
		rr,cc = line(adjusted_route[idx][0], adjusted_route[idx][1], adjusted_route[idx+1][0], adjusted_route[idx+1][1])
		approx_image[rr,cc] = 4
		approx_image[adjusted_route[idx][0], adjusted_route[idx][1]] = 5
		approx_image[adjusted_route[(idx+1)% len_points][0], adjusted_route[(idx+1)% len_points][1]] = 5
	rr,cc = line(adjusted_route[len_points-1][0], adjusted_route[len_points-1][1], adjusted_route[0][0], adjusted_route[0][1])
	approx_image[rr,cc] = 4

	# for idx in xrange(0,len(adjusted_route)-1):
	# 	rr,cc = line(ordered_points[int(adjusted_route[idx])][0], ordered_points[int(adjusted_route[idx])][1], ordered_points[int(adjusted_route[idx+1])][0], ordered_points[int(adjusted_route[idx+1])][1])
	# 	approx_image[rr,cc] = 1
	# 	approx_image[ordered_points[int(adjusted_route[idx])][0], ordered_points[int(adjusted_route[idx])][1]] = 2
	# 	approx_image[ordered_points[int(adjusted_route[idx+1])][0], ordered_points[int(adjusted_route[idx+1])][1]] = 2

	approx_image[approx_image>0] = 1
	filled = ndimage.binary_fill_holes(approx_image)
	filled = filled*1	
	filled[filled==1] = indexedObject[0] 
	
	t1=time.time()
	print "Finished processing index",indexedObject[0],"in",round(t1-t0,2),"s."		
	return indexedObject[0],filled,indexedObject[2]

def performBoundaryRegularization(labeledMask,numProcesses=7): # This is where the shit starts

	labeledMaskWidth = len(labeledMask)
	labeledMaskHeight = len(labeledMask[0])

	reducedPointsMask = copy.deepcopy(labeledMask)

	indices = np.unique(reducedPointsMask)
	indices = indices[1:]

	objects = []
	indexList = []
	slices2 = []
	results = []

	for index in indices:

		clone = copy.deepcopy(labeledMask)
		islays = ndimage.find_objects(clone==index)

		obj = clone[islays[0][0],islays[0][1]]
		obj[obj!=index] = 0
		obj = ndimage.binary_fill_holes(obj)
		obj = morphology.remove_small_objects(obj,5) # Fallback lamang ito 
		obj = obj*index

		area = np.bincount(obj.flatten())[index]
		
		objects.append(obj)
		indexList.append(index)
		slices2.append(islays[0])
		

	indexedObjects = zip(indexList,objects,slices2) 
	print "Number of objects to be processed:", len(indexedObjects)

	pool = mp.Pool(numProcesses)
	results = pool.map(regularizeBoundary,indexedObjects)
	pool.close()
	pool.join()

	return results


def performBoundaryRegularizationV2(labeledMask,numProcesses=7): # This is where the shit starts

	labeledMaskWidth = len(labeledMask)
	labeledMaskHeight = len(labeledMask[0])

	reducedPointsMask = copy.deepcopy(labeledMask)

	indices = np.unique(reducedPointsMask)
	indices = indices[1:]

	objects = []
	indexList = []
	slices2 = []
	results = []

	for index in indices:
		print "Preparing",index
		clone = copy.deepcopy(labeledMask)
		islays = ndimage.find_objects(clone==index)

		obj = clone[islays[0][0],islays[0][1]]
		obj[obj!=index] = 0
		obj = ndimage.binary_fill_holes(obj)

		labeled_ulit,num_labels = ndimage.label(obj)

		if num_labels >1:

			objects_ulit = ndimage.find_objects(labeled_ulit)

			biggestArea = 0
			biggest = 0
			for i,o in enumerate(objects_ulit):

				area = len(obj[o])*len(obj[o][0])	

				if area > biggestArea:
					biggestArea = area	
					biggest = i

			obj = obj[objects_ulit[biggest]]		
			islays[0] = objects_ulit[biggest]	


		obj = obj*index

		# area = np.bincount(obj.flatten())[index]
		
		objects.append(obj)
		indexList.append(index)
		slices2.append(islays[0])
		

	indexedObjects = zip(indexList,objects,slices2) 
	print "Number of objects to be processed:", len(indexedObjects)

	pool = mp.Pool(numProcesses)
	results = pool.map(regularizeBoundary,indexedObjects)
	pool.close()
	pool.join()

	return results

def nonParallel(labeledMask,numProcesses=7):

	labeledMaskWidth = len(labeledMask)
	labeledMaskHeight = len(labeledMask[0])

	reducedPointsMask = copy.deepcopy(labeledMask)

	indices = np.unique(reducedPointsMask)
	indices = indices[1:]
	# indices = [37,38]

	objects = []
	indexList = []
	slices2 = []
	results = []

	for index in indices:

		# t0 = time.time()

		t0 = time.time()

		clone = copy.deepcopy(labeledMask)
		islays = ndimage.find_objects(clone==index)

		obj = clone[islays[0][0],islays[0][1]]
		obj[obj!=index] = 0
		obj = ndimage.binary_fill_holes(obj)
		obj = morphology.remove_small_objects(obj,5) # Fallback lamang ito 
		obj = obj*index

		area = np.bincount(obj.flatten())[index]
		
		print "Processing index", index, "with an area of",area,"pixels."

		result = regularizeBoundary((index,obj,islays[0]))


		# cmap = matplotlib.colors.ListedColormap ( np.random.rand ( 256,3))

		# fig, axes = plt.subplots(ncols=2, figsize=(18, 10))
		# ax0, ax1 = axes
		# fig0 = ax0.imshow(result[1],interpolation="none",cmap=plt.cm.gray)
		# fig1 = ax1.imshow(result[1],interpolation="none",cmap=cmap)

		# plt.show()
		results.append(result)

		t1 = time.time()

		print "Finished in",round(t1-t0,2),"s."


	return results	