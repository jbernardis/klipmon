import wx
import io
DATAPOINTS = 240 # 4 minutes


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
	def __init__(self, parent, pname, settings):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(255, 255, 255))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  Thermals  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		self.ftb = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		self.ft = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.moonraker = None

		self.sensors = []
		self.sensorMap = {}
		self.heaters = []
		self.heaterMap = {}

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(20)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		self.thermList = ThermList(self)
		hsz.Add(self.thermList)
		hsz.AddSpacer(20)
		vsz.Add(hsz)

		vsz.AddSpacer(20)

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

		self.thermList.LoadData(self.sensors, self.heaters)

	def UpdateStatus(self, jmsg):
		for s in self.sensors:
			n = s.GetName()
			if n in jmsg:
				s.UpdateCurrentValues(jmsg[n])

		for h in self.heaters:
			n = h.GetName()
			if n in jmsg:
				h.UpdateCurrentValues(jmsg[n])

	def Ticker(self):
		for s in self.sensors:
			n = s.GetName()
			temps = s.Record()

		for h in self.heaters:
			n = h.GetName()
			temps, targets, powers = h.Record()

		self.thermList.Ticker()


class ThermList (wx.ListCtrl):
	def __init__(self, parent):
		wx.ListCtrl.__init__(self, parent, wx.ID_ANY, size=(470, 200),
				style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES | wx.LC_SINGLE_SEL)
		self.SetFont(wx.Font(wx.Font(12, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")))
		self.moonraker = None
		self.parent = parent
		self.sensors = []
		self.heaters = []
		self.fnList = []
		self.nItems = 0

		self.InsertColumn(0, "name")
		self.SetColumnWidth(0, 230)
		self.InsertColumn(1, "power")
		self.SetColumnWidth(1, 80)
		self.InsertColumn(2, "actual")
		self.SetColumnWidth(2, 80)
		self.InsertColumn(3, "target")
		self.SetColumnWidth(3, 80)

		self.SetItemCount(0)

		self.attr1 = wx.ItemAttr()
		self.attr1.SetBackgroundColour(wx.Colour(156, 252, 126))

		self.attr2 = wx.ItemAttr()
		self.attr2.SetBackgroundColour(wx.Colour(255, 255, 255))

		# self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
		# self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
		# self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)
		# self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemRughtClicked)

	def LoadData(self, sensors, heaters):
		self.sensors = sensors
		self.heaters = heaters

		self.nItems = len(self.sensors) + len(self.heaters)
		self.SetItemCount(self.nItems)

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
