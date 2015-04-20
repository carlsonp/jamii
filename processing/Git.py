import subprocess, re, sys, socket, os

sys.path.append("../")
import devknowledge.settings, Util

from datetime import datetime

from DatabaseThread import consumerDatabaseThread, SaveEntry

from py2neo import neo4j


def parseGitBlameResult(manager, save_line, git_repo, line, filename, git_hash, project, update_existing, most_recent_hash, previous_committers, depth):

	committer = ""
	email = ""
	old_line = ""
	previous_hash = ""
	current_hash = ""

	continue_running = True
	entry = None
	#call git blame with appropriate parameters
	#https://www.kernel.org/pub/software/scm/git/docs/git-blame.html
	#http://stackoverflow.com/questions/89228/calling-an-external-command-in-python
	#print "git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" blame -L"+str(line)+","+str(line)+" --porcelain --incremental "+git_repo+filename+" "+git_hash
	p = callGit("git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" blame -L"+str(line)+","+str(line)+" --porcelain --incremental "+git_repo+filename+" "+git_hash)
	for line in p.stdout.readlines():
		#http://www.tutorialspoint.com/python/python_reg_expressions.htm
		found = re.search(r'(?<=author\s).*', line) #Committer name
		if found:
			#convert from <str> to <unicode> so we can deal with international characters
			committer = found.group().strip().decode("utf-8")
		found = re.search(r'(?<=author-mail\s<).*(?=>)', line) #Committer email
		if found:
			email = found.group().lower()
		found = re.search(r'(^[\w]{40})\s([0-9]+)\s', line) #curent_hash and previous line number
		if found:
			current_hash = found.group(1)
			old_line = found.group(2)
		found = re.search(r'(?<=author-time\s).*', line) #Time since epoch
		if found:
			epoch = found.group()
			#print "Date: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(epoch)))
			#print "Previous committers: ", previous_committers
			if (committer not in previous_committers):
				entry = SaveEntry(project, save_line, epoch, current_hash, committer, email, filename, most_recent_hash)
				previous_committers.append(committer)
		found = re.search(r'(?<=previous\s)[\w]{40}', line) #Previous hash
		if found:
			previous_hash = found.group()
			#print "Previous hash found: ", previous_hash

	#only run if we have an entry (committer may have already been previously added)
	if entry is not None:
		#print "Adding: ", save_line, current_hash, entry.author, entry.filename
		if update_existing:
			#print "Running update existing database method for file:", filename
			continue_running = updateExistingDatabase(entry, previous_committers, old_line, previous_hash)
		else:
			manager.addToQueue(entry)

	#do we continue recursing or not
	if (old_line != "" and previous_hash != "" and continue_running):
		#check max recursive depth setting
		if devknowledge.settings.MAX_RECURSIVE_DEPTH == 0 or depth < devknowledge.settings.MAX_RECURSIVE_DEPTH:
			#recursive call
			parseGitBlameResult(manager, save_line, git_repo, old_line, filename, previous_hash, project, update_existing, most_recent_hash, previous_committers, depth+1)

	#prevent zombie processes
	p.wait()

def callGit(gitcall):
	return subprocess.Popen([gitcall], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def returnLastHash(git_repo, filename):
	#returns the hash for the last time a file has been modified
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" log -n 1 --format='%H' "+git_repo+filename+" | head -1"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		line = line.replace("\n", "")
		#TODO: put regex check in here to make sure this is actually a hash?
		return line

def storeKnowledge(manager, project, filename, start_line, end_line, update_existing, start_hash):
	most_recent_hash = returnLastHash(devknowledge.settings.VERSION_CONTROL_REPOS+project, filename)
	if update_existing:
		#use our most recent hash to check against the file to see if we should even bother running on it
		if not checkRunFile(project, filename, most_recent_hash):
			#there were no changes between then and now for this file
			#print "No changes made, skipping file: ", filename
			return None
	#print "Most recent hash: ", most_recent_hash
	#for each line in the file
	for i in range(start_line, end_line+1):
		parseGitBlameResult(manager, i, devknowledge.settings.VERSION_CONTROL_REPOS+project, i, filename, start_hash, project, update_existing, most_recent_hash, [], 1)
	if update_existing:
		#at this point, we've gone through and matched up the history or created new entries
		#now we can go through and clear all the stale entries and set the new hash value
		clearStaleEntries(project, filename, most_recent_hash)


def checkRunFile(project, filename, most_recent_hash):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	f = index_nodes.get('filename', project+filename)
	f = f[0]

	if most_recent_hash == f["most_recent_hash"]:
		return False
	else:
		return True

def createFilesAuthorsInIndex(project, all_files):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")
	
	git_repo = devknowledge.settings.VERSION_CONTROL_REPOS+project

	for file in all_files:
		f = index_nodes.get("filename", project+file)
		if len(f) == 0:
			#don't set the most_recent_hash here because we still have to process the file
			f, = gdb.create({"filename": project+file})
			index_nodes.add("filename", project+file, f)

	#https://www.kernel.org/pub/software/scm/git/docs/git-log.html
	#get all authors who ever worked on the project
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" log --format='%aN <%aE>' | sort -u"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		found = re.search(r'(.*?)\s<(.*?)>', line) #Committer name and email address
		if found:
			author = found.group(1).strip().decode("utf-8")
			email = found.group(2).lower()
			a = index_nodes.get("author", author)
			if len(a) == 0:
				#print "Creating author: ", author, email
				a, = gdb.create({"author": author, "knowledge_last_update": str(datetime.now()), "email": email})
				index_nodes.add("author", author, a)
		else:
			print "Error: unable to find author/email for: ", line


def clearStaleEntries(project, filename, most_recent_hash):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	#print "Starting to clear stale entries."

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#this should already exist, no need to check for it
	f = index_nodes.get('filename', project+filename)
	#print "Checking file: ", filename
	if len(f) == 1:
		f = f[0]
		#print "Found file using index: ", f
		#Delete all edges that do not have a processed property
		q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE NOT HAS(r.processed) DELETE r;"
		#print q
		query = neo4j.CypherQuery(gdb, q)
		query.execute()
		#Delete all processed properties
		q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE HAS(r.processed) REMOVE r.processed;"
		#print q
		query = neo4j.CypherQuery(gdb, q)
		query.execute()
		#set new most_recent_hash value to new updated value
		q = "START f=node("+str(f._id)+") SET f.most_recent_hash='"+str(most_recent_hash)+"';"
		query = neo4j.CypherQuery(gdb, q)
		query.execute()
	else:
		print "Something went wrong, can't find the file: ", project+filename

def updateExistingDatabase(entry, previous_committers, old_line, previous_hash):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#grab filename and author from index - they should already exist based on createFilesAuthorsInIndex()
	f = index_nodes.get('filename', entry.project+entry.filename)
	f = f[0]
	a = index_nodes.get("author", entry.author)
	a = a[0]

	#update existing author node's last knowledge update property
	#print "Updating existing author node's knowledge timestamp, author:", entry.author
	q = "START a=node("+str(a._id)+") SET a.knowledge_last_update='"+str(datetime.now())+"';"
	query = neo4j.CypherQuery(gdb, q)
	query.execute()

	#check if current hash and line number are already set, if so, we didn't insert anything so we can exit immediately
	q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(entry.line_number)+" AND r.hash='"+entry.hash+"' RETURN COUNT(r);"
	#print q
	result = neo4j.CypherQuery(gdb, q)
	for record in result.stream():
		if record[0] == 1:
			q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(entry.line_number)+" SET r.processed=True;"
			#print q
			query = neo4j.CypherQuery(gdb, q)
			query.execute()
			
			return False

	if previous_hash != "":
		q = "START a=node(*), f=node("+str(f._id)+") MATCH a-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" AND r.hash='"+previous_hash+"' RETURN COUNT(r);"
		print q
		result = neo4j.CypherQuery(gdb, q)
		for record in result.stream():
			print record
			if record[0] == 1:
				#delete all old relationships for old author entries
				print previous_committers
				for committer in previous_committers:
					#print "Deleting old relationshp for committer: ", committer
					q = "START f=node("+str(f._id)+") MATCH a-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" AND a.author='"+committer+"' DELETE r;"
					print q
					query = neo4j.CypherQuery(gdb, q)
					query.execute()
			
				#print "Creating new relationship for ", entry.author, entry.filename, entry.line_number, entry.hash
				rel, = gdb.create((a, "knowledge", f, {"line_number": entry.line_number, "hash": entry.hash, "epoch": entry.epoch}))
				
				if old_line != entry.line_number:
					#set all old line numbers to the new line number
					q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" SET r.line_number="+str(entry.line_number)+";"
					#print q
					query = neo4j.CypherQuery(gdb, q)
					query.execute()
					
				q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(entry.line_number)+" SET r.processed=True;"
				#print q
				query = neo4j.CypherQuery(gdb, q)
				query.execute()
			
				return False
				
	print "Creating new relationship for ", entry.author, entry.filename, entry.line_number, entry.hash
	rel, = gdb.create((a, "knowledge", f, {"line_number": entry.line_number, "hash": entry.hash, "epoch": entry.epoch, "processed": True}))
				
	return True
				

				

	#if old_found and not new_found and old_line != entry.line_number:
		#new_found = True

	##[0]<-0
	##[... 0 0]<-0
	#if new_found:
		##at this point we're good, all the old history and new changes have been merged
		##set our update property for all nodes to mark them as "processed"
		#q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" SET r.processed=True;"
		##print q
		#query = neo4j.CypherQuery(gdb, q)
		#query.execute()
		##[... 0 0]<|-0
		#if old_line != entry.line_number:
			##set all old line numbers to the new line number
			#q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" SET r.line_number="+str(entry.line_number)+";"
			##print q
			#query = neo4j.CypherQuery(gdb, q)
			#query.execute()
		#return False #stop running for this line, continue to next line

	#if not new_found:
		##[]<-0
		##print "Creating new relationship for ", entry.author, entry.filename, entry.line_number, entry.hash
		#rel, = gdb.create((a, "knowledge", f, {"line_number": entry.line_number, "hash": entry.hash, "epoch": entry.epoch, "processed": True}))
		##end[]<-0
		#if previous_hash == "":
			#q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(entry.line_number)+" SET r.processed=True;"
			##print q
			#query = neo4j.CypherQuery(gdb, q)
			#query.execute()
			#return False #stop running for this line, continue to next line

	##[0 x]<-0
	#if old_found:
		##print "Found matchup for file: ", entry.filename
		##delete all old relationships for old author entries
		#for committer in previous_committers:
			##print "Deleting old relationshp for committer: ", committer
			#q = "START f=node("+str(f._id)+") MATCH a-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" AND a.author='"+committer+"' DELETE r;"
			##print q
			#query = neo4j.CypherQuery(gdb, q)
			#query.execute()
		##set all old line numbers to the new line number
		#q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(old_line)+" SET r.line_number="+str(entry.line_number)+";"
		##print q
		#query = neo4j.CypherQuery(gdb, q)
		#query.execute()
		##at this point we're good, all the old history and new changes have been merged
		##set our update property for all nodes to mark them as "processed"
		#q = "START f=node("+str(f._id)+") MATCH ()-[r:knowledge]-f WHERE r.line_number="+str(entry.line_number)+" SET r.processed=True;"
		##print q
		#query = neo4j.CypherQuery(gdb, q)
		#query.execute()
		##print "Finished with matchup."
		#return False

	#return True

def pruneDatabaseStaleFiles(all_files, project):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#TODO: set processed boolean on all files, then delete later, this way we don't have to have a massive select statement
	q = "START f=node(*) WHERE HAS(f.filename) RETURN f;"
	#print q
	result = neo4j.CypherQuery(gdb, q)
	for record in result.stream():
		file = record.f["filename"].replace(project, "", 1) #replace first occurence
		if file not in all_files:
			#print "Deleting file ", record.f["filename"], " in database."
			#delete all edges first as this is a requirement before we can delete the node
			record.f.isolate() #delete all relationships connected to this node, both incoming and outgoing
			#clear out index
			index_nodes.remove("filename", record.f["filename"], record.f)
			#delete the file node
			record.f.delete()

def pruneDatabaseStaleAuthors():
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#find all author nodes that do not have any inbound/outbound relationships
	q = "START a=node(*) WHERE NOT ((a)--()) AND HAS(a.author) RETURN a;"
	result = neo4j.CypherQuery(gdb, q)
	for record in result.stream():
		#clear out the index
		index_nodes.remove("author", record.a["author"], record.a)
	#finally delete them
	q = "START a=node(*) WHERE NOT ((a)--()) AND HAS(a.author) DELETE a;"
	query = neo4j.CypherQuery(gdb, q)
	query.execute()

def pruneAllOtherNodes():
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#TODO: probably change this to use labels later
	#delete all nodes that do not have the properties we specified
	q = "START n=node(*) WHERE NOT HAS(n.filename) AND NOT HAS(n.author) AND NOT HAS(n.subject) DELETE n;"
	query = neo4j.CypherQuery(gdb, q)
	query.execute()
