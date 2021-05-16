'''
Created on Feb 11, 2013

@author: shalom
'''

import os
import hashlib
import random
import queue
import threading
from collections import OrderedDict
import logging

import requests

logger = logging.getLogger('capi_tester')

#=====================================================================
#
# This is a cross between a dictionary and an LRU. It is based on
# the OrderedDict class
#
class LimitedSizeDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        if key in self: del self[key]
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()


    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)
                
                
#------------------------------------------------------------------------------------------


class MapSource:
    mapSources = {}
    
    ''' Define map sources using the same names as osmgpsmap for cache sharing. '''
    def __init__(self, name, friendlyName, URLTemplate, imageFormat = 'png'):
        self.name = name
        self.friendlyName = friendlyName
        self.URLTemplate = URLTemplate
        self.imageFormat = imageFormat
        MapSource.mapSources.setdefault(self.name, self)
        self.hash = hashlib.md5(URLTemplate.encode()).hexdigest()
        

MapSource("OSM_GPS_MAP_SOURCE_NULL",                        "None",                 "none://"),
MapSource("OSM_GPS_MAP_SOURCE_OPENSTREETMAP",              "OpenStreetMap I",   "http://tile.openstreetmap.org/%(zoom)d/%(x)d/%(y)d.png"),
MapSource("OSM_GPS_MAP_SOURCE_OPENSTREETMAP_RENDERER",   "OpenStreetMap II",    "http://tah.openstreetmap.org/Tiles/tile/%(zoom)d/%(x)d/%(y)d.png"),
#        MapSource("OSM_GPS_MAP_SOURCE_OPENAERIALMAP",              "OpenAerialMap",     "http://openaerialmap.org/pipermail/talk_openaerialmap.org/2008-December/000055.html"),
MapSource("OSM_GPS_MAP_SOURCE_OPENCYCLEMAP",               "OpenCycleMap", "http://c.andy.sandbox.cloudmade.com/tiles/cycle/%(zoom)d/%(x)d/%(y)d.png"),
MapSource("OSM_GPS_MAP_SOURCE_OSM_PUBLIC_TRANSPORT",     "Public Transport", "http://tile.xn--pnvkarte-m4a.de/tilegen/%(zoom)d/%(x)d/%(y)d.png"),
MapSource("OSM_GPS_MAP_SOURCE_OSMC_TRAILS",                "OSMC Trails", "http://topo.geofabrik.de/trails/%(zoom)d/%(x)d/%(y)d.png"),
MapSource("OSM_GPS_MAP_SOURCE_MAPS_FOR_FREE",              "Maps-For-Free", "http://maps-for-free.com/layer/relief/z%(zoom)d/row%(y)d/%(zoom)d_%(x)d-%(y)d.jpg", 'jpg'),
MapSource("OSM_GPS_MAP_SOURCE_GOOGLE_STREET",              "Google Maps", "http://mt%(random)d.google.com/vt/lyrs=m@146&hl=en&x=%(x)d&s=&y=%(y)d&z=%(zoom)d", 'jpg'),
MapSource("OSM_GPS_MAP_SOURCE_GOOGLE_SATELLITE",          "Google Satellite", "http://khm%(random)d.google.com/kh/v=80&x=%(x)d&y=%(y)d&z=%(zoom)d", 'jpg'),
MapSource("OSM_GPS_MAP_SOURCE_GOOGLE_HYBRID",              "Google Hybrid", "http://mt%(random)d.google.com/vt/lyrs=h@146&hl=en&x=%(x)d&s=&y=%(y)d&z=%(zoom)d", 'jpg'),
MapSource("OSM_GPS_MAP_SOURCE_VIRTUAL_EARTH_STREET",      "Virtual Earth", "http://a%(random)d.ortho.tiles.virtualearth.net/tiles/r#W.jpeg?g=50", 'jpg'),
MapSource("OSM_GPS_MAP_SOURCE_VIRTUAL_EARTH_SATELLITE",  "Virtual Earth Satellite", "http://a%(random)d.ortho.tiles.virtualearth.net/tiles/a#W.jpeg?g=50", 'jpg'),
MapSource("OSM_GPS_MAP_SOURCE_VIRTUAL_EARTH_HYBRID",      "Virtual Earth Hybrid", "http://a%(random)d.ortho.tiles.virtualearth.net/tiles/h#W.jpeg?g=50", 'jpg'),
#        MapSource("OSM_GPS_MAP_SOURCE_YAHOO_STREET",                "Yahoo Maps", "http://us.maps3.yimg.com/aerial.maps.yimg.com/ximg?v=1.7&t=a&s=256&x=%d&y=%-d&z=%d"),
#        MapSource("OSM_GPS_MAP_SOURCE_YAHOO_SATELLITE",            "Yahoo Satellite", "http://us.maps3.yimg.com/aerial.maps.yimg.com/ximg?v=1.7&t=a&s=256&x=%d&y=%-d&z=%d"),
#        MapSource("OSM_GPS_MAP_SOURCE_YAHOO_HYBRID",                "Yahoo Hybrid", "http://us.maps3.yimg.com/aerial.maps.yimg.com/ximg?v=1.7&t=a&s=256&x=%d&y=%-d&z=%d"),


