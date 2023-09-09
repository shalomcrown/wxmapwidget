#!/usr/bin/env python3
'''
Created on Jun 27, 2020

@author: shalomc
'''

import math
import sys
import os

scriptPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scriptPath)

from projection import Projection
from tiles import Tiles, LimitedSizeDict

import wx
import tilenames

wx.InitAllImageHandlers()


def drawArrowhead(dc, fromX, fromY, toX, toY, color = wx.BLACK, filled=True, width=3):
    ang = math.atan2(toX - fromX, fromY - toY);
    arrowAngle = ang - math.radians(33) + math.pi / 2 ;

    dc.SetPen(wx.Pen(color, width, wx.PENSTYLE_SOLID))
    dc.SetBrush(wx.Brush(color, wx.BRUSHSTYLE_SOLID if filled else wx.BRUSHSTYLE_TRANSPARENT))
    
    points = [wx.Point(toX, toY),
              wx.Point(toX + width * math.cos(arrowAngle), toY + width * math.sin(arrowAngle)) ]

    arrowAngle = ang +  math.radians(33) +  math.pi / 2;
    
    points.append(wx.Point(toX + width * math.cos(arrowAngle), toY + width * math.sin(arrowAngle)))
    points.append(wx.Point(toX, toY));
    
    dc.DrawPolygon(points)
    
    
#------------------------------------------------------------------------------------------

def drawDroneSymbol(dc, x, y, heading):
    dc.SetPen(wx.Pen(wx.BLACK, 2));
    
    heading = math.radians(heading) - math.pi / 2
    xOffset = 10 * math.cos(heading + math.pi / 4)
    yOffset = 10 * math.sin(heading + math.pi / 4)
    
    dc.DrawLine(x - xOffset, y - yOffset, x + xOffset, y + yOffset)
    dc.DrawLine(x + yOffset, y - xOffset, x - yOffset, y + xOffset)

    xOffset = 12 * math.cos(heading)
    yOffset = 12 * math.sin(heading)
    dc.DrawLine(x, y, x + xOffset, y + yOffset);
    drawArrowhead(dc, x, y, x + xOffset, y + yOffset,  width=3.0)
    
#------------------------------------------------------------------------------------------
    
def drawProjArrow(dc, x, y, toX, toY):
    dc.SetPen(wx.Pen(wx.BLACK, 1, wx.PENSTYLE_LONG_DASH));
    dc.DrawLine(x, y, toX, toY)
    drawArrowhead(dc, x, y, toX, toY, filled = False)
    

#=====================================================================
class SlippyLayer:
    def do_draw(self, gpsmap, dc):
        pass


class DroneSymbol(SlippyLayer):
    
    def __init__(self):
        self.heading = self.lat = self.lon = 0
        self.projLat = self.projLon = self.projHeight = None
        self.path = {}
        self.corners = []

    def set_position(self, time, lat, lon):
        self.lat, self.lon = lat, lon
        
        if lat != 0 and lon != 0:
            self.path[time] = (lat, lon)
        
    def set_heading(self, heading):
        self.heading = heading

    def do_draw(self, gpsmap, dc):
        x, y = gpsmap.ll2xy(self.lat, self.lon)
        drawDroneSymbol(dc, x, y, self.heading)
        
        if self.projLat is not None and self.projLon is not None:
            projX, projY = gpsmap.ll2xy(self.projLat, self.projLon)
            drawProjArrow(dc, x, y, projX, projY)
            
        dc.SetPen(wx.Pen(wx.BLACK, 2));
        lastX = lastY = None
        for time in sorted(self.path):
            point = self.path[time]
            x, y = gpsmap.ll2xy(point[0], point[1])
            if lastX is None:
                lastX, lastY = x, y
            else:
                dc.DrawLine(lastX, lastY, x, y)
                lastX, lastY = x, y
        
    def setProjCorners(self, corners):
        self.corners = corners

        
    def set_projection_center(self, projLat, projLon, projHeight):
        self.projLat, self.projLon, self.projHeight = projLat, projLon, projHeight

#------------------------------------------------------------------------------------------

