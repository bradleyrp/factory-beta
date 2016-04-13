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
then make sure you use the "system" flag when you make the environment.
Start from scratch with:

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

[INCOMING DOCUMENTATION BELOW!]

## set up a redis queue
## set up apache
## tunnelport

running icon when calculating
queue for simulator
dropdowns for calculation to show slices
