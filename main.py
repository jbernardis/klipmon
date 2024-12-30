import wx
from settings import Settings
from printer import PrinterFrame


class App(wx.App):

	def NotifyInit(self, flag, name):
		if not flag:
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
			"closer": self.ClosePrinter,
			"init": self.NotifyInit
		}
		self.frame = PrinterFrame("voron", settings, cbMap)
		return True


app = App(False)
app.MainLoop()
