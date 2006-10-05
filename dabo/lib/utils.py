# This serves as a catch-all script for common utilities that may be used
# in lots of places throughout Dabo. Typically, to use a function 'foo()' in
# this file, add the following import statement to your script:
#
#	import dabo.lib.utils as utils
# 
# Then, in your code, simply call:
#
#	utils.foo()

import os
import sys


def reverseText(tx):
	"""Takes a string and returns it reversed. Example:
	
	utils.reverseText("Wow, this is so cool!")
		=> returns "!looc os si siht ,woW"
	"""
	return tx[::-1]


def padl(txt, lngth, fill=" "):
	"""Left pads the given string to the given length."""
	txt = str(txt)[:lngth]
	return (fill * (lngth-len(txt)) ) + txt
		

def padr(txt, lngth, fill=" "):
	"""Right pads the given string to the given length."""
	txt = str(txt)[:lngth]
	return txt + (fill * (lngth-len(txt)) )
		

def padc(txt, lngth, fill=" "):
	""" Return string of the specified length, padded with the
	specified fill character equally on the left and right (center
	the string). Default fill character	is space.
	"""
	txt = str(txt)[:lngth]
	# If the difference is odd, the extra character goes on the right
	diff = lngth - len(txt)
	dl = int( diff / 2)
	dr = diff - dl
	
	return (fill * dl) + txt[:lngth] + (fill * dr)


def getUserHomeDirectory():
	"""Return the user's home directory in a platform-portable way.

	If the home directory cannot be determined, return None.
	"""
	# os.path.expanduser should work on all posix systems (*nix, Mac, and some
	# Windows NT setups):
	hd = None
	try:
		hd = os.path.expanduser("~")
	except:
		pass

	# If for some reason the posix function above didn't work, most Linux setups
	# define the environmental variable $HOME, and perhaps this is done sometimes
	# on Mac and Win as well:
	if hd is None:
		hd = os.environ.get("HOME")

	# If we still haven't found a value, Windows tends to define a $USERPROFILE
	# directory, which usually expands to something like
	#	 c:\Documents and Settings\maryjane
	if hd is None:
		hd = os.environ.get("USERPROFILE")

	return hd


def getUserDaboDirectory(appName="Dabo"):
	"""Return the directory where Dabo can save user preference and setting information.

	On *nix, this will be something like /home/pmcnett/.dabo
	On Windows, it will be more like c:\Documents and Settings\pmcnett\Application Data\Dabo

	This function relies on platform conventions to determine this information. If it
	cannot be determined (because platform conventions were circumvented), the return
	value will be None.

	if appName is passed, the directory will be named accordingly.

	This function will try to create the directory if it doesn't already exist, but if the
	creation of the directory fails, the return value will revert to None.
	"""
	dd = None
	if sys.platform in ("win32", ):
		dd = os.environ.get("APPDATA")
		if dd is not None:
			dd = os.path.join(dd, appName)

	if dd is None:
		dd = getUserHomeDirectory()

		if dd is not None:
			dd = os.path.join(dd, ".%s" % appName.lower())

	if not os.path.exists(dd):
		# try to create the dabo directory:
		try:
			os.makedirs(dd)
		except:
			print "Couldn't create the user setting directory (%s)." % dd
			dd = None

	return dd
	
	
def dictStringify(dct):
	"""The ability to pass a properties dict to an object relies on
	the practice of passing '**properties' to a function. Seems that 
	Python requires that the keys in any dict being expanded like
	this be strings, not unicode. This method returns a dict with all
	unicode keys changed to strings.
	"""
	ret = {}
	for kk, vv in dct.items():
		if isinstance(kk, unicode):
			ret[str(kk)] = vv
		else:
			ret[kk] = vv
	return ret
		

def relativePathList(toLoc, fromLoc=None):
	"""Given two paths, returns a list that, when joined with 
	os.path.sep, gives the relative path from 'fromLoc' to
	"toLoc'. If 'fromLoc' is not specified, the current directory
	is assumed.
	"""
	if fromLoc is None:
		fromLoc = os.getcwd()
	toLoc = os.path.abspath(toLoc)
	fromLoc = os.path.abspath(fromLoc)
	if os.path.isfile(fromLoc):
		fromLoc = os.path.split(fromLoc)[0]
	fromList = fromLoc.split(os.path.sep)
	toList = toLoc.split(os.path.sep)	
	# There can be empty strings from the split
	while len(fromList) > 0 and not fromList[0]:
		fromList.pop(0)
	while len(toList) > 0 and not toList[0]:
		toList.pop(0)
	lev = 0
	while (len(fromList) > lev) and (len(toList) > lev) and \
			(fromList[lev] == toList[lev]):
		lev += 1
		
	# 'lev' now contains the first level where they differ
	fromDiff = fromList[lev:]
	toDiff = toList[lev:]
	return [".."] * len(fromDiff) + toDiff


def relativePath(toLoc, fromLoc=None):
	"""Given two paths, returns a relative path from fromLoc to toLoc."""
	return os.path.sep.join(relativePathList(toLoc, fromLoc))


def getPathAttributePrefix():
	return "path://"


def resolveAttributePathing(atts, pth=None):
	"""Dabo design files store their information in XML, which means
	when they are 'read' the values come back in a dictionary of 
	attributes, which are then used to restore the designed object to its
	intended state. Path values will be stored in a relative path format,
	with the value preceeded by the string returned by 
	getPathAttributePrefix(); i.e., 'path://'.
	
	This method finds all values that begin with the 'path://' label, 
	strips off that label, converts the paths back to values that
	can be used by the object, and then updates the attribute dict with
	those new values.
	"""
	prfx = getPathAttributePrefix()
	pathsToConvert = [(kk, vv) for kk, vv in atts.items()
			if vv.startswith(prfx)]
	for convKey, convVal in pathsToConvert:
		# Strip the path designator
		convVal = convVal.replace(prfx, "")
		# Convert to relative path
		relPath = relativePath(convVal, pth)
		# Update the atts
		atts[convKey] = relPath


