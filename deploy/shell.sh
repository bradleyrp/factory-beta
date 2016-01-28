#!/bin/bash

#!!!! NEEDS FIXED FOR DEV AND SITE!

projname=$1
pathprefix=""
if [ -z $projname ]; then { echo "[USAGE] make shell <project_name>"; exit; }; fi
#---dev resides at the root directory not site so we have to go up
if [ "$projname" == "dev" ]; then pathprefix="../"; fi

source env/bin/activate
python site/$pathprefix$projname/manage.py shell
