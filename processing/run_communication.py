import sys, os, re, subprocess, mailbox
from datetime import datetime
sys.path.append("../")
import devknowledge.settings

from DatabaseThread import communicationDatabaseThread, consumerDatabaseThreadManager, CommunicationEntry
import Util
from ThreadPool import ThreadPool


projects = [d for d in os.listdir(devknowledge.settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, d))]

manager = consumerDatabaseThreadManager("communication")

def getBodyFromEmail(msg):
	#http://stackoverflow.com/questions/7166922/extracting-the-body-of-an-email-from-mbox-file-decoding-it-to-plain-text-regard
	body = None
	#Walk through the parts of the email to find the text body.
	if msg.is_multipart():
		for part in msg.walk():
			# If part is multipart, walk through the subparts.
			if part.is_multipart():
				for subpart in part.walk():
					if subpart.get_content_type() == 'text/plain':
						# Get the subpart payload (i.e the message body)
						body = subpart.get_payload(decode=True)
			# Part isn't multipart so get the email body
			elif part.get_content_type() == 'text/plain':
				body = part.get_payload(decode=True)

	# If this isn't a multi-part message then get the payload (i.e the message body)
	elif msg.get_content_type() == 'text/plain':
		body = msg.get_payload(decode=True)

	if body is not None:
		# Cleanup the body
		body = Util.removeNonAscii(body)

		# No checking done to match the charset with the correct part.
		charsets = set({})
		for c in msg.get_charsets():
			if c is not None:
				charsets.update([c])
		for charset in charsets:
			#special case
			#http://stackoverflow.com/questions/11889262/how-do-i-convert-iso-8859-8-i-to-utf-8
			if charset == "iso-8859-8-i":
				charset = "iso-8859-8"
			try:
				body = body.decode(charset)
			except UnicodeDecodeError:
				print "UnicodeDecodeError: encountered: ",charset
			except AttributeError:
				print "AttributeError: encountered: ",charset
			except LookupError:
				print "LookupError: encountered: ",charset
	return body


#iterate through all projects
for project in projects:
	if project in devknowledge.settings.PROJECT_FOLDERS:
		for mailing_list in devknowledge.settings.MAILING_LIST_FILES:
			print "Reading mbox file: ", devknowledge.settings.MBOX_ARCHIVES+mailing_list
			#http://docs.python.org/2/library/mailbox.html
			mbox = mailbox.mbox(devknowledge.settings.MBOX_ARCHIVES+mailing_list)

			number_to_process = len(mbox)
			print "Number of emails to process: ", number_to_process
			processed_files = 0

			for message in mbox:
				#https://en.wikipedia.org/wiki/Email#Header_fields
				if message['Subject'] is not None:
					#Grab the body of the email
					#body = getBodyFromEmail(message)
					body = None
					subject = Util.removeNonAscii(message['Subject'])
					if subject.startswith("Re: "):
						subject = subject.replace("Re: ", "").strip()
					name, email = Util.splitNameEmail(message['From'])
					#http://docs.python.org/2/library/datetime.html#datetime.datetime.strptime
					#Apparently UTC offset isn't really supported on all platforms? I don't want to use a third-party library, we'll just go without it
					#http://stackoverflow.com/questions/10494312/parsing-time-string-in-python
					date = re.sub(r"[+-]([0-9])+.*", "", message['Date']).strip()
					#strip off GMT, UT, CST, etc. from the end of the string: e.g.: Thu, 12 Dec 2002 23:36:29 CST
					UTC_GMT = re.search(r'([0-9]{1,2}:[0-9]{2}:[0-9]{2})(.*)', date) #first part of match is time, second is UTC/GMT
					if UTC_GMT:
						date = date.replace(UTC_GMT.group(2), "").strip()
					#Dates are in a variety of formats, so we'll try a bunch
					date_regexes = ['%a, %d %b %Y %H:%M:%S', '%d %b %Y %H:%M:%S', '%a, %d %b %y %H:%M:%S', '%d %b %y %H:%M:%S', '%a, %d %b %Y %H:%M', '%d %b %Y %H:%M', '%a, %d %b %y %H:%M', '%d %b %y %H:%M']
					found_date = False
					for date_regex in date_regexes:
						try:
							date = datetime.strptime(date, date_regex)
						except ValueError:
							pass #do nothing
						else:
							found_date = True
							break
					if found_date:
						#convert date to epoch for uniformity
						#https://stackoverflow.com/questions/11743019/convert-python-datetime-to-epoch-with-strftime
						epoch = (datetime(date.year, date.month, date.day) - datetime(1970,1,1)).total_seconds()
						entry = CommunicationEntry(name, email, subject, body, epoch)
						manager.addToQueue(entry)
					else:
						print "Unable to find the date for string: ", date
						sys.exit()

				processed_files += 1

				print "Percent done: %.2f %%" % float(float(processed_files)/float(number_to_process) * 100)
				Util.checkDatabaseFolderSize()

manager.markForFinish()
print "Done.  Exiting."


