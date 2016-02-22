#!/usr/bin/python

"""
Interpret a user input (typically connect.yaml) in order to set up the "factory".
See connect.yaml for example connections.
"""

import os,sys,re,subprocess,shutil,glob,json
from copy import deepcopy
import yaml

#---user must supply the yaml file to describe the connections
devmode = "DEVELOP" in sys.argv
if len(sys.argv)!=2 and not (len(sys.argv)==3 and devmode): 
	raise Exception('\n[USAGE] make connect <yaml>') 
	quit()
with open(sys.argv[1]) as fp: sets = yaml.load(fp.read())
if 'examples' in sets: del sets['examples']

#---develop flag restricts attention only to the single develop entry
if devmode:
	devkeys = [i for i in sets if sets[i]['type']=='development']
	if len(devkeys)>1: 
		raise Exception('\n[ERROR] when using the develop option to connect.py you can only have one '+
			'development type in the yaml file')
	elif len(devkeys)==1:
		sets = dict([(key,val) for key,val in sets.items() if key==devkeys[0]])
	else: devmode = False

#---APPENDAGES
#-------------------------------------------------------------------------------------------------------------

urls_additions = """
#---automatically added
from django.views.generic.base import RedirectView
urlpatterns += [
	url(r'^simulator/',include('simulator.urls',namespace='simulator')),
	url(r'^calculator/',include('calculator.urls',namespace='calculator')),
	url(r'^$',RedirectView.as_view(url='calculator/',permanent=False),name='index'),
	]
"""

write_additions = """
from django.conf.urls.static import static	
urlpatterns += static('/write/',document_root='/home/localshare/analysis/mplxr/write/')
"""

setings_additions = """
#---automatically added from kickstart
INSTALLED_APPS = tuple(list(INSTALLED_APPS)+['simulator','calculator','djcelery'])

#---celery worker and routing settings
import djcelery
from kombu import Exchange,Queue
djcelery.setup_loader()
BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERYD_CONCURRENCY = 1
CELERY_QUEUES = (
    Queue('queue_sim',Exchange('queue_sim'),routing_key='queue_sim'),
    Queue('queue_calc',Exchange('queue_calc'),routing_key='queue_calc'),
    )
CELERY_ROUTES = {
    'simulator.tasks.sherpa':{'queue':'queue_sim','routing_key':'queue_sim'},
    'calculator.tasks.sherpacalc':{'queue':'queue_calc','routing_key':'queue_calc'},
    }

#---PATHS
"""

def abspath(path): return os.path.join(os.path.expanduser(os.path.abspath(path)),'')

def mkdir_or_report(dn):

	if os.path.isdir(dn): print "[STATUS] found %s"%(dn)
	else: 
		os.mkdir(dn)
		print "[STATUS] created %s"%dn

#---MAIN
#-------------------------------------------------------------------------------------------------------------

