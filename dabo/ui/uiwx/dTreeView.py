import dabo
import re, os, glob
import wx
if __name__ == "__main__":
	dabo.ui.loadUI("wx")
import dControlMixin as dcm
import dabo.dEvents as dEvents
from dabo.dLocalize import _
import dabo.dColors as dColors
from dabo.dObject import dObject


class dNode(dObject):
	"""Wrapper class for the tree nodes."""
	def __init__(self, tree, _id, txt, parent):
		self.tree = tree
		# The '_id' in this case is a wxPython wx.TreeItemID object used
		# by wx to work with separate nodes.
		self._id = _id
		self.txt = txt
		self.parent = parent
	
	
	def expand(self):
		self.tree.expand(self)
	
	
	def collapse(self):
		self.tree.collapse(self)
	
	
	def show(self):
		self.tree.showNode(self)
		
	
	def appendChild(self, txt):
		return self.tree.appendNode(self, txt)
	
	
	def removeChild(self, txt):
		"""Removes the child node whose text matches the passed value"""
		mtch = self.tree.find(txt)
		# We have a list of matching nodes. Find the first whose parent
		# is this object, and delete it
		for m in mtch:
			if m.parent == self:
				self.tree.removeNode(m)
				break
		return
		
	
	def _getBackColor(self):
		return self.tree.GetItemBackgroundColour(self._id)

	def _setBackColor(self, val):
		if isinstance(val, basestring):
			try:
				val = dColors.colorTupleFromName(val)
			except: pass
		self.tree.SetItemBackgroundColour(self._id, val)
	

	def _getBold(self):
		return self.tree.IsBold(self._id)

	def _setBold(self, val):
		self.tree.SetItemBold(self._id, val)


	def _getForeColor(self):
		return self.tree.GetItemTextColour(self._id)

	def _setForeColor(self, val):

		if isinstance(val, basestring):
			try:
				val = dColors.colorTupleFromName(val)
			except: pass
		self.tree.SetItemTextColour(self._id, val)
	
	def _getImg(self):
		return self.tree.getNodeImg(self)
	def _setImg(self, key):
		return self.tree.setNodeImg(self, key)
		
	def _getCap(self):
		if self.txt:
			ret = self.txt
		else:
			ret = self.tree.GetItemText(self._id)
		return ret
	def _setCap(self, val):
		self.txt = val
		self.tree.SetItemText(self._id, val)
	
	def _getChildren(self):
		return self.tree.getChildren(self)

	def _getDescendents(self):
		return self.tree.getDescendents(self)

	def _getSel(self):
		sel = self.tree.Selection
		if isinstance(sel, list):	
			ret = self in sel
		else:
			ret = (self == sel)
		return ret
	def _setSel(self, val):
		self.tree.SelectItem(self._id, val)

	def _getSiblings(self):
		return self.tree.getSiblings(self)

	
	BackColor = property(_getBackColor, _setBackColor, None,
			_("Background color of this node  (wx.Colour)") )
			
	Caption = property(_getCap, _setCap, None,
			_("Returns/sets the text of this node.  (str)") )
			
	Children = property(_getChildren, None, None,
			_("List of all nodes for which this is their parent node.  (list of dNodes)") )
	
	Descendents = property(_getDescendents, None, None,
			_("List of all nodes for which this node is a direct ancestor.  (list of dNodes)") )
	
	FontBold = property(_getBold, _setBold, None, 
			_("Bold status for the text of this node.  (bool)") )
		
	ForeColor = property(_getForeColor, _setForeColor, None,
			_("Foreground (text) color of this node  (wx.Colour)") )
			
	Image = property(_getImg, _setImg, None,
			_("""Sets the image that is displayed on the node. This is
			determined by the key value passed, which must refer to an 
			image already added to the parent tree. 	When used to retrieve 
			an image, it returns the index of the node's image in the parent 
			tree's image list.   (int)""") )
			
	Selected = property(_getSel, _setSel, None,
			_("Is this node selected?.  (bool)") )
	
	Siblings = property(_getSiblings, None, None,
			_("List of all nodes with the same parent node.  (list of dNodes)") )
	
	

