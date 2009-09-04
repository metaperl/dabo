#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, copy
import dabo, dabo.ui
dabo.ui.loadUI("wx")
import dabo.dEvents as dEvents
from dabo.dReportWriter import dReportWriter
from dabo.lib.reportWriter import *
from dabo.dLocalize import _
from dabo.ui import dKeys
import ClassDesignerPropSheet


NEW_FILE_CAPTION = "< New >"

rdc = None


def DesignerController():
	# Wrapper function to enforce singleton class instance
	class DesignerController(dabo.dApp):
		def initProperties(self):
			self.BasePrefKey = "dabo.ide.reportdesigner"
			self.setAppInfo("appName", "Dabo Report Designer")
			self.MainFormClass = None

		def beforeInit(self):
			self._inSelection = False

		def afterInit(self):
			if sys.platform == "darwin":
				self.bindEvent(dEvents.KeyDown, self._onKeyDown)

		def _onKeyDown(self, evt):
			# Mac-specific behavior
			self.ActiveEditor.onKeyDown(evt)

		def onFileExit(self, evt):
			ret = self.ActiveEditor.closeFile()
			if ret is not None:
				self.finish()

		def getShortExpr(self, expr):
			"""Given an expression, return a shortened version for display in designer."""
			if expr is None:
				return "None"
			if len(expr) < 3:
				return expr
			
			def isVariable(name):
				for v in rdc.ReportForm["Variables"]:
					if v.get("Name", None) == name:
						return True
				return False

			def isRecord(name):
				if name and rdc.ReportForm.has_key("TestCursor") \
						and len(rdc.ReportForm["TestCursor"]) > 0 \
						and rdc.ReportForm["TestCursor"][0].has_key(name):
					return True
				return False

			import re
			c = re.compile("self.(?P<type>Record|Variables)\[(?P<name>.*)\]")
			m = c.match(expr)
			if m:
				name = m.group("name")
				name = name[1:-1]  ## (remove outer quotes)
			else:
				if "." in expr:
					name = expr.split(".")[-1]
				else:
					# No record or variable found: leave alone
					name = None

			if not isVariable(name) and not isRecord(name):
				# This isn't a record or variable: don't shortcut the name as a 
				# visual cue to the developer.
				name = None

			if name is None:
				quotes = ('"', "'")
				if expr[0] in quotes and expr[-1] in quotes:
					# Remove outer quotes
					name = expr[1:-1]
				else:
					for quote in quotes:
						if expr.count(quote) >= 2:
							name = expr[expr.find(quote)+1:]
							name = name[:name.find(quote)]
							break
			if name:
				expr = name
			return expr

			
		def newObject(self, typ, mousePosition):
			"""Add a new object of the passed type to the selected band."""
			rf = self.ReportForm
			parents = []
			objects = []

			defaultProps = {}

			if typ == Variable:
				parents.append(rf["Variables"])
			elif typ == Group:
				parents.append(rf["Groups"])
			else:
				# Normal report object. Place it in all selected bands.
				if isinstance(typ, basestring):
					if typ[:7] == "Field: ":
						# Testcursor field. Create string object with expr of this field.
						defaultProps["expr"] = "self.%s" % typ[7:].strip()
						typ = String
					elif typ[:10] == "Variable: ":
						# Report Variable: Create string object with expr of this variable.
						defaultProps["expr"] = "self.%s" % typ[10:].strip()
						typ = String

				## Want to put the object where the mouse was, however there are things to 
				## consider such as zoom factor, and that the mouse position is absolute 
				## screen position. Also, we only want to do this if we were dealing with the
				## context menu from the designer, as opposed to the one in the object tree.
