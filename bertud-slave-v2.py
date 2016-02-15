import os
import socket
import sys
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem
import Masking as ma
import BoundaryRegularizationV2 as br
import time
import wx

# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

#define worker identity
WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())

TRAY_TOOLTIP = 'Bertud Slave'

#Indicates that there are no connection between the slave and the dispatcher
TRAY_ICON_GRAY = 'gray.png'
#Indicates that the slave is free of work
TRAY_ICON_GREEN = 'green.png'
#Indicates that the slave is working
TRAY_ICON_RED = 'red.png'

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
        self.ShowBalloon("", "Hello " + WORKERNAME + ", you are being used by BERTUD ")

    #balloon - slave initiated
    def balloon_running(self):
        self.ShowBalloon("", "BERTUD POWER!")

def main():
    #instantiate application
    app = wx.PySimpleApp()
    taskbar = BertudTaskBarIcon()

    print("This is worker %s" % WORKERNAME)

    #make connection to dispatcher server
    dispatcher = Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@169.254.28.136")

    #Loop for getting work
    while True:
        #Check for work in dispatcher
        try:
            item = dispatcher.getWork()
        #If there are no work available
        except ValueError:
            print("no work available yet.")
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
                    break
        #Processing work from dispatcher
        else:
            #Set taskbar's icon to red -> working
            taskbar.set_icon(TRAY_ICON_RED)
            taskbar.balloon_work()

            print("Got some work...")

            #Use the data collected from the dispatcher
            ndsm = item.data["ndsm"]
            classified= item.data["classified"]
            slope= item.data["slope"]
            slopeslope= item.data["slopeslope"]

            #Process the data
            print "Generating Initial Mask..."
            veggieMask,initialMask = ma.generateInitialMask(ndsm,classified,slope,ndsmThreshold=3,slopeThreshold=60)

            print "Generating markers for Watershed segmentation..."

            initialMarkers = ma.generateInitialMarkers(slopeslope,veggieMask)
            
            print "Performing Watershed segmentation..."

            labeledMask = ma.watershed2(ndsm,initialMask,initialMarkers,veggieMask)

            print "Performing basic region merging..."

            mergedMask = ma.mergeRegionsBasicV2(labeledMask,mergeThreshold=0.10,iterations=10)

            print "Performing basic boundary regularization..."
        
            pieces = br.performBoundaryRegularizationV2(mergedMask,numProcesses=6)

            print "Creating final mask and saving output raster..."
            
            finalMask = ma.buildFinalMask(pieces,mergedMask)

            #set the output to the item's final result
            item.result = finalMask
            #set the item's worker
            item.processedBy = WORKERNAME
            
            #KAGEYAMA
            #return the result to the dispatcher
            try:
                dispatcher.putResult(item)
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
                        dispatcher.putResult(item)
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