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

#---maintain a list of possible (upstream) data spot locations
lookup_spotnames = {}

def prepare_simulation(sim):

	"""
	Prepare a simulation given an incomplete row.
	"""

	#---! need to make the naming systematic
	rootdir = 'simulation-v%05d'%sim.id
	if os.path.isdir(rootdir): 
		HttpResponse('[ERROR] %s already exists so '+
			'we cannot use this code to make a new simulation. '+
			'you probably need to move or delete that folder. '+
			'try moving to another dropspot'%rootdir)
	sim.code = rootdir
	subprocess.check_call('git clone %s %s'%(settings.AUTOMACS_UPSTREAM,rootdir),
		shell=True,cwd=settings.DROPSPOT)
	subprocess.check_call('make program %s'%sim.program,
		shell=True,cwd=os.path.join(settings.DROPSPOT,sim.code),executable="/bin/bash")
	subprocess.check_call('source %s/env/bin/activate && make docs'%settings.ROOTSPOT,
		shell=True,cwd=os.path.join(settings.DROPSPOT,sim.code),executable="/bin/bash")
	sim.save()

def prepare_source(source,sim,settings_dict,single_pdb=False):

	"""
	Prepare a source before running a simulation.
	"""

	additional_files,additional_sources = [],[]
	fns = glob.glob(settings.DROPSPOT+'/sources/'+source.folder()+'/*')
	#---if only one file and it's a PDB 
	if len(fns) == 1 and re.match('^.+\.(gro|pdb)$',fns[0]):
		#---note the PDB structure name if this is a protein atomistic run
		if (sim.program == 'protein' and 
			settings_dict['start structure']=='inputs/STRUCTURE.pdb'):
			infile = os.path.basename(fns[0])
			settings_dict['start structure'] = 'inputs/'+str(infile)			
		elif (sim.program == 'homology' and 
			settings_dict['template']=='inputs/STRUCTURE.pdb'):
			infile = os.path.basename(fns[0])
			settings_dict['template'] = 'inputs/'+str(infile)
		single_pdb = True
	#---if the source is "elevated" then we copy everything from its subfolder into inputs
	if source.elevate or single_pdb:
		fns = glob.glob(settings.DROPSPOT+'/sources/'+source.folder()+'/*')
		for fn in fns: 
			shutil.copyfile(fn,find_simulation(sim.code)+'/inputs/'+os.path.basename(fn))
		additional_files.append(os.path.basename(fn))
	#---if the source is not elevated we copy its folder into inputs
	#---note downstream codes need a source, they must refer to it by underscored name
	else:
		shutil.copytree(settings.DROPSPOT+'/sources/'+source.folder(),
			find_simulation(sim.code)+'/inputs/'+source.folder())
		additional_sources.append(source.folder())
	return additional_files,additional_sources

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
			#---save to set the pk which determines the folder
			sim.save()
			prepare_simulation(sim)
			return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	allsims = Simulation.objects.all().order_by('id')
	allsources = Source.objects.all().order_by('id')
	modifier = ['','_basic'][0]
	return render(request,'simulator/index%s.html'%modifier,{
		'form_simulation':form,'allsims':allsims,
		'form_sources':form_sources,'allsources':allsources,
		'CELERYPORT':settings.CELERYPORT,
		})
		
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
	exec('\n'.join(script[:[ii for ii,i in enumerate(script) 
		if re.match(end_settings_regex,i)][0]]),extract)
	settings_text = extract['settings']
	if changes:
		altered_settings_text = ''.join(['%s: %s\n'%(str(key),str(val)) for key,val in changes.items()])
		with open(fn,'w') as fp:
			fp.write('#!/usr/bin/python\n')
			fp.write('settings = """\n')
			fp.write(altered_settings_text)
			fp.write('"""\n')
			for line in script[start_line:]: fp.write(line)
		settings_text = altered_settings_text
	#---parse the text on the way out
	regex = '^(\s*[^:]+)\s*:\s+(.+)'		
	settings_dict,settings_order = {},[]
	for line in settings_text.split('\n'):
		if re.match(regex,line):
			key,val = re.findall(regex,line)[0]
			settings_dict[key] = val
			settings_order.append(key)
	else: return {'text':settings_text,'dict':settings_dict,'order':settings_order}

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
	Check all spots for a simulation code.
	Check omnicalc for spotnames for each simulation and accumulate them in lookup_spotnames.
	"""

	global lookup_spotnames
	if code not in lookup_spotnames: 
		proc = subprocess.Popen('make look',cwd=settings.CALCSPOT,
			shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.PIPE)
		catch = proc.communicate(
			input="print '>>>'+work.spotname_lookup('%s')\nsys.exit()\n'"%str(code))
		try: 
			regex = '^>>>([^\s]+)$'
			selected, = [re.findall(regex,i)[0] for i in ('\n'.join(catch)).split('\n') if re.match(regex,i)]
			spotname = str(selected)
			lookup_spotnames[code] = spotname
			print '[NOTE] found %s under spotname "%s"'%(code,spotname)
		except Exception as e:
			print '[WARNING] failed to find "%s" in omnicalc so perhaps '%code+\
				'it is new returning dropspot+code'
			return os.path.join(settings.DROPSPOT,code)
		return os.path.join(settings.PATHFINDER[lookup_spotnames[code]],code)

def detail_simulation(request,id):

	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	"""

	sim = get_object_or_404(Simulation,pk=id)
	location = find_simulation(sim.code)
	outgoing = {'sim':sim,'path':location}
	simscript = location+'/script-%s.py'%sim.program
	if not os.path.isfile(simscript): 
		return HttpResponse("[ERROR] could not locate %s, perhaps this simulation is old-school?"%simscript)
	#---serve the simulation settings in a form if the simulation has not been started
	if request.method=='GET':
		settings_text = simulation_script(simscript)['text']
		if not sim.started: outgoing['form'] = form_simulation_tune(initial={'settings':settings_text})
		outgoing['settings_text'] = re.sub('\n\n','\n',settings_text)
	#---interpret any changes to the settings and rewrite the simulation script before submitting
	else:
		form = form_simulation_tune(request.POST,request.FILES)
		sim = get_object_or_404(Simulation,pk=id)
		script_fn = simscript
		scriptset = simulation_script(script_fn)
		settings_text,settings_dict,settings_order = [scriptset[i] for i in ['text','dict','order']]
		#---start simulation
		additional_sources,additional_files = [],[]
		if form.is_valid():
			for key,val in form.data.items():
				if key in settings_dict: settings_dict[key] = val
			for pk in form.cleaned_data['incoming_sources']:
				obj = Source.objects.get(pk=pk)
				extra_files,extra_sources = prepare_source(obj,sim,settings_dict=settings_dict)
				additional_files.extend(extra_files)
				additional_sources.extend(extra_sources)
		if additional_sources != []: 
			settings_dict['sources'] = str(additional_sources)
			settings_order.append('sources')
		if additional_files != []: 
			settings_dict['files'] = str(additional_files)
			settings_order.append('files')
		#---prepare the simulation script
		scriptset = simulation_script(script_fn,changes=[(key,settings_dict[key]) for key in settings_order])
		#---previously: sherpa.delay(sim.program,this_job.id,cwd=location)
		#---send the simulation to the worker
		sherpa.apply_async(args=(sim.program,),kwargs={'cwd':location},retry=False)
		sim.started = True
		sim.save()
		#---replace the settings in the original script with the updated copy
		outgoing['settings_text'] = scriptset['text']
		return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	return render(request,'simulator/detail.html',outgoing)
	
def calculation_monitor(request,debug=False):

	"""
	Report on a running calculation if one exists.
	"""

	try:	
		dn = os.path.dirname(max(
			glob.iglob(settings.DROPSPOT+'/*/script-*.py'),key=os.path.getctime))
		last_log = sorted([os.path.basename(g) for g in glob.glob(dn+'/script*.log')],
			key=lambda x:int(re.findall('script-s([0-9]+)-.+\.log$',x)[0]))[-1]
		with open(dn+'/'+last_log) as fp: lines = fp.readlines()
		return JsonResponse({'line':lines,'running':True})
	except: return JsonResponse({'line':'idle','running':False})

def queue_monitor(request):

	"""
	Report on a running calculation if one exists.
	"""

	lines = ''
	active = inspector.active()
	for task in active['celery@queue_sim']:
		lines += 'JOB: %s, worker pid: %d, task id: %s\n\n'%(
			os.path.basename(eval(task['kwargs'])['cwd']),task['worker_pid'],task['id'])
	return JsonResponse({'line':lines,'running':True})
