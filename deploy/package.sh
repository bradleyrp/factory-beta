#!/bin/bash

projname=$1
if [ -z $projname ]; then { echo "[USAGE] make package <app_name>"; exit; }; fi
if ! [ -d "dev/$projname" ]; then { echo "[ERROR] 'multiplexer/$1' does not exist"; exit; }; fi
if [ -d "pack/$projname" ]; then { echo "[ERROR] 'pack/$1' exists"; exit; }; fi
cp -a deploy/packer ./pack/$1
cp -a dev/$1 ./pack/$1/
repl="packname,packages = \"$1\",[\"$1\"]"
sed -i.bak "s/#---SETTINGS/$repl/g" pack/$projname/setup.py 
sed -i.bak "s/APPNAME/$projname/g" pack/$projname/MANIFEST.in 
python pack/$projname/setup.py sdist
source env/bin/activate
echo "[STATUS] installing package"
echo -e "y\n" | pip uninstall $projname &> logs/log-pip-$projname 
pip install pack/$projname/dist/$projname-0.1.tar.gz 1>&2 logs/log-pip-$projname
echo "[STATUS] $projname installed"