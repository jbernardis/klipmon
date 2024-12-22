import math
import re


gcRegex = re.compile("[-]?\\d+[.]?\\d*")

MOVE_MOVE = 'm'
MOVE_PRINT = 'p'
MOVE_EXTRUDE = 'e'
MOVE_RETRACT = 'r'


def calcFilamentVolume(flen, fdiam):
	csArea = ((fdiam/2.0)**2)*math.pi
	return csArea * flen


class GCMove:
	def __init__(self, x, y, z, e, f, mtype, offset):
		self.x = x
		self.y = y
		self.z = z
		self.e = e
		self.f = f
		self.mtype = mtype
		self.offset = offset
		self.moveTime = 0.0
		
		self.lastDx = 0.0
		self.lastDy = 0.0
		self.lastSpeed = 0.0

	def getMoveType(self):
		return self.mtype

	def getOffset(self):
		return self.offset
	
	def calcMoveTime(self, lx, ly, lz, le, lf, acceleration):
		speed = lf / 60.0

		dx = self.x - lx
		dy = self.y - ly
		dz = self.z - lz
		
		dist = 0
		if self.mtype in [MOVE_RETRACT, MOVE_EXTRUDE]:
			de = self.e - le
			dist = de

		elif self.mtype in [MOVE_MOVE, MOVE_PRINT]:
			dist = math.hypot(dx, dy)
			if dist == 0:
				dist = dz

		if dx * self.lastDx + dy * self.lastDy <= 0:
			self.lastSpeed = 0
				
		if speed == self.lastSpeed:
			mvTime = dist / speed if speed != 0 else 0
		else:
			d = 2 * abs(((speed + self.lastSpeed) * (speed - self.lastSpeed) * 0.5) / acceleration)
			if d <= dist and self.lastSpeed + speed != 0 and speed != 0:
				mvTime = 2 * d / (self.lastSpeed + speed)
				mvTime += (dist - d) / speed
			else:
				mvTime = 2 * dist / (self.lastSpeed + speed)  

		self.lastDx = dx
		self.lastDy = dy

		#print ("calculated print/move time dxyz ({:f}, {:f}, {:f}) dist {:f} speed {:f}/{:f} == {:f}".format(dx, dy, dz, dist, speed, self.lastSpeed, mvTime))
		
		self.lastSpeed = speed

		self.moveTime = mvTime
		return self.moveTime
	
	def getMoveTime(self):
		return self.moveTime

class GCLayer:
	def __init__(self, ht, nExtr, fDiam):
		# print ("new layer at height {:f}".format(ht))
		self.height = ht
		self.nExtr = nExtr
		self.filamentDiameter = fDiam
		self.moves = []
		self.minOffset = None
		self.maxOffset = None
		self.printMoves = 0
		self.moveMoves = 0
		self.extrudeMoves = 0
		self.layerTime = 0.0
		self.filament = [0.0] * nExtr
		self.filamentVolume = [0*x for x in range(self.nExtr)]

	def getMoves(self):
		return self.moves

	def addMove(self, move):
		self.moves.append(move)
		self.layerTime += move.getMoveTime()
		
		mo = move.getOffset()
		if self.minOffset is None or mo < self.minOffset: self.minOffset = mo
		if self.maxOffset is None or mo > self.maxOffset: self.maxOffset = mo
		mt = move.getMoveType()
		if mt == MOVE_PRINT:
			self.printMoves += 1
		elif mt == MOVE_MOVE:
			self.moveMoves += 1
		elif mt == MOVE_EXTRUDE:
			self.extrudeMoves += 1

	def addTime(self, tm):
		self.layerTime += tm
			
	def addFilament(self, f, t):
		self.filament[t] += f
		
	def getFilament(self):
		return [[self.filament[x], self.filamentVolume[x]/1000.0] for x in range(self.nExtr)]

	def calcLayerVolume(self):
		self.filamentVolume = [calcFilamentVolume(self.filament[x], self.filamentDiameter) for x in range(self.nExtr)]
		
	def getHeight(self):
		return self.height

	def getMoveCounts(self):
		return len(self.moves), self.printMoves, self.moveMoves, self.extrudeMoves

	def getOffsets(self):
		return self.minOffset, self.maxOffset

	def setMinOffset(self, mino):
		self.minOffset = mino
		
	def getLayerTime(self):
		return self.layerTime