class PosMarker(SlippyLayer):
    def do_draw(self, gpsmap, dc):
        size = gpsmap.GetSize()
        lat, lon = gpsmap.xy2ll(gpsmap.mousePosition.x, gpsmap.mousePosition.y)
        
        position = "{:.6f},{:.6f}".format(lat, lon)
        w, h = dc.GetTextExtent(position)

        startX = size.GetWidth() - 10 - w
        startY = size.GetHeight() - 10 - h
        
        dc.SetTextForeground(wx.WHITE)
        dc.DrawText(position, startX, startY)
        
        dc.SetTextForeground(wx.BLACK)
        dc.DrawText(position, startX - 1, startY - 1)
    
#=====================================================================
#
# Layer to print a scale mark over the map 
#
class ScaleMarkLayer(SlippyLayer):
    def do_draw(self, gpsmap, dc):
        size = gpsmap.GetSize()
        _w, h = size.GetWidth(), size.GetHeight() 
        
        lineStart = wx.Point(10, h - 20)
        lineEnd = wx.Point(75, h - 20)
        
        #------------------------------------------------------
        # Get length of line, and decide where second mark will be
        #------------------------------------------------------
        
        startCoords = gpsmap.xy2ll(lineStart.x, lineStart.y)
        endCoords = gpsmap.xy2ll(lineEnd.x, lineEnd.y)
        
        distMeters = gpsmap.distanceMeters(startCoords, endCoords)
        
        if distMeters < 100:
            distMeters -= distMeters % 10
            text = '%d m' % distMeters
        elif distMeters < 1000:
            distMeters -= distMeters % 100
            text = '%d m' % int(distMeters)
        elif distMeters < 20000:
            distMeters -=  distMeters % 1000
            text = '%d Km' % int(distMeters / 1000)
        elif distMeters < 200000:
            distMeters -=  distMeters % 10000
            text = '%d Km' % int(distMeters / 1000)
        else:
            distMeters -=  distMeters % 100000
            text = '%d Km' % int(distMeters / 1000)
        
        markCoords = gpsmap.araz(startCoords, distMeters, -90)
        mark = wx.Point(*gpsmap.ll2xyi(*markCoords))
        
        #------------------------------------------------------
        # Draw lines...and text
        #------------------------------------------------------
                
        dc.SetBrush(wx.Brush(wx.WHITE))
        dc.DrawLine(lineStart.x, lineStart.y - 10, lineStart.x, lineStart.y + 10)
        dc.DrawLine(lineStart.x, lineStart.y, lineEnd.x, lineEnd.y)
        dc.DrawLine(mark.x, mark.y, mark.x, mark.y - 10)

        dc.SetBrush(wx.Brush(wx.BLACK))
        dc.DrawLine(lineStart.x + 1, lineStart.y - 10 + 1, lineStart.x + 1, lineStart.y + 10 + 1)
        dc.DrawLine(lineStart.x + 1, lineStart.y + 1, lineEnd.x + 1, lineEnd.y + 1)
        dc.DrawLine(mark.x + 1, mark.y + 1, mark.x + 1, mark.y - 10 + 1)
        
        startX, startY = int(mark.x + 2), int (lineEnd.y) - 1
        
        dc.SetTextForeground(wx.WHITE)
        dc.DrawText(text, startX, startY)
        
        dc.SetTextForeground(wx.BLACK)
        dc.DrawText(text, startX + 1, startY + 1)
                
    
    
#--------------------------------------------------------------------------------

