import subprocess
import atexit
import psutil
import os
os.environ["PYRO_LOGFILE"] = "pyro.log"
os.environ["PYRO_LOGLEVEL"] = "DEBUG"
import Pyro4
import time
import json
import sys
from workitem import Workitem
from Pyro4.util import SerializerBase
import pickle

# from Pyro4.util import SerializerBase
# import workitem

from flask import Flask,render_template,url_for,redirect,jsonify,request

SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

app = Flask(__name__)

ip = ""
pythonPath = ""

def exit_handler():

	PROCNAMES = ["pyro4-ns.exe","python.exe"]

	for proc in psutil.process_iter():
	    # check whether the process name matches
	    if proc.name() in PROCNAMES:
	    	# print "Closing nameserver..."
	        proc.kill()

atexit.register(exit_handler)

@app.route('/')
def index():
	print ip
	# Create a condition to check if these processes are running
	
	for proc in psutil.process_iter():
	    if proc.name() == "pyro4-ns.exe":
	    	return redirect(url_for('dashboard'))

	subprocess.Popen([pythonPath+"/Scripts/pyro4-ns","--host",ip])
	subprocess.Popen([pythonPath+"python","dispatcher.py",ip])
	
	return redirect(url_for('dashboard'))
				
	

@app.route('/dashboard')
def dashboard():
	# p = subprocess.Popen(["pyro4-ns","--host","10.0.63.90"])
	return render_template("index-v3.html")

@app.route('/status')
def status():
	# SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)
	dispatcher = Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+ip)

	return jsonify(dispatcher.getWorkerInfo())

@app.route('/inputfolder', methods=['POST'])
def inputfolder():
	path = request.form.get("sourcefolder")
	# print path
	dirExists = os.path.isdir(path)
	retval = {'exists':dirExists,'files':""}
		
	files=[]

	if(dirExists):
		for f in os.listdir(path):
			# print f
			if f.endswith(".las") or f.endswith(".laz"):
				files.append(f[:-4])
    	# files=files[:-1]
    	retval['files']= files			
    			    	
	return jsonify(retval)

@app.route('/initializeQueue', methods=['POST'])
def initializeQueue():

	queue = pickle.load(open("config/work_queue.p","rb"))
	dictQueue = []
	for key,val in queue.items():
		dictQueue.append({"itemId":val.itemId,"path":val.path,"output_path":val.output_path,"worker_id":val.worker_id,"start_time":val.start_time,"end_time":val.end_time})
		# dictQueue.append(queue[key].dictify())

	return jsonify({"success":"true","queue":dictQueue})

@app.route('/addToQueue', methods=['POST'])
def addToQueue():

	filePaths = json.loads(request.form.get("files"))
	filesShort = json.loads(request.form.get("filesShort"))
	outputPath = request.form.get("outputPath")
	current_id = 0
	# Read max_id from file

	with open("config/max_id.json","r") as f:
		current_id = int(json.loads(f.read())["id"])

	with Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+ip) as dispatcher:
		for path,pathShort in zip(filePaths,filesShort):
			current_id+=1
			filename = pathShort.split(".")[0]
			outputPath = outputPath + "/" + filename + ".tif"
			item = Workitem(current_id, path, outputPath)
			dispatcher.putWork(item)

	#Add To Queue
	with open("config/max_id.json","w") as f:	
		f.write(json.dumps({"id":str(current_id)}))

	# Assume queueing is successful	
	
	queue = pickle.load(open("config/work_queue.p","rb"))
	# print queue	
	dictQueue = []
	for key,val in queue.items():
		dictQueue.append({"itemId":val.itemId,"path":val.path,"output_path":val.output_path,"worker_id":val.worker_id,"start_time":val.start_time,"end_time":val.end_time})
		# dictQueue.append(queue[key].dictify())

	return jsonify({"success":"true","queue":dictQueue})



if __name__ == '__main__':
	with open("config/config.json","r") as f:
		configfile = f.read()

	config = json.loads(configfile)	

	ip= config["ip"]
	pythonPath= config["pythonPath"]

	app.run(debug=True,host='0.0.0.0')
