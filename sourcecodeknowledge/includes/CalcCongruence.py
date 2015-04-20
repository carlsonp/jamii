import math, socket, time, re, hashlib

from django.conf import settings

from py2neo import neo4j

from sourcecodeknowledge.models import Congruence, CongruencePercentages

def calculateCongruence(project, developer_email):
	#congruence, congruence_JSON_string = calculateUIC(project, developer_email)
	#return congruence, congruence_JSON_string
	
	name, congruence_array = calculatePercentageCongruence(project, developer_email)
	return name, congruence_array

def calculatePercentageCongruence(project, developer_email):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")
	a = index_nodes.get('author', developer_email)
	if a:
		a = a[0]
		name = a['author']
	else:
		return None
	
	congruence_array = []
		
	q = "start a=node("+str(a._id)+") match a-[r:file_score]->b optional match a-[t:interpersonal_score]->b " + \
	"with case when t.percentage is NULL then 0 else t.percentage end as t, r, b with (t-r.percentage) as diff, b, t, r " + \
	"return diff, b.email, b.author, t, r.percentage ORDER BY diff limit 5;"
	
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		if (r['r.percentage'] and r['diff']):
			difference = round(r['diff'], 4)
			if difference >= 0:
				difference = 0
			else:
				difference = difference * -1
			congruence_model = CongruencePercentages(file_percentage=round(r['r.percentage'], 4), comm_percentage=round(r['t'], 4), difference_score=difference, name=r['b.author'], email=r['b.email'], email_hash=hashlib.md5(r['b.email']).hexdigest().lower())
			congruence_array.append(congruence_model)
		
	return name, congruence_array

def calculateUIC(project, developer_email):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	#unweighted individual congruence

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")
	a = index_nodes.get('author', developer_email)
	if a:
		a = a[0]
	else:
		return Congruence(UIC=0, name="Unable to find developer")

	q = "START a=node("+str(a._id)+") MATCH (a)-[:knowledge]->(x) WITH DISTINCT x, a " + \
		"MATCH (x)-[:depends]-(y) " + \
		"WITH DISTINCT y, a " + \
		"MATCH (y)<-[:knowledge]-(end) " + \
		"WITH DISTINCT end, a " + \
		"MATCH (end)-[:communication]-(g)-[:communication]-(a) " + \
		"WITH DISTINCT end " + \
		"RETURN COUNT(end);"
	result = neo4j.CypherQuery(gdb, q)
	numerator = 0
	for r in result.stream():
		numerator = r[0]

	q = "START a=node("+str(a._id)+") MATCH (a)-[:knowledge]->(x) WITH DISTINCT x " + \
		"MATCH (x)-[:depends]-(y) " + \
		"WITH DISTINCT y " + \
		"MATCH (y)<-[:knowledge]-(end) " + \
		"WITH DISTINCT end " + \
		"RETURN COUNT(end);"
	result = neo4j.CypherQuery(gdb, q)
	denominator = 0
	for r in result.stream():
		denominator = r[0]

	if numerator == 0 or denominator == 0:
		uic = 0
	else:
		uic = round(float(numerator)/float(denominator), 4) * 100

	congruence = Congruence(UIC=uic, name=a['author'])

	nodes = []
	links = []

	nodes.append((a['author'], 1))
	
	#identify the developers who work on dependent files but who have NOT communicated
	q = "START a=node("+str(a._id)+") MATCH (a)-[:knowledge]->(x) WITH DISTINCT a, x " + \
	"MATCH (x)-[:depends]-(y) WITH DISTINCT a, x, y " + \
	"MATCH (y)<-[:knowledge]-(end) WITH DISTINCT a, x, y, end " + \
	"MATCH end WHERE NOT (end)-[:communication]-()-[:communication]-(a) WITH DISTINCT a, x, y, end " + \
	"RETURN x, y, end LIMIT 50;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		#create nodes if they don't already exist
		if (r['x']['filename'] not in [node[0] for node in nodes]):
			nodes.append((r['x']['filename'], 2))
		if (r['y']['filename'] not in [node[0] for node in nodes]):
			nodes.append((r['y']['filename'], 2))
		if (r['end']['author'] not in [node[0] for node in nodes]):
			nodes.append((r['end']['author'], 3))
		#add links (relationships)
		links.append(([node[0] for node in nodes].index(a['author']), [node[0] for node in nodes].index(r['x']['filename'])))
		links.append(([node[0] for node in nodes].index(r['x']['filename']), [node[0] for node in nodes].index(r['y']['filename'])))
		links.append(([node[0] for node in nodes].index(r['y']['filename']), [node[0] for node in nodes].index(r['end']['author'])))

	congruence_JSON_string = '{"nodes":['
	if nodes:
		for node in nodes[:-1]:
			congruence_JSON_string = congruence_JSON_string + '{"name":"'+node[0]+'","group":'+str(node[1])+'},'
		congruence_JSON_string = congruence_JSON_string + '{"name":"'+nodes[-1][0]+'","group":'+str(nodes[-1][1])+'}'
	
	congruence_JSON_string = congruence_JSON_string + '], "links":['
	if links:
		for link in links[:-1]:
			congruence_JSON_string = congruence_JSON_string + '{"source":'+str(link[0])+',"target":'+str(link[1])+'},'
		congruence_JSON_string = congruence_JSON_string + '{"source":'+str(links[-1][0])+',"target":'+str(links[-1][1])+'}'
	
	congruence_JSON_string = congruence_JSON_string + ']}'

	return congruence, congruence_JSON_string

