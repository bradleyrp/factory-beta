#!/bin.bash

#---check for numpy development headers
python -c "import numpy,glob;header,=glob.glob(numpy.get_include()+'/numpy/arrayobject.h')"
if [ $? -ne 0 ]; then { echo "[ERROR] failed to find arrayobject.h: please install python-numpy-dev"; exit 1; } fi

#---check for hdf5 libraries
if [[ -z $(/sbin/ldconfig -p | grep hdf5) ]]; then  
echo "[ERROR] failed to find hdf5 libraries using \"/sbin/ldconfig -p\": please install hdf5 to continue"; exit 1; 
fi

#---! must also check for "hdf5-devel" on RPM-based distros