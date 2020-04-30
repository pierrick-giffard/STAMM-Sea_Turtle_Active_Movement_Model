#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Functions needed to:
    -create FieldSet
    -create ParticleSet
    -define kernels to be used in execute
    -modify output file
"""

# =============================================================================
# IMPORTS
# =============================================================================
#Python libraries
from parcels import FieldSet, ParticleSet, AdvectionRK4, AdvectionEE, Field
from datetime import timedelta
import numpy as np
import time
import netCDF4
import math
import subprocess
import sys, os, operator

#Personal libraries
import Advection_kernel as adv
import Passive_kernels as pk
import Active_kernels as ak
sys.path.insert(1, os.path.join(sys.path[0], 'Species'))
import Leatherback as leath
import Loggerhead as log
sys.path.insert(1, os.path.join(sys.path[0], '../LIB'))
import IOlib as IO


# =============================================================================
# FIELDSET
# =============================================================================
def create_fieldset(param, ndays_simu, t_init):
    """
    Build fieldset from data files, dimensions and variables.
    """
    print('****************************************************')
    print("Building FieldSet...")
    print('****************************************************')
    t0 = time.time()
    key_alltracers = param['key_alltracers']
    mesh_phy = param['mesh_phy']
    mesh_food = param['mesh_food']
    #Forcings
    last_date = IO.find_last_date(param)
    date_start, date_end, time_periodic = IO.define_start_end(ndays_simu, param, t_init, last_date)
    ufiles = IO.forcing_list(param['U_dir'], param['U_suffix'], date_start, date_end, print_date=True)
    vfiles = IO.forcing_list(param['V_dir'], param['V_suffix'], date_start, date_end)
    #Filenames
    filenames = {'U': {'lon': mesh_phy, 'lat': mesh_phy, 'data': ufiles},
                 'V': {'lon': mesh_phy, 'lat': mesh_phy, 'data': vfiles}}
    #Variables
    variables = {'U': param['U_var'],
                 'V': param['V_var']}
    #Dimensions: Caution, C-grids need f nodes
    dimensions = {'U': {'lon': param['lon_phy'], 'lat': param['lat_phy'], 'time': param['time_var_phy']},
                  'V': {'lon': param['lon_phy'], 'lat': param['lat_phy'], 'time': param['time_var_phy']}}
    if time_periodic:
        time_periodic *= 86400 #days to seconds
    #Fieldset creation
    chs = {'longitude':256, 'latitude':256}
    if param['grid_phy'] == 'A':
        fieldset = FieldSet.from_netcdf(filenames, variables, dimensions, time_periodic=time_periodic, field_chunksize=chs)
        #add_LandMask(ufiles[0], param['U_var'], param, fieldset)
    else:
        fieldset = FieldSet.from_c_grid_dataset(filenames, variables, dimensions, time_periodic=time_periodic, field_chunksize=chs)
    
    
    if key_alltracers:
        tfiles = IO.forcing_list(param['T_dir'], param['T_suffix'], date_start, date_end)
        ffiles = IO.forcing_list(param['food_dir'], param['food_suffix'], date_start, date_end, vgpm=param['vgpm'])
        #Filenames
        Tfiles = {'lon': mesh_phy, 'lat': mesh_phy, 'data': tfiles}
        NPPfiles = {'lon': mesh_food, 'lat': mesh_food, 'data': ffiles}
        #Dimensions
        if param['grid_phy'] == 'A':
            Tdim = {'lon': param['lon_phy'], 'lat': param['lat_phy'], 'time': param['time_var_phy']}
        else:
            Tdim = {'lon': param['lon_T'], 'lat': param['lat_T'], 'time': param['time_var_phy']}
        NPPdim = {'lon': param['lon_food'], 'lat': param['lat_food'], 'time': param['time_var_food']}
        #Field creation
        T = Field.from_netcdf(Tfiles, ('T', param['T_var']), Tdim, interp_method='linear_invdist_land_tracer', time_periodic=time_periodic, field_chunksize=chs)
        NPP = Field.from_netcdf(NPPfiles, ('NPP', param['food_var']), NPPdim, interp_method='linear_invdist_land_tracer', time_periodic=time_periodic, field_chunksize={'time':1,'fakeDim0':256, 'fakeDim1':256})
        #Add to fieldset
        fieldset.add_field(T)
        fieldset.add_field(NPP)
        
    #East/West periodicity
    if param['periodicBC'] and not param['halo']:
        add_halo(fieldset)

    #Time
    tt=time.time()-t0
    print('\n')
    print(' => FieldSet created in: '+ str(timedelta(seconds=int(tt))))
    print('\n')
    return fieldset




def PSY_patch(fieldset,param):
    """
    Our files PSY4 interpolated on A-grid coarsened to 1/4° have a 
    problem at the equator and at Greenwich meridian: lon and lat are NaN.
    This function passes them to 0.
    """
    try:
        fieldset.U.grid.lon[:,720] = 0
        fieldset.U.grid.lat[320,:] = 0
        fieldset.V.grid.lon[:,720] = 0
        fieldset.V.grid.lat[320,:] = 0
        print('Using PSY patch')
        if param['key_alltracers']:
            fieldset.T.grid.lon[:,720] = 0
            fieldset.T.grid.lat[320,:] = 0
            fieldset.NPP.grid.lon[:,720] = 0
            fieldset.NPP.grid.lat[320,:] = 0
    except:
        print('Not Using PSY patch')


def add_halo(fieldset):
    try:
        fieldset.add_constant('halo_west', fieldset.U.grid.lon[0,0])
        fieldset.add_constant('halo_east', fieldset.U.grid.lon[0,-1])
    except:
        fieldset.add_constant('halo_west', fieldset.U.grid.lon[0])
        fieldset.add_constant('halo_east', fieldset.U.grid.lon[-1])
    #          
    fieldset.add_periodic_halo(zonal=True)

""" not working for the moment
def add_LandMask(file, var, param, fieldset):
    nc = netCDF4.Dataset(file)
    values = nc.variables[var][:]
    print(values)
    data = np.where(values == np.nan, 0, 1) 
    if param['grid_phy'] == 'A':
        mask = Field('LandMask', data, grid = fieldset.U.grid)
    elif param['grid_phy'] == 'C' and key_alltracers==True:
        mask = Field('LandMask', data, grid = fieldset.T.grid)
    else:
        raise ValueError("LandMask à implementer..., (recuperer les lon/lat centres).")
    fieldset.add_field(mask)