#				defaultProps["x"] = "%s" % mousePosition[0]
#				defaultProps["y"] = "%s" % mousePosition[1]

				for selObj in self.SelectedObjects:
					if isinstance(selObj, Band):
						parents.append(selObj)

			for parent in parents:			
				obj = parent.addObject(typ)
				obj.update(defaultProps.copy())
				objects.append(obj)

			if objects:
				self.SelectedObjects = objects

			dabo.ui.callAfter(self.ActiveEditor.Form.Raise)


		def getContextMenu(self, mousePosition):
			def onNewObject(evt):
				"""Called from the context menu."""
				tag = evt.EventObject.Tag
				self.newObject(tag, mousePosition)

			def onSelectAll(evt):
				self.selectAllObjects()

			def onCopy(evt):
				self.copy()

			def onPaste(evt):
				self.paste()

			def onCut(evt):
				self.cut()

			def onMoveToTop(evt):
				self.ActiveEditor.sendToBack()

			def onMoveToBottom(evt):
				self.ActiveEditor.bringToFront()

			menu = dabo.ui.dMenu()
			newObjectMenuCreated = False
			newVariableMenuCreated = False
			newGroupMenuCreated = False
			variableSelected, groupSelected = False, False

			for robj in self.SelectedObjects:
				if isinstance(robj, Variable):
					variableSelected = True
				if isinstance(robj, Group):
					groupSelected = True
				if not newVariableMenuCreated and isinstance(robj, (Variables, Variable)):
					menu.append("New variable", OnHit=onNewObject, Tag=Variable)
					newVariableMenuCreated = True
				if not newGroupMenuCreated and isinstance(robj, (Groups, Group)):
					menu.append("New group", OnHit=onNewObject, Tag=Group)
					newGroupMenuCreated = True
				if not newObjectMenuCreated and isinstance(robj, Band):
					newObjectMenuCreated = True
					objectChoices = dabo.ui.dMenu(Caption="New object")
					for choice in (Image, Line, Rectangle, String):
						objectChoices.append(choice.__name__, 
								OnHit=onNewObject, Tag=choice)
					objectChoices.appendSeparator()
					for choice in (SpanningLine, SpanningRectangle):
						objectChoices.append(choice.__name__,
								OnHit=onNewObject, Tag=choice)
					tc = self.ReportForm.get("TestCursor", [])
					var = self.ReportForm.get("Variables", [])
					if tc or var:
						objectChoices.appendSeparator()

					for typ, cap in ((tc, "Field"), (var, "Variable")):
						if typ:
							submenu = dabo.ui.dMenu(Caption=cap)
							fields = []
							if typ == tc:
								if tc:
									fields = tc[0].keys()
							elif typ == var:
								for v in var:
									try:
										fields.append(v["Name"])
									except KeyError:
										# variable not given a name
										pass
							fields.sort()
							for field in fields:
								submenu.append(field, OnHit=onNewObject, 
										Tag="%s: %s" % (cap, field))
							objectChoices.appendMenu(submenu)
					menu.appendMenu(objectChoices)

			if len(menu.Children) > 0:
				menu.appendSeparator()

			menu.append(_("Select All"), HotKey="Ctrl+A", OnHit=onSelectAll)
			menu.appendSeparator()
			menu.append(_("Copy"), HotKey="Ctrl+C", OnHit=onCopy)
			menu.append(_("Cut"), HotKey="Ctrl+X", OnHit=onCut)
			menu.append(_("Paste"), HotKey="Ctrl+V", OnHit=onPaste)

			if variableSelected or groupSelected:
				menu.appendSeparator()
				menu.append(_("Move to top"), HotKey="Ctrl+H", OnHit=onMoveToTop)
				menu.append(_("Move to bottom"), HotKey="Ctrl+J", OnHit=onMoveToBottom)

			return menu


		def selectAllObjects(self):
			"""Select all objects in the selected band(s)."""
			selection = []
		 	for band in self.getSelectedBands():
				for obj in band["Objects"]:
					selection.append(obj)
			self.SelectedObjects = selection


		def showObjectTree(self, bringToTop=False, refresh=False):
			ot = self.ObjectTree
			if ot is None:
				refresh = True
				ot = self.loadObjectTree()
				self.refreshTree()
				
			ot.Form.Visible = True
			if refresh:
				ot.refreshSelection()
			if bringToTop:
				ot.Raise()

		def hideObjectTree(self):
			ot = self.ObjectTree
			if ot is not None and ot.Form.Visible:
				ot.Form.Visible = False

		def loadObjectTree(self):
			otf = ObjectTreeForm()
			ot = self.ObjectTree = otf.Editor
			otf.bindEvent(dEvents.Close, self._onObjectTreeFormClose)
			# Allow the activate to fire so that position is set:
			otf.Visible = True
			otf.Raise()
			self.ActiveEditor.Form.Raise()
			return ot


		def showPropSheet(self, bringToTop=False, refresh=False, prop=None,
				enableEditor=False, focusBack=False):
			ps = self.PropSheet
			if ps is None:
				refresh = True
				ps = self.loadPropSheet()
			ps.Form.Visible = True

			if refresh:
				ps.refreshSelection()

			if prop:
				pg = ps.propGrid
				ds = pg.DataSet

				if enableEditor:
					# Select the value column and enable the editor for the prop. Note: 
					# This needs to be done before changing rows, for some reason, or the
					# editor column isn't activated.
					pg.CurrentColumn = 1

				# Put the propsheet on the row for the passed prop.
				for idx, record in enumerate(ds):
					if record["prop"].lower() == prop.lower():
						pg.CurrentRow = idx
						if focusBack:
							pg._focusToDesigner = True
						break

			if bringToTop:
				ps.Form.Raise()


		def hidePropSheet(self):
			ps = self.PropSheet
			if ps is not None and ps.Form.Visible:
				ps.Form.Visible = False

		def loadPropSheet(self):
			psf = PropSheetForm()
			ps = self.PropSheet = psf.Editor
			psf.bindEvent(dEvents.Close, self._onPropSheetFormClose)
			psf.Visible = True
			psf.Raise()
			self.ActiveEditor.Form.Raise()
			return ps

		
		def refreshTree(self):
			if self.ObjectTree:
				self.ObjectTree.refreshTree()
				self.ObjectTree.refreshSelection()


		def refreshProps(self, refreshEditor=True):
			if refreshEditor and self.ActiveEditor:
				self.ActiveEditor.refresh()
			if self.PropSheet and self.PropSheet.Form.Visible:
				self.PropSheet.refreshSelection()

			
		def refreshSelection(self, refreshEditor=False):
			self._inSelection = True
			for obj in (self.PropSheet, self.ObjectTree):
				if obj is not None:
					obj.refreshSelection()
			if refreshEditor:
				self.ActiveEditor.refresh()
			self._inSelection = False


		def isSelected(self, obj):
			"""Return True if the object is selected."""
			for selObj in self.SelectedObjects:
				if id(selObj) == id(obj):
					return True
			return False


		def getNextDrawable(self, obj):
			"""Return the next drawable after the passed obj."""
			collection = self.getParentBand(obj)["Objects"]
			idx = collection.index(obj) + 1
			if len(collection) <= idx:
				idx = 0
			return collection[idx]


		def getPriorDrawable(self, obj):
			"""Return the prior drawable before the passed obj."""
			collection = self.getParentBand(obj)["Objects"]
			idx = collection.index(obj) - 1
			if len(collection) <= idx:
				idx = len(collection) - 1
			return collection[idx]


		def ReportObjectSelection(self):
			import pickle
			import wx
			rw = self.ActiveEditor._rw

			class ReportObjectSelection(wx.CustomDataObject):
				def __init__(self):
					wx.CustomDataObject.__init__(self, wx.CustomDataFormat("ReportObjectSelection"))
					self.setObject([])

				def setObject(self, objs):
					# We are receiving a sequence of selected objects. Convert to a list of 
					# new dicts representing the object properties.
					copyObjs = []
					for obj in objs:
						copyObj = obj.getMemento()
						copyObjs.append(copyObj)
					self.SetData(pickle.dumps(copyObjs))

				def getObject(self):
					# We need to convert the representative object dicts back into report
					# objects
					copyObjs = pickle.loads(self.GetData())
					objs = []
					for copyObj in copyObjs:
						obj = self.getReportObjectFromMemento(copyObj)
						objs.append(obj)
					return objs

				def getReportObjectFromMemento(self, memento, parent=None):
					obj = rw._getReportObject(memento["type"], parent)
					del(memento["type"])
					for k, v in memento.items():
						if isinstance(v, dict):
							obj[k] = self.getReportObjectFromMemento(v, obj)
						elif isinstance(v, list):
							obj[k] = rw._getReportObject(k, obj)
							for c in v:
								obj[k].append(self.getReportObjectFromMemento(c, obj))
						else:
							obj[k] = v
					return obj

			return ReportObjectSelection()


		def getSelectedBands(self):
			"""Return the list of bands that are currently selected."""
			selBands = []
			for selObj in self.SelectedObjects:
				if not isinstance(selObj, Band) and isinstance(selObj.parent.parent, Band):
					selObj = selObj.parent.parent
				if isinstance(selObj, Band):
					if selObj not in selBands:
						selBands.append(selObj)
			return selBands


		def copy(self, cut=False):
			import wx
			do = self.ReportObjectSelection()
			copyObjs = [selObj for selObj in self.SelectedObjects \
					if not isinstance(selObj, (Report, Band, list))]
			if not copyObjs:
				# don't override the current clipboard with an empty clipboard
				return
			do.setObject(copyObjs)
			if wx.TheClipboard.Open():
				wx.TheClipboard.SetData(do)
				wx.TheClipboard.Close()
			if cut:
				parent = None
				for obj in copyObjs:
					parent = obj.parent
					if isinstance(parent, dict):
						for typ in ("Objects", "Variables", "Groups"):
							if parent.has_key(typ):
								if obj in parent[typ]:
									parent[typ].remove(obj)
					elif isinstance(parent, list):
						parent.remove(obj)
					else:
						print type(parent)
				if parent:
					self.SelectedObjects = [parent]
				else:
					self.SelectedObjects = []
				dabo.ui.callAfterInterval(self.refreshTree, 200)
	
		def cut(self):
			self.copy(cut=True)
			

		def paste(self):
			import wx
			success = False
			do = self.ReportObjectSelection()
			if wx.TheClipboard.Open():
				success = wx.TheClipboard.GetData(do)
				wx.TheClipboard.Close()

			if success:
				objs = do.getObject()
			else:
				# nothing valid in the clipboard
				return

			# Figure out the band to paste the obj(s) into:
			selBands = self.getSelectedBands()
			selBand = None

			if len(selBands) > 0:
				# paste into the first selected band
				selBand = selBands[-1]
			else:
				if len(self.SelectedObjects) > 0:
					# paste into the parent band of the first selected object:
					selBand = self.getParentBand(self.SelectedObjects[-1])

			selectedObjects = []
			for obj in objs:
				if isinstance(obj, Variable):
					# paste into Variables whether or not Variables selected
					pfObjects = self.ReportForm.setdefault("Variables", Variables(self.ReportForm))
					obj.parent = pfObjects
				elif isinstance(obj, Group):
					# paste into Groups whether or not Groups selected
					pfObjects = self.ReportForm.setdefault("Groups", Groups(self.ReportForm))
					obj.parent = pfObjects	
				else:
					pfObjects = selBand.setdefault("Objects", [])
					obj.parent = selBand
				pfObjects.append(obj)
				selectedObjects.append(obj)

			self.ActiveEditor.drawReportForm()
			self.SelectedObjects = selectedObjects

		def getParentBand(self, obj):
			"""Return the band that the obj is a member of."""
			parent = obj
			while parent is not None:
				if isinstance(parent, Band):
					return parent
				parent = parent.parent
			return None

		def _onObjectTreeFormClose(self, evt):
			self.ObjectTree = None

		def _onPropSheetFormClose(self, evt):
			self.PropSheet = None


		def _getActiveEditor(self):
			return getattr(self, "_activeEditor", None)

		def _setActiveEditor(self, val):
			changed = (val != self.ActiveEditor)
			if changed:
				self._activeEditor = val
				self.refreshTree()
				self.refreshProps()


		def _getObjectTree(self):
			try:
				val = self._objectTree
			except AttributeError:
				val = self._objectTree = None
			return val

		def _setObjectTree(self, val):
			self._objectTree = val


		def _getPropSheet(self):
			try:
				val = self._propSheet
			except AttributeError:
				val = self._propSheet = None
			return val

		def _setPropSheet(self, val):
			self._propSheet = val


		def _getReportForm(self):
			return self.ActiveEditor.ReportForm


		def _getSelectedObjects(self):
			return getattr(self.ActiveEditor, "_selectedObjects", [])

		def _setSelectedObjects(self, val):
			self.ActiveEditor._selectedObjects = val
			self.refreshSelection(refreshEditor=True)
		
		ActiveEditor = property(_getActiveEditor, _setActiveEditor)
		ObjectTree = property(_getObjectTree, _setObjectTree)
		PropSheet = property(_getPropSheet, _setPropSheet)
		ReportForm = property(_getReportForm)
		SelectedObjects = property(_getSelectedObjects, _setSelectedObjects)
		Selection = SelectedObjects  ## compatability with ClassDesignerPropSheet
	

	global rdc
	if rdc is None:
		rdc = DesignerController()
	return rdc


# All the classes below will use the singleton DesignerController instance:
rdc = DesignerController()


class DesignerControllerForm(dabo.ui.dForm):
	def initProperties(self):
		self.Caption = "DesignerController Form"
		self.TinyTitleBar = True
		self.ShowMaxButton = False
		self.ShowStatusBar = False
		self.ShowMinButton = False
		self.ShowSystemMenu = False
		self.ShowInTaskBar = False
		self.ShowMenuBar = False


	def afterInit(self):
		sz = self.Sizer
		sz.Orientation = "h"

		self.Editor = self.addObject(self.EditorClass)
		sz.append(self.Editor, 2, "x")
		self.layout()


	def _getEditor(self):
		if hasattr(self, "_editor"):
			val = self._editor
		else:
			val = self._editor = None
		return val

	def _setEditor(self, val):
		self._editor = val
	

	def _getEditorClass(self):
		if hasattr(self, "_editorClass"):
			val = self._editorClass
		else:
			val = self._editorClass = None
		return val

	def _setEditorClass(self, val):
		self._editorClass = val

	Editor = property(_getEditor, _setEditor)
	EditorClass = property(_getEditorClass, _setEditorClass)


