#!env/bin/python

"""
Interpret a user input (typically connect.yaml) in order to set up the "factory".
See connect.yaml for example connections.

This file either creates a new "connection" from scratch OR updates any changes to a "connection" described
in the yaml file. This incremental design is key to developing these codes on-the-fly and allowing for many
varied use cases to work in the same pipeline. The use cases are provided as examples in the default yaml 
file. 

NEEDS LIST OF IMPORTANT FLAGS
"""

import os,sys,re,subprocess,shutil,glob,json
from copy import deepcopy
import yaml

#---user must supply the yaml file to describe the connections
if len(sys.argv)!=2: raise Exception('\n[USAGE] make connect <yaml>') 
with open(sys.argv[1]) as fp: sets = yaml.load(fp.read())
#---ignore examples (and later we will skip any entries with "enabled: false")
if 'examples' in sets: del sets['examples']

#---disallow any project named dev to protect the codes in that folder
if any([i=='dev' for i in sets]): 
	raise Exception('[ERROR] cannot name a project "dev" in %s'%sys.argv[1])

#---APPENDAGES
#-------------------------------------------------------------------------------------------------------------

urls_additions = """
#---automatically added
from django.conf.urls import include, url
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
CELERY_ACKS_LATE = False
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

lockdown_extra = """
INSTALLED_APPS = tuple(list(INSTALLED_APPS)+['lockdown'])
LOCKDOWN_PASSWORDS = ('%s')
MIDDLEWARE_CLASSES = tuple(list(MIDDLEWARE_CLASSES)+['lockdown.middleware.LockdownMiddleware'])
LOCKDOWN_FORM = 'lockdown.forms.LockdownForm'
"""

get_omni_dataspots = """if os.path.isfile(CALCSPOT+'/paths.py'):
    omni_paths = {};execfile(CALCSPOT+'/paths.py',omni_paths)
    DATASPOTS = omni_paths['paths']['data_spots']
    del omni_paths
"""

#---permission settings for apache
media_segment = """
    Alias %s "%s"
    <Directory %s>
        Require all granted
    </Directory> 
"""

#---! note previously used "Options Indexes FollowSymLinks" for write directories
vhost_config = """
#---to serve FACTORY:
#---install apache2 and WSGI
#---copy this file to /etc/apache2/vhosts.d/
#---add "WSGIPythonPath /home/localshare/analysis/mplxr/env" to httpd.conf and substitue paths below
#---restart apache
<VirtualHost *:%d>
    ServerName %s
    ServerAlias factory
    DocumentRoot %s
%s
    WSGIScriptAlias / %s
    WSGIDaemonProcess factory python-path=%s:%s:%s
    WSGIProcessGroup factory
    <Directory %s>
    	Order allow,deny
    	Allow from all
    	Require all granted
    </Directory>
