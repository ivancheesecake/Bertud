import time

class Workitem(object):
    def __init__(self, itemId, path,output_path):
        print("Created workitem %s" % itemId)
        self.itemId = itemId
        self.path = path
        self.output_path = output_path
        # self.result = None
        self.worker_id = None
        self.start_time = None
        self.end_time = None
        self.error_msg = ""

    def __str__(self):
        return "<Workitem id=%s>" % str(self.itemId)
    
    def dictify(self):

        start_formatted = ""
        end_formatted = ""
        time_elapsed = ""

        if self.start_time != None:
            start_formatted = time.asctime(time.localtime(self.start_time))
        
        if self.end_time != None:
            end_formatted = time.asctime(time.localtime(self.end_time))

        # if self.start_time != None and self.end_time != None:
        #     time_elapsed = (self.end_time - self.start_time)

        return {"itemId":self.itemId,"path":self.path,"output_path":self.output_path,"worker_id":self.worker_id,"start_time":start_formatted,"end_time":end_formatted,"error_msg":self.error_msg}

    @staticmethod
    def from_dict(classname, d):
        """this method is used to deserialize a workitem from Pyro"""
        assert classname == "workitem.Workitem"
        w = Workitem(d["itemId"], d["path"], d["output_path"])
        # w.result = d["result"]
        w.worker_id = d["worker_id"]
        w.start_time = d["start_time"]
        w.end_time = d["end_time"]
        w.error_msg = d["error_msg"]
        return w

        

