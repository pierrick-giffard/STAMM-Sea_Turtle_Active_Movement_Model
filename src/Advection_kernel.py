#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Define the advection kernel.
In active mode, the swimming velocity is added to the current velocity.
"""

from parcels import AdvectionRK4, AdvectionEE



def RK4_swim(particle, fieldset, time):
    """
    Advection of particles using fourth-order Runge-Kutta integration.
    Swimming velocity is added to the current velocity.
    Swimming velocity is supposed constant during the whole timestep.
    """
    (u1, v1) = fieldset.UV[time, particle.depth, particle.lat, particle.lon]
    u1 += particle.u_swim
    v1 += particle.v_swim
    lon1, lat1 = (particle.lon + u1*.5*particle.dt, particle.lat + v1*.5*particle.dt)

    (u2, v2) = fieldset.UV[time + .5 * particle.dt, particle.depth, lat1, lon1]
    u2 += particle.u_swim
    v2 += particle.v_swim
    lon2, lat2 = (particle.lon + u2*.5*particle.dt, particle.lat + v2*.5*particle.dt)

    (u3, v3) = fieldset.UV[time + .5 * particle.dt, particle.depth, lat2, lon2]
    u3 += particle.u_swim
    v3 += particle.v_swim
    lon3, lat3 = (particle.lon + u3*particle.dt, particle.lat + v3*particle.dt)

    (u4, v4) = fieldset.UV[time + particle.dt, particle.depth, lat3, lon3]
    u4 += particle.u_swim
    v4 += particle.v_swim

    particle.lon += (u1 + 2*u2 + 2*u3 + u4) / 6. * particle.dt
    particle.lat += (v1 + 2*v2 + 2*v3 + v4) / 6. * particle.dt


def Euler_swim(particle, fieldset, time):
    """
    Advection of particles using Explicit Euler (aka Euler Forward) integration.
    Swimming velocity is added to the current velocity.
    """
    (u1, v1) = fieldset.UV[time, particle.depth, particle.lat, particle.lon]
    u1 += particle.u_swim
    v1 += particle.v_swim
    particle.lon += u1 * particle.dt
    particle.lat += v1 * particle.dt
            
    

def define_advection_kernel(pset, mode, adv_scheme):
    """
    Function that defines the kernel that will be used for advection.
    Parameters:
        -pset: ParticleSet
        -mode: active or passive
        -adv_scheme: RK4 or Euler
    Return: the advection kernel (kernel object)
    """
    if mode == 'passive':
        if adv_scheme == 'RK4':
            adv_kernel = AdvectionRK4
        elif adv_scheme == 'Euler':
            adv_kernel = AdvectionEE
            
       
    elif mode == 'active':
        if adv_scheme == 'RK4':
            adv_kernel = RK4_swim 
        elif adv_scheme == 'Euler':
            adv_kernel = Euler_swim
    
    return pset.Kernel(adv_kernel)
