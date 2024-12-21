import wx, math
import os
import json

from moonraker import MoonrakerException
from gcode import GCode, MOVE_MOVE, MOVE_PRINT, MOVE_EXTRUDE, MOVE_RETRACT

MAXZOOM = 10
ZOOMDELTA = 0.1


def triangulate(p1, p2):
	dx = p2[0] - p1[0]
	dy = p2[1] - p1[1]
	d = math.sqrt(dx*dx + dy*dy)
	return d


dk_Gray = wx.Colour(224, 224, 224)
lt_Gray = wx.Colour(128, 128, 128)
black = wx.Colour(0, 0, 0)


class GcFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(255, 255, 255))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  G Code Viewer  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.gcodesettings = self.settings.GetPrinterGCodeSettings(self.pname)
		self.moonraker = None
		self.filename = None

		self.followprint = False
		self.ppos = 0
		self.progress = 0.0
		self.gcode = None

		self.active = False
		self.activeFn = None

		self.showmoves = self.gcodesettings["showmoves"]
		self.showprevious = self.gcodesettings["showprevious"]
		self.showretractions = self.gcodesettings["showretractions"]
		self.showrevretractions = self.gcodesettings["showrevretractions"]
		self.showprintedonly = self.gcodesettings["showprintedonly"]

		self.gcPanel = GcPanel(self, pname, self.settings)
		ht = self.gcPanel.GetSize()[1]
		self.slLayer = wx.Slider(
			self, wx.ID_ANY, 0, 0, 100, size=(-1, ht),
			style=wx.SL_VERTICAL | wx.SL_LABELS | wx.SL_INVERSE
		)
		self.slLayer.Enable(False)
		self.Bind(wx.EVT_SCROLL_CHANGED, self.onSCROLL_CHANGED, self.slLayer)

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(20)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		self.bOpenPrinter = wx.Button(self, wx.ID_ANY, "Printer File")
		self.bOpenPrinter.Enable(False)
		self.Bind(wx.EVT_BUTTON, self.onBOpenPrinter, self.bOpenPrinter)
		hsz.Add(self.bOpenPrinter)
		hsz.AddSpacer(20)
		self.bOpenCurrent = wx.Button(self, wx.ID_ANY, "Current File")
		self.bOpenCurrent.Enable(False)
		self.Bind(wx.EVT_BUTTON, self.onBOpenCurrent, self.bOpenCurrent)
		hsz.Add(self.bOpenCurrent)
		hsz.AddSpacer(20)
		self.bOpenLocal = wx.Button(self, wx.ID_ANY, "Local File")
		self.Bind(wx.EVT_BUTTON, self.onBOpenLocal, self.bOpenLocal)
		hsz.Add(self.bOpenLocal)
		hsz.AddSpacer(20)
		vsz.Add(hsz)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		hsz.Add(self.gcPanel)
		hsz.Add(self.slLayer)
		hsz.AddSpacer(20)

		vsz.AddSpacer(20)
		vsz.Add(hsz)
		vsz.AddSpacer(10)

		optsizer = wx.BoxSizer(wx.HORIZONTAL)
		optsizer.AddSpacer(60)

		optvsizer = wx.BoxSizer(wx.VERTICAL)
		optvsizer.AddSpacer(10)

		self.cbFollowPrint = wx.CheckBox(self, wx.ID_ANY, "Follow Print")
		self.cbFollowPrint.SetValue(self.followprint)
		self.Bind(wx.EVT_CHECKBOX, self.onCbFollowPrint, self.cbFollowPrint)
		optvsizer.Add(self.cbFollowPrint)
		self.gcPanel.setFollowPrint(self.followprint)
		optvsizer.AddSpacer(5)

		self.cbShowMoves = wx.CheckBox(self, wx.ID_ANY, "Show moves")
		self.cbShowMoves.SetValue(self.showmoves)
		self.Bind(wx.EVT_CHECKBOX, self.obCbShowMoves, self.cbShowMoves)
		optvsizer.Add(self.cbShowMoves)
		self.gcPanel.setShowMoves(self.showmoves)
		optvsizer.AddSpacer(5)

		self.cbShowPrevious = wx.CheckBox(self, wx.ID_ANY, "Show previous layer")
		self.cbShowPrevious.SetValue(self.showprevious)
		self.Bind(wx.EVT_CHECKBOX, self.obCbShowPrevious, self.cbShowPrevious)
		optvsizer.Add(self.cbShowPrevious)
		self.gcPanel.setShowPrevious(self.showprevious)
		optvsizer.AddSpacer(5)

		self.cbShowRetractions = wx.CheckBox(self, wx.ID_ANY, "Show retractions")
		self.cbShowRetractions.SetValue(self.showretractions)
		self.Bind(wx.EVT_CHECKBOX, self.obCbShowRetractions, self.cbShowRetractions)
		optvsizer.Add(self.cbShowRetractions)
		self.gcPanel.setShowRetractions(self.showretractions)
		optvsizer.AddSpacer(5)

		self.cbShowRevRetractions = wx.CheckBox(self, wx.ID_ANY, "Show reverse retractions")
		self.cbShowRevRetractions.SetValue(self.showrevretractions)
		self.Bind(wx.EVT_CHECKBOX, self.obCbShowRevRetractions, self.cbShowRevRetractions)
		optvsizer.Add(self.cbShowRevRetractions)
		self.gcPanel.setShowRevRetractions(self.showrevretractions)
		optvsizer.AddSpacer(5)

		self.cbShowPrintedOnly = wx.CheckBox(self, wx.ID_ANY, "Show printed only")
		self.cbShowPrintedOnly.SetValue(self.showprintedonly)
		self.Bind(wx.EVT_CHECKBOX, self.obCbShowPrintedOnly, self.cbShowPrintedOnly)
		optvsizer.Add(self.cbShowPrintedOnly)
		self.gcPanel.setShowPrintedOnly(self.showprintedonly)
		optvsizer.AddSpacer(10)

		optsizer.Add(optvsizer)
		optsizer.AddSpacer(20)

		vsz.Add(optsizer)

		vsz.AddSpacer(20)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def setTitle(self, fn, loc):
		tstr = self.titleText
		self.filename = fn
		if fn is not None:
			tstr += " - " + loc + ": " + fn + "  "

		self.SetLabel(tstr)

	def SetInitialValues(self, ivals):
		if "print_stats" in ivals:
			try:
				fn = ivals["print_stats"]["filename"]
				if fn.strip() == "":
					fn = None
			except KeyError:
				fn = None
			self.activeFn = fn
			self.bOpenCurrent.Enable(self.moonraker is not None and self.activeFn is not None)

	def setJobStatus(self, active, fn, pos, prog):
		self.active = active
		if fn is not None:
			self.activeFn = fn

		self.bOpenCurrent.Enable(self.moonraker is not None and self.activeFn is not None)

		self.ppos = pos
		self.progress = prog
		self.gcPanel.setPrintPosition(pos)
		if self.followprint:
			if self.gcode is not None:
				l = self.gcode.findLayerByOffset(pos)[0]
				self.slLayer.SetValue(l)

	def UpdateStatus(self, jmsg):
		pass

	def SetMoonraker(self, mr):
		self.moonraker = mr
		self.bOpenPrinter.Enable(mr is not None)
		self.bOpenCurrent.Enable(self.moonraker is not None and self.activeFn is not None)

	def onBOpenPrinter(self, evt):
		fl = self.moonraker.FilesList()
		fnlist = [x["path"] for x in fl]

		dlg = wx.SingleChoiceDialog(self, 'Choose a GCode File', 'Printer Files', fnlist, wx.CHOICEDLG_STYLE)

		if dlg.ShowModal() == wx.ID_OK:
			fn = dlg.GetStringSelection()
			gcl = self.moonraker.FileDownload(fn).text.split("\n")
			gcode = GCode(gcl, self.pname, self.settings)
			print("calling from open printer %s" % str(gcode))
			self.loadGCode(gcode, False)
			self.setTitle(fn, "Printer")

		dlg.Destroy()
		self.cbFollowPrint.SetValue(False)
		self.cbFollowPrint.Enable(False)

	def onBOpenCurrent(self, evt):
		self.OpenCurrent()

	def OpenCurrent(self):
		if self.activeFn is None:
			return
		gcl = self.moonraker.FileDownload(self.activeFn).text.split("\n")
		gcode = GCode(gcl, self.pname, self.settings)
		print("calling from open current %s" % str(gcode))
		self.loadGCode(gcode, True)
		self.setTitle(self.activeFn, "Current")
		self.cbFollowPrint.Enable(True)

	def onBOpenLocal(self, evt):
		wildcard = "G Code files (*.gcode)|*.gcode|" \
				   "All files (*.*)|*.*"

		dlg = wx.FileDialog(
			self, message="Choose a G Code file",
			defaultDir=os.getcwd(),
			defaultFile="",
			wildcard=wildcard,
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW
		)
		rc = dlg.ShowModal()
		if rc == wx.ID_OK:
			path = dlg.GetPath()
		else:
			return

		with open(path) as x:
			gcl = x.readlines()

		gcode = GCode(gcl, self.pname, self.settings)
		print("calling from open local %s" % str(gcode))
		self.loadGCode(gcode, False)
		self.setTitle(os.path.basename(path), "Local")

		self.cbFollowPrint.SetValue(False)
		self.cbFollowPrint.Enable(False)

	def onSCROLL_CHANGED(self, evt):
		lyr = self.slLayer.GetValue()
		self.gcPanel.setLayer(lyr)
		self.followprint = False
		self.cbFollowPrint.SetValue(False)
		self.gcPanel.setFollowPrint(self.followprint)

	def onCbFollowPrint(self, evt):
		self.followprint = self.cbFollowPrint.IsChecked()
		self.gcPanel.setFollowPrint(self.followprint)

	def obCbShowMoves(self, evt):
		self.gcPanel.setShowMoves(self.cbShowMoves.IsChecked())

	def obCbShowPrevious(self, evt):
		self.gcPanel.setShowPrevious(self.cbShowPrevious.IsChecked())

	def obCbShowRetractions(self, evt):
		self.gcPanel.setShowRetractions(self.cbShowRetractions.IsChecked())

	def obCbShowRevRetractions(self, evt):
		self.gcPanel.setShowRevRetractions(self.cbShowRevRetractions.IsChecked())

	def obCbShowPrintedOnly(self, evt):
		self.gcPanel.setShowPrintedOnly(self.cbShowPrintedOnly.IsChecked())

	def loadGCode(self, gcode, followable):
		self.gcode = gcode
		if gcode is None:
			self.slLayer.Enable(False)
			return

		self.gcPanel.loadGCode(gcode, 0, 1, followable)
		nlayers = gcode.layerCount()
		if nlayers == 0:
			self.slLayer.Enable(False)
		else:
			self.slLayer.SetRange(0, nlayers-1)
			self.slLayer.SetValue(0)
			self.slLayer.Enable(True)
			print(self.slLayer.GetTickFreq())

