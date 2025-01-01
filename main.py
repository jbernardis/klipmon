import wx
import sys
import getopt
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
		try:
			opts, _ = getopt.getopt(sys.argv[1:], "", ["dbot", "voron"])
		except getopt.GetoptError:
			print('Invalid command line arguments')
			return False

		pname = None

		for opt, _ in opts:
			if opt == "--dbot":
				pname = "dbot"
			elif opt == "--voron":
				pname = "voron"
			else:
				print("Invalid command line argument: %s" % opt)
				return False

		settings = Settings()
		cbMap = {
			"closer": self.ClosePrinter,
			"init": self.NotifyInit
		}
		if pname is None:
			print("No printer name specified")
			return False

		print("pname = %s" % pname)
		self.frame = PrinterFrame(pname, settings, cbMap)
		return True


app = App(False)
app.MainLoop()
