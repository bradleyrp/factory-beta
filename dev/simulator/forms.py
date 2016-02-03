from django import forms
from .models import *
from django.contrib import messages
from django.conf import settings
from django.forms import formset_factory
from multiple_uploads import *
import re

class build_simulation_form(forms.ModelForm):

	class Meta:  

		model = Simulation
		fields = ['name','program']

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
		else: settings_info = ''
		kwargs.setdefault('label_suffix','')
		super(forms.Form,self).__init__(*args,**kwargs)
		regex = '^(\s*[^:]+)\s*:\s+(.+)'
		for line in settings_info.split('\n'):
			if re.match(regex,line):
				key,val = re.findall(regex,line)[0]
				self.fields[key] = forms.CharField(max_length=255,initial=val)
				self.fields[key].label = key.lower()
		source_choices = [[obj.id,obj.name] for obj in Source.objects.all()]
		#---previously used widget=forms.CheckboxSelectMultiple
		self.fields['incoming_sources'] = forms.MultipleChoiceField(required=False,
			choices=source_choices)
		self.fields['incoming_sources'].label = 'extras'
		if len(self.fields['incoming_sources'].choices)==0:
			self.fields['incoming_sources'].label = ''

class build_sources_form(forms.ModelForm):

	class Meta:  

		model = Source
		fields = ['name']
		
	fileset = MultiFileField(min_num=1,maximum_file_size=1024*1024*5)

	def __init__(self,*args,**kwargs):	
		
		kwargs.setdefault('label_suffix', '')
		super(build_sources_form, self).__init__(*args, **kwargs)
		for field in self.fields: self.fields[field].label = field.lower()	
