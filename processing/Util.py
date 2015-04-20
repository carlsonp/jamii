import sys, os, re, subprocess, magic
sys.path.append("../")
import devknowledge.settings

from py2neo import neo4j


def returnListAllEmails(project):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	all_emails = []

	#http://docs.neo4j.org/refcard/2.0/
	# this returns all emails in the database
	q = "START a=node(*) WHERE HAS(a.email) RETURN a;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		all_emails.append(r.a['email'])

	return all_emails

def fileLength(fname):
	count = 0
	for line in open(fname).xreadlines():
		count += 1
	return count

def returnCandCPlusPlusFiles(all_files, project):
	c_files = []
	for file in all_files:
		full_file = devknowledge.settings.VERSION_CONTROL_REPOS+project+file
		if os.path.isfile(full_file):
			try:
				line = magic.from_file(full_file)
				#Note: ASCII text is VERY generic but there seem to be lots of .cpp and .h files
				#that are being missing by only using C++ source and C source
				found = re.search(r'(C\+\+ source|C source|ASCII text)', line)
				if found:
					c_files.append(file)
			except magic.MagicException:
				print "Unable to identify file type: ", file
	return c_files
	
def returnListCPPFilesChanged(git_repo, hash):
	files_changed = []
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" diff-tree --no-commit-id --name-only -r "+hash], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		line = "/"+line.rstrip('\n')
		check_ending = re.search(r'(\.h|\.cpp|\.c|\.hpp)$', line)
		if check_ending:
			files_changed.append(git_repo+line)
	return files_changed

def returnHeadHash(git_repo):
	#print "Running git rev-parse HEAD."
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" rev-parse HEAD"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		found = re.search(r'^[\w]{40}$', line)
		if found:
			head_hash = found.group()
			#print "Head hash: ", str(head_hash)
			return head_hash

def returnCPPFiles(git_repo, project):
	c_files = []
	p = subprocess.Popen(["find "+git_repo+" -name '*.cpp' -o -name '*.h' -o -name '*.hpp' -o -name '*.c'"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		line = line.rstrip("\n")
		current_file = line.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
		c_files.append(current_file)
	return c_files		

def returnMasterHash(git_repo):
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" log -n 1 origin/master --pretty=format:'%H'"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		found = re.search(r'^[\w]{40}$', line)
		if found:
			return found.group()

def checkoutHash(git_repo, commit_hash):
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" checkout -f "+commit_hash], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	if p.wait(): #wait for the background process to finish
		return

def returnFilesLastLine(project):
	all_files = []
	last_lines = []
	for root, subfolders, files in os.walk(devknowledge.settings.VERSION_CONTROL_REPOS+project):
		for folder in devknowledge.settings.BLACKLIST_FOLDERS:
			if folder in subfolders:
				subfolders.remove(folder)
		for file in files:
			found = re.search(r'\.([A-Za-z0-9]+)$', file)
			if found:
				file_extension = found.group().lower()
				if file_extension in devknowledge.settings.WHITELIST_EXTENSIONS:
					file = os.path.join(root, file)
					if os.path.isfile(file):
						last_line = fileLength(file)
						if last_line != 0: #make sure the file isn't empty
							#this way we have the subfolder as well
							file = file.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
							#print "Adding file, ", file
							all_files.append(file)
							last_lines.append(last_line)
	return all_files, last_lines

def returnProjectType(folder):
	if os.path.isdir(os.path.join(folder, ".git")):
		return "git"
	if os.path.isdir(os.path.join(folder, ".hg")):
		return "hg"
	return "error"

def checkDatabaseFolderSize():
	try:
		limit = devknowledge.settings.NEO4J_DATABASE_SIZE_LIMIT
	except AttributeError:
		# NEO4J_DATABASE_SIZE_LIMIT is not defined in the settings file
		return

	p = subprocess.Popen(["du -sb "+devknowledge.settings.NEO4J_DATABASE], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		found = re.search(r'[0-9]+', line)
		if found:
			if float(int(found.group())/1024)/1024 > limit:
				print "Size (MB): ", float(int(found.group())/1024)/1024
				print "We went over the size limit, exiting..."
				sys.exit(0)

def splitNameEmail(string):
	string = removeNonAscii(string)
	found_email = re.search(r'[a-zA-Z0-9._%+-/~]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', string)
	if found_email:
		try:
			email = found_email.group().strip().decode("utf-8")
			string = string.replace(email, "")
			email = email.lower()
			#strip out any weird characters in the name
			string = re.sub(r'(\<|\>|\(|\)|\"|\.|\\|\*|\?|\-|\:|\@|\,|\/|(\=iso\-8859\-1q)|(\=ISO\-8859\-1Q))', "", string).strip().decode("utf-8")
			name = string
		except UnicodeDecodeError:
			print "Unable to convert from <str> to <unicode>: ", string

		#print "Returning: '"+name+"' email: '"+email+"'"
		return name, email

	print "Unable to match string to search criteria for name/email:", string
	return None, None

def removeNonAscii(s):
	#http://stackoverflow.com/questions/1342000/how-to-replace-non-ascii-characters-in-string
	return "".join(i for i in s if ord(i)<128)


def getIncludeDirectories(git_repo):
	include_dirs = []
	include_dirs.append(git_repo) #add current directory
	for root, dirs, files in os.walk(git_repo):
		for singledir in dirs:
			include_dirs.append(os.path.abspath(singledir))

	return include_dirs
