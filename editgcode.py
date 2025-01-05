import wx
import  wx.lib.editor    as  editor
import re

def findallpos(regexp, mstr):
	m = regexp.findall(mstr)
	mpos = []
	spos = 0
	ms = regexp.search(mstr, spos)
	while ms:
		spos = ms.start() + 1
		mpos.append(spos-1)
		ms = regexp.search(mstr, spos)		
	
	res = []
	lim = len(mpos)
	
	if len(m) != len(mpos):
		if len(m) < lim:
			lim = len(m)
		
	for i in range(lim):
		res.append([mpos[i], m[i]])
	
	return res
	

class myEditor(editor.Editor):
	def __init__(self, parent, iD):
		self.parent = parent
		editor.Editor.__init__(self, parent, iD, style=wx.SUNKEN_BORDER)
		self.findData = wx.FindReplaceData()
		self.findData.SetFlags(0x01)
		
	def BindFindEvents(self, win):
		win.Bind(wx.EVT_FIND, self.OnFind)
		win.Bind(wx.EVT_FIND_NEXT, self.OnFind)
		win.Bind(wx.EVT_FIND_REPLACE, self.OnFind)
		win.Bind(wx.EVT_FIND_REPLACE_ALL, self.OnFind)
		win.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
		
	def DrawCursor(self, dc=None):
		editor.Editor.DrawCursor(self, dc)
		self.parent.showRowCol(self.cy,self.cx)
		
	def SetControlFuncs(self, action):
		editor.Editor.SetControlFuncs(self, action)
		action['f'] = self.doFind
		action['r'] = self.doFindReplace
		
	def doFind(self, evt):
		dlg = wx.FindReplaceDialog(self, self.findData, "Find")
		self.BindFindEvents(dlg)
		#dlg.SetFocus()
		dlg.Show(True)
	
	def doFindReplace(self, evt):
		dlg = wx.FindReplaceDialog(self, self.findData, "Find/Replace", wx.FR_REPLACEDIALOG)
		self.BindFindEvents(dlg)
		#dlg.SetFocus()
		dlg.Show(True)
		
	def OnFind(self, evt):
		et = evt.GetEventType()
		flags = evt.GetFlags()
		buf = self.GetText()
		down = False
		if flags & 0x01: down = True

		wholeword = False		
		if flags & 0x02: wholeword = True
		
		casematch = False
		if flags & 0x04: casematch = True
		
		if et in [ wx.wxEVT_COMMAND_FIND, wx.wxEVT_COMMAND_FIND_NEXT ]:
			x = self.cx
			y = self.cy
			if et == wx.wxEVT_COMMAND_FIND_NEXT:
				if down:
					x += 1
				else:
					x -= 1
					if x < 0:
						y -= 1
						if y < 0:
							y = len(buf)-1
						x = len(buf[y])
						
			loc = self.findString(evt.GetFindString(), down, wholeword, casematch, [x, y])
			if loc is None:
				wx.Bell()
				return
			
			self.DrawSimpleCursor(0, 0, old=True)
			self.cx = loc[0]
			self.cy = loc[1]+1
			self.KeepCursorOnScreen()
			self.cy = loc[1]
			self.DrawCursor()
			
		elif et in [ wx.wxEVT_COMMAND_FIND_REPLACE ]:
			loc = self.findString(evt.GetFindString(), down, wholeword, casematch, [self.cx, self.cy], evt.GetReplaceString())
			if loc is None:
				wx.Bell()
				return
			
			self.DrawSimpleCursor(0, 0, old=True)
			self.cx = loc[0]
			self.cy = loc[1]+1
			self.KeepCursorOnScreen()
			self.cy = loc[1]
			self.DrawCursor()
			self.UpdateView()
			
		elif et in [ wx.wxEVT_COMMAND_FIND_REPLACE_ALL ]:
			cy = 0
			cx = 0
			fstr = evt.GetFindString()
			rstr = evt.GetReplaceString()
			
			while True:
				# just ignore the direction and do the whole thing in a downward direction
				loc = self.findString(fstr, True, wholeword, casematch, [cx, cy], rstr)
				if loc is None:
					self.UpdateView()
					return
				
				if loc[1] < cy:
					self.UpdateView()
					return
				
				cx = loc[0]
				cy = loc[1]
			
	def findString(self, mstr, down, wholeword, casematch, start, replace=None):
		buf = self.GetText()
		
		if wholeword:
			mstr = r"\b" + mstr + r"\b"
		
		reFlags = 0			
		if not casematch:
			reFlags = re.IGNORECASE
			
		regexp = re.compile(mstr, reFlags)

		cy = start[1]
		cx = start[0]
				
		lct = 0
		while lct < len(buf):
			m = findallpos(regexp, buf[cy])
			if len(m) > 0:
				if down:
					for i in range(len(m)):
						if m[i][0] >= cx: # found one
							if replace:
								buf[cy] = buf[cy][:m[i][0]] + replace + buf[cy][m[i][0]+len(m[i][1]):]
							return([m[i][0], cy, m[i][1]])
				else:		
					for i in range(len(m), 0, -1):
						if (m[i-1][0] <= cx) or (cx == -1): # found one
							if replace:
								buf[cy] = buf[cy][:m[i-1][0]] + replace + buf[cy][m[i-1][0]+len(m[i-1][1]):]
							return([m[i-1][0], cy, m[i-1][1]])

			# no matches - move to the next line
			lct += 1
			if down:
				cx = 0
				cy += 1
				if cy >= len(buf): cy = 0
			else:
				cx = -1
				cy -= 1
				if cy < 0: cy = len(buf)-1
				
		return None
			
		
	def OnFindClose(self, evt):
		evt.GetDialog().Destroy()
			

