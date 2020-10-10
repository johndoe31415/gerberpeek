#	gerberpeek - Render RS-274X Gerber files to image
#	Copyright (C) 2019-2020 Johannes Bauer
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
from .CairoContext import CairoContext
from .Vector2d import Vector2d

class ApertureRenderer():
	_COLORS = {
		"red":		(1, 0, 0),
		"green":	(0, 1, 0),
		"blue":		(0, 0, 1),
		"black":	(0, 0, 0),
		"white":	(1, 1, 1),
	}

	@classmethod
	def generate_x(cls, size = 5, width = 1, color = "red"):
		"""Useful for debugging, not used in Gerber."""
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
		return cls.generate_rectangluar(width = size, height = size, color = color)

	@classmethod
	def generate_rectangular(cls, width, height, color):
		aperture = CairoContext(dimensions = Vector2d(width, height), dpi = None)
		if color in cls._COLORS:
			(r, g, b) = cls._COLORS.get(color)
		else:
			(r, g, b) = color
		aperture.cctx.set_source_rgb(r, g, b)
		aperture.cctx.rectangle(0, 0, width, height)
		aperture.cctx.fill()
		return aperture

	@classmethod
	def generate_obround(cls, width, height, color):
		radius = min(width, height) / 2
		padding = 1
		dimensions = Vector2d(math.ceil(width) + (2 * padding), math.ceil(height) + (2 * padding))
		aperture = CairoContext(dimensions = dimensions, dpi = None)

		if color in cls._COLORS:
			(r, g, b) = cls._COLORS.get(color)
		else:
			(r, g, b) = color
		aperture.cctx.set_source_rgb(r, g, b)
		if height < width:
			# Horizontal obround
			aperture.cctx.rectangle(radius + padding, padding, width - (2 * radius), height)
			aperture.cctx.fill()
			aperture.cctx.arc(width - radius + padding, radius + padding, radius, 0, 2 * math.pi)
		else:
			# Vertical obround
			aperture.cctx.rectangle(padding, radius + padding, width, height - (2 * radius))
			aperture.cctx.fill()
			aperture.cctx.arc(radius + padding, padding + height - radius, radius, 0, 2 * math.pi)
		aperture.cctx.arc(radius + padding, radius + padding, radius, 0, 2 * math.pi)
		aperture.cctx.fill()
		return aperture

	@classmethod
	def generate_circular(cls, radius, color):
		rounded_radius = (2 * math.ceil(radius)) + 4
		dimensions = Vector2d(rounded_radius, rounded_radius)
		aperture = CairoContext(dimensions = dimensions, dpi = None)

		if color in cls._COLORS:
			(r, g, b) = cls._COLORS.get(color)
		else:
			(r, g, b) = color
		mid_pixel = dimensions / 2
		aperture.cctx.set_source_rgb(r, g, b)
		aperture.cctx.arc(mid_pixel.x, mid_pixel.y, radius, 0, 2 * math.pi)
		aperture.cctx.fill()
		return aperture

	@classmethod
	def from_raw_definition(cls, aperture_definition_template, aperture_definition_params, dpi, color):
		if aperture_definition_template == "C":
			# Circular aperture
			radius_in = aperture_definition_params[0] / 2
			radius_px = radius_in * dpi
			aperture = cls.generate_circular(radius_px, color = color)
		elif aperture_definition_template == "O":
			# Obround aperture
			width_px = aperture_definition_params[0] * dpi
			height_px = aperture_definition_params[1] * dpi
			aperture = cls.generate_obround(width_px, height_px, color = color)
		elif aperture_definition_template == "R":
			# Rectangular aperture
			width_px = aperture_definition_params[0] * dpi
			height_px = aperture_definition_params[1] * dpi
			aperture = cls.generate_rectangular(width_px, height_px, color = color)
		else:
			raise NotImplementedError(aperture_definition_template)
		aperture.dpi = dpi
		return aperture

	@classmethod
	def from_macro_definition(cls, aperture_macro, dpi, color):
		print("TODO: NOT IMPLEMENTED")
		aperture = cls.generate_circular(5, color = color)
		aperture.dpi = dpi
		return aperture

	@classmethod
	def from_definition(cls, aperture_definition, dpi, color):
		if not aperture_definition.is_macro:
			return cls.from_raw_definition(aperture_definition.template, aperture_definition.params, dpi, color)
		else:
			return cls.from_macro_definition(aperture_definition, dpi, color)

	@classmethod
	def physical_extents_macro(cls, aperture_macro):
		print("TODO: NOT IMPLEMENTED")
		return Vector2d(0.1, 0.1)

	@classmethod
	def physical_extents(cls, aperture_definition):
		if aperture_definition.is_macro:
			return cls.physical_extents_macro(aperture_definition)
		elif aperture_definition.template == "C":
			# Circular aperture
			diameter_in = aperture_definition.params[0]
			return Vector2d(diameter_in, diameter_in)
		elif aperture_definition.template in [ "O", "R" ]:
			# Obround or rectangular aperture
			width_in = aperture_definition.params[0]
			height_in = aperture_definition.params[1]
			return Vector2d(width_in, height_in)
		else:
			raise NotImplementedError(aperture_definition)
