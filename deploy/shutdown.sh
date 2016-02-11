#!/bin/bash

<<notes
Turn off the servers.
Note that this also wipes dead screens.
notes

#---get the PID of the suspended screen
#---previously used: screen -r multiplexer and the user had to send ctrl+c
echo "[SERVE] shutting down runserver, worker, and flower"
PID=$(screen -ls | awk '/\.multiplexer\t/ {print strtonum($1)}')
if ! [ -z $PID ]; then kill -KILL $PID; fi
PID=$(screen -ls | awk '/\.flower\t/ {print strtonum($1)}')
if ! [ -z $PID ]; then kill -KILL $PID; fi
PID=$(screen -ls | awk '/\.worker_sim\t/ {print strtonum($1)}')
if ! [ -z $PID ]; then kill -KILL $PID; fi
PID=$(screen -ls | awk '/\.worker_calc\t/ {print strtonum($1)}')
if ! [ -z $PID ]; then kill -KILL $PID; fi
rm /tmp/screenrc
screen -wipe &> /dev/null
echo "[SERVE] see log/log-serve for messages"
echo "[STATUS] bye"
