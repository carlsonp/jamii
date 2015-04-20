import subprocess, re, time, sys

sys.path.append("../")
import devknowledge.settings
import time

from DatabaseThread import consumerDatabaseThread, SaveEntry


def parseHGBlameResult(manager, save_line, hg_repo, line, filename, hg_hash, project):

	#call hg with appropriate parameters
	#http://selenic.com/hg/help/annotate
	#http://stackoverflow.com/questions/89228/calling-an-external-command-in-python
	p = callHG("hg -R "+hg_repo+" annotate -unlcvd -r "+hg_hash+" "+hg_repo+filename+" | sed -n "+str(line)+","+str(line)+"p")
	for line in p.stdout.readlines():
		#http://www.tutorialspoint.com/python/python_reg_expressions.htm
		#group 1: committer name
		#group 2: hash
		#group 3: date (excluding timezone, this just simplifies life a little, otherwise this would be brutal)
		#group 4: line number
		#Regex:
		#^(.*?)\s[0-9]+\s
		#(?<=\s)([\w]{12})\s
		#([\w]{3}\s[\w]{3}\s[0-9]{2}\s[0-9]{2}:[0-9]{2}:[0-9]{2}\s[0-9]{4})
		#\s[+|-]{1}[0-9]{4}:+
		#([0-9]+):
		found = re.search(r'^(.*?)\s[0-9]+\s(?<=\s)([\w]{12})\s([\w]{3}\s[\w]{3}\s[0-9]{2}\s[0-9]{2}:[0-9]{2}:[0-9]{2}\s[0-9]{4})\s[+|-]{1}[0-9]{4}:+([0-9]+):', line)
		if found:
			#convert from <str> to <unicode> so we can deal with international characters
			committer = found.group(1).strip().decode("utf-8")
			#split out the committer name and email address
			inner_found = re.search(r'(.*)\s<(.*@.*)>', committer)
			if inner_found:
				committer = inner_found.group(1)
				email = inner_found.group(2)
			else:
				print "Trouble parsing email address: ", committer
			previous_hash = found.group(2)
			#convert human date format to epoch format
			epoch = int(time.mktime(time.strptime(found.group(3), '%a %b %d %H:%M:%S %Y')))
			days = (((time.mktime(time.gmtime()) - float(epoch)) / 60) / 60) / 24
			old_line = found.group(4)

			#print "Filename: ", filename, " Committer: ", committer, " Previous hash: ", previous_hash, " Days: ", days, " Old Line: ", old_line, " Date: ", str(found.group(3))

			#TODO: check if this is duplicating values
			entry = SaveEntry(project, save_line, days, hg_hash, committer, email, filename)
			manager.addToQueue(entry)

			if hg_hash != previous_hash:
				#recursive call
				parseHGBlameResult(manager, save_line, hg_repo, old_line, filename, previous_hash, project)
		else:
			print "Something went wrong in Mercurial regex."

def callHG(hgcall):
	return subprocess.Popen([hgcall], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def storeKnowledge(manager, project, filename, start_line, end_line, start_hash):
	#for each line in the file
	for i in range(start_line, end_line+1):
		parseHGBlameResult(manager, i, devknowledge.settings.VERSION_CONTROL_REPOS+project, i, filename, start_hash, project)

def returnTipHash(hg_repo):
	#print "Running tip hash."
	p = subprocess.Popen(["hg -R "+hg_repo+" tip"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		found = re.search(r'(?<=^changeset:).*', line)
		if found:
			tip_hash = found.group().partition(":")[2]
			#print "Tip hash: ", str(tip_hash)
			return tip_hash