class ReportObjectTree(dabo.ui.dTreeView):
	def initProperties(self):
		self.MultipleSelect = True
		self.ShowButtons = True

	def initEvents(self):
		self.bindKey("ctrl+c", self.onCopy)
		self.bindKey("ctrl+x", self.onCut)
		self.bindKey("ctrl+v", self.onPaste)


	def onCopy(self, evt):
		rdc.copy()

	def onCut(self, evt):
		rdc.cut()

	def onPaste(self, evt):
		rdc.paste()


	def syncSelected(self):
		"""Sync the treeview's selection to the rdc."""
		if not rdc._inSelection:
			rdc.SelectedObjects = [obj.ReportObject for obj in self.Selection]

		
	def onHit(self, evt):
		self.syncSelected()


	def onContextMenu(self, evt):
		evt.stop()
		self.syncSelected()
		self.showContextMenu(rdc.getContextMenu(mousePosition=evt.EventData["mousePosition"]))


	def refreshTree(self):
		"""Constructs the tree of report objects."""
		self.clear()
		self.recurseLayout()
		self.expandAll()

	def recurseLayout(self, frm=None, parentNode=None):
		rd = rdc.ActiveEditor
		rw = rd._rw
		rf = rdc.ReportForm

		if rf is None:
			# No form to recurse
			return

		fontSize = 8

		if frm is None:
			frm = rf
			parentNode = self.setRootNode(frm.__class__.__name__)
			parentNode.FontSize = fontSize
			parentNode.ReportObject = frm
			elements = frm.keys()
			elements.sort(rw._elementSort)
			for name in elements:
				self.recurseLayout(frm=frm[name], parentNode=parentNode)
			return

		if isinstance(frm, dict):
			node = parentNode.appendChild(self.getNodeCaption(frm))
			node.ReportObject = frm
			node.FontSize = fontSize
			for child in frm.get("Objects", []):
				self.recurseLayout(frm=child, parentNode=node)
			for band in ("GroupHeader", "GroupFooter"):
				if frm.has_key(band):
					self.recurseLayout(frm=frm[band], parentNode=node)

		elif frm.__class__.__name__ in ("Variables", "Groups", "TestCursor"):
			node = parentNode.appendChild(self.getNodeCaption(frm))
			node.ReportObject = frm
			node.FontSize = fontSize
			for child in frm:
				self.recurseLayout(frm=child, parentNode=node)						

	def getNodeCaption(self, frm):
		caption = frm.__class__.__name__
		if not frm.__class__.__name__ in ("Variables", "Groups", "TestCursor"):
			expr = rdc.getShortExpr(frm.get("expr", ""))
			if expr:
				if caption.lower() in ("group",):
					caption = expr
				elif caption.lower() in ("variable",):
					caption = frm.getProp("Name", evaluate=False)
				else:
					expr = ": %s" % expr
					caption = "%s%s" % (frm.__class__.__name__, expr)
		return caption

	def refreshSelection(self):
		"""Iterate through the nodes, and set their Selected status
		to match if they are in the current selection of controls.
		"""
		objList = rdc.SelectedObjects
		# First, make sure all selected objects are represented:
		for obj in objList:
			rep = False
			for node in self.nodes:
				if id(node.ReportObject) == id(obj):
					rep = True
					break
			if not rep:
				# Nope, the object isn't in the tree yet.
				self.refreshTree()
				break

		# Now select the proper nodes:
		selNodes = []
		for obj in objList:
			for node in self.nodes:
				if id(node.ReportObject) == id(obj):
					selNodes.append(node)

		self.Selection = selNodes
		
	def refreshCaption(self):
		"""Iterate the Selection, and refresh the Caption."""
		for node in self.Selection:
			node.Caption = self.getNodeCaption(node.ReportObject)

	
class ObjectTreeForm(DesignerControllerForm):
	def initProperties(self):
		ObjectTreeForm.doDefault()
		self.Caption = "Report Object Tree"
		self.EditorClass = ReportObjectTree

	def selectAll(self):
		rdc.selectAllObjects()


class ReportPropSheet(ClassDesignerPropSheet.PropSheet):
	def beforeInit(self):
		# The ClassDesignerPropSheet appears to need a self.app reference:
		self.app = rdc

	def afterInit(self):
		ReportPropSheet.doDefault()
		self.addObject(dabo.ui.dLabel, Name="lblType", FontBold=True)
		self.Sizer.insert(0, self.lblType, "expand", halign="left", border=10)
		self.Sizer.insertSpacer(0, 10)

	def getObjPropVal(self, obj, prop):
		return obj.getPropVal(prop)

	def getObjPropDoc(self, obj, prop):
		doc = obj.getPropDoc(prop)
		return self.formatDocString(doc)

	def updateVal(self, prop, val, typ):
		"""Called from the grid to notify that the current cell's
		value has been changed. Update the corresponding 
		property value.
		"""
		reInit = False

		if typ == "color":
			# need to convert from rgb to reportlab rgb, and stringify.
			val = rdc.ActiveEditor._rw.getReportLabColorTuple(val)
			val = "(%.3f, %.3f, %.3f)" % (val[0], val[1], val[2])
		for obj in self._selected:
			obj.setProp(prop, val)
			if isinstance(obj, Group) and prop.lower() == "expr":
				reInit = True
		rdc.ActiveEditor.propsChanged(reinit=reInit)
		if rdc.ObjectTree:
			rdc.ObjectTree.refreshCaption()
		if getattr(self.propGrid, "_focusToDesigner", False):
			rdc.ActiveEditor.Form.bringToFront()
			self.propGrid._focusToDesigner = False

	def refreshSelection(self):
		objs = rdc.SelectedObjects
		self.select(objs)

		if len(objs) > 1:
			typ = "-multiple selection-"
		elif len(objs) == 0:
			typ = "None"
		else:
			typ = objs[0].__class__.__name__
		self.lblType.Caption = typ

	def editColor(self, objs, prop, val):
		# Override base editColor: need to convert stringified rl tuple to 
		# rgb tuple.
		try:
			rgbTuple = eval(val)
		except:
			rgbTuple = None
		if rgbTuple is None:
			rgbTuple = (0, 0, 0)
		rgbTuple = rdc.ActiveEditor._rw.getColorTupleFromReportLab(rgbTuple)
		ReportPropSheet.doDefault(objs, prop, rgbTuple)
		

class PropSheetForm(DesignerControllerForm):
	def initProperties(self):
		PropSheetForm.doDefault()
		self.Caption = "Report Properties"
		self.EditorClass = ReportPropSheet



class DesignerPanel(dabo.ui.dPanel):
	def onGotFocus(self, evt):
		# Microsoft Windows gives the keyboard focus to sub-panels, which
		# really sucks. This takes care of it.
		rdc.ActiveEditor.SetFocusIgnoringChildren()
		

#------------------------------------------------------------------------------
#  BandLabel Class
# 
class BandLabel(DesignerPanel):
	"""Base class for the movable label at the bottom of each band.
	
	These are the bands like pageHeader, pageFooter, and detail that
	the user can drag up and down to make the band smaller or larger,
	respectively.
	"""
	def afterInit(self):
		self._dragging = False
		self._dragStart = (0,0)
		self._dragImage = None


	def copy(self):
		self.Parent.copy()

	def cut(self):
		self.Parent.cut()

	def paste(self):
		self.Parent.paste()


	def onMouseMove(self, evt):
		import wx  ## need to abstract DC and mouse cursors!!
		if self._dragging:
			self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))
			pos = evt.EventData["mousePosition"]
	
			if pos[1] != self._dragStart[1]:
				ypos = (self.Parent.Top + self.Top + pos[1] 
						- self._dragStart[1]    ## (correct for ypos in the band)
						+ 2)                    ## fudge factor


				if ypos < self.Parent.Top:
					# Don't show the band dragging above the topmost valid position:
					ypos = self.Parent.Top

				if self._dragImage is None:
					# Erase the band label, and instantiate the dragImage rendition of it.
					dc = wx.WindowDC(self)
					dc.Clear()

					self._dragImage = wx.DragImage(self._captureBitmap,
							wx.StockCursor(wx.CURSOR_HAND))

					self._dragImage.BeginDragBounded((self.Parent.Left, ypos), 
							self, self.Parent.Parent)
					self._dragImage.Show()

				self._dragImage.Move((self.Parent.Left,ypos))



	def onMouseLeftUp(self, evt):
		dragging = self._dragging
		self._dragging = False
		if dragging:
			if self._dragImage is not None:
				self._dragImage.EndDrag()
			self._dragImage = None
			pos = evt.EventData["mousePosition"]
			starty = self._dragStart[1]
			currenty = pos[1]
			yoffset = currenty - starty

			if yoffset != 0:
				z = self.Parent.Parent.ZoomFactor
				# dragging the band is changing the height of the band.
				oldHeight = self.Parent.getProp("Height")
				if oldHeight is not None:
					oldHeight = self.Parent._rw.getPt(oldHeight)
				else:
					# Height is None, meaning it is to stretch dynamically at runtime.
					# However, the user just overrode that by setting it explicitly.
					oldHeight = 75
				newHeight = round(oldHeight + (yoffset/z), 1)
				if newHeight < 0: newHeight = 0
				self.Parent.setProp("Height", newHeight)
			rdc.SelectedObjects = [self.Parent.ReportObject]


	def onMouseLeftDown(self, evt):
		if self.Application.Platform == "Mac":
			# Mac needs the following line, or LeftUp will never fire. TODO:
			# figure out how to abstract this into dPemMixin (if possible).
			# I posted a message to wxPython-mac regarding this - not sure if
			# it is a bug or a "by design" platform inconsistency.
			evt.stop()
		if not self.Parent.getProp("designerLock"):
			self._dragging = True
			self._dragStart = evt.EventData["mousePosition"]
			self._captureBitmap = self.getCaptureBitmap()


	def onMouseEnter(self, evt):
		import wx		## need to abstract mouse cursor

		if self.Parent.getProp("designerLock"):
			self.SetCursor(wx.NullCursor)
		else:
			self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENS))


	def onMouseLeftDoubleClick(self, evt):
		self.Parent._rd.editProperty("Height")


	def onPaint(self, evt):
		import wx		## (need to abstract DC drawing)
		dc = wx.PaintDC(self)
		rect = self.GetClientRect()
		font = self.Font

		dc.SetTextForeground(self.ForeColor)
		dc.SetBrush(wx.Brush(self.BackColor, wx.SOLID))
		dc.SetFont(font._nativeFont)
		dc.DrawRectangle(rect[0],rect[1],rect[2],rect[3])
		rect[0] = rect[0]+5
		rect[1] = rect[1]+1
		dc.DrawLabel(self.Caption, rect, wx.ALIGN_LEFT)


	def _getCaption(self):
		return self.Parent.Caption

	def _setCaption(self, val):
		self.Parent.Caption = val

	Caption = property(_getCaption, _setCaption)

