import wx
import json

from moonraker import MoonrakerException
from statframe import formatTime
import time

BTNSZ = (120, 50)


def formatTimeStamp(ss):
	return time.strftime("%d%b%y %H:%M:%S", time.localtime(ss))


class HistoryDlg(wx.Dialog):
	def __init__(self, parent, pname, settings, moonraker):
		wx.Dialog.__init__(self, parent, wx.ID_ANY, "Job History")
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.pname = pname
		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(self.pname)
		self.moonraker = moonraker

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

		self.page = 0
		self.perPage = 50
		self.nJobs = 0
		self.messageText = ""

		vsz = wx.BoxSizer(wx.VERTICAL)
		hsz = wx.BoxSizer(wx.HORIZONTAL)

		hsz.AddSpacer(self.hspacing)

		self.hl = HistoryList(self)
		self.history = self.LoadHistory()
		if self.history is None:
			wx.CallAfter(self.SelfDestruct)
			return
		self.hl.LoadData(self.history)

		hsz.Add(self.hl)

		hsz.AddSpacer(self.hspacing)

		btnszr = wx.BoxSizer(wx.VERTICAL)

		self.bUp = wx.Button(self, wx.ID_ANY, "Page Up", size=(100, 25))
		self.Bind(wx.EVT_BUTTON, self.OnBPageUp, self.bUp)
		btnszr.Add(self.bUp)
		self.bUp.Enable(False)

		btnszr.AddSpacer(self.vspacing)

		self.bDn = wx.Button(self, wx.ID_ANY, "Page Down", size=(100, 25))
		self.Bind(wx.EVT_BUTTON, self.OnBPageDown, self.bDn)
		btnszr.Add(self.bDn)

		hsz.Add(btnszr)

		hsz.AddSpacer(self.hspacing)

		vsz.AddSpacer(self.vspacing)
		vsz.Add(hsz)
		vsz.AddSpacer(self.vspacing)

		self.stMessage = wx.StaticText(self, wx.ID_ANY, self.messageText, size=(400, -1))
		self.stMessage.SetFont(self.ftb)
		vsz.Add(self.stMessage, 0, wx.ALIGN_CENTER_HORIZONTAL)

		vsz.AddSpacer(self.vspacing)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def OnBPageUp(self, evt):
		if self.page >= 1:
			self.page -= 1
		if self.page == 0:
			self.bUp.Enable(False)
		self.history = self.LoadHistory()
		self.hl.LoadData(self.history)
		self.bDn.Enable(True)

	def OnBPageDown(self, evt):
		self.page += 1
		self.history = self.LoadHistory()
		self.hl.LoadData(self.history)
		self.bUp.Enable(True)
		self.bDn.Enable(self.start > 1)

	def LoadHistory(self):
		try:
			r = self.moonraker.GetHistoryTotals()
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return None

		try:
			self.nJobs = int(r["result"]["job_totals"]["total_jobs"]) + 1
		except KeyError:
			self.nJobs = 0

		if self.nJobs <= 0:
			dlg = wx.MessageDialog(self, "No jobs in history", "No History", wx.OK | wx.ICON_INFORMATION)
			dlg.ShowModal()
			dlg.Destroy()
			return None

		limit = self.perPage
		self.start = self.nJobs - ((self.page+1) * self.perPage) + 1
		if self.start < 1:
			self.start = 1

		self.messageText = "Showing jobs %d down to %d out of %d total." % (self.start + limit - 1, self.start, self.nJobs)
		try:
			self.stMessage.SetLabel(self.messageText)
		except AttributeError:
			pass

		try:
			r = self.moonraker.GetHistoryList(limit, self.start)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return None

		results = []
		for j in reversed(r["result"]["jobs"]):
			results.append(
				{
					"job_id": j["job_id"],
					"filename": j["filename"],
					"status": j["status"],
					"start_time": formatTimeStamp(j["start_time"]),
					"end_time": formatTimeStamp(j["end_time"]),
					"print_duration": formatTime(j["print_duration"]),
					"filament_used": int(j["filament_used"])
				}
			)

		return results

	def GetJobHistory(self, jobid):
		try:
			r = self.moonraker.GetHistoryJob(jobid)
		except MoonrakerException as e:
			print("unable to retrieve job %s" % jobid)
			r = None
		return r

	def SelfDestruct(self):
		self.EndModal(wx.ID_CANCEL)

	def onClose(self, evt):
		self.EndModal(wx.ID_OK)


