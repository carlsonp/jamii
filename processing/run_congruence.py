import sys, os, re, subprocess, getopt
sys.path.append("../")
import devknowledge.settings

import Util, socket, math, time

from py2neo import neo4j

class Expertise:
	name = ''
	email = ''
	neo4j_id = ''
	expertise = 0.0

	def __init__(self, name, email, neo4j_id, expertise):
		self.name = name
		self.email = email
		self.neo4j_id = neo4j_id
		self.expertise = expertise

def main(argv):

	projects = [d for d in os.listdir(devknowledge.settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, d))]
	
	try:
		gdb = neo4j.GraphDatabaseService(devknowledge.settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", devknowledge.settings.NEO4J_SERVER

	#iterate through all projects
	for project in projects:
		if project in devknowledge.settings.PROJECT_FOLDERS:
			#calculate expertise score
			all_files, last_lines = Util.returnFilesLastLine(project)
			number_to_process = len(all_files)
			print "Number of files to process: ", number_to_process
			processed_files = 0
			for file in all_files:
				last_line = last_lines[processed_files]
				#print "Project: ", project, " ", file, " number lines: ", last_line

				saveExpertise(gdb, project, project+file, 1, last_line)

				processed_files += 1

				exp_percentage = float(float(processed_files)/float(number_to_process) * 100)
				printPercentage(exp_percentage, 0, 0, 0, 0, 0)

				#You can comment this out for a small speed boost
				#Util.checkDatabaseFolderSize()

			#calculate communication score
			email_list = Util.returnListAllEmails(project)
			number_people_process = len(email_list)
			processed_comm = 0
			
			for email in email_list:
				saveCommunication(gdb, project, email)
				processed_comm += 1

				comm_percentage = float(float(processed_comm)/float(number_people_process) * 100)
				printPercentage(100, comm_percentage, 0, 0, 0, 0)
				
				#You can comment this out for a small speed boost
				#Util.checkDatabaseFolderSize()

			#calculate interpersonal score (total of communication_score values)
			processed_personal = 0
			
			for email in email_list:
				saveInterpersonalScore(gdb, project, email)
				processed_personal += 1
				
				interpersonal_percentage = float(float(processed_personal)/float(number_people_process) * 100)
				printPercentage(100, 100, interpersonal_percentage, 0, 0, 0)
				
				#You can comment this out for a small speed boost
				#Util.checkDatabaseFolderSize()
				
			#delete communication_scores
			q = "START a=node(*) MATCH (a)-[r:communication_score]->() DELETE r;"
			result = neo4j.CypherQuery(gdb, q)
			result.execute()

			#calculate file score (total weighted value of expertise values)
			processed_file_score = 0
			
			for email in email_list:
				saveFileScore(gdb, project, email)
				processed_file_score += 1
				
				file_percentage = float(float(processed_file_score)/float(number_people_process) * 100)
				printPercentage(100, 100, 100, file_percentage, 0, 0)
				
				#You can comment this out for a small speed boost
				#Util.checkDatabaseFolderSize()
				
			#calculate and save overall aggregate average file/communication scores
			processed_overall_scores = 0
			
			for email in email_list:
				calculateOverallFileCommScores(gdb, project, email)
				processed_overall_scores += 1
				
				file_percentage = float(float(processed_overall_scores)/float(number_people_process) * 100)
				printPercentage(100, 100, 100, 100, file_percentage, 0)
				
				#You can comment this out for a small speed boost
				#Util.checkDatabaseFolderSize()
				
			#calculate and save normalized percentage of score
			calculate_processed = 0
			
			for email in email_list:
				calculateNormalizedPercentage(gdb, project, email)
				calculate_processed += 1
				
				file_percentage = float(float(calculate_processed)/float(number_people_process) * 100)
				printPercentage(100, 100, 100, 100, 100, file_percentage)
				
				#You can comment this out for a small speed boost
				#Util.checkDatabaseFolderSize()

	print "Done.  Exiting."


def printPercentage(exp_percentage, comm_percentage, personal_percentage, file_percentage, overall_percentage, calculate_percentage):
	#clear terminal for printing percentages
	#https://stackoverflow.com/questions/2084508/clear-terminal-in-python
	os.system('cls' if os.name == 'nt' else 'clear')

	print "Expertise Percent done: %.2f %%" % exp_percentage
	print "Communication Percent done: %.2f %%" % comm_percentage
	print "Interpersonal Score Percent done: %.2f %%" % personal_percentage
	print "File Score Percent done: %.2f %%" % file_percentage
	print "Overall Score Calculation Percent done: %.2f %%" % overall_percentage
	print "Calculate Overall Percentages: %.2f %%" % calculate_percentage
	
	
def calculateNormalizedPercentage(gdb, project, email):

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")
	
	a = index_nodes.get("author", email)
	a = a[0]
	if a:
		#calculate file_score percentage
		q = "start a=node("+str(a._id)+") match (a)-[r:file_score]->() return min(r.score), max(r.score);"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			minimum = r[0]
			maximum = r[1]
		
		#if the minimum equals the maximum, we have no range of data therefore we can't make any suggestions
		if minimum != maximum and minimum != "" and maximum != "" and minimum is not None and maximum is not None:
			q = "start a=node("+str(a._id)+") match (a)-[r:file_score]->() return r;"
			result = neo4j.CypherQuery(gdb, q)
			for r in result.stream():
				r.r['percentage'] = normalizeScore(r.r['score'], minimum, maximum)
		
		#calculate interpersonal_score percentage
		q = "start a=node("+str(a._id)+") match (a)-[r:interpersonal_score]->() return min(r.score), max(r.score);"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			minimum = r[0]
			maximum = r[1]
		
		if minimum != maximum and minimum != "" and maximum != "" and minimum is not None and maximum is not None:
			q = "start a=node("+str(a._id)+") match (a)-[r:interpersonal_score]->() return r;"
			result = neo4j.CypherQuery(gdb, q)
			for r in result.stream():
				r.r['percentage'] = normalizeScore(r.r['score'], minimum, maximum)

	
def normalizeScore(score, minimum, maximum):
	return (score - minimum) / (maximum - minimum)

	
def calculateOverallFileCommScores(gdb, project, email):

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")
	
	a = index_nodes.get("author", email)
	a = a[0]
	if a:
		q = "start a=node("+str(a._id)+") match a-[r:file_score]->() return avg(r.score);"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			#set property for this node
			a['overall_file_score'] = r[0]
			
		q = "start a=node("+str(a._id)+") match a-[r:interpersonal_score]->() return avg(r.score);"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			#set property for this node
			a['overall_interpersonal_score'] = r[0]
		
	
def saveFileScore(gdb, project, email):

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	#weighting: 1, 1/2, 1/4, etc.
	#same file, dependent files, middle-man file, etc.

	email_list = []

	a = index_nodes.get("author", email)
	a = a[0]
	if a:
		#figure out who we should query for paths, this prevents us from running on every single pairing which takes way too long
		q = "start a=node("+str(a._id)+") match a-[:expertise]->()-[:depends*0..2]-()<-[:expertise]-b where a<>b return distinct(b);"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			email_list.append(r.b['email'])
	
		for e in email_list:
			b = index_nodes.get("author", e)
			b = b[0]
			if b:
				total_file_score = 0
				intermediate_score = 0

				#same file
				q = "START a=node("+str(a._id)+"), b=node("+str(b._id)+") match a-[r:expertise]->()<-[:expertise]-b with sum(r.expertise) as sum WHERE sum > 0 return sum;"
				result = neo4j.CypherQuery(gdb, q)
				for r in result.stream():
					intermediate_score += float(r[0])
				total_file_score += intermediate_score #times 1
				intermediate_score = 0

				#dependent files
				q = "START a=node("+str(a._id)+"), b=node("+str(b._id)+") match a-[r:expertise]->()-[:depends]-()<-[:expertise]-b with sum(r.expertise) as sum WHERE sum > 0 return sum;"
				result = neo4j.CypherQuery(gdb, q)
				for r in result.stream():
					intermediate_score += float(r[0])
				total_file_score += intermediate_score * 0.5
				intermediate_score = 0

				#middle-man file
				q = "START a=node("+str(a._id)+"), b=node("+str(b._id)+") match a-[r:expertise]->()-[:depends]-()-[:depends]-()<-[:expertise]-b with sum(r.expertise) as sum WHERE sum > 0 return sum;"
				result = neo4j.CypherQuery(gdb, q)
				for r in result.stream():
					intermediate_score += float(r[0])
				total_file_score += intermediate_score * 0.25

				#create new relationship between A and B with the summed and weighted score value
				rel, = gdb.create((a, "file_score", b, {"score": float(total_file_score)}))


def saveInterpersonalScore(gdb, project, email):

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	email_list = []

	a = index_nodes.get("author", email)
	a = a[0]
	if a:
		#get list of people to check for score, this way we don't have to run on every pairing which takes a long time
		q = "START a=node("+str(a._id)+") MATCH (a)-[:communication_score]->()<-[:communication_score]-(b) where a<>b return distinct(b);"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			email_list.append(r.b['email'])

		for e in email_list:
			b = index_nodes.get("author", e)
			b = b[0]
			if b:
				q = "START a=node("+str(a._id)+"), b=node("+str(b._id)+") MATCH (a)-[r:communication_score]->()<-[:communication_score]-(b) with sum(r.score) AS sum WHERE sum > 0 RETURN sum;"
				result = neo4j.CypherQuery(gdb, q)
				for r in result.stream():
					rel, = gdb.create((a, "interpersonal_score", b, {"score": float(r[0])}))



def saveCommunication(gdb, project, email):

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	a = index_nodes.get("author", email)
	a = a[0]
	if a:
		#http://docs.neo4j.org/refcard/2.0/
		q = "START a=node("+str(a._id)+") MATCH (a)-[:communication]->(e) RETURN DISTINCT e;"
		result = neo4j.CypherQuery(gdb, q)
		try:
			for r in result.stream():
				comm_score = 0
				q = "START a=node("+str(a._id)+"), e=node("+str(r.e._id)+") MATCH (a)-[c:communication]->(e) RETURN c;"
				result_nested = neo4j.CypherQuery(gdb, q)
				for c in result_nested.stream():
					days = (((time.mktime(time.gmtime()) - float(c.c['epoch'])) / 60) / 60) / 24
					comm_score = comm_score + math.pow((1 - devknowledge.settings.EXPONENTIAL_DECAY), days)
				rel, = gdb.create((a, "communication_score", r.e, {"score": comm_score}))
		except ValueError:
			#TODO: find why this might be erroring in py2neo
			#raise ValueError("Cannot determine object type", data)
			print "Error: ValueError. continuing..."


def saveExpertise(gdb, project, filename, line_start, line_end):

	index_nodes = gdb.get_or_create_index(neo4j.Node, "index_nodes")

	f = index_nodes.get('filename', filename)
	if f:
		f = f[0]
	#TODO: check why this might fail

	if f:
		expertise = {}

		#http://docs.neo4j.org/refcard/2.0/
		# this returns all developers
		q = "START f=node("+str(f._id)+") MATCH f<-[rel:knowledge]-a WHERE rel.line_number >= "+str(line_start)+" AND rel.line_number <= "+str(line_end)+" return rel, a;"
		result = neo4j.CypherQuery(gdb, q)
		for r in result.stream():
			#print "Author: ", r.a['author']
			a = index_nodes.get("author", r.a['email'])
			a = a[0]
			if a:
				if r.a['email'] not in expertise:
					#create object if it's not in the hash table
					expertise[r.a['email']] = Expertise(name=r.a['name'], email=r.a['email'], neo4j_id=r.a._id, expertise=0.0)

				days = (((time.mktime(time.gmtime()) - float(r.rel['epoch'])) / 60) / 60) / 24
				expertise[r.a['email']].expertise = expertise[r.a['email']].expertise + math.pow((1 - devknowledge.settings.EXPONENTIAL_DECAY), days)

		for dev in expertise:
			a = index_nodes.get("author", expertise[dev].email)
			a = a[0]
			rel, = gdb.create((a, "expertise", f, {"expertise": expertise[dev].expertise}))


if __name__ == "__main__":
   main(sys.argv[1:])
