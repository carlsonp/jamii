import sys, os, re, subprocess, getopt, shutil, math, Queue
from subprocess import STDOUT
sys.path.append("../")
import devknowledge.settings
import Util

from decimal import Decimal

#IMPORTANT:
#The python embedded bindings for Neo4j use JPype.  Based on the Neo4j mailing list thread
#entitled [Neo4j] Java segfaults using paste and Python bindings, the Neo4j Python binding
#needs to be single threaded.  Thus, waiting to import until the thread is ready and running.
from neo4j import GraphDatabase


class FilenameEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["project", "filename", "include_filename"]
	def __init__(self, project, filename, include_filename):
		self.project = project
		self.filename = filename
		self.include_filename = include_filename

class FunctionDefCallEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["project", "filename", "function_name", "ending_filename"]
	def __init__(self, project, filename, function_name, ending_filename):
		self.project = project
		self.filename = filename
		self.function_name = function_name
		self.ending_filename = ending_filename

def main(argv):
	#Parse commandline arguments
	#http://www.tutorialspoint.com/python/python_command_line_arguments.htm
	start_hash = None
	try:
		opts, args = getopt.getopt(argv,"h:s:")
	except getopt.GetoptError:
		print "-s <hash>"
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print "-s <hash>"
		elif opt == "-s":
			start_hash = arg

	projects = [d for d in os.listdir(devknowledge.settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, d))]
	
	try:
		#print "Connecting to database: ",devknowledge.settings.NEO4J_DATABASE
		gdb = GraphDatabase(devknowledge.settings.NEO4J_DATABASE)
	except Exception, e:
		print "Error: ",e.message()
		
	#create indexes (we only need to do this once, thus why it's outside the main loop)
	with gdb.transaction:
		#create indexes if they don't exist
		if (not gdb.node.indexes.exists("index_nodes")):
			index_nodes = gdb.node.indexes.create("index_nodes")
			#print "Created index_nodes"
	
	#iterate through all projects
	for project in projects:
		if project in devknowledge.settings.PROJECT_FOLDERS:
			git_repo = devknowledge.settings.VERSION_CONTROL_REPOS+project
			Util.checkoutHash(git_repo, Util.returnMasterHash(git_repo))
			#from oldest commit to newest
			hash_commits, hash_dates = returnHashCommits(git_repo, start_hash)
			number_to_process = len(hash_commits)
			print "Number of commits to process: ", number_to_process
			processed_commits = 0
			for i, commit in enumerate(hash_commits):
				print "Running on hash: ", commit
				#check if file exists in our temp location
				if os.path.exists("/tmp/devknowledge/"+commit+".txt"):
					changed_files = []
					if commit != start_hash:
						#only process files that have changed
						changed_files = Util.returnListCPPFilesChanged(git_repo, commit)

					if len(changed_files) != 0:
						clearEdgesForChangedFiles(project, gdb, changed_files)
						
					items = []
					#print "Opening saved data for commit: ", commit
					fo = open("/tmp/devknowledge/"+commit+".txt", "r")
					for line in fo:
						chunk = line.split(",")
						if chunk[0] == "function":
							entry = FunctionDefCallEntry(chunk[1], chunk[2], chunk[3], chunk[4].rstrip("\n"))
							items.append(entry)
						elif chunk[0] == "file":
							if chunk[3] == "None\n":
								entry = FilenameEntry(chunk[1], chunk[2], None)
							else:
								entry = FilenameEntry(chunk[1], chunk[2], chunk[3].rstrip("\n"))
							items.append(entry)
					fo.close()
					saveQueueToDatabase(gdb, items)
					
					#In cases where we have deleted the "has" relationship to a function, the "calls" are now out of date.
					#However, these files may not have been changed so we may not actually hit them in the queue,
					#therefore, we do some cleanup to remove these edges.
					#*The IDEAL case is to not run clang on *only* these diffed files but on the entire sourcecode because
					#things like #defines and others might have sweeping changes on the entire technical graph.  However, this takes
					#too long so this is more of an approximation.*
					cleanupPrunedCalls(project, gdb)

					calculateNewPageRank(project, gdb)
					
					#calculate delta impact value
					#don't run it on the first commit because we have no baseline to compare it against
					if processed_commits != 0:
						delta_impact = calculateSavePageRankDeltaDifference(project, gdb, commit, hash_dates[i], git_repo)
					else:
						delta_impact = 0
				else:
					#no changes have been made to C++ files, therefore the delta impact change is zero
					delta_impact = 0
					
				print "Delta impact: ", delta_impact
				
				processed_commits += 1
				print "Percent done: %.2f %%" % float(float(processed_commits)/float(number_to_process) * 100)
			#deleteStaleFileNodes(project, gdb)
			deleteCachedProperties(project, gdb)
	if gdb:
		gdb.shutdown()
	print "Done.  Exiting."
	
