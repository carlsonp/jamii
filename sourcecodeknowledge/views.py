# views.py

from django.http import HttpResponse
from django.shortcuts import render

from django.conf import settings

from includes import pygment_format, list_projects, list_developers, read_file, CalcExpertise, CalcCongruence, CodeImpact, CommitInformation, FindDevelopers

from sourcecodeknowledge.models import DevKnowledge, FolderListing
from sourcecodeknowledge.forms import CodeImpactFilter

import hashlib, json

# Displays the main index page
def index(request):

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/index.html')

def communicationindex(request, project):
	context = {
		'project': project
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/communicationindex.html', context)

def developers(request, project, letter="unknown", page=1):
	page = int(page)
	developers_model = list_developers.returnDevelopers(project, letter, page)
	if len(developers_model) == 50:
		next_page = True
	else:
		next_page = False
	context = {
		'project': project,
		'letter': letter,
		'page': page,
		'developers': developers_model,
		'next_page': next_page,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/developers.html', context)
	
def finddevelopers(request, project, developer):
	#TODO: sanitize input
	found = FindDevelopers.findDevelopers(project, developer)

	response_data = []
	for dev in found:
		response_data.append({'value': dev.name+" ("+dev.email+")", 'email': dev.email})

	return HttpResponse(json.dumps(response_data), content_type="application/json")

def getcommits(request, project):
	if request.method == 'POST':
		#TODO: sanitize input
		# create a form instance and populate it with data from the request:
		form = CodeImpactFilter(request.POST)
		# check whether it's valid:
		if form.is_valid():
			limit = form.cleaned_data['limit']
			epochtime = form.cleaned_data['epochtime']
			relativetoemail = form.cleaned_data['relativetoemail']
			if limit <= 60:
				found = CodeImpact.filteredCodeImpact(project, str(limit), str(epochtime), relativetoemail)

				response_data = []
				for commit in found:
					response_data.append({'commit_hash': commit.commit_hash,
										'datereadable': commit.datereadable,
										'delta_impact': commit.delta_impact,
										'author_developer': commit.author_developer,
										'author_email': commit.author_email,
										'logmsg': commit.logmsg})

				return HttpResponse(json.dumps(response_data), content_type="application/json")

	#failure, send nothing
	return HttpResponse(json.dumps([]), content_type="application/json")

def searchdevelopers(request, project):
	searchterm = request.POST.get('searchterm', "")
	if searchterm != "":
		developers_model = list_developers.searchDevelopers(project, searchterm)
	else:
		developers_model = None

	context = {
		'project': project,
		'developers': developers_model,
		'searchterm': searchterm,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/searchdevelopers.html', context)

def congruence(request, project, dev_email):
	name, congruence_array = CalcCongruence.calculateCongruence(project, dev_email)
	
	email_hash = hashlib.md5(dev_email).hexdigest().lower()

	context = {
		'name': name,
		'project': project,
		'dev_email': dev_email,
		'email_hash': email_hash,
		'congruence_array': congruence_array,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/congruence.html', context)


# Displays the sourcecode file for the user to select lines
def file(request, project, file):
	# read in file and get code
	code, number_lines = read_file.readFile(project+"/"+file)
	#TODO: this section needs to be rewritten once the lines are figured out
	sourcecode, css, language = pygment_format.formatSourcecode(project+file, code)
	developers = list_projects.returnUniqueAuthors(project, file)
	
	knowledge_model = []
	if request.method == "POST":
		#TODO: sanatize POST data
		if developers is not None:
			knowledge_model = CalcExpertise.calculateExpertise(project+"/"+file, developers, int(request.POST['start']), int(request.POST['end']))
		else:
			knowledge_model = "NotAvailable"
		start = int(request.POST['start'])
		end = int(request.POST['end'])
	else:
		start = 1
		end = number_lines

	#TODO: should some of this stuff be stored in a Model?
	context = {
		'project': project,
		'file': file,
		'sourcecode': sourcecode,
		'css': css,
		'language': language,
		'start': start,
		'end': end,
		'knowledge_model': knowledge_model,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/file.html', context)

# Displays the main page with links for this project
def project(request, project):
	context = {
		'project': project,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/project.html', context)

# Displays directory and file structure links for user to click on for a particular git repo
def expertise(request, project, subfolder=""):
	folders, files = list_projects.listRepoFilesAndFolders(project, subfolder)
	subfolder_list_split = subfolder.split('/')
	subfolders_list = []
	for i in range(0, len(subfolder_list_split)):
		f_name = ""
		build_string = ""
		for j in range(0, i+1):
			if j == 0:
				build_string = build_string + subfolder_list_split[j]
			else:
				build_string = build_string + "/" + subfolder_list_split[j]
			f_name = subfolder_list_split[j]
		subfolders_list.append(FolderListing(folder_link=build_string, name=f_name))

	context = {
		'project': project,
		'subfolder': subfolder,
		'subfolders_list': subfolders_list,
		'folders': folders,
		'files': files,
		'extensions': settings.WHITELIST_EXTENSIONS
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/expertise.html', context)
	
# Displays a list of the most recent code hash commits and the delta code impact
def codeimpact(request, project):

	codeimpact = CodeImpact.returnCodeImpact(project)

	context = {
		'project': project,
		'codeimpact': codeimpact,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/codeimpact.html', context)

# Displays a graph of the most recent code hash commits and the delta code impact
def codeimpactgraph(request, project):

	codeimpact = CodeImpact.returnCodeImpact(project)

	context = {
		'project': project,
		'codeimpact': codeimpact,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/codeimpactgraph.html', context)

# Displays information about a specific commit
def commit(request, project, commit):

	if len(commit) == 40: #check SHA1 hash length
		commit_info, code_impact = CommitInformation.returnCommitInformation(project, commit)

	context = {
		'project': project,
		'commit_info': commit_info,
		'code_impact': code_impact,
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/commit.html', context)

# Displays the about page
def about(request, project):
	context = {
		'project': project
	}

	#render() takes (request, template, dictionary (optional third argument))
	return render(request, 'sourcecodeknowledge/about.html', context)