def get_float(paramStr, which, last, relativeValue=False):
	try:
		v = float(gcRegex.findall(paramStr.split(which)[1])[0])
		if relativeValue:
			return v+last
		else:
			return v
	except ValueError:
		return last
	except IndexError:
		return last

class GCode:
	def __init__(self, gc, pname, psettings):
		self.gcode = [g for g in gc]

		self.nExtr = 1 # settings.getSetting("nExtr", pname, 1)
		self.acceleration = 1500 # settings.getSetting("acceleration", pname, 1500)
		self.filamentDiameter = 1.75 #settings.getSetting("filamentDiameter", pname, 1.75)
		self.g28time = 15 # settings.getSetting("g28time", pname, 15)
		self.g29time = 60 #settings.getSetting("g29time", pname, 60)

		self.relativeExtrude = False
		self.relativeMove = False
		self.hasMovement = False
		self.hasFilament = False
		self.resetFilament = False
		self.gcmd = ""

		self.filament = [0.0] * self.nExtr
		self.tool = 0

		self.layer = GCLayer(0.0, self.nExtr, self.filamentDiameter)
		self.layers = []
		self.layers.append(self.layer)

		self.lastX = self.paramX = 0.0
		self.lastY = self.paramY = 0.0
		self.lastZ = self.paramZ = 0.0
		self.lastE = self.paramE = 0.0
		self.lastF = self.paramF = 1000.0
		
		self.totalTime = 0.0

		offset = 0
		ln = 0
		for gl in self.gcode:
			offset += len(gl) + 1

			ln += 1
			self.parseGLine(gl)
			moveType = None
			dFilament = 0.0
			if self.hasMovement:
				if self.paramZ != self.lastZ:
					self.layer = GCLayer(self.paramZ, self.nExtr, self.filamentDiameter)
					self.layers.append(self.layer)

				if self.paramE == self.lastE:
					moveType = MOVE_MOVE
				else:
					moveType = MOVE_PRINT
					dFilament = self.paramE - self.lastE
					
			elif self.hasFilament and not self.resetFilament:
				if self.paramE > self.lastE:
					moveType = MOVE_EXTRUDE
				else:
					moveType = MOVE_RETRACT
				dFilament = self.paramE - self.lastE

			elif self.gcmd == "G28": # home command
				self.layer.addTime(self.g28time)
			elif self.gcmd == "G29": # probe bed command
				self.layer.addTime(self.g29time)

			self.filament[self.tool] += dFilament
			self.layer.addFilament(dFilament, self.tool)
			if moveType:
				mv = GCMove(self.paramX, self.paramY, self.paramZ, self.paramE, self.paramF, moveType, offset)
				t = mv.calcMoveTime(self.lastX, self.lastY, self.lastZ, self.lastE, self.lastF, self.acceleration)
				self.layer.addMove(mv)
				self.totalTime += t

			self.lastX = self.paramX
			self.lastY = self.paramY
			self.lastZ = self.paramZ
			self.lastE = self.paramE
			self.lastF = self.paramF

		self.compress()
		
		self.filamentVolume = [calcFilamentVolume(self.filament[x], self.filamentDiameter) for x in range(self.nExtr)]
		for l in self.layers:
			l.calcLayerVolume()
			
