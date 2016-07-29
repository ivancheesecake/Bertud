# Bertud Slave Standalone

from skimage import io
import Masking as ma
import BoundaryRegularizationV3 as br
import PrepareInputs as pi
import pickle
import time

def main():

	t0 = time.time()

	print "Preparing Inputs..."
	pi.prepareInputs()

	ndsm = io.imread("C:\\bertud_temp\\ndsm.tif")
	classified = io.imread("C:\\bertud_temp\\classified.tif")
	classified = classified[0:len(ndsm),0:len(ndsm[0])]
	slope = io.imread("C:\\bertud_temp\\slope.tif")
	numret = io.imread("C:\\bertud_temp\\numret.tif")

	print "Generating Initial Mask..."
	initialMask = ma.generateInitialMask(ndsm,classified,slope,numret)

	io.imsave("C:\\bertud_temp\\initialMask.tif",initialMask)


	pieces = br.performBoundaryRegularizationV2(initialMask,numProcesses=3)

	finalMask = ma.buildFinalMask(pieces,initialMask)

	io.imsave("C:\\bertud_temp\\finalMask.tif",finalMask)

	# pickle.dump(pieces,open("E:/BertudV2/pieces.pickle","wb"))

	t1 = time.time()

	print "Finished everything in ",round(t1-t0,2),"s."

if __name__ == "__main__":

	main()