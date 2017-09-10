import sublime
import sublime_plugin
import urllib.request, urllib.parse
import json

class HascheckCommand(sublime_plugin.TextCommand):
	def highlight_errors(self, errors):
		regions = []
		for e in errors:
			length = e["length"]
			for p in e["position"]:
				regions.append(sublime.Region(p, p + length))
		flags = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
		self.view.add_regions("hascheck_errors", regions, "invalid", "dot", flags)

	def run(self, edit):
		text = self.view.substr(sublime.Region(0, self.view.size()))
		data = bytes(urllib.parse.urlencode({ "textarea" : text }).encode())
		with urllib.request.urlopen("https://ispravi.me/api/ispravi.pl", data) as url:
			res = json.loads(url.read().decode())["response"]
			if res:
				self.highlight_errors(res["error"])
				self.view.set_status("hascheck", "{0} errors".format(res["errors"]))
			else:
				self.view.set_status("hascheck", "No errors")
		return