class WxMapWidget(wx.Panel, Projection, Tiles):

    cachedTileBitmaps = LimitedSizeDict(size_limit = 32)

    def __init__(self, parent, lat = 32.10932741542229, lon = 34.89818882620658, zoom = 15):
        super().__init__(parent)
        Projection.__init__(self)
        Tiles.__init__(self, self.tileRetrieved)
        self.recentre(lat, lon, zoom)
        self.drag = False
        self.dragStartCoords = (0, 0)
        self.layers = []
        self.Bind(wx.EVT_SIZE, self.sizeChanged)
        self.Bind(wx.EVT_PAINT, self.updatePanel)
        self.Bind(wx.EVT_MOUSEWHEEL, self.scroll_event)
        
        self.Bind(wx.EVT_LEFT_DOWN, self.click)
        self.Bind(wx.EVT_LEFT_UP, self.release)
        self.Bind(wx.EVT_MOTION, self.mousemove)
        
        self.Bind(wx.EVT_MOUSEWHEEL, self.scroll_event)
        size = self.GetSize()
        self.mousePosition = wx.Point(size.GetWidth() // 2, size.GetHeight() // 2)
        
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        
        
    def sizeChanged(self, evt):
        size = evt.GetSize();
        self.setView(0, 0, size.GetWidth(), size.GetHeight())
        self.findEdges()

    #------------------------------------------------------------------------------------------
    
    def scroll_event(self, evt):
        rotation = evt.GetWheelRotation()
        
        if rotation > 0:
            self.implementNewZoom(self.zoom  + 1)
        elif rotation < 0:
            self.implementNewZoom(self.zoom  - 1)
            
        self.Refresh()


    #--------------------------------------------        
    def click(self, evt):
        pos = evt.GetPosition()
        self.dragStartCoords = (pos.x, pos.y)
        self.drag = True

    #--------------------------------------------        
    def release(self, _evt):
        self.drag = False

    #--------------------------------------------        
    def mousemove(self, evt):
        pos = evt.GetPosition()
        self.mousePosition = pos
        if evt.Dragging():
            self.nudge(pos.x - self.dragStartCoords[0], pos.y - self.dragStartCoords[1])
            self.dragStartCoords = (pos.x, pos.y)
            
        self.Refresh()

    #------------------------------------------------------------------------------------------
    
    def tileRetrieved(self, _filename):
        self.Refresh()

    #------------------------------------------------------------------------------------------
    
    def updatePanel(self, _evt):
        dc = wx.BufferedPaintDC(self)
        
        dc.SetBrush(wx.GREEN_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        
        for x in range(int(math.floor(self.px1)), int(math.ceil(self.px2))):
            for y in range(int(math.floor(self.py1)), int(math.ceil(self.py2))):
                tileFileName = self.getTile(x, y, self.zoom)
                
                x1,y1 = self.pxpy2xyi(x,y)
                
                if not tileFileName: 
                    dc.DrawRectangle(x1, y1, tilenames.tileSizePixels(), tilenames.tileSizePixels())
                    continue
                
                bitmap = self.cachedTileBitmaps.get(tileFileName)
                
                if not bitmap:
                    try:
                        bitmap = wx.Bitmap(tileFileName, wx.BITMAP_TYPE_ANY)
                    except Exception as e:
                        print(e)
                        dc.DrawRectangle(x1, y1, tilenames.tileSizePixels(), tilenames.tileSizePixels())
                        self.queueDownloadTile(x, y, self.zoom, True)
                        continue
                    
                if bitmap.IsOk():
                    self.cachedTileBitmaps.update({tileFileName: bitmap})
                    
                    # Convert those edges to screen coordinates
                    dc.DrawBitmap(bitmap, int(x1), int(y1), True)
                else:
                    self.cachedTileBitmaps.remove({tileFileName: bitmap})
                    dc.DrawRectangle(x1, y1, tilenames.tileSizePixels(), tilenames.tileSizePixels())

        for layer in self.layers:
            layer.do_draw(self, dc)

    #------------------------------------------------------------------------------------------
    
    def set_center_and_zoom(self, lat, lon, zoom):
        self.recentre(lat, lon, zoom)
        self.Refresh()

    def set_center(self, lat, lon):
        self.recentre(lat, lon, self.zoom)
        self.Refresh()

    def set_zoom(self, zoom):
        self.implementNewZoom(zoom)
        self.Refresh()

    #--------------------------------------------
    def layer_add(self, layer):
        if not isinstance(layer, SlippyLayer): raise Exception('Not a slippy layer')
        self.layers.append(layer)
        self.Refresh()
        
    #--------------------------------------------        
    def layer_remove(self, layer):
        if layer in self.layers: self.layers.remove(layer)
        self.Refresh()
          
    #--------------------------------------------
    def latlon_to_screen(self, lat, lon):
        '''Convert lat,lon to interger screen coordinates '''
        x, y = self.ll2xy(lat, lon)
        return int(x), int(y)
    
            
