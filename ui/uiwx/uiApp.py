import sys, os, wx
import dabo
import dabo.ui as ui
import dabo.dEvents as dEvents
from dabo.common.dObject import dObject
from dabo.dLocalize import _, n_

class uiApp(wx.App, dObject):
	_IsContainer = False
	
	def __init__(self, *args):
		wx.App.__init__(self, 0, args)
		dObject.__init__(self)
		self.Bind(wx.EVT_ACTIVATE_APP, self._onWxActivate)
		
		self.Name = _("uiApp")
		self._noneDisp = _("<null>")
		
		
	def OnInit(self):
		return True


	def setup(self, dApp):
		# wx has properties for appName and vendorName, so Dabo should update
		# these. Among other possible uses, I know that on Win32 wx will use
		# these for determining the registry key structure.
		self.SetAppName(dApp.getAppInfo("appName"))
		self.SetClassName(dApp.getAppInfo("appName"))
		self.SetVendorName(dApp.getAppInfo("vendorName"))
		
		self.charset = "unicode"
		if not self.charset in wx.PlatformInfo:
			self.charset = "ascii"
		string = "wxPython Version: %s %s (%s)" % (wx.VERSION_STRING, 
			wx.PlatformInfo[1], self.charset)
			
		if wx.PlatformInfo[0] == "__WXGTK__":
			string += " (%s)" % wx.PlatformInfo[3]
			self._platform = _("GTK")
		elif wx.PlatformInfo[0] == "__WXMAC__":
			self._platform = _("Mac")
		elif wx.PlatformInfo[0] == "__WXMSW__":
			self._platform = _("Win")

		dabo.infoLog.write(string)
			
		wx.InitAllImageHandlers()

		self.dApp = dApp
		
		if dApp.MainFormClass is not None:
			self.dApp.MainForm = dApp.MainFormClass()
			self.SetTopWindow(self.dApp.MainForm)
			self.dApp.MainForm.Show(dApp.showMainFormOnStart)
			

	def start(self, dApp):
		# Manually raise Activate, as wx doesn't do that automatically
		self.raiseEvent(dEvents.Activate)
		self.MainLoop()

	
	def finish(self):
		# Manually raise Deactivate, as wx doesn't do that automatically
		self.raiseEvent(dEvents.Deactivate)
	
	
	def _getPlatform(self):
		return self._platform
		
	def _onWxActivate(self, evt):
		""" Raise the Dabo Activate or Deactivate appropriately.
		"""
		if bool(evt.GetActive()):
			self.raiseEvent(dEvents.Activate, evt)
		else:
			self.raiseEvent(dEvents.Deactivate, evt)
		evt.Skip()
			
	
	def onWinClose(self, evt):
		"""Close the topmost window, if any."""
		if self.ActiveForm:
			self.ActiveForm.close()


	def onFileExit(self, evt):
		"""The MainForm contains the logic in its close methods to 
		cycle through all the forms and determine if they can all be
		safely closed. If it closes them all, it will close itself.
		"""
		if self.dApp.MainForm:
			self.dApp.MainForm.close()
		else:
			frms = self.Application.uiForms
			while frms:
				frm = frms[0]
				# This will allow forms to veto closing (i.e., user doesn't
				# want to save pending changes). 
				try:
					if frm.close() == False:
						# The form stopped the closing process. The user
						# must deal with this form (save changes, etc.) 
						# before the app can exit.
						frm.bringToFront()
						return False
					else:
						frms.remove(frm)
				except:
					# Object is already deleted
					frms.remove(frm)
		

	def onEditCut(self, evt):
		self.onEditCopy(evt, cut=True)


	def onEditCopy(self, evt, cut=False):
		# Some controls (stc...) have Cut(), Copy(), Paste() methods,
		# while others do not. Try these methods first, but fall back
		# to interacting with wx.TheClipboard if necessary.
		if self.ActiveForm:
			win = self.ActiveForm.ActiveControl
			try:
				if cut:
					win.Cut()
				else:
					win.Copy()
					
			except AttributeError:
				try:
					selectedText = win.GetStringSelection()
				except AttributeError:
					selectedText = None
	
				if selectedText:
					self.copyToClipboard(selectedText)
					if cut:
						win.Remove(win.GetSelection()[0], win.GetSelection()[1])
	
	def copyToClipboard(self, txt):
		data = wx.TextDataObject()
		data.SetText(txt)
		cb = wx.TheClipboard
		cb.Open()
		cb.SetData(data)
		cb.Close()


	def onEditPaste(self, evt):
		if self.ActiveForm:
			win = self.ActiveForm.ActiveControl
			try:
				win.Paste()
			except AttributeError:
			
				try:
					selection = win.GetSelection()
				except AttributeError:
					selection = None
	
				if selection != None:
					data = wx.TextDataObject()
					cb = wx.TheClipboard
					cb.Open()
					success = cb.GetData(data)
					cb.Close() 
					if success: 
						win.Replace(selection[0], selection[1], data.GetText())
		

	def onEditPreferences(self, evt):
		dabo.infoLog.write(_("Stub: uiApp.onEditPreferences()"))


	def onEditUndo(self, evt):
		if self.ActiveForm:
			win = self.ActiveForm.ActiveControl
			try:
				win.Undo()
			except AttributeError:
				dabo.errorLog.write(_("No apparent way to undo."))
	

	def onEditRedo(self, evt):
		if self.ActiveForm:
			win = self.ActiveForm.ActiveControl
			try:
				win.Redo()
			except AttributeError:
				dabo.errorLog.write(_("No apparent way to redo."))


	def onEditFind(self, evt):
		""" Display a Find dialog. """
		if self.ActiveForm:
			win = self.ActiveForm.ActiveControl
			if win:
				self.findWindow = win           # Save reference for use by self.OnFind()
	
				try:
					data = self.findReplaceData
				except AttributeError:
					data = wx.FindReplaceData(wx.FR_DOWN)
					self.findReplaceData = data
				dlg = wx.FindReplaceDialog(win, data, "Find")
				
				# Map enter key to find button:
				anId = wx.NewId()
				dlg.SetAcceleratorTable(wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, anId),]))
				dlg.Bind(wx.EVT_MENU, self.onEnterInFindDialog, id=anId)
	
				dlg.Bind(wx.EVT_FIND, self.OnFind)
				dlg.Bind(wx.EVT_FIND_NEXT, self.OnFind)
				dlg.Bind(wx.EVT_CLOSE, self.OnFindClose)
	
				dlg.Show()
	#- 			self.findDialog = dlg
			
	
	def onEnterInFindDialog(self, evt):
		## I don't know what to do from here: how do I simulate the user
		## clicking "find"...
		pass
