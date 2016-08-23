from skimage import io, morphology
# import BoundaryRegularizationV2 as br
import copy
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
import time
import cmath
# from scipy.interpolate import interp1d
from scipy.misc import derivative
import matplotlib.pyplot as plt
import matplotlib
from skimage.draw import circle_perimeter,line
from skimage.transform import rotate
from skimage.segmentation import find_boundaries
from skimage.morphology import opening, square
import networkx as nx
import math
import random
import pickle
import multiprocessing as mp
from Building import Building

# def sendLogs(dispatcher, worker_id, level, msg):
#     try:
#         dispatcher.saveLogs(worker_id, level, msg)
#     except:
#         while True:
#             #Try to reconnect to dispatcher
#             try:
#                 print("Dispatcher not found. Reconnecting...")
#                 dispatcher._pyroReconnect()
#             #Can't connect -> Sleep then retry again
#             except Exception:
#                 time.sleep(1)
#             #Reconnecting succesful
#             else:
#                 dispatcher.saveLogs(worker_id, level, msg)
#                 print("Connected to dispatcher.")
#                 break

def start_building_regularization(building):
	# building = args[0]
	# dispatcher = args[1]
	# worker_id = args[2]
	results, logs = building.regularizeBoundary()

	if len(logs) > 0:
		#pickle building
		pickle.dump( building, open( building.PICKLE_filename, "wb" ) )

		# for log in logs:
		# 	log_level = log[0]
		# 	log_msg = log[1]
		# 	sendLogs(dispatcher, worker_id, log_level, log_msg)

	return results, logs
	# return building.regularizeBoundary()

def performBoundaryRegularizationV2(labeledMask,laz_location, pickle_folder,numProcesses=7): # This is where the shit starts

	labeledMaskWidth = len(labeledMask)
	labeledMaskHeight = len(labeledMask[0])

	reducedPointsMask = copy.deepcopy(labeledMask)

	indices = np.unique(reducedPointsMask)
	indices = indices[1:]

	# objects = []
	# indexList = []
	# slices2 = []
	results = []

	buildings = []

	# lin_area = [60,86,113,137,140,146,152,155,158,176,183,187,191,194,198,202,209,221,231,240,247,254,265,280,289,290,293,294,299,307,317,332,344,369,386,398,415,424,446,256,472,485,517,532,571,590,611,634,671,689,713,722,755,781,796,893,938,970,1004,1050,1050,1107,1114,1153,1164,1226,1518,1598,1762,1830,1875,1985,2045,2212,2574,2829,2895,3038,3610,4299,5088,5261,5312,5961,10616,12586,20576]
	# lin_min_e = [0.4,0.4,0.4,0.4,0.6,0.4,0.425,0.5,0.425,0.4,0.475,0.5,0.475,0.475,0.5,0.6,0.625,0.7,0.6,0.6,0.6,0.725,0.725,0.7,0.7,0.7,0.6,0.6,0.7,0.7,0.75,0.75,0.75,0.775,0.76,0.75,0.8,0.775,0.7,0.725,0.725,0.8,0.83,0.805,0.82,0.8,0.85,0.85,0.9,0.87,0.9,0.9,0.9,0.92,1.0,1.0,1.0,0.95,1.0,0.9,0.95,1.0,1.0,1.0,1.0,1.0,0.9,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0]
	# angle_x = [0,20,45,75,90,105,120,135,150,165,180]
	# penalty_y = [1.1,1.0,0.6,0.7,0.1,0.7,0.6,0.5,0.6,0.5,0.1]

	# FXN_angle_cost = interp1d(angle_x, penalty_y, kind='cubic')
	# FXN_min_e = interp1d(lin_area, lin_min_e)

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

		area = np.bincount(obj.flatten())[index]
		
		# print "Index: ", index, "Area: ", area
		
		areaThresh  = 50000

		if area < areaThresh:

			print "Pasok! Index: ", index, "Area: ", area

			# objects.append(obj)
			# indexList.append(index)
			# slices2.append(islays[0])

			# buildings.append(Building(obj, index, islays[0], FXN_min_e, FXN_angle_cost))
			
			buildings.append(Building(obj, index, islays[0], laz_location, pickle_folder))
		

	# indexedObjects = zip(indexList,objects,slices2) 
	# print "Number of objects to be processed:", len(indexedObjects)
	print "Number of objects to be processed:", len(buildings)

	if len(buildings) == 0:
	# if len(indexedObjects) == 0:
		return [], []

	pool = mp.Pool(numProcesses)
	# results = pool.map(regularizeBoundary,indexedObjects)
	results = pool.map(start_building_regularization,buildings)
	pool.close()
	pool.join()

	pieces = []
	all_logs = []
	for result in results:
		pieces.append(result[0])
		all_logs += result[1]

	# return results
	return pieces, all_logs

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

	# indices = [260]

	# print "Preparing labels"
	for index in indices:

		print "Preprocessing index ",index
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
		
		area = np.bincount(obj.flatten())[index]
		
		print "Index: ", index, "Area: ", area

		areaThresh  = 50000

		if area >= areaThresh:
			continue

		objects.append(obj)
		indexList.append(index)
		slices2.append(islays[0])
	

		indexedObject = (index,obj,islays[0]) 
	# print "Number of objects to be processed:", len(indexedObjects)

		result = regularizeBoundary(indexedObject)
		results.append(result)
	
	return results
