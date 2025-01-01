"""
Created on May 11, 2018

@author: Jeff
"""

import wx
import os


class HeaterDlg(wx.Dialog):
	def __init__(self, parent, pname, hname, settings, images):
		wx.Dialog.__init__(self, parent, wx.ID_ANY, "Heater control")
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.parent = parent
		self.images = images
		self.settings = settings
		self.hname = hname
		self.pname = pname

		self.cmd = None

		self.heaterOn = False
		self.lastSetValue = -1

		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.gcode = self.psettings["heaters"][hname]["gcode"]
		self.presets = self.psettings["heaters"][hname]["presets"]

		lbFont = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		lFont = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

		self.SetBackgroundColour("white")

		szHeater = wx.BoxSizer(wx.HORIZONTAL)
		szHeater.AddSpacer(10)

		l = wx.StaticText(self, wx.ID_ANY, self.hname, size=(100, -1))
		l.SetFont(lbFont)
		szHeater.Add(l, 0, wx.TOP, 13 if os.name == 'posix' else 5)
		szHeater.AddSpacer(5)

		self.sc = wx.SpinCtrl(self, wx.ID_ANY, "", size=(120 if os.name == 'posix' else 70, -1), style=wx.ALIGN_RIGHT)
		self.sc.SetFont(lbFont)
		self.sc.SetRange(0, 250)
		self.sc.SetValue(0)

		szHeater.Add(self.sc, 0, wx.TOP, 8 if os.name == 'posix' else 0)

		self.bPower = wx.BitmapButton(self, wx.ID_ANY, self.images.pngHeaton,
									  size=(48, 48) if os.name == 'posix' else (32, 32), style=wx.NO_BORDER)
		self.bPower.SetToolTip("Turn heater on/off")
		self.bPower.SetBackgroundColour("white")
		self.Bind(wx.EVT_BUTTON, self.onBPower, self.bPower)

		szHeater.AddSpacer(5)
		szHeater.Add(self.bPower)

		self.ch = sorted([x for x in sorted(self.presets.values())])
		if self.ch[0] != 0:
			self.ch = [0] + self.ch
		self.chPresets = wx.Choice(self, wx.ID_ANY, choices=["%d" % x for x in self.ch])
		self.chPresets.SetFont(lFont)
		self.chPresets.SetSelection(0)
		self.Bind(wx.EVT_CHOICE, self.onPreset, self.chPresets)

		szHeater.AddSpacer(5)
		szHeater.Add(self.chPresets, 0, wx.TOP, 8 if os.name == 'posix' else 0)

		szHeater.AddSpacer(10)
		self.SetSizer(szHeater)
		self.Layout()
		self.Fit()

	def onPreset(self, evt):
		s = evt.GetSelection()
		if s == wx.NOT_FOUND:
			return

		t = self.ch[s]
		self.sc.SetValue(t)
		self.setHeater(t)

	def onBPower(self, _):
		nv = self.sc.GetValue()
		self.setHeater(nv)
		self.EndModal(wx.ID_OK)

	def setHeater(self, nv):
		self.cmd = "%s S%d" % (self.gcode, nv)
		self.sc.SetValue(nv)
		self.lastSetValue = nv

	def GetResults(self):
		return self.cmd

	def onClose(self, evt):
		self.EndModal(wx.ID_CANCEL)
