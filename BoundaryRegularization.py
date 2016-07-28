from skimage import io, morphology
# import BoundaryRegularizationV2 as br
import copy
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
import time
import cmath
from scipy.interpolate import interp1d
from scipy.misc import derivative
import matplotlib.pyplot as plt
import matplotlib
from skimage.draw import circle_perimeter,line
from skimage.segmentation import find_boundaries
import networkx as nx
import math
import random
import multiprocessing as mp

SM_START_TEMP = 1.0
SM_MAX_TEMP = 3.5
SM_TEMP_RATE = 0.5

LEARN_ITR = 40

TRAINING_MIN_AREA = 60			#MINIMUM AREA IN TRAINING DATA
TRAINING_MAX_AREA = 20576		#MAXIMUM AREA IN TRAINING DATA

def uniqify(seq): # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

def moore_neighbor_tracing(points, obj):
	ordered_points = [points[0]]
	start = point = points[0]
	start_pos = pos = 0
	flag = True

	while(flag):
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

		# if pos == start_pos and point == start:
		
		if point == start:
			if len(uniqify(ordered_points)) == len(points):
				flag = False

	return uniqify(ordered_points)

# ------ Start of Allen's Madness ------- >

def get_angle(PoI, index, footprint):

	#Look for the first adjacent point not equal to current point
	idx = 1
	while np.array_equal(footprint[index - idx], PoI):
		idx += 1
	point1 = footprint[index - idx]

	#Look for the second adjacent point not equal to current point
	idx = 1
	while np.array_equal(footprint[(index + idx) % len(footprint)], PoI):
		idx += 1
	point2 = footprint[(index + idx) % len(footprint)]

	P01_dist = np.linalg.norm(PoI - point1)
	P02_dist = np.linalg.norm(PoI - point2)
	P12_dist = np.linalg.norm(point1 - point2)
	angle = np.degrees(np.arccos((P01_dist ** 2 + P02_dist ** 2 - P12_dist ** 2) / (2 * P01_dist * P02_dist)))

	return angle

def form_mask_BR_v2(start_temp, max_temp, temp_rate):
	dtype = [('temp', float), ('mask', np.ndarray), ('dist', np.ndarray)]
	masks = []
	#IMPROVEMENT!!!
	#MINUS LAST COORDINATES TO NEXT TEMPERATURE
	#LESS POINTS TO CHECK
	while (start_temp <= max_temp):
		coordinates = []
		coor_dist = []
		distance = int(round(start_temp))
		array_size = distance * 2 + 1
		img = np.zeros((array_size, array_size), dtype=np.uint8)
		rr, cc = circle_perimeter(distance, distance, distance)
		img[rr, cc] = 1
		rr,cc = np.nonzero(ndimage.binary_fill_holes(img).astype(int))
		img[rr, cc] = 1

		for idx in xrange(0, len(rr)):
			dist_temp = np.linalg.norm(np.array([rr[idx], cc[idx]]) - np.array([distance, distance]))
			if dist_temp <= start_temp:
				coordinates.append([rr[idx], cc[idx]])
				coor_dist.append(dist_temp)

		# coordinates.remove([distance, distance])
		coordinates = coordinates - np.array([distance, distance])
		masks.append((start_temp, coordinates, np.array(coor_dist)))
		start_temp += temp_rate

	return np.array(masks, dtype=dtype)

def compute_solution_cost(angles, distances, temperature, cost_spline):

	cost_angles = 0.0
	cost_distances = 0.0

	for idx, angle in enumerate(angles):
		cost_angles += math.log10(cost_spline(angle))
		cost_distances += distances[idx] ** 2.0

	return (cost_angles) + ((1.0 / (2.0 * (temperature ** 2.0))) * cost_distances)

def acceptance_probability(old_cost, new_cost, T):

	return math.e ** ((old_cost - new_cost) / T)

