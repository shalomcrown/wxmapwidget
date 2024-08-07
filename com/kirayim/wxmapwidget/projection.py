#!/usr/bin/python
#-----------------------------------------------------------------------------
# Projection code (lat/long to screen conversions)
#
# Usage: 
#   (library code for pyroute GUI, not for direct use)
#-----------------------------------------------------------------------------
# Copyright 2007, Oliver White
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------------

from tilenames import latlon2xy, tileSizePixels, xy2latlon

import math


class Projection:
    radius = 6366710.0 # Earth's radius in meters - as nautical mile.    
    
    def __init__(self):
        self.xyValid = False
        self.llValid = False
        self.needsEdgeFind = False
        self.zoomLimit = 17
        
        # Scale is the number of display pixels per projected unit
        self.scale = tileSizePixels()
    
    #-----------------------------------------------------------------
    def isValid(self):
        """Test if the module contains all the information needed to do conversions"""
        return(self.xyValid and self.llValid)
  
    #-----------------------------------------------------------------
    def setView(self,x,y,w,h):
        """Setup the display"""
        self.w = w
        self.h = h
        self.xc = x + self.w
        self.yc = y + self.h
        self.xyValid = True
        if(self.needsEdgeFind):
            self.findEdges()
    
    #-----------------------------------------------------------------
    def recentre(self,lat,lon,zoom = None):
        """Move the projection to a particular geographic location
        (with optional zoom level)"""
        self.lat = lat
        self.lon = lon
        if(zoom != None):
            self.implementNewZoom(zoom)
            # note: implementNewZoom calls findEdges, hence the else: statement
        else:
            self.findEdges()
        self.llValid = True
    
    #-----------------------------------------------------------------
    def setZoom(self, value, isAdjustment=False):
        """Change the zoom level, keeping same map centre
        if isAdjustment is true, then value is relative to current zoom
        otherwise it's an absolute value"""
        if(isAdjustment):
            # TODO: maybe we don't want all zoom levels?
            self.implementNewZoom(self.zoom + value)
        else:
            self.implementNewZoom(value)

    #-----------------------------------------------------------------
    def limitZoom(self):
        """Check the zoom level, and move it if necessary to one of
            the 'allowed' zoom levels"""
        if self.zoom < 1: self.zoom = 1
        elif self.zoom > self.zoomLimit: self.zoom = self.zoomLimit
  
    #-----------------------------------------------------------------
    def implementNewZoom(self, zoom):
        """Change the zoom level"""
        self.zoom = int(zoom)
        # Check it's valid
        self.limitZoom()
        # Update the projection
        self.findEdges()
  
    #-----------------------------------------------------------------
    def findEdges(self):
        """Update the projection meta-info based on its fundamental parameters"""
        if(not self.xyValid):
            # If the display is not known yet, then we can't do anything, but we'll
            # mark it as something that needs doing as soon as the display 
            # becomes valid
            self.needsEdgeFind = True
            return
        
        # Find the map centre in projection units
        self.px, self.py = latlon2xy(self.lat,self.lon,self.zoom)
        
        # Find the map edges in projection units
        self.px1 = self.px - 0.5 * self.w / self.scale
        self.px2 = self.px + 0.5 * self.w / self.scale
        self.py1 = self.py - 0.5 * self.h / self.scale
        self.py2 = self.py + 0.5 * self.h / self.scale
        
        # Store width and height in projection units, just to save time later
        self.pdx = self.px2 - self.px1
        self.pdy = self.py2 - self.py1
        
        # Calculate the bounding box 
        # ASSUMPTION: (that the projection is regular and north-up)
        self.N,self.W = xy2latlon(self.px1, self.py1, self.zoom)
        self.S,self.E = xy2latlon(self.px2, self.py2, self.zoom)
        
        # Mark the meta-info as valid
        self.needsEdgeFind = False
  
    #-----------------------------------------------------------------
    def pxpy2xy(self,px,py):
        """Convert projection units to display units"""
        x = self.w * (px - self.px1) / self.pdx
        y = self.h * (py - self.py1) / self.pdy
        return(x,y)

    # -----------------------------------------------------------------
    def pxpy2xyi(self, px, py):
        """Convert projection units to display units, return integers"""
        x = self.w * (px - self.px1) / self.pdx
        y = self.h * (py - self.py1) / self.pdy
        return (int(x), int(y))

    #-----------------------------------------------------------------
    def nudge(self,dx,dy):
        """Move the map by a number of pixels relative to its current position"""
        if dx == 0 and dy == 0: return
        
        # Calculate the lat/long of the pixel offset by dx,dy from the centre,
        # and centre the map on that
        newXC = self.px - dx / self.scale
        newYC = self.py - dy / self.scale
        self.lat,self.lon = xy2latlon(newXC,newYC, self.zoom)
        self.findEdges()

    #-----------------------------------------------------------------
    def ll2xy(self,lat,lon):
        """Convert geographic units to display units"""
        px,py = latlon2xy(lat,lon,self.zoom)
        x = (px - self.px1) * self.scale
        y = (py - self.py1) * self.scale
        return(x,y)

    # -----------------------------------------------------------------
    def ll2xyi(self, lat, lon):
        """Convert geographic units to display units, return integers"""
        px, py = latlon2xy(lat, lon, self.zoom)
        x = (px - self.px1) * self.scale
        y = (py - self.py1) * self.scale
        return (int(x), int(y))

    #-----------------------------------------------------------------
    def xy2ll(self,x,y):
        """Convert display units to geographic units"""
        px = self.px1 + x / self.scale
        py = self.py1 + y / self.scale
        lat,lon = xy2latlon(px, py, self.zoom)
        return(lat,lon)
  
    #-----------------------------------------------------------------
    def onscreen(self,x,y):
        """Test if a position (in display units) is visible"""
        return(x >= 0 and x < self.w and y >= 0 and y < self.h)
  
    #-----------------------------------------------------------------
    def relXY(self,x,y):
        return(x/self.w, y/self.h)
    
    
    #-----------------------------------------------------------------
    #
    # Great circle spherical distance (not WGS..) between two 
    # lat/lon pairs, in meters
    #
    def distanceMeters(self, origin, destination):
        lat1, lon1 = origin
        lat2, lon2 = destination
    
        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = self.radius * c
    
        return d
    
    #-----------------------------------------------------------------
    #  
    def araz(self, origin, distanceMeters, azimuthDegrees):
        # Calculate new lat/lon from original point plus distance and
        # azimuth. Uses spherical geometry, not WGS
        oldlat, oldlon = math.radians(origin[0]), math.radians(origin[1])
        

        angle = math.radians(azimuthDegrees)
        dist = distanceMeters / self.radius  # convert to angular distance
        lat = math.asin(math.sin(oldlat) * math.cos(dist) + math.cos(oldlat) * math.sin(dist) * math.cos(angle))
        dlon = math.atan2( math.sin(angle)* math.sin(dist)* math.cos(oldlat), math.cos(dist) - math.sin(oldlat) * math.sin(lat))
        lon = ((oldlon - dlon + math.pi) % (2 * math.pi)) - math.pi
        return math.degrees(lat), math.degrees(lon)
