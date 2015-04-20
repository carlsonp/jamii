import re, sys, os

sys.path.append("../")
import devknowledge.settings

from DatabaseThread import dependenciesDatabaseThread, FileDependencyEntry

from py2neo import neo4j


def parseFileDependencies(manager, project, filename, c_files, update_existing):

	if update_existing:
		#clear out all previous "depends" relationships so we can re-run
		clearDependencyRelsForFile(filename, project)

	project_dir = os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, project)
	#this little replace is necessary because os.path.join doesn't like stuff with slashes at the front
	fromFile = os.path.join(project_dir, filename.replace("/", "", 1))
	#print "From file: ", fromFile
	with open(fromFile) as f:
		content = f.readlines()
		line_counter = 1
		directory = os.path.dirname(fromFile)
		#print "Directory: ", directory
		for line in content:
			found = re.search(r'''(?<=#include [<|"|']).*(?=["|'|>])''', line) #single/double quoted, or bracketed filename
			if found:
				#print "Found match on line: ", line
				#we don't really know where the file is so we check all C/C++ files
				for c_file in c_files:
					if c_file.endswith(found.group()):
						fFile = fromFile.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
						c_file = c_file.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
						#print "From file: ", fFile, " To File: ", c_file
						entry = FileDependencyEntry(project, fFile, c_file, line_counter)
						if update_existing:
							saveEntryViaREST(entry)
						else:
							manager.addToQueue(entry)
						break

			line_counter += 1

	f.close()


def saveEntryViaREST(entry):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#create file node if it doesn't exist
	to_f = index_nodes.get('filename', entry.project+entry.toFilename)
	if len(to_f) == 0:
		#create file
		to_f, gdb.create({"filename": entry.project+entry.toFilename})
		index_nodes.add("filename", entry.project+entry.toFilename, to_f)
	else:
		to_f = to_f[0]

	#create file node if it doesn't exist
	from_f = index_nodes.get('filename', entry.project+entry.fromFilename)
	if len(from_f) == 0:
		#create file
		from_f, gdb.create({"filename": entry.project+entry.fromFilename})
		index_nodes.add("filename", entry.project+entry.fromFilename, from_f)
	else:
		from_f = from_f[0]

	#create relationship
	rel, = gdb.create((from_f, "depends", to_f, {"line_number": entry.line_number}))


def clearDependencyRelsForFile(filename, project):
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#grab filename from index
	f = index_nodes.get('filename', project+filename)
	f = f[0]

	q = "START f=node("+str(f._id)+") MATCH f-[r:depends]-() DELETE r;"
	query = neo4j.CypherQuery(gdb, q)
	query.execute()