def simulated_annealing_v2(footprint, angles, distances, cost_spline, init_temp = 0.125, max_temp = 1.0, rate_temp = 0.0625, max_dist = 5.0):

	temp = init_temp
	iteration_per_temp = 400
	num_points = len(distances)
	gauss_multiplier = 8.0

	best_solution = {}
	best_solution["footprint"] = footprint
	best_solution["angles"] = angles
	best_solution["distances"] = distances
	# best_solution["cost"] = compute_solution_cost(angles, distances, temp * gauss_multiplier, cost_spline)
	accepted_solution = copy.deepcopy(best_solution)
	# new_solution = copy.deepcopy(best_solution)

	#generate mask for neighbor
	neighbors = form_mask_BR_v2(max_dist, max_dist, rate_temp)
	neighbors_distances = neighbors[neighbors["temp"] == max_dist]["dist"][0]
	neighbors_locations = neighbors[neighbors["temp"] == max_dist]["mask"][0]

	while temp <= max_temp:

		#?
		accepted_solution["cost"] = compute_solution_cost(accepted_solution["angles"], accepted_solution["distances"], gauss_multiplier, cost_spline)
		best_solution["cost"] = compute_solution_cost(best_solution["angles"], best_solution["distances"], gauss_multiplier, cost_spline)

		for idx in xrange(0, iteration_per_temp):

			#randomize distances for each points
			random_distances = []
			for idx2 in xrange(0, num_points):
				dist = abs(np.random.normal(scale = math.sqrt(temp * gauss_multiplier)))

				#bound dist to max_dist
				if dist > max_dist:
					dist = max_dist

				random_distances.append(dist)

			prospect_solution = copy.deepcopy(accepted_solution)

			for idx2 in xrange(0, num_points):
				#OPTIMIZE
				new_solution = copy.deepcopy(accepted_solution)

				#subtract to distances in masks then get the lowest or "nearest"
				temp_distances = neighbors_distances - random_distances[idx2]
				prospect_idxs = np.where(temp_distances == min(temp_distances[temp_distances >= 0.0]))[0] #?
				#randomize point to use
				rand_pros_idx = random.choice(prospect_idxs)
				#minus / add the mask to the point
				new_solution["footprint"][idx2] = footprint[idx2] + neighbors_locations[rand_pros_idx]
				new_solution["distances"][idx2] = neighbors_distances[rand_pros_idx]		#update distance
				
				#OPTIMIZE - wag na lahat iupdate no need
				for idx3, point in enumerate(new_solution["footprint"]):
					new_solution["angles"][idx3] = get_angle(point, idx3, new_solution["footprint"])

				new_solution["cost"] = compute_solution_cost(new_solution["angles"], new_solution["distances"], gauss_multiplier, cost_spline)
				ap = acceptance_probability(accepted_solution["cost"], new_solution["cost"], temp)

				#if acceptance probability > random number, accept the solution
				if ap > random.random():
					prospect_solution["footprint"][idx2] = new_solution["footprint"][idx2]
					prospect_solution["distances"][idx2] = new_solution["distances"][idx2]
			
			for idx2, point in enumerate(prospect_solution["footprint"]):
				prospect_solution["angles"][idx2] = get_angle(point, idx2, prospect_solution["footprint"])

			prospect_solution["cost"] = compute_solution_cost(prospect_solution["angles"], prospect_solution["distances"], gauss_multiplier, cost_spline)
			ap = acceptance_probability(accepted_solution["cost"], prospect_solution["cost"], temp)
			
			if ap > random.random():
				old_cost = accepted_solution["cost"]
				accepted_solution = copy.deepcopy(prospect_solution)
				if accepted_solution["cost"] < best_solution["cost"]:
					best_solution = copy.deepcopy(accepted_solution)


		#update temp
		temp += rate_temp

	return best_solution["footprint"]

def adjust_route_v2(footprint):

	#print "================ADJUSTING ROUTES================="

	angle_x = [0,20,45,75,90,105,120,135,150,165,180]
	penalty_y = [1.1,1.0,0.6,0.7,0.1,0.7,0.6,0.5,0.6,0.5,0.1]
	angle_cost_fxn = interp1d(angle_x, penalty_y, kind='cubic')

	angles = []
	distances = []

	for idx, point in enumerate(footprint):
		angles.append(get_angle(point, idx, footprint))
		distances.append(0.0)

	# print "POINT", footprint
	# print "ANGLE", angles
	# print "DIST", distances

	footprint = simulated_annealing_v2(footprint, angles, distances, angle_cost_fxn)

	# print "NEW", footprint
	# gradient_descent(footprint, angles, distances, angle_cost_fxn)

	return footprint

