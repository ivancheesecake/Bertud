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
        self.Qwaiting = queue.Queue()

        #load past works and place them to Qwaiting
        work_Q = pickle.load(open("config/work_queque.p", "rb"))
        for key, item in work_Q.item():
            self.Qwaiting.put(item)

        self.Qprocessing = {}
        self.Qfinished = {}
        # self.workqueue = queue.Queue()
        # self.resultqueue = queue.Queue()
        # 
                            #id  #attributes
        self.worker_info = {'1':{'cpu':-1,'ram':-1,'status':"0"}} # Create 10 of these next time


    #function that receives work from client
    def putWork(self, item):
        #add item to queue
        self.Qwaiting.put(item)

        #update the work_queue item for backup
        work_Q = pickle.load(open("config/work_queque.p", "rb"))
        work_Q[str(item.itemId)] = item
        pickle.dump(work_Q, open("config/work_queque.p", "wb"))

    #slaves use this to check for available works
    def getWork(self, worker_ID, timeout=5):
        try:
            #give work to slave
            item = self.Qwaiting.get(block=True, timeout=timeout)
            item.worker_id = worker_ID                  #set worker id to item
            self.Qprocessing[str(item.itemId)] = item   #add item to the queue for currently processing

            #read the input file and return them to worker
            with open(item.path, "rb") as file:
                return item, file.read()

        except queue.Empty:
            raise ValueError("no items in queue")

    #function that receives results from slaves
    def putResult(self, item, output):
        self.Qprocessing.pop(str(item.itemId), None)
        self.Qfinished[str(item.itemId)] = item

        #update the work_queue item for backup
        work_Q = pickle.load(open("config/work_queque.p", "rb"))
        self.work_Q.pop(str(item.itemId), None)
        pickle.dump(work_Q, open("config/work_queque.p", "wb"))

        #update finished works
        work_F = pickle.load(open("config/finished_work.p", "rb"))
        work_F[str(item.itemId)] = item
        pickle.dump(work_F, open("config/finished_work.p", "wb"))

        #write output file
        with open(item.output_path) as file:
                file.write(output)

        # self.resultqueue.put(item)

    #clients use this to check for available results
    def getResult(self):
        return self.Qfinished
        # try:
        #     return self.resultqueue.get(block=True, timeout=timeout)
        # except queue.Empty:
        #     raise ValueError("no result available")

    # def workQueueSize(self):
    #     return self.workqueue.qsize()

    # def resultQueueSize(self):
    #     return self.resultqueue.qsize()

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