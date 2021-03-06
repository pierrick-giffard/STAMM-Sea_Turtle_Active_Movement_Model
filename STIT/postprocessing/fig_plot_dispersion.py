#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Usage: fig_plot_dispersion namelist.nc zone
zone (optional) can be NA, PA', 'auto' 
"""

# =============================================================================
# IMPORTS
# =============================================================================
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

#Personal Librairies
sys.path.insert(1, os.path.join(sys.path[0], '../../LIB'))
import plot_lib as pl
import netCDF_lib as ncl
# =============================================================================
# USERS PARAMETERS
# =============================================================================

# =============================================================================
# CODE
# =============================================================================
ifile = sys.argv[1]
try:
    zone = str(sys.argv[2])
except:
    zone = 'auto'
    print('Zone was set to auto. You can define it with a third argument (ex: NA)')

ofile = ifile.replace(".nc","_dispersion.png")
## -- Si l'affichage coupe les trace à 0° de longitude, bien vérifier que x n'est pas corrigé dans 
## -- PlotTrajectories2(display_trajectories_all) : #x = np.array([l+(((1-np.sign(l))/2)*360) for l in x])
## -- il faut que cette ligne soit bien commentée

# Plot figure ------
c = 0.89
f = plt.figure(figsize = (12*c/2.54,8*c/2.54))
gs = gridspec.GridSpec(2,1,height_ratios=[11,1],left=0.08, right=0.98, bottom=0.07, top=0.95)

dataFile = ncl.data(ifile)
# =============================================================================
# ZONE TO PLOT
# =============================================================================
if zone == 'auto':
    zoom_out = 10
    xmin = np.min(dataFile.lon) - zoom_out
    xmax = np.max(dataFile.lon) + zoom_out
    ymin = max(-90, np.min(dataFile.lat) - zoom_out)
    ymax = min(90, np.max(dataFile.lat) + zoom_out)

elif zone == 'NA':
    xmin = -110
    xmax = 30
    ymin = -10
    ymax = 70

elif zone == 'PA':
    xmin = -60
    xmax = 300
    ymin = -60
    ymax = 60

elif zone == 'IND':
    xmin = 0
    xmax = 120
    ymin = -60
    ymax = 20

elif zone == 'COR': #coral sea
    xmin = 80
    xmax = 220
    ymin = -60
    ymax = 10


lat_space = 20
lon_space = 40




ax = plt.subplot(gs[0])
     
im,time = pl.display_trajectories(dataFile,f,ax,xmin)
pl.show_start_point(ax, dataFile.lat, dataFile.lon-360)
pl.plot_map(ax,ymin,ymax,xmin,xmax,lon_space=lon_space,lat_space=lat_space)

 
ax.spines['right'].set_linewidth(0.5)
ax.spines['left'].set_linewidth(0.5)
ax.spines['bottom'].set_linewidth(0.5)
ax.spines['top'].set_linewidth(0.5)
        

if np.max(time)>0*365: 
    ax_cb = plt.subplot(gs[1])
    label = u"Age (Years)"
    pl.display_colorbar(f,im, ax_cb, label)

else:
    ax_cb = plt.subplot(gs[2])
    label = u"Age (Days)"
    pl.display_colorbar(f,im, ax_cb, label)
            
        
plt.savefig(ofile,bbox_inches='tight',dpi=800)
print('\n')
print('********************************************************************************')
print("Wrote", ofile)
print('********************************************************************************')
plt.close()
