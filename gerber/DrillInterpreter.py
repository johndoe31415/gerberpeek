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

class EndOfFile(Exception): pass

class Unit(enum.Enum):
	Inch = "INCH"
	MM = "METRIC"

class ValueInterpretation(enum.IntEnum):
	LiteralFloat = 1
	Decimal = 2

class DrillInterpreter():
	_CMDS = MultiRegex(collections.OrderedDict((
		("G", re.compile(r"G(?P<g>\d+)")),
		("M", re.compile(r"M(?P<m>\d+)")),
		("T", re.compile(r"T(?P<t>\d+)")),
		("XY", re.compile(r"X(?P<x>-?\d+(\.\d+)?)Y(?P<y>-?\d+(\.\d+)?)")),
		("X", re.compile(r"X(?P<x>-?\d+(\.\d+)?)")),
		("Y", re.compile(r"Y(?P<y>-?\d+(\.\d+)?)")),
		("unit", re.compile(r"(?P<unit>INCH|METRIC)(,(?P<mode>LZ|\d+.\d+))?")),
		("tooldef", re.compile(r"T(?P<t>\d+)(F(?P<f>\d+))?(S(?P<s>\d+))?C(?P<c>\d+(\.\d+)?)")),
		("key_value", re.compile(r";(?P<key>[^=]+)=(?P<value>[^=]+)")),
		("comment", re.compile(r";(?P<comment>.*)")),
		("end_of_header", re.compile(r"%")),
		("unknown", re.compile(r"(?P<unknown>FMAT.*)")),
	)))

	def __init__(self, filename, callback):
		self._filename = filename
		self._callback = callback
		self._unit = None
		self._tools = { }
		self._x = None
		self._y = None
		self._value_interpretation = ValueInterpretation.LiteralFloat
		self._precision = None

	def _convert_coord(self, value):
		if self._value_interpretation == ValueInterpretation.LiteralFloat:
			value = float(value)
		elif self._value_interpretation == ValueInterpretation.Decimal:
			digits = self._precision[0] + self._precision[1]
			value = value.ljust(digits, "0")
			(pre, post) = (value[ : self._precision[0] ], value[self._precision[0] : ])
			value = int(pre) + (int(post) / (10 ** self._precision[1]))
		else:
			raise NotImplementedError(self._value_interpretation)
		return self._to_inch(value)

	def _to_inch(self, value):
		if self._unit == Unit.Inch:
			return value
		elif self._unit == Unit.MM:
			return value / 25.4
		else:
			raise NotImplementedError(self._unit)

	def _match_G(self, match):
		g = int(match["g"])
		if g == 5:
			# Set drill mode.
			pass
		else:
			print("Unexpected G in drill file: %d" % (g))

	def _match_M(self, match):
		m = int(match["m"])
		if m == 48:
			# Beginning of file.
			pass
		elif m == 30:
			# End of file
			raise EndOfFile()
		else:
			print("Unknown: M%d" % (m))

	def _match_comment(self, match):
		pass

	def _match_unknown(self, match):
		print("Unknown: %s" % (match))

	def _match_unit(self, match):
		self._unit = Unit(match["unit"])
		mode = match["mode"]
		if mode is not None:
			if mode.startswith("0"):
				(pre, post) = mode.split(".", maxsplit = 1)
				self._precision = (len(pre), len(post))
				self._value_interpretation = ValueInterpretation.Decimal

	def _match_tooldef(self, match):
		tool_id = int(match["t"])
		diameter = float(match["c"])
		self._tools[tool_id] = self._to_inch(diameter)

	def _match_end_of_header(self, match):
		pass

	def _match_T(self, match):
		tool_id = int(match["t"])
		if tool_id not in self._tools:
			print("Warning: Tool %d requested, but no such tool defined previously in drill file. Ignoring tool change." % (tool_id))
		else:
			active_tool = self._tools[tool_id]
			self._callback.switch_drill_tool(active_tool)

	def _match_XY(self, match):
		x = self._convert_coord(match["x"])
		y = self._convert_coord(match["y"])
		self._callback.drill(Vector2d(x, y))
		self._x = x
		self._y = y

	def _match_X(self, match):
		x = self._convert_coord(match["x"])
		self._callback.drill(Vector2d(x, self._y))
		self._x = x

	def _match_Y(self, match):
		y = self._convert_coord(match["y"])
		self._callback.drill(Vector2d(self._x, y))
		self._y = y

	def _match_key_value(self, match):
		(key, value) = (match["key"], match["value"])
		if key == "FILE_FORMAT":
			self._precision = [ int(x) for x in value.split(":", maxsplit = 1) ]
			self._value_interpretation = ValueInterpretation.Decimal

	def _interpret_line(self, line):
		self._CMDS.fullmatch(line, self, groupdict = True)

	def run(self):
		with open(self._filename) as f:
			try:
				for line in f:
					line = line.rstrip("\r\n")
					self._interpret_line(line)
			except EndOfFile:
				pass
