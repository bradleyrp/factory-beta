#!/bin/bash

if [[ -f env ]]; then { echo "[STATUS] env already exists"; exit; }; fi
echo "[STATUS] setting up virtualenv"
bash deploy/check_dependencies.sh || { exit 1; }
#---use system packages for now however this is a HACK (problems with h5py headers)
virtualenv --system-site-packages env &> logs/log-env || { echo "[ERROR] needs python-virtualenv"; exit 1; }
source env/bin/activate 
pip install -r deploy/requirements.txt &> logs/log-pip
echo "[TIME] $SECONDS sec elapsed since starting virtualenv"
