#	gerberpeek - Render RS-274X Gerber files to image
#	Copyright (C) 2019-2019 Johannes Bauer
#
#	This file is part of gerberpeek.
#
#	gerberpeek is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	gerberpeek is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import re
import collections
import enum
from .MultiRegex import MultiRegex
from .Vector2d import Vector2d

class InterpolationMode(enum.IntEnum):
	Linear = 1
	ClockwiseCircular = 2
	CounterClockwiseCircular = 3

class Unit(enum.IntEnum):
	Inch = 70
	MM = 71

class QuadrantMode(enum.IntEnum):
	SingleQuadrant = 74
	MultiQuadrant = 75

class EndOfFile(Exception): pass

class Aperture():
	def __init__(self, template, params, unit):
		assert(unit == Unit.Inch)
		self._template = template
		if self._template == "C":
			# Circle with radius
			self._params = float(params)
		elif self._template == "R":
			# Rectangle
			self._params = tuple(float(x) for x in params.split("X", maxsplit = 1))
		elif self._template == "O":
			# Obround
			self._params = tuple(float(x) for x in params.split("X", maxsplit = 1))
		else:
			raise NotImplementedError(self._template)
		self._unit = unit

	@property
	def template(self):
		return self._template

	@property
	def params(self):
		return self._params

	def __repr__(self):
		return "Aperture<%s, %s>" % (self._template, self._params)

