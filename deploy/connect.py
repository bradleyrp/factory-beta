#!/usr/bin/python -i
execfile('/etc/pythonstart')

"""
Interpret a user input (typically deploy/connect.yaml) in order to set up the factory.
"""

import os,sys,re,subprocess
import yaml,json

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

	#---! need to make the data spots directory from a list or a string here
	subprocess.check_call('make kickstart %s'%connection_name,shell=True)
	if 0:
		if 0:
			#---if the site is not ready then we kickstart a django project
			if 'site' not in specs and specs['site']!=None: 
				raise Exception('UNDER DEVELOPMENT NEED TO KICKSTART HERE')
			else: 
				if not os.path.isdir('site/'+connection_name):
					subprocess.check_call('ln -s ../dev',shell=True,cwd='./site')
				print "[STATUS] user-supplied django project is at %s"%specs['site']	
			
		#---clone omnicalc if absent
		omnicalc_dir = specs['paths']['calc']
		if os.path.isdir(omnicalc_dir): print "[STATUS] found omnicalc at %s"%omnicalc_dir
		else: 
			os.system('git clone %s %s &> /dev/null'%(specs['omnicalc'],omnicalc_dir))
			print "[STATUS] cloned omnicalc from %s to %s"%(specs['omnicalc'],omnicalc_dir)
			#---make default gromacs.py and paths.py and then override the latter
			os.system('make -C %s config defaults &> /dev/null'%(omnicalc_dir))
			default_paths = {}
			execfile(omnicalc_dir+'/paths.py',default_paths)
			with open(omnicalc_dir+'/paths.py','w') as fp:
				fp.write('#!/usr/bin/python\n')
				fp.write('\nparse_specs = '+
					json.dumps(default_paths['parse_specs'],indent=4).
					replace('\\\\','\\').replace('    ','\t'))
				out_paths = {key:specs['paths'][key] for key in 
					['data_spots','post_data_spot','post_plot_spot','workspace_spot','specs_file']}
				fp.write('\n\npaths = '+json.dumps(out_paths,indent=4).replace('\\\\','\\').
					replace('    ','\t'))
			#---create specs folder and meta.yaml
			os.mkdir(omnicalc_dir+'/calcs/specs/')
			os.system('touch '+omnicalc_dir+'/calcs/specs/meta.yaml')
					
		#---! clone repo if specified
