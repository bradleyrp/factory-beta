from __future__ import absolute_import
from celery import shared_task
from .models import Simulation
import os,subprocess
from django.conf import settings
from .models import Simulation,BackgroundJob
import time

@shared_task(track_started=True)
def sherpa(program,job_row_id,cwd='./'):

	"""
	Use subprocess and celery to execute a job in the background.
	#python manage.py celeryd --loglevel=INFO
	#python manage.py celery -A multiplexer flower
	"""

	job = subprocess.Popen('./script-%s.py'%program,
		shell=True,cwd=settings.ROOTSPOT+'/'+cwd)
	this_job = BackgroundJob.objects.get(pk=job_row_id)
	this_job.pid = job.pid
	this_job.save()
	job.communicate()
	this_job.delete()
	return
