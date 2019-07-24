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

class ApertureDefinition():
	def __init__(self, template, params):
		self._template = template
		self._params = params

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
		("cmd", re.compile(r"(?P<cmds>[-GDXYIJ0-9]+)\*")),
		("key_value", re.compile(r"G04 (?P<key>\w+)=(?P<value>\w+)\*")),
		("comment", re.compile(r"G04\s(?P<comment>.*)\*")),
		("M", re.compile(r"M(?P<m>\d+)\*")),
		("load_polarity", re.compile(r"%LP(?P<pol>[CD])\*%")),
		("not_implemented", re.compile(r"(?P<unknown_command>%.*)")),
	)))
	_CMD_RE = re.compile("(?P<cmdcode>[A-Z])(?P<parameter>-?[0-9]+)")

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
		self._properties = { }

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

	def _match_not_implemented(self, match):
		print(match)

	def _match_load_polarity(self, match):
		pol = match["pol"]
		if pol == "C":
			# Clear
			self._callback.drawmode_clear()
		else:
			# Dark
			self._callback.drawmode_dark()

	def _match_cmd(self, match):
		orig_cmds = match["cmds"]
		remaining = orig_cmds

		parameters = { }
		while len(remaining) > 0:
			match = self._CMD_RE.match(remaining)
			if not match:
				raise Exception("Could not match remaining '%s' in '%s'." % (remaining, orig_cmds))
			cmd = match.groupdict()
			remaining = remaining[match.span()[1]: ]

			cmdcode = cmd["cmdcode"]
			param = cmd["parameter"]
			if cmdcode == "G":
				self._execute_G(int(param))
			elif cmdcode == "D":
				parameters[cmdcode] = param
				self._execute_D(parameters)
				parameters = { }
			else:
				parameters[cmdcode] = param

	def _execute_D(self, match):
		x = self._convert(match.get("X"), self._precision["x"])
		y = self._convert(match.get("Y"), self._precision["y"])
		i = self._convert(match.get("I"), self._precision["x"])
		j = self._convert(match.get("J"), self._precision["y"])
		xy = Vector2d(self._to_inches(x) if x is not None else self._pos.x, self._to_inches(y) if y is not None else self._pos.y)
		ij = Vector2d(self._to_inches(i) if i is not None else 0, self._to_inches(j) if j is not None else 0)
		d = int(match["D"])
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
		(key, value) = (match["key"], match["value"])
		self._properties[key] = value

	def _match_add_aperture(self, match):
		template = match["template"]
		params = tuple(self._to_inches(float(value)) for value in match["params"].split("X"))
		aperture = ApertureDefinition(template = template, params = params)
		d = int(match["d"])
		self._apertures[d] = aperture

	def _match_set_unit(self, match):
		if match["unit"] == "MM":
			self._unit = Unit.MM
		elif match["unit"] == "IN":
			self._unit = Unit.Inch
		else:
			print(match)

	def _execute_G(self, g):
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

	def _match_G(self, match):
		self._execute_G(int(match["g1"]))
		if match["g2"] is not None:
			self._execute_G(int(match["g2"]))

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
