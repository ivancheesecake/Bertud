import copy
import numpy as np
from scipy import ndimage
import time
from skimage.draw import circle_perimeter,line
from skimage.transform import rotate
from skimage.segmentation import find_boundaries
from skimage.morphology import opening, square
import networkx as nx
import math
import random


class Building(object):

	def __init__(self, initial_footprint, footprint_index, footprint_slice, FXN_min_e, FXN_angle_cost):
		self.FOOTPRINT_index_num = footprint_index
		self.FOOTPRINT_initial = initial_footprint
		self.FOOTPRINT_slice = footprint_slice
		self.FOOTPRINT_added_boundary = None
		self.FOOTPRINT_cleaned_opening = None
		self.FOOTPRINT_final = None
		self.POINTS_initial = None
		self.POINTS_ordered = None
		self.POINTS_critical = None
		self.POINTS_SA_adjusted = None
		self.POINTS_final = None
		self.FXN_min_e = FXN_min_e
		self.FXN_angle_cost = FXN_angle_cost
		self.processing_time = None

	def clean_footprint(self, OPENING_THRESH = 5):
		self.FOOTPRINT_cleaned_opening = opening(self.FOOTPRINT_added_boundary, square(OPENING_THRESH))

		labeled_image, num_of_labels = ndimage.measurements.label(self.FOOTPRINT_cleaned_opening, [[1,1,1],[1,1,1],[1,1,1]])
		
		if num_of_labels > 1:
			b_slices = ndimage.find_objects(labeled_image)
			area = []
			for idx,s in enumerate(b_slices):
				area.append(len(self.FOOTPRINT_cleaned_opening[self.FOOTPRINT_cleaned_opening[s] != 0]))
			self.FOOTPRINT_cleaned_opening[labeled_image != (area.index( max(area))) + 1] = 0


		# area = np.bincount(obj.flatten())[indexedObject[0]]
		return len(self.FOOTPRINT_cleaned_opening[self.FOOTPRINT_cleaned_opening!=0])

	def remove_deep_points(self, CIRCLE_RADIUS = 5, MINIMUM_BOUNDARY = 70):
		for point in self.POINTS_initial:
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
					# if original_image[line_points[0]][line_points[1]] != 0:
					if self.FOOTPRINT_cleaned_opening[line_points[0]][line_points[1]] != 0:
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
				# boundary_image[point[0]][point[1]] = 0							#TAMA BANG TANGGALIN?

				if (point[0],point[1]) in self.POINTS_ordered:  ## IDENTIFY KUNG BAKIT NAGKA-ERRROR, EXAMPLE pt000120_merged4.py obj 1301
					self.POINTS_ordered.remove((point[0],point[1]))
	
	def approximate_line_segments(self, TRAINING_MIN_AREA = 60, TRAINING_MAX_AREA = 20576, MAX_FAIL_COUNTER = 20, NEIGHBOR_TRESHOLD = 6):

		obj_area = len(self.FOOTPRINT_initial[self.FOOTPRINT_initial != 0])
		if obj_area < TRAINING_MIN_AREA:
			obj_area = TRAINING_MIN_AREA
		elif obj_area > TRAINING_MAX_AREA:
			obj_area = TRAINING_MAX_AREA

		MIN_E_DISTANCE = self.FXN_min_e(obj_area)

		G=nx.DiGraph()
		E=nx.DiGraph()
		len_ordered_points = len(self.POINTS_ordered)

		for idx in xrange(0,len_ordered_points):

			
			next_idx = (idx+1) % len_ordered_points
			dist = math.hypot(self.POINTS_ordered[idx][0] - self.POINTS_ordered[next_idx][0], self.POINTS_ordered[idx][1] - self.POINTS_ordered[next_idx][1])
			G.add_edge(idx,next_idx,weight=dist)
			G.add_edge(idx,str(next_idx),weight=dist)
			E.add_edge(idx,next_idx,weight=0)
			E.add_edge(idx,str(next_idx),weight=0)

			idx2 = (idx + 2) % len_ordered_points
			fail_counter = 0

			while((idx2 + 1) % len_ordered_points != idx and fail_counter < MAX_FAIL_COUNTER):  #?

				counter = 0
				average_distance = 0.0
				base   = math.hypot(self.POINTS_ordered[idx][0] - self.POINTS_ordered[idx2][0], self.POINTS_ordered[idx][1] - self.POINTS_ordered[idx2][1])
				idx3 = (idx + 1) % len_ordered_points

				while(idx2 != idx3): #?

					side_1 = math.hypot(self.POINTS_ordered[idx][0] - self.POINTS_ordered[idx3][0], self.POINTS_ordered[idx][1] - self.POINTS_ordered[idx3][1])
					side_2 = math.hypot(self.POINTS_ordered[idx2][0] - self.POINTS_ordered[idx3][0], self.POINTS_ordered[idx2][1] - self.POINTS_ordered[idx3][1])
					semi_perimeter = (side_1 + side_2 + base) / 2.0
					temp = semi_perimeter * (semi_perimeter - side_1) * (semi_perimeter - side_2) * (semi_perimeter - base)
					if temp < 0:
						temp = 0
					area   = math.sqrt(temp)
					height = (2.0 * area) / base
					average_distance += height
					counter += 1
					idx3 = (idx3 + 1) % len_ordered_points

				average_distance /= counter

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
		for target in xrange(0,len_ordered_points):
			pointer = str(target)
			route = []
			route.append(pointer)

			while pointer != target:
				pointer = F[0][target][pointer]
				route.append(pointer)
			
			if len(best_route) == 0 or len(best_route) > len(route):
				best_route = copy.deepcopy(route)

		valid_nodes = []
		best_route = best_route[::-1]
		best_route.pop()

		for point in best_route:
			point = int(point)
			valid_nodes.append([point])
			for i in xrange(1, (NEIGHBOR_TRESHOLD / 2) + 1):
				valid_nodes[-1].append((point + i) % len_ordered_points)
				valid_nodes[-1].append((point - i) % len_ordered_points)

		len_valid_nodes = len(valid_nodes)
		simplified_E=nx.DiGraph()

		for node_idx in xrange(0, len_valid_nodes):
			next_node = (node_idx + 1) % len_valid_nodes
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
		best_cost = "notset"
		best_route = []
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
					break
				route.append(pointer)

			if len(route) == (len_valid_nodes + 1) and (best_cost == "notset" or best_cost > route_cost):
				best_route = copy.deepcopy(route)
				best_cost = route_cost

		best_route = best_route[::-1]
		best_route.pop()

		critical_points = []
		for point in best_route:
			critical_points.append(list(self.POINTS_ordered[int(point.split("_")[1])]))
		critical_points = np.array(critical_points)

		return critical_points

	def adjust_footprint(self, MAX_ITR_FOR_ADJUSTING = 2):
		final_route = copy.deepcopy(self.POINTS_SA_adjusted)
		adjust_itr = 1
		while adjust_itr <= MAX_ITR_FOR_ADJUSTING:
			adjusted_sides = self.adjust_sides(final_route)
			adjusted_rotation = self.adjust_rotation(adjusted_sides)
			if np.array_equal(final_route,adjusted_rotation):
				break
			else:
				final_route = copy.deepcopy(adjusted_rotation)
				adjust_itr += 1

		return final_route

	def DFS_ordering(self, G, current_node, stack, thresh_num_nodes, itr, MAX_DFS_ITR = 5000000):
		for a, b, dct in sorted(G.edges(current_node,data = True), key = lambda (a, b, dct): dct['weight']):
			if b not in stack:
				stack.append(b)
				if (stack[0],stack[-1]) in G.edges(stack[0]) and len(stack) > thresh_num_nodes:
					break
				elif itr >= MAX_DFS_ITR:
					break
				stack, FLAG_finished, itr = self.DFS_ordering(G, b, stack, thresh_num_nodes, itr + 1)
				if FLAG_finished or itr >= MAX_DFS_ITR:
					break

		if (stack[0],stack[-1]) in G.edges(stack[0]) and len(stack) > thresh_num_nodes:
			return stack, True, itr
		elif len(stack) <= 1 or itr >= MAX_DFS_ITR:
			return stack, False, itr
		else:
			stack.pop()
			return stack, False, itr

	def neighbor_tracing(self, DIST_BET_PTS = 1.5):
		num_points = len(self.POINTS_initial)
		thresh_num_points = round(num_points * 0.6)
		FLAG_points_not_ordered = True
		
		while FLAG_points_not_ordered:
			indexes = range(0, num_points)

			G=nx.Graph()
			for index_1 in xrange(0, num_points):
				for index_2 in xrange(0, num_points):
					if index_1 != index_2:
						dist = np.linalg.norm(np.array(self.POINTS_initial[index_1]) - np.array(self.POINTS_initial[index_2]))
						if dist <= DIST_BET_PTS:
							G.add_edge(index_1,index_2,weight=dist)
			while len(indexes) > 0:
				seed_point = random.choice(indexes)
				indexes.remove(seed_point)
				ordered_indexes, FLAG_finished, itr = self.DFS_ordering(G, seed_point, [seed_point], thresh_num_points, itr = 1)
				if FLAG_finished:
					FLAG_points_not_ordered = False
					break

			DIST_BET_PTS += 1.0

		ordered_points = []
		for point in ordered_indexes:
			ordered_points.append(self.POINTS_initial[point])

		return ordered_points

	def get_angle(self, PoI, index, footprint):

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

	def form_mask_BR_v2(self, start_temp, max_temp, temp_rate):
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

	def simulated_annealing_solution_cost(self, angles, distances, temperature):

		cost_angles = 0.0
		cost_distances = 0.0

		for idx, angle in enumerate(angles):
			cost_angles += math.log10(self.FXN_angle_cost(angle))
			cost_distances += distances[idx] ** 2.0

		return (cost_angles) + ((1.0 / (2.0 * (temperature ** 2.0))) * cost_distances)

	def simulated_annealing_acceptance_probability(self, old_cost, new_cost, T):

		return math.e ** ((old_cost - new_cost) / T)

	def simulated_annealing_regularization(self, GAUSS_MULTIPLIER = 8.0, ITR_PER_TEMP = 400, INIT_TEMP = 0.125, MAX_TEMP = 1.0, RATE_TEMP = 0.0625, MAX_DIST = 5.0):

		temp = INIT_TEMP

		best_solution = {}
		best_solution["footprint"] = self.POINTS_critical
		best_solution["angles"] = []
		best_solution["distances"] = []

		# angles = []
		# distances = []

		for idx, point in enumerate(self.POINTS_critical):
			best_solution["angles"].append(self.get_angle(point, idx, self.POINTS_critical))
			best_solution["distances"].append(0.0)

		num_points = len(best_solution["distances"])

		
		# best_solution["cost"] = compute_solution_cost(angles, distances, temp * GAUSS_MULTIPLIER, cost_spline)
		accepted_solution = copy.deepcopy(best_solution)
		# new_solution = copy.deepcopy(best_solution)

		#generate mask for neighbor
		neighbors = self.form_mask_BR_v2(MAX_DIST, MAX_DIST, RATE_TEMP)
		neighbors_distances = neighbors[neighbors["temp"] == MAX_DIST]["dist"][0]
		neighbors_locations = neighbors[neighbors["temp"] == MAX_DIST]["mask"][0]

		while temp <= MAX_TEMP:

			#?
			accepted_solution["cost"] = self.simulated_annealing_solution_cost(accepted_solution["angles"], accepted_solution["distances"], GAUSS_MULTIPLIER)
			best_solution["cost"] = self.simulated_annealing_solution_cost(best_solution["angles"], best_solution["distances"], GAUSS_MULTIPLIER)

			for idx in xrange(0, ITR_PER_TEMP):

				#randomize distances for each points
				random_distances = []
				for idx2 in xrange(0, num_points):
					dist = abs(np.random.normal(scale = math.sqrt(temp * GAUSS_MULTIPLIER)))

					#bound dist to MAX_DIST
					if dist > MAX_DIST:
						dist = MAX_DIST

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
					new_solution["footprint"][idx2] = self.POINTS_critical[idx2] + neighbors_locations[rand_pros_idx]
					new_solution["distances"][idx2] = neighbors_distances[rand_pros_idx]		#update distance
					
					#OPTIMIZE - wag na lahat iupdate no need
					for idx3, point in enumerate(new_solution["footprint"]):
						new_solution["angles"][idx3] = self.get_angle(point, idx3, new_solution["footprint"])

					new_solution["cost"] = self.simulated_annealing_solution_cost(new_solution["angles"], new_solution["distances"], GAUSS_MULTIPLIER)
					ap = self.simulated_annealing_acceptance_probability(accepted_solution["cost"], new_solution["cost"], temp)

					#if acceptance probability > random number, accept the solution
					if ap > random.random():
						prospect_solution["footprint"][idx2] = new_solution["footprint"][idx2]
						prospect_solution["distances"][idx2] = new_solution["distances"][idx2]
				
				for idx2, point in enumerate(prospect_solution["footprint"]):
					prospect_solution["angles"][idx2] = self.get_angle(point, idx2, prospect_solution["footprint"])

				prospect_solution["cost"] = self.simulated_annealing_solution_cost(prospect_solution["angles"], prospect_solution["distances"], GAUSS_MULTIPLIER)
				ap = self.simulated_annealing_acceptance_probability(accepted_solution["cost"], prospect_solution["cost"], temp)
				
				if ap > random.random():
					old_cost = accepted_solution["cost"]
					accepted_solution = copy.deepcopy(prospect_solution)
					if accepted_solution["cost"] < best_solution["cost"]:
						best_solution = copy.deepcopy(accepted_solution)


			#update temp
			temp += RATE_TEMP

		return best_solution["footprint"]	

	def remove_item_in_numpyArray(self, nparray, item_to_be_remove, GIVEN_AXIS = 1):	#from http://stackoverflow.com/questions/10120008/remove-one-value-from-a-numpy-array
		# to_be_removed = item_to_be_remove  # Can be any row values: [5, 6], etc.
		other_rows = (nparray != item_to_be_remove).any(axis=GIVEN_AXIS)  # Rows that have at least one element that differs
		n_other_rows = nparray[other_rows]  # New array with rows equal to to_be_removed removed.

		return n_other_rows

	def footprint_fitness_error(self, points):
		temp_footprint = np.zeros(self.FOOTPRINT_added_boundary.shape, dtype=np.uint8)
		len_points = len(points)

		for idx1 in xrange(0, len_points):
			rr,cc = line(points[idx1][0], points[idx1][1], points[idx1-1][0],points[idx1-1][1])
			temp_footprint[rr,cc] = 1

		temp_footprint = ndimage.binary_fill_holes(temp_footprint)
		temp_footprint = temp_footprint * 1

		rr,cc = np.nonzero(temp_footprint)
		
		#RATIO OF ZEROS AND ONES SA LOOB
		zero_counter = 0.0
		nonzero_counter = 0.0
		for point in zip(rr,cc):
			if self.FOOTPRINT_added_boundary[point[0]][point[1]] == 0:
				zero_counter += 1.0
			else:
				nonzero_counter += 1.0

		footprint_copy = copy.deepcopy(self.FOOTPRINT_added_boundary)
		footprint_copy[rr,cc] = 0

		nonzero = len(footprint_copy[footprint_copy != 0])
		total = (len(footprint_copy[footprint_copy == 0]) + nonzero) * 1.0

		return (nonzero / total) + (zero_counter / (nonzero_counter + zero_counter))

	def uniquify_points(self, points, ANGLE_TRESH = 170):
		new_points = []
		last_point = "notset"

		for idx, point in enumerate(points):
			if np.array_equal(point, last_point):
				continue

			angle = self.get_angle(point, idx, points)
			if angle < ANGLE_TRESH:
				new_points.append(point)

			last_point = copy.deepcopy(point)

		return np.array(new_points)

	def get_line_orientation(self, points, MOVE_BY):

		line_operations = []
		len_points = len(points)

		new_footprint = np.zeros(self.FOOTPRINT_added_boundary.shape, dtype=np.uint8)
		for point in points:
			new_footprint[point[0]][point[1]] = 1

		for idx1 in xrange(0, len_points):
			rr,cc = line(points[idx1][0], points[idx1][1], points[idx1-1][0],points[idx1-1][1])
			new_footprint[rr,cc] = 1

		new_footprint = ndimage.binary_fill_holes(new_footprint)
		new_footprint = new_footprint * 1


		for idx1 in xrange(0, len_points):
			A = copy.deepcopy(points[idx1][::-1])
			B = copy.deepcopy(points[idx1 - 1][::-1])
			C = copy.deepcopy(points[(idx1 + 1) % len_points][::-1])
			D = copy.deepcopy(points[(idx1 + 2) % len_points][::-1])

			A[1] *= -1
			B[1] *= -1
			C[1] *= -1
			D[1] *= -1

			#may be buggy
			AC_midpoint_x = (A[0] + C[0]) / 2.0
			AC_midpoint_y = (A[1] + C[1]) / 2.0

			AM_dist = np.linalg.norm(A - np.array([AC_midpoint_x, AC_midpoint_y]))
			CM_dist = np.linalg.norm(C - np.array([AC_midpoint_x, AC_midpoint_y]))

			if B[0] == A[0]:
				AB_slope = "undefined"
			else:
				AB_slope = (B[1] - A[1] * 1.0) / (B[0] - A[0])

			if D[0] == C[0]:
				CD_slope = "undefined"
			else:
				CD_slope = (D[1] - C[1] * 1.0) / (D[0] - C[0])

			#bawas dapat - minus = bawas
			A_new_x = A[0] - (A[0] - B[0]) / np.linalg.norm(A - B) * (MOVE_BY + 2)
			A_new_y = A[1] - (A[1] - B[1]) / np.linalg.norm(A - B) * (MOVE_BY + 2)

			C_new_x = C[0] - (C[0] - D[0]) / np.linalg.norm(C - D) * (MOVE_BY + 2)
			C_new_y = C[1] - (C[1] - D[1]) / np.linalg.norm(C - D) * (MOVE_BY + 2)

			if AB_slope == "undefined":
				AB_testpoint_x1 = AC_midpoint_x
				AB_testpoint_y1 = AC_midpoint_y - (MOVE_BY + 2)

				AB_testpoint_x2 = AC_midpoint_x
				AB_testpoint_y2 = AC_midpoint_y + (MOVE_BY + 2)
			else:
				AB_testpoint_x1 = AC_midpoint_x - ((MOVE_BY + 2) / math.sqrt((AB_slope ** 2) + 1))
				AB_testpoint_y1 = AC_midpoint_y - (AB_slope * (AC_midpoint_x - AB_testpoint_x1))

				AB_testpoint_x2 = AC_midpoint_x - ((MOVE_BY + 2) / -(math.sqrt((AB_slope ** 2) + 1)))
				AB_testpoint_y2 = AC_midpoint_y - (AB_slope * (AC_midpoint_x - AB_testpoint_x2))

			AB_dist1 = np.linalg.norm(np.array([A_new_x, A_new_y]) - np.array([AB_testpoint_x1, AB_testpoint_y1]))
			AB_dist2 = np.linalg.norm(np.array([A_new_x, A_new_y]) - np.array([AB_testpoint_x2, AB_testpoint_y2]))

			if CD_slope == "undefined":
				CD_testpoint_x1 = AC_midpoint_x
				CD_testpoint_y1 = AC_midpoint_y - (MOVE_BY + 2)

				CD_testpoint_x2 = AC_midpoint_x
				CD_testpoint_y2 = AC_midpoint_y + (MOVE_BY + 2)
			else:
				CD_testpoint_x1 = AC_midpoint_x - ((MOVE_BY + 2) / math.sqrt((CD_slope ** 2) + 1))
				CD_testpoint_y1 = AC_midpoint_y - (CD_slope * (AC_midpoint_x - CD_testpoint_x1))

				CD_testpoint_x2 = AC_midpoint_x - ((MOVE_BY + 2) / -(math.sqrt((CD_slope ** 2) + 1)))
				CD_testpoint_y2 = AC_midpoint_y - (CD_slope * (AC_midpoint_x - CD_testpoint_x2))

			CD_dist1 = np.linalg.norm(np.array([C_new_x, C_new_y]) - np.array([CD_testpoint_x1, CD_testpoint_y1]))
			CD_dist2 = np.linalg.norm(np.array([C_new_x, C_new_y]) - np.array([CD_testpoint_x2, CD_testpoint_y2]))

			if abs(AM_dist - AB_dist1) < abs(AM_dist - AB_dist2):
				AB_testpoint_x = int(round(AB_testpoint_x1))
				AB_testpoint_y = int(round(AB_testpoint_y1))
			else:
				AB_testpoint_x = int(round(AB_testpoint_x2))
				AB_testpoint_y = int(round(AB_testpoint_y2))

			if abs(CM_dist - CD_dist1) < abs(AM_dist - CD_dist2):
				CD_testpoint_x = int(round(CD_testpoint_x1))
				CD_testpoint_y = int(round(CD_testpoint_y1))
			else:
				CD_testpoint_x = int(round(CD_testpoint_x2))
				CD_testpoint_y = int(round(CD_testpoint_y2))

			if new_footprint[(-AB_testpoint_y,AB_testpoint_x)] == 0:		#nasa labas
				line_operations.append(["plus"])
			else:
				line_operations.append(["minus"])

			if new_footprint[(-CD_testpoint_y,CD_testpoint_x)] == 0:
				line_operations[idx1].append("plus")
			else:
				line_operations[idx1].append("minus")

		return line_operations, new_footprint

	def adjust_sides(self, points, MOVE_BY = 1, NEIGHBOR_THRESH = 0.4, MAX_ITERATION = 15):

		new_points = self.uniquify_points(points)
		FLAG_change = True
		len_points = len(new_points)

		line_operations, new_footprint = self.get_line_orientation(new_points, MOVE_BY)

		ITRs = 0
		while FLAG_change and ITRs < MAX_ITERATION:
			ITRs += 1
			FLAG_change = False
			for idx1 in xrange(0, len_points):
				A = copy.deepcopy(new_points[idx1][::-1])
				B = copy.deepcopy(new_points[idx1 - 1][::-1])
				C = copy.deepcopy(new_points[(idx1 + 1) % len_points][::-1])
				D = copy.deepcopy(new_points[(idx1 + 2) % len_points][::-1])

				A[1] *= -1
				B[1] *= -1
				C[1] *= -1
				D[1] *= -1

				#SUBUKANG MAGBAWAS
				
				rr,cc = line(A[0], -A[1], C[0], -C[1])
				length_line = len(rr) * 1.0
				line_completeness = (len(self.FOOTPRINT_added_boundary[cc,rr][self.FOOTPRINT_added_boundary[cc,rr] != 0]) / length_line)

				if line_completeness < NEIGHBOR_THRESH:	#bawas

					if line_operations[idx1][0] == 'minus':			#check operation for bawas line AB
						pros_point1_x = int(round(A[0] - (A[0] - B[0]) / np.linalg.norm(A - B) * MOVE_BY));
						pros_point1_y = int(round(A[1] - (A[1] - B[1]) / np.linalg.norm(A - B) * MOVE_BY));
					else:
						pros_point1_x = int(round(A[0] + (A[0] - B[0]) / np.linalg.norm(A - B) * MOVE_BY));
						pros_point1_y = int(round(A[1] + (A[1] - B[1]) / np.linalg.norm(A - B) * MOVE_BY));

					if line_operations[idx1][1] == 'minus':			#check operation for bawas line CD
						pros_point2_x = int(round(C[0] - (C[0] - D[0]) / np.linalg.norm(C - D) * MOVE_BY));
						pros_point2_y = int(round(C[1] - (C[1] - D[1]) / np.linalg.norm(C - D) * MOVE_BY));
					else:
						pros_point2_x = int(round(C[0] + (C[0] - D[0]) / np.linalg.norm(C - D) * MOVE_BY));
						pros_point2_y = int(round(C[1] + (C[1] - D[1]) / np.linalg.norm(C - D) * MOVE_BY));

					rr,cc = line(pros_point1_x, -pros_point1_y, pros_point2_x, -pros_point2_y)
					length_newline = len(rr) * 1.0
					newline_completeness = (len(self.FOOTPRINT_added_boundary[cc,rr][self.FOOTPRINT_added_boundary[cc,rr] != 0]) / length_newline)

					if newline_completeness >= line_completeness:			#accept new points for A and C
						FLAG_change = True
						new_points[idx1] = np.array([pros_point1_x, -pros_point1_y])[::-1]						#UPDATE A
						new_points[(idx1 + 1) % len_points] = np.array([pros_point2_x, -pros_point2_y])[::-1]	#UPDATE C

						FLAG_less_points = False
						if np.array_equal(B,np.array([pros_point1_x, pros_point1_y])):						#compare new A and B
							FLAG_less_points = True
							new_points = self.remove_item_in_numpyArray(new_points, np.array([pros_point1_x, -pros_point1_y])[::-1])
						if np.array_equal(D,np.array([pros_point2_x, pros_point2_y])):						#compare new C and D
							FLAG_less_points = True
							new_points = self.remove_item_in_numpyArray(new_points, np.array([pros_point2_x, -pros_point2_y])[::-1])
						if FLAG_less_points:
							line_operations, new_footprint = self.get_line_orientation(new_points, MOVE_BY)
							len_points = len(new_points)
							break

					continue

				if line_operations[idx1][0] == 'minus':			#check operation for dagdag line AB
					pros_point1_x = int(round(A[0] + (A[0] - B[0]) / np.linalg.norm(A - B) * MOVE_BY));
					pros_point1_y = int(round(A[1] + (A[1] - B[1]) / np.linalg.norm(A - B) * MOVE_BY));
				else:
					pros_point1_x = int(round(A[0] - (A[0] - B[0]) / np.linalg.norm(A - B) * MOVE_BY));
					pros_point1_y = int(round(A[1] - (A[1] - B[1]) / np.linalg.norm(A - B) * MOVE_BY));

				if line_operations[idx1][1] == 'minus':			#check operation for dagdag line CD
					pros_point2_x = int(round(C[0] + (C[0] - D[0]) / np.linalg.norm(C - D) * MOVE_BY));
					pros_point2_y = int(round(C[1] + (C[1] - D[1]) / np.linalg.norm(C - D) * MOVE_BY));
				else:
					pros_point2_x = int(round(C[0] - (C[0] - D[0]) / np.linalg.norm(C - D) * MOVE_BY));
					pros_point2_y = int(round(C[1] - (C[1] - D[1]) / np.linalg.norm(C - D) * MOVE_BY));

				rr,cc = line(pros_point1_x, -pros_point1_y, pros_point2_x, -pros_point2_y)
				length_newline = len(rr) * 1.0
				newline_completeness = (len(self.FOOTPRINT_added_boundary[cc,rr][self.FOOTPRINT_added_boundary[cc,rr] != 0]) / length_newline)

				if newline_completeness >= NEIGHBOR_THRESH:
					FLAG_change = True
					new_points[idx1] = np.array([pros_point1_x, -pros_point1_y])[::-1]						#UPDATE A
					new_points[(idx1 + 1) % len_points] = np.array([pros_point2_x, -pros_point2_y])[::-1]	#UPDATE C

					FLAG_less_points = False
					if np.array_equal(B,np.array([pros_point1_x, pros_point1_y])):						#compare new A and B
						FLAG_less_points = True
						new_points = self.remove_item_in_numpyArray(new_points, np.array([pros_point1_x, -pros_point1_y])[::-1])
					if np.array_equal(D,np.array([pros_point2_x, pros_point2_y])):						#compare new C and D
						FLAG_less_points = True
						new_points = self.remove_item_in_numpyArray(new_points, np.array([pros_point2_x, -pros_point2_y])[::-1])
					if FLAG_less_points:
						line_operations, new_footprint = self.get_line_orientation(new_points, MOVE_BY)
						len_points = len(new_points)
						break

		return new_points

	def adjust_rotation(self, points, MAX_ROTATION = 15):
	
		points = self.uniquify_points(points)
		new_footprint = np.zeros(self.FOOTPRINT_added_boundary.shape, dtype=np.uint8)
		len_points = len(points)

		for idx in xrange(0, len_points):
			new_footprint[points[idx][0]][points[idx][1]] = idx + 2

		points_x = points[:,0]
		points_y = points[:,1]
		center_x = (max(points_x) + min(points_x)) / 2.0
		center_y = (max(points_y) + min(points_y)) / 2.0
		footprint_center = (int(round(center_x)), int(round(center_y)))
		
		best_error = self.footprint_fitness_error(points)
		best_points = copy.deepcopy(points)

		rotation = 1
		while rotation <= MAX_ROTATION:
			#ROTATE COUNTER
			rotated_footprint = rotate(new_footprint, rotation, resize=False, center = footprint_center,preserve_range=True, order= 0)

			rr,cc = np.nonzero(rotated_footprint)

			if len_points == len(rotated_footprint[rr,cc]) and len_points == len(np.unique(rotated_footprint[rr,cc])):
				new_points = copy.deepcopy(points)
				for idx1, idx2 in enumerate(rotated_footprint[rr,cc]):
					new_points[idx2 - 2] = np.array([rr[idx1], cc[idx1]])

				FLAG_has_unique_points = True
				for idx,point in enumerate(new_points):
					if np.array_equal(point, best_points[idx]):
					# if np.array_equal(point, points[idx]):
						FLAG_has_unique_points = False
						break

				new_error = self.footprint_fitness_error(new_points)

				#found better points
				if new_error < best_error and FLAG_has_unique_points:
					best_error = new_error
					best_points = copy.deepcopy(new_points)

			#ROTATE CLOCKWISE
			rotated_footprint = rotate(new_footprint, 360 - rotation, resize=False, center = footprint_center,preserve_range=True, order= 0)
			rr,cc = np.nonzero(rotated_footprint)

			if len_points == len(rotated_footprint[rr,cc]) and len_points == len(np.unique(rotated_footprint[rr,cc])):
				new_points = copy.deepcopy(points)
				for idx1, idx2 in enumerate(rotated_footprint[rr,cc]):
					new_points[idx2 - 2] = np.array([rr[idx1], cc[idx1]])

				FLAG_has_unique_points = True
				for idx,point in enumerate(new_points):
					if np.array_equal(point, best_points[idx]):
					# if np.array_equal(point, points[idx]):
						FLAG_has_unique_points = False
						break

				new_error = self.footprint_fitness_error(new_points)

				if new_error < best_error and FLAG_has_unique_points:
					best_error = new_error
					best_points = copy.deepcopy(new_points)

			rotation += 1

		return best_points

	def regularizeBoundary(self, CIRCLE_RADIUS = 5, MIN_FOOTPRINT_AREA = 10):

		t0 = time.time()
		obj = self.FOOTPRINT_initial

		obj_length = obj.shape

		self.FOOTPRINT_added_boundary = np.zeros((obj_length[0]+CIRCLE_RADIUS*2,obj_length[1]+CIRCLE_RADIUS*2),dtype=np.uint)
		self.FOOTPRINT_added_boundary[CIRCLE_RADIUS:obj_length[0]+CIRCLE_RADIUS,CIRCLE_RADIUS:obj_length[1]+CIRCLE_RADIUS] = obj

		area = self.clean_footprint()

		if area < MIN_FOOTPRINT_AREA:

			zeros = np.zeros(self.FOOTPRINT_added_boundary.shape,dtype=np.uint8)
			t1=time.time()
			self.processing_time = round(t1-t0,2)
			print "Finished processing index",self.FOOTPRINT_index_num,"in",self.processing_time,"s."

			return self.FOOTPRINT_index_num, zeros, self.FOOTPRINT_slice

		boundary_image = find_boundaries(self.FOOTPRINT_cleaned_opening, mode='inner').astype(np.uint8) #value = 1

		nonzero_x, nonzero_y = np.nonzero(boundary_image)
		self.POINTS_initial = zip(nonzero_x, nonzero_y)

		self.POINTS_ordered = self.neighbor_tracing()
		self.remove_deep_points()
		
		self.POINTS_critical = self.approximate_line_segments()

		self.POINTS_SA_adjusted = self.simulated_annealing_regularization() 	
		
		try:
			self.POINTS_final = self.adjust_footprint()
		except:
			print "Something went terribly wrong. Sht. I was working on index ", self.FOOTPRINT_index_num
			self.POINTS_final = copy.deepcopy(self.POINTS_SA_adjusted)

		self.FOOTPRINT_final = np.zeros(boundary_image.shape, dtype=np.uint8)

		for idx in xrange(0, len(self.POINTS_final)):
			rr, cc = line(self.POINTS_final[idx][0], self.POINTS_final[idx][1], self.POINTS_final[idx-1][0], self.POINTS_final[idx-1][1])
			self.FOOTPRINT_final[rr,cc] = 1

		self.FOOTPRINT_final = ndimage.binary_fill_holes(self.FOOTPRINT_final)
		self.FOOTPRINT_final = self.FOOTPRINT_final * self.FOOTPRINT_index_num

		t1=time.time()
		self.processing_time = round(t1-t0,2)
		print "Finished processing index",self.FOOTPRINT_index_num,"in",self.processing_time,"s."		
	
		return self.FOOTPRINT_index_num, self.FOOTPRINT_final, self.FOOTPRINT_slice