</VirtualHost>
"""

def prepare_vhosts(rootdir,connection_name,port=None,dev=True):

	"""
	Prepare virtualhost configuration for users to serve over apache2.
	"""

	site_packages = 'env/lib/python2.7/site-packages'
	#---we append the root directory to these media locations
	aliases = {
		'/static/calculator/':os.path.join(rootdir,'dev' if dev else site_packages,
			'calculator/static/calculator',''),
		'/static/simulator/':os.path.join(rootdir,'dev' if dev else site_packages,
			'simulator/static/simulator',''),
		}
	#---generic server settings
	serveset = {
		'port':88,
		'domain':'127.0.0.1',
		'document_root':os.path.join(rootdir,'site',connection_name,''),
		}
	alias_conf = ''
	for key,val in aliases.items(): 
		alias_conf += media_segment%(key,val,val)
	conf = vhost_config%(
		serveset['port'] if not port else port,
		serveset['domain'],
		serveset['document_root'],
		alias_conf,
		os.path.join(rootdir,'site',connection_name,connection_name,'wsgi.py'),
		os.path.join(rootdir,'site',connection_name,''),
		#---add dev early
		os.path.join(rootdir,'dev',''), 
		os.path.join(rootdir,site_packages),
		rootdir)
	return conf

def abspath(path): return os.path.join(os.path.expanduser(os.path.abspath(path)),'')

def mkdir_or_report(dn):

	if os.path.isdir(dn): print "[STATUS] found %s"%(dn)
	else: 
		os.mkdir(dn)
		print "[STATUS] created %s"%dn

#---the development path must be within the factory
absolute_environment_path = abspath('env')

def bash(cmd,log=None,cwd='./',env=False):
	if env: cmd = 'source %s/bin/activate && %s'%(absolute_environment_path,cmd)
	if log:
		output = open(log,'wb')
		subprocess.check_call(cmd,cwd=cwd,shell=True,executable='/bin/bash',stdout=output,stderr=output)
	else: subprocess.check_call(cmd,cwd=cwd,shell=True,executable='/bin/bash')

#---handle the environment
if not os.path.isdir('env'):
	raise Exception('\n[ERROR] no environment. run "make env [system]" to create one')

#---MAIN
#-------------------------------------------------------------------------------------------------------------

#---master loop over all connections
for connection_name,specs in sets.items():

	#---skip a connection if enabled is false
	if not specs.get('enable',True): continue

	#---the site is equivalent to a django project
	#---the site draws on either prepackaged apps in the pack folder or the in-development versions in dev
	#---since the site has no additional data except taht specified in connect.yaml, we can always remake it
	if os.path.isdir('site/'+connection_name):
		print "[STATUS] removing the site for \"%s\" to remake it"%connection_name
		shutil.rmtree('site/'+connection_name)

	#---regex PROJECT_NAME to the connection names in the paths sub-dictionary	
	#---note that "PROJECT_NAME" is therefore protected and always refers to the top-level key in connect.yaml
	#---! note that you cannot use PROJECT_NAME in spots currently
	for key,val in specs.items():
		if type(val)==str: specs[key] = re.sub('PROJECT_NAME',connection_name,val)
		elif type(val)==list:
			for ii,i in enumerate(val): val[ii] = re.sub('PROJECT_NAME',connection_name,i)

	#---make local directories if they are absent or do nothing if the user points to existing data
	root_data_dir = 'data/'+connection_name
	#---always make data/PROJECT_NAME for the default simulation_spot therein
	mkdir_or_report(root_data_dir)
	for key in ['post_data_spot','post_plot_spot','simulation_spot']: 
		mkdir_or_report(abspath(specs[key]))
	#---we always include a "sources" folder in the new simulation spot for storing input files
	mkdir_or_report(abspath(specs['simulation_spot']+'/sources/'))

	#---check if database exists and if so, don't make superuser
	make_superuser = not os.path.isfile(specs['database'])

	#---interpret paths from connect.yaml for PROJECT_NAME/PROJECT_NAME/settings.py in the django project
	#---these paths are all relative to the rootspot, the top directory for the factory codes
	settings_paths = {
		'rootspot':os.path.join(os.getcwd(),''),
		'automacs_upstream':specs['automacs'],
		'project_name':connection_name,
		'plotspot':abspath(specs['post_plot_spot']),
		'postspot':abspath(specs['post_data_spot']),
		'dropspot':abspath(specs['simulation_spot']),
		'calcspot':specs['calc'],
		}

	#---prepare additions to the settings.py and urls.py
	settings_append_fn = 'logs/setup-%s-settings-append.py'%connection_name
	urls_append_fn = 'logs/setup-%s-urls-append.py'%connection_name
	with open(settings_append_fn,'w') as fp:
		if 'development' in specs and specs['development']: 
			devpath = "import sys;sys.path.insert(0,os.getcwd()+'/dev/')" 
		else: devpath = ""
		fp.write(devpath+setings_additions)
		for key,val in settings_paths.items():
			fp.write('%s = "%s"\n'%(key.upper(),val))
		for key in ['PLOTSPOT','POSTSPOT','ROOTSPOT']: 
			fp.write('%s = os.path.expanduser(os.path.abspath(%s))\n'%(key,key))
		#---must specify a database location
		if 'database' in specs: 
			fp.write("DATABASES['default']['NAME'] = \"%s\"\n"%os.path.abspath(specs['database']))
		if 'lockdown' in specs: fp.write(lockdown_extra%specs['lockdown'])
		fp.write(get_omni_dataspots)
	with open(urls_append_fn,'w') as fp: fp.write(urls_additions)

	#---replacing bash script kickstart.sh here
	#---to run from python we have to drop into the enviroment every time
	drop = 'source env/bin/activate && '
	for app in ['simulator','calculator']:
		if not os.path.isdir('pack/%s'%app): bash(drop+'make -s package %s'%app,log='logs/log-pack-%s'%app)
	bash('django-admin startproject %s'%connection_name,
		log='logs/log-%s-startproject'%connection_name,cwd='site/',env=True)
	bash('cat %s >> site/%s/%s/settings.py'%(settings_append_fn,connection_name,connection_name))
	bash('cat %s >> site/%s/%s/urls.py'%(urls_append_fn,connection_name,connection_name))
	if not os.path.isdir('calc/%s'%connection_name):
		bash('git clone %s calc/%s'%(specs['omnicalc'],connection_name),
			 log='logs/log-%s-git-omni'%connection_name)
	if not os.path.isdir('data/%s/sims/docs'%connection_name):
		bash('git clone %s data/%s/sims/docs'%(specs['automacs'],connection_name),
			log='logs/log-%s-git-amx'%connection_name)
	bash('make docs',cwd='data/%s/sims/docs'%connection_name,
		log='logs/log-%s-automacs-docs'%connection_name,env=True)
	#---! no more config?
	#bash('make config defaults',cwd='calc/%s'%connection_name,
	#	log='logs/log-%s-omnicalc-config'%connection_name,env=True)
	for dn in ['calc/%s/calcs'%connection_name,'calc/%s/calcs/scripts'%connection_name]: 
		if not os.path.isdir(dn): os.mkdir(dn)
	bash('make docs',cwd='calc/%s'%connection_name,log='logs/log-%s-omnicalc-docs'%connection_name,env=True)
	shutil.copy('deploy/celery_source.py','site/%s/%s/celery.py'%(connection_name,connection_name))
	bash('sed -i "s/multiplexer/%s/g" site/%s/%s/celery.py'%
		(connection_name,connection_name,connection_name))	
	bash('python site/%s/manage.py migrate'%connection_name,
		log='logs/log-%s-migrate'%connection_name,env=True)
	if make_superuser:
		print "[STATUS] making superuser"
		su_script = "from django.contrib.auth.models import User; "+\
			"User.objects.create_superuser('admin','','admin');print;quit();"
		p = subprocess.Popen('source %s/bin/activate && python ./site/%s/manage.py shell'%(
			absolute_environment_path,connection_name),		
			stdin=subprocess.PIPE,stderr=subprocess.PIPE,stdout=open(os.devnull,'w'),
			shell=True,executable='/bin/bash')
		catch = p.communicate(input=su_script)[0]
	print "[STATUS] new project \"%s\" is stored at ./data/%s"%(connection_name,connection_name)
	print "[STATUS] replace with a symlink if you wish to store the data elsewhere"
	#---done kickstart

	#---remove blank calcs and local post/plot from default omnicalc configuration
	for folder in ['post','plot','calcs']:
		dn = 'calc/%s/%s'%(connection_name,folder)
		if os.path.isdir(dn): shutil.rmtree(dn)

	#---if the repo points nowhere we prepare a calcs folder for omnicalc (repo is required)
	new_calcs_repo = not (os.path.isdir(specs['repo']) and (
		os.path.isdir(specs['repo']+'/.git') or os.path.isfile(specs['repo']+'/HEAD')))
	if new_calcs_repo:
		print "[STATUS] repo path %s does not exist so we are making a new one"%specs['repo']
		mkdir_or_report(specs['calc']+'/calcs')
		bash('git init',cwd=specs['calc']+'/calcs',log='logs/log-%s-new-calcs-repo')
		#---! AUTO POPULATE WITH CALCULATIONS HERE
	#---if the repo is a viable git repo then we clone it
	else: 
		bash('git clone '+specs['repo']+' '+specs['calc']+'/calcs',cwd='./',
			log='logs/log-%s-clone-calcs-repo'%connection_name)
	
	#---create directories if they are missing
	mkdir_or_report(specs['calc']+'/calcs/specs/')
	mkdir_or_report(specs['calc']+'/calcs/scripts/')
	subprocess.check_call('touch __init__.py',cwd=specs['calc']+'/calcs/scripts',
		shell=True,executable='/bin/bash')

	#---if startup then we load some common calculations (continued below)
	if specs['startup']: 
		for fn in glob.glob('deploy/preloads/*'): shutil.copy(fn,specs['calc']+'/calcs/')
	#---! add these calculations to the database (possibly for FACTORY)
	if 0: subprocess.check_call(
		'source env/bin/activate && python ./deploy/register_calculation.py %s %s %s'%
		(specs['site'],connection_name,specs['calc']),shell=True,executable='/bin/bash')

	#---write the paths.yaml for the new omnicalc with the correct spots, paths, etc
	with open(os.path.join(specs['calc'],'paths.yaml')) as fp: default_paths = yaml.load(fp.read())
	default_paths['post_data_spot'] = settings_paths['postspot']
	default_paths['post_plot_spot'] = settings_paths['plotspot']
	default_paths['workspace_spot'] = abspath(specs['workspace_spot'])
	default_paths['timekeeper'] = specs.get('timekeeper',False)
	default_paths['spots'] = specs['spots']
	#---in case spots refers to a local directory we use full paths
	for spotname in specs['spots']:
		specs['spots'][spotname]['route_to_data'] = re.sub(
			'PROJECT_NAME',connection_name,os.path.abspath(specs['spots'][spotname]['route_to_data']))
	#---final substitutions so PROJECT_NAME can be used anywhere
	with open(os.path.join(specs['calc'],'paths.yaml'),'w') as fp: 
		fp.write(re.sub('PROJECT_NAME',connection_name,yaml.dump(default_paths)))
	
	#---previous omnicalc users may have a specific gromacs.py that they wish to use
	if 'omni_gromacs_config' in specs and specs['omni_gromacs_config']:
		gromacs_fn = os.path.abspath(os.path.expanduser(specs['omni_gromacs_config']))
		shutil.copyfile(gromacs_fn,specs['calc']+'/gromacs.py')

	#---assimilate old data if available
	subprocess.check_call('source env/bin/activate && make -s -C '+specs['calc']+' export_to_factory %s %s'%
		(connection_name,settings_paths['rootspot']+specs['site']),shell=True,executable='/bin/bash')
	print "[STATUS] got omnicalc errors? try git pull to stay current"
	#---prepare a vhost file
	conf = prepare_vhosts(os.getcwd(),connection_name,port=None if 'port' not in specs else specs['port'])
	with open('logs/vhost_%s.conf'%connection_name,'w') as fp: fp.write(conf)
	print "[STATUS] connected %s!"%connection_name
	print "[STATUS] start with \"make run %s\""%connection_name
