import wx
import wx.lib.newevent
import json
import os

from gcframe import GcFrame
from flframe import FlFrame
from statframe import StatFrame
from thermframe import ThermalFrame
from tempgraph import TempGraph
from fanframe import FanFrame
from manualgcframe import ManualGCodeFrame
from moonraker import Moonraker, MoonrakerException
from listdlg import ListDlg
from images import Images
from jogdlg import JogDlg

(WSDeliveryEvent, EVT_WSDELIVERY) = wx.lib.newevent.NewEvent()
(WSConnectEvent, EVT_WSCONNECT) = wx.lib.newevent.NewEvent()
(WSDisconnectEvent, EVT_WSDISCONNECT) = wx.lib.newevent.NewEvent()
(WSErrorEvent, EVT_WSERROR) = wx.lib.newevent.NewEvent()

BTNSZ = (120, 50)

MENU_VIEW_LOG = 1100
MENU_VIEW_GCODE = 1101
MENU_MACROS_BASE = 1200
MENU_TOOLS_BACKUP_CONFIG = 1300
MENU_TOOLS_BLTOUCH = 1310
MENU_TOOLS_BLTOUCH_DOWN = 1311
MENU_TOOLS_BLTOUCH_UP = 1312
MENU_TOOLS_BLTOUCH_SELF_TEST = 1313
MENU_TOOLS_BLTOUCH_RESET = 1314