def cleanupPrunedCalls(project, gdb):
	with gdb.transaction:
		#TODO: when upgrading to newer Neo4j 2.X version, DELETE is now REMOVE
		gdb.query("START a=node(*) MATCH b-[r:calls]->a WHERE HAS(a.function) AND NOT(()-[:has]->a) DELETE r;")
		#to check to make sure this worked:
		#start a=node(*) match ()-[:calls]->a<-[:has]-() where has(a.function) return count(distinct a);
		#vs.
		#start a=node(*) where has(a.function) return count(a);
		#The function node still exists because it's tied via "impacts" to a hash node, it's just not tied
		#now to any files.

def deleteCachedProperties(project, gdb):
	#TODO: make this work for more than one project
	with gdb.transaction:
		#TODO: when upgrading to newer Neo4j 2.X version, DELETE is now REMOVE
		gdb.query("START a=node(*) where has(a.previouspagerank) DELETE a.previouspagerank;")
	
def calculateSavePageRankDeltaDifference(project, gdb, commit, commit_date, git_repo):
	#TODO: make this work for more than one project
	with gdb.transaction:
		#grab commit details
		author_developer, author_email, logmsg = returnCommitDetails(git_repo, commit)

		index_nodes = gdb.node.indexes.get("index_nodes")
		#create hash node
		#date is in epoch format
		f = gdb.node(hash=commit, date=int(commit_date), author_developer=author_developer, author_email=author_email, logmsg=logmsg)
		index_nodes['hash'][commit] = f
		
		delta_impact = 0
		#find all nodes that have a delta change
		#Neo4j doesn't do floating point equality very well so we have to fudge it a little in the cypher query...
		for node in gdb.query("start c=node(*) where has(c.pagerank) and has(c.previouspagerank) and abs(c.pagerank-c.previouspagerank)>0.000001 with abs(c.pagerank-c.previouspagerank) as delta, c return delta, c;"):
			#make a relationship link between the commit and the node
			#convert from jpype java double to python float
			#https://github.com/neo4j-contrib/python-embedded/blob/master/src/main/python/neo4j/_backend.py
			delta = node['delta'].doubleValue()
			rel = f.relationships.create("impact", node['c'], impactvalue=delta)
			delta_impact = delta_impact + delta
			
		#save total delta chage in new hash node
		f['total_delta'] = delta_impact
		#if we're saving 0 as the delta change, this means the commit had changes to C++ files but it didn't actually change the network structure
		
	return delta_impact
	
