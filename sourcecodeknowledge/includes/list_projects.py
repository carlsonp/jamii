
import os, subprocess, socket

from django.conf import settings

from py2neo import neo4j

def listProjects():
	# only folders, no files
	folders = [d for d in os.listdir(settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(settings.VERSION_CONTROL_REPOS, d))]
	folders.sort() # make it in alphabetical order
	return folders


def listRepoFilesAndFolders(project, subfolder):
	files = []
	folders = []
	items = os.listdir(settings.VERSION_CONTROL_REPOS+project+"/"+subfolder)
	for f in items:
		item = settings.VERSION_CONTROL_REPOS+project+"/"+subfolder+"/"+f
		if os.path.isfile(item):
			if not f.startswith("."):
				files.append(f)
		elif os.path.isdir(item):
			if not f.startswith("."):
				folders.append(f)

	folders.sort() # make it in alphabetical order
	files.sort() # make it in alphabetical order

	return folders, files


# returns a list of unique authors who have touched this file and who developer knowledge can be calculated
def returnUniqueAuthors(project, filename):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	try:
		f = index_nodes.get('filename', project+"/"+filename)
		f = f[0]
	except:
		#we don't have data on this
		return None

	authors = []

	if f:
		#http://docs.neo4j.org/refcard/2.0/
		q = "START f=node("+str(f._id)+") MATCH f<-[r:knowledge]-(a) RETURN DISTINCT a ORDER BY a.author;"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			authors.append(r.a['author'])

	return authors
