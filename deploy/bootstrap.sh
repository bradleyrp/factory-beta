#!/bin/bash

if [[ -f env ]]; then { echo "[STATUS] env already exists"; exit; }; fi
echo "[STATUS] setting up virtualenv"
#---use system packages for now however this is a HACK (problems with h5py headers)
virtualenv --system-site-packages env &> logs/log-env
#virtualenv env &> logs/log-env
source env/bin/activate 
pip install -r deploy/requirements.txt &> logs/log-pip
echo "[TIME] $SECONDS sec elapsed since starting virtualenv"
