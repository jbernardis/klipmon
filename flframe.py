import wx
import os
import io

from moonraker import MoonrakerException
from editgcode import EditGCodeDlg

MENU_PRINT = 1001
MENU_PREHEAT = 1002
MENU_DOWNLOAD = 1003
MENU_EDIT = 1004
MENU_REMOVE = 1005

BTNSZ = (100, 30)


class FlFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  File List  "
		self.SetLabel(self.titleText)
		topBorder, otherBorder = self.GetBordersForSizer()

		if wx.DisplaySize()[1] == 1440:
			ptsz = 12
			self.vspacing = 20
			self.hspacing = 20
		else:
			ptsz = 9
			self.vspacing = 10
			self.hspacing = 10

		self.ftb = wx.Font(ptsz, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")
		self.ft  = wx.Font(ptsz, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")

		self.parent = parent
		self.pname = pname
		self.settings = settings
		self.psettings = settings.GetPrinterSettings(pname)
		self.moonraker = None
		self.flMeta = {}
		self.fnList = []
		self.emptyBmp = self.MakeEmpty()
		self.menuFileName = None
		self.activeFn = None
		self.editDlg = None

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(self.vspacing)

		flsz = wx.BoxSizer(wx.HORIZONTAL)

		flsz.AddSpacer(self.hspacing)
		self.lcFiles = FileList(self)
		flsz.Add(self.lcFiles)
		flsz.AddSpacer(self.hspacing)

		metasz = wx.BoxSizer(wx.VERTICAL)

		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(self.hspacing)
		st = wx.StaticText(self, wx.ID_ANY, "Object Height: ", size=(100, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stObjHt = wx.StaticText(self, wx.ID_ANY, "", size=(100, -1))
		self.stObjHt.SetFont(self.ft)
		hsz2.Add(self.stObjHt)
		metasz.Add(hsz2)

		metasz.AddSpacer(5)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(self.hspacing)
		st = wx.StaticText(self, wx.ID_ANY, "Print Estimate: ", size=(100, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stPrtTime = wx.StaticText(self, wx.ID_ANY, "", size=(100, -1))
		self.stPrtTime.SetFont(self.ft)
		hsz2.Add(self.stPrtTime)
		metasz.Add(hsz2)

		metasz.AddSpacer(5)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(self.hspacing)
		st = wx.StaticText(self, wx.ID_ANY, "Layer Height: ", size=(100, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stLayerHt = wx.StaticText(self, wx.ID_ANY, "", size=(100, -1))
		self.stLayerHt.SetFont(self.ft)
		hsz2.Add(self.stLayerHt)
		metasz.Add(hsz2)

		metasz.AddSpacer(5)
		hsz2 = wx.BoxSizer(wx.HORIZONTAL)
		hsz2.AddSpacer(self.hspacing)
		st = wx.StaticText(self, wx.ID_ANY, "Total Filament: ", size=(100, -1), style=wx.ALIGN_RIGHT)
		st.SetFont(self.ftb)
		hsz2.Add(st)
		self.stFilament = wx.StaticText(self, wx.ID_ANY, "", size=(100, -1))
		self.stFilament.SetFont(self.ft)
		hsz2.Add(self.stFilament)
		metasz.Add(hsz2)

		metasz.AddSpacer(int(self.vspacing/2))
		self.bmp = wx.StaticBitmap(self, wx.ID_ANY, size=(200, 200))
		metasz.Add(self.bmp, 0, wx.ALIGN_CENTER_HORIZONTAL)
		metasz.AddSpacer(int(self.vspacing/2))

		flsz.Add(metasz)
		flsz.AddSpacer(self.hspacing)
		vsz.Add(flsz)

		self.bUpload = wx.Button(self, wx.ID_ANY, "Upload", size=BTNSZ)
		self.bUpload.SetBackgroundColour(wx.Colour(196, 196, 196))
		self.Bind(wx.EVT_BUTTON, self.OnBUpload, self.bUpload)
		vsz.Add(self.bUpload, 0, wx.ALIGN_CENTER_HORIZONTAL)
		vsz.AddSpacer(int(self.vspacing/2))

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

		item = wx.MenuItem(menu, MENU_EDIT, "Edit")
		item.SetFont(self.ftb)
		menu.Append(item)

		item = wx.MenuItem(menu, MENU_REMOVE, "Remove")
		item.SetFont(self.ftb)
		menu.Append(item)

		self.Bind(wx.EVT_MENU, self.OnMenuPrint, id=MENU_PRINT)
		self.Bind(wx.EVT_MENU, self.OnMenuPreheat, id=MENU_PREHEAT)
		self.Bind(wx.EVT_MENU, self.OnMenuDownload, id=MENU_DOWNLOAD)
		self.Bind(wx.EVT_MENU, self.OnMenuEdit, id=MENU_EDIT)
		self.Bind(wx.EVT_MENU, self.OnMenuRemove, id=MENU_REMOVE)

		return menu

	def OnMenuPrint(self, evt):
		if self.menuFileName is None:
			return

		try:
			self.moonraker.PrintFile(self.menuFileName)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

		wx.CallLater(1000, self.parent.LoadCurrentGCode)

	def OnMenuPreheat(self, evt):
		if self.menuFileName is None:
			return

		meta = self.flMeta[self.menuFileName]
		bedCmd  = "M140S%d" % meta["firstlayerbedtemp"]
		extrCmd = "M104S%d" % meta["firstlayerextrtemp"]
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

	def OnMenuDownload(self, evt):
		wildcard = "G Code files (*.gcode)|*.gcode|" \
				   "All files (*.*)|*.*"
		if self.menuFileName is None:
			return

		try:
			r = self.moonraker.FileDownload(self.menuFileName)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		sdir = self.settings.LastDir()
		dlg = wx.FileDialog(
			self, message="Save file as ...", defaultDir=sdir,
			defaultFile="", wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
		)
		rc = dlg.ShowModal()
		if rc == wx.ID_OK:
			path = dlg.GetPath()
			dlg.Destroy()
		else:
			dlg.Destroy()
			return

		try:
			with open(path, "wb") as ofp:
				ofp.write(r.content)
		except Exception as e:
			dlg = wx.MessageDialog(self, str(e), "File I/O error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		self.settings.SetLastDir(os.path.dirname(path))

		dlg = wx.MessageDialog(self, "File %s" % path, "Download Successful", wx.OK | wx.ICON_EXCLAMATION)
		dlg.ShowModal()
		dlg.Destroy()

	def OnMenuEdit(self, evt):
		if self.menuFileName is None:
			return

		try:
			r = self.moonraker.FileDownload(self.menuFileName)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		gcstring = r.content.decode('utf-8')
		gcode = gcstring.split("\n")
		self.editDlg = EditGCodeDlg(self, gcode, "Edit GCode: %s" % self.menuFileName, self.EditClose)
		self.editDlg.Show()

	def EditClose(self, rc):
		if rc == wx.ID_CANCEL:
			self.editDlg.Destroy()
			self.editDlg = None
			return

		gcode = self.editDlg.getData()

		try:
			self.editDlg.Destroy()
		except:
			pass

		self.editDlg = None

		with open(self.menuFileName, "w") as ofp:
			ofp.write("\n".join(gcode))

		try:
			fp = open(self.menuFileName, "rb")
		except Exception as e:
			dlg = wx.MessageDialog(self, str(e), "File I/O error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		try:
			self.moonraker.FileUpload(self.menuFileName, fp)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

		fp.close()

		os.unlink(self.menuFileName)

	def OnBUpload(self, evt):
		wildcard = "G Code files (*.gcode)|*.gcode|" \
				   "All files (*.*)|*.*"

		sdir = self.settings.LastDir()
		dlg = wx.FileDialog(
			self, message="Choose a G Code file",
			defaultDir=sdir,
			defaultFile="",
			wildcard=wildcard,
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW
		)
		rc = dlg.ShowModal()
		if rc == wx.ID_OK:
			path = dlg.GetPath()
			dlg.Destroy()
		else:
			dlg.Destroy()
			return

		klipName = os.path.basename(path)

		self.settings.SetLastDir(os.path.dirname(path))

		dlg = wx.TextEntryDialog(self, 'Enter new file name',
			'Enter File Name', klipName)
		if dlg.ShowModal() == wx.ID_OK:
			klipName = dlg.GetValue()
			if klipName is None:
				klipName = os.path.basename(path)
		dlg.Destroy()

		if klipName in self.fnList:
			dlg = wx.MessageDialog(self, "File %s already exists.\nPress \"Yes\" to proceed" % self.menuFileName,
								   "Duplicate File", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
			rc = dlg.ShowModal()
			dlg.Destroy()
			if rc == wx.ID_NO:
				return

		try:
			fp = open(path, "rb")
		except Exception as e:
			dlg = wx.MessageDialog(self, str(e), "File I/O error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		try:
			self.moonraker.FileUpload(self.menuFileName, fp)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

	def OnMenuRemove(self, evt):
		if self.menuFileName is None:
			return

		dlg = wx.MessageDialog(self, "Are you sure you want to delete\n%s" % self.menuFileName,
						"Delete Confirmation", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
		rc = dlg.ShowModal()
		dlg.Destroy()
		if rc == wx.ID_NO:
			return

		try:
			self.moonraker.FileDelete(self.menuFileName)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

	def SetMoonraker(self, mr):
		self.moonraker = mr
		self.RefreshFilesList()

	def SetInitialValues(self, ivals):
		pass

	def setJobStatus(self, active, fn, pos, prog):
		if fn is not None:
			self.activeFn = fn

	def HasCurrentFile(self):
		if self.activeFn is None or self.activeFn == "":
			return True # if I said false here, we would try to "fix" it, but nothing needs fixing here

		return self.activeFn in self.fnList

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
		try:
			fl = self.moonraker.FilesList()
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		self.flMeta = {}
		self.fnList = [x["path"] for x in fl]
		for fn in self.fnList:
			try:
				j = self.moonraker.GetGCodeMetaData(fn)
			except MoonrakerException as e:
				dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()
				continue

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
					try:
						d = self.moonraker.FileDownload(tfn)
					except MoonrakerException as e:
						dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
						dlg.ShowModal()
						dlg.Destroy()
						continue

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

		ptsz = 12 if wx.DisplaySize()[1] == 1440 else 9
		self.SetFont(wx.Font(wx.Font(ptsz, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD, faceName="Arial")))
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.moonraker = None
		self.parent = parent
		self.fnList = []

		self.InsertColumn(0, "File name")
		self.SetColumnWidth(0, 300)

		self.SetItemCount(0)

		self.attr1 = wx.ItemAttr()
		self.attr1.SetBackgroundColour(wx.Colour(8, 149, 235))

		self.attr2 = wx.ItemAttr()
		self.attr2.SetBackgroundColour(wx.Colour(196, 196, 196))

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
