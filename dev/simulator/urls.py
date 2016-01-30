from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings
from .models import Simulation
from . import views

urlpatterns = [
	url(r'^$',views.index,name='index'),
	url(r'^builder$',views.index,name='build_simulation'),
	url(r'^upload_sources$',views.upload_sources,name='upload_sources'),
	url(r'^sim(?P<id>[0-9]+)',views.detail_simulation,name='detail_simulation'),
	url(r'^background_job_kill(?P<id>[0-9]+)',views.background_job_kill,name='background_job_kill'),
	url(r'^source(?P<id>[0-9]+)',views.detail_source,name='detail_source'),
	]

urlpatterns += static('/static/simulator/',document_root='static/simulator/')
urlpatterns += static(r'/amxdocs/',
<<<<<<< HEAD
	document_root=settings.ROOTSPOT+'/dev/data/%s/amx/docs/build/_build/html/'%
=======
	document_root=settings.DROPSPOT+'/data/%s/amx/docs/build/_build/html/'%
>>>>>>> e316a24d6ae5c008a99a1ea6ad551cff4656429b
	str(Simulation.objects.all().order_by("-id")[0].code) if len(Simulation.objects.all())>0 else 
	settings.ROOTSPOT+'/dev/data/docs/amx/docs/build/_build/html/')
