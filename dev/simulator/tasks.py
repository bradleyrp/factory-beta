from __future__ import absolute_import
from celery import shared_task
from .models import Simulation
import os,subprocess
from django.conf import settings
from .models import Simulation,BackgroundJob,Source
from celery.utils.log import get_task_logger
import time,re,json,glob,shutil
import os

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

logger = get_task_logger(__name__)

@shared_task(track_started=True,default_retry_delay=12*60*60)
def sherpa(program,job_row_id,cwd='./'):

	"""
	Use subprocess and celery to execute a job in the background.
	#python manage.py celeryd --loglevel=INFO
	#python manage.py celery -A multiplexer flower
	"""

	# YOU ABSOLUTELY CANNOT CHANGE THIS FILE WITHOUT RESTARTING THE WORKER !!!

	#---infer the watch file
	detect_last(cwd)
	#---concatenate to the script here
	errorlog = 'script-s%02d-%s.log'%(detect_last(cwd),program)
	print "[STATUS] sherpa is running a job with errors logged to %s"%errorlog
	this_job = BackgroundJob.objects.get(pk=job_row_id)
        if this_job.pid!=-1:
                logger.info("background job row {0} has pid {1}".format(job_row_id,this_job.pid))
                logger.info("leaving kansas")
                return False
	job = subprocess.Popen('./script-%s.py 2>> %s'%(program,errorlog),
		shell=True,cwd=cwd)

        logger.info("submitted job {0} pre-save, row {1}".format(job.pid,job_row_id))
	this_job.pid = job.pid
	this_job.save()
        logger.info("submitted job {0} pre-communicate, row {1}".format(job.pid,job_row_id))
	job.communicate()
	post_job_tasks(program,cwd=cwd+'/s%02d-%s'%(detect_last(cwd),program))
	#---wait to delete the job so that AJAX refreshes the log
	time.sleep(8)
	this_job.delete()
	return True
