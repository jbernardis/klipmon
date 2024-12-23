import wx
import wx.lib.newevent
import json
import os
from subprocess import Popen

from gcframe import GcFrame
from flframe import FlFrame
from statframe import StatFrame
from thermframe import ThermalFrame
from tempgraph import TempGraph
from thermaldlg import ThermalDlg
from fanframe import FanFrame
from moonraker import Moonraker, MoonrakerException

(WSDeliveryEvent, EVT_WSDELIVERY) = wx.lib.newevent.NewEvent()
(WSConnectEvent, EVT_WSCONNECT) = wx.lib.newevent.NewEvent()
(WSDisconnectEvent, EVT_WSDISCONNECT) = wx.lib.newevent.NewEvent()
(WSErrorEvent, EVT_WSERROR) = wx.lib.newevent.NewEvent()

BTNSZ = (120, 50)


class PrinterFrame(wx.Frame):
	def __init__(self, name, settings, cbmap):
		wx.Frame.__init__(self, None, title="Klipper Monitor - %s" % name)
		self.SetBackgroundColour(wx.Colour(128, 128, 128))
		self.SetForegroundColour(wx.Colour(0, 0, 0))
		self.closing = False
		self.Bind(wx.EVT_CLOSE, self.onClose)

		self.initialized = False
		self.moonraker = None
		self.connectionId = None
		self.ws = None

		self.settings = settings
		self.psettings = self.settings.GetPrinterSettings(name)
		self.tempGraph = None

		self.prMplayer = None
		self.mplayer = self.settings.GetSetting("mplayer")

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
		self.statusUpdater = cbmap["status"]
		self.notifyInitialized = cbmap["init"]
		self.baseUrl = "http://%s" % self.ip

		self.Bind(EVT_WSDELIVERY, self.onWSDeliveryEvent)
		self.Bind(EVT_WSDISCONNECT, self.onWSDisconnectEvent)
		self.Bind(EVT_WSCONNECT, self.onWSConnectEvent)
		self.Bind(EVT_WSERROR, self.onWSErrorEvent)

		self.fanList = sorted(list(self.psettings["fans"].keys()))
		self.heaterList = sorted(list(self.psettings["heaters"].keys()))
		self.sensorList = sorted(list(self.psettings["sensors"].keys()))

		self.statFrame = StatFrame(self, self.name, self.psettings)
		self.gcFrame = GcFrame(self, self.name, self.psettings)
		self.flFrame = FlFrame(self, self.name, self.psettings)
		self.thermFrame = ThermalFrame(self, self.name, self.psettings)
		self.tempGraph = TempGraph(self, self.name, self.psettings)
		self.fanFrame = FanFrame(self, self.name, self.psettings, self.fanList)

		vsz = wx.BoxSizer(wx.VERTICAL)
		vsz.AddSpacer(20)
		btnsz = wx.BoxSizer(wx.HORIZONTAL)
		btnsz.AddSpacer(20)

		self.bThermals = wx.Button(self, wx.ID_ANY, "Thermals", size=BTNSZ)
		self.bThermals.SetBackgroundColour(wx.Colour(196, 196, 196))
		self.Bind(wx.EVT_BUTTON, self.onBThermals, self.bThermals)
		btnsz.Add(self.bThermals)
		btnsz.AddSpacer(20)

		self.bJogging = wx.Button(self, wx.ID_ANY, "Jogging", size=BTNSZ)
		self.bJogging.SetBackgroundColour(wx.Colour(196, 196, 196))
		self.Bind(wx.EVT_BUTTON, self.onBJogging, self.bJogging)
		btnsz.Add(self.bJogging)
		btnsz.AddSpacer(20)

		self.bVideo = wx.Button(self, wx.ID_ANY, "Video", size=BTNSZ)
		self.bVideo.SetBackgroundColour(wx.Colour(196, 196, 196))
		self.bVideo.Enable(self.mplayer is  not None)
		self.Bind(wx.EVT_BUTTON, self.onBVideo, self.bVideo)
		btnsz.Add(self.bVideo)

		vsz.Add(btnsz)
		vsz.AddSpacer(10)

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
		vsz2.AddSpacer(20)
		vsz2.Add(self.fanFrame)
		hsz.Add(vsz2)
		hsz.AddSpacer(20)
		hsz.Add(self.flFrame)
		hsz.AddSpacer(20)

		vsz.Add(hsz)
		vsz.AddSpacer(20)

		self.SetSizer(vsz)
		self.Layout()
		self.Fit()

		wx.CallAfter(self.Initialize)

	def Initialize(self):
		self.initialized = False
		self.statusUpdater("Creating web socket to printer %s" % self.name)
		self.moonraker = Moonraker(self.ip, self.port, self.name)

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
				print("Unknown message: %s" % str(jmsg))
				return

			self.connectionId = cid
			self.statusUpdater("Received connectionId: %d" % cid)
			self.WaitForKlipperReady()
			return

		if method == "notify_proc_stat_update":
			#print("notify proc state update")
			#print(json.dumps(jmsg))
			#print("=========================================")
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

		elif method == "notify_filelist_changed":
			self.flFrame.RefreshFilesList()

		else:
			if method in ["notify_gcode_response", "notify_history_changed"]:
				return
			print("unknown method: (%s)" % method)
			print(json.dumps(jmsg))
			print("=========================================")

	def WaitForKlipperReady(self, retry=0):
		if retry > 3:
			self.statusUpdater("Too many retries")
			self.close()
			return

		self.statusUpdater("Retrieve klipper status %s" % ("retry %d" % retry if retry > 0 else ""))
		try:
			si = self.moonraker.ServerInfo()
		except MoonrakerException as e:
			self.statusUpdater(e.message)
			self.close()
			raise

		try:
			kstat = si["result"]["klippy_state"]
		except KeyError:
			self.statusUpdater("Unable to parse system info message")
			self.close()
			return

		if kstat == "ready":
			self.statusUpdater("klipper ready")
			self.SubscribeToPrinterObjects()
		elif kstat in ["shutdown", "error"]:
			# get better error message here
			self.statusUpdater("Klipper status: %s.  Unable to proceed" % kstat)
			self.close()
		elif kstat == "startup":
			self.statusUpdater("klipper in startup state - retry after 2 seconds")
			wx.CallLater(2000, self.WaitForKlipperReady, retry+1)
		else:
			self.statusUpdater("Unknown klipper state: %s" % kstat)
			self.close()

	def SubscribeToPrinterObjects(self):
		subList = self.fanList + self.heaterList + self.sensorList + ["toolhead", "print_stats"]
		self.statusUpdater("subscribing for following objects: %s" % ", ".join(subList))
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
		self.flFrame.SetMoonraker(self.moonraker)
		self.statFrame.SetMoonraker(self.moonraker)
		self.fanFrame.SetMoonraker(self.moonraker)

		self.gcFrame.SetInitialValues(ivals)
		self.flFrame.SetInitialValues(ivals)
		self.statFrame.SetInitialValues(ivals)
		self.fanFrame.SetInitialValues(ivals)

		self.notifyInitialized(True, self.name)
		self.timer.Start(1000)

	def onTimer(self, evt):
		if self.prMplayer is not None:
			if self.prMplayer.poll() is not None:
				self.prMplayer = None

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

		self.statFrame.Ticker()
		self.thermFrame.Ticker()

		if self.tempGraph is not None:
			try:
				self.tempGraph.draw()
			except RuntimeError:
				self.tempGraph = None

	def onWSConnectEvent(self, evt):
		self.statusUpdater("requesting connection ID")
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
		self.statusUpdater("Websocket disconnected: %s" % evt.data)
		self.close()

	def onWSErrorEvent(self, evt):
		self.statusUpdater("websocket error: %s" % evt.data)
		if not self.initialized:
			self.close()

	def onBThermals(self, evt):
		dlg = ThermalDlg(self, self.name, self.settings, self.moonraker)
		dlg.Show()

	def onBJogging(self, evt):
		print("jogging")

	def onBVideo(self, evt):
		if self.prMplayer is None:
			url = "http://" + self.ip + "/webcam?action=stream"
			self.prMplayer = Popen([self.mplayer, "-loglevel", "quiet", url])
		else:
			self.prMplayer.kill()
			self.prMplayer = None

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

		if self.prMplayer is not None:
			try:
				self.prMplayer.kill()
			except:
				pass

		self.closer(self.name)
		self.Destroy()
