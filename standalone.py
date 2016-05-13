import Masking as ma 
import PrepareInputs as pi 
import BoundaryRegularizationV2 as br
import json
from skimage import io
import subprocess
import time
import psutil


def getRecCores(maxCores, itr = 3, timeout = 1):
    ave_cpu = []
    recCores = 2

    for i in xrange(0,itr):
        time.sleep(timeout)
        ave_cpu.append(psutil.cpu_percent())

    # print ave_cpu
    ave_cpu_usage = sum(ave_cpu)/float(itr)

    # print "HEY",ave_cpu_usage

    if ave_cpu_usage <= 25:                                 #low cpu usage
        recCores = 6
    elif ave_cpu_usage <= 37.5:
        recCores = 5
    elif ave_cpu_usage <= 50:                                 #moderate cpu usage
        recCores = 4
    elif ave_cpu_usage <= 62.5:
        recCores = 3

    if recCores > maxCores:
        return maxCores
    else:
        return recCores

def main():

	 

     print "Preparing Inputs..."
     pi.prepareInputs()

     ndsm = io.imread("C:\\bertud_temp\\ndsm.tif")
     classified = io.imread("C:\\bertud_temp\\classified.tif")
     slope = io.imread("C:\\bertud_temp\\slope.tif")
     slopeslope = io.imread("C:\\bertud_temp\\slopeslope.tif")

     print "Generating Initial Mask..."
     veggieMask,initialMask = ma.generateInitialMask(ndsm,classified,slope,ndsmThreshold=3,slopeThreshold=60)

     print "Generating markers for Watershed segmentation..."

     initialMarkers = ma.generateInitialMarkers(slopeslope,veggieMask)

     print "Performing Watershed segmentation..."

     labeledMask = ma.watershed2(ndsm,initialMask,initialMarkers,veggieMask)

     print "Performing basic region merging..."

     mergedMask = ma.mergeRegionsBasicV2(labeledMask,mergeThreshold=0.10,iterations=10)

     print "Performing basic boundary regularization..."
     
     
     #if __name__ == '__main__':
     #	pieces = br.performBoundaryRegularizationV2(mergedMask,numProcesses=getRecCores(maxCores = 2))
     
     pieces = br.nonParallel(mergedMask)

     print "Creating final mask and saving output raster..."

     finalMask = ma.buildFinalMask(pieces,mergedMask)

main()