class GcPanel (wx.Panel):
	def __init__(self, parent, pname, settings):
		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.gcodesettings = self.settings.GetPrinterGCodeSettings(self.pname)

		self.printPosition = 0

		self.scale = self.gcodesettings["scale"]
		self.zoom = 1
		self.offsety = 0
		self.offsetx = 0
		self.startPos = (0, 0)
		self.startOffset = (0, 0)
		self.buildarea = self.gcodesettings["buildarea"]
		self.gcode = None
		self.currentlx = None
		self.shiftX = 0
		self.shiftY = 0
		self.buffer = None
		self.penMap = {}
		self.bkgPenMap = {}

		self.followprint = False
		self.followrequested = False
		self.followable = False

		self.penInvisible = wx.Pen(wx.Colour(0, 0, 0), 1, style=wx.PENSTYLE_TRANSPARENT)
		self.pensInvisible = [self.penInvisible, self.penInvisible]

		self.movePens = [wx.Pen(wx.Colour(0, 0, 0), 1), wx.Pen(wx.Colour(128, 128, 128), 1)]
		self.printPens = [wx.Pen(wx.Colour(0, 0, 255), 2), wx.Pen(wx.Colour(180, 180, 180), 2)]
		self.retractionPens = [wx.Pen(wx.Colour(255, 0, 0), 10), wx.Pen(wx.Colour(180, 180, 180), 10)]
		self.revRetractionPens = [wx.Pen(wx.Colour(0, 255, 0), 10), wx.Pen(wx.Colour(180, 180, 180), 10)]

		self.backgroundPen = wx.Pen(wx.Colour(128, 128, 128), 1)

		self.showmoves = False
		self.showprevious = False
		self.showretractions = False
		self.showrevretractions = False
		self.showprintedonly =False

		self.setPenMap()

		sz = [(x+1) * self.scale for x in self.buildarea]

		wx.Panel.__init__(self, parent, size=sz)
		self.Show()

		self.initBuffer()
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
		self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
		self.Bind(wx.EVT_MOTION, self.onMotion)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel, self)

	def setPenMap(self):
		self.penMap = { MOVE_PRINT: self.printPens,
						MOVE_MOVE: self.movePens if self.showmoves else self.pensInvisible,
						MOVE_EXTRUDE: self.revRetractionPens if self.showrevretractions else self.pensInvisible,
						MOVE_RETRACT: self.retractionPens if self.showretractions else self.pensInvisible }

		self.bkgPenMap = { MOVE_PRINT: self.backgroundPen,
							MOVE_MOVE: self.backgroundPen if self.showmoves else self.penInvisible,
							MOVE_EXTRUDE: self.backgroundPen if self.showrevretractions else self.penInvisible,
							MOVE_RETRACT: self.backgroundPen if self.showretractions else self.penInvisible }

	def onSize(self, _):
		self.initBuffer()

	def setFollowPrint(self, flag=True):
		self.followrequested = flag
		self.followprint = flag
		self.redrawCurrentLayer()

	def setShowPrintedOnly(self, flag=True):
		self.showprintedonly = flag
		self.redrawCurrentLayer()

	def setShowMoves(self, flag=True):
		self.showmoves = flag
		self.setPenMap()
		self.redrawCurrentLayer()

	def setShowPrevious(self, flag=True):
		self.showprevious = flag
		self.setPenMap()
		self.redrawCurrentLayer()

	def setShowRetractions(self, flag=True):
		self.showretractions = flag
		self.setPenMap()
		self.redrawCurrentLayer()

	def setShowRevRetractions(self, flag=True):
		self.showrevretractions = flag
		self.setPenMap()
		self.redrawCurrentLayer()

	def setPrintPosition(self, pos):
		self.printPosition = pos
		if self.followprint:
			lx = self.gcode.findLayerByOffset(pos)[0]
			if lx != self.currentlx:
				self.setLayer(lx)
			else:
				self.redrawCurrentLayer()

	def getPrintPosition(self):
		return self.printPosition

	def onPaint(self, _):
		dc = wx.BufferedPaintDC(self, self.buffer)  # @UnusedVariable

	def onLeftDown(self, evt):
		self.startPos = evt.GetPosition()
		self.startOffset = (self.offsetx, self.offsety)
		self.CaptureMouse()
		self.SetFocus()

	def onLeftUp(self, _):
		if self.HasCapture():
			self.ReleaseMouse()

	def onMotion(self, evt):
		if evt.Dragging() and evt.LeftIsDown():
			x, y = evt.GetPosition()
			dx = x - self.startPos[0]
			dy = y - self.startPos[1]
			self.offsetx = self.startOffset[0] - dx/(2*self.zoom)
			if self.offsetx < 0:
				self.offsetx = 0
			if self.offsetx > (self.buildarea[0]-self.buildarea[0]/self.zoom):
				self.offsetx = self.buildarea[0]-self.buildarea[0]/self.zoom

			self.offsety = self.startOffset[1] - dy/(2*self.zoom)
			if self.offsety < 0:
				self.offsety = 0
			if self.offsety > (self.buildarea[1]-self.buildarea[1]/self.zoom):
				self.offsety = self.buildarea[1]-self.buildarea[1]/self.zoom

			self.redrawCurrentLayer()

		evt.Skip()

	def onMouseWheel(self, evt):
		if evt.GetWheelRotation() < 0:
			self.zoomIn()
		else:
			self.zoomOut()

	def zoomIn(self):
		if self.zoom < MAXZOOM:
			zoom = self.zoom + ZOOMDELTA
			self.setZoom(zoom)

	def zoomOut(self):
		if self.zoom > 1:
			zoom = self.zoom - ZOOMDELTA
			self.setZoom(zoom)

	def loadGCode(self, gcode, layer=0, zoom=1, followable=False):
		self.followable = followable
		self.followprint = self.followrequested if followable else False
		self.gcode = gcode

		if gcode is None:
			self.currentlx = None
		else:
			self.currentlx = layer
		self.shiftX = 0
		self.shiftY = 0
		if zoom is not None:
			self.zoom = zoom
			if zoom == 1:
				self.offsetx = 0
				self.offsety = 0

		if not followable:
			self.printPosition = 0

		self.redrawCurrentLayer()

	def initBuffer(self):
		w, h = self.GetClientSize()
		if w > 0 and h > 0:
			self.buffer = wx.Bitmap(w, h)
			self.redrawCurrentLayer()

	def setLayer(self, lyr):
		if self.gcode is None:
			return
		if lyr < 0 or lyr >= self.gcode.layerCount():
			return
		if lyr == self.currentlx:
			return

		self.currentlx = lyr
		self.redrawCurrentLayer()

	def getCurrentLayerNum(self):
		return self.currentlx
	
	def getMaxLayerNum(self):
		if self.gcode is None:
			return 0
		return self.gcode.layerCount()-1

	def getCurrentLayer(self):
		if self.currentlx is None:
			return None

		return self.gcode.getLayer(self.currentlx)

	def getZoom(self):
		return self.zoom

	def setZoom(self, zoom):
		if zoom > self.zoom:
			oldzoom = self.zoom
			self.zoom = zoom
			cx = self.offsetx + self.buildarea[0]/oldzoom/2.0
			cy = self.offsety + self.buildarea[1]/oldzoom/2.0
			self.offsetx = cx - self.buildarea[0]/self.zoom/2.0
			self.offsety = cy - self.buildarea[1]/self.zoom/2.0
		else:
			oldzoom = self.zoom
			self.zoom = zoom
			cx = self.offsetx + self.buildarea[0]/oldzoom/2.0
			cy = self.offsety + self.buildarea[1]/oldzoom/2.0
			self.offsetx = cx - self.buildarea[0]/self.zoom/2.0
			self.offsety = cy - self.buildarea[1]/self.zoom/2.0
			if self.offsetx < 0:
				self.offsetx = 0
			if self.offsetx > (self.buildarea[0]-self.buildarea[0]/self.zoom):
				self.offsetx = self.buildarea[0]-self.buildarea[0]/self.zoom

			if self.offsety < 0:
				self.offsety = 0
			if self.offsety > (self.buildarea[1]-self.buildarea[1]/self.zoom):
				self.offsety = self.buildarea[1]-self.buildarea[1]/self.zoom

		self.redrawCurrentLayer()

	def setShift(self, sx, sy):
		self.shiftX = sx
		self.shiftY = sy
		self.redrawCurrentLayer()

	def redrawCurrentLayer(self):
		dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)

		self.drawGraph(dc, self.currentlx)

		del dc
		self.Refresh()
		self.Update()

	def drawGraph(self, dc, lyr):
		dc.SetBackground(wx.Brush(wx.Colour(255, 255, 255)))
		dc.Clear()

		self.drawGrid(dc)
		self.drawLayer(dc, lyr)

	def drawGrid(self, dc):
		yleft = round((0 - self.offsety)*self.zoom*self.scale)
		if yleft < 0: 
			yleft = 0

		yright = round((self.buildarea[1] - self.offsety)*self.zoom*self.scale)
		if yright > self.buildarea[1]*self.scale:
			yright = round(self.buildarea[1]*self.scale)

		for x in range(0, self.buildarea[0]+1, 10):
			if x == 0 or x == self.buildarea[0]:
				dc.SetPen(wx.Pen(black, 1))
			elif x%50 == 0:
				dc.SetPen(wx.Pen(lt_Gray, 1))
			else:
				dc.SetPen(wx.Pen(dk_Gray, 1))
			x = round((x - self.offsetx)*self.zoom*self.scale)
			if 0 <= x <= self.buildarea[0]*self.scale:
				dc.DrawLine(x, yleft, x, yright)

		xtop = round((0 - self.offsetx)*self.zoom*self.scale)
		if xtop <1:
			xtop = 1

		xbottom = round((self.buildarea[0] - self.offsetx)*self.zoom*self.scale)
		if xbottom > self.buildarea[0]*self.scale:
			xbottom = round(self.buildarea[0]*self.scale)

		for y in range(0, self.buildarea[1]+1, 10):
			if y == 0 or y == self.buildarea[1]:
				dc.SetPen(wx.Pen(black, 1))
			if y%50 == 0:
				dc.SetPen(wx.Pen(lt_Gray, 1))
			else:
				dc.SetPen(wx.Pen(dk_Gray, 1))
			y = round((y - self.offsety)*self.zoom*self.scale)
			if 0 <= y <= self.buildarea[1]*self.scale:
				dc.DrawLine(xtop, y, xbottom, y)

	def drawLayer(self, dc, lx):
		if lx is None:
			return

		pl = self.currentlx-1
		if pl>=0 and self.showprevious:
			self.drawOneLayer(dc, pl, background=True)

		self.drawOneLayer(dc, lx)

	def drawOneLayer(self, dc, lx, background=False):
		if lx is None:
			return

		layer = self.gcode.getLayer(lx)
		if layer is None:
			return

		pts = [ self.transform(m.x, m.y) for m in layer.getMoves() if m.mtype not in [MOVE_EXTRUDE, MOVE_RETRACT]]
		mtype = [m.mtype for m in layer.getMoves()  if m.mtype not in [MOVE_EXTRUDE, MOVE_RETRACT]]
		offsets = [m.offset for m in layer.getMoves()  if m.mtype not in [MOVE_EXTRUDE, MOVE_RETRACT]]

		expts = [ self.transform(m.x, m.y) for m in layer.getMoves() if m.mtype in [MOVE_EXTRUDE, MOVE_RETRACT]]
		exmtype = [m.mtype for m in layer.getMoves()  if m.mtype in [MOVE_EXTRUDE, MOVE_RETRACT]]
		exoffsets = [m.offset for m in layer.getMoves()  if m.mtype in [MOVE_EXTRUDE, MOVE_RETRACT]]

		if len(pts) == 0:
			return

		if len(pts) == 1:
			pts = [[pts[0][0], pts[0][1]], [pts[0][0], pts[0][1]]]
			mt = mtype[0]
			mtype = [mt, mt]
			of = offsets[0]
			offsets = [of, of]

		lines = [[pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]] for i in range(len(pts)-1)] + \
			[[expts[i][0], expts[i][1], expts[i][0], expts[i][1]] for i in range(len(expts))]
		pens = [self.getPen(mtype[i+1], offsets[i+1], background) for i in range(len(mtype)-1)] + \
			[self.getPen(exmtype[i], exoffsets[i], background) for i in range(len(expts))]

		try:
			dc.DrawLineList(lines, pens)
		except TypeError:
			print("Type error: lines = %s" % str(lines))
			print("             pens = %s" % str(pens))
			raise

	def getPen(self, mtype, offset, background):
		if background:
			return self.bkgPenMap[mtype]

		if not self.followable or self.printPosition < offset:
			if self.followprint and self.showprintedonly:
				return self.penInvisible
			else:
				return self.penMap[mtype][0]
		else:
			return self.penMap[mtype][1]

	def transform(self, ptx, pty):
		x = round((ptx - self.offsetx + self.shiftX)*self.zoom*self.scale)
		y = round((self.buildarea[1]-pty - self.offsety - self.shiftY)*self.zoom*self.scale)
		return x, y
