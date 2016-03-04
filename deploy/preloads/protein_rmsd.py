#!/usr/bin/python

import time
from numpy import *
import MDAnalysis
from base.tools import status

def protein_rmsd(grofile,trajfile,**kwargs):

	"""
	LIPID ABSTRACTOR
	Reduce a bilayer simulation to a set of points.
	"""

	#---unpack
	sn = kwargs['sn']
	work = kwargs['workspace']
	
	#---prepare universe	
	slice_name = kwargs['calc']['slice_name']
	group = kwargs['calc']['group']
	grofile,trajfile = [work.slices[sn][slice_name][group][i] for i in ['gro','xtc']]
	uni = MDAnalysis.Universe(work.postdir+grofile,work.postdir+trajfile)
	nframes = len(uni.trajectory)
	protein = uni.select_atoms('protein and name CA')

	#---reference frame
	uni.trajectory[0]
	r0 = protein.coordinates()
	r0 -= mean(r0,axis=0)

	#---collect coordinates
	nframes = len(uni.trajectory)
	coords = []
	for fr in range(0,nframes):
		uni.trajectory[fr]
		r1 = protein.coordinates()
		coords.append(r1)

	#---simple RMSD code
	rmsds = []
	for fr in range(nframes):
		status('RMSD',i=fr,looplen=nframes)
		r1 = coords[fr]
		r1 -= mean(r1,axis=0)
		#---computation of RMSD validated against VMD but no reflection
		U,s,Vt = linalg.svd(dot(r0.T,r1))
		signer = identity(3)
		signer[2,2] = sign(linalg.det(dot(Vt.T,U)))
		RM = dot(dot(U,signer),Vt)
		rmsds.append(sqrt(mean(sum((r0.T-dot(RM,r1.T))**2,axis=0))))

	#---pack
	attrs,result = {},{}
	result['rmsds'] = array(rmsds)
	return result,attrs	
