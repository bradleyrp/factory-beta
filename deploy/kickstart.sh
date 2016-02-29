#!/bin/bash

<<'notes'
Kickstart a new DJANGO project and automatically add the simulator to it.
Note that we use strict argument ordering because makefile calls this script.
This is only called by connect.py even though it's accessible from make. 
It might be worth incorporating this into python.
notes

#---arguments
projname=$1
settings_appends=$2
urls_appends=$3
omni_repo=$4
amx_repo=$5

#---check for arguments
if [ -z $projname ]; then { echo "[USAGE] make kickstart <project_name> <settings_additions> <urls_additions>"; exit; }; fi
if [ -z $settings_appends ]; then { echo "[USAGE] make kickstart <project_name> <settings_additions> <urls_additions>"; exit; }; fi
if [ -z $urls_appends ]; then { echo "[USAGE] make kickstart <project_name> <settings_additions> <urls_additions>"; exit; }; fi
if [ -d "$projname" ]; then { echo "[ERROR] '$1' exists"; exit; }; fi
echo "[STATUS] kickstarting project: \"$1\""
source env/bin/activate

#---check if the simulator package exists or make it
if ! [[ -f pack/simulator ]]; then make -s package simulator &> logs/log-pack-simulator; fi
if ! [[ -f pack/calculator ]]; then make -s package calculator &> logs/log-pack-calculator; fi

#---create the project
cd site
django-admin startproject $1 &> ../logs/log-$1-startproject
cd ..

#---append settings from the user to project/settings.py and project/urls.py
cat $2 >> site/$1/$1/settings.py
cat $3 >> site/$1/$1/urls.py

#---previously used sed to specify the database
#sed -i "s/os.path.join(BASE_DIR, 'db.sqlite3')/os.path.join(os.path.abspath(BASE_DIR)+'\/..\/..\/data\/$1','db.sqlite3')/g" site/$1/$1/settings.py

#---create data directories
if ! [[ -e data/$1  ]]; then mkdir data/$1; fi 
if ! [[ -e data/$1/sources  ]]; then mkdir data/$1/sources; fi 

#---clone and configure external codes
git clone $omni_repo calc/$1 &> logs/log-$1-git-omni
#---! docs assumes the dropspot path below
git clone $amx_repo data/$1/sims/docs &> logs/log-$1-git-amx
make -C data/$1/sims/docs docs &> logs/log-$1-docs
make -C calc/$1/ config defaults &> logs/log-$1-omnicalc-config
if ! [[ -e calc/$1/calcs ]]; then mkdir calc/$1/calcs; fi 
if ! [[ -e calc/$1/calcs/scripts ]]; then mkdir calc/$1/calcs/scripts; touch calc/$1/calcs/scripts/__init__.py; fi 
make -C calc/$1/ docs &> logs/log-$1-omnicalc-docs

#---assemble celery codes
cp deploy/celery_source.py site/$1/$1/celery.py
sed -i "s/multiplexer/$1/g" site/$1/$1/celery.py

#---migrations
python site/$1/manage.py migrate djcelery &> logs/log-$1-djcelery
python site/$1/manage.py migrate &> logs/log-$1-migrate

#---create superuser password
echo "[STATUS] making superuser"
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin','','admin');print;quit();" | python ./site/$1/manage.py shell &> /dev/null

#---report
echo "[STATUS] new project \"$1\" is stored at ./data/$1"
echo "[STATUS] replace with a symlink if you wish to store the data elsewhere"
