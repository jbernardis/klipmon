import os
import requests
import json
import urllib.parse

from mrclient import Client


def getErrorMessage(p, operation):
	j = p.json()
	try:
		return j["error"]["message"] + " during " + operation
	except KeyError:
		return "HTTP Error %d during %s" % (p.status_code, operation)


class MoonrakerException(Exception):
	def __init__(self, message):
		Exception.__init__(self)
		self.message = message


class Moonraker:
	def __init__(self, parent, ip, port, name):
		self.parent = parent
		self.ip = ip
		self.port = str(port)
		self.name = name
		self.ipString = "http://" + self.ip + ":" + self.port
		self.ipPort = ip + ":" + self.port
		self.baseUrl = "http://%s" % ip
		self.baseUrlPort = "http://%s" % ip + ":" + self.port

		self.mrClient = Client(self.baseUrlPort)
		self.mrSocket = None

		self.messageUpdate = None
		self.errorUpdate = None
		self.connectUpdate = None
		self.disconnectUpdate = None

		self.connectionId = None

		self.session = requests.Session()

	def GetConnectionId(self):
		return self.connectionId

	def start(self, reportMap={}):
		try:
			self.messageUpdate = reportMap["message"]
		except KeyError:
			self.messageUpdate = None

		try:
			self.connectUpdate = reportMap["connect"]
		except KeyError:
			self.connectUpdate = None

		try:
			self.disconnectUpdate = reportMap["disconnect"]
		except KeyError:
			self.disconnectUpdate = None

		try:
			self.errorUpdate = reportMap["error"]
		except KeyError:
			self.errorUpdate = None

		if self.mrSocket is None:
			self.mrSocket = self.mrClient.create_socket(
				on_message=self.onSocketMessage,
				on_open=self.onSocketConnect,
				on_close=self.onSocketDisconnect,
				on_error=self.onSocketError)

	def unsubscribe(self):
		if self.mrSocket:
			self.mrSocket.disconnect()
			if os.name == 'posix':
				try:
					self.mrSocket.wait(1)
				except:
					pass
			else:
				self.mrSocket.wait()

		self.mrSocket = None

	def onSocketError(self, ws, error):
		if callable(self.errorUpdate):
			self.errorUpdate(ws, error)

	def onSocketConnect(self, ws):
		if callable(self.connectUpdate):
			self.connectUpdate(ws)

	def onSocketMessage(self, msg):
		j = json.loads(msg)
		if callable(self.messageUpdate):
			self.messageUpdate(j)

	def onSocketDisconnect(self, ws, status, msg):
		if callable(self.disconnectUpdate):
			self.disconnectUpdate(status, msg)

	def close(self):
		self.unsubscribe()

	def EmergencyStop(self):
		try:
			p = self.session.post(self.ipString + "/printer/emergency_stop", timeout=5.0)

		except requests.exceptions.ReadTimeout:
			return

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer emergency stop")

		if p.status_code >= 400:
			raise MoonrakerException(getErrorMessage(p, "emergency stop"))

		try:
			j = p.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse emergency stop return message as JSON")

		try:
			result = j["result"]
		except KeyError:
			msg = "Unexpected response from emergency stop: %s" % p.text
			raise MoonrakerException(msg)

		if result != "ok":
			msg = "Unexpected response from emergency stop: %s" % p.text
			raise MoonrakerException(msg)

	def ServerInfo(self):
		try:
			r = self.session.get(self.ipString + "/server/info", timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on server info")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send server info request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server info"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			return r.text

	def PrinterInfo(self):
		try:
			r = self.session.get(self.ipString + "/printer/info", timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on printer info")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer info request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "printer info"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			return r.text

	def RootsList(self):
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/server/files/roots", timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on roots list")

		except requests.exceptions.ConnectionError:
			return False, "Unable to send list roots request"

		if r.status_code >= 400:
			msg = getErrorMessage(r, "server files roots")
			return False, msg

		try:
			return True, r.json()
		except json.decoder.JSONDecodeError:
			return True, r.text

	def FilesList(self, root="gcodes"):
		parms = {"root": root}
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/server/files/list", params=parms, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on files list")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to establish connection with printer %s at address %s" % (self.name, self.ipString))

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server files list"))

		try:
			j = r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse return value as JSON")

		try:
			return j["result"]
		except KeyError:
			return []

	def GetGCodeMetaData(self, fn):
		parms = {"filename": fn}
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/server/files/metadata", params=parms, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on server files metadata")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to establish connection with printer %s at address %s" % (self.name, self.ipString))

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server files metadata"))

		try:
			j = r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse return value as JSON")

		try:
			return j["result"]
		except KeyError:
			return []

	def PrinterObjectsList(self):
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/printer/objects/list", timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on printer objects list")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer object list request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "printer objects list"))

		try:
			j = r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Object List return message as JSON")

		try:
			return j["result"]["objects"]
		except KeyError:
			raise MoonrakerException("Object List return message missing result/objects key")

	def PrinterObjectStatus(self, objects):
		objString = "&".join(objects)
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/printer/objects/query?" + objString, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on printer objects query")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer object %s query request" % object)

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "printer objects query"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			return r.text

	def PrinterObjectSubscribe(self, objects, cid):
		objString = "&".join(objects)
		cidString = "%d" % cid
		parms = "connection_id=" + cidString + "&" + objString
		try:
			url = "http://" + self.ip + ":" + self.port + "/printer/objects/subscribe?" + parms
			r = self.session.get(url, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on printer objects subscribe")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer object %s subscribe request" % object)

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "printer objects subscribe"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Object Subscribe return message as JSON")

	def PrinterCachedTemps(self):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/temperature_store?include_monitors=false"
			r = self.session.get(url, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on server temperature_store")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send server temperature_store request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server temperature_store"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Object Status return message as JSON")

	def PrintFile(self, fn):
		url = "http://" + self.ip + ":" + self.port + "/printer/print/start?filename=" + fn
		try:
			p = self.session.post(url, timeout=2.0)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on printer print start")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send print start request")

		if p.status_code >= 400:
			raise MoonrakerException(getErrorMessage(p, "printer print start"))

		try:
			j = p.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse print file return message as JSON")

		try:
			result = j["result"]
		except KeyError:
			msg = "Unexpected response from start print: %s" % p.text
			raise MoonrakerException(msg)

		if result != "ok":
			msg = "Unexpected response from start print: %s" % p.text
			raise MoonrakerException(msg)

	def PrintFilePause(self):
		url = "http://" + self.ip + ":" + self.port + "/printer/print/pause"
		try:
			p = self.session.post(url, timeout=2.0)

		except requests.exceptions.ReadTimeout:
			return

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send print pause request")

		if p.status_code >= 400:
			raise MoonrakerException(getErrorMessage(p, "printer print pause"))

		try:
			j = p.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse print pause return message as JSON")

		try:
			result = j["result"]
		except KeyError:
			msg = "Unexpected response from pause print: %s" % p.text
			raise MoonrakerException(msg)

		if result != "ok":
			msg = "Unexpected response from pause print: %s" % p.text
			raise MoonrakerException(msg)

	def PrintFileResume(self):
		url = "http://" + self.ip + ":" + self.port + "/printer/print/resume"
		try:
			p = self.session.post(url, timeout=2.0)

		except requests.exceptions.ReadTimeout:
			return

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send print resume request")

		if p.status_code >= 400:
			raise MoonrakerException(getErrorMessage(p, "printer print resume"))

		try:
			j = p.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse print resume return message as JSON")

		try:
			result = j["result"]
		except KeyError:
			msg = "Unexpected response from resume print: %s" % p.text
			raise MoonrakerException(msg)

		if result != "ok":
			msg = "Unexpected response from resume print: %s" % p.text
			raise MoonrakerException(msg)

	def PrintFileCancel(self):
		url = "http://" + self.ip + ":" + self.port + "/printer/print/cancel"
		try:
			p = self.session.post(url, timeout=2.0)

		except requests.exceptions.ReadTimeout:
			return

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send print cancel request")

		if p.status_code >= 400:
			raise MoonrakerException(getErrorMessage(p, "printer print cancel"))

		try:
			j = p.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse print cancel return message as JSON")

		try:
			result = j["result"]
		except KeyError:
			msg = "Unexpected response from cancel print: %s" % p.text
			raise MoonrakerException(msg)

		if result != "ok":
			msg = "Unexpected response from cancel print: %s" % p.text
			raise MoonrakerException(msg)

	def ClearFile(self):
		return self.SendGCode("SDCARD_RESET_FILE")

	def SendGCode(self, gcodecmd, timeout=0.7):
		self.parent.AddGCode(">> " + gcodecmd)
		try:
			p = self.session.post("http://" + self.ip + ":" + self.port + "/printer/gcode/script?script=" + urllib.parse.quote(gcodecmd), timeout=timeout)

		except requests.exceptions.ReadTimeout:
			print("read timeout")
			return

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send GCode commands")

		if p.status_code >= 400:
			raise MoonrakerException(getErrorMessage(p, "printer gcode script"))

		try:
			j = p.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse send gcode return message as JSON")

		try:
			result = j["result"]
		except KeyError:
			msg = "Unexpected response from send gcode: %s" % p.text
			print(msg)
			raise MoonrakerException(msg)

		if result != "ok":
			msg = "Unexpected response from send gcode: %s" % p.text
			raise MoonrakerException(msg)


	def PrinterJobStatus(self, object="virtual_sdcard"):
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/printer/objects/query?"+object, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on job status")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer job status request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "printer objects query"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Job Status return message as JSON")

	def FileDownload(self, filename, root="gcodes"):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/files/" + root + "/" + filename
			r = self.session.get(url, timeout=20.0)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on server files download")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send file download request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server files download"))

		return r

	def FileUpload(self, filename, filep, root="gcodes"):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/files/upload"
			files={"file": filep, "filename": filename, "root": root}
			r = requests.post(url, files=files, timeout=20.0)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on server files upload")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send post request.")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "printer files upload"))

		return True

	def FileDelete(self, filename, root="gcodes"):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/files/" + root + "/" + filename
			r = requests.delete(url, timeout=2.0)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on server files delete")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send delete request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server files delete"))

		return True

	def GetHistoryTotals(self):
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/server/history/totals", timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on get history totals")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send history Totals request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server history totals"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse history totals return message as JSON")

	def GetHistoryList(self, limit, start):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/history/list?limit=%s&start=%d&order=asc" % (limit, start)
			r = self.session.get(url, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on get history list")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send history list request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server history list"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse history list return message as JSON")

	def GetHistoryJob(self, jobid):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/history/job?uid=%s" % jobid
			r = self.session.get(url, timeout=0.7)

		except requests.exceptions.ReadTimeout:
			raise MoonrakerException("Read timeout on get history job")

		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send history job request")

		if r.status_code >= 400:
			raise MoonrakerException(getErrorMessage(r, "server history job"))

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse history job return message as JSON")
