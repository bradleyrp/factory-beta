#!/usr/bin/python

"""
TEST SUITE + BATCH FACTORY MANIPULATOR
Perform some factory tasks automatically in FACTORY.
note that this code was used during testing of the factory
try the following commands to use it:

make nuke && \
make env system && \
make connect connect.local.yaml && \
source env/bin/activate && \
make run project && \
python deploy/script-testing.py && \
deactivate
"""

import os,sys
import shutil
import subprocess

###---SETTINGS
nsims = [0,10][0]
test = 'trialanine'
project_name = 'project'
rootdir = os.path.abspath(os.getcwd())
djpath = os.path.join(rootdir,'site',project_name)
simspath = os.path.join(rootdir,'data',project_name,'sims')
sources = {'villin':os.path.join(rootdir,'CELL/3trw_nosol.pdb')}
bundles = {'trialanine':{'path':'~/worker/factory/amx-module-test-3ala','metarun':'3ala',
	'program':'trialanine > metarun_test_3ala.py'}}

#---imports from django
sys.path.insert(0,djpath)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",project_name+".settings")
import django
django.setup()
import simulator
from django.conf import settings
from simulator.views import prepare_simulation,prepare_source
from simulator.views import find_simulation,simulation_script,get_bundle,is_bundle
from simulator.tasks import sherpa

def upload_source(name,fn):

	"""
	Replicate the upload function.
	"""

	if not os.path.isdir(os.path.join(simspath,'sources',name)):
		os.mkdir(os.path.join(simspath,'sources',name))
		shutil.copy(fn,os.path.join(simspath,'sources',name,''))
	elif os.path.isdir(os.path.join(simspath,'sources',name,'')): pass
	raise Exception('failed to upload %s,%s'%(name,fn))

#---make sources
if test in sources:
	for name,source in sources.items():
		try: upload_source(name,source)
		except: print '[STATUS] source %s exists'%name
		obj,created = simulator.models.Source.objects.get_or_create(name='villin')
		if not created: 
			print '[STATUS] making source %s'%name
			obj.save()

#---make bundles
if test in bundles:
	for name,details in bundles.items():
		obj,created = simulator.models.Bundle.objects.get_or_create(name=name,path=details['path'])
		if not created: 
			print '[STATUS] making bundle %s'%name
			obj.save()

#---run a gillion simulations maybe?
for num in range(nsims):
	if test=='villin':
		print '[STATUS] preparing simulation %d/%d'%(num,nsims)
		source = simulator.models.Source.objects.get(name=test)
		sim,created = simulator.models.Simulation.objects.get_or_create(name='%s rp%d'%(test,num))
		prepare_simulation(sim)
		#---mimic simulator.views
		location = find_simulation(sim.code)
		simscript = location+'/script-%s.py'%sim.program
		scriptset = simulation_script(simscript)
		prepare_source(source,sim,settings_dict=scriptset['dict'])
		sherpa.apply_async(args=(sim.program,),kwargs={'cwd':location},retry=False)
	elif test=='trialanine':
		print '[STATUS] preparing simulation %d/%d'%(num,nsims)
		bundle = simulator.models.Bundle.objects.get(name=test)
		sim,created = simulator.models.Simulation.objects.get_or_create(name='%s rp%d'%(test,num),
			program=bundles[test]['program'])
		prepare_simulation(sim)
		get_bundle(bundle.id,sim.code)
		bundle_info = is_bundle(sim.program)
		location = find_simulation(sim.code)
		sherpa.apply_async(args=(sim.program,),kwargs={'cwd':location,
			'metarun':bundle_info[1]},retry=False)
	else: raise
