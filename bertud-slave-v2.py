import os
import socket
import sys
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import Masking as ma
import PrepareInputs as pi
import BoundaryRegularizationV3 as br
import time
import wx
import json
from skimage import io,external
import subprocess
import atexit
import psutil
import shutil

Pyro4.config.SERIALIZER = "pickle"

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

#define worker identity

TRAY_TOOLTIP = 'Bertud Slave'

#Indicates that there are no connection between the slave and the dispatcher
TRAY_ICON_GRAY = 'img/white.png'
#Indicates that the slave is free of work
TRAY_ICON_GREEN = 'img/green.png'
#Indicates that the slave is working
TRAY_ICON_RED = 'img/red.png'

EXTREME_CPU_USAGE = 90

class BertudTaskBarIcon(wx.TaskBarIcon):
    def __init__(self):
        super(BertudTaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON_GRAY)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_exit(self, event):
        wx.CallAfter(self.Destroy)

    #balloon - finished work
    def balloon_free(self):
        self.ShowBalloon("", "Tapos ka na gamitin ni BERTUD. GOODBYE")

    #balloon - starting work
    def balloon_work(self):
        self.ShowBalloon("", "Hello Human, you are being used by BERTUD ")

    #balloon - slave initiated
    def balloon_running(self):
        self.ShowBalloon("", "BERTUD POWER!")

