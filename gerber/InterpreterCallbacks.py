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
import collections
from .CairoContext import CairoContext
from .Vector2d import Vector2d

class PrintCallback():
	def _generic_method(self, key, *args):
		print(key, args)

	def __getattr__(self, key):
		return lambda *args: self._generic_method(key, *args)

class BaseCallback():
	def __init__(self):
		pass

	def begin_path(self):
		pass

	def region_move(self, point):
		pass

	def region_line(self, point):
		pass

	def region_arc(self, TODO):
		pass

	def drawmode_clear(self):
		pass

	def drawmode_dark(self):
		pass

	def end_path(self):
		pass

	def close_contour(self):
		pass

	def select_aperture(self, aperture):
		pass

	def circle(self, center_pt, radius):
		pass

	def arc_ccw(self, start_pt, end_pt, center_pt):
		pass

	def arc_cw(self, start_pt, end_pt, center_pt):
		pass

	def line(self, start_pt, end_pt):
		pass

	def flash_at(self, point):
		pass

class CairoCallback(BaseCallback):
	_MoveToCmd = collections.namedtuple("PathCommandMoveTo", [ "cmd", "coord" ])
	_LineToCmd = collections.namedtuple("PathCommandLineTo", [ "cmd", "coord" ])
	_ArcToCmd = collections.namedtuple("PathCommandArcTo", [ "cmd", "TODO" ])

	def __init__(self, cairo_context, src_color = None):
		BaseCallback.__init__(self)
		self._cctx = cairo_context
		if src_color is None:
			self._src_color = (0, 0, 0)
		else:
			self._src_color = src_color
		self._aperture = None
		self._path = [ ]

	def begin_path(self):
		self._path = [ ]

	def region_move(self, point):
		self._path.append(self._MoveToCmd(cmd = "moveto", coord = point))

	def region_line(self, point):
		self._path.append(self._LineToCmd(cmd = "lineto", coord = point))

	def region_arc(self, TODO):
		self._path.append(self._ArcToCmd(cmd = "arcto", coord = point))

	def drawmode_clear(self):
		self._cctx.set_mode_erase()

	def drawmode_dark(self):
		self._cctx.set_mode_draw()

	def end_path(self):
		self._cctx.cctx.fill()
		self._cctx.draw_path(self._path, color = self._src_color, unit = "in")
		self._path = [ ]

	def close_contour(self):
		pass

	def select_aperture(self, aperture):
		if aperture.template == "C":
			# Create circle aperture
			radius_in = aperture.params / 2
			width_height_in = 2.1 * radius_in
			self._aperture = CairoContext.create_inches(Vector2d(width_height_in, width_height_in), dpi = self._cctx.dpi)
			mid_pixel = self._aperture.width / 2
			radius_pixel = radius_in * self._aperture.dpi
			self._aperture.cctx.set_source_rgb(*self._src_color)
			self._aperture.cctx.arc(mid_pixel, mid_pixel, radius_pixel, 0, 2 * math.pi)
			self._aperture.cctx.fill()
		else:
			# TODO
			pass

	def circle(self, center_pt, radius):
		if self._aperture is not None:
			self._aperture.blit_circle(self._cctx, center_pt, radius, unit = "in")

	def arc_ccw(self, start_pt, end_pt, center_pt):
		if self._aperture is not None:
			self._aperture.blit_arc_ccw(self._cctx, start_pt, end_pt, center_pt, unit = "in")

	def arc_cw(self, start_pt, end_pt, center_pt):
		if self._aperture is not None:
			self._aperture.blit_arc_cw(self._cctx, start_pt, end_pt, center_pt, unit = "in")

	def line(self, start_pt, end_pt):
		if self._aperture is not None:
			self._aperture.blit_line(self._cctx, start_pt, end_pt, unit = "in")

	def flash_at(self, point):
		self.line(point, point)

class SizeDeterminationCallback(BaseCallback):
	def __init__(self):
		BaseCallback.__init__(self)
		self._minx = None
		self._miny = None
		self._maxx = None
		self._maxy = None
		self._aperture = None

	def _add_point(self, point):
		if self._aperture is not None:
			minpt = point - self._aperture
			maxpt = point + self._aperture
		else:
			minpt = point
			maxpt = point
		self._minx = minpt.x if (self._minx is None) else min(self._minx, minpt.x)
		self._miny = minpt.y if (self._miny is None) else min(self._miny, minpt.y)
		self._maxx = maxpt.x if (self._maxx is None) else max(self._maxx, maxpt.x)
		self._maxy = maxpt.y if (self._maxy is None) else max(self._maxy, maxpt.y)

	@property
	def min_pt(self):
		if (self._minx is not None) and (self._miny is not None):
			return Vector2d(self._minx, self._miny)
		else:
			return None

	@property
	def max_pt(self):
		if (self._maxx is not None) and (self._maxy is not None):
			return Vector2d(self._maxx, self._maxy)
		else:
			return None

	def line(self, start_pt, end_pt):
		self._add_point(start_pt)
		self._add_point(end_pt)

	def flash_at(self, point):
		self._add_point(point)
