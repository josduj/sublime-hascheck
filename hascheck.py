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
	elif "!TUĐICA!" in items:
		return "Might be foreign word!"
	else:
		html = "<b>Suggestions: </b>"
		for i in items:
			html += "<li><a href='{0}'>{0}</a></li>".format(i)
		return html

def get_flags(highlight, underline):
	if highlight == "underline":
		clean = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE
		if underline == "solid":
			return clean | sublime.DRAW_SOLID_UNDERLINE
		elif underline == "stippled":
			return clean | sublime.DRAW_STIPPLED_UNDERLINE
		else:
			return clean | sublime.DRAW_SQUIGGLY_UNDERLINE
	elif highlight == "outline":
		return sublime.DRAW_NO_FILL
	else:
		return 0

def replace_text(view, region, text):
	args = {
		"begin"	: region.a,
		"end"	: region.b,
		"text"	: text
	}
	view.run_command("hascheck_replace_text", args)
	view.hide_popup()

def show_suggestions_menu(view, region):
	def popup():
		view.show_popup_menu(suggestions[text], lambda x:
			x == -1 or replace_text(view, region, suggestions[text][x]))
	text = view.substr(region)
	view.show_at_center(region)
	sublime.Selection.clear(view)
	sublime.Selection.add(view, region)
	sublime.set_timeout_async(popup, 200)

def remove_region(view, region):
	regions = view.get_regions("hascheck_errors")
	regions.remove(region)
	view.add_regions("hascheck_errors", regions, SCOPE, ICON, FLAGS)

class HascheckListener(sublime_plugin.ViewEventListener):
	def on_hover(self, point, hover_zone):
		if suggestions and hover_zone == sublime.HOVER_TEXT:
			selection = self.view.word(point)
			text = self.view.substr(selection)
			if text in suggestions.keys():
				self.view.show_popup(
					get_popup_content(suggestions[text]),
					sublime.HIDE_ON_MOUSE_MOVE_AWAY,
					point,
					on_navigate = lambda x: replace_text(self.view, selection, x)
				)

	def on_modified_async(self):
		regions = self.view.get_regions("hascheck_errors")
		for r in regions:
			if self.view.substr(r) not in suggestions.keys():
				remove_region(self.view, r)

class HascheckReplaceText(sublime_plugin.TextCommand):
	def run(self, edit, begin, end, text):
		self.view.replace(edit, sublime.Region(begin, end), text)
		return

class HascheckNextErrorCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		regions = self.view.get_regions("hascheck_errors")
		return len(regions) > 0 and self.view.sel()[0].end() < regions[-1].a

	def run(self, edit):
		regions = self.view.get_regions("hascheck_errors")
		for reg in regions:
			if self.view.sel()[0].end() < reg.a:
				show_suggestions_menu(self.view, reg)
				return

class HascheckPrevErrorCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		regions = self.view.get_regions("hascheck_errors")
		return len(regions) > 0 and self.view.sel()[0].end() > regions[0].b

	def run(self, edit):
		regions = self.view.get_regions("hascheck_errors")
		for reg in reversed(regions):
			if self.view.sel()[0].end() > reg.b:
				show_suggestions_menu(self.view, reg)
				return

class HascheckCommand(sublime_plugin.TextCommand):
	def highlight_errors(self, errors):
		regions = []
		for e in errors:
			length = e["length"]
			for p in e["position"]:
				regions.append(sublime.Region(p, p + length))
			suggestions[e["suspicious"]] = e["suggestions"]
		self.view.add_regions("hascheck_errors", regions, SCOPE, ICON, FLAGS)

	def run(self, edit):
		suggestions = {}
		text = self.view.substr(sublime.Region(0, self.view.size()))

		def fetch_async():
			data = bytes(urllib.parse.urlencode({ "textarea" : text }).encode())
			with urllib.request.urlopen("https://ispravi.me/api/ispravi.pl", data) as url:
				res = json.loads(url.read().decode())["response"]
				if res:
					self.highlight_errors(res["error"])
					self.view.set_status("hascheck", "{0} errors".format(res["errors"]))
				else:
					self.view.set_status("hascheck", "No errors")
			return

		sublime.set_timeout_async(fetch_async, 0)

def plugin_loaded():
	global FLAGS, ICON, SCOPE
	global suggestions
	
	suggestions = {}
	settings = sublime.load_settings("Hascheck.sublime-settings")

	FLAGS = get_flags(settings.get("highlight_style"), settings.get("underline_style"))
	ICON = settings.get("icon_style")
	SCOPE = "invalid"