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

NUMBER_OF_ITEMS = 40


def main():
    # print("\nThis program will calculate Prime Factorials of a bunch of random numbers.")
    print("The more workers you will start (on different cpus/cores/machines),")
    print("the faster you will get the complete list of results!\n")
    with Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@10.0.63.66") as dispatcher:
        placework(dispatcher)
        result = collectresults(dispatcher)
    printresults(result)


def placework(dispatcher):
    print("placing work items into dispatcher queue.")
    inputs = {}
    inputs["classified"] = io.imread('bertud_inputs\\pt000127_classified.tif')
    inputs["ndsm"] = io.imread('bertud_inputs\\pt000127_ndsm.tif')
    inputs["slope"] = io.imread('bertud_inputs\\pt000127_slope.tif')
    inputs["slopeslope"] = io.imread('bertud_inputs\\pt000127_slopeslope.tif')
    # output = np.zeros(buildings.shape,dtype=np.uint)
    # slices = ndimage.find_objects(buildings)
    # obj = copy.deepcopy(buildings[slices[199 - 1]])
    item = Workitem(1, inputs)
    dispatcher.putWork(item)


def collectresults(dispatcher):
    print("getting results from dispatcher queue.")
    # numbers = {}
    while True:
        try:
            item = dispatcher.getResult()
        except ValueError:
            print("di pa tapos")
        else:
            print("Got result from %s" % (item.processedBy))
            break

    # if dispatcher.resultQueueSize() > 0:
    #     print("there's still stuff in the dispatcher result queue, that is odd...")
    return item.result


def printresults(result):
    # fig, axes = plt.subplots(ncols=1, figsize=(18, 10))
    # ax0 = axes

    # # ax0,ax1,ax2,ax3 = axes


    # # fig0 = ax0.imshow(buildings,interpolation="none",cmap=plt.cm.gray)
    # # fig1 = ax1.imshow(output,interpolation="none",cmap=plt.cm.gray)
    # fig0 = ax0.imshow(result,interpolation="none",cmap=plt.cm.gray)
    # # fig1 = ax1.imshow(approx_image,interpolation="none",cmap=plt.cm.gray)
    # # fig2 = ax2.imshow(regularized_image,interpolation="none",cmap=plt.cm.gray)
    # # fig3 = ax3.imshow(tapal,interpolation="none",cmap=plt.cm.gray)
    # plt.show()
    io.imsave("bertud_output\\output.tif", result)

if __name__ == "__main__":
    main()
