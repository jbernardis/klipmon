import wx
import sys
import getopt
from settings import Settings
from printer import PrinterFrame


class App(wx.App):
	def ClosePrinter(self, rc):
		if not rc:
			logtext = self.frame.GetLogText()
			logmsg = logtext.split("\n")[-1]
			dlg = wx.MessageDialog(self.frame, logmsg, "Error closing printer %s" % self.pname, wx.OK)
			dlg.ShowModal()
			dlg.Destroy()

		self.frame.Hide()
		self.frame.Destroy()

	def OnInit(self):
		try:
			opts, _ = getopt.getopt(sys.argv[1:], "", ["dbot", "voron"])
		except getopt.GetoptError:
			print('Invalid command line arguments')
			return False

		self.pname = None

		for opt, _ in opts:
			if opt == "--dbot":
				self.pname = "dbot"
			elif opt == "--voron":
				self.pname = "voron"
			else:
				print("Invalid command line argument: %s" % opt)
				return False

		settings = Settings()
		if self.pname is None:
			print("No printer name specified")
			return False

		self.frame = PrinterFrame(self.pname, settings, self.ClosePrinter)
		return True


app = App(False)
app.MainLoop()
