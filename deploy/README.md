    ___                                    
   / __)              _                    
 _| |__ _____  ____ _| |_ ___   ____ _   _ 
(_   __|____ |/ ___|_   _) _ \ / ___) | | |
  | |  / ___ ( (___  | || |_| | |   | |_| |
  |_|  \_____|\____)  \__)___/|_|    \__  |
                                    (____/ 
             "one-to-many"

[NOTE] use 'make help' for details

# QUICKSTART GUIDE

Copy <connect.yaml> to <connect.local.yaml>.
Use examples in <connect.yaml> to set up paths for your data.
Install system-level dependencies listed below.
If you already have mathematics libraries (e.g. scipy) installed
then make sure you use the "system" flag when you make the 
environment. Start from scratch with:

"make nuke && make env system && make connect connect.local.yaml"

Then open a project using: "make run <project>". If you change 
paths in connect.local.yaml you can "refresh" the setup by running:
"make connect connect.local.yaml" again. This preserves your omnicalc
codes found in "./calcs" but allows you to change any path.

# REQUIRES

Factory will create a local python virtual environment which will
compile and install most dependencies. However, the simulator requires
a local GROMACS installation, and the factory uses background "workers"
using Celery, which depends on starting a redis queue in the background
for coordinating the simulation queue. 

1. Development headers for scientific libraries (e.g. scipy).
   these are typically installed 
2. Set up 

OSX redis

brew install redis
ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents

# REMOTE ACCESS

You can view the HTML front-end over an ssh connection.
First, add an alias for your machine to ~/.ssh/config.
If you have ssh keys you won't need to enter your password.
Then, copy ./deploy/tunnelport to your $PATH with execute
permissions. You can then run: "tunnelport <alias>" to
open two tunnels: one for the site and the other for the
celery workers.


[INCOMING DOCUMENTATION BELOW!]

1. development headers
2. redis 
3. COMMAND TO REDIS
4. GROMACS
5. virtualenv

## set up a redis queue
## set up apache
## tunnelport
running icon when calculating
queue for simulator
final start-to-finish test on a protein for tutorial
TRR for icam project
ptdins calculations
ENTH calculations
