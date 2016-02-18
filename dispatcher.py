# from __future__ import print_function
try:
    import queue
except ImportError:
    import Queue as queue
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import copy
import sys
import pickle

ip = sys.argv[1]

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)


class DispatcherQueue(object):
    def __init__(self):
        self.Qwaiting = pickle.load( open( "config/work_queue.p", "rb" ) )
        self.Qprocessing = {}
        self.Qfinished = {}
                            #id  #attributes
        self.worker_info = {'1':{'cpu':-1,'ram':-1,'status':"0"}} # Create 10 of these next time


    #function that receives work from client
    def putWork(self, item_id, item):
        self.Qwaiting[item_id] = item                   #ASSUMING NA DICT THEN FROM SERVER SI ITEM
        self.updateWorkFile()

    #function that updates the work_queue file
    def updateWorkFile(self):
        clone = self.Qwaiting
        clone.update(self.Qprocessing)

        pickle.dump(clone, open( "config/work_queue.p", "wb" ))

    #slaves use this to check for available works
    def getWork(self, timeout=5):
        try:
            return self.workqueue.get(block=True, timeout=timeout)
        except queue.Empty:
            raise ValueError("no items in queue")

    #function that receives results from slaves
    def putResult(self, item):
        self.resultqueue.put(item)

    #clients use this to check for available results
    def getResult(self, timeout=5):
        try:
            return self.resultqueue.get(block=True, timeout=timeout)
        except queue.Empty:
            raise ValueError("no result available")

    def workQueueSize(self):
        return self.workqueue.qsize()

    def resultQueueSize(self):
        return self.resultqueue.qsize()

    #updates the state of utilization of slaves
    def updateWorkerUsage(self, worker_id, cpu_usage, ram_usage):
        self.worker_info[worker_id]['cpu'] =cpu_usage 
        self.worker_info[worker_id]['ram'] =ram_usage

    def updateWorkerStatus(self,worker_id,status):
        self.worker_info[worker_id]['status'] = status

    def getWorkerInfo(self):

        clone = copy.deepcopy(self.worker_info)
        # return self.worker_info 
        
        for key,obj in self.worker_info.iteritems():
            self.worker_info[key]['cpu'] = -1
            self.worker_info[key]['ram'] = -1

        return clone 

#Starts the dispatcher server
Pyro4.Daemon.serveSimple(
    {
        DispatcherQueue(): "bertud.dispatcher"
    },
    ns=True, verbose=True, host=ip)