#- 		findButton = None
#- 		dlg = self.findDialog
#- #- 		print dir(dlg)
#- 		for child in dlg.GetChildren():
#- 			if child.GetName() == "button" and child.GetLabel() == "Find":
#- 				findButton = child
#- 				break
#- 		if findButton is not None:
#- 			findButton.Command(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED))			
					

	def onEditFindAgain(self, evt):
		"""Repeat the last search."""
		try:
			fd = self.findReplaceData
			self.OnFind(fd)
		except AttributeError:
			self.onEditFind(None)
			return
			

	def OnFindClose(self, evt):
		""" User clicked the close button, so hide the dialog."""
		evt.GetEventObject().Destroy()
		evt.Skip()


	def OnFind(self, evt):
		""" User clicked the 'find' button in the find dialog.

		Run the search on the current control, if it is a text-based control.
		Select the found text in the control.
		"""
#- 		flags = evt.GetFlags()
#- 		findString = evt.GetFindString()
		flags = self.findReplaceData.GetFlags()
		findString = self.findReplaceData.GetFindString()
		downwardSearch = (flags & wx.FR_DOWN) == wx.FR_DOWN
		wholeWord = (flags & wx.FR_WHOLEWORD) == wx.FR_WHOLEWORD
		matchCase = (flags & wx.FR_MATCHCASE) == wx.FR_MATCHCASE
		
		win = self.findWindow
		
		if win:
			try:
				# SCT:
				start = win.GetCurrentPos()
				flags = 0
				if downwardSearch:
					finish = win.GetTextLength()
				else:
					finish = 0
				pos = win.FindText(start, finish, findString, flags)
				if pos > -1:
					win.SetSelection(pos, pos+len(findString))
				
			except AttributeError:		
				try: 
					value = win.GetValue()
				except AttributeError:
					value = None
				if not isinstance(value, basestring):
					dabo.errorLog.write(_("Active control isn't text-based."))
					return


				currentPos = win.GetInsertionPoint()

				if downwardSearch:
					value = win.GetValue()[currentPos:]
				else:
					value = win.GetValue()[0:currentPos]
					value = list(value)
					value.reverse()
					value = ''.join(value)
					findString = list(findString)
					findString.reverse()
					findString = ''.join(findString)

				if not matchCase:
					value = value.lower()
					findString = findString.lower()

				result = value.find(findString)
				if result >= 0:
					if downwardSearch:
						win.SetSelection(currentPos+result, currentPos+result+len(findString))
					else:
						win.SetSelection(currentPos-result, currentPos-result-len(findString))
					win.ShowPosition(win.GetSelection()[1])
				else:
					dabo.infoLog.write(_("Not found"))


	def getLoginInfo(self, message=None):
		""" Display the login form, and return the user/password 
		as entered by the user.
		"""
		import dabo.ui.dialogs.login as login
		ld = login.Login(self.dApp.MainForm)
		ld.setMessage(message)
		ld.show()
		user, password = ld.user, ld.password
		return user, password
	
	
	def onCmdWin(self, evt):
		"""Display a command window for debugging."""
		try:
			self.ActiveForm.onCmdWin(evt)
		except AttributeError:
			# Either no form active, or it's not a proper Dabo form
			pass
	

	def _getActiveForm(self):
		try:
			v = self._activeForm
		except AttributeError:
			v = self._activeForm = None
		return v
	def _setActiveForm(self, frm):
		self._activeForm = frm
		
		
	def _getNoneDisp(self):
		return self._noneDisp
	def _setNoneDisp(self, val):
		self._noneDisp = val
		

	
	ActiveForm = property(_getActiveForm, None, None, 
			_("Returns the form that currently has focus, or None.  (dForm)" ) )

	NoneDisplay = property(_getNoneDisp, _setNoneDisp, None, 
			_("Text to display for null (None) values.  (str)") )
	
