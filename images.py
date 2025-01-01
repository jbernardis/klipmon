import wx
import os


class Images:
    def __init__(self):
        self.nameMap = {}
        try:
            pdir = os.path.join(os.getcwd(), "images")
            l = os.listdir(pdir)
        except:
            print ("Unable to get listing from images directory")
            return

        for f in l:
            if not os.path.isdir(f) and f.lower().endswith(".png"):
                b = os.path.splitext(os.path.basename(f))[0]

                fp = os.path.join(pdir, f)
                png = wx.Image(fp, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
                mask = wx.Mask(png, wx.BLUE)
                png.SetMask(mask)

                setattr(self, 'png' + b.capitalize(), png)
                self.nameMap[b] = png

    def getByName(self, name):
        if name in self.nameMap.keys():
            return self.nameMap[name]
        else:
            return None
