import wx
import wx.lib.newevent
import json
from settings import Settings
from printer import PrinterDlg


class MainFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, size=(500, 500), style=wx.DEFAULT_FRAME_STYLE)

		self.settings = Settings()
		self.printerList = self.settings.GetPrinters()
		self.initialized = {x: False for x in self.printerList}
		self.initialized = {x: False for x in self.printerList}
		self.dialogs = {x: None for x in self.printerList}

		self.Bind(wx.EVT_CLOSE, self.onClose)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)

		st = wx.StaticText(self, wx.ID_ANY, "Available Printers:")
		hsz.Add(st, 0, wx.TOP, 5)
		hsz.AddSpacer(10)

		self.chPrinter = wx.Choice(self, wx.ID_ANY, choices=self.printerList)
		hsz.Add(self.chPrinter)
		self.Bind(wx.EVT_CHOICE, self.onChoicePrinter, self.chPrinter)
		self.chPrinter.SetSelection(0)
		self.selectedPrinter = self.printerList[0]

		hsz.AddSpacer(10)

		self.bConnect = wx.Button(self, wx.ID_ANY, "connect")
		self.Bind(wx.EVT_BUTTON, self.onButtonConnect, self.bConnect)
		hsz.Add(self.bConnect)

		hsz.AddSpacer(20)

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(20)
		vsz.Add(hsz)
		vsz.AddSpacer(20)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

	def onChoicePrinter(self, evt):
		self.selectedPrinter = evt.GetString()
		self.SetConnectLabel()

	def onButtonConnect(self, evt):
		if not self.initialized[self.selectedPrinter]:
			psettings = self.settings.GetPrinterSettings(self.selectedPrinter)
			ip = psettings["ip"]
			port = psettings["port"]
			cbMap = {
				"status": self.addStatusLine,
				"closer": self.ClosePrinter,
				"init": self.NotifyInit
			}
			dlg = self.dialogs[self.selectedPrinter] = PrinterDlg(self, ip, port, self.selectedPrinter, self.settings, cbMap)
			dlg.Initialize()
			self.bConnect.Enable(False)
		else:
			self.dialogs[self.selectedPrinter].Show()

	def addStatusLine(self, line):
		print("ASL: %s" % line)

	def SetConnectLabel(self):
		if self.selectedPrinter is None:
			self.bConnect.Enable(False)
			self.bConnect.SetLabel("connect")
		else:
			self.bConnect.Enable(True)
			self.bConnect.SetLabel("connect" if not self.initialized[self.selectedPrinter] else "show")

	def NotifyInit(self, flag, name):
		self.initialized[name] = flag
		if flag:
			self.dialogs[name].Show()
		self.SetConnectLabel()

	def ClosePrinter(self, name):
		if self.dialogs[name] is None:
			return

		self.initialized[name] = False
		self.dialogs[name] = None
		self.SetConnectLabel()

	def onClose(self, _):
		self.Destroy()


class App(wx.App):
	def OnInit(self):
		frame = MainFrame()
		frame.Show()
		return True


app = App(False)
app.MainLoop()