"""

# =============================================================================
# PARTICLESET
# =============================================================================
def create_particleset(fieldset, pclass, lon, lat, t_init, param):
    print('\n')
    print('****************************************************')
    print("Building ParticleSet...")
    print('****************************************************')
    #
    t0 = time.time()
    #
    t_release = (t_init - np.min(t_init)) * 86400
    pset = ParticleSet(fieldset, pclass=pclass, lon=lon, lat=lat, time = t_release)
    #
    pset.execute(pk.CheckOnLand, dt=0)
    #Time
    tt=time.time()-t0
    print('\n')
    print(' => ParticleSet created in: '+ str(timedelta(seconds=int(tt))))
    print('\n')
    
    return pset


# =============================================================================
# CONSTANT PARAMETERS
# =============================================================================
def initialization(fieldset, ndays_simu, param):
    """
    Links constant parameters to fieldset in order to use them within kernels.
    """
    fieldset.deg = 111120. #1degree = 111,120 km approx (same as in parcels)
    fieldset.cold_resistance = param['cold_resistance'] * 86400 #from days to seconds
    fieldset.ndays_simu = ndays_simu
    if param['mode'] == 'active':
        ### NAMELIST PARAMETERS ###
        fieldset.active = 1
        fieldset.vscale = param['vscale']
        fieldset.P0 = param['P0']
        fieldset.grad_dx = param['grad_dx']
        fieldset.alpha = param['alpha']
        fieldset.SCL0 = param['SCL0']
        fieldset.t = param['tactic_factor']
        ### SPECIES PARAMETERS ###
        if param['species'] == 'leatherback':
            file = leath
        elif param['species'] == 'loggerhead':
            file = log
        #
        fieldset.a = file.a
        fieldset.b = file.b
        fieldset.d = file.d
        if param['growth'] == 'VGBF':
            fieldset.k = file.k
            fieldset.SCLmax = file.SCLmax
            fieldset.beta_jones = file.beta_jones
        elif param['growth'] == 'Gompertz':
            fieldset.alpha_gomp = file.alpha_gomp
            fieldset.beta = file.beta
            fieldset.M0 = file.M0
            fieldset.S = file.S
            fieldset.K0 = file.K0
            fieldset.c = file.c
        if file.Tmin_Topt == 'constant':
            fieldset.Tmin = file.Tmin
            fieldset.Topt = file.Topt
        elif file.Tmin_Topt == 'variable':
            fieldset.T0 = file.T0
            fieldset.to = file.to
            fieldset.tm = file.tm
            fieldset.Tmin = 0.
            fieldset.Topt = 0.
        else:
            raise ValueError('Please set Tmin_Topt to constant or variable')
        param['Tmin_Topt'] = file.Tmin_Topt
    else:
        fieldset.active = 0
    if param['key_alltracers']:
        fieldset.key_alltracers = 1
    else:
        fieldset.key_alltracers = 0



# =============================================================================
# DEFINE KERNELS
# =============================================================================
def define_advection_kernel(pset, param):
    """
    Function that defines the kernel that will be used for advection.
    Parameters:
        -pset: ParticleSet
        -param: needs mode (active or passive) and adv_scheme (RK4 or Euler)
    Return: the advection kernel (kernel object)
    """
    mode = param['mode']
    adv_scheme = param['adv_scheme']
    #passive
    if mode == 'passive':
        if adv_scheme == 'RK4':
            adv_kernel = AdvectionRK4
        elif adv_scheme == 'Euler':
            adv_kernel = AdvectionEE
    #active
    elif mode == 'active':
        if adv_scheme == 'RK4':
            adv_kernel = adv.RK4_swim 
        elif adv_scheme == 'Euler':
            adv_kernel = adv.Euler_swim
    
    return pset.Kernel(adv_kernel)



def define_passive_kernels(fieldset, pset, param):
    """
    Parameters:
        -fieldset
        -pset
        -param: needs key_alltracers (if True, T and NPP are sampled) and
        periodicBC (True for east/west periodicity)
    """
    key_alltracers = param['key_alltracers']
    periodicBC = param['periodicBC']
    mode = param['mode']
    #
    kernels_list = [pk.store_variables,
                    pk.IncrementAge, 
                    pk.BeachTesting, 
                    pk.UndoMove]
    #
    if key_alltracers and mode == 'passive':
        kernels_list.append(pk.SampleTracers)
    #
    if periodicBC:
        kernels_list.append(pk.Periodic)
    #
    for k in range(len(kernels_list)):
        kernels_list[k]=pset.Kernel(kernels_list[k])  
    return kernels_list



def define_active_kernels(pset, param):
    """
    Function that defines additional kernel that will be used for computation.
    Parameters:
        -pset: ParticleSet
        -param: needs mode (active or passive) and species (leatherback, loggerhead or green)
    """
    #
    mode = param['mode']
    species = param['species']
    growth = param['growth']
    #
    kernels_list = []
    if mode == 'active':      
        if growth == 'VGBF':
            compute_SCL = ak.compute_SCL_VGBF
            compute_PPmax = ak.compute_PPmax_VGBF   
        elif growth == 'Gompertz':
            compute_SCL = ak.compute_SCL_Gompertz
            compute_PPmax = ak.compute_PPmax_Gompertz
        #
        kernels_list = [compute_SCL,
                        ak.compute_Mass,
                        compute_PPmax,
                        ak.compute_vmax,
                        ak.compute_habitat,
                        ak.compute_swimming_direction,
                        ak.compute_swimming_velocity]
        if param['Tmin_Topt'] == 'variable':
            kernels_list.insert(2, ak.compute_Tmin_Topt) #Needs to be after compute_Mass
    if param['cold_death']:
        kernels_list.append(ak.cold_induced_mortality)
        
    for k in range(len(kernels_list)):
        kernels_list[k]=pset.Kernel(kernels_list[k]) 
    return kernels_list



def sum_kernels(k_adv, k_active, k_passive):
    """
    Sums all the kernels and returns the summed kernel.
    WARNING: The position is important.
    """
    kernels = k_passive[0] #store_variables kernel
    print_kernels = [k_passive[0].funcname]
    if k_active != []:
        for k in k_active:
            kernels = kernels + k
            print_kernels.append(k.funcname)
    kernels += k_adv
    print_kernels.append(k_adv.funcname)
    #    
    for k in k_passive[1:]:
        kernels = kernels + k
        print_kernels.append(k.funcname)
    #
    print('****************************************************')
    print("These kernels will be used for computation: \n")
    for k in print_kernels:
        print(k, "\n")
    print('****************************************************')
    
    return kernels


# =============================================================================
# OUTPUT
# =============================================================================
def modify_output(OutputFile, t_init, param):
    """
    Modify output file so that variables names are the same as in STAMM 2.0 and
    turtles live exactly ndays_simu days.
    """
    dt = math.ceil(max(t_init) - min(t_init))
    #
    nc_i = netCDF4.Dataset(OutputFile, 'r')
    name_out = OutputFile.replace('.nc', '0.nc')
    nc_o = netCDF4.Dataset(name_out, 'w')
    #
    nsteps = nc_i.dimensions['obs'].size
    nturtles = nc_i.dimensions['traj'].size
    #
    nc_o.createDimension('nsteps', size = nsteps - dt)
    nc_o.createDimension('nturtles', size = nturtles)
    #
    for var_name in nc_i.variables:
        if var_name not in ['time','trajectory','z']:
            var = nc_i.variables[var_name]
            if dt > 0:
                values = np.transpose(np.squeeze(var))[:-dt, :]
            else:
                values = np.transpose(np.squeeze(var))[:]
            tmp = nc_o.createVariable(var_name, 'f', ('nsteps','nturtles'))
            tmp[:] = values
    #
    nc_o.renameVariable('lat','traj_lat')
    nc_o.renameVariable('lon','traj_lon')
    nc_o.renameVariable('age','traj_time')
    if param['key_alltracers']:
        nc_o.renameVariable('T','traj_temp')
        nc_o.renameVariable('NPP','traj_pp')
    if param['mode'] == 'active':
        nc_o.renameVariable('xgradh','xgrad')
        nc_o.renameVariable('ygradh','ygrad')
    init_t = nc_o.createVariable('init_t', 'f', ('nturtles'))
    init_t[:] = t_init
    #Global variables
    nc_o.title = 'Output variables from Sea Turtle Active Movement Model'
    nc_o.tstep = float(param['tstep'])
    nc_o.adv_scheme = param['adv_scheme']
    nc_o.ystart = param['ystart']
    if param['mode'] == 'active':
        nc_o.species = param['species']
        nc_o.alpha = param['alpha']
        nc_o.vscale = param['vscale']
        nc_o.grad_dx = param['grad_dx']
        nc_o.P0 = param['P0']
        nc_o.growth = param['growth']
    #
    nc_o.close()
    nc_i.close()
    #delete initial OutputFile 
    subprocess.run(["mv", "-f", name_out, OutputFile])
    print('\n')
    print('********************************************************************************')
    print("Wrote", OutputFile)
    print('********************************************************************************')
    print('\n')
    
        
       
