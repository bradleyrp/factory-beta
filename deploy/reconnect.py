#!/usr/bin/python -i
execfile('/etc/pythonstart')

"""
USEAGE: "make connect (deploy/connect.yaml)"
Completely wipes any local data and sets up projects and connections to omnicalc datasets 
according to the settings in deploy/connect.yaml.
"""

import os,sys,re,subprocess,glob
import yaml

#---unpack arguments
if len(sys.argv)>1: fn = sys.argv[1]
else: fn = "./deploy/connect.yaml"
print "[STATUS] pointed to connect file at %s"%fn
if not os.path.isfile(fn): raise Exception("\n[ERROR] %s is not a file"%fn)

#---settings
APPS = ['simulator','calculator']
variables = {
	'simulator':{'DROPSPOT':'drop','AUTOMACS_UPSTREAM':'automacs'},
	'calculator':{'PLOTSPOT':'plot','AUTOMACS_UPSTREAM':'automacs'},
	}

#---constants
add_app = """echo -e "INSTALLED_APPS = tuple(list(INSTALLED_APPS)+%s)" >> site/%s/%s/settings.py"""
add_settings_variable = """echo -e "%s = '%s'" >> site/%s/%s/settings.py"""
add_urlpatterns = """echo -e "
urlpatterns += [url(r'^%s/',include('%s.urls',namespace='%s'))]" >> site/%s/%s/urls.py"""
add_root_url = '\n'.join([
	"""from django.views.generic.base import RedirectView""",
	"""urlpatterns += [url(r'^$',RedirectView.as_view(url='calculator/',permanent=False),name='index')]"""])

#---ensure that the apps have been packaged
#---note that connect requires kickstart in the makefile which packages the simulator
for app in APPS:
	if not os.path.isdir('pack/%s'%app): 
		os.system("make package %s &> logs/log-pack-%s"%(app,app))

#---read the connection file
with open(fn) as fp: sets = yaml.load(fp.read())

#---loop over connections
for name in sets:
	print "[CONNECT] connecting to \"%s\""%name
	if sets[name]['type'] == 'existing omnicalc':
		os.system("cd site;django-admin startproject %s &> ../logs/log-%s-startproject;"%(name,name))
		os.system(add_app%(str(APPS),name,name))
		for app in APPS: os.system(add_urlpatterns%(app,app,app,name,name))
		os.system("source env/bin/activate;python %s/manage.py migrate &> logs/log-%s-migrate"%(name,name))
		os.system("echo %s >> logs/projects.txt"%name)
		os.mkdir('data/%s'%name)
		os.mkdir('data/%s/sources'%name)
		os.system('git clone %s calc/%s &> logs/log-%s-git'%(sets[name]['omnicalc'],name,name))
		os.system('rm -rf calc/%s/paths.py calc/%s/gromacs.py'%(name,name))
		os.system('make -C calc/%s/ config defaults post=%s plot=%s &> logs/log-omni-config'%
			(name,sets[name]['post'],sets[name]['plot']))
		#---if connecting to an existing omnicalc we add necessary variables to the settings.py
		for key,val in variables['omnicalc'].items(): 
			os.system(add_settings_variable%(key,sets[name][val],name,name))
		os.system('rm -rf calc/%s/calcs'%name)
		os.system('git clone %s calc/%s/calcs &> logs/log-clone-calcs'%(sets[name]['repo'],name))
		print "[STATUS] connected"
	elif sets[name]['type'] == 'new':
		os.system('make kickstart %s'%name)
		os.system("echo %s >> logs/projects.txt"%name)
		#---if connecting to an existing omnicalc we add necessary variables to the settings.py
		for key,val in variables['simulator'].items(): 
			os.system(add_settings_variable%(key,sets[name][val],name,name))
		for app in APPS: os.system(add_urlpatterns%(app,app,app,name,name))
	else: raise Exception('unclear connection type')
	if 'write' in sets[name]: os.system('git clone %s ./write/write-%s &> logs/log-git-clone-write-%s'%(
		sets[name]['write'],name,name))
	os.system(add_settings_variable%('PROJECT_NAME',name,name,name))
	with open('site/%s/%s/urls.py'%(name,name),'a') as fp: fp.write(add_root_url) 
	addlines = ["\nfrom django.conf.urls.static import static",
	"""urlpatterns += static('/write/',document_root='/home/localshare/analysis/mplxr/write/')\n"""]
	with open('site/%s/%s/urls.py'%(name,name),'a') as fp: fp.write('\n'.join(addlines)) 
		
