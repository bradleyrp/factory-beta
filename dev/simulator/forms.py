from django import forms
from .models import *
from django.contrib import messages
from django.conf import settings
from django.forms import formset_factory
from multiple_uploads import *
import re,subprocess
from django.db.models.fields import BLANK_CHOICE_DASH

#---some functions require absolute paths
def path_expander(x): return os.path.abspath(os.path.expanduser(x))

class build_simulation_form(forms.ModelForm):

	class Meta:  

		model = Simulation
		fields = ['name','program']
		widgets = {
			'program':forms.Select(attrs={
				'title':'copy sources directly into step\nfolder (not step/source_name)',
				'size':len(get_program_choices())+len(default_programs),
				})}

	def __init__(self,*args,**kwargs):

		"""
		Tell the user which fields are required.
		"""

		kwargs.setdefault('label_suffix', '')
		super(build_simulation_form, self).__init__(*args, **kwargs)
		for field in self.fields.values():
			field.error_messages = {'required':
				'field "{fieldname}" is required'.format(fieldname=field.label)}
		for field in self.fields: self.fields[field].label = field.lower()

class form_simulation_tune(forms.Form):

	def __init__(self,*args,**kwargs):

		if 'initial' in kwargs: settings_info = kwargs['initial']['settings']
		else: settings_info = None
		kwargs.setdefault('label_suffix','')
		super(forms.Form,self).__init__(*args,**kwargs)
		if settings_info:
			print "IAM FORM HERE IS SETTinGGSS"
			print settings_info
			for group_num,(named_settings,specs) in enumerate(settings_info):
				for key,val in specs:
					self.fields[named_settings+'|'+key] = forms.CharField(max_length=255,initial=val)
					self.fields[named_settings+'|'+key].label = key.lower()
					self.fields[named_settings+'|'+key].group = group_num
		source_choices = [[obj.id,obj.name] for obj in Source.objects.all()]
		self.fields['incoming_sources'] = forms.MultipleChoiceField(required=False,choices=source_choices)
		self.fields['incoming_sources'].label = 'sources'

class build_sources_form(forms.ModelForm):

	class Meta:  

		model = Source
		fields = ['name','fileset','elevate']
		widgets = {
			'elevate':forms.CheckboxInput(attrs={'title':
			'copy sources directly into step\nfolder (not step/source_name)'}),}
		
	fileset = MultiFileField(min_num=1,maximum_file_size=1024*1024*5)

	def __init__(self,*args,**kwargs):	
		
		kwargs.setdefault('label_suffix','')
		super(build_sources_form, self).__init__(*args, **kwargs)
		for field in self.fields: self.fields[field].label = field.lower()	

class build_bundles_form(forms.ModelForm):

	class Meta:  

		model = Bundle
		fields = ['name','path']
		
	def __init__(self,*args,**kwargs):	
		
		kwargs.setdefault('label_suffix', '')
		super(build_bundles_form, self).__init__(*args, **kwargs)
		for field in self.fields: self.fields[field].label = field.lower()
