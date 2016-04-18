#!/bin/bash

<<notes
Turn off the servers.
Note that this also wipes dead screens.
notes

#---get the PID of the suspended screen
#---previously used: screen -r multiplexer and the user had to send ctrl+c
echo "[SERVE] shutting down runserver, worker, and flower"
PID=$(screen -ls | perl -ne 'print $1 if /^\s*([0-9]+)\.multiplexer/')
if ! [ -z $PID ]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'print $1 if /^\s*([0-9]+)\.flower/')
if ! [ -z $PID ]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'print $1 if /^\s*([0-9]+)\.worker_sim/')
if ! [ -z $PID ]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'print $1 if /^\s*([0-9]+)\.worker_calc/')
if ! [ -z $PID ]; then kill -KILL $PID; fi
rm -f /tmp/screenrc
screen -wipe &> /dev/null

#----more permissive killing because some systems chain together PIDs when running runserver
#---! is this dangerous? it appears to require only one project per machine otherwise shutdown kills all
targets=($(ps -ef | egrep "[s]ite/.+/manage.py" | awk '{print $2}'))
for i in "${!targets[@]}"; do kill ${targets[$i]}; done

echo "[SERVE] see log/log-serve for messages"
echo "[STATUS] bye"
