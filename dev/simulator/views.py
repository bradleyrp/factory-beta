from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.forms import formset_factory
from django.contrib.staticfiles.views import serve
from .forms import *
from .models import *
from .tasks import sherpa
import os,subprocess
import re,glob,shutil,time

def index(request):

	"""
	Simline index holds a list of actions and lists of simulation and protein objects.
	"""

	if request.method == 'GET': 
		form = build_simulation_form()
		form_sources = build_sources_form()
	else:
		form = build_simulation_form(request.POST,request.FILES)
		if form.is_valid():
			sim = form.save(commit=False)
			#---clone automacs
			sim.save()
			#---prepare the simulation
			print '[STATUS] cloning AUTOMACS'
			rootdir = 'simulation-v%05d'%sim.id
			sim.code = rootdir
			settings.DROPSPOT = os.path.join(settings.DROPSPOT,'')
			subprocess.check_call('git clone %s %s'%(settings.AUTOMACS_UPSTREAM,rootdir),
				shell=True,cwd=settings.DROPSPOT)
			subprocess.check_call('make program %s'%sim.program,
				shell=True,cwd=settings.DROPSPOT+sim.code)
			subprocess.check_call('make docs',shell=True,cwd=settings.DROPSPOT+sim.code)
			sim.save()
			return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	allsims = Simulation.objects.all().order_by('id')
	allsources = Source.objects.all().order_by('id')
	return render(request,'simulator/index.html',
		{'form_simulation':form,'allsims':allsims,
		'form_sources':form_sources,'allsources':allsources,
		'alljobs':BackgroundJob.objects.all().order_by('id')})
		
def upload_sources(request):

	"""
	Upload files to a new external source which can be added to future simulations.
	"""

	form = build_simulation_form()
	if request.method == 'GET': form_sources = build_sources_form()
	else:
		if 0 and 'upload_button' in request.POST: print "FOUND UPLOAD BUTTON!"
		form_sources = build_sources_form(request.POST,request.FILES)
		if form_sources.is_valid():
			source = form_sources.save(commit=False)
			source.dropspot = os.path.join(settings.DROPSPOT,'')+'sources/'
			source.save()
			os.mkdir(settings.DROPSPOT+'/sources/%s'%source.folder())
			for filedat in request.FILES.getlist('fileset'):
				with open(settings.DROPSPOT+'/sources/%s/'%source.folder()+'/'+str(filedat),'wb+') as fp:
					for chunk in filedat.chunks(): fp.write(chunk)
			return HttpResponseRedirect(reverse('simulator:index'))
	return render(request,'simulator/index.html',{
		'form_simulation':form,'form_sources':form_sources,
		'allsims':Simulation.objects.all().order_by('id'),
		'allsources':Source.objects.all().order_by('id')})

		
def simulation_script(fn,changes=None):

	"""
	Read (and possibly rewrite) the settings from a simulation script.
	"""
	
	with open(fn) as fp: script = fp.readlines()
	start_line = [ii for ii,i in enumerate(script) if re.match('^import amx',i)][0]
	extract = {}
	exec('\n'.join(script[:[ii for ii,i in enumerate(script) if re.match('^import amx',i)][0]]),extract)
	settings_text = extract['settings']
	if not changes: return settings_text
	else:
		with open(fn,'w') as fp:
			fp.write('#!/usr/bin/python\n')
			fp.write('settings = """\n')
			for key,val in changes: fp.write('%s: %s\n'%(str(key),str(val)))
			fp.write('"""\n')
			for line in script[start_line:]: fp.write(line)

def detail_source(request,id):

	"""
	Show the files in a source.
	"""

	source = get_object_or_404(Source,pk=id)
	for (dirpath,dirnames,filenames) in os.walk(source.dropspot+'/'+source.folder()): break
	fns = '\n'.join(filenames)	
	return render(request,'simulator/source.html',{'files':fns,'source':source})

def detail_simulation(request,id):

	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	URGENT NOTE: sim.dropspot IS DEPRECATED and was replaced with settings.DROPSPOT
	"""

	sim = get_object_or_404(Simulation,pk=id)
	outgoing = {'sim':sim,'path':settings.DROPSPOT+sim.code}
	#---serve the simulation settings in a form if the simulation has not been started
	if request.method=='GET':
		settings_text = simulation_script(settings.DROPSPOT+sim.code+'/script-%s.py'%sim.program)
		if not sim.started:
			settings_text = simulation_script(settings.DROPSPOT+sim.code+'/script-%s.py'%sim.program)
			outgoing['form'] = form_simulation_tune(initial={'settings':settings_text})
		outgoing['settings_text'] = settings_text
	#---interpret any changes to the settings and rewrite the simulation script before submitting
	else:
		form = form_simulation_tune(request.POST,request.FILES)
		sim = get_object_or_404(Simulation,pk=id)
		script_fn = settings.DROPSPOT+sim.code+'/script-%s.py'%sim.program
		settings_text = simulation_script(script_fn)
		regex = '^(\s*[^:]+)\s*:\s+(.+)'		
		settings_order = []
		settings_dict = {}
		for line in settings_text.split('\n'):
			if re.match(regex,line):
				key,val = re.findall(regex,line)[0]
				settings_dict[key] = val
				settings_order.append(key)
		for key,val in form.data.items():
			if key in settings_dict: settings_dict[key] = val
		#---start simulation
		for pk in form.data['incoming_sources']:
			#---if the source is a single PDB we copy that directly
			obj = Source.objects.get(pk=pk)
			source_files = glob.glob(settings.DROPSPOT+'/sources/'+obj.folder()+'/*.pdb')
			if len(source_files) == 1 and re.match('^(.+)\.pdb$',source_files[0]):
				shutil.copyfile(source_files[0],
					settings.DROPSPOT+sim.code+'/inputs/'+os.path.basename(source_files[0]))
				infile = os.path.basename(source_files[0])
				#---for the protein atomistic simulation we autocomplete the start structure field
				if (sim.program == 'protein' and 
					settings_dict['start structure']=='inputs/STRUCTURE.pdb'):
					settings_dict['start structure'] = 'inputs/'+str(infile)			
			elif len(source_files) == 0: raise Exception('no source files in resource %s'%str(obj))
			else: 
				raise Exception('UNDER DEVELOPMENT: not sure how to process source files: %s'
					%str(source_files))
		simulation_script(script_fn,changes=[(key,settings_dict[key]) for key in settings_order])
		this_job = BackgroundJob()
		this_job.simulation = Simulation.objects.get(pk=sim.id)
		this_job.save()
		sherpa.delay(sim.program,this_job.id,cwd=settings.DROPSPOT+sim.code)
		sim.started = True
		sim.save()
		settings_text = simulation_script(settings.DROPSPOT+sim.code+'/script-%s.py'%sim.program)
		outgoing['settings_text'] = settings_text
		return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	return render(request,'simulator/detail.html',outgoing)
	
def background_job_kill(request,id):

	"""
	Kill a background job.
	Note that this must be run from the mplxr root directory!
	"""
	
	this_job = BackgroundJob.objects.get(pk=id)
	print "[STATUS] killing background job with PID: %d"%this_job.pid
	os.system('bash '+settings.DROPSPOT_ABSOLUTE+'/deploy/terminate_children.sh %d'%this_job.pid)
	this_job.delete()	
	return HttpResponseRedirect(reverse('simulator:index'))
	
