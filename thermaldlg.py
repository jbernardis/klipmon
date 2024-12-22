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

		self.presets = self.psettings["presets"]
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
		bedCmd  = "M140S0"
		extrCmd = "M104S0"
		try:
			self.moonraker.SendGCode(bedCmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

		try:
			self.moonraker.SendGCode(extrCmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

		self.Destroy()

	def onPreset(self, evt):
		b = evt.GetEventObject()
		ps = b.GetLabel()
		try:
			temps = self.presets[ps]
		except KeyError:
			print("unknown preset")
			return

		bedCmd  = "M140S%d" % temps[0]
		extrCmd = "M104S%d" % temps[1]
		try:
			self.moonraker.SendGCode(bedCmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

		try:
			self.moonraker.SendGCode(extrCmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

		self.Destroy()

	def onClose(self, evt):
		self.Destroy()
