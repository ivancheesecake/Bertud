# File: bertud-server-v2.py
# Description: Implementation of the Bertud webserver
# Author: UPLB Phil-LiDAR 1 

# Import the necessary stuff
import subprocess
import atexit
import psutil
import os
import Pyro4
import time
import json
import sys
from workitem import Workitem
from Pyro4.util import SerializerBase
import pickle
import collections
from flask import Flask,render_template,url_for,redirect,jsonify,request

# Configuration stuff for Pyro
Pyro4.config.SERIALIZER = "pickle"
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

ip = ""
pythonPath = ""

# Definition of utility functions

# Function to split list l into n-sized chunks
# From: http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def chunks(l, n):
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]

# Funtion for handling program termination
def exit_handler():

	# Define processes to be closed 
	PROCNAMES = ["pyro4-ns.exe","python.exe"]

	for proc in psutil.process_iter():
	    # Check whether the process name matches
	    if proc.name() in PROCNAMES:
	        proc.kill()

# Register exit event
atexit.register(exit_handler)

# Initialize application
app = Flask(__name__)

# Route definitions

# Route for Index page
# Starts the nameserver and dispatcther, redirects to the dashboard after doing so
@app.route('/')
def index():
	
	# If nameserver is already running, redierct to dashboard
	for proc in psutil.process_iter():
	    if proc.name() == "pyro4-ns.exe":
	    	return redirect(url_for('dashboard'))

	# Initialize nameserver and dispatcher    	
	subprocess.Popen([pythonPath+"/Scripts/pyro4-ns","--host",ip])
	subprocess.Popen([pythonPath+"python","dispatcher.py",ip])
	
	# Redirect to dashboard	
	return redirect(url_for('dashboard'))
				
# Route for Dashboard page
# Provides the main interface for the user
@app.route('/dashboard')
def dashboard():

	# Check if nameserver is already running, if it is, display the page	
	for proc in psutil.process_iter():
	    if proc.name() == "pyro4-ns.exe":
	    	return render_template("index-v4.html",defaultFolders=defaultFolders,workers=workersChunks)
	
	# Else, redirect to the index page
	return redirect(url_for('index'))    	

# Route for accessing the status of BERTUD's workers and processing
# Called in n-second intervals by the dashboard page
@app.route('/status')
def status():

	# Get a reference to the dispatcher
	dispatcher = Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+ip) 
	
	# Fetch updates
	worker_info,finished,processing = dispatcher.getUpdates()

	# Send to page
	return jsonify({"worker_info":worker_info,"finished":finished,"processing":processing})

# Route for checking if the specified input folder exists and for fetching the input file paths
@app.route('/inputfolder', methods=['POST'])
def inputfolder():

	# Fetch get variable
	path = request.form.get("sourcefolder")
	
	dirExists = os.path.isdir(path)
	
	retval = {'exists':dirExists,'files':""}
	files=[]

	# Fetch laz files	
	if(dirExists):
		for f in os.listdir(path):
			# print f
			if f.endswith(".laz"):
				files.append(f[:-4])
    	# files=files[:-1]
    	retval['files']= files			
	
	# Send to page	
	return jsonify(retval)

# Route for loading the serialized work queue during application initialization 
@app.route('/initializeQueue', methods=['POST'])
def initializeQueue():

	# Open pickle
	queue = pickle.load(open("config/work_queue.p","rb"))
	dictQueue = []
	
	# Fetch contents
	for key,val in queue.items():
		dictQueue.append({"itemId":val.itemId,"path":val.path,"output_path":val.output_path,"worker_id":val.worker_id,"start_time":val.start_time,"end_time":val.end_time})
		# dictQueue.append(queue[key].dictify())
	
	# Sort	
	ordered = sorted(dictQueue, key=lambda k:k["itemId"])

	# Send to page
	return jsonify({"success":"true","queue":ordered})

# Route for adding items to the work queue
@app.route('/addToQueue', methods=['POST'])
def addToQueue():

	# Fetch get variables
	filePaths = json.loads(request.form.get("files"))
	filesShort = json.loads(request.form.get("filesShort"))
	outputPath = request.form.get("outputPath")

	current_id = 0

	# Read max_id from file
	with open("config/max_id.json","r") as f:
		current_id = int(json.loads(f.read())["id"])

	# Get reference to the dispatcher	
	with Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+ip) as dispatcher:
		# Prepare the items and add to queue
		for path,pathShort in zip(filePaths,filesShort):
			current_id+=1
			filename = pathShort.split(".")[0]
			outPath = outputPath + "/" + filename + ".tif"
			print filename
			print outputPath
			item = Workitem(current_id, path, outPath)
			dispatcher.putWork(item)

	# Update max id
	with open("config/max_id.json","w") as f:	
		f.write(json.dumps({"id":str(current_id)}))

	# Get the current queue	
	queue = pickle.load(open("config/work_queue.p","rb"))
	
	# Prepare the response
	dictQueue = []
	for key,val in queue.items():
		dictQueue.append({"itemId":val.itemId,"path":val.path,"output_path":val.output_path,"worker_id":val.worker_id,"start_time":val.start_time,"end_time":val.end_time})
		
	ordered = sorted(dictQueue, key=lambda k:k["itemId"])

	# Send to page
	return jsonify({"success":"true","queue":ordered})

@app.route('/removeFromQueue',methods=['POST'])
def removeFromQueue():

	removeID = request.form.get("removeID")
	dispatcher = Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+ip) 
	
	removed = dispatcher.removeWork(removeID)		

	return jsonify(removed)


@app.route('/getFinished', methods=['POST'])
def getFinished():

	dispatcher = Pyro4.core.Proxy("PYRONAME:bertud.dispatcher@"+ip) 
	finished,error = dispatcher.getResult()
	print finished
	print error

	return jsonify({"finished":finished,"error":error})

@app.route('/reports')
def reports():

	reports = pickle.load(open("config/finished_work.p","rb"));
	reports = reports.items()
	reports.sort(key=lambda x:x[1]['itemId'],reverse=True)
	workers_reports = {}

	for w in workers:
		workers_reports[w['workerID']] = w['workerName']

	return render_template("reports.html",reports=reports,workers=workers_reports)


if __name__ == '__main__':
	
	with open("config/config.json","r") as f:
		configfile = f.read()

	with open("config/slaves.json","r") as f:
		workersfile = f.read()	

	config = json.loads(configfile)
	workers = json.loads(workersfile)	
	workersChunks = chunks(workers,3)
	ip= config["ip"]
	pythonPath= config["pythonPath"]
	defaultInputFolder = config["defaultInputFolder"]
	defaultOutputFolder = config["defaultOutputFolder"]

	defaultFolders = defaultInputFolder,defaultOutputFolder

	app.run(debug=True,host='0.0.0.0')

