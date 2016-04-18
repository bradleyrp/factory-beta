#!/bin/bash

<<'notes'
Start the interface and worker servers in background screens.
It is absolutely crucial that you DENY OSX the ability to listen to incoming connections.
notes

wait_grep() {
  local file="$1"; shift
  local match="$1"; shift
  local wait_seconds="${1:-20}"; shift
  until [[ $((wait_seconds--)) -eq 0 ]] || ( [[ -f $file ]] && grep -q $match $file ); do sleep 1; done
  ((++wait_seconds))
}

cat << EOF >$TMPDIR/screenrc
logfile logs/log-serve
EOF

projname=$1
sitespot="site/"
#---previously used the projects.txt file to get the last project
if [ -z $projname ]; then { echo "[USAGE] make run <project_name>"; exit; }; fi
if [ "$projname" == "dev" ]; then { sitespot="./"; } fi

source env/bin/activate
if [[ -f logs/log-serve ]]; then rm logs/log-serve; fi
#---open screens for the server, for the worker, and for flower
echo "[SERVE] waiting for the servers" 
sleep 3
screen -c $TMPDIR/screenrc -d -L -S multiplexer -m python $sitespot/$projname/manage.py runserver
sleep 3
screen -c $TMPDIR/screenrc -d -L -S worker_sim -m python $sitespot/$projname/manage.py celery -A $projname worker -n queue_sim -Q queue_sim --loglevel=INFO
sleep 3
screen -c $TMPDIR/screenrc -d -L -S worker_calc -m python $sitespot/$projname/manage.py celery -A $projname worker -n queue_calc -Q queue_calc --loglevel=INFO
sleep 3
screen -c $TMPDIR/screenrc -d -L -S flower -m python $sitespot/$projname/manage.py celery -A $projname flower
wait_grep logs/log-serve http || { echo "[ERROR] no http in logs/log-serve"; exit 1; }
address=$(sed -En 's/^Starting development server at (http.+)\//\1/p' logs/log-serve)
echo "[SERVE] interface website @ "$(echo $address | tr -d '\r')"/simulator"
wait_grep logs/log-serve 5555 || { echo "[ERROR] no 5555 in logs/log-serve"; exit 1; }
flower=$(sed -En 's/^.+Visit me at (http.+)/\1/p' logs/log-serve)
echo "[SERVE] flower monitor @ "$(echo $flower | tr -d '\r')
