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
import json


# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

if sys.version_info < (3, 0):
    range = xrange   # make sure to use the memory efficient range generator

#Loads the worker's info
# WORKERINFO = pickle.load(open("config_worker.pickle", "rb"))

def main():
	#connects to the dispatcher

	with open("config/slave_config.json","r") as f:
		configfile = f.read()

	config = json.loads(configfile)

	dispatcher = Pyro4.core.Proxy("PYRONAME:"+config["dispatcherNameServer"]+"@"+config["dispatcherIP"])

	#Iterativly update the worker's cpu and ram usage to the dispatcher
	while True:
		try:
			dispatcher.updateWorkerUsage(str(config["workerID"]), psutil.cpu_percent(), psutil.virtual_memory().percent)
			# For UI Testing lang
			# dispatcher.updateWorkerStatus('1', 1)

		except:
			while True:
                #Try to reconnect to dispatcher
				try:
					print("Dispatcher not found. Reconnecting...")
					dispatcher._pyroReconnect()
                #Can't connect -> Sleep then retry again
				except Exception:
					time.sleep(1)
                #Reconnecting succesful
				else:
					print("Connected to dispatcher.")
					break

		time.sleep(0.4)

if __name__ == "__main__":
    main()