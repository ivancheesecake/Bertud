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

SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())
TRAY_TOOLTIP = 'Bertud Slave'
TRAY_ICON_GREEN = 'green.png'
TRAY_ICON_RED = 'red.png'

class BertudTaskBarIcon(wx.TaskBarIcon):
    def __init__(self):
        super(BertudTaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON_GREEN)

        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.on_exit)    

    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_exit(self, event):
        wx.CallAfter(self.Destroy)

    def balloon_free(self):
        self.ShowBalloon("", "Tapos ka na gamitin ni BERTUD. GOODBYE")

    def balloon_work(self):
        self.ShowBalloon("", "Hello " + WORKERNAME + ", you are being used by BERTUD ")

    def balloon_running(self):
        self.ShowBalloon("", "BERTUD POWER!")

def main():
    app = wx.PySimpleApp()
    taskbar = BertudTaskBarIcon()

    dispatcher = Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@10.0.63.66")
    print("This is worker %s" % WORKERNAME)
    print("getting work from dispatcher.")
    taskbar.balloon_running()

    while True:
        try:
            time.sleep(2)
            taskbar.set_icon(TRAY_ICON_RED)
            item = dispatcher.getWork()
        except ValueError:
            print("no work available yet.")
        else:
            taskbar.set_icon(TRAY_ICON_RED)
            taskbar.balloon_work()

            print("Got some work...")
            # print("Received "+str(item.data.nbytes)+" bytes.")

            ndsm = item.data["ndsm"]
            classified= item.data["classified"]
            slope= item.data["slope"]
            slopeslope= item.data["slopeslope"]


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




            item.result = finalMask
            item.processedBy = WORKERNAME
            
            # PROCESS_BLOCK(item)
            dispatcher.putResult(item)

            taskbar.set_icon(TRAY_ICON_GREEN)
            taskbar.balloon_free()

    app.MainLoop()

if __name__ == "__main__":
    main()