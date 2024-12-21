import numpy
import matplotlib
import pylab

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

import wx
from thermframe import DATAPOINTS


class TempGraph(wx.Panel):
    def __init__(self, parent, pname, settings):
        wx.Panel.__init__(self, parent, size=(600, 400))
        self.parent = parent
        self.pname = pname
        self.settings = settings
        self.psettings = self.settings.GetPrinterSettings(self.pname)
        self.sensors = None
        self.heaters = None
        self.heater_actual = {}
        self.heater_target = {}
        self.sensor_actual = {}
        self.plotColors = {}

        self.dpi = 100
        self.figure = Figure((6.0, 4.0), dpi=self.dpi)
        self.axes = self.figure.add_subplot(111)

        self.canvas = FigureCanvas(self, wx.ID_ANY, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas) #, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Layout()
        self.Fit()
        self.xrange = numpy.arange(-239, 1, 1)

    def initPlot(self, sensors, heaters):
        self.sensors = sensors
        self.heaters = heaters
        print(str(heaters))
        print(str(list(heaters.keys())))
        self.plotColors = {}
        for sn in self.sensors:
            self.plotColors[sn] = self.psettings["sensors"][sn]["tempcolor"]
        for hn in self.heaters:
            self.plotColors[hn] = self.psettings["heaters"][hn]["tempcolor"]

        self.axes.set_xbound(-239, 0)
        self.axes.set_xlim(-239, 0)
        self.axes.set_ybound(0, 250)
        self.axes.set_ylim(0, 250)
        self.axes.set_xticks(range(-239, 1, 30))
        xticklabels = []
        for i in range(-240, 0, 60):
            xticklabels.append("%d:00" % int(i / 60))
            xticklabels.append("")
        self.axes.set_xticklabels(xticklabels)
        self.axes.set_facecolor((4.0/255.0, 4.0/255.0, 4.0/255.0, 0.9))

        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        legends = []
        for hn, htr in self.heaters.items():
            self.heater_actual[hn] = self.axes.plot(
                [0] * DATAPOINTS,
                linewidth=2,
                color=[x / 255.0 for x in self.plotColors[hn]]
            )[0]
            legends.append(hn)
            self.heater_target[hn] = self.axes.plot(
                [0] * DATAPOINTS,
                linewidth=2,
                linestyle="-.",
                color=[x / 255.0 for x in self.plotColors[hn]]
            )[0]
            legends.append("")

        for sn, ssr in self.sensors.items():
            self.sensor_actual[sn] = self.axes.plot(
                [0] * DATAPOINTS,
                linewidth=2,
                color=[x / 255.0 for x in self.plotColors[sn]]
            )[0]
            if sn.startswith("temperature_sensor "):
                name = sn[19:]
            else:
                name = sn
            legends.append(name)

        l = self.axes.legend(legends, loc=2)
        f = l.get_frame()
        f.set_facecolor((128.0/255.0, 128.0/255.0, 128.0/255.0, 0.1))

    def draw(self):
        self.axes.grid(True, color='gray')
        for hn, htr in self.heaters.items():
            self.heater_actual[hn].set_xdata(self.xrange)
            self.heater_actual[hn].set_ydata(numpy.array(htr.GetTemps()))
            self.heater_target[hn].set_xdata(self.xrange)
            self.heater_target[hn].set_ydata(numpy.array(htr.GetTargets()))

        for sn, ssr in self.sensors.items():
            self.sensor_actual[sn].set_xdata(self.xrange)
            self.sensor_actual[sn].set_ydata(numpy.array(ssr.GetTemps()))

        self.canvas.draw()
