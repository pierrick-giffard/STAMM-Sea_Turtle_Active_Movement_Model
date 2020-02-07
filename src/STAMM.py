#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main code of STAMM.
Need parcels version 2.0.0.

Author: Pierrick Giffard in Philippe Gaspar team at Mercator Ocean.
February 2020.
"""

# =============================================================================
# IMPORTS
# =============================================================================
#Python libraries
from parcels import plotTrajectoriesFile, ErrorCode
from datetime import timedelta as delta
import sys

#Personal libraries
import IOlib as IO
import TurtleClass as tc
import Advection_kernel as adv
import Passive_kernels as pk
import Active_kernels as ak
import Functions as fc

# =============================================================================
# PARAMETERS
# =============================================================================
#Users arguments
namelist = sys.argv[1]
OutputFile = sys.argv[2]

#Read namelist
param = IO.read_namelist(namelist)
IO.check_param(param,OutputFile)

#Time step in seconds
tstep = param['tstep']
#Number of time steps
ndays_simu = param['ndays_simu']
#Output frequency
t_output = param['t_output']
#Temporal loop over data for time_periodic days
time_periodic = param['time_periodic'] 

# =============================================================================
# Read initial positions and time
# =============================================================================
lon_init, lat_init, t_init = IO.read_positions(param)

# =============================================================================
# FIELDSET, CLASS AND PARTICLESET
# =============================================================================
fieldset = fc.create_fieldset(param, t_init)
turtle = tc.define_Turtle_Class(fieldset,param)
pset = fc.create_particleset(fieldset, turtle, lon_init, lat_init, t_init)

#
fc.initialization(pset, param)

# =============================================================================
# KERNELS
# =============================================================================
k_adv = adv.define_advection_kernel(pset, param)
k_active = ak.define_turtle_kernels(pset, param)
k_passive = pk.define_passive_kernels(fieldset, pset, param) 
#
kernels = pk.sum_kernels(k_adv, k_active, k_passive)

    
# =============================================================================
# COMPUTATION
# =============================================================================
output_file = pset.ParticleFile(name=OutputFile, outputdt=delta(seconds=t_output))
pset.execute(kernels, runtime=delta(days=ndays_simu), dt=delta(seconds=tstep),\
             output_file=output_file,\
             recovery={ErrorCode.ErrorOutOfBounds: pk.DeleteParticle})




# =============================================================================
# PLOT
# =============================================================================
output_file.export()  # only for parcels version > 2.1
plotTrajectoriesFile(OutputFile)
