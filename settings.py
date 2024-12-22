import json
import os
import sys
import getopt

INIFILE = "klipmon.json"


class Settings:
	def __init__(self):
		self.datafolder = os.getcwd()
		self.inifile = os.path.join(self.datafolder, INIFILE)

		with open(self.inifile, "r") as jfp:
			self.data = json.load(jfp)

	def GetSetting(self, name):
		try:
			return self.data[name]
		except KeyError:
			return None

	def GetPrinters(self):
		return sorted(list(self.data["printers"].keys()))

	def GetPrinterSettings(self, pn):
		try:
			return self.data["printers"][pn]
		except KeyError:
			return None

	def GetPrinterGCodeSettings(self, pn):
		try:
			return self.data["printers"][pn]["gcode"]
		except KeyError:
			return None

