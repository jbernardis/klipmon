import wx


class ImageMap(wx.Panel):
	def __init__(self, parent, bmp, style=wx.NO_BORDER):
		self.bmp = bmp
		self.enabled = True
		self.mask = wx.Mask(self.bmp, wx.BLUE)
		self.bmp.SetMask(self.mask)
		self.height = self.bmp.GetHeight()
		self.width = self.bmp.GetWidth()
		wx.Panel.__init__(self, parent, size=(self.width, self.height), style=style)
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		self.Bind(wx.EVT_LEFT_DOWN, self.onMouseClick)
		self.w, self.h = self.GetClientSize()
		self.buffer = None

		self.hotspots = []
		self.handler = None

		self.initBuffer()

	def enableControls(self, flag):
		self.enabled = flag
		if not flag:
			self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

	def changeBmp(self, newbmp):
		if (newbmp.GetHeight() != self.height) or (newbmp.GetWidth() != self.width):
			print ("New Bitmap needs to be the same size as the original")
			return False

		self.bmp = newbmp
		self.mask = wx.Mask(self.bmp, wx.BLUE)
		self.bmp.SetMask(self.mask)
		self.Refresh()
		return True

	def onSize(self, _):
		self.initBuffer()

	def onPaint(self, _):
		dc = wx.PaintDC(self)
		self.drawImage(dc)

	def onMouseMove(self, evt):
		if not self.enabled:
			return

		x, y = evt.GetPosition()
		if self.inHotSpot(x, y) is not None:
			self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
		else:
			self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

	def onMouseClick(self, evt):
		if not self.enabled:
			return

		if self.handler is not None:
			x, y = evt.GetPosition()
			l = self.inHotSpot(x, y)
			if l is not None:
				self.handler(l)
		evt.Skip()

	def inHotSpot(self, x, y):
		for r in self.hotspots:
			if r[0] < x < r[2] and r[1] < y < r[3]:
				return r[4]

		return None

	def setHotSpots(self, handler, hs):
		self.handler = handler
		self.hotspots = hs

	def initBuffer(self):
		self.w, self.h = self.GetClientSize()
		self.buffer = wx.Bitmap(self.w, self.h)
		self.redrawImage()

	def redrawImage(self):
		dc = wx.ClientDC(self)
		self.drawImage(dc)

	def drawImage(self, dc):
		dc.DrawBitmap(self.bmp, 0, 0, False)
