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
	def __init__(self, dimensions, dpi, offset = None, invert_y_axis = True):
		(width, height) = round(dimensions.x), round(dimensions.y)
		self._surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
		self._cctx = cairo.Context(self._surface)
		matrix = cairo.Matrix()
		if invert_y_axis:
			matrix.scale(1, -1)
			matrix.translate(0, -height)
		if offset is not None:
			matrix.translate(-offset.x, -offset.y)
			self._offset = offset
		else:
			self._offset = Vector2d(0, 0)
		self._cctx.set_matrix(matrix)
		self._dpi = dpi

	@classmethod
	def create_inches(cls, dimensions_inches, dpi, offset_inches = None, invert_y_axis = True):
		if offset_inches is None:
			offset = None
		else:
			offset = offset_inches * dpi
		return cls(dimensions = dimensions_inches * dpi, dpi = dpi, offset = offset, invert_y_axis = invert_y_axis)

	@classmethod
	def create_composition_canvas(cls, contexts):
		assert(len(contexts) > 0)
		assert(all(context.dpi == contexts[0].dpi for context in contexts))
		(minx, maxx, miny, maxy) = (None, None, None, None)
		for ctx in contexts:
			min_pt = ctx.offset
			max_pt = ctx.offset + ctx.dimensions
			minx = min_pt.x if (minx is None) else min(minx, min_pt.x)
			miny = min_pt.y if (miny is None) else min(miny, min_pt.y)
			maxx = max_pt.x if (maxx is None) else max(maxx, max_pt.x)
			maxy = max_pt.y if (maxy is None) else max(maxy, max_pt.y)
		offset = Vector2d(minx, miny)
		dimensions = Vector2d(maxx, maxy) - offset
		return cls(dimensions = dimensions, offset = offset, dpi = contexts[0].dpi, invert_y_axis = False)

	@property
	def width(self):
		return self.surface.get_width()

	@property
	def height(self):
		return self.surface.get_height()

	@property
	def dimensions(self):
		return Vector2d(self.width, self.height)

	@property
	def offset(self):
		return self._offset

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

	@dpi.setter
	def dpi(self, value):
		assert(self._dpi is None)
		self._dpi = value

	def fill(self, color):
		(r, g, b) = color
		self._cctx.set_source_rgb(r, g, b)
		self._cctx.rectangle(self.offset.x, self.offset.y, self.width, self.height)
		self._cctx.fill()

	def compose_onto(self, destination):
		height_diff = destination.height - self.height
		destination.cctx.set_source_surface(self.surface, self.offset.x, self.offset.y + height_diff)
		destination.cctx.paint()

	def compose_all(self, sources):
		for source in sources:
			source.compose_onto(self)

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

	def __str__(self):
		return "CairoContext<dim %s, offs %s>" % (self.dimensions, self.offset)
