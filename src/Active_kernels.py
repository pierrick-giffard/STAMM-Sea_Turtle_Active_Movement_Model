#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kernels used to compute swimming velocity. 
"""


from math import sqrt, cos, sin, atan2
import math
from parcels import random



def compute_swimming_direction(particle, fieldset, time):
    """
    Compute particule.theta
    Theta has to be between 0 and 2*pi for random.vommises, 0 corresponding to east.
    """
    #Compute theta0
    theta0 = atan2(particle.ygradh,particle.xgradh) #return 0 in case xgradh=ygradh=0 (east !)
                                                    #but ok because vonmises becomes uniform without gradient
    if theta0 < 0:
        theta0 = 2 * math.pi + theta0 #theta0 has to be between 0 and 2*pi
    
    grad = sqrt(math.pow(particle.xgradh, 2) + math.pow(particle.ygradh, 2))
    
    #Compute theta
    particle.theta = random.vonmisesvariate(theta0,fieldset.alpha*grad)




def compute_swimming_velocity(particle, fieldset, time):
    """
    Compute particule.u_swim and particle.v_swim
    """
    particle.u_swim = particle.vmax * (1-particle.hab) * cos(particle.theta)
    particle.v_swim = particle.vmax * (1-particle.hab) * sin(particle.theta)
    


def cold_induced_mortality(particle, fieldset, time):
    """
    Increment particle.lethargy_time if T < Tmin.
    If particle.lethargy_time > cold_resistance, then delete particle.
    """
    if fieldset.T[time, particle.depth, particle.lat, particle.lon] < particle.Tmin:
        particle.lethargy_time += fieldset.tstep
        if particle.lethargy_time > fieldset.cold_resistance:
            particle.cold_death = 1
            particle.delete()
    else:
        particle.lethargy_time = 0    


                