# 		print ("total filament used: {:s}".format(str(self.filament)))
# 		for l in self.layers:
# 			print ("  Filament used: {:s}".format(str(l.getFilament())))
# 		print ("total print time: {:s}".format(formatElapsed(self.totalTime)))
# 		for l in self.layers:
# 			print ("  Layer Height {:f} print time {:s}".format(l.getHeight(), formatElapsed(l.getLayerTime())))

	def getFilament(self):
		return [[self.filament[x], self.filamentVolume[x]/1000.0] for x in range(self.nExtr)]
			
	def getPrintTime(self):
		return self.totalTime
	
	def getLayerTimes(self):
		return [l.getLayerTime() for l in self.layers]
	
	def getLayersBetweenOffsets(self, so, eo):
		res = []
		for l in self.layers:
			o = l.getOffsets()
			if so < o[0] and eo > o[1]:
				res.append(l)

		return res

	def getLayer(self, lx):
		if lx < 0 or lx >= len(self.layers):
			return None

		return self.layers[lx]

	def findLayerByOffset(self, offset):
		lx = 0
		if len(self.layers) == 0:
			return 0, 0

		for l in self.layers:
			minOff, maxOff = l.getOffsets()
			if minOff <= offset <= maxOff:
				lpct = (float(offset-minOff)/float(maxOff-minOff))
				return lx, lpct
			lx += 1

		minOff, maxOff = self.layers[-1].getOffsets()
		if offset >= maxOff:
			return lx-1, 1.0

		return 0, 0

	def layerCount(self):
		return len(self.layers)

	def compress(self):
		nl = []
		lastMaxOffset = None
		for l in self.layers:
			printMoves = l.getMoveCounts()[1]

			if printMoves != 0:
				if lastMaxOffset is not None:
					l.setMinOffset(lastMaxOffset+1)
				lastMaxOffset = l.getOffsets()[1]
				nl.append(l)

		self.layers = nl

	def parseGLine(self, gl):
		self.hasMovement = False
		self.hasFilament = False
		self.resetFilament = False
		if ";" in gl:
			gl = gl.split(";")[0]
		if gl.strip() == "":
			return

		p = re.split("\\s+", gl, 1) + [""]

		cmd = p[0].strip().upper()
		self.gcmd = cmd
		if cmd in ["G1", "G2"]:
			if "X" in p[1]:
				self.hasMovement = True
			if "Y" in p[1]:
				self.hasMovement = True
			if "Z" in p[1]:
				self.hasMovement = True
			if "E" in p[1]:
				self.hasFilament = True

			self.paramX = get_float(p[1], "X", self.lastX, self.relativeMove)
			self.paramY = get_float(p[1], "Y", self.lastY, self.relativeMove)
			self.paramZ = get_float(p[1], "Z", self.lastZ, self.relativeMove)
			self.paramE = get_float(p[1], "E", self.lastE, self.relativeExtrude)
			self.paramF = get_float(p[1], "F", self.lastF)

		elif cmd == "G92":
			self.paramX = get_float(p[1], "X", self.lastX)
			self.paramY = get_float(p[1], "Y", self.lastY)
			self.paramZ = get_float(p[1], "Z", self.lastZ)
			self.paramF = get_float(p[1], "F", self.lastF)
			if self.hasFilament:
				self.paramE = get_float(p[1], "E", self.lastE)
			else:
				self.paramE = 0.0
			self.resetFilament = True

		elif cmd == "G28":
			self.hasMovement = True
			if not ("X" in p[1] or "Y" in p[1] or "Z" in p[1]):
				self.paramX = self.paramY = self.paramZ = 0.0
			else:
				self.paramX = 0.0 if "X" in p[1] else self.lastX
				self.paramY = 0.0 if "Y" in p[1] else self.lastY
				self.paramZ = 0.0 if "Z" in p[1] else self.lastZ
			self.paramE = self.lastE
			self.paramF = self.lastF

		elif cmd == "G90":
			self.relativeMove = False

		elif cmd == "G91":
			self.relativeMove = True

		elif cmd == "M82":
			self.relativeExtrude = False

		elif cmd == "M83":
			self.relativeExtrude = True
			
		elif cmd.startswith("T"):
			try:
				self.tool = int(cmd[1:])
				if self.tool > self.nExtr or self.tool < 0:
					self.tool = 0
			except ValueError:
				self.tool = 0

		else:
			pass
			# print ("Not processing command (%s) at offset %d" % (cmd, offset))
