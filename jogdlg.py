import os
import wx

from moonraker import MoonrakerException
from imagemap import ImageMap

imageMapXY = [[10, 10, 50, 50, "HX"], [201, 192, 239, 230, "HY"], [201, 10, 239, 50, "HZ"], [10, 192, 50, 230, "HA"],
			  [216, 86, 235, 156, "X+4"], [193, 86, 212, 156, "X+3"], [168, 86, 190, 156, "X+2"],
			  [143, 104, 164, 136, "X+1"],
			  [83, 104, 105, 136, "X-1"], [58, 86, 79, 156, "X-2"], [33, 86, 56, 156, "X-3"], [11, 86, 29, 156, "X-4"],
			  [98, 214, 152, 231, "Y-4"], [98, 188, 152, 209, "Y-3"], [98, 163, 152, 185, "Y-2"],
			  [110, 139, 140, 161, "Y-1"],
			  [110, 79, 140, 101, "Y+1"], [98, 53, 152, 78, "Y+2"], [98, 28, 152, 52, "Y+3"], [98, 7, 152, 27, "Y+4"]]

imageMapZ = [[11, 39, 47, 62, "Z+3"], [11, 67, 47, 88, "Z+2"], [11, 91, 47, 109, "Z+1"],
			 [11, 126, 47, 145, "Z-1"], [11, 148, 47, 170, "Z-2"], [11, 172, 47, 197, "Z-3"]]

imageMapE = [[11, 10, 46, 46, "Retr"], [11, 93, 46, 129, "Extr"]]


