import sublime
import sublime_plugin
import urllib.request, urllib.parse
import json

def get_popup_content(items):
	if not items:
		return "No suggestions"
	elif "!RIJEČ!" in items:
		return "Might be a word!"
	elif "!IME!" in items:
		return "Might be a name!"
	else:
		html = "<b>Suggestions: </b>"
		for i in items:
			html += "<li><a href='{0}'>{0}</a></li>".format(i)
		return html

class HascheckListener(sublime_plugin.ViewEventListener):
	def on_hover(self, point, hover_zone):
		if suggestions and hover_zone == sublime.HOVER_TEXT:
			selection = self.view.word(point)
			text = self.view.substr(selection)
			if text in suggestions.keys():
				def select(text):
					args = {
						"begin"	: selection.a,
						"end"	: selection.b,
						"text"	: text
					}
					self.view.run_command("hascheck_replace_text", args)
					self.view.hide_popup()
					
				self.view.show_popup(
					get_popup_content(suggestions[text]),
					sublime.HIDE_ON_MOUSE_MOVE_AWAY,
					point,
					on_navigate = select
				)

	def on_modified_async(self):
		regions = self.view.get_regions("hascheck_errors")
		for r in regions:
			if self.view.substr(r) not in suggestions.keys():
				self.view.run_command("hascheck_remove_region", {"begin": r.a, "end": r.b})


class HascheckReplaceText(sublime_plugin.TextCommand):
	def run(self, edit, begin, end, text):
		self.view.replace(edit, sublime.Region(begin, end), text)
		self.view.run_command("hascheck_remove_region", {"begin": begin, "end": end})
		return


class HascheckRemoveRegion(sublime_plugin.TextCommand):
	def run(self, edit, begin, end):
		regions = self.view.get_regions("hascheck_errors")
		regions.remove(sublime.Region(begin, end))
		self.view.add_regions("hascheck_errors", regions, "invalid", "dot", flags)
		return

class HascheckCommand(sublime_plugin.TextCommand):
	def highlight_errors(self, errors):
		regions = []
		for e in errors:
			length = e["length"]
			for p in e["position"]:
				regions.append(sublime.Region(p, p + length))
			suggestions[e["suspicious"]] = e["suggestions"]
		self.view.add_regions("hascheck_errors", regions, "invalid", "dot", flags)

	def run(self, edit):
		suggestions = {}
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

global suggestions
global flags
global icon

suggestions = {}
flags = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE