#!/bin/bash

<<notes
Turn off the servers.
Note that this also wipes dead screens.
notes

if [[ -z $1 ]]; then incoming="\.\w+"; else incoming="\.$1"; fi
#---get the PID of the suspended screen
#---previously used: screen -r multiplexer and the user had to send ctrl+c
echo "[SERVE] shutting down runserver, worker, and flower"
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.multiplexer/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.flower/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.worker_sim/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.worker_calc/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
screen -wipe &> /dev/null
echo "[SERVE] see log/log-serve for messages"
echo "[STATUS] bye"