#  End BandLabel Class
#
#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
#
#  Band Class
#
class DesignerBand(DesignerPanel):
	"""Base class for report bands.
	
	Bands contain any number of objects, which can receive the focus and be
	acted upon. Bands also manage their own BandLabels.
	"""
	def beforeInit(self):
		self._idleRefreshProps = False


	def initProperties(self):
		self.BackColor = (255,255,255)
		self.Top = 100


	def afterInit(self):
		self._cachedBitmaps = {}
		self._rd = self.Form.editor
		self._rw = self._rd._rw
		self.Bands = self._rw.Bands

		self._bandLabelHeight = 18
		self.addObject(BandLabel, "bandLabel", FontSize=9, 
				BackColor=(215,215,215), ForeColor=(128,128,128),
				Height=self._bandLabelHeight)

		self._anchorThickness = 5
		self._anchor = None
		self._mouseDown = False
		self._mousePosition = (0,0)
		self._mouseDragMode = ""

		self._dragging = False
		self._dragStart = (0,0)
		self._dragObject = None

		self._captureBitmap = None


	def copy(self):
		self.Parent.copy()

	def cut(self):
		self.Parent.cut()

	def paste(self):
		self.Parent.paste()


	def onContextMenu(self, evt):
		evt.stop()
		self.updateSelected()
		self.showContextMenu(rdc.getContextMenu(evt.EventData["mousePosition"]))


	def onMouseLeftDoubleClick(self, evt):
		mouseObj = self.getMouseObject()
		propName = None
		for prop in ("expr",):
			if prop in mouseObj.AvailableProps:
				propName = prop
				break
		self._rd.editProperty(propName)


	def onMouseMove(self, evt):
		import wx  ## need to abstract DC and mouse cursors!!
		if self._mouseDown:
			if not self._dragging:
				self._dragging = True
				self._dragStart = evt.EventData["mousePosition"]
		else:
			self._setMouseMoveMode(evt.EventData["mousePosition"])
		
		evt.stop()
				

	def onMouseLeftUp(self, evt):
		self._mouseDown = False
		dragging = self._dragging
		dragObject = self._dragObject
		self._dragging, self._dragObject = False, None

		if dragging and dragObject is not None and self._mouseDragMode == "moving":
			pos = evt.EventData["mousePosition"]

			offset = {"x": pos[0] - self._dragStart[0],
					"y": -1*(pos[1] - self._dragStart[1])}

			if offset["x"] != 0 or offset["y"] !=0:
				z = self.Parent.ZoomFactor
				# dragging the object is moving it to a new position.
				for propName in ("x", "y"):
					old = dragObject.getProp(propName)

					unit = "pt"
					if isinstance(old, basestring) and len(old) > 3:
						if old[-4] == "pica":
							unit = "pica"
						elif old[-2].isalpha():
							unit = old[-2:]
					old = self._rw.getPt(old)

					new = round(old + (offset[propName]/z), 1)
					if new < 0:
						new = 0
					new = self._rw.ptToUnit(new, unit)
					dragObject.setProp(propName, repr(new))
			self.refresh()
			rdc.refreshProps(refreshEditor=False)



	def onMouseLeftDown(self, evt):
		self.updateSelected(evt)
		# If we let the default event handler run, self.SetFocus() will happen,
		# which we want so that we can receive keyboard focus, but SetFocus() has
		# the side-effect of also scrolling the panel in both directions, for some
		# reason. So, we need to work around this annoyance and call SetFocus()
		# manually:
		evt.stop()
		vs = self.Parent.GetViewStart() 
		self.SetFocus()
		self.Parent.Scroll(*vs)

		self._mouseDown = True
		mouseObj = self.getMouseObject()
		if not isinstance(mouseObj, Band):
			self._dragObject = mouseObj
		self._mousePosition = evt.EventData["mousePosition"]


	def _setMouseMoveMode(self, pos):
		import wx
		mouseObj = self.getMouseObject()

		if not isinstance(mouseObj, Band) and mouseObj in rdc.SelectedObjects \
				and not mouseObj.getProp("designerLock"):
			self._anchor = self._mouseOnAnchor(pos) 
			if self._anchor is not None:
				self._mouseDragMode = "sizing"
				self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
			else:
				self._mouseDragMode = "moving"
				self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENWSE))
		else:
			self._anchor = None
			self._mouseDragMode = None
			self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))


	def _mouseOnAnchor(self, pos):
		"""Return the anchor that the mouse is on, or None."""
		mouseObj = self.getMouseObject()
		if mouseObj is None or isinstance(mouseObj, Band):
			return None

		for k,v in mouseObj._anchors.items():
			minx, miny = v[2] - self._anchorThickness, v[3] - self._anchorThickness
			maxx, maxy = v[2] + self._anchorThickness, v[3] + self._anchorThickness
			if (minx < pos[0] and maxx > pos[0]) and (miny < pos[1] and maxy > pos[1]):
				return k
		return None


	def getMouseObject(self):
		"""Returns the topmost object underneath the mouse."""
		rw = self.Parent._rw
		objs = copy.copy(self.ReportObject.get("Objects", []))
		objs.reverse()  ## top of z order to bottom
		mouseObj = self.ReportObject  ## the band
		mousePos = self.getMousePosition()

		for obj in objs:
			size, position = self.getObjSizeAndPosition(obj)
			if isinstance(obj, SpanningLine):
				# Allow the object to be selected when clicked on by adding some sensitivity
				size = list(size)
				position = list(position)
				size[0] += 2
				size[1] += 2
				position[0] -= 1
				position[1] -= 1
			if mousePos[0] >= position[0] and mousePos[0] <= position[0] + size[0] \
					and mousePos[1] >= position[1] and mousePos[1] <= position[1] + size[1]:			
				mouseObj = obj
				break
		return mouseObj


	def updateSelected(self, evt=None):
		mouseObj = self.getMouseObject()

		selectedObjs = rdc.SelectedObjects

		if evt and (evt.EventData["controlDown"] or evt.EventData["shiftDown"]):
			# toggle selection of the selObj
			if mouseObj in selectedObjs:
				selectedObjs.remove(mouseObj)
			else:
				selectedObjs.append(mouseObj)
		else:
			# replace selection with the selObj
			selectedObjs = [mouseObj]

		rdc.SelectedObjects = selectedObjs

	
	def getObjSizeAndPosition(self, obj):
		"""Return the size and position needed to draw the object at the current zoom factor."""
		rw = self._rw
		z = self.Parent.ZoomFactor
		x = rw.getPt(obj.getProp("x"))
		y_ = rw.getPt(obj.getProp("y"))
		y = ((self.Height - self._bandLabelHeight)/z) - y_

		if isinstance(obj, (SpanningLine, SpanningRectangle)):
			xFooter = rw.getPt(obj.getProp("xFooter"))
			yFooter = rw.getPt(obj.getProp("yFooter"))
			width = xFooter - x
			height = y_  ## currently can't draw down to the footer because painting doesn't cross panels
		else:
			width = rw.getPt(obj.getProp("Width"))
			height = obj.getProp("Height")
			hAnchor = obj.getProp("hAnchor").lower()
			vAnchor = obj.getProp("vAnchor").lower()

			if height is None:
				# dynamic height. Fake it here for now:
				height = 23
	
			if hAnchor == "right":
				x = x - width
			elif hAnchor == "center":
				x = x - (width/2)
	
			if vAnchor == "top":
				y = y + height
			elif vAnchor == "middle":
				y = y + (height/2)

		height = rw.getPt(height)

		size = (z*width, z*height)
		if isinstance(obj, (SpanningLine, SpanningRectangle)):
			position = (z*x, z*y)
		else:
			position = (z*x, (z*y) - (z*height))
		return (size, position)


	def getPositionText(self):
		if self.getProp("designerLock"):
			locktext = "(locked)"
		else:
			locktext = ""
		cap = "(%s) height:%s %s" % (self.ReportObject.__class__.__name__, 
				self.getProp("Height"), locktext)
		return cap


	def onPaint(self, evt):
		import wx		## (need to abstract DC drawing)

		dc = wx.PaintDC(self)
		dc.Clear()

		for obj in self.ReportObject.get("Objects", []):
			self._paintObj(obj, dc)

		dc.DestroyClippingRegion()

		columnCount = rdc.ReportForm.getProp("ColumnCount")
		if isinstance(self.ReportObject, (Detail, GroupHeader, GroupFooter)) \
				and columnCount > 1:
			# Cover up all but the first column:
			dc.SetBrush(wx.Brush((192,192,192), wx.SOLID))
			dc.SetPen(wx.Pen((192,192,192), 0, wx.SOLID))
			colWidth = self.Width / columnCount
			dc.DrawRectangle(colWidth, 0, colWidth*(columnCount-1) + 10, self.Height)


	def _paintObj(self, obj, dc=None):
		import wx

		obj._anchors = {}
		objType = obj.__class__.__name__
		selectColor = (128,192,0)

		size, position = self.getObjSizeAndPosition(obj)
		rect = [position[0], position[1], size[0], size[1]]

		dc.DestroyClippingRegion()

		dc.SetBrush(wx.Brush((0,0,0), wx.TRANSPARENT))
		dc.SetPen(wx.Pen(selectColor, 0.1, wx.DOT))
		dc.DrawRectangle(position[0], position[1], size[0], size[1])


		if objType == "String":
			dc.SetBackgroundMode(wx.TRANSPARENT)
			expr = rdc.getShortExpr(obj.getProp("expr", evaluate=False))
			alignments = {"left": wx.ALIGN_LEFT,
					"center": wx.ALIGN_CENTER,
					"right": wx.ALIGN_RIGHT,}

			alignment = obj.getProp("align")
			fontName = obj.getProp("fontName")
			fontSize = obj.getProp("fontSize")
			rotation = obj.getProp("rotation")

			z = self.Parent.Zoom

			if "helvetica" in fontName.lower():
				fontFamily = wx.MODERN
				fontBold = "bold" in fontName.lower()
				fontItalic = "oblique" in fontName.lower()
				fontName = "Helvetica"
			elif "times" in fontName.lower():
				fontFamily = wx.ROMAN
				fontBold = "bold" in fontName.lower()
				fontItalic = "italic" in fontName.lower()
				fontName = "Times"
			elif "courier" in fontName.lower():
				fontFamily = wx.TELETYPE
				fontBold = "bold" in fontName.lower()
				fontItalic = "oblique" in fontName.lower()
				fontName = "Courier"
			elif "symbol" in fontName.lower():
				fontFamily = wx.DEFAULT
				fontBold = False
				fontItalic = False
				fontName = "Symbol"
			elif "zapfdingbats" in fontName.lower():
				fontFamily = wx.DEFAULT
				fontBold = False
				fontItalic = False
				fontName = "ZapfDingbats"
			else:
				fontName = "Helvetica"
				fontFamily = wx.MODERN
				fontBold = False
				fontItalic = False

			# Can't seem to get different faces represented
			font = dabo.ui.dFont()
			font._nativeFont.SetFamily(fontFamily)
			font.Bold = fontBold
			font.Italic = fontItalic
			font.Face = fontName
			font.Size = fontSize * z

			dc.SetFont(font._nativeFont)
			dc.SetTextForeground(self._rw.getColorTupleFromReportLab(obj.getProp("fontColor")))

			top_fudge = .5   ## wx draws a tad too high
			left_fudge = .25  ## and a tad too far to the left
			# We need the y value to match up with the font at the baseline, but to clip
			# the entire region, including descent.
			descent = dc.GetFullTextExtent(expr)[2]
			rect[0] += left_fudge
			rect[2] += left_fudge
			rect[1] += top_fudge
			rect[3] += top_fudge + descent
			dc.SetClippingRect(rect)

			if False and rotation != 0:
				# We lose the ability to have the alignment and exact rect positioning.
				# But we get to show it rotated. The x,y values below are hacks.
				dc.DrawRotatedText(expr, rect[0]+(rect[2]/4), rect[3] - (rect[3]/2), rotation)
			else:
				dc.DrawLabel(expr, (rect[0], rect[1], rect[2], rect[3]),
						alignments[alignment]|wx.ALIGN_BOTTOM)


		if objType in ("Rectangle", "SpanningRectangle"):
			strokeWidth = self._rw.getPt(obj.getProp("strokeWidth")) * self.Parent.Zoom
			sc = obj.getProp("strokeColor")
			if sc is None:
				sc = (0, 0, 0)
			strokeColor = self._rw.getColorTupleFromReportLab(sc)
			fillColor = obj.getProp("fillColor")
			if fillColor is not None:
				fillColor = self._rw.getColorTupleFromReportLab(fillColor)
				fillMode = wx.SOLID
			else:
				fillColor = (255, 255, 255)
				fillMode = wx.TRANSPARENT
			dc.SetPen(wx.Pen(strokeColor, strokeWidth, wx.SOLID))
			dc.SetBrush(wx.Brush(fillColor, fillMode))
			dc.DrawRectangle(rect[0],rect[1],rect[2],rect[3])


		if objType in ("Line", "SpanningLine"):
			strokeWidth = self._rw.getPt(obj.getProp("strokeWidth")) * self.Parent.Zoom
			strokeColor = self._rw.getColorTupleFromReportLab(obj.getProp("strokeColor"))
			dc.SetPen(wx.Pen(strokeColor, strokeWidth, wx.SOLID))

			if objType != "SpanningLine":
				lineSlant = obj.getProp("lineSlant")
				anchors = {"left": rect[0],
						"center": rect[0] + (rect[2]/2),
						"right": rect[0] + rect[2],
						"top": rect[1],
						"middle": rect[1] + (rect[3]/2),
						"bottom": rect[1] + rect[3]}

				if lineSlant == "-":
					# draw line from (left,middle) to (right,middle) anchors
					beg = (anchors["left"], anchors["middle"])
					end = (anchors["right"], anchors["middle"])
				elif lineSlant == "|":
					# draw line from (center,bottom) to (center,top) anchors
					beg = (anchors["center"], anchors["bottom"])
					end = (anchors["center"], anchors["top"])
				elif lineSlant == "\\":
					# draw line from (right,bottom) to (left,top) anchors
					beg = (anchors["right"], anchors["bottom"])
					end = (anchors["left"], anchors["top"])
				elif lineSlant == "/":
					# draw line from (left,bottom) to (right,top) anchors
					beg = (anchors["left"], anchors["bottom"])
					end = (anchors["right"], anchors["top"])
				else:
					# don't draw the line
					lineSlant = None

			if objType == "SpanningLine":
				rect = [rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]]
				dc.DrawLine(*rect)
			elif lineSlant:
				dc.DrawLine(beg[0], beg[1], end[0], end[1])


		if objType == "Image":
			bmp = None
			expr = obj.getProp("expr", evaluate=False)
			if expr is None:
				expr = "<< missing expression >>"
			else:
				try:
					imageFile = eval(expr)
				except:
					imageFile = None

				if imageFile is not None:
					if not os.path.exists(imageFile):
						imageFile = os.path.join(self._rw.HomeDirectory, imageFile)
					imageFile = str(imageFile)

				if imageFile is not None:
					if os.path.exists(imageFile) and not os.path.isdir(imageFile):
						bmp = self._cachedBitmaps.get((imageFile, self.Parent.ZoomFactor), None)
						if bmp is None:
							import wx
							expr = None
							img = wx.Image(imageFile)
							## Whether rescaling, resizing, or nothing happens depends on the 
							## scalemode prop. For now, we just unconditionally rescale:
							img.Rescale(rect[2], rect[3])
							bmp = img.ConvertToBitmap()
							self._cachedBitmaps[(imageFile, self.Parent.ZoomFactor)] = bmp
					else:
						expr = "<< file not found >>"
				else:
					expr = "<< error parsing expr >>"
			if bmp is not None:
				dc.DrawBitmap(bmp, rect[0], rect[1])
			else:
				dc.DrawLabel(expr, (rect[0]+2, rect[1], rect[2]-4, rect[3]), wx.ALIGN_LEFT)

		dc.SetBrush(wx.Brush((0,0,0), wx.TRANSPARENT))

		# Draw a border around the object, if appropriate:
		if obj.has_key("BorderWidth"):
			borderWidth = self._rw.getPt(obj.getProp("BorderWidth")) * self.Parent.Zoom
			if borderWidth > 0:
				borderColor = self._rw.getColorTupleFromReportLab(obj.getProp("BorderColor"))
				dc.SetPen(wx.Pen(borderColor, borderWidth, wx.SOLID))
				dc.DrawRectangle(rect[0],rect[1],rect[2],rect[3])
	
		if rdc.isSelected(obj):
			rect = (position[0], position[1], size[0], size[1])
			# border around selected control with sizer boxes:
			dc.SetBrush(wx.Brush((0,0,0), wx.TRANSPARENT))
			dc.SetPen(wx.Pen(selectColor, 0.25, wx.SOLID))
			dc.DrawRectangle(rect[0],rect[1],rect[2],rect[3])

			x,y = (rect[0], rect[1])
			width, height = (rect[2], rect[3])
			thickness = self._anchorThickness

			if "hAnchor" in obj:
				hAnchor = obj.getProp("hAnchor").lower()
			else:
				hAnchor = "left"

			if "vAnchor" in obj:
				vAnchor = obj.getProp("vAnchor").lower()
			else:
				vAnchor = "top"

			anchors = {"lt": ["left", "top", x-1, y-1],
					"lb": ["left", "bottom", x-1, y+height-thickness+1],
					"ct": ["center", "top", x+(.5*width)-(.5*thickness), y-1],
					"cb": ["center", "bottom", x+(.5*width)-(.5*thickness), y+height-thickness+1],
					"rt": ["right", "top", x+width-thickness+1, y-1],
					"rb": ["right", "bottom", x+width-thickness+1, y+height-thickness+1],
					"lm": ["left", "middle", x-1, y+(.5*height)-(.5*thickness)],
					"rm": ["right", "middle", x+width-thickness+1, y+(.5*height)-(.5*thickness)]}

			obj._anchors = anchors

			for k,v in anchors.items():
				dc.SetBrush(wx.Brush((0,0,0), wx.SOLID))
				dc.SetPen(wx.Pen((0,0,0), 0.25, wx.SOLID))
				if hAnchor == v[0] and vAnchor == v[1]:
					dc.SetBrush(wx.Brush(selectColor, wx.SOLID))
					dc.SetPen(wx.Pen(selectColor, 1, wx.SOLID))
				dc.DrawRectangle(v[2], v[3], thickness, thickness)


	def getProp(self, prop, evaluate=True, fillDefault=True):
		if evaluate and fillDefault:
			# The report object can do it all:
			return self.ReportObject.getProp(prop)

		try:
			val = self.ReportObject[prop]
		except KeyError:
			if fillDefault:
				val = self.ReportObject.AvailableProps.get(prop)["default"]

		if val is not None and evaluate:
			try:
				vale = eval(val)
			except:
				vale = "?: %s" % str(val)
		else:
			vale = val
		return vale


	def setProp(self, prop, val, sendPropsChanged=True):
		"""Set the specified object property to the specified value.

		If setting more than one property, self.setProps() is faster.
		"""
		self.ReportObject.setProp(prop, str(val))
		if sendPropsChanged:
			self.Parent.propsChanged()


	def setProps(self, propvaldict):
		"""Set the specified object properties to the specified values."""
		for p,v in propvaldict.items():
			self.setProp(p, v, False)
		self.Parent.propsChanged()


	def _getCaption(self):
		try:
			v = self._caption
		except AttributeError:
			v = ""
		return v

	def _setCaption(self, val):
		self._caption = val


	Caption = property(_getCaption, _setCaption)

