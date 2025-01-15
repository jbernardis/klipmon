import wx

from moonraker import MoonrakerException

BUFFERSIZE = 16


class ManualGCodeFrame (wx.StaticBox):
	def __init__(self, parent, pname, settings):
		wx.StaticBox.__init__(self, parent, wx.ID_ANY, "")
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.titleText = "  Manual GCode Entry  "
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
		self.psettings = self.settings.GetPrinterSettings(pname)
		self.moonraker = None
		self.buffer = []
		self.bx = 0

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(topBorder)
		vsz.AddSpacer(self.vspacing)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(self.hspacing)

		self.tcGCode = wx.TextCtrl(self, wx.ID_ANY, size=(500, -1), style=wx.TE_PROCESS_ENTER)
		self.tcGCode.SetFont(self.ftb)
		self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter, self.tcGCode)
		self.tcGCode.Bind(wx.EVT_CHAR, self.OnTextChar)
		hsz.Add(self.tcGCode)

		hsz.AddSpacer(int(self.hspacing/2))
		self.bClear = wx.Button(self, wx.ID_ANY, "X", size=(30, 30))
		self.Bind(wx.EVT_BUTTON, self.OnBClear, self.bClear)
		hsz.Add(self.bClear)

		hsz.AddSpacer(self.hspacing)
		vsz.Add(hsz, 0, wx.EXPAND)

		vsz.AddSpacer(self.vspacing)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def SetMoonraker(self, mr):
		self.moonraker = mr

	def OnTextEnter(self, evt):
		cmd = evt.GetString()
		if len(self.buffer) == 0:
			self.buffer = [cmd]
		else:
			if cmd != self.buffer[self.bx]:
				self.buffer = [cmd] + self.buffer[:BUFFERSIZE-1]
				self.bx = 0

		try:
			self.moonraker.SendGCode(cmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

	def OnTextChar(self, evt):
		k = evt.GetKeyCode()
		if k == 315: # up
			if self.bx < len(self.buffer)-1:
				self.bx += 1
		elif k == 317: #down
			if self.bx > 0:
				self.bx -= 1
		else:
			evt.Skip()
			return

		self.tcGCode.Clear()
		self.tcGCode.AppendText(self.buffer[self.bx])

	def OnBClear(self, evt):
		self.tcGCode.Clear()

