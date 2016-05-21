from __future__ import absolute_import
from celery import shared_task
from .models import Simulation
import os,subprocess,re
from django.conf import settings
from .models import Simulation,Source
from celery.utils.log import get_task_logger
import time,re,json,glob,shutil,os
from billiard.exceptions import Terminated
from celery.signals import task_revoked

logger = get_task_logger(__name__)

def post_job_tasks(program,cwd):

	"""
	Method-specific cleanup tasks.
	"""

	if program=='homology':
		best_pointer = cwd+'/best_structure_path'
		if os.path.isfile(best_pointer):
			with open(best_pointer) as fp: bsp = fp.read()
			best = re.search('[\w0-9\.]+\.pdb',bsp).group()
			new_source = Source(name=best.rstrip('\.pdb'),elevate=False)
			new_source.save()
			os.mkdir(settings.DROPSPOT+'/sources/%s'%new_source.folder())
			shutil.copy(cwd+'/'+best,settings.DROPSPOT+'sources/%s'%new_source.folder())
	else: print "[WARNING] no post_job_tasks for method %s"%program

def detect_last(cwd):

	"""
	Find the last step number and part number (if available).
	"""

	step_regex = '^s([0-9]+)-\w+$'
	part_regex = '^[^\/]+\/md\.part([0-9]{4})\.cpt' 
	possible_steps = [i for i in glob.glob(cwd+'/s*-*') if os.path.isdir(i)]
	try:
		last_step = max(map(
			lambda z:int(z),map(
			lambda y:re.findall(step_regex,y).pop(),filter(
			lambda x:re.match(step_regex,x),possible_steps))))
	except: last_step = 0
	return last_step + 1

@shared_task(track_started=True,max_retries=0,bind=True,throws=(Terminated,))
def old_sherpa(self,program,**kwargs):

	"""
	Use subprocess and celery to execute a job in the background.
	YOU ABSOLUTELY CANNOT CHANGE THIS FILE WITHOUT RESTARTING THE WORKER!!!
	"""

	#---infer the watch file
	cwd = kwargs.get('cwd','./')
	detect_last(cwd)
	metarun = kwargs.get('metarun',None)
	if not metarun:
		#---concatenate to the script here
		errorlog = 'script-s%02d-%s.log'%(detect_last(cwd),program)
		print "[STATUS] sherpa is running a job with errors logged to %s"%errorlog
		job = subprocess.Popen('./script-%s.py 2>> %s'%(program,errorlog),
			shell=True,cwd=cwd,preexec_fn=os.setsid)
	else: 
		#---concatenate to the script here
		metarun_short = re.match('^(.+)\.py$',metarun).group(1)
		errorlog = 'script-%s.log'%(metarun_short)
		print "[STATUS] sherpa is running a METARUN job with errors logged to %s"%errorlog
		job = subprocess.Popen('make metarun %s 2>> %s'%(metarun_short,errorlog),
			shell=True,cwd=cwd,preexec_fn=os.setsid)
	pid_log = os.path.join(cwd,'PID.log')
	with open(pid_log,'w') as fp: fp.write('%d'%job.pid)
	job.communicate()
	#---rpb notes that some PID.log files were not removed, particularly on zombie jobs
	if os.path.isfile(pid_log): os.remove(pid_log)
	post_job_tasks(program,cwd=cwd+'/s%02d-%s'%(detect_last(cwd),program))

@shared_task(track_started=True,max_retries=0,bind=True,throws=(Terminated,))
def old_sherpa(self,program,**kwargs):

	"""
	Use subprocess and celery to execute a job in the background.
	YOU ABSOLUTELY CANNOT CHANGE THIS FILE WITHOUT RESTARTING THE WORKER!!!
	"""

	#---infer the watch file
	cwd = kwargs.get('cwd','./')
	detect_last(cwd)
	metarun = kwargs.get('metarun',None)
	if not metarun:
		#---concatenate to the script here
		errorlog = 'script-s%02d-%s.log'%(detect_last(cwd),program)
		print "[STATUS] sherpa is running a job with errors logged to %s"%errorlog
		job = subprocess.Popen('./script-%s.py 2>> %s'%(program,errorlog),
			shell=True,cwd=cwd,preexec_fn=os.setsid)
	else: 
		#---concatenate to the script here
		metarun_short = re.match('^(.+)\.py$',metarun).group(1)
		errorlog = 'script-%s.log'%(metarun_short)
		print "[STATUS] sherpa is running a METARUN job with errors logged to %s"%errorlog

	job = subprocess.Popen(cmd,shell=True,cwd=cwd,preexec_fn=os.setsid)
	job.communicate()
	pid_log = os.path.join(cwd,'PID.log')
	with open(pid_log,'w') as fp: fp.write('%d'%job.pid)
	job.communicate()
	if os.path.isfile(pid_log): os.remove(pid_log)
	post_job_tasks(program,cwd=cwd+'/s%02d-%s'%(detect_last(cwd),program))

@task_revoked.connect()
def job_revoked(*args,**kwargs):

	"""
	Kill the job when celery revokes it.
	"""

	request = kwargs['request']
	print '[STATUS] revoking request '+str(request)
	cwd = request.kwargs['cwd']
	pid_log = os.path.join(cwd,'PID.log')
	with open(pid_log) as fp: pid = int(re.search('([0-9]+)',fp.read()).group())
	print '[STATUS] killing PID %d and company'%pid
	#---kill the group related to the session leader
	os.system('pkill -TERM -g %d'%pid)
