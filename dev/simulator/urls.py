from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings
from .models import Simulation
from . import views
import os

urlpatterns = [
	url(r'^$',views.index,name='index'),
	url(r'^builder$',views.index,name='build_simulation'),
	url(r'^upload_sources$',views.upload_sources,name='upload_sources'),
	url(r'^sim(?P<id>[0-9]+)',views.detail_simulation,name='detail_simulation'),
	url(r'^background_job_kill(?P<id>[0-9]+)',views.background_job_kill,name='background_job_kill'),
	url(r'^source(?P<id>[0-9]+)',views.detail_source,name='detail_source'),
	url(r'^logger',views.calculation_monitor,name='calculation_monitor'),
	]

urlpatterns += static('/static/simulator/',document_root='static/simulator/')
urlpatterns += static(r'/amxdocs/',
	document_root=settings.ROOTSPOT+'/dev/data/%s/amx/docs/build/_build/html/'%
	str(Simulation.objects.all().order_by("-id")[0].code) if len(Simulation.objects.all())>0 
	and os.path.isdir(settings.ROOTSPOT+'/dev/data/sims/'+Simulation.objects.all().order_by('-id')[0].code)
	else settings.ROOTSPOT+'/data/dev/sims/docs/amx/docs/build/_build/html/')
