import math, socket, time

from django.conf import settings

from py2neo import neo4j

from sourcecodeknowledge.models import DevKnowledge

def calculateExpertise(filename, authors, line_start, line_end):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None
	
	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	expertise = {}
	for author in authors:
		expertise[author] = 0;

	devknowledge = {}
	knowledge_model = []

	f = index_nodes.get('filename', filename)
	f = f[0]

	if f:
		num_developers = 0
		#http://docs.neo4j.org/refcard/2.0/
		# We need to return ALL developers here because we need the number of total developers for the calculation
		q = "START f=node("+str(f._id)+") MATCH f<-[rel:knowledge]-a WHERE rel.line_number >= "+str(line_start)+" AND rel.line_number <= "+str(line_end)+" return rel, a;"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			#print "Author: ", r.a['author']
			a = index_nodes.get("author", r.a['email'])
			a = a[0]
			if a:
				days = (((time.mktime(time.gmtime()) - float(r.rel['epoch'])) / 60) / 60) / 24
				#print "Days: " + str(days)
				expertise[r.a['author']] = expertise[r.a['author']] + math.pow((1 - settings.EXPONENTIAL_DECAY), days)
				#print "Expertise: ", expertise[r.a['author']]
			num_developers += 1
		#print "Number of developers: ", num_developers

		total = 0
		for author in authors:
			total = total + expertise[author]/num_developers
		#print "total: ", total
		for author in authors:
			#save expertise knowledge as percentage
			devknowledge[author] = round(((expertise[author]/num_developers)/total)*100, 2)

		#only return top 10
		for w in sorted(devknowledge, key=devknowledge.get, reverse=True)[:10]:
			if devknowledge[w] > 1: #only return developers who have one percent or greater expertise
				knowledge_model.append(DevKnowledge(name=w, knowledge=devknowledge[w]))


	return knowledge_model
