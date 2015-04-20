import math, socket, time, sys, subprocess

from django.conf import settings

from py2neo import neo4j

from sourcecodeknowledge.models import CodeImpact, CodeImpactFiles

def returnCommitInformation(project, commit):
	try:
		gdb = neo4j.GraphDatabaseService(settings.NEO4J_SERVER)
	except socket.error:
		print "Unable to connect to Neo4j: ", settings.NEO4J_SERVER
		return None

	q = "START a=node(*) where has(a.hash) return max(a.total_delta) as maximum;"
	result = neo4j.CypherQuery(gdb, q) #TODO: switch this so it's only a single return (so we don't have to go through the for loop)
	for r in result.stream():
		maximum = r['maximum']

	commit_info = None

	q = "START a=node(*) match a-[:impact]->() where a.hash = '"+commit+"' return distinct a;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream(): #TODO: switch this so it's only a single return (so we don't have to go through the for loop)
		converted_date = time.strftime('%Y/%m/%d', time.localtime(int(r.a['date'])))
		if r.a['total_delta'] == 0:
			impact_msg = "No technical change"
		elif r.a['total_delta'] < (maximum * 0.25):
			impact_msg = "Minimal technical change"
		elif r.a['total_delta'] < (maximum * 0.5):
			impact_msg = "Low technical change"
		elif r.a['total_delta'] < (maximum * 0.75):
			impact_msg = "Moderate technical change"
		else:
			impact_msg = "Substantial technical change."
		commit_info = CodeImpact(commit_hash=r.a['hash'], date=converted_date, delta_impact=round(r.a['total_delta'], 3), delta_impact_msg=impact_msg, logmsg=r.a['logmsg'], author_developer=r.a['author_developer'], author_email=r.a['author_email'])

	#if we don't have an :impact edge, we still need to populate the commit_info variable
	if not commit_info:
		q = "START a=node(*) where a.hash = '"+commit+"' return a;"
		result = neo4j.CypherQuery(gdb, q)
		for res in result.stream(): #TODO: switch this so it's only a single return (so we don't have to go through the for loop)
			converted_date = time.strftime('%Y/%m/%d', time.localtime(int(res.a['date'])))
			commit_info = CodeImpact(commit_hash=res.a['hash'], date=converted_date, delta_impact=0, delta_impact_msg="No technical change", logmsg=res.a['logmsg'], author_developer=res.a['author_developer'], author_email=res.a['author_email'])


	code_impact = []

	q = "START a=node(*) match a-[r:impact]->b where a.hash = '"+commit+"' optional match b<-[:has]-c return r, b, c order by r.impactvalue desc limit 10;"
	result = neo4j.CypherQuery(gdb, q)
	for r in result.stream():
		if r.c is not None:
			code_impact.append(CodeImpactFiles(code_impact=round(r.r['impactvalue'], 3), filename=r.b['filename'], function=r.b['function'], functionfilename=r.c['filename']))
		else:
			code_impact.append(CodeImpactFiles(code_impact=round(r.r['impactvalue'], 3), filename=r.b['filename'], function=r.b['function'], functionfilename=None))

	return commit_info, code_impact
