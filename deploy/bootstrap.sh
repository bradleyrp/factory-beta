#!/bin/bash

<<'notes'

This code will create the environment if it's not ready yet.
We create an isolated vitual environment (via --no-site-packages)
which will compile the necessary packages from scratch. This tends to
eliminate problems with a user's system packages. However, the user
will have to install lapack-devel, hdf5-devel, cblas-devel,
libatlas3-devel, as root for many of these packages to work correctly. 
You can use --system-site-packages instead for a quicker 
install, if you have a clean environment. You also need 
libjpeg8-devel for Pillow.

! Note that we may wish to be more careful about which libraries are necessary
! Give the user the option to use system packages or not? Currently we are failing on cblas or something.

notes

if [[ -d env ]]; then { echo "[STATUS] env already exists"; exit; }; fi
# easy keyword lets you use system packages in the virtualenv
if [[ "$1" = "system" ]]; then { echo "[STATUS] using system site-packages"; VENV_OPTS="--system-site-packages"; }
else
	echo "[STATUS] using an isolated virtual environment"
	VENV_OPTS="--no-site-packages"
	# requirements if not system
	#! finish adding other tests (see comments for library names)
	avail=$(echo '#include <cblas.h>' | cpp -H -o /dev/null 2>&1)
	if ! [[ $? -eq 0 ]]; then { echo "[ERROR] no cblas"; exit 1; }; fi
fi

echo "[STATUS] setting up virtualenv"
bash deploy/check_dependencies.sh || { exit 1; }
virtualenv $VENV_OPTS env &> logs/log-env || { echo "[ERROR] needs python-virtualenv. see logs/log-env"; exit 1; }
source env/bin/activate 
pip install -r deploy/requirements.txt &> logs/log-pip || { echo "[ERROR] in pip install. see logs/log-pip"; exit 1; }
perl -ne 'print "$1\n" if /^Requirement already.+\:\s*([^\s]+)/' logs/log-pip > logs/log-pip-remotes
echo "[STATUS] see logs/log-pip-remotes for external packages"
echo "[TIME] $SECONDS sec elapsed since starting virtualenv"

echo "[STATUS] checking redis"
redis-cli --version &> /dev/null
if ! [[ $? == 0 ]]; then { echo "[ERROR] install redis and run \"sudo /usr/sbin/redis-server deploy/redis.conf\""; exit 1; }; fi
echo "[STATUS] redis is ready"