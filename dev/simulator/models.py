from django.db import models
from django.core.files.storage import Storage
from django.conf import settings
import shutil,os,re,subprocess

#---global copy of the default program list also used in forms.py
default_programs = ['protein','cgmd-bilayer','homology']

class SourceQuerySet(models.QuerySet):
	
	"""
	Must accompany the custom delete in the model for bulk deletion.
	"""

	def delete(self,*args,**kwargs):
		for obj in self: obj.delete()
		super(SourceQuerySet,self).delete(*args,**kwargs)

class Source(models.Model):

	"""
	A generic input file for a simulation.
	"""
	
	objects = SourceQuerySet.as_manager()
	name = models.CharField(max_length=100,default='',unique=True)
	elevate = models.BooleanField(default=False)
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
		if not os.path.isdir(settings.DROPSPOT+'/sources/'+self.folder()):
			print '[WARNING] that source cannot be found or deleted'
		else: shutil.rmtree(settings.DROPSPOT+'/sources/'+self.folder())
		print '[STATUS] done'
		super(Source,self).delete()

class SimulationQuerySet(models.QuerySet):
	
	"""
	Must accompany the custom delete in the model for bulk deletion.
	"""

	def delete(self,*args,**kwargs):
		for obj in self: obj.delete()
		super(SimulationQuerySet,self).delete(*args,**kwargs)


class Bundle(models.Model):

	"""
	A pointer to a git repository that contains a pre-made simulation procedure.
	The repo will be cloned into inputs before running the simulation.
	"""
	
	name = models.CharField(max_length=100,default='',unique=True)
	path = models.CharField(max_length=200,unique=False,blank=False)
	def __str__(self): return self.name

	class Meta:
		verbose_name = 'AUTOMACS bundle'

def get_program_choices():

	"""
	Collect a list of simulation protocols.
	"""

	#---add metaruns to program choices
	program_choices = []
	for pk,path in [[obj.pk,obj.path] for obj in Bundle.objects.all()]:
		kwargs = dict(shell=True,executable="/bin/bash",stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		proc = subprocess.Popen("git -C %s ls-tree --full-tree -r HEAD"%
			os.path.abspath(os.path.expanduser(path)),**kwargs)
		ans = '\n'.join(proc.communicate())
		regex = '^[0-9]+\s*[^\s]+\s*[^\s]+\s*(metarun[^\s]+)'
		for m in [re.findall(regex,i)[0] for i in ans.split('\n') if re.match(regex,i)]:
			program_choices.append(obj.name+' > '+m)
	return program_choices

class Simulation(models.Model):

	"""
	A simulation executed by automacs.
	"""

	objects = SimulationQuerySet.as_manager()

	class Meta:
		verbose_name = 'AUTOMACS simulation'

	name = models.CharField(max_length=100,unique=True)
	try: program_choices = default_programs + list(get_program_choices())
	except: program_choices = default_programs
	program = models.CharField(max_length=100,choices=[(i,i) for i in program_choices],default='protein')
	started = models.BooleanField(default=False)
	code = models.CharField(max_length=200,unique=True,blank=True)
	sources = models.ManyToManyField(Source)
	time_sequence = models.CharField(max_length=100,default='')
	def __str__(self): return self.name

	def delete(self):

		"""
		Remove the simulation directory via the admin page.
		"""

		print '[STATUS] deleting simulation %s'%self.name
		#---removed exception if the code is blank and now allow deletion even if no folder
		if re.match('^\s*$',self.code) or not os.path.isdir(settings.DROPSPOT+self.code):
			print '[WARNING] that simulation cannot be found or deleted (code="%s")'%self.code
		else: shutil.rmtree(settings.DROPSPOT+'/'+self.code)
		print '[STATUS] done'
		super(Simulation,self).delete()