class Interpreter():
	_CMDS = MultiRegex(collections.OrderedDict((
		("D", re.compile(r"D(?P<d>\d+)\*")),
		("set_unit", re.compile(r"%MO(?P<unit>IN|MM)\*%")),
		("set_precision", re.compile(r"%FSLAX(?P<xi>\d)(?P<xd>\d)Y(?P<yi>\d)(?P<yd>\d)\*%")),
		("add_aperture", re.compile(r"%ADD(?P<d>\d{2})(?P<template>[^,]+),(?P<params>.*)\*%")),
		("move_cmd", re.compile(r"(X(?P<x>-?\d+))?(Y(?P<y>-?\d+))?(I(?P<i>-?\d+))?(J(?P<j>-?\d+))?D(?P<d>\d+)\*")),
		("key_value", re.compile(r"G04 (?P<key>\w+)=(?P<value>\w+)\*")),
		("G", re.compile(r"G(?P<g>\d+)\*")),
		("M", re.compile(r"M(?P<m>\d+)\*")),
		("load_polarity", re.compile(r"%LP(?P<pol>[CD])\*%")),
		("comment", re.compile(r"%(?P<comment>.*)")),
	)))

	def __init__(self, filename, callback):
		self._filename = filename
		self._callback = callback
		self._unit = None
		self._interpolation = None
		self._quadrantmode = None
		self._pos = None
		self._precision = { "x": None, "y": None }
		self._apertures = { }
		self._region = False

	def _begin_region(self):
		assert(not self._region)
		self._region = True
		self._callback.begin_path()

	def _end_region(self):
		assert(self._region)
		self._region = False
		self._callback.end_path()

	def _convert(self, value, coord_fmt):
		if value is None:
			return None
		else:
			negative = False
			if value[0] == "-":
				negative = True
				value = value[1:]
			digits = coord_fmt[0] + coord_fmt[1]
			value = value.rjust(digits, "0")
			(i, d) = (value[:coord_fmt[0]], value[coord_fmt[0]:])
			denominator = 10 ** coord_fmt[1]
			value = int(i) + (int(d) / denominator)
			if negative:
				return -value
			return value

	def _to_inches(self, value):
		if value is None:
			return None
		elif self._unit == Unit.Inch:
			return value
		elif self._unit == Unit.MM:
			return 25.4 * value
		else:
			raise NotImplementedError(self._unit)

	def _match_load_polarity(self, match):
		pol = match["pol"]
		if pol == "C":
			# Clear
			self._callback.drawmode_clear()
		else:
			# Dark
			self._callback.drawmode_dark()

	def _match_move_cmd(self, match):
		x = self._convert(match["x"], self._precision["x"])
		y = self._convert(match["y"], self._precision["y"])
		i = self._convert(match["i"], self._precision["x"])
		j = self._convert(match["j"], self._precision["y"])
		xy = Vector2d(self._to_inches(x) if x is not None else self._pos.x, self._to_inches(y) if y is not None else self._pos.y)
		ij = Vector2d(self._to_inches(i) if i is not None else 0, self._to_inches(j) if j is not None else 0)
		d = int(match["d"])
		if self._interpolation == InterpolationMode.Linear:
			if d == 1:
				if not self._region:
					self._callback.line(self._pos, xy)
				else:
					self._callback.region_line(xy)
			elif d == 2:
				if self._region:
					self._callback.region_move(xy)
			elif d == 3:
				self._callback.flash_at(xy)
			else:
				raise NotImplementedError(self._interpolation, self._quadrantmode, match)
			self._pos = xy
		elif (self._interpolation in [ InterpolationMode.ClockwiseCircular, InterpolationMode.CounterClockwiseCircular ]) and self._quadrantmode == QuadrantMode.MultiQuadrant:
			start_pt = self._pos
			end_pt = xy
			center_pt = start_pt + ij
			if (d == 1) and (start_pt == end_pt):
				# Full circle
				radius = (center_pt - start_pt).length
				self._callback.circle(center_pt, radius)
			elif (d == 1) and (self._interpolation == InterpolationMode.ClockwiseCircular):
				self._callback.arc_cw(start_pt = start_pt, end_pt = end_pt, center_pt = center_pt)
			elif (d == 1) and (self._interpolation == InterpolationMode.CounterClockwiseCircular):
				self._callback.arc_ccw(start_pt = start_pt, end_pt = end_pt, center_pt = center_pt)
			else:
				raise NotImplementedError(self._interpolation, self._quadrantmode, match)
			self._pos = end_pt
		else:
			raise NotImplementedError(self._interpolation, self._quadrantmode, match)


	def _match_key_value(self, match):
		print(match)

	def _match_add_aperture(self, match):
		aperture = Aperture(template = match["template"], params = match["params"], unit = self._unit)
		d = int(match["d"])
		self._apertures[d] = aperture

	def _match_set_unit(self, match):
		if match["unit"] == "MM":
			self._unit = Unit.MM
		elif match["unit"] == "IN":
			self._unit = Unit.Inch
		else:
			print(match)

	def _match_G(self, match):
		g = int(match["g"])
		if g in [ 1, 2, 3 ]:
			self._interpolation = InterpolationMode(g)
		elif g in [ 70, 71 ]:
			self._unit = Unit(g)
		elif g in [ 74, 75 ]:
			self._quadrantmode = QuadrantMode(g)
		elif g == 36:
			self._begin_region()
		elif g == 37:
			self._end_region()
		else:
			print(match)

	def _match_D(self, match):
		# Set aperture
		d = int(match["d"])
		if d == 2:
			# Close contour
			self._callback.close_contour()
		elif d == 3:
			# Flash
			self._callback.flash_at(self._pos)
		elif d >= 10:
			self._callback.select_aperture(self._apertures[d])
		else:
			print(match)

	def _match_M(self, match):
		m = int(match["m"])
		if m == 2:
			# End-of-file
			raise EndOfFile()
		else:
			print(match)

	def _match_comment(self, match):
		print(match)

	def _match_set_precision(self, match):
		self._precision["x"] = (int(match["xi"]), int(match["xd"]))
		self._precision["y"] = (int(match["yi"]), int(match["yd"]))

	def _interpret_line(self, line):
		self._CMDS.fullmatch(line, self, groupdict = True)

	def run(self):
		try:
			with open(self._filename) as f:
				for line in f:
					line = line.rstrip("\r\n")
					self._interpret_line(line)
		except EndOfFile:
			pass
