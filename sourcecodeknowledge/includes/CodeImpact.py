import math, socket, time

from django.conf import settings

from py2neo import neo4j

from sourcecodeknowledge.models import CodeImpact

def returnCodeImpact(project):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None
	
	#for the code impact graph
	code_impact = []
	
	q = "START a=node(*) WHERE HAS(a.hash) RETURN a ORDER BY a.date LIMIT 50;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		converted_date = time.strftime('%Y/%m/%d', time.localtime(int(r.a['date'])))
		code_impact.append(CodeImpact(commit_hash=r.a['hash'], date=r.a['date'], datereadable=converted_date, delta_impact=r.a['total_delta']))

	return code_impact


def filteredCodeImpact(project, limit, epochtime, relativetoemail):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#for the filtered table listing
	code_impact = []

	if relativetoemail is None or relativetoemail == "":
		q = "START a=node(*) WHERE HAS(a.hash) AND a.date >= "+epochtime+" RETURN a ORDER BY a.total_delta DESC LIMIT "+limit+";"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			converted_date = time.strftime('%Y/%m/%d', time.localtime(int(r.a['date'])))
			code_impact.append(CodeImpact(commit_hash=r.a['hash'], date=r.a['date'], datereadable=converted_date, delta_impact=round(r.a['total_delta'], 2), logmsg=r.a['logmsg'], author_developer=r.a['author_developer'], author_email=r.a['author_email']))
	else:
		dev = index_nodes.get("author", relativetoemail)[0]
		#TODO: check to make sure this query doesn't take too long, we might need to add some sort of limit on it
		#This is the more simplified version.  A better approach might be to total the individual impact values for each hash since
		#this is a more personalized recommendation
		q = "START a=node(*), c=node("+str(dev._id)+") MATCH a-[:impact]->b<-[:expertise]-c WHERE HAS(a.hash) AND a.date >= "+epochtime+" RETURN DISTINCT a ORDER BY a.total_delta DESC LIMIT "+limit+";"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			converted_date = time.strftime('%Y/%m/%d', time.localtime(int(r.a['date'])))
			code_impact.append(CodeImpact(commit_hash=r.a['hash'], date=r.a['date'], datereadable=converted_date, delta_impact=round(r.a['total_delta'], 2), logmsg=r.a['logmsg'], author_developer=r.a['author_developer'], author_email=r.a['author_email']))


	return code_impact
