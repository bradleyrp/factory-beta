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
python deploy/script-test-suite.py && \
deactivate

additional notes:
	see the notes on the macbook worker/aside-factory for a description of the celery problem
	if you shutdown a worker it (1) won't kill the running job and (2) doesn't revoke it
	but when you start everything up again, it will pick up the previous jobs (flower misses them)
	this behavior is ideal: you can shut everything down but when it spins up it continues the other jobs
	it finishes running jobs even when you shut things down (somehow this doesn't kill the worker via pgid)
	actually it seems to start things in random order when you restart the worker
		if you restart the project before the last-running job completes 
			then you will have two running at once
		note that I added some instructions in the queue so the user understands
		also added terminate commands
		it's up to the user to terminate pending/running jobs before shutdown

upcoming:
	use (separate) AJAX for the queue
	debug 
"""

import os,sys,glob,re
import shutil
import subprocess

###---SETTINGS
nsims = [0,10,5][-1]
test = ['trialanine','villin'][0]

#---more settings
project_name = 'project'
rootdir = os.path.abspath(os.getcwd())
djpath = os.path.join(rootdir,'site',project_name)
simspath = os.path.join(rootdir,'data',project_name,'sims')
sources = {'villin':os.path.join(rootdir,'amx-module-test-villin/3trw_nosol_single.pdb')}
bundles = {'trialanine':{'path':'~/worker/factory/amx-module-test-3ala','metarun':'3ala',
	'program':'trialanine > metarun_test_3ala.py'}}

#---imports from django
sys.path.insert(0,djpath)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",project_name+".settings")
import django
django.setup()
import simulator
from django.conf import settings
from simulator.views import prepare_simulation,prepare_source,detect_last
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

#---not designed for old-school which was half-baked anyway
assert settings.BACKRUN in ['celery','celery_backrun']

#---start many simulations
for num in range(0,nsims):
	#---a program type job
	if test=='villin':
		print '[STATUS] preparing simulation %d/%d'%(num,nsims)
		source,created = simulator.models.Source.objects.get_or_create(name=test)
		sim,created = simulator.models.Simulation.objects.get_or_create(
			name='%s rp%d'%(test,num),program='protein')
		prepare_simulation(sim)
		#---mimic simulator.views
		location = find_simulation(sim.code)
		simscript = location+'/script-%s.py'%sim.program
		scriptset = simulation_script(simscript)
		prepare_source(source,sim,settings_dict=scriptset)
		with open(os.path.join(location,'waiting.log'),'w') as fp: fp.write('waiting for execution')
		errorlog = 'script-s%02d-%s.log'%(detect_last(location),sim.program)
		command = './script-%s.py >> %s 2>&1'%(sim.program,errorlog)
		sherpa.apply_async(args=(command,),kwargs={'cwd':location},retry=False)
		sim.started = True
		sim.details = str(scriptset)
		sim.save()
	#---a bundle type job
	elif test=='trialanine':
		print '[STATUS] preparing simulation %d/%d'%(num,nsims)
		bundle = simulator.models.Bundle.objects.get(name=test)
		sim,created = simulator.models.Simulation.objects.get_or_create(name='%s rp%d'%(test,num),
			program=bundles[test]['program'])
		prepare_simulation(sim)
		#---mimic simulator.views for a BUNDLE
		location = find_simulation(sim.code)
		with open(os.path.join(location,'waiting.log'),'w') as fp: fp.write('waiting for execution')
		bundle_info = is_bundle(sim.program)
		if bundle_info:
			candidate_fns = glob.glob(location+'/inputs/meta*')+glob.glob(location+'inputs/*/meta*')
			script_fn = [i for i in candidate_fns if re.search(bundle_info[1],os.path.basename(i))]
			simscript = script_fn[0]
		else: simscript = location+'/script-%s.py'%sim.program
		scriptset = simulation_script(simscript)
		location = find_simulation(sim.code)
		metarun = re.match('^(.+)\.py$',bundle_info[1]).group(1) if bundle_info else None
		errorlog = 'script-%s.log'%metarun
		command = 'make metarun %s >> %s 2>&1'%(metarun,errorlog)
		sherpa.apply_async(args=(command,),kwargs={'cwd':location},retry=False)
		sim.started = True
		sim.details = str(scriptset)
		sim.save()
	else: raise
