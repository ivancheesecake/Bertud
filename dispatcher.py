# from __future__ import print_function
try:
    import queue
except ImportError:
    import Queue as queue
import os
# os.environ["PYRO_LOGFILE"] = "pyro.log"
# os.environ["PYRO_LOGLEVEL"] = "DEBUG"

import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import copy
import sys
import pickle
from skimage import io
import time

Pyro4.config.SERIALIZER = "pickle"

ip = sys.argv[1]

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

# global work_q 
class DispatcherQueue(object):
    
    def __init__(self):
        # self.Qwaiting = queue.Queue()
        self.Qwaiting = {}

        #load past works and place them to Qwaiting
        work_q = pickle.load(open("config/work_queue.p", "rb"))
        for key, item in work_q.items():
            # self.Qwaiting.put(item)
            self.Qwaiting[key] = item

        self.Qprocessing = {}
        self.Qfinished = {}
        self.RemoveIDs = []
        # self.workqueue = queue.Queue()
        # self.resultqueue = queue.Queue()
        # 
                            #id  #attributes
        self.worker_info = {'1':{'cpu':-1,'ram':-1,'status':"0"}} # Create 10 of these next time


    #function that receives work from client
    def putWork(self, item):
        #add item to queue
        # self.Qwaiting.put(item)
        self.Qwaiting[str(item.itemId)] = item
        # print self.Qwaiting

        #update the work_queue item for backup
        work_q = pickle.load(open("config/work_queue.p", "rb"))
        work_q[str(item.itemId)] = item
        # print self.Qwaiting
        pickle.dump(work_q, open("config/work_queue.p", "wb"))

    def removeWork(self, itemID):

        self.Qwaiting.pop(str(itemID), None)

        #update the work_queue item for backup
        work_q = pickle.load(open("config/work_queue.p", "rb"))
        work_q.pop(str(itemID), None)
        pickle.dump(work_q, open("config/work_queue.p", "wb"))


    #slaves use this to check for available works
    def getWork(self, worker_ID, timeout=5):
        # try:
        #     #give work to slave
        #     item = self.Qwaiting.get(block=True, timeout=timeout)
        #     item.worker_id = worker_ID                  #set worker id to item
        #     print item.worker_id
        #     print item.path
        #     print item.output_path
        #     self.Qprocessing[str(item.itemId)] = item.dictify()   #add item to the queue for currently processing

        #     # #read the input file and return them to worker
        #     with open(item.path, "rb") as file:

        #         return item, file.read()

        #     # return "HI FANS","HELLO"   
        # except queue.Empty:
        #     raise ValueError("no items in queue")

        time.sleep(timeout)
        
        if len(self.Qwaiting) > 0:
            next = min(self.Qwaiting.keys())
            item = self.Qwaiting.pop(next)
            item.worker_id = worker_ID                  #set worker id to item
            self.Qprocessing[str(item.itemId)] = item.dictify()   #add item to the queue for currently processing

            # #read the input file and return them to worker
            with open(item.path, "rb") as file:

                return item, file.read()
        else:
            raise ValueError("no items in queue")

    #function that receives results from slaves
    def putResult(self, item, output):
        self.Qprocessing.pop(str(item.itemId), None)
        self.RemoveIDs.append({"item_id":int(item.itemId),"path":item.path,"worker_id":item.worker_id})
        # Tried dictify()

        self.Qfinished[str(item.itemId)] = item.dictify()

        #update the work_queue item for backup
        work_q = pickle.load(open("config/work_queue.p", "rb"))
        work_q.pop(str(item.itemId), None)
        pickle.dump(work_q, open("config/work_queue.p", "wb"))

        #update finished works
        #Dictify this
        work_F = pickle.load(open("config/finished_work.p", "rb"))
        work_F[str(item.itemId)] = item.dictify()
        pickle.dump(work_F, open("config/finished_work.p", "wb"))

        #write output file
 
        print item.output_path
        io.imsave(item.output_path,output)

        # with open(item.output_path,"wb") as file:
        #         file.write(output)

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

    # def getProcessing(self):
    #     return self.Qprocessing

    #updates the state of utilization of slaves
    def updateWorkerUsage(self, worker_id, cpu_usage, ram_usage):
        self.worker_info[worker_id]['cpu'] =cpu_usage 
        self.worker_info[worker_id]['ram'] =ram_usage

    def updateWorkerStatus(self,worker_id,status):
        self.worker_info[worker_id]['status'] = status

    def getUpdates(self):

        slave_infos= copy.deepcopy(self.worker_info)
        remove_works= copy.deepcopy(self.RemoveIDs)
        

        for key,obj in self.worker_info.iteritems():
            self.worker_info[key]['cpu'] = -1
            self.worker_info[key]['ram'] = -1

        self.RemoveIDs = []
        return slave_infos,remove_works,self.Qprocessing 

#Starts the dispatcher server
Pyro4.Daemon.serveSimple(
    {
        DispatcherQueue(): "bertud.dispatcher"
    },
    ns=True, verbose=True, host=ip)