def calculateNewPageRank(project, gdb):
	#This iterates through all nodes and calculates the page rank
	#make all previouspagerank variables set to the current page rank
	#we're going to be overwriting the current page rank here shortly
	#TODO: make this work for more than one project
	with gdb.transaction:
		##add in test data
		#http://www.cs.princeton.edu/~chazelle/courses/BIB/pagerank.htm
		#a = gdb.node(filename="A",pagerank=0,previouspagerank=0)
		#b = gdb.node(filename="B",pagerank=0,previouspagerank=0)
		#c = gdb.node(filename="C",pagerank=0,previouspagerank=0)
		#d = gdb.node(filename="D",pagerank=0,previouspagerank=0)
		#a.relationships.create("include", b)
		#b.relationships.create("has", c)
		#a.relationships.create("calls", c)
		#c.relationships.create("include", a)
		#d.relationships.create("include", c)
		#pagerank output should be:
		#A: 1.49
		#B: 0.78
		#C: 1.58
		#D: 0.15
		
		gdb.query("START a=node(*) WHERE HAS(a.pagerank) AND HAS(a.previouspagerank) SET a.previouspagerank = a.pagerank;")
		
		#cache and save all outgoing link counts (this speeds up calculation of page rank later since we don't have to do a COUNT looping through nodes
		gdb.query("start a=node(*) MATCH a-[:has|include|calls]->b with count(b) as b, a set a.outgoinglinks = b;")
		
	d = 0.85
	
	continue_running = True
	counter = 0
	while continue_running:
		with gdb.transaction:
			continue_running = False
			#run through at least 2 runs of all nodes before starting to prune off ones that haven't changed
			if counter < 2:
				query = "START a=node(*) WHERE HAS(a.pagerank) AND HAS(a.previouspagerank) return a;"
			else:
				query = "START a=node(*) WHERE HAS(a.pagerank) AND HAS(a.previouspagerank) and NOT HAS(a.finished) return a;"
			for node in gdb.query(query)['a']:
				#print "Calculating page rank for node: ", node
				old_pagerank = float(node['pagerank'])
				#for all inbound links into the node
				main_pr_calc = 0
				for startnode in gdb.query("START a=node("+str(node.id)+") MATCH a<-[:has|include|calls]-b return b;")['b']:
					#make sure to only use the relationships that qualify, since later we'll be adding in other types like
					#the links from files/functions to hash commit nodes, we don't want to include those
					if startnode['outgoinglinks'] is not None:
						main_pr_calc = main_pr_calc + (float(startnode['pagerank'])/startnode['outgoinglinks'])

				page_rank_calc = (1-d)+d*(main_pr_calc)
				
				#print "Old: ", old_pagerank
				#print "New: ", page_rank_calc
				if abs(page_rank_calc-old_pagerank) > 0.000001:
					continue_running = True
					del node['finished']
				else:
					#mark it so we don't have to go through the computation next cycle
					node['finished'] = "True"
				
				node['pagerank'] = float(page_rank_calc)
				
		counter = counter + 1
	#cleanup and remove all "finished" properties
	with gdb.transaction:
		#TODO: when upgrading to newer Neo4j 2.X version, DELETE is now REMOVE
		gdb.query("START a=node(*) WHERE HAS(a.finished) DELETE a.finished;")
		#remove "outgoinglinks" properties, this will be recalculated next round
		gdb.query("START a=node(*) WHERE HAS(a.outgoinglinks) DELETE a.outgoinglinks;")


#def deleteStaleFileNodes(project, gdb):
	#with gdb.transaction:
		#index_nodes = gdb.node.indexes.get("index_nodes")
		##delete all function definition nodes that have no inbound connections
		#for node in gdb.query("start a=node(*) match a where has(a.function) and not a<-[:has]-() return a;")['a']:
			#item = index_nodes['function'][node['filefunction']]
			#if len(item) != 0:
				#del item #delete index
			##delete all inbound and outbound edges from the function
			#for edge in node.relationships:
				#edge.delete()
			#item.delete() #delete node
	#with gdb.transaction:
		#index_nodes = gdb.node.indexes.get("index_nodes")
		##check files that may no longer exist
		#for q in gdb.query("start a=node(*) where has(a.filename) return a;"):
			#for node in q.values():
				#print "Checking file: ", devknowledge.settings.VERSION_CONTROL_REPOS+node['filename']
				#if not os.path.isfile(devknowledge.settings.VERSION_CONTROL_REPOS+node['filename']):
					##delete from the index
					#f = index_nodes['filename'][node['filename']]
					#if len(f) != 0:
						#del f
					##delete function definition nodes
					#for edge in node.has.outgoing:
						##delete from index
						#g = index_nodes['function'][node['filename']+edge.end['function']]
						#if len(g) != 0:
							#del g
						#edge.end.delete()
					##delete all inbound and outbound edges
					#for edge in node.relationships:
						#edge.delete()
					##delete the node
					#node.delete()


def clearEdgesForChangedFiles(project, gdb, files_changed):
	with gdb.transaction:
		index_nodes = gdb.node.indexes.get("index_nodes")
		#this clears away all "calls", "include", and "has" edge relationships
		#so the new ones can be populated
		for changed in files_changed:
			changed = changed.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
			f = index_nodes['filename'][project+changed]
			if len(f) != 0:
				f = f[0]
				#print "Clearing away stale edges."
				for rel in f.calls.outgoing:
					rel.delete()
				for rel in f.include.outgoing:
					rel.delete()
				for rel in f.has.outgoing:
					rel.delete()

