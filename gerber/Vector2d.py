#!/usr/bin/python3
#
#	Vector2d - Simple 2d vector representation
#	Copyright (C) 2017-2019 Johannes Bauer
#
#	This file is part of pycommon.
#
#	pycommon is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pycommon is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pycommon; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>
#
#	File UUID be055e49-1346-4f4b-89e6-f48c25ef6f83

import math

class Vector2d(object):
	def __init__(self, x, y):
		self._x = x
		self._y = y

	@classmethod
	def unit_angle(cls, angle_rad):
		return cls(x = math.cos(angle_rad), y = math.sin(angle_rad))

	@property
	def x(self):
		return self._x

	@property
	def y(self):
		return self._y

	@property
	def length(self):
		return math.sqrt((self.x ** 2) + (self.y ** 2))

	@property
	def angle(self):
		return math.atan2(self.y, self.x) % (2 * math.pi)

	def comp_div(self, other):
		"""Component-wise division."""
		return Vector2d(self.x / other.x, self.y / other.y)

	def comp_mul(self, other):
		"""Component-wise multiplication."""
		return Vector2d(self.x * other.x, self.y * other.y)

	def __mul__(self, scalar):
		return Vector2d(self.x * scalar, self.y * scalar)

	def __rmul__(self, scalar):
		return self * scalar

	def __truediv__(self, scalar):
		divscalar = 1 / scalar
		return self * (1 / scalar)

	def __add__(self, other):
		return Vector2d(self.x + other.x, self.y + other.y)

	def __sub__(self, other):
		return Vector2d(self.x - other.x, self.y - other.y)

	def __neg__(self):
		return Vector2d(-self.x, -self.y)

	@staticmethod
	def _almost_equal(x, y):
		return abs(x - y) < 1e-6

	def __eq__(self, other):
		return self._almost_equal(self.x, other.x) and self._almost_equal(self.y, other.y)

	def __neq__(self, other):
		return not (self == other)

	def __iter__(self):
		yield self.x
		yield self.y

	def __repr__(self):
		return "(%.3f, %.3f)" % (self.x, self.y)
