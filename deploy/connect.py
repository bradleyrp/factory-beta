#!/usr/bin/python

"""
Interpret a user input (typically deploy/connect.yaml) in order to set up the factory.
"""

import os,sys,re,subprocess,shutil,glob,json
from copy import deepcopy
import yaml

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

#---user must supply the yaml file to describe the connections
if len(sys.argv)!=2: 
	raise Exception('\n[USAGE] make connect <yaml>') 
	quit()
	
with open(sys.argv[1]) as fp: sets = yaml.load(fp.read())
if 'examples' in sets: del sets['examples']

#---master loop over all connections
for connection_name,specs in sets.items():

	#---regex NAME to the connection name in the paths sub-dictionary
	for key,val in specs['paths'].items(): 
		if type(val)==list: 
			for item in val: item = re.sub('PROJECT_NAME',connection_name,item)
		else: specs['paths'][key] = re.sub('PROJECT_NAME',connection_name,val)

	for key,val in specs.items():
		if type(val)==str: specs[key] = re.sub('PROJECT_NAME',connection_name,val)
	
	#---make directories if they are absent
	root_data_dir = 'data/'+connection_name

	if os.path.isdir(root_data_dir): print "[STATUS] found root data directory at %s"%(root_data_dir)
	else: 
		os.mkdir(root_data_dir)
		print "[STATUS] created %s"%root_data_dir
	for key in ['post_plot_spot','post_data_spot']:
		if os.path.isdir(specs['paths'][key]): print "[STATUS] found %s at %s"%(key,specs['paths'][key])
		else: 
			os.mkdir(specs['paths'][key])
			print "[STATUS] created %s"%specs['paths'][key]

	settings_paths = {
		'automacs_upstream':specs['automacs'],
		'project_name':connection_name,
		'plotspot':specs['paths']['post_plot_spot'],
		'postspot':specs['paths']['post_data_spot'],
		'dropspot':'PLACEHOLDER',
		'calcspot':specs['calc'],
		'rootspot':os.path.abspath(os.path.expanduser(os.getcwd()))
	}

	#---prepare additions to the settings.py and urls.py
	settings_append_fn = 'logs/setup-%s-settings-append.py'%connection_name
	urls_append_fn = 'logs/setup-%s-urls-append.py'%connection_name
	with open(settings_append_fn,'w') as fp:
		fp.write(setings_additions)
		for key,val in settings_paths.items():
			fp.write('%s = "%s"\n'%(key.upper(),val))
	with open(urls_append_fn,'w') as fp: fp.write(urls_additions)

	#---! need to make the data spots directory from a list or a string here
	subprocess.check_call('make kickstart %s %s %s'%(connection_name,settings_append_fn,urls_append_fn),shell=True)

	#---kickstart makes a default omnicalc configuration
	#---if a repo is specified, we modify the default configuration
	if 'repo' in specs and not (not specs['repo'] or specs['repo']==''):
		#---remove blank calcs and local post/plot from default omnicalc configuration
		for folder in ['post','post','calcs']:
			dn = 'calc/%s/post'%connection_name
			if os.path.isdir(dn): shutil.rmtree(dn)
		#---clone the user's repo into calcs
		print "[STATUS] cloning the user repo from %s"%specs['repo']
		#### subprocess.check_call('git clone %s calcs'%specs['repo'],shell=True,cwd=specs['calc'])

		#---modify the default paths in omnicalc to correspond to the paths defined above
		with open(specs['calc']+'/paths.py') as fp: default_paths = fp.read()
		default_paths = {}
		paths_fn = specs['calc']+'/paths.py'
		execfile(paths_fn,default_paths)
		new_paths = deepcopy(default_paths['paths'])
		new_paths['data_spots'] = specs['paths']['data_spots']
		new_paths['post_data_spot'] = settings_paths['postspot']
		new_paths['post_plot_spot'] = settings_paths['plotspot']
		new_paths['workspace_spot'] = root_data_dir+'/workspace'
		#---automatically detect any yaml files in the specs folder
		new_paths['specs_file'] = glob.glob(specs['calc']+'/calcs/specs/meta*.yaml')
		new_paths_file = {'paths':new_paths,'parse_specs':default_paths['parse_specs']}
		with open(paths_fn,'w') as fp:
			fp.write('#!/usr/bin/python\n\n')
			for key in new_paths_file:
				fp.write('%s = %s\n\n'%(key,
				json.dumps(new_paths_file[key],indent=4,ensure_ascii=False).
				replace('\\\\','\\').replace('    ','\t')))
