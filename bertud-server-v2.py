import subprocess
import atexit
import psutil
import Pyro4
import os
import time
import json
import sys

# from Pyro4.util import SerializerBase
# import workitem

from flask import Flask,render_template,url_for,redirect,jsonify,request

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

@app.route('/addToQueue', methods=['POST'])
def addToQueue():

	items = json.loads(request.form.get("files"))
	outputPath = request.form.get("outputPath")
	current_id = 0
	# Read max_id from file

	with open("config/max_id.json","r") as f:
		current_id = int(json.loads(f.read())["id"])

	for item in items:
		current_id+=1

		#Add To Queue

	with open("config/max_id.json","w") as f:	
		f.write(json.dumps({"id":str(current_id)}))


	return jsonify({"success":"true"})



if __name__ == '__main__':
	with open("config/config.json","r") as f:
		configfile = f.read()

	config = json.loads(configfile)	

	ip= config["ip"]
	pythonPath= config["pythonPath"]

	app.run(debug=True,host='0.0.0.0')
