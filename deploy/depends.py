#!/usr/bin/python -i
execfile('/etc/pythonstart')

import subprocess,re

"""
Utilities for reporting to the user which packages need to be installed. 
DEVELOPMENT only. Not currently part of the pipeline.
Currently the check_dependencies.sh script checks for the numpy headers.

Assembled the depends library with the following three-step.
	1. Get an error in logs/log-pip that says header.h is missing.
	2. Make sure it's really missing with:
		echo '#include <cblas.h>' | cpp -H -o /dev/null 2>&1
	3. Find a machine that has the header file and then figure out the parent package with:
		rpm -qf /usr/include/cblas.h

PACKAGE NOTES for openSuSE/RPM distributions

started by noticing that computers with healthy development headers had blas packages from the openSuSE science repo and as with deb-based distributions it is important to use the right repos even if they come with good stock headers
started by removing some old packages, particularly libatlas3, libatlas3-devel which have known problems with numpy and just to be sure removed some other common blas-affiliated packages because they are problematic
	sudo zypper remove libatlas3 libatlas3-devel
	sudo zypper remove libcblas3 libblas3 cblas-devel blas-devel
	sudo zypper install cblas-devel blas-devel python-numpy-devel openblas-devel
note that the problem was not solved until openblas-devel and I also threw in python-numpy-devel due to a separate error message
"""

is_rpm,is_deb = False,False
try: isdeb = subprocess.check_call('apt-get --version &>/dev/null',shell=True,executable='/bin/bash')==0
except: pass
try: is_rpm = subprocess.check_call('zypper --version &>/dev/null',shell=True,executable='/bin/bash')==0
except: pass
if is_deb and is_rpm: raise Exception('\n[ERROR] cannot figure out if this system is rpm or deb')
system = 'rpm' if is_rpm else 'deb'
cmd_install = {'rpm':'sudo zypper install','deb':'sudo apt-get install'}
unknown = '???'
depends = {
	'cblas.h':{'rpm':'cblas-devel','deb':unknown,'repo':'science'},
	'cblas_f77.h':{'rpm':'cblas-devel','deb':unknown},
	}

def ask(header_file):

	"""
	Find a header file.
	"""

	oneliner = "echo '#include <%s>' | cpp -H -o /dev/null 2>&1"%header_file
	proc = subprocess.Popen(oneliner,
		cwd='./',shell=True,executable='/bin/bash',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	back = proc.communicate()
	try: return re.findall('^.+\s+(\/.+)',back[0])[0]
	except: return None
	
needs = ['cblas.h','cblas_f77']
missing = [need for need in depends if not ask(need)]
for need in missing:
	print '[NOTE] missing %s'%need,
	if 'repo' in depends[need]: print '(which requires the "%s" repo)'%depends[need]['repo'],
	print 'try "%s %s"'%(cmd_install[system],depends[need][system])