class JogDlg(wx.Frame):
	def __init__(self, parent, pname, settings, images, dlgExit):
		wx.Frame.__init__(self, parent, wx.ID_ANY, "Jogging")
		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self.SetBackgroundColour("white")

		self.parent = parent
		self.moonraker = None
		self.pname = pname
		self.settings = settings
		self.images = images
		self.dlgExit = dlgExit

		self.movementEnabled = True
		self.extrusionEnabled = True
		self.CanExtrude = False
		self.ColdExtrusionEnabled = False

		self.xySpeed = self.settings.GetPrinterSetting(pname, "xyspeed", 300)
		self.zSpeed = self.settings.GetPrinterSetting(pname, "zspeed", 300)
		self.eSpeed = self.settings.GetPrinterSetting(pname, "espeed", 300)
		self.eLength = self.settings.GetPrinterSetting(pname, "elength", 5)

		self.movementEnabled = True

		jogsz = wx.BoxSizer(wx.VERTICAL)
		lbFont = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

		h = wx.BoxSizer(wx.HORIZONTAL)
		self.axesXY = ImageMap(self, self.images.pngControl_xy)
		self.axesXY.SetToolTip("Move X/Y axes")
		self.axesXY.setHotSpots(self.onImageClickXY, imageMapXY)
		self.axisZ = ImageMap(self, self.images.pngControl_z)
		self.axisZ.SetToolTip("Move Z axis")
		self.axisZ.setHotSpots(self.onImageClickZ, imageMapZ)

		h.Add(self.axesXY)
		h.Add(self.axisZ)

		jogsz.Add(h)

		h = wx.BoxSizer(wx.HORIZONTAL)
		h.AddSpacer(10)

		self.scXYSpeed = wx.SpinCtrl(self, wx.ID_ANY, "",
				size=(120 if os.name == 'posix' else 70, -1), style=wx.ALIGN_RIGHT)
		self.scXYSpeed.SetFont(lbFont)
		self.scXYSpeed.SetRange(10, 1800)
		self.scXYSpeed.SetValue(self.xySpeed)
		self.Bind(wx.EVT_SPINCTRL, self.onScXYSpeed, self.scXYSpeed)

		self.scZSpeed = wx.SpinCtrl(self, wx.ID_ANY, "",
				size=(120 if os.name == 'posix' else 70, -1), style=wx.ALIGN_RIGHT)
		self.scZSpeed.SetFont(lbFont)
		self.scZSpeed.SetRange(10, 600)
		self.scZSpeed.SetValue(self.zSpeed)
		self.Bind(wx.EVT_SPINCTRL, self.onScZSpeed, self.scZSpeed)

		st = wx.StaticText(self, wx.ID_ANY, "X/Y:")
		st.SetFont(lbFont)
		h.Add(st, 0, wx.TOP, 5)
		h.AddSpacer(5)
		h.Add(self.scXYSpeed)
		st = wx.StaticText(self, wx.ID_ANY, " cm/m")
		st.SetFont(lbFont)
		h.Add(st, 0, wx.TOP, 5)

		h.AddSpacer(10)

		st = wx.StaticText(self, wx.ID_ANY, "Z:")
		st.SetFont(lbFont)
		h.Add(st, 0, wx.TOP, 5)
		h.AddSpacer(5)
		h.Add(self.scZSpeed)
		st = wx.StaticText(self, wx.ID_ANY, " cm/m")
		st.SetFont(lbFont)
		h.Add(st, 0, wx.TOP, 5)
		h.AddSpacer(10)

		jogsz.AddSpacer(5)
		jogsz.Add(h)
		jogsz.AddSpacer(5)

		extsz = wx.BoxSizer(wx.VERTICAL)

		self.axisE = ImageMap(self, self.images.pngControl_e)
		self.axisE.SetToolTip("Extrude/Retract")
		self.axisE.setHotSpots(self.onImageClickE, imageMapE)
		extsz.Add(self.axisE, 4, wx.ALIGN_CENTER)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(5)
		self.scEDist = wx.SpinCtrl(self, wx.ID_ANY, "",
				  size=(120 if os.name == 'posix' else 50, -1), style=wx.ALIGN_RIGHT)
		self.scEDist.SetFont(lbFont)
		self.scEDist.SetRange(1, 100)
		self.scEDist.SetValue(self.eLength)
		self.Bind(wx.EVT_SPINCTRL, self.onScEDist, self.scEDist)
		hsz.Add(self.scEDist, 3)
		hsz.AddSpacer(5)

		st = wx.StaticText(self, wx.ID_ANY, "mm")
		st.SetFont(lbFont)
		hsz.Add(st, 1, wx.TOP, 5)
		hsz.AddSpacer(5)

		extsz.Add(hsz, 1, wx.ALIGN_CENTER)

		self.scESpeed = wx.SpinCtrl(self, wx.ID_ANY, "",
				size=(120 if os.name == 'posix' else 70, -1), style=wx.ALIGN_RIGHT)
		self.scESpeed.SetFont(lbFont)
		self.scESpeed.SetRange(10, 600)
		self.scESpeed.SetValue(self.eSpeed)
		self.Bind(wx.EVT_SPINCTRL, self.onScESpeed, self.scESpeed)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(self, wx.ID_ANY, "E:")
		st.SetFont(lbFont)
		hsz.Add(st, 0, wx.TOP, 5)
		hsz.AddSpacer(5)
		hsz.Add(self.scESpeed)
		st = wx.StaticText(self, wx.ID_ANY, " cm/m")
		st.SetFont(lbFont)
		hsz.Add(st, 0, wx.TOP, 5)
		hsz.AddSpacer(10)
		hsz.AddSpacer(5)
		extsz.Add(hsz, 1, wx.ALIGN_CENTER)

		self.cbColdExt = wx.CheckBox(self, wx.ID_ANY, "Allow Cold")
		self.cbColdExt.SetValue(False)
		self.cbColdExt.SetToolTip("Allow cold extrusion")
		self.cbColdExt.SetFont(lbFont)
		extsz.Add(self.cbColdExt, 1, wx.ALIGN_CENTER)
		self.Bind(wx.EVT_CHECKBOX, self.onCbColdExt, self.cbColdExt)
		extsz.AddSpacer(5)

		dlgsz = wx.BoxSizer(wx.HORIZONTAL)
		dlgsz.Add(jogsz)
		dlgsz.AddSpacer(10)
		dlgsz.Add(extsz)

		dlgsz.Fit(self)
		self.SetSizer(dlgsz)
		self.Fit()
		
	def SetMoonraker(self, mr):
		self.moonraker = mr

	def SetCanExtrude(self, flag):
		self.CanExtrude = flag
		self.enableExtrusionControls(self.CanExtrude)

	def enableManualControls(self, flag=True):
		self.enableMovementControls(flag)
		self.enableExtrusionControls(flag and self.CanExtrude)

	def enableMovementControls(self, flag=True):
		self.axesXY.enableControls(flag)
		self.axisZ.enableControls(flag)
		self.scXYSpeed.Enable(flag)
		self.scZSpeed.Enable(flag)
		self.movementEnabled = flag

	def enableExtrusionControls(self, flag=True):
		if flag and not self.CanExtrude:
			return
		self.axisE.enableControls(flag)
		self.cbColdExt.Enable(True)
		self.scEDist.Enable(True)
		self.extrusionEnabled = flag

	def Jog(self, v, spd):
		cmd = "G0"
		if v[0] != 0:
			cmd += "X%d" % v[0]
		if v[1] != 0:
			cmd += "Y%d" % v[1]
		if v[2] != 0:
			cmd += "Z%d" % v[2]
		cmd += "F%d" % spd

		try:
			self.moonraker.SendGCode("G91")
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		try:
			self.moonraker.SendGCode(cmd)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		try:
			self.moonraker.SendGCode("G90")
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

	def Home(self, v):
		cmd = "G28"
		if v[0]:
			cmd += "X"
		if v[1]:
			cmd += "Y"
		if v[2]:
			cmd += "Z"

		try:
			self.moonraker.SendGCode(cmd, timeout=10)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

	def Extrude(self, el):
		self.DoExtruder(el, self.eSpeed)

	def Retract(self, el):
		self.DoExtruder(-el, self.eSpeed)

	def DoExtruder(self, el, spd):
		cmd = "G1E%dF%d" % (el, spd)
		cmds = ["M83", "G92E0", cmd, "G92E0", "M82"]
		for c in cmds:
			try:
				self.moonraker.SendGCode(c, timeout=10)
			except MoonrakerException as e:
				dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()
				return

	def onImageClickXY(self, command):
		try:
			if command == "HX":
				self.Home([True, False, False])
			elif command == "HY":
				self.Home([False, True, False])
			elif command == "HZ":
				self.Home([False, False, True])
			elif command == "HA":
				self.Home([True, True, True])
			elif command == "Y+1":
				self.Jog([0, 0.1, 0], self.xySpeed)
			elif command == "Y+2":
				self.Jog([0, 1, 0], self.xySpeed)
			elif command == "Y+3":
				self.Jog([0, 10, 0], self.xySpeed)
			elif command == "Y+4":
				self.Jog([0, 100, 0], self.xySpeed)
			elif command == "Y-1":
				self.Jog([0, -0.1, 0], self.xySpeed)
			elif command == "Y-2":
				self.Jog([0, -1, 0], self.xySpeed)
			elif command == "Y-3":
				self.Jog([0, -10, 0], self.xySpeed)
			elif command == "Y-4":
				self.Jog([0, -100, 0], self.xySpeed)
			elif command == "X+1":
				self.Jog([0.1, 0, 0], self.xySpeed)
			elif command == "X+2":
				self.Jog([1, 0, 0], self.xySpeed)
			elif command == "X+3":
				self.Jog([10, 0, 0], self.xySpeed)
			elif command == "X+4":
				self.Jog([100, 0, 0], self.xySpeed)
			elif command == "X-1":
				self.Jog([-0.1, 0, 0], self.xySpeed)
			elif command == "X-2":
				self.Jog([-1, 0, 0], self.xySpeed)
			elif command == "X-3":
				self.Jog([-10, 0, 0], self.xySpeed)
			elif command == "X-4":
				self.Jog([-100, 0, 0], self.xySpeed)

		except:
			dlg = wx.MessageDialog(self, "Error moving X/Y axes",
								   "Job Error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

	def onImageClickZ(self, command):
		try:
			if command == "Z+1":
				self.Jog([0, 0, 0.1], self.zSpeed)
			elif command == "Z+2":
				self.Jog([0, 0, 1], self.zSpeed)
			elif command == "Z+3":
				self.Jog([0, 0, 10], self.zSpeed)
			elif command == "Z+4":
				self.Jog([0, 0, 100], self.zSpeed)
			elif command == "Z-1":
				self.Jog([0, 0, -0.1], self.zSpeed)
			elif command == "Z-2":
				self.Jog([0, 0, -1], self.zSpeed)
			elif command == "Z-3":
				self.Jog([0, 0, -10], self.zSpeed)
			elif command == "Z-4":
				self.Jog([0, 0, -100], self.zSpeed)
		except:
			dlg = wx.MessageDialog(self, "Error moving Z axis",
								   "Job Error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

	def onImageClickE(self, command):
		try:
			if command == "Retr":
				self.Retract(self.eLength)
			elif command == "Extr":
				self.Extrude(self.eLength)
		except:
			dlg = wx.MessageDialog(self, "Error during extrude/retract",
								   "Extrude Error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

	def onScEDist(self, _):
		dist = self.scEDist.GetValue()
		if dist != self.eLength:
			self.eLength = dist
			self.settings.SetPrinterSetting("elength", dist, self.pname)

	def onScXYSpeed(self, _):
		spd = self.scXYSpeed.GetValue()
		if spd != self.xySpeed:
			self.xySpeed = spd
			self.settings.SetPrinterSetting("xyspeed", spd, self.pname)

	def onScZSpeed(self, _):
		spd = self.scZSpeed.GetValue()
		if spd != self.zSpeed:
			self.zSpeed = spd
			self.settings.SetPrinterSetting("zspeed", spd, self.pname)

	def onScESpeed(self, _):
		spd = self.scESpeed.GetValue()
		if spd != self.eSpeed:
			self.eSpeed = spd
			self.settings.SetPrinterSetting("espeed", spd, self.pname)

	def onCbColdExt(self, _):
		if self.cbColdExt.GetValue():
			self.ColdExtrusionEnabled = True
			if not self.CanExtrude:
				self.axisE.enableControls(True)
			self.parent.LogItem("Cold Extrusion Enabled")
			self.parent.AddGCode("Cold Extrusion Enabled")
			try:
				self.moonraker.SendGCode("M302 S0")
			except:
				dlg = wx.MessageDialog(self, "Unable to set for cold extrude",
									   "Printer Error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()
		else:
			self.ColdExtrusionEnabled = False
			if not self.CanExtrude:
				self.axisE.enableControls(False)
			self.parent.LogItem("Cold Extrusion Disabled")
			self.parent.AddGCode("Cold Extrusion Disabled")
			try:
				self.moonraker.SendGCode("M302 S170")
			except:
				dlg = wx.MessageDialog(self, "Unable to clear for cold extrude",
									   "Printer Error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()

	def OnClose(self, evt):
		self.DoClose()

	def DoClose(self):
		self.dlgExit()

