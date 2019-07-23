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

class NoRegexMatchedException(Exception): pass
class NoCallbackFoundException(Exception): pass

class MultiRegex():
	def __init__(self, regex_dict):
		self._dict = regex_dict

	def fullmatch(self, pattern, callback, callback_prefix = "_match_", groupdict = False):
#		print(pattern)
		for (name, regex) in self._dict.items():
			match = regex.fullmatch(pattern)
			if match is not None:
				callback_name = callback_prefix + name
				callback = getattr(callback, callback_name, None)
				if callback is None:
					raise NoCallbackFoundException("Callback '%s' not present for match %s." % (callback_name, name))
				if groupdict:
					match = match.groupdict()
#				print("> %s" % (str(match)))
				callback(match)
				return
		raise NoRegexMatchedException("No regex matched: %s" % (pattern))
