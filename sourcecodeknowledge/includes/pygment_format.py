from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.util import ClassNotFound #this is for exceptions
from pygments.formatters import HtmlFormatter


#http://pygments.org/docs/formatters/
class CodeHtmlFormatter(HtmlFormatter):
	def wrap(self, source, outfile):
		return self._wrap_code(source)

	def _wrap_code(self, source):
		yield 0, '<div class="source"><pre>'
		counter = 1
		for i, t in source:
			if i == 1:
				# single line
				t = '<div class="ui-widget-content" lineNum="'+str(counter)+'">' + str(counter) + "\t" + t + '</div>'
				counter += 1
			yield i, t
		yield 0, '</pre></div>'


def formatSourcecode(filename, code):
	try:
		#Don't strip blank lines
		lexer = guess_lexer_for_filename(filename, code, stripnl=False)
		language = lexer.name
		# http://pygments.org/docs/formatters/
		#the <br> separator gets around issues with files that have spaces at the beginning and line numbers not lining up
		#formatter = HtmlFormatter(cssclass="source",linenos=True,full=False,lineseparator="<br>") #<- default formatter
		formatter = CodeHtmlFormatter(cssclass="source",linenos=False,full=False,lineseparator="<br>") #<- custom formatter
		highlighted = highlight(code, lexer, formatter)
	except ClassNotFound:
		language = "Unknown"
		highlighted = "Unable to display the contents of this file.  Is this a binary file?"

	css = HtmlFormatter().get_style_defs('.highlight')

	return highlighted, css, language