def regularizeBoundary(indexedObject):

	print "Started processing index ",indexedObject[0],"."
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
	E=nx.DiGraph()
	len_ordered_points = len(ordered_points)

	for idx in xrange(0,len_ordered_points):

		
		next_idx = (idx+1) % len_ordered_points
		dist = math.hypot(ordered_points[idx][0] - ordered_points[next_idx][0], ordered_points[idx][1] - ordered_points[next_idx][1])
		G.add_edge(idx,next_idx,weight=dist)
		G.add_edge(idx,str(next_idx),weight=dist)
		E.add_edge(idx,next_idx,weight=0)
		E.add_edge(idx,str(next_idx),weight=0)

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

			# if average_distance <= MIN_E_DISTANCE and total_distance >= -MIN_E_DISTANCE and total_distance < 30:
			if average_distance <= MIN_E_DISTANCE:
				G.add_edge(idx,idx2,weight=base)
				G.add_edge(idx,str(idx2),weight=base)
				E.add_edge(idx,idx2,weight=average_distance)
				E.add_edge(idx,str(idx2),weight=average_distance)
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
	# print "BESTROUTE", best_route

	#######################################CODE 4/29/16
	NEIGHBOR_TRESHOLD = 6

	valid_nodes = []
	best_route = best_route[::-1]
	best_route.pop()

	for point in best_route:
		point = int(point)
		valid_nodes.append([point])
		for i in xrange(1, (NEIGHBOR_TRESHOLD / 2) + 1):
			valid_nodes[-1].append((point + i) % len_ordered_points)
			valid_nodes[-1].append((point - i) % len_ordered_points)
	# print "VALID NODESSS", valid_nodes
	simplified_E=nx.DiGraph()

	for node_idx in xrange(0, len(valid_nodes)):
		next_node = (node_idx + 1) % len(valid_nodes)
		for point in valid_nodes[node_idx]:
			for adj_point in valid_nodes[next_node]:

				curr_edge = E.get_edge_data(point, adj_point, False)

				if next_node != 0:
					next_node_name = str(next_node) + '_' + str(adj_point)
				else:
					next_node_name = adj_point

				if curr_edge != False:
					simplified_E.add_edge(str(node_idx) + '_' + str(point), next_node_name, weight = curr_edge['weight'])
				elif point == adj_point:
					simplified_E.add_edge(str(node_idx) + '_' + str(point), next_node_name, weight = 0)	

	SHORTEST_E = nx.floyd_warshall_predecessor_and_distance(simplified_E)
	num_nodes = len(valid_nodes)
	# print "VALIDNODES",valid_nodes[0]
	best_cost = "notset"
	for target in valid_nodes[0]:
		pointer = target
		target = '0_' + str(target)
		route = []
		route.append(pointer)
		route_cost = 0

		while pointer != target:
			try:
				route_cost += SHORTEST_E[1][target][pointer]
				pointer = SHORTEST_E[0][target][pointer]
			except KeyError:
				# print "BREAK!"
				break
			route.append(pointer)
		# print "target", target, "route", route, "len_route", len(route), num_nodes == len(route), best_cost
		if best_cost == "notset" or (best_cost > route_cost and num_nodes == len(route)):
			best_route = copy.deepcopy(route)
			best_cost = route_cost
			# print "CHANGE", best_route

	# print "BESTROUTEV2", best_route
	best_route = best_route[::-1]
	best_route.pop()

	footprint = []
	for point in best_route:
		footprint.append(list(ordered_points[int(point.split("_")[1])]))

	# print footprint, "HAHAHAHA"
	
	critical_points = copy.deepcopy(boundary_image)

	for point in footprint:
		critical_points[point[0], point[1]] = 5

	# print "JEJEJEJEJEJJEJEJEJE", MIN_E_DISTANCE

	adjusted_route = adjust_route_v2(np.array(footprint)) 	
	# adjusted_route = adjust_route(np.array(footprint),mask_BR, max_temp = CURR_MAX_TEMP) 		
	# print np.array(footprint)
	# print adjusted_route
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

	approx_image[approx_image>0] = 1
	filled = ndimage.binary_fill_holes(approx_image)
	filled = filled*1	
	filled[filled==1] = indexedObject[0] 
	
	test = copy.deepcopy(boundary_image)
	test[filled > 0] = 2
	test[boundary_image != 0] = 1

	t1=time.time()
	print "Finished processing index",indexedObject[0],"in",round(t1-t0,2),"s."		
	# return indexedObject[0],filled,indexedObject[2]
	# 
	

	return indexedObject[0],filled,indexedObject[2]

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

	print "Preparing labels"
	for index in indices:
		# print "Preparing",index
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

def nonParallel(labeledMask,numProcesses=7): # This is where the shit starts

	labeledMaskWidth = len(labeledMask)
	labeledMaskHeight = len(labeledMask[0])

	reducedPointsMask = copy.deepcopy(labeledMask)

	indices = np.unique(reducedPointsMask)
	indices = indices[1:]

	objects = []
	indexList = []
	slices2 = []
	results = []

	indices = [260]

	# print "Preparing labels"
	for index in indices:

		print "Preocessing index ",index
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
		
		indexedObject = (index,obj,islays[0]) 
	# print "Number of objects to be processed:", len(indexedObjects)

		result = regularizeBoundary(indexedObject)
		results.append(result)
	
	return results

# ========================= MAIN ========================= #

# labeledMask = io.imread("C:\\Users\\User\\Projects\\Phil-LiDAR\\Border Detection\\Input\\pt000071_merged.tif")

# reducedPointsMask = copy.deepcopy(labeledMask)

# indices = np.unique(reducedPointsMask)
# indices = indices[1:]

# #THE TAIL PROBLEM
# #1003

# #90 NOT 180 DEGREE PROBLEM
# #

# #LOCK PROBLEM
# #135

# #ROUGH CASES
# #845, 956

# #THE GOOD  GUYS
# #793, 869, 1050, 939,995 ,910, 223
# index = 223

# clone = copy.deepcopy(labeledMask)
# islays = ndimage.find_objects(clone==index)

# obj = clone[islays[0][0],islays[0][1]]
# obj[obj!=index] = 0
# obj = ndimage.binary_fill_holes(obj)
# obj = morphology.remove_small_objects(obj,5) 
# obj = obj*index

# print obj

# result = regularizeBoundary((index,obj,islays[0]))

# fig, axes = plt.subplots(ncols=3, figsize=(18, 10))
# ax0, ax1, ax2 = axes
# # ax0,ax1,ax2,ax3 = axes

# fig0 = ax0.imshow(result[0],interpolation="none",cmap=plt.cm.gray)
# fig1 = ax1.imshow(result[1],interpolation="none",cmap=plt.cm.gray)
# fig2 = ax2.imshow(result[2],interpolation="none",cmap=plt.cm.gray)

# plt.show()