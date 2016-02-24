from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.forms import formset_factory
from django.contrib.staticfiles.views import serve
from django.http import JsonResponse
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
		form_sources = build_sources_form()
		if form.is_valid():
			sim = form.save(commit=False)
			#---clone automacs
			sim.save()
			#---prepare the simulation
			print '[STATUS] cloning AUTOMACS'
			rootdir = 'simulation-v%05d'%sim.id
			sim.code = rootdir
			subprocess.check_call('git clone %s %s'%(settings.AUTOMACS_UPSTREAM,rootdir),
				shell=True,cwd=settings.DROPSPOT)
			subprocess.check_call('make program %s'%sim.program,
				shell=True,cwd=settings.DROPSPOT+sim.code)
			subprocess.check_call('source %s/env/bin/activate && make docs'%settings.ROOTSPOT,
				shell=True,cwd=settings.DROPSPOT+sim.code,executable="/bin/bash")
			sim.save()
			return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	allsims = Simulation.objects.all().order_by('id')
	allsources = Source.objects.all().order_by('id')
	modifier = ['','_basic'][0]
	return render(request,'simulator/index%s.html'%modifier,
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

	end_settings_regex = '^(import amx|from amx import)'	
	with open(fn) as fp: script = fp.readlines()
	start_line = [ii for ii,i in enumerate(script) if re.match(end_settings_regex,i)][0]
	extract = {}
	exec('\n'.join(script[:[ii for ii,i in enumerate(script) if re.match(end_settings_regex,i)][0]]),extract)
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
	for (dirpath,dirnames,filenames) in os.walk(settings.DROPSPOT+'/sources/'+source.folder()): break
	fns = '\n'.join(filenames)	
	return render(request,'simulator/source.html',{'files':fns,'source':source})

def find_simulation(code):

	"""
	Utility function to check the DROPSPOT (new simulations) or the DATASPOTS (previous simulations)
	gleaned from the omnicalc paths.py file in order to find a current simulation code.
	"""

	path_candidates = [settings.DROPSPOT]+settings.DATASPOTS
	location, = [pc+'/'+code for pc in path_candidates if os.path.isdir(pc+'/'+code)]
	return location

def detail_simulation(request,id):

	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	URGENT NOTE: sim.dropspot IS DEPRECATED and was replaced with settings.DROPSPOT
	"""

	sim = get_object_or_404(Simulation,pk=id)
	location = find_simulation(sim.code)
	outgoing = {'sim':sim,'path':location}
	simscript = location+'/script-%s.py'%sim.program
	if not os.path.isfile(simscript): 
		return HttpResponse("[ERROR] could not locate %s, perhaps this simulation is old-school?"%simscript)
	#---serve the simulation settings in a form if the simulation has not been started
	if request.method=='GET':
		settings_text = simulation_script(simscript)
		if not sim.started:
			settings_text = simulation_script(simscript)
			outgoing['form'] = form_simulation_tune(initial={'settings':settings_text})
		outgoing['settings_text'] = settings_text
	#---interpret any changes to the settings and rewrite the simulation script before submitting
	else:
		form = form_simulation_tune(request.POST,request.FILES)
		sim = get_object_or_404(Simulation,pk=id)
		script_fn = simscript
		settings_text = simulation_script(script_fn)
		regex = '^(\s*[^:]+)\s*:\s+(.+)'		
		settings_order = []
		settings_dict = {}
		for line in settings_text.split('\n'):
			if re.match(regex,line):
				key,val = re.findall(regex,line)[0]
				settings_dict[key] = val
				settings_order.append(key)
		#---start simulation
		additional_sources,additional_files = [],[]
		if form.is_valid():
			for key,val in form.data.items():
				if key in settings_dict: settings_dict[key] = val
			for pk in form.cleaned_data['incoming_sources']:
				single_pdb = False
				obj = Source.objects.get(pk=pk)
				fns = glob.glob(settings.DROPSPOT+'/sources/'+obj.folder()+'/*')
				#---if only one file and it's a PDB 
				if len(fns) == 1 and re.match('^.+\.(gro|pdb)$',fns[0]):
					#---note the PDB structure name if this is a protein atomistic run
					if (sim.program == 'protein' and 
						settings_dict['start structure']=='inputs/STRUCTURE.pdb'):
						infile = os.path.basename(fns[0])
						settings_dict['start structure'] = 'inputs/'+str(infile)			
					single_pdb = True
				#---if the source is "elevated" then we copy everything from its subfolder into inputs
				if obj.elevate or single_pdb:
					fns = glob.glob(settings.DROPSPOT+'/sources/'+obj.folder()+'/*')
					for fn in fns: 
						shutil.copyfile(fn,settings.DROPSPOT+'/'+sim.code+'/inputs/'+os.path.basename(fn))
					additional_files.append(os.path.basename(fn))
				#---if the source is not elevated we copy its folder into inputs
				#---note downstream codes need a source, they must refer to it by underscored name
				else:
					shutil.copytree(settings.DROPSPOT+'/sources/'+obj.folder(),
						settings.DROPSPOT+'/'+sim.code+'/inputs/'+obj.folder())
					additional_sources.append(obj.folder())
		if additional_sources != []: 
			settings_dict['sources'] = str(additional_sources)
			settings_order.append('sources')
		if additional_files != []: 
			settings_dict['files'] = str(additional_files)
			settings_order.append('files')
		simulation_script(script_fn,changes=[(key,settings_dict[key]) for key in settings_order])
		this_job = BackgroundJob()
		this_job.simulation = Simulation.objects.get(pk=sim.id)
		this_job.save()
		sherpa.delay(sim.program,this_job.id,cwd=location)
		sim.started = True
		sim.save()
		settings_text = simulation_script(simscript)
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
	os.system('bash '+settings.ROOTSPOT+'/deploy/terminate_children.sh %d'%this_job.pid)
	this_job.delete()	
	return HttpResponseRedirect(reverse('simulator:index'))
	
def calculation_monitor(request):

	"""
	Report on a running calculation if one exists.
	"""

	#---only read if jobs are running otherwise ajax will remember the last text
	print BackgroundJob.objects.all()
	if any(BackgroundJob.objects.all()):
		jobs = BackgroundJob.objects.all().order_by('-id')
		dn = next(j for j in jobs if j.pid!=-1).simulation.code
		logs = glob.glob(settings.DROPSPOT+dn+'/*.log')
		last_log = sorted([os.path.basename(g) for g in glob.glob(settings.DROPSPOT+dn+'/*.log')],
			key=lambda x:int(re.findall('^script-s([0-9]+)-.+\.log$',x)[0]))[-1]
		with open(settings.DROPSPOT+dn+'/'+last_log) as fp: lines = fp.readlines()
		return JsonResponse({'line':lines,'running':True})
	else: return JsonResponse({'line':'','running':True})
