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

import math
from .Vector2d import Vector2d

class GeoInterpolation():
	def __init__(self, callback, sampling_coefficient = 1.0):
		self._callback = callback
		self._sampling_coefficient = sampling_coefficient

	def line(self, src, dst):
		length = (src - dst).length
		points = round(length * self._sampling_coefficient)
		if points == 0:
			self._callback((src + dst) / 2)
		else:
			slope = (dst - src) / points
			for i in range(points + 1):
				pt = src + (i * slope)
				self._callback(pt)

	def arc(self, center, radius, from_rad, to_rad):
		if (from_rad is None) or (abs(from_rad - to_rad) < 1e-6):
			# Full circle
			ratio = 1
			from_rad = 0
			to_rad = 2 * math.pi
		else:
			ratio = ((to_rad - from_rad) % (2 * math.pi)) / (2 * math.pi)
		length = (2 * radius * math.pi) * ratio
		points = round(length * self._sampling_coefficient)
		points = max(points, 2)

		if to_rad < from_rad:
			to_rad += 2 * math.pi
		rad_slope = (to_rad - from_rad) / points
		for i in range(points + 1):
			angle = from_rad + (i * rad_slope)
			point = center + (radius * Vector2d.unit_angle(angle))
			self._callback(point)

	def circle(self, center, radius):
		return self.arc(center, radius, from_rad = None, to_rad = None)

if __name__ == "__main__":

	def print_coords(x):
		print(x)

	gip = GeoInterpolation(print_coords)
#	gip.line(Vector2d(0, 0), Vector2d(10, 10))
#	gip.arc(Vector2d(0, 0), 10, 0, math.pi)
#	gip.circle(Vector2d(0, 0), 1)

	gip.arc(Vector2d(0, 0), 1, 0, 0.1)
#	gip.arc(Vector2d(0, 0), 10, 0.3, 0.1)
