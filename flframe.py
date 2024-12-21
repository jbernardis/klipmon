import wx, math
import json
import io

from moonraker import MoonrakerException
from gcode import GCode, MOVE_MOVE, MOVE_PRINT, MOVE_EXTRUDE, MOVE_RETRACT

MENU_PRINT = 1001
MENU_PREHEAT = 1002
MENU_DOWNLOAD = 1003
MENU_REMOVE = 1004



class FlFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(255, 255, 255))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  File List  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		self.ftb = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		self.ft = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.moonraker = None
		self.flMeta = {}
		self.fnList = []
		self.emptyBmp = self.MakeEmpty()
		self.menuFileName = None

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(20)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		self.lcFiles = FileList(self)
		hsz.Add(self.lcFiles)
		hsz.AddSpacer(20)
		vsz.Add(hsz)


		vsz.AddSpacer(10)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(20)
		st = wx.StaticText(self, wx.ID_ANY, "Object Height: ", size=(130, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stObjHt = wx.StaticText(self, wx.ID_ANY, "", size=(150, -1))
		self.stObjHt.SetFont(self.ft)
		hsz2.Add(self.stObjHt)
		vsz.Add(hsz2)

		vsz.AddSpacer(5)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(20)
		st = wx.StaticText(self, wx.ID_ANY, "Print Estimate: ", size=(130, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stPrtTime = wx.StaticText(self, wx.ID_ANY, "", size=(150, -1))
		self.stPrtTime.SetFont(self.ft)
		hsz2.Add(self.stPrtTime)
		vsz.Add(hsz2)

		vsz.AddSpacer(5)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(20)
		st = wx.StaticText(self, wx.ID_ANY, "Layer Height: ", size=(130, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stLayerHt = wx.StaticText(self, wx.ID_ANY, "", size=(150, -1))
		self.stLayerHt.SetFont(self.ft)
		hsz2.Add(self.stLayerHt)
		vsz.Add(hsz2)

		vsz.AddSpacer(5)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(20)
		st = wx.StaticText(self, wx.ID_ANY, "Total Filament: ", size=(130, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stFilament = wx.StaticText(self, wx.ID_ANY, "", size=(150, -1))
		self.stFilament.SetFont(self.ft)
		hsz2.Add(self.stFilament)
		vsz.Add(hsz2)

		vsz.AddSpacer(10)
		self.bmp = wx.StaticBitmap(self, wx.ID_ANY, size=(200, 200))
		vsz.Add(self.bmp, 0, wx.ALIGN_CENTER_HORIZONTAL)
		vsz.AddSpacer(10)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

		self.MakeMenu()

	def MakeMenu(self):
		menu = wx.Menu()
		item = wx.MenuItem(menu, MENU_PRINT, "Print")
		item.SetFont(self.ftb)
		menu.Append(item)

		item = wx.MenuItem(menu, MENU_PREHEAT, "Preheat")
		item.SetFont(self.ftb)
		menu.Append(item)

		item = wx.MenuItem(menu, MENU_DOWNLOAD, "Download")
		item.SetFont(self.ftb)
		menu.Append(item)

		item = wx.MenuItem(menu, MENU_REMOVE, "Remove")
		item.SetFont(self.ftb)
		menu.Append(item)

		self.Bind(wx.EVT_MENU, self.OnMenuPrint, id=MENU_PRINT)
		self.Bind(wx.EVT_MENU, self.OnMenuPreheat, id=MENU_PREHEAT)
		self.Bind(wx.EVT_MENU, self.OnMenuDownload, id=MENU_DOWNLOAD)
		self.Bind(wx.EVT_MENU, self.OnMenuRemove, id=MENU_REMOVE)

		return menu

	def OnMenuPrint(self, evt):
		if self.menuFileName is None:
			return

		self.moonraker.PrintFile(self.menuFileName)
		wx.CallLater(1000, self.parent.LoadCurrentGCode)

	def OnMenuPreheat(self, evt):
		if self.menuFileName is None:
			return

		meta = self.flMeta[self.menuFileName]
		bedCmd  = "M140S%d" % meta["firstlayerbedtemp"]
		extrCmd = "M104S%d" % meta["firstlayerextrtemp"]
		self.moonraker.SendGCode(bedCmd)
		self.moonraker.SendGCode(extrCmd)

	def OnMenuDownload(self, evt):
		# TODO
		print("download")

	def OnMenuRemove(self, evt):
		# TODO
		print("remove")

	def SetMoonraker(self, mr):
		self.moonraker = mr
		self.RefreshFilesList()

	def SetInitialValues(self, ivals):
		pass

	def GetMeta(self, fn):
		if fn is None:
			return None
		try:
			meta = self.flMeta[fn]
		except KeyError:
			return None

		try:
			return self.flMeta[fn]
		except KeyError:
			return None

	def RefreshFilesList(self):
		fl = self.moonraker.FilesList()
		self.flMeta = {}
		self.fnList = [x["path"] for x in fl]
		for fn in self.fnList:
			j = self.moonraker.GetGCodeMetaData(fn)
			self.flMeta[fn] = {
				"height": j["object_height"],
				"printtime": j["estimated_time"],
				"layerheight": j["layer_height"],
				"filamenttotal": j["filament_total"],
				"firstlayerbedtemp": j["first_layer_bed_temp"],
				"firstlayerextrtemp": j["first_layer_extr_temp"]
			}
			self.flMeta[fn]["thumbnail"] = None
			for tn in j["thumbnails"]:
				if tn["width"] == 200:
					tfn = tn["relative_path"]
					d = self.moonraker.FileDownload(tfn)
					i = wx.Image(io.BytesIO(d.content)).ConvertToBitmap()
					self.flMeta[fn]["thumbnail"]  = i

		self.lcFiles.loadFiles(self.fnList)
		if len(self.fnList) == 0:
			self.lcFiles.Select(wx.NOT_FOUND, False)
		else:
			self.lcFiles.Select(0, True)

	def UpdateStatus(self, jmsg):
		pass

	def ReportListSelection(self, lx):
		try:
			fn = self.fnList[lx]
		except:
			return

		try:
			tn = self.flMeta[fn]["thumbnail"]
		except:
			return

		if tn is not None:
			self.bmp.SetBitmap(tn)
		else:
			self.bmp.SetBitmap(self.emptyBmp)

		try:
			htStr = "%.2fmm" % self.flMeta[fn]["height"]
		except:
			htStr = "??"

		try:
			ptSec =  self.flMeta[fn]["printtime"]
			ptHrs = int(ptSec / 3600)
			ptMins = int((ptSec % 3600) / 60)
			ptSecs = (ptSec % 3600) % 60
			ptStr = "%dh %dm %ds" % (ptHrs, ptMins, ptSecs)
		except:
			ptStr = "??"

		try:
			lhtStr = "%.2fmm" % self.flMeta[fn]["layerheight"]
		except:
			lhtStr = "??"

		try:
			filStr = "%.2f" % self.flMeta[fn]["filamenttotal"]
		except:
			filStr = "??"

		self.stObjHt.SetLabel(htStr)
		self.stPrtTime.SetLabel(ptStr)
		self.stLayerHt.SetLabel(lhtStr)
		self.stFilament.SetLabel(filStr)

	def ReportListRightClick(self, lx):
		try:
			fn = self.fnList[lx]
		except:
			return

		self.menuFileName = fn
		menu = self.MakeMenu()
		self.PopupMenu(menu)
		menu.Destroy()

	def MakeEmpty(self):
		empty = wx.Bitmap(200, 200, 32)
		dc = wx.MemoryDC(empty)
		dc.SetBackground(wx.Brush((0, 0, 0, 0)))
		dc.Clear()
		del dc
		empty.SetMaskColour((0, 0, 0))
		return empty


class FileList (wx.ListCtrl):
	def __init__(self, parent):
		wx.ListCtrl.__init__(self, parent, wx.ID_ANY, size=(300, 300), \
				style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL)
		self.SetFont(wx.Font(wx.Font(16, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")))
		self.moonraker = None
		self.parent = parent
		self.fnList = []

		self.InsertColumn(0, "File name")
		self.SetColumnWidth(0, 300)

		self.SetItemCount(0)

		self.attr1 = wx.ItemAttr()
		self.attr1.SetBackgroundColour(wx.Colour(156, 252, 126))

		self.attr2 = wx.ItemAttr()
		self.attr2.SetBackgroundColour(wx.Colour(255, 255, 255))

		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
		self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemRughtClicked)

	def loadFiles(self, fl):
		self.SetItemCount(0)
		self.fnList = [x for x in fl]
		self.SetItemCount(len(self.fnList))

	def OnItemSelected(self, evt):
		cx = evt.Index
		self.parent.ReportListSelection(cx)

	def OnItemActivated(self, evt):
		pass

	def OnItemDeselected(self, evt):
		pass

	def OnItemRughtClicked(self, evt):
		cx = evt.Index
		self.parent.ReportListRightClick(cx)

	def OnGetItemText(self, item, col):
		return self.fnList[item]

	def OnGetItemAttr(self, item):
		if item % 2 == 1:
			return self.attr1
		else:
			return self.attr2
