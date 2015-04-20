import socket

from django.conf import settings

from py2neo import neo4j

from sourcecodeknowledge.models import Developer

def findDevelopers(project, query):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None
	
	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	developers_model = []

	#http://docs.neo4j.org/refcard/2.0/
	#(?i) means do a case-insensitive search
	q = "start a=node(*) where has(a.author) and (a.author =~ '(?i).*"+query+".*' or a.email =~ '(?i).*"+query+".*') return a limit 20;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		developers_model.append(Developer(name=r.a['author'], email=r.a['email']))

	return developers_model
