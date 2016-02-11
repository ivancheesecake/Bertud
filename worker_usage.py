# from __future__ import print_function
import os
import socket
import sys
from math import sqrt
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import psutil
import time
import pickle

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

if sys.version_info < (3, 0):
    range = xrange   # make sure to use the memory efficient range generator

#Loads the worker's info
WORKERINFO = pickle.load(open("config_worker.pickle", "rb"))
WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())

def main():
	#connects to the dispatcher
	dispatcher = Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@169.254.28.136")

	#Iterativly update the worker's cpu and ram usage to the dispatcher
	while True:
		dispatcher.updateWorkerUsage(WORKERINFO["id"], WORKERNAME, psutil.cpu_percent(), psutil.virtual_memory().percent)
		time.sleep(2)


if __name__ == "__main__":
    main()