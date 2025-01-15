import wx

from thermaldlg import ThermalDlg
from heater import HeaterDlg
from moonraker import MoonrakerException

DATAPOINTS = 240 # 4 minutes
BTNSZ = (100, 30)


def CollapseList(l, n):
	if len(l) > n:
		return l[-DATAPOINTS:]

	elif len(l) == 0:
		return [0] * DATAPOINTS

	else:
		# list is smaller than desired data points - replicate the first element to fill it out
		nv = l[0]
		toAdd = DATAPOINTS - len(l)
		return [nv] * toAdd + l


class Sensor:
	def __init__(self, name):
		self.name = name
		self.temps = [0] * DATAPOINTS
		self.currentTemp = 0

	def GetName(self):
		return self.name

	def GetCurrentTemp(self):
		return self.currentTemp

	def CachedValues(self, temps):
		self.temps = CollapseList(temps, DATAPOINTS)
		self.currentTemp = self.temps[-1]

	def GetTemps(self):
		return self.temps

	def UpdateCurrentValues(self, msg):
		try:
			self.currentTemp = msg["temperature"]
		except KeyError:
			pass

	def Record(self):
		self.temps = self.temps[1:] + [self.currentTemp]
		return self.temps


class Heater:
	def __init__(self, name):
		self.name = name
		self.temps = [0] * DATAPOINTS
		self.targets = [0] * DATAPOINTS
		self.powers = [0] * DATAPOINTS
		self.currentTemp = 0
		self.currentTarget = 0
		self.currentPower = 0

	def GetName(self):
		return self.name

	def GetCurrentTemp(self):
		return self.currentTemp

	def GetCurrentTarget(self):
		return self.currentTarget

	def GetCurrentPower(self):
		return self.currentPower

	def CachedValues(self, temps, targets, powers):
		self.temps = CollapseList(temps, DATAPOINTS)
		self.targets = CollapseList(targets, DATAPOINTS)
		self.powers = CollapseList(powers, DATAPOINTS)
		self.currentTemp = self.temps[-1]
		self.currentTarget = self.targets[-1]
		self.currentPower = self.powers[-1]

	def GetTemps(self):
		return self.temps

	def GetTargets(self):
		return self.targets

	def GetPowers(self):
		return self.powers

	def UpdateCurrentValues(self, msg):
		try:
			self.currentTemp = msg["temperature"]
		except KeyError:
			pass
		try:
			self.currentTarget = msg["target"]
		except KeyError:
			pass
		try:
			self.currentPower = msg["power"]
		except KeyError:
			pass

	def Record(self):
		self.temps = self.temps[1:] + [self.currentTemp]
		self.targets = self.targets[1:] + [self.currentTarget]
		self.powers = self.powers[1:] + [self.currentPower]
		return self.temps, self.targets, self.powers


class ThermalFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings, heaters, sensors):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  Thermals  "
		self.SetLabel(self.titleText)
		self.topBorder, otherBorder = self.GetBordersForSizer()

		if wx.DisplaySize()[1] == 1440:
			ptsz = 12
			self.vspacing = 20
			self.hspacing = 20
		else:
			ptsz = 9
			self.vspacing = 10
			self.hspacing = 10

		self.ftb = wx.Font(ptsz, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		self.ft = wx.Font(ptsz, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.images = parent.images
		self.psettings = self.settings.GetPrinterSettings((pname))
		self.moonraker = None

		self.sensors = []
		self.sensorMap = {}
		self.heaters = []
		self.heaterMap = {}

		self.SetSensors(sensors)
		self.SetHeaters(heaters)

		self.thermList = ThermList(self, self.heaters, self.sensors)
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnThermalDClick, self.thermList)

		self.bThermals = wx.Button(self, wx.ID_ANY, "Presets", size=BTNSZ)
		self.bThermals.SetBackgroundColour(wx.Colour(196, 196, 196))
		self.Bind(wx.EVT_BUTTON, self.onBThermals, self.bThermals)

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(self.topBorder)
		vsz.AddSpacer(self.vspacing)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(self.hspacing)
		hsz.Add(self.thermList, 0, wx.EXPAND)
		hsz.AddSpacer(self.hspacing)
		vsz.Add(hsz)

		vsz.AddSpacer(self.vspacing)

		vsz.Add(self.bThermals, 0, wx.ALIGN_CENTER_HORIZONTAL)
		vsz.AddSpacer(self.vspacing)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def SetMoonraker(self, mr):
		self.moonraker = mr

	def SetSensors(self, sl):
		self.sensors = [Sensor(x) for x in sl]
		self.sensorMap = {s.GetName(): s for s in self.sensors}

	def GetSensorMap(self):
		return self.sensorMap

	def SetHeaters(self, hl):
		self.heaters = [Heater(x) for x in hl]
		self.heaterMap = {h.GetName(): h for h in self.heaters}

	def GetHeaterMap(self):
		return self.heaterMap

	def SetInitialValues(self, ivals):
		for s in self.sensors:
			n = s.GetName()
			if n in ivals["result"]:
				s.CachedValues(ivals["result"][n]["temperatures"])
			else:
				print("sensor %s not found in cached temperatures" % n)

		for h in self.heaters:
			n = h.GetName()
			if n in ivals["result"]:
				h.CachedValues(ivals["result"][n]["temperatures"], ivals["result"][n]["targets"], ivals["result"][n]["powers"])
			else:
				print("heater %s not found in cached temperatures" % n)

	def UpdateStatus(self, jmsg):
		for s in self.sensors:
			n = s.GetName()
			if n in jmsg:
				s.UpdateCurrentValues(jmsg[n])

		for h in self.heaters:
			n = h.GetName()
			if n in jmsg:
				h.UpdateCurrentValues(jmsg[n])

	def OnThermalDClick(self, evt):
		ci = evt.Index
		if ci == wx.NOT_FOUND:
			return
		hn = self.thermList.GetItemText(ci)
		try:
			htr = self.heaterMap[hn]
		except KeyError:
			dlg = wx.MessageDialog(self, "Not a controllable heater", "Invalid heater", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		dlg = HeaterDlg(self, self.pname, hn, self.settings, self.images)
		rc = dlg.ShowModal()
		if rc != wx.ID_OK:
			dlg.Destroy()
			return

		cmd = dlg.GetResults()
		dlg.Destroy()

		try:
			self.moonraker.SendGCode(cmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

	def onBThermals(self, evt):
		dlg = ThermalDlg(self, self.pname, self.settings, self.moonraker)
		dlg.Show()

	def Ticker(self):
		for s in self.sensors:
			n = s.GetName()
			temps = s.Record()

		for h in self.heaters:
			n = h.GetName()
			temps, targets, powers = h.Record()

		self.thermList.Ticker()


class ThermList (wx.ListCtrl):
	def __init__(self, parent, heaters, sensors):
		self.nItems = len(heaters) + len(sensors)

		if wx.DisplaySize()[1] == 1440:
			self.ptsz = 12
		else:
			self.ptsz = 9

		sz = (470, int(self.nItems * (self.ptsz*2.5) + (self.ptsz*2.5)))
		wx.ListCtrl.__init__(self, parent, wx.ID_ANY, size=sz,
				style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES | wx.LC_SINGLE_SEL)
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))

		self.SetFont(wx.Font(self.ptsz, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial"))
		self.moonraker = None
		self.parent = parent
		self.sensors = sensors
		self.heaters = heaters
		self.fnList = []

		self.InsertColumn(0, "name")
		self.SetColumnWidth(0, 230)
		self.InsertColumn(1, "power")
		self.SetColumnWidth(1, 80)
		self.InsertColumn(2, "actual")
		self.SetColumnWidth(2, 80)
		self.InsertColumn(3, "target")
		self.SetColumnWidth(3, 80)

		self.SetItemCount(self.nItems)

		self.attr1 = wx.ItemAttr()
		self.attr1.SetBackgroundColour(wx.Colour(8, 149, 235))

		self.attr2 = wx.ItemAttr()
		self.attr2.SetBackgroundColour(wx.Colour(196, 196, 196))

	def Ticker(self):
		self.RefreshItems(0, self.nItems-1)

	def OnGetItemText(self, item, col):
		if item < len(self.sensors):
			if col == 0:
				s = self.sensors[item].GetName()
				if s.startswith("temperature_sensor "):
					return s[19:]
				return s
			elif col == 1 or col == 3:
				return ""
			else: # col = 2
				return "%9.2f" % self.sensors[item].GetCurrentTemp()
		else:
			ix = item - len(self.sensors)
			if col == 0:
				return self.heaters[ix].GetName()
			elif col == 1:
				p = self.heaters[ix].GetCurrentPower()
				if p < 0.001:
					return ""
				else:
					return "%9.2f" % p
			elif col == 2:
				return "%9.2f" % self.heaters[ix].GetCurrentTemp()
			elif col == 3:
				return "%9.2f" % self.heaters[ix].GetCurrentTarget()

	def OnGetItemAttr(self, item):
		if item % 2 == 1:
			return self.attr1
		else:
			return self.attr2
