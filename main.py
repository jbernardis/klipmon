import wx
from settings import Settings
from printer import PrinterFrame


class App(wx.App):
	def addStatusLine(self, line):
		print(line)

	def NotifyInit(self, flag, name):
		try:
			self.dlg.Destroy()
		except:
			pass

		if flag:
			self.frame.Show()
		else:
			print("Failed initialization - terminating")
			try:
				self.frame.Destroy()
			except Exception as e:
				print("Exception on shutdown: %s" % str(e))

	def ClosePrinter(self, name):
		self.frame.Destroy()

	def OnInit(self):
		settings = Settings()
		cbMap = {
			"status": self.addStatusLine,
			"closer": self.ClosePrinter,
			"init": self.NotifyInit
		}
		self.frame = PrinterFrame("dbot", settings, cbMap)

		self.dlg = wx.MessageDialog(self.frame, "hello", "goodbye", wx.OK | wx.ICON_INFORMATION)
		self.dlg.Show()

		return True


app = App(False)
app.MainLoop()
