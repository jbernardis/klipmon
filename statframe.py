import wx


def MakeEmpty():
	empty = wx.Bitmap(200, 200, 32)
	dc = wx.MemoryDC(empty)
	dc.SetBackground(wx.Brush((0, 0, 0, 0)))
	dc.Clear()
	del dc
	empty.SetMaskColour((0, 0, 0))
	return empty


def formatTime(ss):
	s = int(ss)
	hrs = int(s / 3600)
	mins = int((s % 3600) / 60)
	secs = int(s % 60)

	if hrs > 0:
		result = "%dh %dm %ds" % (hrs, mins, secs)
	else:
		result = "%dm %ds" % (mins, secs)

	return result


class StatFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings):
		# TODO pause/resume cancel buttons
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(255, 255, 255))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  Printer Status  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		self.active = None
		self.state = None
		self.activeFn = None
		self.toolPosition = None
		self.homedAxes = None
		self.activeFn = None
		self.activeMeta = None
		self.totalduration = 0
		self.printduration = 0
		self.totallayers = None
		self.currentlayer = None
		self.jobStatus = False
		self.fpos = 0
		self.progress = 0.0
		self.filamentused = 0

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.moonraker = None

		self.emptyBmp = MakeEmpty()

		ftb = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		ft  = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(20)

		fnhz = wx.BoxSizer(wx.VERTICAL)
		self.stState = wx.StaticText(self, wx.ID_ANY, "", size=(200, -1))
		self.stState.SetFont(ftb)
		fnhz.Add(self.stState)
		fnhz.AddSpacer(20)

		self.stFileName = wx.StaticText(self, wx.ID_ANY, "", size=(200, -1))
		self.stFileName.SetFont(ftb)
		fnhz.Add(self.stFileName, 0, wx.ALIGN_CENTER_HORIZONTAL)
		fnhz.AddSpacer(10)

		self.bmp = wx.StaticBitmap(self, wx.ID_ANY, size=(200, 200))
		fnhz.Add(self.bmp, 0, wx.ALIGN_CENTER_HORIZONTAL)

		possz = wx.BoxSizer(wx.HORIZONTAL)
		possz.AddSpacer(20)

		self.stLabelX = wx.StaticText(self, wx.ID_ANY, "X:")
		self.stLabelX.SetFont(ftb)
		possz.Add(self.stLabelX)

		self.stPosX = wx.StaticText(self, wx.ID_ANY, "", size=(60, -1))
		self.stPosX.SetFont(ftb)
		possz.Add(self.stPosX)

		self.stLabelY = wx.StaticText(self, wx.ID_ANY, "Y:")
		self.stLabelY.SetFont(ftb)
		possz.Add(self.stLabelY)
		possz.AddSpacer(5)

		self.stPosY = wx.StaticText(self, wx.ID_ANY, "", size=(60, -1))
		self.stPosY.SetFont(ftb)
		possz.Add(self.stPosY)
		possz.AddSpacer(5)

		self.stLabelZ = wx.StaticText(self, wx.ID_ANY, "Z:")
		self.stLabelZ.SetFont(ftb)
		possz.Add(self.stLabelZ)

		self.stPosZ = wx.StaticText(self, wx.ID_ANY, "", size=(60, -1))
		self.stPosZ.SetFont(ftb)
		possz.Add(self.stPosZ)

		possz.AddSpacer(20)

		metasz = wx.BoxSizer(wx.VERTICAL)
		metasz.Add(possz)

		metasz.AddSpacer(30)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Total Duration: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stTDur = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stTDur.SetFont(ft)
		lnsz.Add(self.stTDur)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Print Duration: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stPDur = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stPDur.SetFont(ft)
		lnsz.Add(self.stPDur)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Estimate: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stEDur = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stEDur.SetFont(ft)
		lnsz.Add(self.stEDur)
		metasz.Add(lnsz)

		metasz.AddSpacer(15)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Total Height: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stTHt = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stTHt.SetFont(ft)
		lnsz.Add(self.stTHt)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Layer Height: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stLHt = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stLHt.SetFont(ft)
		lnsz.Add(self.stLHt)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Layer: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stLayer = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stLayer.SetFont(ft)
		lnsz.Add(self.stLayer)
		metasz.Add(lnsz)

		metasz.AddSpacer(15)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Total Filament: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stTFil = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stTFil.SetFont(ft)
		lnsz.Add(self.stTFil)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Filament Used: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stUFil = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stUFil.SetFont(ft)
		lnsz.Add(self.stUFil)
		metasz.Add(lnsz)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		hsz.Add(fnhz)
		hsz.AddSpacer(10)
		hsz.Add(metasz)

		vsz.Add(hsz)

		vsz.AddSpacer(20)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def Ticker(self):
		self.stTDur.SetLabel(formatTime(self.totalduration))
		self.stPDur.SetLabel(formatTime(self.printduration))
		self.stUFil.SetLabel("%9.2f" % self.filamentused)

		if self.totallayers is None and self.currentlayer is None:
			self.stLayer.SetLabel("")
		elif self.currentlayer is not None:
			self.stLayer.SetLabel("%d" % int(self.currentlayer))
		else:
			self.stLayer.SetLabel("%d/%d" % (int(self.currentlayer), int(self.totallayers)))

	def UpdateToolPosition(self):
		if self.toolPosition is None:
			self.stPosX.SetLabel("")
			self.stPosY.SetLabel("")
			self.stPosZ.SetLabel("")
		else:
			self.stPosX.SetLabel("%7.2f" % self.toolPosition[0])
			self.stPosY.SetLabel("%7.2f" % self.toolPosition[1])
			self.stPosZ.SetLabel("%7.2f" % self.toolPosition[2])

	def UpdateHomedAxes(self):
		axes = self.homedAxes.lower()
		xc = wx.Colour(0, 0, 0) if "x" in axes else wx.Colour(255, 0, 0)
		yc = wx.Colour(0, 0, 0) if "y" in axes else wx.Colour(255, 0, 0)
		zc = wx.Colour(0, 0, 0) if "z" in axes else wx.Colour(255, 0, 0)

		self.stLabelX.SetForegroundColour(xc)
		self.stLabelY.SetForegroundColour(yc)
		self.stLabelZ.SetForegroundColour(zc)

		self.stLabelX.Refresh()
		self.stLabelY.Refresh()
		self.stLabelZ.Refresh()

	def UpdateFileName(self):
		if self.activeFn is None:
			self.stFileName.SetLabel("")
		else:
			self.stFileName.SetLabel(self.activeFn)

		if self.activeMeta is None:
			self.bmp.SetBitmap(self.emptyBmp)
		else:
			self.bmp.SetBitmap(self.activeMeta["thumbnail"])

		if self.activeMeta is None:
			self.stEDur.SetLabel("")
			self.stTHt.SetLabel("")
			self.stLHt.SetLabel("")
			self.stTFil.SetLabel("")
		else:
			try:
				s = self.activeMeta["printtime"]
				self.stEDur.SetLabel(formatTime(s))
			except KeyError:
				self.stEDur.SetLabel("")

			try:
				s = self.activeMeta["height"]
				self.stTHt.SetLabel("%7.2f" % s)
			except KeyError:
				self.stTHt.SetLabel("")

			try:
				s = self.activeMeta["layerheight"]
				self.stLHt.SetLabel("%7.2f" % s)
			except KeyError:
				self.stLHt.SetLabel("")

			try:
				s = self.activeMeta["filamenttotal"]
				self.stTFil.SetLabel("%9.2f" % s)
			except KeyError:
				self.stTFil.SetLabel("")

	def UpdateState(self):
		if self.state is None:
			self.stState.SetLabel("")
		else:
			self.stState.SetLabel("State: %s" % self.state)

	def SetMoonraker(self, mr):
		self.moonraker = mr
		self.RefreshFilesList()

	def SetInitialValues(self, ivals):
		if "toolhead" in ivals:
			try:
				tp = ivals["toolhead"]["position"]
			except KeyError:
				tp = None

			if tp != self.toolPosition:
				self.toolPosition = tp
				self.UpdateToolPosition()

			try:
				ha = ivals["toolhead"]["homed_axes"]
			except KeyError:
				ha = ""

			if ha != self.homedAxes:
				self.homedAxes = ha
				self.UpdateHomedAxes()

		if "print_stats" in ivals:
			self.ParsePrintStats(ivals["print_stats"])

	def ParsePrintStats(self, pstats):
		try:
			fn = pstats["filename"]
		except KeyError:
			fn = None
		if fn is not None and fn != self.activeFn:
			self.activeFn = fn
			self.activeMeta = self.parent.GetMeta(fn)
			self.UpdateFileName()

		try:
			st = pstats["state"]
		except KeyError:
			st = None

		if st is not None and st != self.state:
			self.state = st
			self.UpdateState()

		try:
			self.printduration = pstats["print_duration"]
		except KeyError:
			pass

		try:
			self.filamentused = pstats["filament_used"]
		except KeyError:
			pass

		try:
			self.totalduration = pstats["total_duration"]
		except KeyError:
			pass

		try:
			self.totallayers = pstats["info"]["total_layer"]
		except KeyError:
			pass

		try:
			self.currentlayer = pstats["info"]["current_layer"]
		except KeyError:
			pass

	def setJobStatus(self, active, fn, pos, prog):
		self.jobStatus = active
		self.fpos = pos
		# TODO - display this progress as a circular chart
		self.progress = prog

	def UpdateStatus(self, jmsg):
		if "toolhead" in jmsg:
			try:
				pos = jmsg["toolhead"]["position"]
			except KeyError:
				pos = None

			if pos is not None:
				self.toolPosition = pos
				self.UpdateToolPosition()

			try:
				axes = jmsg["toolhead"]["homed_axes"]
			except KeyError:
				axes = None

			if axes is not None:
				if axes != self.homedAxes:
					self.homedAxes = axes
					self.UpdateHomedAxes()

		if "print_stats" in jmsg:
			self.ParsePrintStats(jmsg["print_stats"])

	def RefreshFilesList(self):
		pass
