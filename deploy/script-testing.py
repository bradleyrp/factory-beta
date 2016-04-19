#!/usr/bin/python

"""
Perform some factory tasks automatically in FACTORY.

note that this code was used during testing of the factory
try the following commands to use it:

make nuke && \
make env system && \
make connect connect.local.yaml && \
source env/bin/activate && \
python deploy/puppet.py && \
deactivate && make run project
"""

import os,sys
import shutil
execfile(os.environ['PYTHONSTARTUP'])
import os

project_name = 'project'
rootdir = os.path.abspath(os.getcwd())
djpath = os.path.join(rootdir,'site',project_name)
simspath = os.path.join(rootdir,'data',project_name,'sims')
sources = {
	'villin':os.path.join(rootdir,'CELL/3trw_nosol.pdb'),
	'martini.ff':os.path.join(rootdir,'CELL/martini.ff'),
	}

sys.path.insert(0,djpath)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",project_name+".settings")
import pdb;pdb.set_trace()
import django
django.setup()
import simulator

#---replicate upload function
def upload_source(name,fn):
	if not os.path.isdir(os.path.join(simspath,'sources',name)):
		os.mkdir(os.path.join(simspath,'sources',name))
		shutil.copy(fn,os.path.join(simspath,'sources',name,''))
	else:
		import pdb;pdb.set_trace()
		#os.system()

#---make sources
for name,source in sources.items():
	try: upload_source(name,source)
	except: print '[STATUS] source %s exists'%name
	obj,created = simulator.models.Source.objects.get_or_create(name='villin')
	if not created: 
		print '[STATUS] making source %s'%name
		obj.save()
