from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.forms import formset_factory
from django.contrib.staticfiles.views import serve
from django.http import JsonResponse
from .forms import *
from .models import *
if settings.BACKRUN == '':
	from .tasks import sherpa
import os,subprocess
import re,glob,shutil,time

#---fieldsets to organize the parts of a form
from django.forms.forms import BoundField
class FieldSet(object):
    def __init__(self,form,fields,legend='',cls=None):
        self.form = form
        self.legend = legend
        self.fields = fields
        self.cls = cls
    def __iter__(self):
        for name in self.fields:
            field = self.form.fields[name]
            yield BoundField(self.form, field, name)

#---maintain a list of possible (upstream) data spot locations for fast lookups
lookup_spotnames = {}

#---some functions require absolute paths
def path_expander(x): return os.path.abspath(os.path.expanduser(x))

def is_bundle(name): 

	"""
	Convert a bundle "name" composed of the name and metarun name into parts.
	"""

	if re.match('^(.+)\s>\s(.+)$',name): return re.findall('^(.+)\s>\s(.+)$',name)[0]
	else: return False

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
	subprocess.check_call('source %s/env/bin/activate && make docs'%settings.ROOTSPOT,
		shell=True,cwd=os.path.join(settings.DROPSPOT,sim.code),executable="/bin/bash")
	bundle_info = is_bundle(sim.program)
	if not bundle_info:
		subprocess.check_call('make program %s'%sim.program,
			shell=True,cwd=os.path.join(settings.DROPSPOT,sim.code),executable="/bin/bash")
	else:
		bundle = Bundle.objects.get(name=bundle_info[0]) 
		get_bundle(bundle.id,sim.code)
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
		form_bundles = build_bundles_form()
	else:
		form = build_simulation_form(request.POST,request.FILES)
		form_sources = build_sources_form()
		form_bundles = build_bundles_form()
		if form.is_valid():
			sim = form.save(commit=False)
			sim.save()
			prepare_simulation(sim)
			return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	allsims = Simulation.objects.all().order_by('id')
	allsources = Source.objects.all().order_by('id')
	bundles = Bundle.objects.all().order_by('id')
	modifier = ['','_basic'][0]
	return render(request,'simulator/index%s.html'%modifier,{
		'form_simulation':form,'allsims':allsims,'bundles':bundles,
		'form_bundles':form_bundles,'form_sources':form_sources,'allsources':allsources,
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

def upload_bundles(request):

	"""
	Upload files to a new external source which can be added to future simulations.
	"""

	form = build_simulation_form()
	form_sources = build_sources_form()
	if request.method == 'GET': form_bundles = build_bundles_form()
	else:
		form_bundles = build_bundles_form(request.POST,request.FILES)
		if form_bundles.is_valid():
			bundle = form_bundles.save(commit=True)
			if not os.path.isdir(path_expander(bundle.path)):
				path = bundle.path
				bundle.delete()
				return HttpResponse('[ERROR] "%s" is not a directory on this system'%path)
			if (not os.path.isdir(os.path.join(path_expander(bundle.path),'.git')) and not
				os.path.isfile(os.path.join(path_expander(bundle.path),'HEAD'))):
				path = bundle.path
				bundle.delete()
				return HttpResponse('[ERROR] "%s" does not contain ".git" or \"HEAD\"'%path)
			return HttpResponseRedirect(reverse('simulator:index'))
	return render(request,'simulator/index.html',{
		'form_simulation':form,'form_sources':form_sources,'form_bundles':form_bundles,
		'allsims':Simulation.objects.all().order_by('id'),
		'allsources':Source.objects.all().order_by('id'),
		'bundles':Bundle.objects.all().order_by('id')})
		
def simulation_script(fn,changes=None):

	"""
	Read (and possibly rewrite) the settings from a simulation script.
	"""

	#---read the raw script
	with open(fn) as fp: script_raw = fp.read()
	#---extract all settings blocks which must multi-line python strings without escaped newlines
	regex_settings_block = '^(settings\w*)\s*=\s*[\"]{3}(.*?)(?:[\"]{3})'
	#---get the first line of a settings blocks
	#first_line = next(ii for ii,i in enumerate(script_raw.split('\n')) if re.match(regex_settings_block,i))
	settings_blocks = [(i,j) for i,j in re.findall(regex_settings_block,script_raw,re.MULTILINE+re.DOTALL)]
	#---infer whether we are running a program or a bundle
	regex_program_fn = '^script-\w+\.py$'
	regex_bundle_fn = '^(meta|proc)\w+\.py$'
	basename = os.path.basename(fn)
	if not (re.match(regex_program_fn,basename) or re.match(regex_bundle_fn,basename)):
		return HttpResponse('[ERROR] the name of your program "%s" violates the naming convention'%fn)
	if 0 and changes:
		text_new = str(script_raw) 
		for key,val in settings_blocks:
			text_new = re.sub(re.escape(val),'',text_new,re.MULTILINE+re.DOTALL)
			text_new = '\n'.join([t for t in text_new.split('\n') if not 
				re.match('^%s.+$'%key,t,re.MULTILINE)])
		text_new = re.sub(re.escape("#!/usr/bin/python\n"),"",text_new)
		print "INSIDE CHANGES"
		print fn
		with open(fn,'w') as fp:
			fp.write('#!/usr/bin/python\n\n')
			for named_settings,vals in changes:
				fp.write('%s = """\n'%named_settings)
				for key,val in vals:
					fp.write('%s : %s\n'%(key,val))
				fp.write('"""\n\n')
			fp.write(text_new)
		#---re-read the answer for current settings
		with open(fn) as fp: script_raw = fp.read()
		settings_blocks = [(i,j) for i,j in 
			re.findall(regex_settings_block,script_raw,re.MULTILINE+re.DOTALL)]
	#---regex to extract data from a settings block
	regex = '^(\s*[^:]+)\s*:\s+(.+)'
	#---organize all settings by name
	outgoing = []
	#---loop over all settings blocks
	for named_settings,text in settings_blocks:
		settings_dict = []
		for line in text.split('\n'):
			if re.match(regex,line):
				key,val = re.findall(regex,line)[0]
				settings_dict.append((key,val))
		outgoing.append((named_settings,settings_dict))
	return outgoing

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

def get_bundle(pk,sim_code):

	"""
	Clone a bundle according to its primary key.
	"""

	bundle = Bundle.objects.get(pk=pk)
	subprocess.check_call('make review source="%s"'%path_expander(bundle.path),
		shell=True,cwd=os.path.join(settings.DROPSPOT,sim_code),executable="/bin/bash")

def detail_settings_text(settings):

	"""
	Takes a list of name,dictionary tuples and prints the text.
	"""

	text_view_settings = []
	for name,specs in settings:
		text_view_settings.append('<strong>%s</strong>'%name)
		for key,val in specs:
			text_view_settings.append('%s : %s'%(str(key),str(val)))
	return '<br>'.join(text_view_settings)

def detail_simulation(request,id):

	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	"""

	sim = get_object_or_404(Simulation,pk=id)
	location = find_simulation(sim.code)
	outgoing = {'sim':sim,'path':location}
	bundle_info = is_bundle(sim.program)
	if bundle_info:
		candidate_fns = glob.glob(location+'/inputs/meta*')+glob.glob(location+'inputs/*/meta*')
		script_fn = [i for i in candidate_fns if re.search(bundle_info[1],os.path.basename(i))]
		if len(script_fn)!=1:
			return HttpResponse('[ERROR] non-unique meta script match "%s"'%str(script_fn))
		simscript = script_fn[0]
	else: simscript = location+'/script-%s.py'%sim.program
	if not is_bundle(sim.program) and not os.path.isfile(simscript): 
		return HttpResponse("[ERROR] could not locate %s, perhaps this simulation is old-school?"%simscript)
	settings = simulation_script(simscript)
	settings_orders = [(i,zip(*j)[0]) for i,j in settings]
	settings_dict = {i:{k:l for k,l in j} for i,j in settings}
	#---serve the simulation settings in a form if the simulation has not been started
	if request.method=='GET':
		if not sim.started: 
			form = form_simulation_tune(initial={'settings':settings})
			outgoing['fieldsets'] = tuple([FieldSet(form,[name+'|'+i for i,j in vals],legend=name) 
				for snum,(name,vals) in enumerate(settings)])
			#outgoing['form'] = form_simulation_tune(initial={'settings':settings})
		outgoing['settings'] = settings
	#---interpret any changes to the settings and rewrite the simulation script before submitting
	else:
		form = form_simulation_tune(request.POST,request.FILES)
		sim = get_object_or_404(Simulation,pk=id)
		#---start simulation
		additional_sources,additional_files = [],[]
		if form.is_valid():
			#---read the data from the form into the settings dictionary
			all_settings_keys = [i for j in zip(*settings_orders)[1] for i in j]
			unpacked_form = [(i.split('|'),j) for i,j in form.data.items() if '|' in i]
			for (named_settings,name),val in [(i,j) for i,j in unpacked_form if i[1] in all_settings_keys]:
				#---for metarun we have to recover the settings block name and the text
				settings_dict[named_settings][name] = val
			#---intercept the sources so we can copy them
			for pk in form.cleaned_data['incoming_sources']:
				obj = Source.objects.get(pk=pk)
				extra_files,extra_sources = prepare_source(obj,sim,settings_dict=settings_dict)
				additional_files.extend(extra_files)
				additional_sources.extend(extra_sources)
		else: return HttpResponse('[ERROR] INVALID FORM')
		if additional_sources != []: 
			settings_dict['sources'] = str(additional_sources)
			settings_order.append('sources')
		if additional_files != []: 
			settings_dict['files'] = str(additional_files)
			settings_order.append('files')
		#---prepare the simulation script
		changes = []
		for key,val in settings_orders: 
			changes.append((key,[(i,settings_dict[key][i]) for i in val]))
		scriptset = simulation_script(simscript,changes=changes)
		#---send the simulation to the worker
		kwargs = {'cwd':location}
		if False:
			#---override if a bundle was selected (note that this ignores the settings writing above)
			bundles = form.cleaned_data['incoming_bundles']
			if bundles: 
				pk,metarun = eval(bundles)
				get_bundle(pk,sim.code)
				kwargs['metarun'] = metarun
		bundle_info = is_bundle(sim.program)
		if bundle_info: kwargs['metarun'] = bundle_info[1]
		sherpa.apply_async(args=(sim.program,),kwargs=kwargs,retry=False)
		sim.started = True
		sim.save()
		#---replace the settings in the original script with the updated copy
		outgoing['settings_text'] = detail_settings_text(scriptset)
		return HttpResponseRedirect(reverse('simulator:detail_simulation',kwargs={'id':sim.id}))
	print "REQUEST = %s"%request.method
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
