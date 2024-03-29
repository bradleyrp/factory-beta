<img src="https://github.com/bradleyrp/factory/raw/master/dev/simulator/static/simulator/factory.png" width="150"/>

FACTORY
=======

The "factory" codes provide a browser-based interface for [AUTOMACS](https://github.com/bradleyrp/automacs) (simulation) and [OMNICALC](https://github.com/bradleyrp/omnicalc) (analysis) codes in order to scale molecular biophysical modeling projects to hundreds of simulations, easily reproduce calculations on these data, and easily share the underlying code.

## Installation

The factory codes use python's virtual environment to install 
many of its dependencies. In addition to installing python 2.7 
or higher, you must also have the following software available. 
We have listed common package names for `RPM` and `DEB` systems 
below. If you're using `DEB` systems, install these packages via:

`sudo apt-get install <name>`

1. `Git` for version control. Many internal parts of the code
   rely on this program for keeping track of your codes.
2. Python virtual environment. The packages are named 
   `python-virtualenv` and `python-virtualenvwrapper` 
   on `RPM/DEB` systems and `pyenv-virtualenv` and 
   `pyenv-virtualenvwrapper` in homebrew.
3. Python development headers (namely `arrayobject.h`) 
   named `python-dev` on `DEB` and `python-devel` on `RPM`.
4. Development headers for `NUMPY`, and `SCIPY`. Note that 
   setup will be much faster if you already have these 
   packages installed system-wide. Packages are named 
   `python-numpy-devel` on `RPM` systems. Simply installing 
   `numpy` and `scipy` on `DEB` and homebrew should be 
   sufficient. We also recommend installing `matplotlib` via
   the package manager because `pip` often fails at this.
5. The `hdf5` package for writing binary files. On `DEB` we 
   recommend installing `libhdf5`, `libhdf5-dev`, and 
   `python-h5py`. These packages are named `hdf5`, and 
   `hdf5-devel`, and `python-h5py` on RPM. On homebrew 
   you only need `hdf5`.
6. The `redis` message-passing interface named `redis` on 
   `homebrew/RPM` and `redis-server` on `DEB`.
7. `GROMACS` should be installed and available in your path. 
   It is also possible to use environment modules to control 
   your `GROMACS` versions, and our codes let you specify the 
   versions explicitly later on.
8. Other tools like `MODELLER` and `VMD` can be useful if they are
   available in your path for some functionality. Other 
   packages like `scikit-learn` are required for more advanced 
   simulation procedures.

Some of these steps are easier to complete with superuser 
access, and the factory codes work best when you can run a 
local web-server to view the interface. Users who lack sudo 
rights should contact the authors to help with the installation.

### Installing `redis`

Once the software is installed, we must setup `redis`. Factory 
provides a cluster-like functionality that runs simulations in 
the background using `celery`. This requires a message-passing 
interface provided by `redis`. 

We recommend following your system-specific instructions to
start the redis daemon using the standard configuration. 

1. Run `redis-server` once to make sure `redis` is installed 
   properly. It will show a neat picture and run in the foreground.
2. Hit `ctrl+c` to exit, and then locate the default 
   configuration. Sometimes the splash screen tells you where this
   can be found. It can probably be found at:
   `/etc/redis/default.conf`.
3. Make a local copy of the default configuration. For example:
   `cp /etc/redis/default.conf ./deploy/redis.conf` will store
   a local copy of the configuration in the factory `deploy` folder.
4. Edit the conf file so it runs in daemon mode: `daemonize yes`.
5. Run `redis-server deploy/redis.conf`.

Redis will run in the background indefinitely. You may need to 
restart it, if you reboot your computer. You can shut it down
if desired by running `redis-cli` and issuing `shutdown`.

## Quickstart guide

Once you have the software requirements installed and `redis` 
running as a daemon, we can set up the virtual environment and 
start the factory. It always helps to have some of the larger 
packages (namely `scipy`) installed system-wide in the background. 
The following commands will make a virtual environment, and 
using the `system` flag allows the system to use system-wide 
binaries if it can find them. Conversely, if your numpy or scipy 
installations are broken, you may wish to omit the `system` flag 
in which case factory will compile everything from scratch. Please
note that compiling from scratch takes about 10 minutes, so we 
recommend using your package manager instead. This solution is more
conservative, however, because it will not change any of your
system-wide settings, paths, etc.

Copy `connect.yaml` to `connect.local.yaml`. Select a use-case to 
start with (we recommend `NEW`) and set `enabled: true`. Then 
run the following commands.

```
make nuke && \
make env system && \
make connect connect.local.yaml && \
make run project
```

The final command starts the factory and provides a link
to the site. Everything runs in the background.

## Remote access

Running the factory uses two ports: `8000` for the site and `5555` 
for a `celery` utility called `flower` which monitors the background jobs.
If you are running the factory on a remote machine, you can view the 
HTML front-end over an ssh connection. First, add an alias for your 
machine to `~/.ssh/config`. If you have `ssh` keys you won't need to 
enter your password. Then, copy `./deploy/tunnelport` to your `$PATH` 
with execute permissions. Run `tunnelport <alias> [port]` to connect 
to both ports. If you specify a port, it will map `8000` to the port and 
`5555` to the next port. This lets you view multiple factories 
remotely from one machine. Close all factory tunnels by running
`tunnelport end` but beward this closes *all* tunnels to ports
`8000` and `5555`.

## Questions

Ask the [authors](mailto:biophyscode@gmail.com), who are happy to 
help you deploy the codes. 

