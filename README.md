# Bertud
##Installation 
* Clone the repository: git clone https://github.com/ivancheesecake/Bertud.git

###Install dependencies
* Add python and python scripts to PATH 
* >cd Bertud/dependencies
* >install.bat
* Extract LAStools in C:\
* Acquire LAStools license
* Open Pyro4 configuration file then add pickle to the entry "self.SERIALIZERS_ACCEPTED"__
	Sample location: "C:\Python27\ArcGIS10.2\Lib\site-packages\Pyro4-4.41-py2.7.egg\Pyro4\configuration.py"__
	self.SERIALIZERS_ACCEPTED = "serpent,marshal,json,pickle"
* Requires internet connection

###To run
* change server's IP in config.json and slave_config.json
* >runserver.bat (on command prompt)
* start bertud-slave-v2
* access 127.0.0.1:5000 in your browser
* add las files to the queue