def saveQueueToDatabase(gdb, items):
	while len(items) != 0:
		#Try to perform insertions in large blocks, lots of tiny single insertions take a LONG time waiting for database lock
		#TODO: there's something wrong with the interplay between Neo4j and Clang
		#Neo4j crashes for some reason if you try to run too many in one transaction, but if you remove
		#the creation of the clang index, it works just fine with larger blocks (10,000).
		limit = 10000
		if len(items) >= limit:
			num_process = limit
		elif len(items) < limit:
			num_process = len(items)

		with gdb.transaction:
			#print "Grabbing index."
			index_nodes = gdb.node.indexes.get("index_nodes")
			#print "Queue size: ", len(items)
			this_chunk = items[:limit]
			for i in range(0, num_process):
				item = this_chunk[i]

				#create file node for either entry type
				if isinstance(item, FilenameEntry) or isinstance(item, FunctionDefCallEntry):
					#print item.project, " - ", item.filename
					#create file node if it doesn't exist
					#print "Checking index: ", item.project+item.filename
					f = index_nodes['filename'][item.project+item.filename]
					if len(f) == 0:
						#print "Starting creating node: ", item.filename
						f = gdb.node(filename=item.project+item.filename,pagerank=0,previouspagerank=0)
						index_nodes['filename'][item.project+item.filename] = f
						#print "Creating new file node: ", item.project+item.filename
					else:
						#print "Attempting to grab existing filename."
						f = f[0]
						#print "Using existing file: ", f

				#parse the possible include
				if isinstance(item, FilenameEntry) and item.include_filename is not None:
					g = index_nodes['filename'][item.project+item.include_filename]
					if len(g) == 0:
						#print "Starting creating node: ", item.include_filename
						g = gdb.node(filename=item.project+item.include_filename,pagerank=0,previouspagerank=0)
						index_nodes['filename'][item.project+item.include_filename] = g
					else:
						g = g[0]
					#check to see if include edge already exists
					exists = False
					for rel in f.include.outgoing:
						if rel.end == g:
							exists = True
							break
					if not exists:
						#print "Creating new include relationship."
						rel = f.relationships.create("include", g)

				if isinstance(item, FunctionDefCallEntry):
					#create function node if it doesn't exist
					#we need to use the filename in the unique lookup because functions might have the same name
					g = index_nodes['function'][item.project+item.ending_filename+item.function_name]
					if len(g) == 1:
						g = g[0]
					else:
						g = gdb.node(function=item.function_name,pagerank=0,previouspagerank=0)
						index_nodes['function'][item.project+item.ending_filename+item.function_name] = g
						#print "Finished creating function node: ", item.project + " " + item.ending_filename + " " + item.function_name
					#check to see if "calls" relationship already exists
					exists = False
					for rel in f.calls.outgoing:
						if rel.end == g:
							exists = True
							break
					if not exists:
						#print "Creating new calls relationship."
						rel = f.relationships.create("calls", g)
					#look for the function definition file
					e = index_nodes['filename'][item.project+item.ending_filename]
					if len(e) == 0:
						#print "Creating new ending file node: ", item.ending_filename
						e = gdb.node(filename=item.project+item.ending_filename,pagerank=0,previouspagerank=0)
						index_nodes['filename'][item.project+item.ending_filename] = e
					else:
						#print "Using existing ending file node."
						e = e[0]
					#check to see if "has" relationship already exists
					exists = False
					for rel in e.has.outgoing:
						if rel.end == g:
							exists = True
							break
					if not exists:
						#print "Creating has relationship."
						rel = e.relationships.create("has", g)

		items = items[limit:]

def returnHashCommits(git_repo, start_hash):
	hash_commits = []
	hash_dates = []

	found = False
	#provides commits from most recent to oldest
	#%H is the commit hash
	#%ct is commiter date in UNIX timestamp
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" log --pretty=format:'%H %ct'"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		line = line.rstrip("\n")
		split = line.split(" ")
		if start_hash == split[0]:
			hash_commits.append(split[0])
			hash_dates.append(split[1])
			found = True
		if not found:
			hash_commits.append(split[0])
			hash_dates.append(split[1])
	hash_commits.reverse()
	hash_dates.reverse()
	return hash_commits, hash_dates

def returnCommitDetails(git_repo, commit):
	#grab commit details given a hash
	#%an - author name
	#%ae - author email
	#%B - raw body (commit message)
	logmsg = ""
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" show -s "+commit+" --pretty=format:'%an%n%ae%n%B'"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for i, line in enumerate(p.stdout.readlines()):
		#use UTF-8 encoding for text to ensure we can properly insert it into Neo4J
		if i == 0:
			line = line.rstrip("\n")
			author_developer = unicode(line, "utf-8")
		elif i == 1:
			line = line.rstrip("\n")
			author_email = unicode(line, "utf-8")
		else:
			logmsg += unicode(line, "utf-8")
			
	return author_developer, author_email, logmsg

if __name__ == "__main__":
   main(sys.argv[1:])
