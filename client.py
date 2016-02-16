from __future__ import with_statement
import random
import sys
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import matplotlib.pyplot as plt
import matplotlib
from skimage import io
import numpy as np
from scipy import ndimage
import copy

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

def main():
    #connect to dispatcher
    with Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@169.254.23.41") as dispatcher:
        placework(dispatcher)
        # collectresults(dispatcher)

#Function for placing work to dispatcher
def placework(dispatcher):
    print("placing work items into dispatcher queue.")

    #Read LAZ input file then send to dispatcher
    with open("E:\FeatureExtractionV4\lasprocessing\ground\pt000002.laz", "rb") as file:
        item = Workitem(1, file.read())                 #ID(FIRST PARAM) SHOULD BE UNIQUE -> CODE CODE CODE

    # inputs = {}
    # inputs["classified"] = io.imread('bertud_inputs\\pt000127_classified.tif')
    # inputs["ndsm"] = io.imread('bertud_inputs\\pt000127_ndsm.tif')
    # inputs["slope"] = io.imread('bertud_inputs\\pt000127_slope.tif')
    # inputs["slopeslope"] = io.imread('bertud_inputs\\pt000127_slopeslope.tif')
    # item = Workitem(1, inputs)                          #ID(FIRST PARAM) SHOULD BE UNIQUE -> CODE CODE CODE

    #put work to dispatcher
    dispatcher.putWork(item)

#Function for collecting result from dispatcher
# def collectresults(dispatcher):
#     print("getting results from dispatcher queue.")
#     #Loop for waiting for the result
#     while True:
#         #Check if the result is available
#         try:
#             item = dispatcher.getResult()
#         #If there are no results available
#         except ValueError:
#             print("di pa tapos")
#         #If there are available result
#         else:
#             print("Got result from %s" % (item.processedBy))
#             #Save the output to a file
#             io.imsave("bertud_output\\output.tif", item.result)
#             break

if __name__ == "__main__":
    main()
