
import os

from django.conf import settings


def readFile(file):
	code = ""
	number_lines = 0
	# make sure there are no ../ in the URL string
	#TODO: does this need more security checks?
	if "../" in file:
		return "", 0

	# check to make sure the file exists
	if not os.path.isfile(settings.VERSION_CONTROL_REPOS+file):
		return "This file does not exist, perhaps you have an old link?"

	with open(settings.VERSION_CONTROL_REPOS+file, "r") as f:
		for line in f.readlines():
			code = code + line
			number_lines += 1
			if number_lines > 10000:
				return "File Too Large To Display", 0
	f.close()

	return code, number_lines