#  End Band Class
#
#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
#
#  ReportDesigner Class
#
class ReportDesigner(dabo.ui.dScrollPanel):
	"""Main report designer panel.
	
	This is the main report designer panel that contains the bands and
	handles setting properties on report objects. While a given object is
	considered to be owned by a particular band, the report designer still
	controls the placement of the object because, among other things, a given
	object can cross bands (a rectangle extending from the group header to the
	group footer, for instance) or move from one band to another.
	"""
	def __init__(self, *args, **kwargs):
		import wx
		kwargs["style"] = wx.WANTS_CHARS
		super(ReportDesigner, self).__init__(*args, **kwargs)

	def afterInit(self):
		self._bands = []
		self._rulers = {}
		self._zoom = self._normalZoom = 1.0
		self._clipboard = []
		self._fileName = ""
		self.BackColor = (192,192,192)
		self.clearReportForm()

		self.Form.bindEvent(dEvents.Resize, self._onFormResize)

	def onMouseLeftClick(self, evt):
		rdc.SelectedObjects = [rdc.ReportForm]


	def onKeyDown(self, evt):
		# We are going to steal the arrow keys, so make sure we really have the
		# focus and there are valid drawable objects selected.
		if self.Form.pgf.SelectedPageNumber != 0:
			return

		selectedDrawables = []
		for obj in rdc.SelectedObjects:
			if isinstance(obj, Drawable):
				selectedDrawables.append(obj)

		# Now check to see that the keycode matches the keys we are interested in
		# intercepting:
		keys = {dKeys.key_Up: "up",
				dKeys.key_Down: "down", 
				dKeys.key_Right: "right",
				dKeys.key_Left: "left",
				dKeys.key_Return: "enter",
				dKeys.key_Tab: "tab",
				396: "/",
				394: "-",
				392: "+"}

		keyCode = evt.EventData["keyCode"]
		if not keys.has_key(keyCode):
			return

		# Okay, we have valid item(s) selected, and it is a key we are interested in.
		shiftDown = evt.EventData["shiftDown"]
		ctrlDown = evt.EventData["controlDown"]
		altDown = evt.EventData["altDown"]
		metaDown = evt.EventData["metaDown"]
		key = keys[keyCode]

		if key == "tab" and (not ctrlDown and not altDown):
			evt.stop()
			selObj = []
			if len(selectedDrawables) > 1:
				# Multiple selected; don't tab traverse; select the first drawable.
				selObj = [selectedDrawables[0],]
			elif not selectedDrawables:
				# No objects selected; select first drawable in selected band,
				# or if no band selected, in the detail band:
				def getNextDrawableInBand(band):
					objs = band.get("Objects", [])
					for obj in objs:
						if isinstance(obj, Drawable):
							return obj

				if len(rdc.SelectedObjects) == 1 \
						and isinstance(rdc.SelectedObjects[0], Band):
					selObj = [getNextDrawableInBand(rdc.SelectedObjects[0])]
				if not selObj:
					selObj = [getNextDrawableInBand(rdc.ReportForm["Detail"])]
				
			else:
				# One object selected; change selection to next/prior drawable.
				if shiftDown:
					selObj = [rdc.getPriorDrawable(selectedDrawables[0])]
				else:
					selObj = [rdc.getNextDrawable(selectedDrawables[0])]
			if selObj[0] is None:
				selObj = [rdc.ReportForm]

			# In order to draw quickly with the paint knowing the object is selected,
			# we manipulate the attribute instead of the property:
			rdc.ActiveEditor._selectedObjects = selObj
			if selObj[0] != rdc.ReportForm:
				rdc.getParentBand(selObj[0]).DesignerObject.refresh()

			# delay the refreshing of the property grid/position:
			rdc.refreshSelection()
			return


		if ctrlDown and not altDown and not shiftDown and not metaDown:
			## On Windows, the accelerators set up for the zooming aren't working.
			## I have no idea why, because in dEditor the same setup is working fine.
			## Anyway, this code makes keyboard zooming work on Windows.
			accel = {"+": self.Form.onViewZoomIn,
					"-": self.Form.onViewZoomOut,
					"/": self.Form.onViewZoomNormal}
			func = accel.get(key)
			if func:
				evt.stop()
				func(None)
				return

		if not selectedDrawables:
			return

		if key == "enter":
			# Bring the prop sheet to top and activate the editor for the
			# most appropriate property for the selected object(s).
			evt.stop()
			propName = None
			for prop in ("expr",):
				if prop in selectedDrawables[0].AvailableProps:
					propName = prop
					break
			self.editProperty(propName)

		else:
			## arrow key
			evt.stop()  ## don't let the arrow key scroll the window.
			size, turbo = False, False
			if shiftDown:
				if key in ["up", "down"]:
					propName = "height"
				else:
					propName = "width"
			else:
				if key in ["up", "down"]:
					propName = "y"
				else:
					propName = "x"
			
			if key in ["up", "right"]:
				adj = 1
			else:
				adj = -1
						
			if ctrlDown:
				adj = adj * 10
	
			parentBands = []				
			for o in rdc.SelectedObjects:
				if not isinstance(o, Drawable) or o.getProp("designerLock"):
					continue

				propNames = [propName]
				if isinstance(o, (SpanningLine, SpanningRectangle)):
					if propName == "x":
						propNames.append("xFooter")
					if propName == "width":
						propNames = ["xFooter"]
					if propName == "height":
						propNames = ["yFooter"]

				for propName in propNames:
					val = o.getProp(propName)
					unit = "pt"
		
					parentBand = rdc.getParentBand(o)
					if parentBand not in parentBands:
						parentBands.append(parentBand)

					if isinstance(val, basestring) and len(val) > 3:
						if val[-4] == "pica":
							unit = "pica"
						elif val[-2].isalpha():
							unit = val[-2:]

					val = self._rw.getPt(val)
					newval = val + adj
					newval = self._rw.ptToUnit(newval, unit)

					if propName.lower() in ("width", "height") and self._rw.getPt(newval) < 0:
						# don't allow width or height to be negative
						newval = "0 pt"
					o.setProp(propName, repr(newval))

			for bandObj in parentBands:
				# refresh the parent bands immediately to reflect the drawing:
				bandObj.DesignerObject.refresh()

			# Don't refresh() because that takes too long for no reason:	
			self.showPosition()
			self.setCaption()

			# delay the refreshing of the property grid/position:
			rdc.refreshProps(refreshEditor=False)


	def refresh(self):
		ReportDesigner.doDefault()
		self.showPosition()
		self.setCaption()


	def showPosition(self):
		"""If one object is selected, show its position and size."""
		# selected objects could include non-visible. Filter these out.
		so = [o for o in rdc.SelectedObjects if isinstance(o, (Drawable, Band))]

		if len(so) == 1:
			so = so[0]
			if isinstance(so, Band):
				do = getattr(so, "DesignerObject", None)
				if do:
					st = do.getPositionText()
				else:
					st = ""
			else:
				if isinstance(so, (SpanningLine, SpanningRectangle)):
					st = "x:%s y:%s  xFooter:%s yFooter:%s" % (so.getProp("x"),
							so.getProp("y"), so.getProp("xFooter"), so.getProp("yFooter"))
				else:
					st = "x:%s y:%s  width:%s height:%s" % (so.getProp("x"),
							so.getProp("y"), so.getProp("width"), so.getProp("Height"))
		elif len(so) > 1:
			st = " -multiple objects selected- "
		else:
			st = ""

		st += " Zoom: %s" % self.ZoomPercent
		self.Form.setStatusText(st)


	def clearReportForm(self):
		"""Called from afterInit and closeFile to clear the report form."""
		for o in self._rulers.values():
			o.Destroy()
		self._rulers = {}
		for o in self._bands:
			o.release()
		self._bands = []
		if not hasattr(self, "_rw"):
			self._rw = dReportWriter()


	def objectTree(self, obj=None):
		"""Display the object Tree for the passed object."""
		if obj is None:
			obj = self
		rw = self._rw

		rdc.showObjectTree(bringToTop=True, refresh=True)


	def editProperty(self, prop=None):
		"""Display the property dialog, and bring it to top.

		If a valid propname is passed, start the editor for that property.
		After the property is edited, send focus back to the designer.
		"""
		rdc.showPropSheet(bringToTop=True, prop=prop, enableEditor=True,
		                  focusBack=True)


	def promptToSave(self):
		"""Decides whether user should be prompted to save, and whether to save."""
		result = True
		if self._rw._isModified():
			result = dabo.ui.areYouSure("Save changes to file %s?" 
					% self._fileName)
			if result:
				self.saveFile()
		return result


	def promptForFileName(self, prompt="Select a file", saveDialog=False):
		"""Prompt the user for a file name."""
		import wx   ## need to abstract getFile()
		try:
			dir_ = self._curdir
		except:
			dir_ = ""
	
		if saveDialog:
			style = wx.SAVE
		else:
			style = wx.OPEN

		dlg = wx.FileDialog(self, 
			message = prompt,
			defaultDir = dir_, 
			style = style,
			wildcard="Dabo Report Forms (*.rfxml)|*.rfxml|All Files (*)|*")

		if dlg.ShowModal() == wx.ID_OK:
			fname = dlg.GetPath()
		else:
			fname = None
		dlg.Destroy()
		return fname


	def promptForSaveAs(self):
		"""Prompt user for the filename to save the file as.
		
		If the file exists, confirm with the user that they really want to
		overwrite.
		"""
		while True:
			fname = self.promptForFileName(prompt="Save As", saveDialog=True)
			if fname is None:
				break
			if os.path.exists(fname):
				r = dabo.ui.areYouSure("File '%s' already exists. "
					"Do you want to overwrite it?" % fname, defaultNo=True)
					
				if r is None:
					# user canceled.
					fname = None
					break
				elif r == False:
					# let user pick another file
					pass
				else:
					# User chose to overwrite fname
					break
			else:
				break
		
		return fname


	def saveFile(self, fileSpec=None):
		if fileSpec is None:
			fileSpec = self._fileName
			if not fileSpec or fileSpec == NEW_FILE_CAPTION:
				fileSpec = self.promptForSaveAs()
				if fileSpec is None:
					return False
		self._fileName = fileSpec
		xml = self._rw._getXMLFromForm(self._rw.ReportForm)
		file(fileSpec, "wb").write(xml.encode(dabo.defaultEncoding))
		self._rw._setMemento()
		self.setCaption()



	def closeFile(self):
		result = self.promptToSave()

		if result is not None:
			self._rw.ReportFormFile = None
			self.clearReportForm()
			self._fileName = ""
		return result


	def setCaption(self):
		"""Sets the form's caption based on file name, whether modified, etc."""
		if not hasattr(self, "_rw"):
			# We simply aren't fully initialized yet.
			return

		if self._rw._isModified():
			modstr = "* "
		else:
			modstr = ""
		self.Form.Caption = "%s%s: %s" % (modstr,
				self.Form._captionBase,
				self._fileName)


	def newFile(self):
		if self.closeFile():
			self._rw.ReportForm = self._rw._getEmptyForm()
			self.initReportForm()
			self._fileName = NEW_FILE_CAPTION
		rdc.ActiveEditor = self
		rdc.SelectedObjects = [self._rw.ReportForm]

	def openFile(self, fileSpec):
		if os.path.exists(fileSpec):
			if self.closeFile():
				self._rw.ReportFormFile = fileSpec
				self.initReportForm()
				self._fileName = fileSpec
			rdc.ActiveEditor = self
			rdc.SelectedObjects = [self._rw.ReportForm]
		else:
			raise ValueError("File %s does not exist." % fileSpec)
		return True

	def reInitReportForm(self):
		"""Clear the report form and redraw from scratch."""
		rf = self._rw.ReportForm
		self.clearReportForm()
		self._rw.ReportForm = rf
		self.initReportForm()

	def initReportForm(self):
		"""Called from openFile and newFile when time to set up the Report Form."""
		rf = self.ReportForm
		self._rw.UseTestCursor = True

		self._rulers = {}
		self._rulers["top"] = self.getRuler("h")
		self._rulers["bottom"] = self.getRuler("h")

		def addBand(bandObj):
			caption = bandObj.__class__.__name__
			if isinstance(bandObj, (GroupHeader, GroupFooter)):
				caption = "%s: %s" % (caption, bandObj.parent.get("expr"))
			self._rulers["%s-left" % caption] = self.getRuler("v")
			self._rulers["%s-right" % caption] = self.getRuler("v")
			b = DesignerBand(self, Caption=caption)
			b.ReportObject = bandObj
			bandObj.DesignerObject = b
			b._rw = self._rw
			self._bands.append(b)

		addBand(rf["PageHeader"])

		groups = copy.copy(rf["Groups"])
		for groupObj in groups:
			addBand(groupObj["GroupHeader"])

		addBand(rf["Detail"])

		groups.reverse()
		for groupObj in groups:
			addBand(groupObj["GroupFooter"])

		addBand(rf["PageFooter"])
		addBand(rf["PageBackground"])			
		addBand(rf["PageForeground"])			

		#self._rw.write()  ## 12/16/2008: No need to write the report form at this time.
		self._rw.write()   ## 02/25/2009: Some cases it is needed, and could be Rodgy's problem with TestCursor.
		self.drawReportForm()


	def propsChanged(self, redraw=True, reinit=False):
		"""Called by subobjects to notify the report designer that a prop has changed."""
		if reinit:
			self._rw._clearMemento = False
			self.reInitReportForm()
			self._rw._clearMemento = True
		if redraw:
			self.drawReportForm()
		self.Form.setModified(self)
		rdc.refreshProps()
		
	def _onFormResize(self, evt):
		self.drawReportForm()

	def drawReportForm(self):
		"""Resize and position the bands accordingly, and draw the objects."""
		viewStart = self.GetViewStart()
		self.SetScrollbars(0,0,0,0)
		rw = self._rw
		rf = self.ReportForm
		z = self.ZoomFactor

		if rf is None:
			return

		pointPageWidth = rw.getPageSize()[0]
		pageWidth = pointPageWidth * z
		ml = rw.getPt(rf["page"].getProp("marginLeft")) * z
		mr = rw.getPt(rf["page"].getProp("marginRight")) * z
		mt = rw.getPt(rf["page"].getProp("marginTop")) * z
		mb = rw.getPt(rf["page"].getProp("marginBottom")) * z
		bandWidth = pageWidth - ml - mr

		tr = self._rulers["top"]
		tr.Length = pageWidth
		tr.pointLength = pointPageWidth
		tr.rulerPos = "t"

		for index in range(len(self._bands)):
			band = self._bands[index]
			band.Width = bandWidth
			b = band.bandLabel
			b.Width = band.Width
			b.Left = 0  ## (for some reason, it defaults to -1)

			bandHeight = band.ReportObject.getProp("Height")
			if bandHeight is None:
				# dynamic band height: size of band determined at runtime. For now, fake it.
				bandHeight = 75	
			pointLength = (band._rw.getPt(bandHeight))
			bandCanvasHeight = z * pointLength
			band.Height = bandCanvasHeight + b.Height
			b.Top = band.Height - b.Height

			if index == 0:
				band.Top = mt + tr.Height
			else:
				band.Top = self._bands[index-1].Top + self._bands[index-1].Height

			lr = self._rulers["%s-left" % band.Caption]
			lr.Length = bandCanvasHeight
			lr.pointLength = pointLength
			lr.rulerPos = "l"
			
			rr = self._rulers["%s-right" % band.Caption]
			rr.Length = bandCanvasHeight
			rr.pointLength = pointLength
			rr.rulerPos = "r"

			band.Left = ml + lr.Thickness
			lr.Position = (0, band.Top)
			rr.Position = (lr.Width + pageWidth, band.Top)
			totPageHeight = band.Top + band.Height

		u = 10
		totPageHeight = totPageHeight + mb

		br = self._rulers["bottom"]
		br.Length = pageWidth
		br.pointLength = pointPageWidth
		br.rulerPos = "b"

		tr.Position = (lr.Width,0)
		br.Position = (lr.Width, totPageHeight)
		totPageHeight += br.Height

		_scrollWidth = (pageWidth + lr.Width + rr.Width) / u
		_scrollHeight = totPageHeight / u
		
		## pkm: Originally, I used just a SetScrollbars() call
		##      along with the arguments for scroll position.
		##      But on Windows, that resulted in the report
		##      drawing on the panel at the wrong offset. 
		##      Separating into these 2 calls fixed the issue.
		self._scrollRate = (u, u)
		self.SetScrollbars(u, u, _scrollWidth, _scrollHeight)
		self.Scroll(viewStart[0], viewStart[1])

		self.showPosition()


	def getRuler(self, orientation):
		defaultThickness = 20
		defaultLength = 1

		rd = self

		class Ruler(DesignerPanel):
			def initProperties(self):
				self.BackColor = (192,128,192)
				self._orientation = orientation[0].lower()
				self.pointLength = 0

			def copy(self):
				return self.Parent.copy()

			def paste(self):
				return self.Parent.paste()

			def cut(self):
				return self.Parent.cut()


			def onPaint(self, evt):
				import wx		## (need to abstract DC drawing)

				z = rd.ZoomFactor

				ruleColor = (0,0,0)
				ruleSizes = {}
				ruleSizes["small"] = 5 ##self.Thickness / 4.0
				ruleSizes["medium"] = 10 ##self.Thickness / 2.0
				ruleSizes["large"] = 15 ##self.Thickness - (self.Thickness / 4)
				unit = "pt"

				size = {}
				if unit == "pt":
					if z > 2.4:
						smallest = 1
					elif z > 1:
						smallest = 5
					else:
						smallest = 10
					size["small"] = 1
					size["medium"] = 10
					size["large"] = 100

				dc = wx.PaintDC(self)
				dc.SetPen(wx.Pen(ruleColor, 0.25, wx.SOLID))

				length = self.Length
				pointLength = self.pointLength
				rulerPos = self.rulerPos
				for pos in range(0, int(pointLength+smallest), smallest):
					for test in ("large", "medium", "small"):
						if pos % size[test] == 0:
							ruleSize = ruleSizes[test]
							break
					if ruleSize:
						rescaledPos = (pos*z)
						if self.rulerPos == "r":
							dc.DrawLine(0, rescaledPos, ruleSize, rescaledPos)
						if self.rulerPos == "l":
							dc.DrawLine(self.Thickness, rescaledPos, self.Thickness - ruleSize, rescaledPos)
						if self.rulerPos == "b":
							dc.DrawLine(rescaledPos, 0, rescaledPos, ruleSize)
						if self.rulerPos == "t":
							dc.DrawLine(rescaledPos, self.Thickness, rescaledPos, self.Thickness - ruleSize)


			def _getThickness(self):
				if self._orientation == "v":
					val = self.Width
				else:
					val = self.Height
				return val

			def _setThickness(self, val):
				if self._orientation == "v":
					self.Width = val
				else:
					self.Height = val
				
			def _getLength(self):
				if self._orientation == "v":
					val = self.Height
				else:
					val = self.Width
				return val

			def _setLength(self, val):
				if self._orientation == "v":
					self.Height = val
				else:
					self.Width = val
			
			Length = property(_getLength, _setLength)
			Thickness = property(_getThickness, _setThickness)

		return Ruler(self, Length=defaultLength, Thickness=defaultThickness)


	def copy(self):
		rdc.copy()

	def cut(self):
		rdc.cut()

	def paste(self):
		rdc.paste()


	def sendToBack(self):
		self._arrange("sendToBack")

	def bringToFront(self):
		self._arrange("bringToFront")

	def _arrange(self, mode):
		toRedraw = []
		for selObj in rdc.SelectedObjects:
			if isinstance(selObj, Variable):
				parentObj = rdc.ReportForm
				objects = parentObj["Variables"]
			elif isinstance(selObj, Group):
				parentObj = rdc.ReportForm
				objects = parentObj["Groups"]
			else:
				parentObj = rdc.getParentBand(selObj)
				objects = parentObj["Objects"]
			curidx = None
			for idx, obj in enumerate(objects):
				if id(obj) == id(selObj):
					curidx = idx
					break

			if curidx is not None:
				obj = objects[idx]
				del objects[idx]
				if mode == "sendToBack":
					objects.insert(0, obj)
				else:
					objects.append(obj)
				
				if parentObj not in toRedraw:
					toRedraw.append(parentObj)

		for parent in toRedraw:
			if hasattr(parent, "DesignerObject"):
				parent.DesignerObject.refresh()

		if toRedraw:
			rdc.refreshTree()


	def _getReportForm(self):
		return self._rw.ReportForm

	def _setReportForm(self, val):
		self._rw.ReportForm = val


	def _getZoomFactor(self):
		return self._zoom * 1.515

	def _getZoomPercent(self):
		return "%s%%" % (int(self._zoom * 100),)

	def _getZoom(self):
		return self._zoom
	
	def _setZoom(self, val):
		self._zoom = val

	ReportForm = property(_getReportForm, _setReportForm)
	Zoom = property(_getZoom, _setZoom)
	ZoomFactor = property(_getZoomFactor)
	ZoomPercent = property(_getZoomPercent)