class PrinterFrame(wx.Frame):
	def __init__(self, name, settings, cbmap):
		wx.Frame.__init__(self, None, title="Klipper Monitor - %s" % name)
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.closing = False
		self.Bind(wx.EVT_CLOSE, self.onClose)

		self.images = Images()

		self.initialized = False
		self.moonraker = None
		self.connectionId = None
		self.ws = None

		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(name)
		self.tempGraph = None
		self.CanExtrude = False

		self.fanList = []
		self.heaterList = []
		self.sensorList = []
		self.objectStatus = {}
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)

		self.ip = self.psettings["ip"]
		self.port = str(self.psettings["port"])
		self.name = name
		self.closer = cbmap["closer"]
		self.notifyInitialized = cbmap["init"]
		self.baseUrl = "http://%s" % self.ip

		self.Bind(EVT_WSDELIVERY, self.onWSDeliveryEvent)
		self.Bind(EVT_WSDISCONNECT, self.onWSDisconnectEvent)
		self.Bind(EVT_WSCONNECT, self.onWSConnectEvent)
		self.Bind(EVT_WSERROR, self.onWSErrorEvent)

		self.fanList = sorted(list(self.psettings["fans"].keys()))
		self.heaterList = sorted(list(self.psettings["heaters"].keys()))
		self.sensorList = sorted(list(self.psettings["sensors"].keys()))
		try:
			self.outputList = sorted(list(self.psettings["outputs"].keys()))
		except KeyError:
			self.outputList = []

		self.statFrame = StatFrame(self, self.name, self.settings)
		self.gcFrame = GcFrame(self, self.name, self.settings)
		self.flFrame = FlFrame(self, self.name, self.settings)
		self.thermFrame = ThermalFrame(self, self.name, self.settings)
		self.tempGraph = TempGraph(self, self.name, self.settings)
		self.fanFrame = FanFrame(self, self.name, self.settings, self.fanList+self.outputList)
		self.manualFrame = ManualGCodeFrame(self, self.name, self.settings)

		menuBar = wx.MenuBar()

		menu = wx.Menu()
		menu.Append(MENU_VIEW_LOG, "Log", "Hide/Show the Log Screen")
		self.Bind(wx.EVT_MENU, self.OnBLog, id=MENU_VIEW_LOG)
		menu.Append(MENU_VIEW_GCODE, "GCode", "Hide/Show the GCode Screen")
		self.Bind(wx.EVT_MENU, self.OnBGCode, id=MENU_VIEW_GCODE)
		menuBar.Append(menu, "View")

		self.macroMap = {}
		if "macros" in self.psettings:
			menu = wx.Menu()
			ix = 0
			for label, macro in self.psettings["macros"].items():
				id = MENU_MACROS_BASE + ix
				ix += 1
				menu.Append(id, label)
				self.Bind(wx.EVT_MENU, self.OnMenuMacro, id=id)
				self.macroMap[id] = macro
			menuBar.Append(menu, "Macros")

		menu = wx.Menu()
		menu.Append(MENU_TOOLS_BACKUP_CONFIG, "Backup Config", "Backup printer configuration files")
		self.Bind(wx.EVT_MENU, self.OnMenuBackupConfig, id=MENU_TOOLS_BACKUP_CONFIG)
		try:
			hasBlTouch = self.psettings["hasbltouch"]
		except KeyError:
			hasBlTouch = False

		if hasBlTouch:
			submenu = wx.Menu()
			submenu.Append(MENU_TOOLS_BLTOUCH_DOWN, "Pin Down", "Lower the BL Touch pin")
			self.Bind(wx.EVT_MENU, self.OnMenuBLTouchDown, id=MENU_TOOLS_BLTOUCH_DOWN)
			submenu.Append(MENU_TOOLS_BLTOUCH_UP, "Pin Up", "Raise the BL Touch pin")
			self.Bind(wx.EVT_MENU, self.OnMenuBLTouchUp, id=MENU_TOOLS_BLTOUCH_UP)
			submenu.Append(MENU_TOOLS_BLTOUCH_SELF_TEST, "Self Test", "Run BL Touch Self Test")
			self.Bind(wx.EVT_MENU, self.OnMenuBLTouchSelfTest, id=MENU_TOOLS_BLTOUCH_SELF_TEST)
			submenu.Append(MENU_TOOLS_BLTOUCH_RESET, "Reset", "Reset the BL Touch")
			self.Bind(wx.EVT_MENU, self.OnMenuBLTouchReset, id=MENU_TOOLS_BLTOUCH_RESET)
			menu.Append(MENU_TOOLS_BLTOUCH, "BLTouch", submenu)

		menuBar.Append(menu, "Tools")

		self.SetMenuBar(menuBar)

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(20)

		hsz = wx.BoxSizer(wx.HORIZONTAL)
		hsz.AddSpacer(20)
		vsz2 = wx.BoxSizer(wx.VERTICAL)
		vsz2.Add(self.statFrame, 0, wx.ALIGN_CENTER_HORIZONTAL)
		vsz2.AddSpacer(10)
		vsz2.Add(self.thermFrame, 0, wx.ALIGN_CENTER_HORIZONTAL)
		vsz2.AddSpacer(10)
		vsz2.Add(self.tempGraph, 0, wx.ALIGN_CENTER_HORIZONTAL)
		hsz.Add(vsz2)
		hsz.AddSpacer(10)
		vsz2 = wx.BoxSizer(wx.VERTICAL)
		vsz2.Add(self.gcFrame)
		vsz2.AddSpacer(10)
		vsz2.Add(self.fanFrame)
		vsz2.AddSpacer(10)
		vsz2.Add(self.manualFrame, 0, wx.EXPAND)
		hsz.Add(vsz2)

		vsz3 = wx.BoxSizer(wx.VERTICAL)
		vsz3.Add(self.flFrame)
		vsz3.AddSpacer(340)

		bszr = wx.BoxSizer(wx.HORIZONTAL)
		self.bEStop = wx.Button(self, wx.ID_ANY, "ESTOP", size=(64, 64))
		self.bEStop.SetBackgroundColour(wx.Colour((255, 0, 0)))
		self.bEStop.SetForegroundColour(wx.Colour((0, 0, 0)))
		self.bEStop.Enable(False)
		self.Bind(wx.EVT_BUTTON, self.OnBEStop, self.bEStop)
		bszr.Add(self.bEStop)
		vsz3.Add(bszr, 0, wx.ALIGN_RIGHT)

		hsz.AddSpacer(20)
		hsz.Add(vsz3)
		hsz.AddSpacer(20)

		vsz.Add(hsz)
		vsz.AddSpacer(20)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

		self.Show()

		self.dlgLog = ListDlg(self, "Log", [], self.HideLog)
		self.dlgLog.Show()

		self.dlgGCode = ListDlg(self, "GCode Response", [], self.HideGCode, True)
		self.dlgGCode.Hide()

		self.dlgJog = JogDlg(self, self.name, self.settings, self.images, self.HideJog)
		self.dlgJog.Hide()

		wx.CallAfter(self.Initialize)

	def HideLog(self):
		self.dlgLog.Hide()

	def ShowLog(self):
		self.dlgLog.Show()

	def OnBLog(self, evt):
		if self.dlgLog.IsShown():
			self.HideLog()
		else:
			self.ShowLog()

	def LogItem(self, msg):
		self.dlgLog.AddItem(msg)

	def HideGCode(self):
		self.dlgGCode.Hide()

	def ShowGCode(self):
		self.dlgGCode.Show()

	def AddGCode(self, msg):
		self.dlgGCode.AddItem(msg)

	def OnBGCode(self, evt):
		if self.dlgGCode.IsShown():
			self.HideGCode()
		else:
			self.ShowGCode()

	def HideJog(self):
		print("hide jog")
		self.dlgJog.Hide()

	def ShowJog(self):
		print("show jog")
		self.dlgJog.Show()

	def OnBJog(self):
		if self.dlgJog.IsShown():
			self.HideJog()
		else:
			self.ShowJog()

	def OnMenuMacro(self, evt):
		idx = evt.GetId()
		try:
			macro = self.macroMap[idx]
		except KeyError:
			print("unknown macro")
			return

		self.moonraker.SendGCode(macro)

	def OnMenuBackupConfig(self, evt):
		dlg = wx.DirDialog(self, "Choose an output directory:", style=wx.DD_DEFAULT_STYLE)
		rc = dlg.ShowModal()
		if rc == wx.ID_OK:
			backupPath = dlg.GetPath()

		dlg.Destroy()
		if rc != wx.ID_OK:
			return

		fl = self.moonraker.FilesList(root="config")
		fList = [f["path"] for f in fl if not f["path"].lower().endswith("bkp")]
		for fn in fList:
			self.LogItem("Downloading file %s..." % fn)
			try:
				fd = self.moonraker.FileDownload(fn, root="config")
			except MoonrakerException as e:
				dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()
				continue

			cfn = os.path.join(backupPath, fn)
			with open(cfn, "wb") as cfp:
				cfp.write(fd.content)
		self.LogItem("Configuration backup completed")

	def OnMenuBLTouchDown(self, evt):
		self.moonraker.SendGCode("BLTOUCH_DEBUG COMMAND=pin_down")

	def OnMenuBLTouchUp(self, evt):
		self.moonraker.SendGCode("BLTOUCH_DEBUG COMMAND=pin_up")

	def OnMenuBLTouchSelfTest(self, evt):
		self.moonraker.SendGCode("BLTOUCH_DEBUG COMMAND=self_test")

	def OnMenuBLTouchReset(self, evt):
		self.moonraker.SendGCode("BLTOUCH_DEBUG COMMAND=reset")

	def Initialize(self):
		self.initialized = False
		self.closing = False
		self.LogItem("Creating web socket to printer %s" % self.name)
		self.moonraker = Moonraker(self, self.ip, self.port, self.name)

		rmp = {
			"message": self.WSMessage,
			"connect": self.WSConnect,
			"disconnect": self.WSDisconnect,
			"error": self.WSError
		}

		self.moonraker.start(rmp)

	def GetMeta(self, fn):
		return self.flFrame.GetMeta(fn)

	def LoadCurrentGCode(self):
		self.gcFrame.OpenCurrent()

	def EnableJogging(self, movement, extrusion):
		self.dlgJog.enableMovementControls(movement)
		self.dlgJog.enableExtrusionControls(extrusion and self.CanExtrude)

	def WSMessage(self, jmsg):
		evt = WSDeliveryEvent(data=jmsg)
		wx.QueueEvent(self, evt)

	def WSConnect(self, ws):
		evt = WSConnectEvent(data=ws)
		wx.QueueEvent(self, evt)

	def WSDisconnect(self, status, msg):
		evt = WSDisconnectEvent(data=msg)
		wx.QueueEvent(self, evt)

	def WSError(self, status, msg):
		evt = WSErrorEvent(data=msg)
		wx.QueueEvent(self, evt)

	def onWSDeliveryEvent(self, evt):
		jmsg = evt.data
		try:
			method = jmsg["method"]
		except KeyError:
			try:
				cid = jmsg["result"]["connection_id"]
			except KeyError:
				self.LogItem("Unknown message: %s" % str(jmsg))
				return

			self.connectionId = cid
			self.LogItem("Received connectionId: %d" % cid)
			self.WaitForKlipperReady()
			return

		if method == "notify_proc_stat_update":
			# print("notify proc state update")
			# print(json.dumps(jmsg))
			# print("=========================================")
			pass

		elif method == "notify_status_update":
			try:
				plist = jmsg["params"]
			except KeyError:
				return

			for p in plist:
				if isinstance(p, dict):
					self.gcFrame.UpdateStatus(p)
					self.flFrame.UpdateStatus(p)
					self.statFrame.UpdateStatus(p)
					self.thermFrame.UpdateStatus(p)
					self.fanFrame.UpdateStatus(p)
					try:
						c = p["extruder"]["can_extrude"]
					except KeyError:
						c = self.CanExtrude

					if c != self.CanExtrude:
						self.CanExtrude = c
						self.dlgJog.SetCanExtrude(self.CanExtrude)
						self.LogItem("Extrusion is now %s" % ("enabled." if c else "disabled."))

					self.bEStop.Enable(self.statFrame.GetState() == "printing")

		elif method == "notify_filelist_changed":
			self.flFrame.RefreshFilesList()
			if not self.flFrame.HasCurrentFile():
				self.moonraker.ClearFile()

		elif method == "notify_klippy_shutdown":
			if not self.closing:
				self.LogItem("klippy shutdown: %s" % str(jmsg))
				self.moonraker.close() # trigger a reconnection attempt
				self.timer.Stop()

		elif method in "notify_gcode_response":
			try:
				msgl = jmsg["params"]
			except KeyError:
				return

			try:
				for msg in msgl:
					if not msg.startswith("B:"):
						self.AddGCode(msg)
			except Exception as e:
				self.LogItem("EXCEPTION %s MESSAGE: %s" % (str(e), str(msgl)))

		else:
			if method in ["notify_history_changed", "notify_service_state_changed"]:
				return
			self.LogItem("unknown method: (%s)" % method)

	def WaitForKlipperReady(self, retry=0):
		if retry > 3:
			self.LogItem("Too many retries")
			self.close()
			return

		self.LogItem("Retrieve klipper status %s" % ("retry %d" % retry if retry > 0 else ""))
		try:
			si = self.moonraker.ServerInfo()
		except MoonrakerException as e:
			self.LogItem(e.message)
			self.close()
			raise
		try:
			kstat = si["result"]["klippy_state"]
		except KeyError:
			self.LogItem("Unable to parse system info message")
			self.close()
			return

		if kstat == "ready":
			self.LogItem("klipper ready")
			self.SubscribeToPrinterObjects()
		elif kstat in ["shutdown", "error"]:
			try:
				pi = self.moonraker.PrinterInfo()
			except MoonrakerException as e:
				self.LogItem(e.message)
				self.close()
				return
			try:
				msg = pi["result"]["state_message"]
			except KeyError:
				msg = "Klipper status: %s" % kstat
			self.LogItem("%s.  Unable to proceed" % msg)
			self.close()
		elif kstat == "startup":
			self.LogItem("klipper in startup state - retry after 2 seconds")
			wx.CallLater(2000, self.WaitForKlipperReady, retry+1)
		else:
			self.LogItem("Unknown klipper state: %s" % kstat)
			self.close()

	def SubscribeToPrinterObjects(self):
		# try:
		# 	objList = self.moonraker.PrinterObjectsList()
		# except MoonrakerException as e:
		# 	dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
		# 	dlg.ShowModal()
		# 	dlg.Destroy()
		# 	objList = None
		#
		# if objList is None:
		# 	self.LogItem("Unable to obtain object list")
		# else:
		# 	self.LogItem("Known objects:")
		# 	for o in sorted(objList):
		# 		self.LogItem("    %s" % o)
		# 	self.LogItem("End of known objects")

		subList = (self.fanList + self.heaterList + self.sensorList + self.outputList +
			["toolhead", "print_stats", "gcode_move"])
		self.LogItem("subscribing for following objects:")
		for o in sorted(subList):
			self.LogItem("    %s" % o)
		self.LogItem("End of subscribed objects")
		try:
			sub = self.moonraker.PrinterObjectSubscribe(subList, self.connectionId)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			self.notifyInitialized(False, self.name)
			return

		status = sub["result"]["status"]
		for obj in subList:
			self.objectStatus[obj] = status[obj].copy()
		try:
			temps = self.moonraker.PrinterCachedTemps()
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			self.notifyInitialized(False, self.name)
			return

		self.thermFrame.SetHeaters(self.heaterList)
		self.thermFrame.SetSensors(self.sensorList)
		self.thermFrame.SetInitialValues(temps)
		self.tempGraph.initPlot(self.thermFrame.GetSensorMap(), self.thermFrame.GetHeaterMap())

		try:
			stat = self.moonraker.PrinterObjectStatus(subList)
		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			self.notifyInitialized(False, self.name)
			return

		ivals = stat["result"]["status"]

		self.gcFrame.SetMoonraker(self.moonraker)
		self.thermFrame.SetMoonraker(self.moonraker)
		self.flFrame.SetMoonraker(self.moonraker)
		self.statFrame.SetMoonraker(self.moonraker)
		self.fanFrame.SetMoonraker(self.moonraker)
		self.manualFrame.SetMoonraker(self.moonraker)
		self.dlgJog.SetMoonraker(self.moonraker)

		self.gcFrame.SetInitialValues(ivals)
		self.flFrame.SetInitialValues(ivals)
		self.statFrame.SetInitialValues(ivals)
		self.fanFrame.SetInitialValues(ivals)

		try:
			c = ivals["extruder"]["can_extrude"]
			self.CanExtrude = c
		except KeyError:
			pass

		self.dlgJog.SetCanExtrude(self.CanExtrude)

		self.notifyInitialized(True, self.name)
		self.timer.Start(1000)

	def onTimer(self, evt):
		try:
			js = self.moonraker.PrinterJobStatus()

		except MoonrakerException as e:
			dlg = wx.MessageDialog(self, e.message, "Moonraker error", wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
			return

		try:
			active = js["result"]["status"]["virtual_sdcard"]["is_active"]
		except KeyError:
			active = False

		try:
			pos = js["result"]["status"]["virtual_sdcard"]["file_position"]
		except KeyError:
			pos = 0

		try:
			prog = js["result"]["status"]["virtual_sdcard"]["progress"]
		except KeyError:
			prog = 0.0

		try:
			fn = js["result"]["status"]["virtual_sdcard"]["file_path"]
		except KeyError:
			dlg = wx.MessageDialog(self, "Unable to parse job status report", "Printer error", wx.OK | wx.ICON_INFORMATION)
			dlg.ShowModal()
			dlg.Destroy()
			return

		if fn is not None:
			fn = os.path.basename(fn)

		self.gcFrame.setJobStatus(active, fn, pos, prog)
		self.statFrame.setJobStatus(active, fn, pos, prog)
		self.flFrame.setJobStatus(active, fn, pos, prog)

		# check here if fn is in the filelist

		if fn is not None:
			if not self.flFrame.HasCurrentFile():
				self.moonraker.ClearFile()

		self.gcFrame.Ticker()
		self.statFrame.Ticker()
		self.thermFrame.Ticker()

		if self.tempGraph is not None:
			try:
				self.tempGraph.draw()
			except RuntimeError:
				self.tempGraph = None

	def onWSConnectEvent(self, evt):
		self.LogItem("requesting connection ID")
		self.ws = evt.data
		clientID = {
			"jsonrpc": "2.0",
			"method": "server.connection.identify",
			"params": {
				"client_name": "klipmon",
				"version": "0.1",
				"url": self.baseUrl,
				"type": "desktop"
			},
			"id": 1508
		}
		self.ws.send(json.dumps(clientID))

	def onWSDisconnectEvent(self, evt):
		self.gcFrame.SetMoonraker(None)
		self.LogItem("Websocket disconnected: %s" % evt.data)
		wx.CallLater(3000, self.ReConnect)

	def ReConnect(self):
		self.moonraker.SendGCode("FIRMWARE_RESTART")
		wx.CallLater(3000, self.Initialize)

	def onWSErrorEvent(self, evt):
		self.LogItem("websocket error: %s" % evt.data)
		if not self.initialized:
			self.close()

	def OnBEStop(self, evt):
		dlg = wx.MessageDialog(self, "Are you sure you want to Emergency Stop?\nPress \"Yes\" to proceed",
							   "Emergency Stop Confirmation", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
		rc = dlg.ShowModal()
		dlg.Destroy()
		if rc == wx.ID_NO:
			return

		self.moonraker.EmergencyStop()

	def onClose(self, evt):
		self.close()

	def close(self):
		if self.closing:
			return
		self.closing = True

		try:
			self.timer.Stop()
		except:
			pass

		try:
			self.moonraker.close()
		except:
			pass

		self.gcFrame.close()

		try:
			self.dlgLog.Destroy()
		except:
			pass

		try:
			self.dlgGCode.Destroy()
		except:
			pass

		try:
			self.dlgJog.Destroy()
		except:
			pass

		self.closer(self.name)
		self.Destroy()
