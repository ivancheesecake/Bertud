import subprocess
import atexit
import psutil
import Pyro4
import os
import time
# from Pyro4.util import SerializerBase
# import workitem

from flask import Flask,render_template,url_for,redirect,jsonify
app = Flask(__name__)

def exit_handler():

	PROCNAMES = ["pyro4-ns.exe","python.exe"]

	for proc in psutil.process_iter():
	    # check whether the process name matches
	    if proc.name() in PROCNAMES:
	    	# print "Closing nameserver..."
	        proc.kill()

atexit.register(exit_handler)

# @app.context_processor
# def override_url_for():
#     return dict(url_for=dated_url_for)

# def dated_url_for(endpoint, **values):
#     if endpoint == 'static':
#         filename = values.get('filename', None)
#         if filename:
#             file_path = os.path.join(app.root_path,
#                                      endpoint, filename)
#             values['q'] = int(os.stat(file_path).st_mtime)
#     return url_for(endpoint, **values)


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

# URI for starting the nameserver
@app.route('/start_services')
def start_services():
	subprocess.Popen(["pyro4-ns","--host","10.0.63.90"])
	# time.sleep(2)
	subprocess.Popen(["python","dispatcher.py"])
	return "Services initialized..."


@app.route('/start_nameserver')
def start_nameserver():

	# Open nameserver
	p = subprocess.Popen(["pyro4-ns","--host","10.0.63.90"])
	return "Started nameserver successfully..."

# URI for starting the nameserver
@app.route('/start_dispatcher')
def start_dispatcher():

	# Open nameserver
	p = subprocess.Popen(["python","dispatcher.py"])
	return "Started dispatcher successfully..."

@app.route('/listen')
def listen():
	# SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)
	dispatcher = Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher@10.0.63.90")

	#JSONIFY THIS SHIT
	return jsonify(dispatcher.getWorkerInfo())

if __name__ == '__main__':
	app.run(debug=True,host='0.0.0.0')