# On shutdown
def exit_handler():

    process = psutil.Process(worker_usage_process.pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def getRecCores(maxCores, itr = 3, timeout = 1):

    if maxCores == 8:
        return maxCores

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

def sendLogs(dispatcher, taskbar, worker_id, msg):
    try:
        dispatcher.saveLogs(worker_id, msg)
    except:
        taskbar.set_icon(TRAY_ICON_GRAY)
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
                taskbar.set_icon(TRAY_ICON_RED)
                dispatcher.saveLogs(worker_id, msg)
                print("Connected to dispatcher.")
                break

def main():
    #instantiate application

    with open("config/slave_config.json","r") as f:
        configfile = f.read()
        config = json.loads(configfile)

    if not os.path.exists(config["tempFolder"]):
        os.makedirs(config["tempFolder"])    

    if not os.path.exists(config["buildingPickleFolder"]):
        os.makedirs(config["buildingPickleFolder"]) 

    recommendedCores = int(config["maxAllowableCore"])

    WORKERID = str(config["workerID"])
    print config["pythonPath"]
    # Run worker_usage.py
    worker_usage_process = subprocess.Popen([config["pythonPath"],"worker_usage.py"],shell=True)

    # Attach atexit event

    atexit.register(exit_handler)
    # os.killpg(os.getpgid(pro.pid), signal.SIGTERM)

    app = wx.PySimpleApp()
    taskbar = BertudTaskBarIcon()

    # print("This is worker %s" % WORKERNAME)
    # print "TESSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSST",config["dispatcherNameServer"]
    #make connection to dispatcher server
    dispatcher = Pyro4.core.Proxy("PYRONAME:"+config["dispatcherNameServer"]+"@"+config["dispatcherIP"])
    gotItem = False
    #Loop for getting work
    while True:
        #Check for work in dispatcher
        try:
            time.sleep(0.5)
            cpu = psutil.cpu_percent()
            print cpu,EXTREME_CPU_USAGE

            if cpu < EXTREME_CPU_USAGE:

                item, laz = dispatcher.getWork(WORKERID)
                gotItem = True
                print "GOT ITEM!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            else:
                print "EXTREEEEEEME!"
                gotItem = False
                dispatcher.updateWorkerStatus(WORKERID,'busy')
        #If there are no work available
        except ValueError:
            print("no work available yet.")
            dispatcher.updateWorkerStatus(WORKERID,'1')
        #No connection to dispatcher
        except:
            print "PUMASOK!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            #Set the taskbar's icon to gray - means no connection
            taskbar.set_icon(TRAY_ICON_GRAY)
            #Loop for reconnecting to dispatcher
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
                    #Set the taskbar;s icon to green -> available
                    taskbar.set_icon(TRAY_ICON_GREEN)
                    taskbar.balloon_running()
                    print("Connected to dispatcher. Getting work now.")
                    dispatcher.updateWorkerStatus(WORKERID,'1')
                    break
        #Processing work from dispatcher
        else:
            if gotItem:
                gotItem = False
                #Set taskbar's icon to red -> working
                taskbar.set_icon(TRAY_ICON_RED)
                taskbar.balloon_work()

                print("Got some work...")
                # print item
                print "Changed worker status"
                dispatcher.updateWorkerStatus(WORKERID,'2')
                print dispatcher.getUpdates()[0]

                # Use the data collected from the dispatcher
                # ndsm = item.data["ndsm"]
                # classified= item.data["classified"]
                # slope= item.data["slope"]
                # slopeslope= item.data["slopeslope"]

                item.start_time = time.time()

                print "Clearing temp folder..."

                # http://stackoverflow.com/questions/185936/delete-folder-contents-in-python
                for the_file in os.listdir(config["tempFolder"]):
                    
                    file_path = os.path.join(config["tempFolder"], the_file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path): 
                            shutil.rmtree(file_path)
                    
                    except Exception, e:
                        print e


                with open(config["tempFolder"]+"/pointcloud.laz", "wb") as file:
                    file.write(laz)

                #Process the data
                try:
                    t0 = time.time()
                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "STARTED Preparing Inputs")])

                    print "Preparing Inputs..."
                    pi.prepareInputs(config["tempFolder"],config["lastoolsPath"])

                    ndsm = io.imread(config["tempFolder"] + "/ndsm.tif")
                    classified = io.imread(config["tempFolder"] + "/classified.tif")
                    classified = classified[0:len(ndsm),0:len(ndsm[0])]
                    slope = io.imread(config["tempFolder"] + "/slope.tif")
                    numret = io.imread(config["tempFolder"] + "/numret.tif")

                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "FINISHED Preparing Inputs - " + str(round(time.time()-t0,2)))])

                    t0 = time.time()
                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "STARTED Generating Initial Mask")])

                    print "Generating Initial Mask..."
                    initialMask = ma.generateInitialMask(ndsm,classified,slope,numret)

                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "FINISHED Generating Initial Mask - " + str(round(time.time()-t0,2)))])
                    # external.tifffile.imsave("initialMask.tif",initialMask)


                except:
                    e = sys.exc_info()[0]
                    error_msg = "Preparing Inputs / Generating Initial Mask - %s" % e
                    item.error_msg = error_msg
                    item.end_time = time.time()
                    try:
                        dispatcher.saveError(item, error_msg)
                        dispatcher.updateWorkerStatus(WORKERID,'1')
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
                                dispatcher.saveError(item, error_msg)
                                dispatcher.updateWorkerStatus(WORKERID,'1')
                                print("Connected to dispatcher.")
                                break
                                  
                else:

                    #set the item's worker
                    t0 = time.time()
                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "STARTED Building Regularization")])

                    print "Performing basic boundary regularization..."

                    pieces, pbr_logs = br.performBoundaryRegularizationV2(initialMask, item.path, config["buildingPickleFolder"], numProcesses=getRecCores(maxCores = recommendedCores))

                    if len(pbr_logs) > 0:
                        # pbr_logs.append(("ERROR", ""))
                        sendLogs(dispatcher, taskbar, WORKERID, pbr_logs)

                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "FINISHED Building Regularization - " + str(round(time.time()-t0,2)))])

                    t0 = time.time()
                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "STARTED Building Final Mask")])

                    finalMask = ma.buildFinalMask(pieces,initialMask)

                    sendLogs(dispatcher, taskbar, WORKERID, [("INFO", "FINISHED Building Final Mask - " + str(round(time.time()-t0,2)))])

                    external.tifffile.imsave("finalmask.tif",finalMask)

            
                    item.result = finalMask

                    item.end_time = time.time()

                    #KAGEYAMA
                    #return the result to the dispatcher
                    try:
                        with open(config["tempFolder"] + "/dsm.tif","rb") as f_dsm:
                            dsm = f_dsm.read()

                        with open(config["tempFolder"] + "/ndsm.tif","rb") as f_ndsm:
                            ndsm = f_ndsm.read()    

                        dispatcher.putResult(item,finalMask,dsm,ndsm)
                        dispatcher.updateWorkerStatus(WORKERID,'1')
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
                                dispatcher.putResult(item, finalMask,dsm,ndsm)
                                dispatcher.updateWorkerStatus(WORKERID,'1')
                                print("Connected to dispatcher.")
                                break

                # dispatcher.putResult(item)

                #set taskbar's icon to green -> available
                taskbar.set_icon(TRAY_ICON_GREEN)
                taskbar.balloon_free()

    #loop the application
    app.MainLoop()

if __name__ == "__main__":
    main()


