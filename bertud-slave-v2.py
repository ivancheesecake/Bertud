import os
import socket
import sys
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import Masking as ma
import PrepareInputs as pi
import BoundaryRegularizationV2 as br
import time
import wx
import json
from skimage import io
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
    #instantiate application

    with open("config/slave_config.json","r") as f:
        configfile = f.read()
        config = json.loads(configfile)

    if not os.path.exists(config["tempFolder"]):
        os.makedirs(config["tempFolder"])    

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

    #make connection to dispatcher server
    dispatcher = Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+config["dispatcherIP"])
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


                with open(config["tempFolder"]+"\\pointcloud.laz", "wb") as file:
                    file.write(laz)

                #Process the data
                try:
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

                    pieces = br.performBoundaryRegularizationV2(mergedMask,numProcesses=getRecCores(maxCores = recommendedCores))

                    print "Creating final mask and saving output raster..."

                    finalMask = ma.buildFinalMask(pieces,mergedMask)
                    
                    # time.sleep(10)

                    # finalMask = io.imread("C:/bertud_temp/slope.tif")
                    #set the output to the item's final result
                    item.result = finalMask

                except:
                    
                    e = sys.exc_info()[0]
                    item.error_msg = e
                    try:
                        dispatcher.saveError(item)
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
                                dispatcher.saveError(item)
                                dispatcher.updateWorkerStatus(WORKERID,'1')
                                print("Connected to dispatcher.")
                                break
                                  
                else:

                    #set the item's worker
                    item.end_time = time.time()

                    #KAGEYAMA
                    #return the result to the dispatcher
                    try:
                        dispatcher.putResult(item, finalMask)
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
                                dispatcher.putResult(item, finalMask)
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


