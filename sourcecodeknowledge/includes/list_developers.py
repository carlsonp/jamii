import socket

from django.conf import settings

from py2neo import neo4j

from sourcecodeknowledge.models import Developer


# returns a list of all developers in database
def returnDevelopers(project, letter, page):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	developers = []

	#TODO: only return based on project label (this should be a little faster)
	#http://docs.neo4j.org/refcard/2.0/
	#The match on file_score only returns developers who have contributed code so
	#we don't overpopulate the communication suggestions section with people who only posted to the mailing list.
	if letter.isalpha() and letter != "unknown":
		q = "START n=node(*) match n-[:file_score]->() WHERE HAS(n.author) AND n.author =~ '^["+letter.upper()+"|"+letter.lower()+"].*' RETURN DISTINCT n ORDER BY n.author SKIP "+str((page-1)*50)+" LIMIT 50;"
	else:
		#unknown name selected
		q = "START n=node(*) match n-[:file_score]->() WHERE HAS(n.author) AND (n.author =~ '^[^A-Za-z].*' OR n.author = '') RETURN DISTINCT n ORDER BY n.author SKIP "+str((page-1)*50)+" LIMIT 50;"

	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		developers.append(Developer(name=r.n['author'], email=r.n['email']))

	return developers

# returns a list of developers based on the search term
def searchDevelopers(project, searchterm):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	developers = []

	#TODO: check for injection attack here?
	#Use parameters but py2neo doesn't support parameters?...
	searchterm = "(?i).*" + searchterm + ".*" #(?i) means case insensitive

	#TODO: only return based on project label (this should be a little faster)
	#http://docs.neo4j.org/refcard/2.0/
	q = "START n=node(*) WHERE HAS(n.author) AND (n.author =~ '"+searchterm+"' OR n.email =~ '"+searchterm+"') RETURN n ORDER BY n.author LIMIT 100;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		developers.append(Developer(name=r.n['author'], email=r.n['email']))

	return developers
