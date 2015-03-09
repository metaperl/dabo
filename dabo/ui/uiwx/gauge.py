# -*- coding: utf-8 -*-
import wx
import dabo
from dabo.dLocalize import _
from dabo.ui import makeDynamicProperty
from . import controlmixin as cm
import dabo.dEvents as dEvents


class dGauge(cm.dControlMixin, wx.Gauge):
	"""Creates a gauge, which can be used as a progress bar."""
	def __init__(self, parent, properties=None, attProperties=None, *args, **kwargs):
		self._baseClass = dGauge
		if dabo.ui.phoenix:
			preClass = wx.Gauge
		else:
			preClass = wx.PreGauge
		cm.dControlMixin.__init__(self, preClass, parent, properties=properties,
				attProperties=attProperties, *args, **kwargs)


	def _initEvents(self):
		super(dGauge, self)._initEvents()


	# Property get/set/del methods follow. Scroll to bottom to see the property
	# definitions themselves.
	def _getPercentage(self):
		return round(100 * (float(self.Value) / self.Range), 2)

	def _setPercentage(self, val):
		if self._constructed():
			self.Value = round(self.Range * (val / 100.0))
		else:
			self._properties["Percentage"] = val


	def _getOrientation(self):
		if self.IsVertical():
			return "Vertical"
		else:
			return "Horizontal"

	def _setOrientation(self, value):
		self._delWindowStyleFlag(wx.GA_HORIZONTAL)
		self._delWindowStyleFlag(wx.GA_VERTICAL)
		if value.lower()[:1] == "h":
			self._addWindowStyleFlag(wx.GA_HORIZONTAL)
		else:
			self._addWindowStyleFlag(wx.GA_VERTICAL)


	def _getRange(self):
		return self.GetRange()

	def _setRange(self, value):
		if self._constructed():
			self.SetRange(value)
		else:
			self._properties["Range"] = value


	def _getValue(self):
		return self.GetValue()

	def _setValue(self, value):
		if self._constructed():
			self.SetValue(value)
		else:
			self._properties["Value"] = value


	# Property definitions:
	Percentage = property(_getPercentage, _setPercentage, None,
			_("""Alternate way of setting/getting the Value, using percentage
			of the Range.  (float)"""))

	Orientation = property(_getOrientation, _setOrientation, None,
			_("Specifies whether the gauge is displayed as Horizontal or Vertical.  (str)"))

	Range = property(_getRange, _setRange, None,
			_("Specifies the maximum value for the gauge.  (int)"))

	Value = property(_getValue, _setValue, None,
			_("Specifies the state of the gauge, relative to max value."))


	DynamicOrientation = makeDynamicProperty(Orientation)
	DynamicRange = makeDynamicProperty(Range)
	DynamicValue = makeDynamicProperty(Value)
