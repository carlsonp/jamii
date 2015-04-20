from django.db import models

class DevKnowledge(models.Model):
	name = models.CharField(max_length=100)
	knowledge = models.CharField(max_length=10)

	def __unicode__(self):
		return self.name

class Developer(models.Model):
	name = models.CharField(max_length=100)
	email = models.CharField(max_length=100)

	def __unicode__(self):
		return self.name

class Congruence(models.Model):
	UIC = models.FloatField() #unweighted individual congruence
	name = models.CharField(max_length=100) #developer name

class CongruencePercentages(models.Model):
	file_percentage = models.FloatField() #file percentage scoring
	comm_percentage = models.FloatField() #communication percentage scoring
	difference_score = models.FloatField() #difference calculation
	name = models.CharField(max_length=100) #developer name
	email = models.CharField(max_length=100) #developer email
	email_hash = models.CharField(max_length=100) #developer email hash for Gravatar

class CodeImpact(models.Model):
	commit_hash = models.CharField(max_length=100) #commit hash
	date = models.CharField(max_length=100) #commit date epoch
	datereadable = models.CharField(max_length=100) #commit date human readable
	delta_impact = models.FloatField() #delta code impact value
	delta_impact_msg = models.CharField(max_length=100) #string message explaining the relative impact
	logmsg = models.CharField(max_length=100) #commit message
	author_developer = models.CharField(max_length=100) #author developer name
	author_email = models.CharField(max_length=100) #author email address
	
class CodeImpactFiles(models.Model):
	code_impact = models.FloatField() #code impact value
	filename = models.CharField(max_length=100) #filename
	function = models.CharField(max_length=100) #function name
	functionfilename = models.CharField(max_length=100) #file that has the function

class FolderListing(models.Model):
	folder_link = models.CharField(max_length=100) #folder link for URL
	name = models.CharField(max_length=100) #last folder name
