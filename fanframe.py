import wx

from moonraker import MoonrakerException


class Fan:
	def __init__(self, name, fsettings):
		self.name = name
		try:
			self.controllable = fsettings["controllable"]
		except KeyError:
			self.controllable = False

		try:
			self.pwm = fsettings["pwm"]
		except KeyError:
			self.pwm = False

		if self.name.startswith("controller_fan"):
			self.simplifiedName = self.name[15:]

		elif self.name.startswith("heater_fan"):
			self.simplifiedName = self.name[11:]

		elif self.name.startswith("output_pin"):
			self.simplifiedName = self.name[11:]

		else:
			self.simplifiedName = name

		self.speed = 0
		self.slider = None
		self.moonraker = None

	def SetMoonraker(self, mr):
		self.moonraker = mr

	def SetSpeed(self, s):
		self.speed = s
		ispeed = int(self.speed * 100.0)
		if self.slider is not None:
			self.slider.SetValue(ispeed)

	def SetSlider(self, sl):
		self.slider = sl
		self.slider.Enable(self.controllable)
		self.slider.SetClientData(self)

	def SimplifiedName(self):
		return self.simplifiedName

	def SendNewValue(self, v):
		if self.moonraker is None:
			dlg = wx.MessageDialog(self, "Moonraker connectiuon has not been established", "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		if self.pwm:
			fspeed = int(255.0 * float(v) / 100.0)
			cmd = "M106P\"%s\"S%d" % (self.simplifiedName, fspeed)
		else:
			cmd = "SET_PIN PIN=%s VALUE=%d" % (self.simplifiedName, v)
		try:
			self.moonraker.SendGCode(cmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()


class MySlider(wx.Slider):
	def __init__(self, parent, limit):
		wx.Slider.__init__(self, parent, wx.ID_ANY, 0, 0, limit, size=(200, 50), style=wx.SL_HORIZONTAL | wx.SL_LABELS)
		self.clientData = None

	def SetClientData(self, data):
		self.clientData = data

	def GetClientData(self):
		return self.clientData


class FanFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings, fans):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  Fans  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		self.ftb = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		self.ft = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(pname)
		self.moonraker = None
		self.fanMap = {}
		self.fanNames = [f for f in fans]
		for f in self.fanNames:
			try:
				s = self.psettings["fans"][f]
			except KeyError:
				try:
					s = self.psettings["outputs"][f]
				except KeyError:
					s = None

			if s is not None:
				self.fanMap[f] = Fan(f, s)
			else:
				print("definition missing for fan/output %s" % f)

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(20)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		col = 0
		for fn, f in self.fanMap.items():
			hsz.AddSpacer(10)
			st = wx.StaticText(self, wx.ID_ANY, f.SimplifiedName(), size=(110, -1), style=wx.ALIGN_RIGHT)
			st.SetFont(self.ftb)
			hsz.Add(st)
			hsz.AddSpacer(20)
			sl = MySlider(self, 100 if f.pwm else 1)
			self.Bind(wx.EVT_SCROLL_CHANGED, self.onScrollChanged, sl)
			sl.SetFont(self.ftb)
			f.SetSlider(sl)
			hsz.Add(sl)
			col = 1 - col
			if col == 0:
				hsz.AddSpacer(20)
				vsz.Add(hsz)
				hsz = wx.BoxSizer(wx.HORIZONTAL)

		if col == 1:
			vsz.Add(hsz)

		hsz.AddSpacer(20)
		vsz.Add(hsz)

		vsz.AddSpacer(20)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	@staticmethod
	def onScrollChanged(evt):
		b = evt.GetEventObject()
		f = b.GetClientData()
		v = b.GetValue()
		f.SendNewValue(v)

	def SetMoonraker(self, mr):
		self.moonraker = mr
		for f in self.fanMap.values():
			f.SetMoonraker(mr)

	def SetInitialValues(self, ivals):
		for fn, f in self.fanMap.items():
			try:
				f.SetSpeed(ivals[fn]["speed"])
			except KeyError:
				pass

	def UpdateStatus(self, jmsg):
		for fn, f in self.fanMap.items():
			try:
				f.SetSpeed(jmsg[fn]["speed"])
			except KeyError:
				pass