class dTreeView(wx.TreeCtrl, dcm.dControlMixin):
	"""Creates a treeview, which allows display of hierarchical data."""
	def __init__(self, parent, properties=None, *args, **kwargs):
		self._baseClass = dTreeView

		# Dictionary for tracking images by key value
		self.__imageList = {}	
		self.nodes = []

		preClass = wx.PreTreeCtrl
		dcm.dControlMixin.__init__(self, preClass, parent, properties, 
				*args, **kwargs)
		
		
	def _initEvents(self):
		super(dTreeView, self)._initEvents()
		self.Bind(wx.EVT_LEFT_UP, self._onWxHit)
		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.__onTreeSel)
		self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.__onTreeItemCollapse)
		self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.__onTreeItemExpand)

	
	def _getInitPropertiesList(self):
		additional = ["Editable", "MultipleSelect", "ShowRootNode", 
				"ShowRootNodeLines", "ShowButtons"]
		original = list(super(dTreeView, self)._getInitPropertiesList())
		return tuple(original + additional)

		
	def clear(self):
		self.DeleteAllItems()
		self.nodes = []

	
	def setRootNode(self, txt):
		_id = self.AddRoot(txt)
		ret = dNode(self, _id, txt, None)
		self.nodes.append(ret)
		return ret
	
	
	def appendNode(self, node, txt):
		_id = self.AppendItem(node._id, txt)
		ret = dNode(self, _id, txt, node)
		self.nodes.append(ret)
		return ret


	def removeNode(self, node):
		self.Delete(node._id)
		for n in node.Descendents:
			self.nodes.remove(n)
		self.nodes.remove(node)
	
	
	def expand(self, node):
		self.Expand(node._id)
	
	
	def collapse(self, node):
		self.Collapse(node._id)
	
	
	def expandAll(self):	
		for n in self.nodes:
			self.expand(n)
	
	
	def collapseAll(self):
		for n in self.nodes:
			self.collapse(n)
	
	
	def showNode(self, node):
		self.EnsureVisible(node._id)
		
		
	# Image-handling function
	def addImage(self, img, key=None):
		""" Adds the passed image to the control's ImageList, and maintains
		a reference to it that is retrievable via the key value.
		"""
		if key is None:
			key = str(img)
		if isinstance(img, basestring):
			img = dabo.ui.strToBmp(img)
		il = self.GetImageList()
		if not il:
			il = wx.ImageList(16, 16, initialCount=0)
			self.AssignImageList(il)
		idx = il.Add(img)
		self.__imageList[key] = idx
		
	
	def setNodeImg(self, node, imgKey):
		""" Sets the specified node's image to the image corresponding
		to the specified key. May also optionally pass the index of the 
		image in the ImageList rather than the key.
		"""
		if isinstance(imgKey, int):
			imgIdx = imgKey
		else:
			imgIdx = self.__imageList[imgKey]
		self.SetItemImage(node._id, imgIdx)

	
	def getNodeImg(self, node):
		""" Returns the index of the specified node's image in the 
		current image list, or -1 if no image is set for the node.
		"""
		ret = self.GetItemImage(node._id)
		return ret		
	
	
	def nodeForObject(self, obj):
		"""Given an object, returns the corresponding node."""
		try:
			ret = [nd for nd in self.nodes
					if nd._obj is obj][0]
		except:
			ret = None
		return ret
				
	
	def getParentNode(self, node):
		"""Returns the node that is the parent of the given node, or 
		None if the node is the root.
		"""
		parentID = self.GetItemParent(node._id)
		ret = self.find(parentID)
		if ret:
			if isinstance(ret, list):
				ret = ret[0]
		else:
			ret = None
		return ret
		
		
	def getChildren(self, node):
		""" Returns a list of all nodes that are child nodes of this node."""
		ret = [n for n in self.nodes
				if n.parent == node]
		return ret
	
	
	def getDescendents(self, node):
		"""  Returns a list of all nodes that are direct descendents of this node. """
		ret = []
		for n in self.nodes:
			par = n.parent
			while par:
				if par == node:
					ret.append(n)
					break
				else:
					par = par.parent
		return ret


	def getSiblings(self, node):
		""" Returns a list of all nodes at the same level as the specified
		node. The specified node is included in the list.
		"""
		ret = [n for n in self.nodes
				if n.parent == node.parent]
		return ret
	

	def find(self, srch, top=None):
		""" Searches the nodes collection for all nodes that match
		whose text matches the passed search value (if a text value
		was passed). If a wxPython TreeItemID object is passed, returns
		a list nodes matching that _id value. If a specific node is passed
		in the top property, the search is limited to descendents of that
		node.
		Returns a list of matching nodes.
		"""
		ret = []
		if top is None:
			nodes = self.nodes
		else:
			nodes = top.Descendents
		if isinstance(srch, basestring):
			ret = [n for n in nodes 
				if n.txt == srch ]
		elif isinstance(srch, wx.TreeItemId):
			ret = [n for n in nodes 
				if n._id == srch ]
		return ret
		
		
	def findPattern(self, srchPat, top=None):
		""" Allows for regexp pattern matching in order to find matching
		nodes using less than exact matches. If a specific node is passed
		in the top property, the search is limited to descendents of that
		node.
		Returns a list of matching nodes.
		"""
		ret = []
		if top is None:
			nodes = self.nodes
		else:
			nodes = top.Descendents
		if isinstance(srchPat, basestring):
			ret = [n for n in nodes 
				if re.match(srchPat, n.txt) ]
		return ret
	
	
	# These related functions all use self._getRelative().
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def nextSibling(self, nd=None):
		"""Returns the next sibling node, or None if there are no more"""
		return self._getRelative(nd, self.GetNextSibling)


	def priorSibling(self, nd=None):
		"""Returns the prior sibling node, or None if there are no more"""
		return self._getRelative(nd, self.GetPrevSibling)
		
		
	def nextNode(self, nd=None):
		"""If the current node has children, returns the first child node. If
		it has no children, returns the next sibling. If there are no next
		siblings, returns the next sibling of the parent node. If the parent
		node has no more siblings, returns the next sibling of the grand-
		parent node, etc. Returns None if we are at the absolute bottom
		of the flattened tree structure. Sometimes referred to as 'flatdown'
		navigation.
		"""
		if nd is None:
			nd = self.Selection
			if isinstance(nd, list):
				nd = nd[0]
		try:
			ret = self.getChildren(nd)[0]._obj
		except:
			ret = None
		if ret is None:
			ret = self._getRelative(nd, self.GetNextSibling)
			while ret is None:
				# No more siblings. Go up the tree, getting the next
				# sibling of each parent until we either find one, or
				# we reach the top.
				nd = self.getParentNode(nd)
				if nd is None:
					break
				ret = self._getRelative(nd, self.GetNextSibling)
		return ret		
			
			
	def priorNode(self, nd=None):
		"""Returns last child of the prior sibling node. If there 
		are no prior siblings, returns the parent. Sometimes 
		referred to as 'flatup' navigation.
		"""
		if nd is None:
			nd = self.Selection
			if isinstance(nd, list):
				nd = nd[0]
		ret = self._getRelative(nd, self.GetPrevSibling)
		if ret is None:
			try:
				ret = self.getParentNode(nd)._obj
			except: pass
		else:
			# Find the last child of the last child of the last child...
			nd = self.nodeForObject(ret)
			kids = self.getChildren(nd)
			while kids:
				nd = kids[-1]
				kids = self.getChildren(nd)
			ret = nd._obj
		return ret


	def _getRelative(self, nd, func):
		"""Used by nextNode(), nextSibling(), priorNode() and 
		priorSibling() methods for relative movement.
		"""
		if nd is None:
			nd = self.Selection
		if isinstance(nd, list):
			nd = nd[0]
		try:
			_id = func(nd._id)
			ret = [nod._obj for nod in self.nodes
					if nod._id == _id][0]
		except:
			ret = None
		return ret
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	
	def makeDirTree(self, dirPath, wildcard=None, showHidden=False):
		self.clear()
		# Add any trailing slash character
		self._pathNode = {}
		# Define the function to be passed to os.path.walk
		def addNode(showHid, currDir, fNames):
			prnt, nm = os.path.split(currDir)
			if not showHid:
				if nm[:1] == ".":
					return
			try:
				nd = self._pathNode[currDir] = self._pathNode[prnt].appendChild(nm)
			except:
				# If this is the first entry, we need to set the root
				if len(self._pathNode.keys()) == 0:
					nd = self._pathNode[currDir] = self.setRootNode(nm)
				else:
					# parent wasn't added, because it was hidden
					return
			for f in fNames:
				fullName = os.path.join(currDir, f)
				if os.path.isdir(fullName):
					# it will be added as a directory
					continue
				if not showHid:
					if f[:1] == ".":
						continue
				if wildcard is not None:
					res = glob.glob(os.path.join(currDir, wildcard))
					if not fullName in res:
						continue
				nd.appendChild(f)
		def sortNode(arg, currDir, fNames):
			self.SortChildren(self._pathNode[currDir]._id)
		os.path.walk(dirPath, addNode, showHidden)
		os.path.walk(dirPath, sortNode, None)


	def addDummyData(self):
		""" For testing purposes! """
		self.DeleteAllItems()
		r = self.setRootNode("This is the root")
		c1 = r.appendChild("First Child")
		c2 = r.appendChild("Second Child")
		c3 = r.appendChild("Third Child")
		c21 = c2.appendChild("Grandkid #1")
		c22 = c2.appendChild("Grandkid #2")
		c23 = c2.appendChild("Grandkid #3")
		c221 = c22.appendChild("Great-Grandkid #1")
		

	# Event-handling code
	def __onTreeSel(self, evt):
		self.raiseEvent(dEvents.TreeSelection, evt)
	def __onTreeItemCollapse(self, evt):
		self.raiseEvent(dEvents.TreeItemCollapse, evt)
	def __onTreeItemExpand(self, evt):
		self.raiseEvent(dEvents.TreeItemExpand, evt)


	def _getEditable(self):
		return self._hasWindowStyleFlag(wx.TR_EDIT_LABELS)

	def _setEditable(self, val):
		self._delWindowStyleFlag(wx.TR_EDIT_LABELS)
		if val:
			self._addWindowStyleFlag(wx.TR_EDIT_LABELS)


	def _getMultipleSelect(self):
		return self._hasWindowStyleFlag(wx.TR_MULTIPLE)

	def _setMultipleSelect(self, val):
		self._delWindowStyleFlag(wx.TR_MULTIPLE)
		self._delWindowStyleFlag(wx.TR_EXTENDED)
		self._delWindowStyleFlag(wx.TR_SINGLE)
		if val:
			self._addWindowStyleFlag(wx.TR_MULTIPLE)
			self._addWindowStyleFlag(wx.TR_EXTENDED)
		else:
			self._addWindowStyleFlag(wx.TR_SINGLE)
			

	def _getSelection(self):
		if self.MultipleSelect:
			try:
				ids = self.GetSelections()
			except:
				ids = []
			ret = [ n for n in self.nodes
					if n._id in ids]
		else:
			_id = self.GetSelection()
			if _id:
				ret = [ n for n in self.nodes
						if n._id == _id]
			else:
				ret = []
		return ret

	def _setSelection(self, node):
		if self._constructed():
			self.UnselectAll()
			if isinstance(node, (list, tuple)):
				for itm in node:
					self.SelectItem(itm._id, True)
			else:
				self.SelectItem(node._id)
		else:
			self._properties["Selection"] = node
	
	
	def _getShowButtons(self):
		return self._hasWindowStyleFlag(wx.TR_HAS_BUTTONS)

	def _setShowButtons(self, val):
		self._delWindowStyleFlag(wx.TR_HAS_BUTTONS)
		self._delWindowStyleFlag(wx.TR_NO_BUTTONS)
		if val:
			self._addWindowStyleFlag(wx.TR_HAS_BUTTONS)
		else:
			self._addWindowStyleFlag(wx.TR_NO_BUTTONS)
			

	def _getShowRootNode(self):
		return not self._hasWindowStyleFlag(wx.TR_HIDE_ROOT)

	def _setShowRootNode(self, val):
		self._delWindowStyleFlag(wx.TR_HIDE_ROOT)
		if not val:
			self._addWindowStyleFlag(wx.TR_HIDE_ROOT)
			

	def _getShowRootNodeLines(self):
		return self._hasWindowStyleFlag(wx.TR_LINES_AT_ROOT)

	def _setShowRootNodeLines(self, val):
		self._delWindowStyleFlag(wx.TR_LINES_AT_ROOT)
		if val:
			self._addWindowStyleFlag(wx.TR_LINES_AT_ROOT)
			

	Editable = property(_getEditable, _setEditable, None,
		_("""Specifies whether the tree labels can be edited by the user."""))

	MultipleSelect = property(_getMultipleSelect, _setMultipleSelect, None,
		_("""Specifies whether more than one node may be selected at once."""))
	
	Selection = property(_getSelection, _setSelection, None,
		_("""Specifies which node or nodes are selected.

		If MultipleSelect is False, an integer referring to the currently selected
		node is specified. If MultipleSelect is True, a list of selected nodes is
		specified."""))

	ShowButtons = property(_getShowButtons, _setShowButtons, None,
		_("""Specifies whether +/- indicators are show at the left of parent nodes."""))
		
	ShowRootNode = property(_getShowRootNode, _setShowRootNode, None,
		_("""Specifies whether the root node is included in the treeview.

		There can be only one root node, so if you want several root nodes you can
		fake it by setting ShowRootNode to False. Now, your top child nodes have
		the visual indication of being sibling root nodes."""))
		
	ShowRootNodeLines = property(_getShowRootNodeLines, _setShowRootNodeLines, None,
		_("""Specifies whether vertical lines are shown between root siblings."""))


class _dTreeView_test(dTreeView):
	def initProperties(self):
		pass
		#self.MultipleSelect = True
		#self.Editable = True
		#self.ShowRootNode = False
		#self.ShowRootNodeLines = True

	def afterInit(self): 
		self.addDummyData()
		self.Width = 240
		self.Height = 140

	def onHit(self, evt):
		## pkm: currently, Hit happens on left mouse up, which totally ignores
		##      keyboarding through the tree. I'm wondering about mapping 
		##      TreeSelection instead... thoughts?
		print "Hit!"

	def onTreeSelection(self, evt):
		print "Selected node caption:", evt.EventData["selectedCaption"]

	def onTreeItemCollapse(self, evt):
		print "Collapsed node caption:", evt.EventData["selectedCaption"]

	def onTreeItemExpand(self, evt):
		print "Expanded node caption:", evt.EventData["selectedCaption"]
		
			
if __name__ == "__main__":
	import test
	test.Test().runTest(_dTreeView_test, ShowRootNode=False, ShowRootNodeLines=True, Editable=True, MultipleSelect=True)
