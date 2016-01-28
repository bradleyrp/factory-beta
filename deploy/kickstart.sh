#!/bin/bash

<<'notes'
Kickstart a new DJANGO project and automatically add the simulator to it.

Current operations:

rm -rf data/project calc/project; make reset; make kickstart project /home/localshare/post-ptdins/data /home/localshare/post-ptdins/plot;rm -rf calc/project/calcs; git clone /home/localshare/analysis/omnicalc-ptdins calc/project/calcs

UPCOMING
	standard method for acquiring a previous omnicalc
		supply data/plot directory
		supply a location of the calcs repo
		maybe copy the workspace
	look
		make the TOC into a tile and make pretty much everything into tiles
		render reduced-resolution pictures of the calculations
		

notes

projname=$1
if [ -z $projname ]; then { echo "[USAGE] make kickstart <project_name>"; exit; }; fi
if [ -d "$projname" ]; then { echo "[ERROR] '$1' exists"; exit; }; fi
echo "[STATUS] kickstarting project: \"$1\""
source env/bin/activate
#---check if the simulator package exists or make it
if ! [[ -f pack/simulator ]]; then make package simulator &> logs/log-pack-simulator; fi
cd site
django-admin startproject $1 &> ../logs/log-$1-startproject
cd ..
python -c "import sys;__file__='tmp.py';execfile('site/$1/$1/settings.py');sys.exit(1) if 'simulator' in INSTALLED_APPS else sys.exit(0)"
if (($?==1)); then { echo "[ERROR] simulator already in INSTALLED_APPS"; exit; }; fi
echo -e "\n#---automatically added\nINSTALLED_APPS = tuple(list(INSTALLED_APPS)+['simulator','omnicalc','djcelery'])\n" >> site/$1/$1/settings.py
queues="RQ_QUEUES = {\n\t'default':{\n\t\t'HOST':'localhost',\n\t\t'PORT':6379,\n\t\t'DB':0,\n\t\t'PASSWORD':'bison',\n\t\t'DEFAULT_TIMEOUT':360,\n\t\t},\n\t}"
celery="import djcelery\ndjcelery.setup_loader()\nBROKER_URL = 'redis://localhost:6379/0'\nCELERY_RESULT_BACKEND = 'redis://localhost:6379/0'\nCELERY_ACCEPT_CONTENT = ['json']\nCELERY_TASK_SERIALIZER = 'json'\nCELERY_RESULT_SERIALIZER = 'json'\nDROPSPOT_ABSOLUTE = '/home/ryb/mplxr/'\nCELERYD_CONCURRENCY = 1\n"
#---alternate database location
sed -i "s/os.path.join(BASE_DIR, 'db.sqlite3')/os.path.join(os.path.abspath(BASE_DIR)+'\/..\/..\/data\/$1','db.sqlite3')/g" site/$1/$1/settings.py
echo -e $queues >> site/$1/$1/settings.py
echo -e $celery >> site/$1/$1/settings.py
echo -e "\n#---automatically added\nurlpatterns += [url(r'^simulator/',include('simulator.urls',namespace='simulator')),]" >> site/$1/$1/urls.py
mkdir data/$1 || echo "[NOTE] data directory already exists: data/$1"
mkdir data/$1/sources
git clone https://github.com/bradleyrp/omnicalc calc/$1 &> logs/log-$1-git-omni
git clone https://github.com/bradleyrp/automacs data/$1/docs &> logs/log-$1-git-amx
make -C calc/$1/ config defaults &> logs/log-$1-omnicalc-config
echo -e "DROPSPOT = 'data/$1/'\n" >> site/$1/$1/settings.py
echo -e "AUTOMACS_UPSTREAM = 'http://www.github.com/bradleyrp/automacs'\n" >> site/$1/$1/settings.py
cp deploy/celery.py site/$1/$1/celery.py
sed -i "s/multiplexer/$1/g" site/$1/$1/celery.py
python site/$1/manage.py migrate djcelery &> logs/log-$1-djcelery
python site/$1/manage.py migrate &> logs/log-$1-migrate
#---create superuser password
echo "[STATUS] making superuser"
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin','','admin');print;quit();" | python ./site/$1/manage.py shell &> /dev/null
echo "[STATUS] new project \"$1\" is stored at ./data/$1"
echo "[STATUS] replace with a symlink if you wish to store the data elsewhere"
