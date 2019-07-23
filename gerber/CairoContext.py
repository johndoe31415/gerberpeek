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
import cairo
from .GeoInterpolation import GeoInterpolation
from .Vector2d import Vector2d

class CairoContext():
	def __init__(self, dimensions, dpi):
		(width, height) = round(dimensions.x), round(dimensions.y)
		self._surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
		self._cctx = cairo.Context(self._surface)
		matrix = cairo.Matrix()
		matrix.scale(1, -1)
		matrix.translate(0, -height)
		self._cctx.set_matrix(matrix)
		self._dpi = dpi

	@classmethod
	def create_inches(cls, dimensions_inches, dpi):
		return cls(dimensions = dimensions_inches * dpi, dpi = dpi)

	@property
	def width(self):
		return self.surface.get_width()

	@property
	def height(self):
		return self.surface.get_height()

	def set_mode_draw(self):
		self._cctx.set_operator(cairo.OPERATOR_OVER)

	def set_mode_erase(self):
		self._cctx.set_operator(cairo.OPERATOR_XOR)

	@property
	def surface(self):
		return self._surface

	@property
	def cctx(self):
		return self._cctx

	@property
	def dpi(self):
		return self._dpi

	def fill(self, color):
		(r, g, b) = color
		self._cctx.set_source_rgb(r, g, b)
		self._cctx.rectangle(0, 0, self.width, self.height)
		self._cctx.fill()

	def blit_on_pixel(self, destination, point):
		destination.cctx.set_source_surface(self.surface, point.x - (self.width / 2), point.y - (self.height / 2))
		destination.cctx.paint()

	def _blit_line_pixel(self, destination_ctx, start_pt, end_pt):
		gip = GeoInterpolation(callback = lambda pt: self.blit_on_pixel(destination_ctx, pt))
		gip.line(start_pt, end_pt)

	def _to_pixel(self, point, unit):
		if unit == "px":
			return point
		elif unit == "in":
			return point * self.dpi
		elif unit == "mm":
			return point * self.dpi * 25.4
		else:
			raise NotImplementedError(unit)

	def blit_line(self, destination_ctx, start_pt, end_pt, unit = "px"):
		start_pt_pixel = self._to_pixel(start_pt, unit)
		end_pt_pixel = self._to_pixel(end_pt, unit)
		return self._blit_line_pixel(destination_ctx, start_pt_pixel, end_pt_pixel)

	def blit_arc_ccw(self, destination_ctx, start_pt, end_pt, center_pt, unit = "px"):
		start_pt_pixel = self._to_pixel(start_pt, unit)
		end_pt_pixel = self._to_pixel(end_pt, unit)
		center_pt_pixel = self._to_pixel(center_pt, unit)
		radius_px = (center_pt_pixel - start_pt_pixel).length

		start_rad = (start_pt_pixel - center_pt_pixel).angle
		end_rad = (end_pt_pixel - center_pt_pixel).angle
		gip = GeoInterpolation(callback = lambda pt: self.blit_on_pixel(destination_ctx, pt))
		gip.arc(center_pt_pixel, radius_px, start_rad, end_rad)

#		ApertureGenerator.generate_x(color = "white").blit_on_pixel(destination_ctx, center_pt_pixel)
#		ApertureGenerator.generate_x(color = "green").blit_on_pixel(destination_ctx, start_pt_pixel)
#		ApertureGenerator.generate_x(color = "blue").blit_on_pixel(destination_ctx, end_pt_pixel)

	def blit_arc_cw(self, destination_ctx, start_pt, end_pt, center_pt, unit = "px"):
		return self.blit_arc_ccw(destination_ctx, end_pt, start_pt, center_pt, unit)

	def blit_circle(self, destination_ctx, center_pt, radius, unit = "px"):
		center_pt_pixel = self._to_pixel(center_pt, unit)
		radius_px = self._to_pixel(radius, unit)
		gip = GeoInterpolation(callback = lambda pt: self.blit_on_pixel(destination_ctx, pt))
		gip.circle(center_pt_pixel, radius_px)

	def draw_path(self, path, color = None, unit = "px"):
		if color is not None:
			self._cctx.set_source_rgb(*color)
		for cmd in path:
			if cmd.cmd == "moveto":
				point = self._to_pixel(cmd.coord, unit)
				self._cctx.move_to(point.x, point.y)
			elif cmd.cmd == "lineto":
				point = self._to_pixel(cmd.coord, unit)
				self._cctx.line_to(point.x, point.y)
		self._cctx.fill()

	def write_to_png(self, filename):
		self._surface.write_to_png(filename)

class ApertureGenerator():
	_COLORS = {
		"red":		(1, 0, 0),
		"green":	(0, 1, 0),
		"blue":		(0, 0, 1),
		"black":	(0, 0, 0),
		"white":	(1, 1, 1),
	}

	@classmethod
	def generate_x(cls, size = 5, width = 1, color = "red"):
		size = round(size)
		aperture = CairoContext(dimensions = Vector2d(size, size), dpi = None)
		if color in cls._COLORS:
			(r, g, b) = cls._COLORS.get(color)
		else:
			(r, g, b) = color
		aperture.cctx.set_source_rgb(r, g, b)
		aperture.cctx.set_line_width(width)
		aperture.cctx.move_to(0, 0)
		aperture.cctx.line_to(size, size)
		aperture.cctx.stroke()

		aperture.cctx.move_to(0, size)
		aperture.cctx.line_to(size, 0)
		aperture.cctx.stroke()
		return aperture

	@classmethod
	def generate_dot(cls, size = 1, color = "red"):
		aperture = CairoContext(dimensions = Vector2d(size, size), dpi = None)
		if color in cls._COLORS:
			(r, g, b) = cls._COLORS.get(color)
		else:
			(r, g, b) = color
		aperture.cctx.set_source_rgb(r, g, b)
		aperture.cctx.rectangle(0, 0, size, size)
		aperture.cctx.fill()
		return aperture


	@classmethod
	def generate_circular(cls):
		pass

if __name__ == "__main__":
	aperture = CairoContext(10, 10)
	aperture.cctx.set_source_rgb(1, 0, 0)
	aperture.cctx.set_line_width(2)
	aperture.cctx.move_to(1, 1)
	aperture.cctx.line_to(9, 9)
	aperture.cctx.stroke()
	aperture.cctx.move_to(9, 1)
	aperture.cctx.line_to(1, 9)
	aperture.cctx.stroke()
	aperture.write_to_png("a.png")

	ctx = CairoContext(600, 600)
	ctx.cctx.set_source_rgb(0, 0, 0)
	ctx.cctx.set_line_width(10)

	ctx.cctx.move_to(0, 0)
	ctx.cctx.line_to(100, 100)
	ctx.cctx.stroke()


#	ctx.cctx.set_source(pat)
#	ctx.cctx.move_to(200, 200)
#	ctx.cctx.line_to(200+100, 200+100)
#	ctx.cctx.stroke()
	aperture.blit_line(ctx, 200, 200, 300, 200)

	ctx.write_to_png("test.png")
