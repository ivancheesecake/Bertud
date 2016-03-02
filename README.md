# Bertud
##Installation 
* Clone the repository: `git clone https://github.com/ivancheesecake/Bertud.git`
* Create a working branch: `git checkout -b work_branch_miyah`

###Install dependencies
* Add python and python scripts to PATH 
* >cd Bertud/dependencies
* >install.bat
* Extract LAStools in C:\
* Acquire LAStools license
* Open Pyro4 configuration file then add pickle to the entry "self.SERIALIZERS_ACCEPTED"<br />
	Sample location: "C:\Python27\ArcGIS10.2\Lib\site-packages\Pyro4-4.41-py2.7.egg\Pyro4\configuration.py"<br />
	self.SERIALIZERS_ACCEPTED = "serpent,marshal,json,pickle"
* Requires internet connection

###Server configuration
Edit `config.json`
* ip - IP address of server
* pythonPath - Path of Python libraries and executables
* defaultInputFolder - Where are laz files are located
* defaultOutputFolder - Where the outputs are placed

`{
   "ip":"10.0.3.115",
   "pythonPath":"C:\\Python27\\ArcGIS10.3\\",
   "defaultInputFolder":"C:/bertud_inputs/",
   "defaultOutputFolder":"C:/bertud_outputs"  
 } 
`
###Client configuration
Edit `slave_config.json`
* dispatcherIP - The IP address of the server
* workerID - The statically assigned IP of the slave
* tempFolder - Path of temporary files

`{"dispatcherIP":"10.0.3.115","workerID":"1", "tempFolder":"C:/bertud_temp"}`

###To run
* >runserver.bat (on command prompt)
* start bertud-slave-v2
* access 127.0.0.1:5000 in your browser
* add las files to the queue