#==============================================================================
class TileDownloader(threading.Thread):
    user_agent = {'user-agent': 'klvPlayer v1.11.1 contact shalomc@airoboticsdrones.com'}
    
    def __init__(self, queue, callback = None):
        threading.Thread.__init__(self, name = 'Tile download thread')
        self.queue = queue
        self.setDaemon(True)
        self.callback = callback
        self.start()
        
    #--------------------------------------------        
    def run(self):
        while True:
            job = self.queue.get()
            logger.debug(f'Queue size {self.queue.qsize()}: get tile {job[0]}')
            
            try:
                if os.path.exists(job[1]) and not job[6]:
                    logger.debug(f'File already exists - not fetching {job[1]}')
                    self.queue.task_done()
                    continue
                
                dirname = os.path.dirname(job[1])
                if not os.path.exists(dirname): 
                    os.makedirs(dirname)
                
                response = requests.get(job[0], headers=TileDownloader.user_agent)
                
                if response.ok:
                    with open(job[1], "wb") as fl:
                        fl.write(response.content)
                        
                    filename = job[1]
                    logger.debug(f"Retrieved tile {filename}")
                    if self.callback: 
                        self.callback(filename)
                        
                else:
                    logger.error(f"Failed to download tile HTTP response code {response.status_code}")
                
            except Exception as e:
                logger.exception(e)
                print(e)
            
            self.queue.task_done()
            
        


#==============================================================================
class Tiles:
    
    def __init__(self, callback = None):
        self.cacheDir = None
        self.callback = callback
        self.cacheTopLevel = os.path.expanduser('~/.cache/osmgpsmap')

        if not os.path.exists(self.cacheTopLevel): os.makedirs(self.cacheTopLevel)
        self.setMapSource("OSM_GPS_MAP_SOURCE_OPENSTREETMAP")
        
        self.pendingFiles = set()
        self.setlock = threading.Lock()
        self.queue = queue.Queue()
        self.tileDownloader = TileDownloader(self.queue, self.on_tile_retrieved)
        
        
        
    #---------------------------------
    def on_tile_retrieved(self, filename):
        if self.callback: self.callback(filename)
        
        with self.setlock:
            if filename in self.pendingFiles:
                self.pendingFiles.remove(filename)

    #---------------------------------
    def fileName(self, x,y,z):
        return os.path.join(self.cacheDir, str(z), str(x), str(y) + "." + self.mapSource.imageFormat)


    #---------------------------------
    def setMapSource(self, mapSource):
        if isinstance(mapSource, str): mapSource = MapSource.mapSources[mapSource]
        self.mapSource = mapSource
        
        self.cacheDir = os.path.join(self.cacheTopLevel, self.mapSource.hash)
        if not os.path.exists(self.cacheDir): os.makedirs(self.cacheDir)


    #---------------------------------
    def queueDownloadTile(self, x, y, z, override = False):
        filename = self.fileName(x, y, z)
        
        with self.setlock:
            if filename in self.pendingFiles:
                #print "File %s already in queue" % filename
                return
            else:
                self.pendingFiles.add(filename)
        
        r = random.randint(0, 4)
        url = self.mapSource.URLTemplate % {'random' : r, 'x' : x, 'y' : y, 'zoom' : z}
        self.queue.put((url, filename, x, y, z, override))
        #print 'Queing tile - queue size', self.queue.qsize()

    #---------------------------------
    def searchCache(self, x, y, z):
        fileName = self.fileName(x,y,z)
        return fileName if os.path.exists(fileName) else None
        
    #---------------------------------
    def getTile(self, x, y, z):
        tile = self.searchCache(x, y, z)
        
        if tile:
            return tile
        
        self.queueDownloadTile(x,y,z)
        return None 



