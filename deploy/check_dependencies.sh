#!/bin.bash

#---check for numpy development headers
python -c "import numpy,glob;header,=glob.glob(numpy.get_include()+'/numpy/arrayobject.h')"
if [ $? -ne 0 ]; then
if [[ -e logs/override_please ]]; then 
echo "[WARNING] found logs/override_please but hdf5 might be missing"
else
echo "[ERROR] failed to find arrayobject.h: please install python-numpy-dev"
echo "[HINT] touch logs/override_please and try again if everything is cool"
exit 1
fi;fi

#---check for hdf5 libraries
#---! check for hdf5 libraries in OSX?
if [[ -z $(/sbin/ldconfig -p | grep hdf5) ]]; then  
echo "[STATUS] failed to find hdf5 libraries using \"/sbin/ldconfig -p\""
echo "[STATUS] since this might be OSX, checking brew"
if [[ -z $(brew search hdf5) ]]; then 
if [[ -e logs/override_please ]]; then 
echo "[WARNING] found logs/override_please but hdf5 might be missing"
else
echo "[ERROR] failed to find hdf5 headers with ldconfig or brew"
echo "[ERROR] on OSX try \"brew install hdf5\", on RPM try to install hdf5-devel, on DEB try hdf5-dev"
echo "[HINT] touch logs/override_please and try again if everything is cool"
exit 1
fi;fi;fi
