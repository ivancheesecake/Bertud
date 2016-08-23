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
import json
import logging.config

Pyro4.config.SERIALIZER = "pickle"

ip = sys.argv[1]
nameServer = sys.argv[2]
# print "POTOTOTOTOTOTOTOTOTOTOTOTOOTT"
# print nameServer

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

def setup_logging(
    default_path='config/logging_config.json', 
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration

    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

# global work_q 
class DispatcherQueue(object):
    
    def __init__(self):


        # Read session number from file
        with open("config/session.json","r") as f:
            self.session = int(json.loads(f.read())["session"])

        # Update session
        with open("config/session.json","w") as f:   
            f.write(json.dumps({"session":str(self.session + 1)}))

        # self.Qwaiting = queue.Queue()
        self.Qwaiting = {}

        #load past works and place them to Qwaiting
        work_q = pickle.load(open("config/work_queue.p", "rb"))
        for key, item in work_q.items():
            # self.Qwaiting.put(item)
            self.Qwaiting[key] = item

        self.Qerror = {}
        self.Qprocessing = {}
        self.Qfinished = {}
        self.RemoveIDs = []
        self.loggers = []
        # self.workqueue = queue.Queue()
        # self.resultqueue = queue.Queue()
        # 
                            #id  #attributes
        # self.worker_info = {'1':{'cpu':-1,'ram':-1,'status':"0"},'2':{'cpu':-1,'ram':-1,'status':"0"}} # Create 10 of these next time
        self.worker_info = {} # Create 10 of these next time

        with open("config/slaves.json","r") as f:
            workersfile = f.read()  

        workers = json.loads(workersfile)

        setup_logging()

        for worker in workers:
            temp_worker_id = str(worker["workerID"])
            self.worker_info[temp_worker_id] = {'cpu':-1,'ram':-1,'status':"0"}
            self.loggers.append(logging.getLogger("worker_" + temp_worker_id))

    # def initializeWorkers(self,workers):
    #     for worker in workers:
    #         self.worker_info[str(worker["workerID"])] = {'cpu':-1,'ram':-1,'status':"0"}

    def saveLogs(self, worker_id, msg):
        worker_id = int(worker_id)
        session_str = "SESSION#" + str(self.session) + " - "
        for level, log_msg in msg:
            full_msg = session_str + log_msg
            if level == "INFO":
                self.loggers[worker_id].info(full_msg)
            elif level == "ERROR":
                self.loggers[worker_id].error(full_msg)
            elif level == "WARNING":
                self.loggers[worker_id].warning(full_msg)
            elif level == "CRITICAL":
                self.loggers[worker_id].critical(full_msg)
            elif level == "DEBUG":
                self.loggers[worker_id].debug(full_msg)


        # try:
        #     worker_id = int(worker_id)
        #     session_str = "SESSION#" + str(self.session) + " - "
        #     full_msg = session_str + msg
        #     if level == "INFO":
        #         self.loggers[worker_id].info(full_msg)
        #     elif level == "ERROR":
        #         self.loggers[worker_id].error(full_msg)
        #     elif level == "WARNING":
        #         self.loggers[worker_id].warning(full_msg)
        #     elif level == "CRITICAL":
        #         self.loggers[worker_id].critical(full_msg)
        #     elif level == "DEBUG":
        #         self.loggers[worker_id].debug(full_msg)
        # except:
        #     print sys.exc_info()

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
        removed = work_q.pop(str(itemID), None)
        pickle.dump(work_q, open("config/work_queue.p", "wb"))
        return removed.dictify()

    def saveError(self, item, error_msg):

        self.saveLogs(item.worker_id, [("ERROR", error_msg)])

        self.Qprocessing.pop(str(item.itemId), None)
        self.RemoveIDs.append({"item_id":int(item.itemId),"path":item.path,"worker_id":item.worker_id,"error":"True"})
        self.Qerror[str(item.itemId)] = item.dictify()

        #update the error_queue item for backup
        error_q = pickle.load(open("config/error_queue.p", "rb"))
        error_q[str(item.itemId)] = item
        pickle.dump(error_q, open("config/error_queue.p", "wb"))

        #update the work_queue item for backup
        work_q = pickle.load(open("config/work_queue.p", "rb"))
        work_q.pop(str(item.itemId), None)
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
            self.saveLogs(worker_ID, [("INFO", "START PROCESSING LAZ FILE - " + str(item.path))])
            # #read the input file and return them to worker
            with open(item.path, "rb") as file:

                return item, file.read()
        else:
            raise ValueError("no items in queue")

    #function that receives results from slaves
    def putResult(self, item, output,dsm,ndsm):

        self.saveLogs(item.worker_id, [("INFO", "FINISHED PROCESSING LAZ FILE - " + str(item.path))])

        self.saveLogs(item.worker_id, [("INFO", "")])
        self.Qprocessing.pop(str(item.itemId), None)
        self.RemoveIDs.append({"item_id":int(item.itemId),"path":item.path,"worker_id":item.worker_id,"error":"False"})
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

        with open(item.output_path[:-4]+"_dsm.tif","wb") as file:
            file.write(dsm)
        with open(item.output_path[:-4]+"_ndsm.tif","wb") as file:
            file.write(ndsm) 

        # self.resultqueue.put(item)

    #clients use this to check for available results
    def getResult(self):
        return self.Qfinished, self.Qerror
        # try:
        #     return self.resultqueue.get(block=True, timeout=timeout)
        # except queue.Empty:
        #     raise ValueError("no result available")

    # def workQueue(self):
    #     return self.Qwaiting

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
            
            if self.worker_info[key]['ram'] < 0:

                self.worker_info[key]['cpu'] -= 1
                self.worker_info[key]['ram'] -= 1

            else:

                self.worker_info[key]['cpu'] = -1
                self.worker_info[key]['ram'] = -1    

        if len(self.Qprocessing) == 0 and len(self.Qwaiting) == 0:
            self.RemoveIDs = []

        # print "DISPATCHER"
        # for val in remove_works:
            # print "DISPATCHER",val

        return slave_infos,remove_works,self.Qprocessing 

#Starts the dispatcher server
Pyro4.Daemon.serveSimple(
    {
        DispatcherQueue(): nameServer
    },
    ns=True, verbose=True, host=ip)