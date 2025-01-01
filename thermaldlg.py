import wx

from moonraker import MoonrakerException

BTNSZ = (120, 50)


class ThermalDlg(wx.Dialog):
	def __init__(self, parent, pname, settings, moonraker):
		wx.Dialog.__init__(self, parent, wx.ID_ANY, "Thermals")
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.moonraker = moonraker

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		vsz = wx.BoxSizer(wx.VERTICAL)

		self.bAllOff = wx.Button(self, wx.ID_ANY, "All Off", size=BTNSZ)
		self.Bind(wx.EVT_BUTTON, self.onBAllOff, self.bAllOff)
		vsz.AddSpacer(20)
		vsz.Add(self.bAllOff)

		self.presets = {}
		for hn, htr in self.psettings["heaters"].items():
			presets = htr["presets"]
			gcode = htr["gcode"]
			for fil, temp in presets.items():
				try:
					self.presets[fil].append([temp, gcode])
				except KeyError:
					self.presets[fil] = [[temp, gcode]]

		for ps in sorted(list(self.presets.keys())):
			b = wx.Button(self, wx.ID_ANY, ps, size=BTNSZ)
			self.Bind(wx.EVT_BUTTON, self.onPreset, b)
			vsz.AddSpacer(20)
			vsz.Add(b)

		vsz.AddSpacer(20)

		hsz.AddSpacer(20)
		hsz.Add(vsz)
		hsz.AddSpacer(20)

		self.SetSizer(hsz)
		self.Layout()
		self.Fit()

	def onBAllOff(self, evt):
		psk = list(self.presets.keys())[0]
		preset = self.presets[psk]

		for _, gcode in preset:
			cmd = gcode + "S0"
			try:
				self.moonraker.SendGCode(cmd)
			except MoonrakerException as e:
				dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()

		self.Destroy()

	def onPreset(self, evt):
		b = evt.GetEventObject()
		ps = b.GetLabel()
		try:
			preset = self.presets[ps]
		except KeyError:
			print("unknown preset")
			return

		for temp, gcode in preset:
			cmd = gcode + "S" + ("%d" % temp)
			try:
				self.moonraker.SendGCode(cmd)
			except MoonrakerException as e:
				dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()

		self.Destroy()

	def onClose(self, evt):
		self.Destroy()