#---master loop over all connections
for connection_name,specs in sets.items():

	#---regex PROJECT_NAME to the connection name in the paths sub-dictionary
	for key,val in specs['paths'].items(): 
		if type(val)==list: 
			for item in val: item = re.sub('PROJECT_NAME',connection_name,item)
		else: 
			if not not val: specs['paths'][key] = re.sub('PROJECT_NAME',connection_name,val)
	for key,val in specs.items():
		if type(val)==str: specs[key] = re.sub('PROJECT_NAME',connection_name,val)
	
	#---make directories if they are absent
	#---! is this necessary?
	root_data_dir = 'data/'+connection_name
	mkdir_or_report(root_data_dir)
	for key in ['post_plot_spot','post_data_spot','dropspot']: 
		mkdir_or_report(abspath(specs['paths'][key]))
	mkdir_or_report(abspath(specs['paths']['dropspot']+'/sources/'))

	#---interpret paths from connect.yaml for PROJECT_NAME/PROJECT_NAME/settings.py in the django project
	#---these paths are all relative to the rootspot, the top directory for the factory codes
	settings_paths = {
		'automacs_upstream':specs['automacs'],
		'project_name':connection_name,
		'plotspot':abspath(specs['paths']['post_plot_spot']),
		'postspot':abspath(specs['paths']['post_data_spot']),
		'dropspot':abspath(specs['paths']['dropspot']),
		'calcspot':specs['calc'],
		'rootspot':os.path.join(os.getcwd(),''),
		}

	#---prepare additions to the settings.py and urls.py
	settings_append_fn = 'logs/setup-%s-settings-append.py'%connection_name
	urls_append_fn = 'logs/setup-%s-urls-append.py'%connection_name
	with open(settings_append_fn,'w') as fp:
		fp.write(setings_additions)
		for key,val in settings_paths.items():
			fp.write('%s = "%s"\n'%(key.upper(),val))
		for key in ['PLOTSPOT','POSTSPOT','ROOTSPOT']: 
			fp.write('%s = os.path.expanduser(os.path.abspath(%s))\n'%(key,key))
		#---user-specified database
		if 'database' in specs['paths']: 
			fp.write("DATABASES['default']['NAME'] = %s\n"%specs['paths']['database'])
		else: fp.write(
			"DATABASES['default']['NAME'] = os.path.join(os.path.abspath(BASE_DIR),'db.sqlite3')\n")
	with open(urls_append_fn,'w') as fp: fp.write(urls_additions)

	#---! need to make the data spots directory from a list or a string here
	#---kickstart packages the codes in dev, makes a new project, and updates settings.py and urls.py
	if not devmode:
		subprocess.check_call('make kickstart %s %s %s'%(
			connection_name,settings_append_fn,urls_append_fn),shell=True)
	else: 
		subprocess.check_call("git clone %s calc/dev &> logs/log-dev-clone-omni"%specs['omnicalc'],
			shell=True,executable='/bin/bash')
		subprocess.check_call("make -C calc/dev config defaults &> logs/log-dev-omni-config",
			shell=True,executable='/bin/bash')

	#---remove blank calcs and local post/plot from default omnicalc configuration
	for folder in ['post','plot','calcs']:
		dn = 'calc/%s/%s'%(connection_name,folder)
		if os.path.isdir(dn): shutil.rmtree(dn)

	#---if the repo points nowhere we prepare a calcs folder for omnicalc (repo is required)
	new_calcs_repo = not (os.path.isdir(specs['repo']) and os.path.isdir(specs['repo']+'/.git'))
	if new_calcs_repo:
		print "[WARNING] repo path %s does not exist so we are making a new one"%specs['repo']
		mkdir_or_report(specs['calc']+'/calcs')
		mkdir_or_report(specs['calc']+'/calcs/specs/')
		subprocess.check_call('git init',shell=True,cwd=specs['calc']+'/calcs')
		#---AUTO POPULATE WITH CALCULATIONS
	#---if the repo is a viable git repo then we clone it
	else: subprocess.check_call('git clone '+specs['repo']+' '+specs['calc']+'/calcs',shell=True)

	#---given a previous omnicalc we consult paths.py in order to set up the new one

	with open(specs['calc']+'/paths.py') as fp: default_paths = fp.read()
	default_paths = {}
	if 'parse_specs' not in specs: paths_fn = specs['calc']+'/paths.py'
	else: paths_fn = specs['parse_specs']
	execfile(paths_fn,default_paths)
	new_paths = deepcopy(default_paths['paths'])
	new_paths['data_spots'] = specs['paths']['data_spots']
	new_paths['post_data_spot'] = settings_paths['postspot']
	new_paths['post_plot_spot'] = settings_paths['plotspot']
	new_paths['workspace_spot'] = abspath(root_data_dir+'/workspace')
	#---specs files must be relative to the omnicalc root
	if not specs['paths']['specs_file']:
		#---automatically detect any yaml files in the specs folder
		new_paths['specs_file'] = glob.glob(specs['calc']+'/calcs/specs/meta*.yaml')
	else:
		custom_specs = specs['paths']['specs_file']
		if type(custom_specs)==str: custom_specs = [custom_specs]
		new_paths['specs_file'] = ['calcs/specs/'+os.path.basename(fn) 
			for fn in glob.glob(specs['calc']+'/calcs/specs/meta*.yaml')]
	new_paths_file = {'paths':new_paths,'parse_specs':default_paths['parse_specs']}
	with open(specs['calc']+'/paths.py','w') as fp:
		fp.write('#!/usr/bin/python\n\n')
		for key in new_paths_file:
			fp.write('%s = %s\n\n'%(key,
			json.dumps(new_paths_file[key],indent=4,ensure_ascii=False).
			replace('\\\\','\\').replace('    ','\t')))

	#---previous omnicalc users may have a specific gromacs.py that they wish to use
	if 'omni_gromacs_config' in specs and not not specs['omni_gromacs_config']:
		gromacs_fn = os.path.abspath(os.path.expanduser(specs['omni_gromacs_config']))
		shutil.copyfile(gromacs_fn,specs['calc']+'/gromacs.py')

	#---extra commands for develpment
	if devmode:

		try: 
			subprocess.check_call("git clone https://github.com/bradleyrp/automacs data/dev/sims/docs "+
				"&> logs/log-dev-clone-sims",shell=True,executable='/bin/bash')
		except: pass
		try:
			subprocess.check_call("make -C data/dev/sims/docs docs &> logs/log-dev-sims-docs",
				shell=True,executable='/bin/bash')
		except: pass
		subprocess.check_call(
			'echo "from django.contrib.auth.models import User;User.objects.create_superuser'+
			'(\'admin\',\'\',\'admin\');print;quit();" | python ./dev/manage.py shell &> /dev/null',
			shell=True,executable='/bin/bash')
		subprocess.check_call('source env/bin/activate && python dev/manage.py makemigrations '+
			'&> logs/log-dev-makemigrations',shell=True,executable='/bin/bash')
		subprocess.check_call('source env/bin/activate && python dev/manage.py migrate '+
			'&> logs/log-dev-migrate',shell=True,executable='/bin/bash')

	#---assimilate old data if available
	subprocess.check_call('source env/bin/activate && make -C '+specs['calc']+' export_to_factory %s %s'%
		(connection_name,settings_paths['rootspot']+specs['site']),shell=True,executable='/bin/bash')

	print "[STATUS] connected %s!"%connection_name
	print "[STATUS] start with \"make run %s\""%connection_name
