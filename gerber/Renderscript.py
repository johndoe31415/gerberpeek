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
import json
import sys
from gerber import Vector2d, CairoContext, CairoCallback, Interpreter, SizeDeterminationCallback

class RenderscriptSyntaxError(Exception): pass
class RenderscriptRenderError(Exception): pass

class Renderscript():
	_COLOR_REGEX = re.compile("#?(?P<r>[0-9a-fA-F]{2})(?P<g>[0-9a-fA-F]{2})(?P<b>[0-9a-fA-F]{2})")
	def __init__(self, args):
		self._args = args
		self._script = {
			"definitions": { },
			"steps": { },
		}
		self._deliverable_names = None
		self._sources = [ ]
		self._deliverables = { }

	def add_script(self, script_filename):
		with open(script_filename) as f:
			new_script = json.load(f)
		if self._script is None:
			# First script
			self._script = new_script
		else:
			self._merge_script(new_script)
		self._check(script_filename, self._script)

	def _merge_script(self, new_script):
		if "definitions" in new_script:
			self._script["definitions"].update(new_script["definitions"])
		if "steps" in new_script:
			self._script["steps"].update(new_script["steps"])

	@staticmethod
	def _check(filename, script):
		if not isinstance(script, dict):
			raise RenderscriptSyntaxError("%s: Expect the render script to be a dictionary." % (filename))
		if not "steps" in script:
			raise RenderscriptSyntaxError("%s: Render script missing render steps." % (filename))
		for (name, step) in script["steps"].items():
			if step["action"] not in [ "render-gerber", "render-drill", "compose" ]:
				raise RenderscriptSyntaxError("%s: Render step action '%s' unsupported." % (step["action"], filename))

	@property
	def deliverable_names(self):
		if self._deliverable_names is None:
			self._deliverable_names = set()
			for (name, step) in self._script["steps"].items():
				if step.get("deliverable"):
					self._deliverable_names.add(step["deliverable"])
		return iter(self._deliverable_names)

	def add_definition(self, deffile):
		with open(deffile) as f:
			definition = json.load(f)
		print(definition)

	def add_source(self, sourcefile):
		self._sources.append(sourcefile)

	def _find_file(self, regex_str, regex_opts = None):
		if regex_opts is None:
			regex_opts = [ ]
		flags = 0
		for regex_opt in regex_opts:
			if regex_opt == "ignore_case":
				flags |= re.IGNORECASE
		regex = re.compile(regex_str, flags = flags)
		for filename in self._sources:
			match = regex.fullmatch(filename)
			if match:
				return filename
		else:
			print("Warning: No source file found to match regex '%s'." % (regex_str))
			return None

	def _replace_definitions(self, text):
		for (name, value) in self._script["definitions"].items():
			pattern = "$" + name
			text = text.replace(pattern, value)
		return text

	def _parse_color(self, color_str):
		match = self._COLOR_REGEX.fullmatch(color_str)
		if match is None:
			raise RenderscriptRenderError("Could not parse color string '%s'." % (color_str))
		match = match.groupdict()
		return (int(match["r"], 16) / 255, int(match["g"], 16) / 255, int(match["b"], 16) / 255)

	def _render_gerber(self, step):
		infile = self._find_file(step["file_regex"], step.get("file_regex_opts"))
		if infile is None:
			return None
		if self._args.verbose >= 2:
			print("Rendering %s" % (infile), file = sys.stderr)

		src_color = self._parse_color(self._replace_definitions(step.get("color", "#000000")))

		# Determine dimensions first
		size_cb = SizeDeterminationCallback()
		Interpreter(infile, size_cb).run()
		dimensions = size_cb.max_pt - size_cb.min_pt
		if self._args.verbose >= 2:
			print("%s: dimensions %s to %s size %s" % (infile, size_cb.min_pt, size_cb.max_pt, dimensions), file = sys.stderr)

		cctx = CairoContext.create_inches(dimensions, offset_inches = size_cb.min_pt, dpi = self._args.resolution)
		callback = CairoCallback(cctx, src_color = src_color)
		Interpreter(infile, callback).run()
		return cctx

	def _render_drill(self, step):
		pass

	def _render_compose(self, step):
		sub_ctxts = [ ]
		for source in step["sources"]:
			sub_ctx = self.render(source["name"])
			if sub_ctx is None:
				print("Warning: Unable to render source '%s', ignoring it." % (source["name"]))
				continue
			else:
				sub_ctxts.append(sub_ctx)

		bg_color = self._parse_color(self._replace_definitions(step.get("background", "#ffffff")))
		cctx = CairoContext.create_composition_canvas(sub_ctxts)
		cctx.fill(bg_color)
		cctx.compose_all(sub_ctxts)
		return cctx

	def _do_render(self, name):
		step = self._script["steps"][name]
		if step["action"] == "render-gerber":
			return self._render_gerber(step)
		elif step["action"] == "render-drill":
			return self._render_drill(step)
		elif step["action"] == "compose":
			return self._render_compose(step)
		else:
			raise NotImplementedError(step["action"])

	def render(self, name):
		if name not in self._deliverables:
			self._deliverables[name] = self._do_render(name)
		return self._deliverables[name]
