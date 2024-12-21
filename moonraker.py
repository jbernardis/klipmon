import os
import requests
import json

from mrclient import Client


class MoonrakerException(Exception):
	def __init__(self, message):
		Exception.__init__(self)
		self.message = message


class Moonraker:
	def __init__(self, ip, port, name):
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

	def ServerInfo(self):
		try:
			r = self.session.get(self.ipString + "/server/info", timeout=0.7)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send server info request")

		if r.status_code >= 400:
			raise MoonrakerException("HTTP Error %d on server info" % r.status_code)

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			return r.text

	def RootsList(self):
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/server/files/roots", timeout=0.7)
		except requests.exceptions.ConnectionError:
			return False, "Unable to send list roots request"

		if r.status_code >= 400:
			msg = "HTTP Error %d on list roots" % r.status_code
			return False, msg

		try:
			return True, r.json()
		except json.decoder.JSONDecodeError:
			return True, r.text

	def FilesList(self, root="gcodes"):
		parms = {"root": root}
		try:
			r = self.session.get("http://" + self.ip + ":" + self.port + "/server/files/list", params=parms, timeout=0.7)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to establish connection with printer %s at address %s" % (self.name, self.ipString))

		if r.status_code >= 400:
			raise MoonrakerException("HTTP Error %d on list files" % r.status_code)

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
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to establish connection with printer %s at address %s" % (self.name, self.ipString))

		if r.status_code >= 400:
			raise MoonrakerException("HTTP Error %d on get file metadata" % r.status_code)

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
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer object list request")

		if r.status_code >= 400:
			msg = "HTTP Error %d on printer object list" % r.status_code
			raise MoonrakerException(msg)

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
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer object %s query request" % object)

		if r.status_code >= 400:
			msg = "HTTP Error %d on printer object %s query" % (r.status_code, object)
			raise MoonrakerException(msg)

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
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer object %s subscribe request" % object)

		if r.status_code >= 400:
			msg = "HTTP Error %d on printer object %s subscribe" % (r.status_code, object)
			raise MoonrakerException(msg)

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Object Subscribe return message as JSON")

	def PrinterCachedTemps(self):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/temperature_store?include_monitors=false"
			r = self.session.get(url, timeout=0.7)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send server temperature_store request")

		if r.status_code >= 400:
			msg = "HTTP Error %d on server temperature_stiore request"
			raise MoonrakerException(msg)

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Object Status return message as JSON")

	def PrintFile(self, fn):
		try:
			p = self.session.post("http://" + self.ip + ":" + self.port + "/printer/print/start?filename=" + fn)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send print start request")

		if p.status_code >= 400:
			msg = "HTTP Error %d on print file" % p.status_code
			raise MoonrakerException(msg)

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

	def SendGCode(self, gcodecmd):
		try:
			p = self.session.post("http://" + self.ip + ":" + self.port + "/printer/gcode/script?script=" + gcodecmd, timeout=0.7)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send GCode commands")

		print(p.url)

		if p.status_code >= 400:
			j = p.json()
			try:
				msg = j["error"]["message"]
			except KeyError:
				msg = "HTTP Error %d on printer send gcode" % p.status_code

			print(msg)
			raise MoonrakerException(msg)

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
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send printer job status request")

		if r.status_code >= 400:
			msg = "HTTP Error %d on printer job status" % r.status_code
			raise MoonrakerException(msg)

		try:
			return r.json()
		except json.decoder.JSONDecodeError:
			raise MoonrakerException("Unable to parse Job Status return message as JSON")

	def FileDownload(self, filename, root="gcodes"):
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/files/" + root + "/" + filename
			r = self.session.get(url, timeout=0.7)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send file download request")

		if r.status_code >= 400:
			msg = "HTTP Error %d on file download" % r.status_code
			raise MoonrakerException(msg)

		return r

	def FileUpload(self, filename, fp, root="gcodes"):
		headers = {
			'filename': filename,
			'name': "file",
			"root": root,
		}
		try:
			url = "http://" + self.ip + ":" + self.port + "/server/files/upload"
			files={filename: fp}
			r = requests.post(url, files=files, timeout=4.0)
		except requests.exceptions.ConnectionError:
			raise MoonrakerException("Unable to send post request is rr server running?")

		if r.status_code >= 400:
			raise MoonrakerException("HTTP Error %d" % r.status_code)

		return True

if __name__ == '__main__':
	p = Moonraker("dbot.local", "7125", "dbot")

	rc, resp = p.ServerInfo()
	print("response code: %s" % rc)
	print("response value:")
	pprint.pprint(resp)

	# rc, resp = p.RootsList()
	# print("response code: %s" % rc)
	# print("response value:")
	# pprint.pprint(resp)
	#
	# rc, resp = p.FilesList()
	# print("response code: %s" % rc)
	# print("response value:")
	# pprint.pprint(resp)
	#
	# rc, resp = p.PrinterJobStatus()
	# print("response code: %s" % rc)
	# print("response value:")
	# pprint.pprint(resp)
	#
	# rc, resp = p.FileDownload("drawer divider.gcode")
	# print("response code: %s" % rc)
	# print("response value:")
	# offset = 0
	# for i in range(10):
	# 	print("%d(%d): %s" % (i, offset, resp[i]))
	# 	offset += len(resp[i]) + 1
	#
	# rc, resp = p.PrinterObjectsList()
	# print("response code: %s" % rc)
	# print("response value:")
	# pprint.pprint(resp)
	#
	# rc, resp = p.PrinterObjectStatus(["extruder", "heater_bed", ])
	# print("response code: %s" % rc)
	# print("response value:")
	# pprint.pprint(resp)
	#
	# rc, resp = p.PrinterObjectStatus(["heaters"])
	# print("response code: %s" % rc)
	# print("response value:")
	# pprint.pprint(resp)

	fp = open("C:\\Users\\jeff\\tmp\\cube.gcode", "r")
	p.FileUpload("file", fp)

