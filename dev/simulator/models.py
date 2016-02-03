from django.db import models
from django.core.files.storage import Storage
from django.conf import settings
import shutil,os,re

class Source(models.Model):

	"""
	A generic input file for a simulation.
	"""
	
	name = models.CharField(max_length=100,default='',unique=True)
	def __str__(self): return self.name

	def folder(self):

		"""
		Remove spaces from folder names.
		"""

		return re.sub(' ','_',self.name)

	def delete(self):

		"""
		Remove the simulation directory via the admin page.
		"""

		print '[STATUS] deleting source %s'%self.name
		shutil.rmtree(settings.DROPSPOT+'/sources/'+self.folder())
		print '[STATUS] done'
		super(Source,self).delete()

	
class Simulation(models.Model):

	"""
	A simulation executed by automacs.
	"""

	class Meta:
		verbose_name = 'AUTOMACS simulation'

	name = models.CharField(max_length=100,unique=True)
	program_choices = ['protein','cgmd-bilayer']
	program = models.CharField(max_length=30,choices=[(i,i) for i in program_choices],default='protein')
	started = models.BooleanField(default=False)
	code = models.CharField(max_length=200,unique=True)
	sources = models.ManyToManyField(Source)
	time_sequence = models.CharField(max_length=100,default='')
	def __str__(self): return self.name

	def delete(self):

		"""
		Remove the simulation directory via the admin page.
		"""

		print '[STATUS] deleting simulation %s'%self.name
		if re.match('^\s*$',self.code): raise Exception('blank code so cannot delete the simulation')
		shutil.rmtree(settings.DROPSPOT+'/'+self.code)
		print '[STATUS] done'
		super(Simulation,self).delete()

class BackgroundJob(models.Model):

	"""
	A job running in the background.
	"""

	class Meta:
		verbose_name = 'Background Job'
	def __str__(self): return 'PID '+str(self.pid)
	pid = models.IntegerField(default=-1)
	print os.getcwd()
	simulation = models.ForeignKey(Simulation,on_delete=models.CASCADE)

	
