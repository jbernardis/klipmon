import wx
import os


class ListDlg(wx.Dialog):
    def __init__(self, parent, title, dataList, dlgexit, clear=False):
        wx.Dialog.__init__(self, parent, style=wx.DEFAULT_FRAME_STYLE)
        
        self.parent = parent
        self.dlgexit = dlgexit

        self.SetTitle(title)
        self.title = title
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        font = wx.Font(wx.Font(18, wx.FONTFAMILY_ROMAN, wx.NORMAL, wx.BOLD, faceName="Arial"))

        vsz = wx.BoxSizer(wx.VERTICAL)
        vsz.AddSpacer(20)

        data = "\n".join(dataList)
        tcList = wx.TextCtrl(self, wx.ID_ANY, data,
                size=(800, 460), style=wx.TE_MULTILINE)
        tcList.SetFont(font)
        tcList.ShowPosition(len(data))
        vsz.Add(tcList)
        vsz.AddSpacer(10)
        self.tcList = tcList
        
        bsz = wx.BoxSizer(wx.HORIZONTAL)

        if clear:
            self.bClear = wx.Button(self, wx.ID_ANY, "Clear")
            self.Bind(wx.EVT_BUTTON, self.OnBClear, self.bClear)
            bsz.Add(self.bClear)

            bsz.AddSpacer(20)

        self.bExit = wx.Button(self, wx.ID_ANY, "Close")
        self.Bind(wx.EVT_BUTTON, self.OnBExit, self.bExit)
        bsz.Add(self.bExit)

        vsz.Add(bsz, 0, wx.ALIGN_CENTER_HORIZONTAL)
        
        vsz.AddSpacer(20)
        
        hsz = wx.BoxSizer(wx.HORIZONTAL)
        hsz.AddSpacer(20)
        
        hsz.Add(vsz)
        hsz.AddSpacer(20)
        
        self.SetSizer(hsz)
        
        self.Fit()
        self.Layout()
        
    def AddItem(self, msg):
        self.tcList.AppendText("\n"+msg)

    def OnBClear(self, evt):
        self.tcList.Clear()

    def OnClose(self, _):
        self.DoClose()
        
    def OnBOK(self, _):
        self.DoClose()
        
    def OnBExit(self, _):
        self.DoClose()

    def GetText(self):
        return self.tcList.GetValue()
        
    def DoClose(self):
        self.dlgexit()

