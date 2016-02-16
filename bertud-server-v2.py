import subprocess
import atexit
import psutil
import Pyro4
import os
import time
import json
# from Pyro4.util import SerializerBase
# import workitem

from flask import Flask,render_template,url_for,redirect,jsonify,request
app = Flask(__name__)

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
	
	# Create a condition to check if these processes are running
	subprocess.Popen(["pyro4-ns","--host","10.0.63.90"])
	subprocess.Popen(["python","dispatcher.py"])
	return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
	# p = subprocess.Popen(["pyro4-ns","--host","10.0.63.90"])
	return render_template("index-v3.html")

@app.route('/listen')
def listen():
	# SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)
	dispatcher = Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@10.0.63.90")

	return jsonify(dispatcher.getWorkerInfo())

@app.route('/inputfolder', methods=['POST'])
def inputfolder():
	path = request.form.get("sourcefolder")
	# print path
	dirExists = os.path.isdir(path)
	retval = {'exists':dirExists,'files':""}
		
	files=""

	if(dirExists):
		for f in os.listdir(path):
			# print f
			if f.endswith(".las") or f.endswith(".laz"):
				files += f+","
    	files=files[:-1]
    	retval['files']= files			
    			    	
	return jsonify(retval)



if __name__ == '__main__':
	app.run(debug=True,host='0.0.0.0')