DLGWIDTH = 800
		
class EditGCodeDlg(wx.Dialog):
	def __init__(self, parent, gcode, title, cbClose):
		wx.Dialog.__init__(self, parent, wx.ID_ANY, "Edit GCode: "+title, size=(DLGWIDTH, 804))
		self.startGCode = gcode	
		self.cbClose = cbClose	
		
		wx.CallAfter(self.finishInit)

	def finishInit(self):
		self.ed = myEditor(self, -1)
		box = wx.BoxSizer(wx.VERTICAL)
		box.Add(self.ed, 1, wx.ALL|wx.GROW, 1)
		self.SetSizer(box)
		self.SetAutoLayout(True)

		self.editbuffer = self.startGCode[:]

		self.ed.SetText(self.editbuffer)

		btnsizer = wx.BoxSizer()

		btn = wx.Button(self, wx.ID_ANY, "Save")
		btn.SetHelpText("Save Modified buffer")
		btn.SetDefault()
		btnsizer.Add(btn)
		self.Bind(wx.EVT_BUTTON, self.doSave, btn)

		btn = wx.Button(self, wx.ID_ANY, "Cancel")
		btn.SetHelpText("Exit without changing code")
		btnsizer.Add(btn)		
		self.Bind(wx.EVT_BUTTON, self.doCancel, btn)
		self.Bind(wx.EVT_CLOSE, self.doCancel)
		
		btnsizer.AddSpacer(DLGWIDTH-360)
		self.font12bold = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		self.stPosition = wx.StaticText(self, wx.ID_ANY, "(0, 0)")
		self.stPosition.SetFont(self.font12bold)
		btnsizer.Add(self.stPosition)
		
		box.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
		self.Layout()
		
	def showRowCol(self, row, col):
		try:
			self.stPosition.SetLabel("(%d, %d)" % (row+1, col+1))
		except AttributeError:
			pass

	def doSave(self, evt):
		self.cbClose(wx.ID_OK)
		
	def doCancel(self, evt):
		if self.hasChanged():
			askok = wx.MessageDialog(self, "Are you Sure you want to Cancel and lose your changes?",
				'Lose Changes', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION)
	
			rc = askok.ShowModal()
			askok.Destroy()
			
			if rc != wx.ID_YES:
				return

		self.cbClose(wx.ID_CANCEL)
		
	def getData(self):
		return self.ed.GetText()
	
	def hasChanged(self):
		eb = self.getData()
		if len(eb) != len(self.startGCode):
			return True
		
		for i in range(len(eb)):
			if eb[i] != self.startGCode[i]:
				return True
			
		return False
			
