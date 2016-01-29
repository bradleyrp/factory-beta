from django.shortcuts import render,get_object_or_404
from django.conf import settings
from django.http import HttpResponseNotFound,HttpResponse,HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.http import JsonResponse
from simulator.models import *
from .forms import *
from .tasks import sherpacalc
from PIL import Image
import json,os,glob,re,time,subprocess
import yaml

def deep_hash_to_text(d,**kwargs):

	"""
	Turn nested dictionaries into a block of text.
	"""

	spacer = kwargs.get('spacer',' ')
	lines = kwargs.get('lines',[])
	indent = kwargs.get('indent',0)
	for key,value in d.iteritems():
		lines.append(spacer*indent+str(key))
		if isinstance(value,dict): deep_hash_to_text(value,indent=indent+1,lines=lines,spacer=spacer)
		else: lines.append(spacer*(indent+1)+str(value))
	return '\n'.join(lines)

def collect_images():

	"""
	Collect the names of all images in the plot directory and read their metadata.
	"""

	omni_paths = {}
	execfile(settings.CALCSPOT+'/paths.py',omni_paths)
	image_fns = [os.path.basename(fn) for fn in glob.glob(settings.PLOTSPOT+'/*.png')]
	names_path_meta = [(
		re.sub('_',' ',re.findall('^fig\.([^\.]+)\.',fn)[0]),fn,
		eval(Image.open(settings.PLOTSPOT+'/'+fn).info['meta'])
		) for fn in image_fns]
	return names_path_meta
	
def refresh_thumbnails(request,remake=False):

	"""
	Create or update thumbnails so the views load faster in case of enormous image files.
	"""	

	root = settings.PLOTSPOT+'/'
	if not os.path.isdir(root+'/thumbs'): os.mkdir(root+'/thumbs')
	image_fns = collect_images()
	for name,fn,meta in image_fns:
		thumbfile = os.path.dirname(root+fn)+'/thumbs/'+os.path.basename(root+fn)
		if not os.path.isfile(thumbfile) or remake:
			os.system('convert %s -thumbnail 500x500 %s'%(root+fn,thumbfile))
	#---wait for thumbs to refresh on disk if we remade them
	if remake: time.sleep(5)
	#---! need to refresh the page manually after refreshing the thumbnails for some reason
	return HttpResponseRedirect('?ignore=%d'%time.time())
	
