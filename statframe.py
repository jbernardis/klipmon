import wx
import time
import json

BTNSZ = (100, 30)


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
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  Printer Status  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		self.active = None
		self.state = None
		self.cancelling = False
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
		self.jogDlg = None
		self.GCHomeOrigin = None
		self.GCPosition = None
		self.GCGPosition = None
		self.zoffset = 0.0
		self.estimated = None
		self.printtime = None
		self.rbx = None

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(pname)
		self.moonraker = None

		self.emptyBmp = MakeEmpty()

		self.ftb = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		self.ft  = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(20)

		fnhz = wx.BoxSizer(wx.VERTICAL)
		self.stState = wx.StaticText(self, wx.ID_ANY, "", size=(200, -1))
		self.stState.SetFont(self.ftb)
		fnhz.Add(self.stState)
		fnhz.AddSpacer(20)

		self.stFileName = wx.StaticText(self, wx.ID_ANY, "", size=(200, -1))
		self.stFileName.SetFont(self.ftb)
		fnhz.Add(self.stFileName, 0, wx.ALIGN_CENTER_HORIZONTAL)
		fnhz.AddSpacer(10)

		self.bmp = wx.StaticBitmap(self, wx.ID_ANY, size=(200, 200))
		fnhz.Add(self.bmp, 0, wx.ALIGN_CENTER_HORIZONTAL)

		possz = wx.BoxSizer(wx.HORIZONTAL)
		possz.AddSpacer(20)

		self.stLabelX = wx.StaticText(self, wx.ID_ANY, "X:")
		self.stLabelX.SetFont(self.ftb)
		possz.Add(self.stLabelX)

		self.stPosX = wx.StaticText(self, wx.ID_ANY, "", size=(60, -1))
		self.stPosX.SetFont(self.ftb)
		possz.Add(self.stPosX)

		self.stLabelY = wx.StaticText(self, wx.ID_ANY, "Y:")
		self.stLabelY.SetFont(self.ftb)
		possz.Add(self.stLabelY)
		possz.AddSpacer(5)

		self.stPosY = wx.StaticText(self, wx.ID_ANY, "", size=(60, -1))
		self.stPosY.SetFont(self.ftb)
		possz.Add(self.stPosY)
		possz.AddSpacer(5)

		self.stLabelZ = wx.StaticText(self, wx.ID_ANY, "Z:")
		self.stLabelZ.SetFont(self.ftb)
		possz.Add(self.stLabelZ)

		self.stPosZ = wx.StaticText(self, wx.ID_ANY, "", size=(60, -1))
		self.stPosZ.SetFont(self.ftb)
		possz.Add(self.stPosZ)

		possz.AddSpacer(20)

		metasz = wx.BoxSizer(wx.VERTICAL)
		metasz.Add(possz)

		metasz.AddSpacer(30)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Total Duration: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stTDur = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stTDur.SetFont(self.ft)
		lnsz.Add(self.stTDur)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Print Duration: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stPDur = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stPDur.SetFont(self.ft)
		lnsz.Add(self.stPDur)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Estimate: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stEDur = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stEDur.SetFont(self.ft)
		lnsz.Add(self.stEDur)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Remaining: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stRemaining = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stRemaining.SetFont(self.ft)
		lnsz.Add(self.stRemaining)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "ETA: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stETA = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stETA.SetFont(self.ft)
		lnsz.Add(self.stETA)
		metasz.Add(lnsz)

		metasz.AddSpacer(15)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Total Height: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stTHt = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stTHt.SetFont(self.ft)
		lnsz.Add(self.stTHt)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Layer Height: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stLHt = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stLHt.SetFont(self.ft)
		lnsz.Add(self.stLHt)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Layer: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(20)
		self.stLayer = wx.StaticText(self, wx.ID_ANY, size=(60, -1))
		self.stLayer.SetFont(self.ft)
		lnsz.Add(self.stLayer)
		metasz.Add(lnsz)

		metasz.AddSpacer(15)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Total Filament: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stTFil = wx.StaticText(self, wx.ID_ANY, size=(100, -1))
		self.stTFil.SetFont(self.ft)
		lnsz.Add(self.stTFil)
		metasz.Add(lnsz)

		metasz.AddSpacer(5)
		lnsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "Filament Used: ", size=(150, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		lnsz.Add(st)
		lnsz.AddSpacer(10)
		self.stUFil = wx.StaticText(self, wx.ID_ANY, size=(100, -1))
		self.stUFil.SetFont(self.ft)
		lnsz.Add(self.stUFil)
		metasz.Add(lnsz)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		hsz.Add(fnhz)
		hsz.AddSpacer(10)
		hsz.Add(metasz)

		vsz.Add(hsz)
		vsz.AddSpacer(10)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		self.Gauge = wx.Gauge(self, wx.ID_ANY, range=100, size=(300, 20), style = wx.GA_HORIZONTAL + wx.GA_TEXT)
		self.Gauge.SetValue(0)
		hsz.Add(self.Gauge)
		hsz.AddSpacer(10)
		self.Percent = wx.StaticText(self, wx.ID_ANY, "0%")
		self.Percent.SetFont(self.ftb)
		hsz.Add(self.Percent)
		vsz.Add(hsz, 0, wx.ALIGN_CENTER_HORIZONTAL)

		vsz.AddSpacer(20)

		btnsz = wx.BoxSizer(wx.HORIZONTAL)

		self.bStart = wx.Button(self, wx.ID_ANY, "Start", size=BTNSZ)
		self.Bind(wx.EVT_BUTTON, self.OnBStart, self.bStart)
		self.bPause = wx.Button(self, wx.ID_ANY, "Pause", size=BTNSZ)
		self.Bind(wx.EVT_BUTTON, self.OnBPause, self.bPause)
		self.bClear = wx.Button(self, wx.ID_ANY, "Clear", size=BTNSZ)
		self.Bind(wx.EVT_BUTTON, self.OnBClear, self.bClear)
		self.bJog = wx.Button(self, wx.ID_ANY, "Jog", size=BTNSZ)
		self.Bind(wx.EVT_BUTTON, self.OnBJog, self.bJog)

		btnsz.Add(self.bStart)
		btnsz.AddSpacer(20)
		btnsz.Add(self.bPause)
		btnsz.AddSpacer(20)
		btnsz.Add(self.bClear)
		btnsz.AddSpacer(20)
		btnsz.Add(self.bJog)

		vsz.Add(btnsz, 0, wx.ALIGN_CENTER_HORIZONTAL)

		vsz.AddSpacer(10)

		vsz.Add(self.ZOffset(), 0, wx.ALIGN_CENTER_HORIZONTAL)

		vsz.AddSpacer(10)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def ZOffset(self):
		sz = wx.BoxSizer(wx.HORIZONTAL)
		self.rbx = wx.RadioBox(self, wx.ID_ANY,"step size", choices=["0.005", "0.01", "0.025", "0.05"],
							majorDimension=1, style=wx.RA_SPECIFY_ROWS)
		self.rbx.SetFont(self.ft)
		sz.Add(self.rbx)
		sz.AddSpacer(10)

		self.bUp = wx.Button(self, wx.ID_ANY, "up", size=(30, 30))
		self.Bind(wx.EVT_BUTTON, self.OnBUp, self.bUp)
		sz.Add(self.bUp, 0, wx.ALIGN_CENTER_VERTICAL)
		sz.AddSpacer(10)

		self.bDn = wx.Button(self, wx.ID_ANY, "dn", size=(30, 30))
		self.Bind(wx.EVT_BUTTON, self.OnBDn, self.bDn)
		sz.Add(self.bDn, 0, wx.ALIGN_CENTER_VERTICAL)

		sz.AddSpacer(10)
		st = wx.StaticText(self, wx.ID_ANY, "Z Offset: ")
		st.SetFont(self.ftb)
		sz.Add(st, 0, wx.ALIGN_CENTER_VERTICAL)

		self.stZOffset = wx.StaticText(self, wx.ID_ANY, "0.0")
		self.stZOffset.SetFont(self.ft)
		sz.Add(self.stZOffset, 0, wx.ALIGN_CENTER_VERTICAL)
		return sz

	def OnBUp(self, evt):
		self.BabyStep(1)

	def OnBDn(self, evt):
		self.BabyStep(-1)

	def BabyStep(self, direction):
		dirchar = "+" if direction == 1 else "-"
		ix = self.rbx.GetSelection()
		amt = self.rbx.GetString(ix)
		mv = "1" if self.state in ["printing", "paused"] else "0"
		cmd = "SET_GCODE_OFFSET Z_ADJUST=%s%s MOVE=%s" % (dirchar, amt, mv)
		self.moonraker.SendGCode(cmd)

	def GetState(self):
		return self.state

	def OnBStart(self, evt):
		if self.state == "printing":
			dlg = wx.MessageDialog(self, "Are you sure you want to cancel this job?\nPress \"Yes\" to proceed",
								   "Cancel Confirmation", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
			rc = dlg.ShowModal()
			dlg.Destroy()
			if rc == wx.ID_NO:
				return

			self.moonraker.PrintFileCancel()
			self.cancelling = True
			self.UpdateState()
		else:
			self.moonraker.PrintFile(self.activeFn)

	def OnBPause(self, evt):
		if self.state == "printing":
			self.moonraker.PrintFilePause()
		else:
			self.moonraker.PrintFileResume()

	def OnBClear(self, evt):
		self.moonraker.ClearFile()

	def OnBJog(self, evt):
		self.parent.OnBJog()

	def Ticker(self):
		self.stTDur.SetLabel(formatTime(self.totalduration))
		self.stPDur.SetLabel(formatTime(self.printduration))
		self.stUFil.SetLabel("%9.2f" % self.filamentused)
		if self.estimated is not None:
			if self.progress > 0.2:
				# calculate remaining once we hit 20% done using the amount of
				# time it took for us to get here
				totalDur = float(self.printduration) / float(self.progress)
				remaining = totalDur - self.printduration
			else:
				# else just use the printduration and estimated from moonraker
				remaining = self.estimated - self.printduration

			if remaining > 0:
				self.stRemaining.SetLabel(formatTime(remaining))
				now = time.time()
				eta = now + remaining
				etaStr = time.strftime("%I:%M:%S%p", time.localtime(eta))
				self.stETA.SetLabel(etaStr)
				self.stRemaining.SetLabel(formatTime(remaining))

			else:
				self.stRemaining.SetLabel("")
				self.stETA.SetLabel("")
		else:
			self.stRemaining.SetLabel("")
			self.stETA.SetLabel("")

		if self.totallayers is None and self.currentlayer is None:
			self.stLayer.SetLabel("")
		elif self.totallayers is None:
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
				self.estimated = s
				self.stEDur.SetLabel(formatTime(s))
			except KeyError:
				self.stEDur.SetLabel("")
				self.estimated = None
				self.stRemaining.SetLabel("")
				self.stETA.SetLabel("")

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
			movement = False
			extrusion = False
		else:
			state = self.state
			if self.state == "standby":
				movement = True
				extrusion = True
				if self.activeFn is None or self.activeFn == "":
					self.bStart.SetLabel("Start")
					self.bStart.Enable(False)
					self.bPause.SetLabel("Pause")
					self.bPause.Enable(False)
					self.bClear.Enable(False)
				else:
					self.bStart.SetLabel("Start")
					self.bStart.Enable(True)
					self.bPause.SetLabel("Pause")
					self.bPause.Enable(False)
					self.bClear.Enable(True)
			elif self.state == "printing" and not self.cancelling:
				movement = False
				extrusion = False
				self.bClear.Enable(False)
				self.bPause.Enable(True)
				self.bPause.SetLabel("Pause")
				self.bStart.Enable(True)
				self.bStart.SetLabel("Cancel")
			elif self.state == "printing" and self.cancelling:
				movement = False
				extrusion = False
				self.bClear.Enable(False)
				self.bPause.Enable(False)
				self.bPause.SetLabel("Pause")
				self.bStart.Enable(False)
				self.bStart.SetLabel("Cancel")
				state = "cancelling"
			elif self.state == "paused":
				movement = False
				extrusion = True
				self.bClear.Enable(False)
				self.bPause.Enable(True)
				self.bPause.SetLabel("Resume")
				self.bStart.Enable(True)
				self.bStart.SetLabel("Cancel")
				if self.jogDlg is not None:
					self.jogDlg.Destroy()
					self.jogDlg = None
			else: # self.state is completed or cancelled
				movement = True
				extrusion = True
				self.cancelling = False
				self.bPause.Enable(False)
				self.bPause.SetLabel("Pause")
				self.bClear.Enable(True)
				self.bStart.Enable(True)
				self.bStart.SetLabel("Restart")

			self.stState.SetLabel("State: %s" % state)

		self.parent.EnableJogging(movement, extrusion)

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

		if "gcode_move" in ivals:
			self.ParseGCodeMove(ivals["gcode_move"])


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

		if st is not None and (st != self.state or self.cancelling):
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

	def ParseGCodeMove(self, gcm):
		if "homing_origin" in gcm:
			self.GCHomeOrigin = gcm["homing_origin"]

		if "position" in gcm:
			self.GCPosition = gcm["position"]
		if "gcode_position" in gcm:
			self.GCGPosition = gcm["gcode_position"]

		try:
			zo = self.GCPosition[2] - self.GCGPosition[2]
		except Exception as e:
			self.parent.LogItem("Exception %s encountered trying to calculate z offset" % str(e))
			return

		self.zoffset = zo
		self.stZOffset.SetLabel("%6.3f" % self.zoffset)

	def setJobStatus(self, active, fn, pos, prog):
		self.jobStatus = active
		self.fpos = pos
		self.progress = prog
		self.ShowProgress()

	def ShowProgress(self):
		pct = self.progress * 100.0
		self.Gauge.SetValue(round(pct))
		self.Percent.SetLabel("%5.2f%%" % pct)

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

		if "gcode_move" in jmsg:
			self.ParseGCodeMove(jmsg["gcode_move"])

	def RefreshFilesList(self):
		pass