class HistoryList (wx.ListCtrl):
	def __init__(self, parent):
		if wx.DisplaySize()[1] == 1440:
			self.ptsz = 12
		else:
			self.ptsz = 9

		wx.ListCtrl.__init__(self, parent, wx.ID_ANY, size=(960+18, 370),
				style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES | wx.LC_SINGLE_SEL)
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))

		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

		self.SetFont(wx.Font(self.ptsz, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial"))
		self.moonraker = None
		self.parent = parent

		self.InsertColumn(0, "file")
		self.SetColumnWidth(0, 280)
		self.InsertColumn(1, "status")
		self.SetColumnWidth(1, 120)
		self.InsertColumn(2, "start")
		self.SetColumnWidth(2, 160)
		self.InsertColumn(3, "end")
		self.SetColumnWidth(3, 160)
		self.InsertColumn(4, "duration")
		self.SetColumnWidth(4, 120)
		self.InsertColumn(5, "filament")
		self.SetColumnWidth(5, 120)

		self.history = []
		self.nItems = 0

		self.attr1 = wx.ItemAttr()
		self.attr1.SetBackgroundColour(wx.Colour(8, 149, 235))

		self.attr2 = wx.ItemAttr()
		self.attr2.SetBackgroundColour(wx.Colour(196, 196, 196))

		self.SetItemCount(self.nItems)

	def OnItemActivated(self, evt):
		ix = evt.Index
		jobid = self.history[ix]["job_id"]
		j = self.parent.GetJobHistory(jobid)
		if j is None:
			dlg = wx.MessageDialog(self, "History database does not contain job id %s" % jobid,
				"Unable to retrieve job %s" % jobid,
			    wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		try:
			m = j["result"]["job"]["metadata"]
		except KeyError:
			dlg = wx.MessageDialog(self, "Job id %s has no associated metadata" % jobid,
								   "No metadata",
								   wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		#k = sorted([md for md in m if md != "thumbnails"])
		#print(str(k))

		dlg = MetadataDlg(self, j["result"]["job"]["filename"], jobid, m)
		dlg.ShowModal()
		dlg.Destroy()

	def Ticker(self):
		self.RefreshItems(0, self.nItems-1)

	def LoadData(self, h):
		self.history = [j for j in h]
		self.nItems = len(self.history)
		self.SetItemCount(self.nItems)
		self.RefreshItems(0, self.nItems-1)

	def OnGetItemText(self, item, col):
		job = self.history[item]
		if col == 0:
			return job["filename"]
		elif col == 1:
			return job["status"]
		elif col == 2:
			return job["start_time"]
		elif col == 3:
			return job["end_time"]
		elif col == 4:
			return job["print_duration"]
		elif col == 5:
			return "%d" % job["filament_used"]

	def OnGetItemAttr(self, item):
		if item % 2 == 1:
			return self.attr1
		else:
			return self.attr2

class MetadataDlg(wx.Dialog):
	def __init__(self, parent, filename, jobid, metadata):
		wx.Dialog.__init__(self, parent, wx.ID_ANY, "Metadata for job %s (file: %s)" % (jobid, filename))
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.parent = parent

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

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		vsz = wx.BoxSizer(wx.VERTICAL)

		keys = sorted([k for k in metadata.keys() if k != "thumbnails"])
		toggle = False
		for k in keys:
			metasz = wx.BoxSizer(wx.HORIZONTAL)
			st = wx.StaticText(self, wx.ID_ANY, k+": ", size=(200, -1), style=wx.ALIGN_RIGHT)
			st.SetFont(self.ftb)
			st.SetBackgroundColour(wx.Colour(8, 149, 235) if toggle else wx.Colour(196, 196, 196))

			metasz.Add(st)
			#metasz.AddSpacer(self.hspacing)
			st = wx.StaticText(self, wx.ID_ANY, self.formatMetadata(k, metadata[k]), size=(400, -1))
			st.SetFont(self.ft)
			st.SetBackgroundColour(wx.Colour(8, 149, 235) if toggle else wx.Colour(196, 196, 196))
			metasz.Add(st)
			vsz.Add(metasz)

			toggle = not toggle

		vsz.AddSpacer(self.vspacing)

		hsz.AddSpacer(self.hspacing)
		hsz.Add(vsz)
		hsz.AddSpacer(self.hspacing)

		self.SetSizer(hsz)
		self.Layout()
		self.Fit()

	def formatMetadata(self, key, value):
		if key == "estimated_time":
			return formatTime(value)
		elif key == "modified":
			return formatTimeStamp(value)
		else:
			return str(value)

	def onClose(self, evt):
		self.EndModal(wx.ID_OK)