#  End of ReportDesigner Class
# 
#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
#
#  ReportDesignerForm Class
#
class ReportDesignerForm(dabo.ui.dForm):
	"""Main form, status bar, and menu for the report designer.
	"""
	def initProperties(self):
		self._captionBase = self.Caption = "Dabo Report Designer"
		
	def afterInit(self):
		self.Sizer = None
		pgf = self.addObject(dabo.ui.dPageFrame, Name="pgf")
		self.pgf.appendPage(ReportDesigner, caption="Visual Editor")
		self.pgf.appendPage(XmlEditor, caption="XML Editor")
		self.pgf.appendPage(PreviewWindow, caption="Preview")
		self.pgf.Pages[1].bindEvent(dEvents.PageEnter, self.onEnterXmlEditorPage)
		self.pgf.Pages[1].bindEvent(dEvents.PageLeave, self.onLeaveXmlEditorPage)
		self.fillMenu()

		self._xmlEditorUpToDate = False
		self.editor = self.pgf.Pages[0]



	def onActivate(self, evt):
		rdc.ActiveEditor = self.editor

		if rdc.ReportForm:
			if not hasattr(self, "_loaded"):
				self._loaded = True
				if self.Application.getUserSetting("ReportDesigner_ShowPropSheet"):
					rdc.showPropSheet()
	
				if self.Application.getUserSetting("ReportDesigner_ShowObjectTree"):
					rdc.showObjectTree()
		

	def setModified(self, page):
		if isinstance(page, ReportDesigner):
			self._xmlEditorUpToDate = False

	def onEnterXmlEditorPage(self, evt):
		editBox = self.pgf.Pages[1]
		if not self._xmlEditorUpToDate:
			editor = self.editor
			editBox.Value = editor._rw._getXMLFromForm(rdc.ReportForm)
			self._xmlEditorUpToDate = True
		self._xmlEditorOldValue = editBox.Value

	def onLeaveXmlEditorPage(self, evt):
		editBox = self.pgf.Pages[1]
		if editBox.Value != self._xmlEditorOldValue:
			editor = self.editor
			editBox = self.pgf.Pages[1]
			editor.clearReportForm()
			editor._rw._clearMemento = False
			report = editor._rw._getFormFromXML(editBox.Value)
			editor._rw.ReportForm = report
			editor._rw._clearMemento = True
			editor.initReportForm()
			editor.setCaption()
			## Force a refresh of the propsheet:
			rdc.ActiveEditor = self.editor
			

	def beforeClose(self, evt):
		result = self.editor.closeFile()
		if result is None:
			return False
		else:
			othersLoaded, psLoaded, otLoaded = False, False, False
			for form in self.Application.uiForms:
				if isinstance(form, PropSheetForm):
					psLoaded = True
				elif isinstance(form, ObjectTreeForm):
					otLoaded = True
				elif form != self:
					othersLoaded = True

			if psLoaded:
				psVisible = rdc.PropSheet.Form.Visible
			else:
				psVisible = False

			if otLoaded:
				otVisible = rdc.ObjectTree.Form.Visible
			else:
				otVisible = False

			if psLoaded and not othersLoaded:
				# The last report has been closed, also close the propsheet:
				rdc.PropSheet.Form.close()
			if otLoaded and not othersLoaded:
				# The last report has been closed, also close the object tree:
				rdc.ObjectTree.Form.close()

			self.Application.setUserSetting("ReportDesigner_ShowPropSheet", psVisible)
			self.Application.setUserSetting("ReportDesigner_ShowObjectTree", otVisible)


	def onFileNew(self, evt):
		o = self.editor
		if o._rw.ReportFormFile is None and not o._rw._isModified():
			# open in this editor
			o = self
		else:
			# open in a new editor
			o = ReportDesignerForm(self.Parent)
			o.Size = self.Size
			o.Position = (self.Left + 20, self.Top + 20)
		o.editor.newFile()
		o.Show()

	def onFileOpen(self, evt):
		o = self.editor
		fileName = o.promptForFileName("Open")
		if fileName is not None:
			if o._rw.ReportFormFile is None and not o._rw._isModified():
				# open in this editor
				o = self
			else:
				# open in a new editor
				o = ReportDesignerForm(self.Parent)
				o.Size = self.Size
				o.Position = (self.Left + 20, self.Top + 20)
			o.editor.newFile()
			o.Show()
			o.editor.openFile(fileName)

	def onFileSave(self, evt):
		self.editor.saveFile()
		
	def onFileClose(self, evt):
		result = self.editor.closeFile()
		if result is not None:
			self.Close()
		
	def onFileSaveAs(self, evt):
		fname = self.editor.promptForSaveAs()
		if fname:
			self.editor.saveFile(fname)
			
	def onFilePreviewReport(self, evt):
		import dabo.lib.reportUtils as reportUtils
		fname = self.editor._rw.OutputFile = reportUtils.getTempFile(ext="pdf")
		self.editor._rw.write()
		reportUtils.previewPDF(fname)

	def onEditBringToFront(self, evt):
		self.editor.bringToFront()

	def onEditSendToBack(self, evt):
		self.editor.sendToBack()

	def selectAll(self):
		rdc.selectAllObjects()
	
	def onViewZoomIn(self, evt):
		ed = self.editor
		if ed.Zoom < 10:
			ed.Zoom *= 1.25
			ed.drawReportForm()

	def onViewZoomNormal(self, evt):
		ed = self.editor
		ed.Zoom = ed._normalZoom
		ed.drawReportForm()

	def onViewZoomOut(self, evt):
		ed = self.editor
		if ed.Zoom > .2:
			ed.Zoom /= 1.25
			ed.drawReportForm()

	def onViewShowObjectTree(self, evt):
		o = rdc.ObjectTree
		if o and o.Form.Visible:
			rdc.hideObjectTree()
		else:
			rdc.showObjectTree()

	def onViewShowPropertySheet(self, evt):
		o = rdc.PropSheet
		if o and o.Form.Visible:
			rdc.hidePropSheet()
		else:
			rdc.showPropSheet()


	def fillMenu(self):
		mb = self.MenuBar
		fileMenu = mb.getMenu("base_file")
		editMenu = mb.getMenu("base_edit")
		viewMenu = mb.getMenu("base_view")
		dIcons = dabo.ui.dIcons
				
		fileMenu.prependSeparator()

		fileMenu.prepend(_("Preview Report"), HotKey="Ctrl-P", OnHit=self.onFilePreviewReport, 
				help=_("Preview the report as a PDF"))

		fileMenu.prependSeparator()

		fileMenu.prepend(_("Save &As"), OnHit=self.onFileSaveAs, bmp="saveAs", 
				help=_("save"))

		fileMenu.prepend(_("&Save"), HotKey="Ctrl+S", OnHit=self.onFileSave, bmp="save",
				help=_("Save file"))

		fileMenu.prepend(_("&Close"), HotKey="Ctrl+W", OnHit=self.onFileClose, bmp="close",
				help=_("Close file"))

		fileMenu.prepend(_("&Open"), HotKey="Ctrl+O", OnHit=self.onFileOpen, bmp="open",
				help=_("Open file"))

		fileMenu.prepend(_("&New"), HotKey="Ctrl+N", OnHit=self.onFileNew, bmp="new",
				help=_("New file"))


		editMenu.appendSeparator()

		editMenu.append(_("Bring to &Front"), HotKey="Ctrl+H", OnHit=self.onEditBringToFront, 
				help=_("Bring selected object(s) to the top of the z-order"))

		editMenu.append(_("Send to &Back"), HotKey="Ctrl+J", OnHit=self.onEditSendToBack, 
				help=_("Send selected object(s) to the back of the z-order"))


		viewMenu.appendSeparator()

		viewMenu.append(_("Zoom &In"), HotKey="Ctrl+]", OnHit=self.onViewZoomIn, 
				bmp="zoomIn", help=_("Zoom In"))

		viewMenu.append(_("&Normal Zoom"), HotKey="Ctrl+\\", OnHit=self.onViewZoomNormal, 
				bmp="zoomNormal", help=_("Normal Zoom"))

		viewMenu.append(_("Zoom &Out"), HotKey="Ctrl+[", OnHit=self.onViewZoomOut, 
				bmp="zoomOut", help=_("Zoom Out"))

		viewMenu.appendSeparator()

		viewMenu.append(_("Show/Hide Object Tree"), HotKey="Shift+Ctrl+O", 
				OnHit=self.onViewShowObjectTree, 
				help=_("Show the object hierarchy."))

		viewMenu.append(_("Show/Hide Property Sheet"), HotKey="Shift+Ctrl+P", 
				OnHit=self.onViewShowPropertySheet, 
				help=_("Show the properties for the selected report objects."))



#  End of ReportDesignerForm Class
#
#------------------------------------------------------------------------------

# For dIDE:
EditorForm = ReportDesignerForm


class XmlEditor(dabo.ui.dEditBox): pass

class PreviewWindow(dabo.ui.dImage):
	def onPageEnter(self, evt):
		self.render()

	def render(self):
		# Eventually, a platform-independent pdf viewer window will hopefully be
		# available. Until that time, just display the report in the available
		# external viewer:
		self.Form.onFilePreviewReport(None)
		dabo.ui.callAfter(self.Form.pgf._setSelectedPageNumber, 0)

if __name__ == "__main__":
	app = DesignerController()
	app.setup()

	if len(sys.argv) > 1:
		for fileSpec in sys.argv[1:]:
			form = ReportDesignerForm()
			form.editor.openFile("%s" % fileSpec)
			form.Visible = True
	else:
		form = ReportDesignerForm()
		form.editor.newFile()
		form.Visible = True
	app.start()
