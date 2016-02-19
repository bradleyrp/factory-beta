#!/bin/bash

<<notes
Reset everything.
Duplicates reset with no confirmation.
Previously used the following sequence:
	make shutdown
	rm -rf env calc/ptdins data/ptdins site/ptdins pack/simulator pack/calculator
	ake connect connect.yaml
	make run ptdins

previous codes
	reset the development server
		source env/bin/activate
		rm dev/data/db.sqlite3
		rm -rf dev/data
		rm -rf dev/calc
		mkdir dev/data
		mkdir dev/data/sources
		python dev/manage.py migrate
		git clone https://github.com/bradleyrp/automacs dev/data/docs
		git clone https://github.com/bradleyrp/omnicalc dev/calc
		mkdir dev/calc/calcs/specs
		touch dev/calc/calcs/specs/meta.yaml
		make -C dev/calc config defaults
		make -C dev/data/docs docs
		echo "from django.contrib.auth.models import User;
			User.objects.create_superuser('admin','','admin');print;quit()" \
			| python ./dev/manage.py shell
		deactivate
	Script to nuke and re-clone omnicalc during calculation development.
		rm -rf dev/calc
		git clone /home/ryb/worker/analysis/omnicalc-joe dev/calc
		mkdir dev/calc/calcs/specs
		touch dev/calc/calcs/specs/meta.yaml
		make -C dev/calc config defaults
notes

#---no enter if you use the -n 1 flag below
read -p "[QUESTION] \"nuke\" starts entirely from scratch. continue (y/N)? " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then echo "[STATUS] reconnecting"
else exit 1; fi

echo "[STATUS] automatically resetting"
echo "[STATUS] deleting pack/*"
rm -rf ./pack/*
echo "[STATUS] deleting env"
rm -rf ./env
if [[ -f logs/projects.txt ]]; then
  while read p; do
    echo "[STATUS] deleting ./site/$p"
    rm -rf ./site/$p
  done < logs/projects.txt
  rm logs/projects.txt
fi
echo "[STATUS] deleting logs/log-serve"
rm -rf logs/log-server
echo "[STATUS] deleting logs/log-*"
rm -rf logs/log-*
echo "[STATUS] deleting write/*"
rm -rf write/*
echo "[STATUS] deleting ./data/*"
rm -rf ./data/*
touch ./data/.info
echo "[STATUS] deleting ./calc/*"
rm -rf ./calc/*
echo "[STATUS] deleting ./site/*"
rm -rf ./site/*
make -s bootstrap

<<deprecated

# these functions were incorporated into connect.py via the dev entry in the yaml file

#---note that the following sequence mimics kickstarter, customized for development
#---! integrate the development setup into the kickstarter to handing different development paths

make bootstrap
mkdir data/dev
mkdir data/dev/sims
mkdir data/dev/sims/sources
mkdir data/dev/plot
mkdir data/dev/post
source env/bin/activate
git clone https://www.github.com/bradleyrp/omnicalc calc/dev
git clone https://github.com/bradleyrp/automacs data/dev/sims/docs
make -C calc/dev config defaults
make -C data/dev/sims/docs docs
python dev/manage.py makemigrations
python dev/manage.py migrate
echo \
"from django.contrib.auth.models import User;User.objects.create_superuser('admin','','admin');print;quit();"|\
python ./dev/manage.py shell &> /dev/null

deprecated