#wxmapwidget

This is a slippy map widget for Python wxWidgets. It uses projection and tile-name calculations 
by Oliver White. 

## Usage
Just use the WxMapWidget like any other widget. You should set the center point.


```python

from wxmapwidget import WxMapWidget, PosMarker, ScaleMarkLayer

....    
    
self.mapPanel = WxMapWidget(splitterLeft)
self.mapPanel.layer_add(PosMarker())
self.mapPanel.layer_add(ScaleMarkLayer())


self.mapPanel.set_center(lat, lon)
    
```


You can make overlay layers by subclassing SlippyLayer. You need to implement a do_draw function as shown in the 
example:


'''python
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

'''