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
	url(r'^source(?P<id>[0-9]+)',views.detail_source,name='detail_source'),
	url(r'^logger$',views.calculation_monitor,name='calculation_monitor'),
	url(r'^queue$',views.queue_monitor,name='queue_monitor'),
	]

urlpatterns += static('/static/simulator/',document_root='static/simulator/')
urlpatterns += static('/amxdocs/',
	document_root=settings.DROPSPOT+'/docs/amx/docs/build/_build/html/')