def index(request,collection_id=-1,group_id=-1,calculation_id=-1,
	update_group=False,update_collection=False,update_calculation=False):

	"""
	Show a set of calculations.
	"""

	if request.method == 'GET': 
		if group_id == -1: form_group = group_form(prefix='group_form')
		else: 
			group = Group.objects.get(pk=group_id)
			form_group = group_form(instance=group,prefix='group_form')	
			form_group.fields['name'].widget.attrs['readonly'] = True
		if collection_id == -1: form_collection = collection_form()
		else: 
			collection = Collection.objects.get(pk=collection_id)
			form_collection = collection_form(instance=collection,prefix='collection_form')	
		if calculation_id == -1: form_calculation = calculation_form(prefix='calculation_form')
		else: 
			calculation = Calculation.objects.get(pk=calculation_id)
			form_calculation = calculation_form(instance=calculation,prefix='calculation_form')	
			form_calculation.fields['name'].widget.attrs['readonly'] = True
		form_slice = slice_form(prefix='slice_form')
	else:
		#---create a new collection
		if request.path == '/calculator/new_collection':
			form_slice = slice_form(prefix='slice_form')
			form_collection = collection_form(request.POST,request.FILES,prefix='collection_form')
			form_group = group_form(prefix='group_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_collection.is_valid():
				new_collection = form_collection.save(commit=False)
				new_collection.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---create a new group
		elif request.path == '/calculator/new_group':
			form_slice = slice_form(prefix='slice_form')
			form_group = group_form(request.POST,request.FILES,prefix='group_form')
			form_collection = collection_form(prefix='collection_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_group.is_valid():
				new_group = form_group.save(commit=False)
				new_group.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---create a new slice
		elif request.path == '/calculator/new_slice':
			form_slice = slice_form(request.POST,request.FILES,prefix='slice_form')
			form_group = group_form(prefix='group_form')
			form_collection = collection_form(prefix='collection_form')
			form_calculation = calculation_form(prefix='calculation_form')
			if form_slice.is_valid():
				slice_name = form_slice.cleaned_data['name']
				#---get the desired collections and make a new slice for each simulation in each collection
				if 'collections' in form_slice.cleaned_data:
					for collection_pk in form_slice.cleaned_data['collections']:
						for sim in Collection.objects.get(pk=collection_pk).simulations.all():
							#---make a new row in the slices table
							print "making slice %s"%sim
							print form_slice.cleaned_data['groups']
							new_slice,created = Slice.objects.update_or_create(
								name=slice_name,
								simulation=sim,
								start=form_slice.cleaned_data['start'],
								end=form_slice.cleaned_data['end'],
								skip=form_slice.cleaned_data['skip'])
							for g in form_slice.cleaned_data['groups']: new_slice.groups.add(g)
							new_slice.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---create a new calculation
		elif request.path == '/calculator/new_calculation':
			form_slice = slice_form(prefix='slice_form')
			form_group = group_form(prefix='group_form')
			form_collection = collection_form(prefix='collection_form')
			form_calculation = calculation_form(request.POST,request.FILES,prefix='calculation_form')
			if form_calculation.is_valid():
				new_calculation = form_calculation.save(commit=False)
				new_calculation.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---update a group
		elif update_group:
			group = Group.objects.get(pk=group_id)
			form_group = group_form(data=request.POST,instance=group,prefix='group_form')
			if form_group.is_valid():
				#---! note that we tried commit=False and later new_group.save() and it didn't update 
				new_group = form_group.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---update a collection
		elif update_collection:
			collection = Collection.objects.get(pk=collection_id)
			form_collection = collection_form(data=request.POST,instance=collection,prefix='collection_form')
			if form_collection.is_valid():
				new_collection = form_collection.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		#---update a calculation
		elif update_calculation:
			calculation = Calculation.objects.get(pk=calculation_id)
			form_calculation = calculation_form(data=request.POST,instance=calculation,prefix='calculation_form')
			if form_calculation.is_valid():
				new_calculation = form_calculation.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		else: 
			raise Exception('unclear incoming path to the index.html page')
	refresh_thumbnails(request)
	image_fns = collect_images()
	outgoing = {
		'image_fns':image_fns,
		'simulations':Simulation.objects.all().order_by('id'),
		'collections':Collection.objects.all().order_by('id'),
		'collection_form':form_collection,
		'groups':Group.objects.all().order_by('id'),
		'calculations':Calculation.objects.all().order_by('id'),
		'group_form':form_group,
		'selected_group':-1 if group_id==-1 else Group.objects.get(pk=group_id),
		'selected_collection':-1 if collection_id==-1 else Collection.objects.get(pk=collection_id),
		'selected_calculation':-1 if calculation_id==-1 else Calculation.objects.get(pk=calculation_id),
		'slice_form':form_slice,
		'running_calculations':BackgroundCalc.objects.all().order_by('id'),
		'calculation_form':form_calculation,
		'slice_form_doc':form_slice.__doc__,
		}
	print image_fns
	rendered = render_to_string('calculator/index.html',outgoing)
	return render(request,'calculator/index.html',outgoing)

def index_preserved(request,col_id,grp_id):

	"""
	Show a set of calculations.
	"""

	print "INCOMING DATA"
	print col_id,grp_id

	if request.method == 'GET': 
		form_collection = collection_form()
		form_group = group_form()
	else:
		form_collection = collection_form(request.POST,request.FILES)
		form_group = group_form(request.POST,request.FILES)
		if request.path == '/calculator/update_collection':
			#---write meta file with a new collection
			if form_collection.is_valid():
				#with open(settings.CALCSPOT+'/calcs/specs/meta.collections.yaml','w') as fp:
				#	for id in list(form.cleaned_data['simulations']):
				#		print Simulation.objects.get(pk=id).name
				#		fp.write(Simulation.objects.get(pk=id).name+'\n')
				new_collection = form_collection.save(commit=False)
				new_collection.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		elif request.path == '/calculator/new_group':
			if form_group.is_valid():
				new_group = form_group.save(commit=False)
				new_group.save()
				return HttpResponseRedirect(reverse('calculator:index'))
		else: raise Exception('unclear incoming path to the index.html page')
	fn_yaml = settings.ROOTSPOT+'/calc/'+settings.PROJECT_NAME+'/calcs/specs/meta.yaml'
	refresh_thumbnails(request)
	with open(fn_yaml) as fp: raw = fp.read()
	specs = yaml.load(raw)
	if not specs: calcs = []
	else: calcs = [(key,nestpretty(val,spacer=' ')) for key,val in specs['calculations'].items()]
	outgoing = {
		'calcs':calcs,
		'image_fns':collect_images(),
		'collection_form':form_collection,
		'group_form':form_group,
		'simulations':Simulation.objects.all().order_by('id'),
		'collections':Collection.objects.all().order_by('id'),
		'groups':Group.objects.all().order_by('id'),
		}
	return render(request,'calculator/index.html',outgoing)
		
def refresh_times(request):

	"""
	"""
	
	proc = subprocess.Popen('make refresh',cwd='./calc/dev/',
		shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	for sim in Simulation.objects.all():
		sn = sim.code	
		miniscript = ';'.join([
			"python -c \"execfile('./omni/base/header.py')",
			"print work.get_timeseq_range('%s')\"",
			])
		proc = subprocess.Popen(miniscript%sn,cwd='./calc/dev/',
			shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		catch = proc.communicate()
		whittled = [i for i in ('\n'.join(catch)).split('\n') if 
			not re.match('^\s*$',i) and 
			not re.match('^\[',i)]
		print whittled
		startstop = eval(whittled[0])
		sim.time_sequence = '-'.join(['%.f'%(i/1000.) for i in startstop])
		sim.save()
	return HttpResponseRedirect(reverse('calculator:index'))

def view_settings(request):

	"""
	Show the settings for a particular instance of calculator.
	"""
	
	#---! hardcoded
	#projname = settings.PROJECT_NAME
	projname = 'ptdins'
	mplxr_basedir = '/home/localshare/analysis/mplxr/'

	with open(mplxr_basedir+'/calc/'+projname+'/gromacs.py') as fp: gromacs_settings = fp.read()
	with open(mplxr_basedir+'/calc/'+projname+'/paths.py') as fp: paths = fp.read()
	return render(request,'calculator/view_settings.html',
		{'gromacs_settings':gromacs_settings,'paths':paths,'rootdir':projname})
		
def detail_simulation(request,id):

	"""
	Detailed view of a simulation with tuneable parameters if the job is not yet submitted.
	URGENT NOTE: sim.dropspot IS DEPRECATED and was replaced with settings.DROPSPOT
	"""

	sim = get_object_or_404(Simulation,pk=id)
	outgoing = {'sim':sim}
	if request.method == 'GET': 
		form = group_form()
		outgoing['group_form'] = form
	else:
		#---write meta file with a new collection
		form = group_form(request.POST,request.FILES)
		if form.is_valid():
			new_collection = form.save(commit=False)
			new_collection.save()
			return HttpResponseRedirect(reverse('calculator:index'))
	return render(request,'calculator/detail.html',outgoing)

def detail_group(request,id):

	"""
	DEPRECATED?
	"""

	group = get_object_or_404(Group,pk=id)
	outgoing = {'group':group}
	if request.method == 'GET': 
		form_group = group_form(instance=group)
		outgoing['group_form'] = form_group
	else:
		form_group = group_form(data=request.POST,instance=group)
		outgoing['group_form'] = form_group
		if form_group.is_valid():
			#---! note that we tried commit=False and later new_group.save() and it didn't update 
			new_group = form_group.save()
			outgoing['collections'] = new_group.collection.all().order_by('id')
			return render(request,'calculator/detail_group.html',outgoing)
	outgoing['collections'] = group.collection.all().order_by('id')
	outgoing['show_collection'] = True
	return render(request,'calculator/detail_group.html',outgoing)

def compute(*args,**kwargs):

	"""
	Write the yaml file and run make compute.
	"""

	#---prepare an a dictionary representing meta.yaml
	outgoing = {'slices':{},'collections':{}}

	for sl in Slice.objects.all():
		if sl.simulation.code not in outgoing['slices']: outgoing['slices'][sl.simulation.code] ={}
		if 'slices' not in outgoing['slices'][sl.simulation.code]: 
			outgoing['slices'][sl.simulation.code]['slices'] = {}
		outgoing['slices'][sl.simulation.code]['slices'][sl.name] = {
			'pbc':'mol','groups':[str(g.name) for g in sl.groups.all()],
			'start':int(sl.start),'end':int(sl.end),'skip':int(sl.skip),
			}
		if 'groups' not in outgoing['slices'][sl.simulation.code]: 
			outgoing['slices'][sl.simulation.code]['groups'] = {}			
		for grp in sl.groups.all():
			outgoing['slices'][sl.simulation.code]['groups'][grp.name] = grp.selection
	outgoing['meta'] = {}
	for sim in Simulation.objects.all():
		outgoing['meta'][sim.code] = {'name':sim.name}

	#---write collections
	for collect in Collection.objects.all():
		outgoing['collections'][collect.name] = [sim.code for sim in collect.simulations.all()]

	#---! fix path below
	print settings.CALCSPOT
	with open(settings.CALCSPOT+'./calcs/specs/meta.slices.yaml','w') as fp:
		fp.write(yaml.safe_dump(outgoing))

	#---write calculations to a separate yaml file
	calcspecs = {'autocalcs':{},'autoplots':{}}
	for calc in Calculation.objects.all():
		calcspecs['autocalcs'][calc.name] = {
			'slice_name':calc.slice_name,
			'group':calc.group.name,
			'collections':[str(c.name) for c in calc.collections.all()],
			'uptype':calc.uptype,
			}
		calcspecs['autoplots'][calc.name] = {
			'slices':calc.slice_name,
			'calculation':[calc.name],
			'group':calc.group.name,
			'collections':[str(c.name) for c in calc.collections.all()],
			'uptype':calc.uptype,
			}

	#---! fix path below
	print settings.CALCSPOT
	with open(settings.CALCSPOT+'./calcs/specs/meta.calculations.yaml','w') as fp:
		fp.write(yaml.safe_dump(calcspecs))			

	#---! this is the hackiest line of code 
	#try: os.system('rm data/dev/post/*')
	#except: pass

	#---! consider adding make compute dry
	this_job = BackgroundCalc()
	this_job.save()
	sherpacalc.delay(this_job.id,autoreload=True,log='log',cwd='./calc/dev/')

	return HttpResponseRedirect(reverse('calculator:index'))

def calculation_monitor(request):

	"""
	Report on a running calculation if one exists.
	"""

	monitor_div = '<div class="tile-col" style="height:200px;">'+\
		'<h3>running calculation</h3>%s</div>'
	#---only read if jobs are running otherwise ajax will remember the last text
	if any(BackgroundCalc.objects.all()):
		with open('./calc/dev/log') as fp: lines = fp.readlines()
		return JsonResponse({'line':'\n'.join([l.lstrip().rstrip() for l in lines]),'running':True})
	else: return JsonResponse({'line':'','running':False})
