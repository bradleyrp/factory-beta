#!/bin/bash

<<'notes'
Start the interface and worker servers in background screens.
It is essential that you DENY OSX the ability to listen to incoming connections.
Otherwise you will evetually get broken pipes.
notes

#---get settings
projname=$1
sitespot="site/"
if [[ ! -d "$sitespot/$projname" ]]; then { echo "[ERROR] no project \"$sitespot/$projname\"" && exit 1; }; fi
backrun=$(python -c \
"__file__='$sitespot/$projname/$projname/settings.py';\
execfile(__file__);print BACKRUN")
DEVPORT=$(source env/bin/activate && python -c \
"__file__='$sitespot/$projname/$projname/settings.py';
execfile(__file__);print DEVPORT if 'DEVPORT' in globals() else ''" \
&& deactivate)
if [[ -z $DEVPORT ]]; then 
DEVPORT=8000
CELERYPORT=8001
else
CELERYPORT=$(($DEVPORT+1))
fi

#---blank backrun defaults to the celery method
if [[ "$backrun" == "celery" ]]; then 

wait_grep() {
  local file="$1"; shift
  local match="$1"; shift
  local wait_seconds="${1:-20}"; shift
  until [[ $((wait_seconds--)) -eq 0 ]] || ( [[ -f $file ]] && grep -q $match $file ); do sleep 1; done
  ((++wait_seconds))
}

if [[ -z $TMPDIR ]]; then TMPDIR=/tmp; fi
cat << EOF >$TMPDIR/screenrc
logfile logs/log-serve
EOF

echo "[SERVE] serving the factory to $DEVPORT"
echo "[SERVE] serving celery at $CELERYPORT"

#---previously used the projects.txt file to get the last project
if [ -z $projname ]; then { echo "[USAGE] make run <project_name>"; exit; }; fi
if [ "$projname" == "dev" ]; then { sitespot="./"; } fi

source env/bin/activate
if [[ -f logs/log-serve ]]; then rm logs/log-serve; fi
#---open screens for the server, for the worker, and for flower
echo "[SERVE] waiting for the servers" 
sleep 3
screen -c $TMPDIR/screenrc -d -L -S $projname.multiplexer \
-m python $sitespot/$projname/manage.py runserver 0.0.0.0:$DEVPORT
sleep 3
screen -c $TMPDIR/screenrc -d -L -S $projname.worker_sim \
-m python $sitespot/$projname/manage.py celery -A $projname worker \
-n queue_sim -Q queue_sim --loglevel=INFO
sleep 3
screen -c $TMPDIR/screenrc -d -L -S $projname.worker_calc \
-m python $sitespot/$projname/manage.py celery -A $projname worker \
-n queue_calc -Q queue_calc --loglevel=INFO 
sleep 3
screen -c $TMPDIR/screenrc -d -L -S $projname.flower \
-m python $sitespot/$projname/manage.py celery -A $projname --port=$CELERYPORT flower
wait_grep logs/log-serve http || { echo "[ERROR] no http in logs/log-serve"; exit 1; }
address=$(sed -En 's/^Starting development server at (http.+)\//\1/p' logs/log-serve)
echo "[SERVE] interface website @ "$(echo $address | tr -d '\r')"/simulator"
wait_grep logs/log-serve $CELERYPORT || { echo "[ERROR] no $CELERYPORT in logs/log-serve"; exit 1; }
flower=$(sed -En 's/^.+Visit me at (http.+)/\1/p' logs/log-serve)
echo "[SERVE] flower monitor @ "$(echo $flower | tr -d '\r')

#---old-school method
elif [[ "$backrun" == "old" ]]; then 

#---use the backrun utility to start this job in the background
./deploy/backrun.py \
name="devserver-$projname" \
log="logs/log-serve" \
pre="source env/bin/activate" \
cmd="python $sitespot/$projname/manage.py runserver 0.0.0.0:$DEVPORT" \
stopper="logs/script-stop-devserver.sh"

#---use celery but start the devserver and workers with backrun (DEFAULT)
elif [[ "$backrun" == "celery_backrun" ]]; then 

#---use the backrun utility to start this job in the background
./deploy/backrun.py \
name="devserver-$projname" \
log="logs/log-serve" \
pre="source env/bin/activate" \
cmd="python $sitespot/$projname/manage.py runserver 0.0.0.0:$DEVPORT" \
stopper="logs/script-stop-devserver.sh"

./deploy/backrun.py \
name="devserver-$projname-worker-calc" \
log="logs/log-worker-calc" \
pre="source env/bin/activate" \
cmd="python $sitespot/$projname/manage.py celery -A $projname worker -n queue_calc -Q queue_calc --loglevel=INFO" \
stopper="logs/script-stop-worker-calc.sh"

./deploy/backrun.py \
name="devserver-$projname-worker-sim" \
log="logs/log-worker-sim" \
pre="source env/bin/activate" \
cmd="python $sitespot/$projname/manage.py celery -A $projname worker -n queue_sim -Q queue_sim --loglevel=INFO" \
stopper="logs/script-stop-worker-sim.sh"

./deploy/backrun.py \
name="devserver-$projname-flower" \
log="logs/log-flower" \
pre="source env/bin/activate" \
cmd="python $sitespot/$projname/manage.py celery -A $projname --port=$CELERYPORT flower" \
stopper="logs/script-stop-flower.sh"

else { echo "[ERROR] unclear backrun" && exit 1; }; fi


