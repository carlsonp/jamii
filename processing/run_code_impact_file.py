import sys, os, re, subprocess, getopt, shutil, Queue
from subprocess import STDOUT
sys.path.append("../")
import devknowledge.settings
import Util
import clang.cindex
from clang.cindex import TranslationUnitLoadError #for clang errors

class FilenameEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["project", "filename", "include_filename"]
	def __init__(self, project, filename, include_filename):
		self.project = project
		self.filename = filename
		self.include_filename = include_filename

class FunctionDefCallEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["project", "filename", "function_name", "ending_filename"]
	def __init__(self, project, filename, function_name, ending_filename):
		self.project = project
		self.filename = filename
		self.function_name = function_name
		self.ending_filename = ending_filename

def main(argv):
	#Parse commandline arguments
	#http://www.tutorialspoint.com/python/python_command_line_arguments.htm
	start_hash = None
	try:
		opts, args = getopt.getopt(argv,"h:s:")
	except getopt.GetoptError:
		print "-s <hash>"
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print "-s <hash>"
		elif opt == "-s":
			start_hash = arg

	projects = [d for d in os.listdir(devknowledge.settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, d))]
	
	if os.path.exists("/tmp/devknowledge/"):
		shutil.rmtree("/tmp/devknowledge/")
	os.makedirs("/tmp/devknowledge/")

	#iterate through all projects
	for project in projects:
		if project in devknowledge.settings.PROJECT_FOLDERS:
			git_repo = devknowledge.settings.VERSION_CONTROL_REPOS+project
			include_dirs = Util.getIncludeDirectories(git_repo)
			Util.checkoutHash(git_repo, Util.returnMasterHash(git_repo))
			#from oldest commit to newest
			hash_commits = returnHashCommits(git_repo, start_hash)
			number_to_process = len(hash_commits)
			print "Number of commits to process: ", number_to_process
			processed_commits = 0
			for commit in hash_commits:
				print "Running on hash: ", commit
				Util.checkoutHash(git_repo, commit)
				all_files_list = fileGenerator(git_repo)
				if commit == start_hash:
					changed_files = fileGenerator(git_repo)
				else:
					#only process files that have changed
					changed_files = Util.returnListCPPFilesChanged(git_repo, commit)
				print "Number of changed files: ", len(changed_files)
				
				if len(changed_files) != 0:
					runClang(project, all_files_list, changed_files, commit, include_dirs)
				
				processed_commits += 1
				print "Percent done: %.2f %%" % float(float(processed_commits)/float(number_to_process) * 100)
	print "Done.  Exiting."

def parse_ast(cursor, item_queue, project, level=1):
	if (level != 1) or (cursor.location.file is not None and cursor.location.file.name is not None and not cursor.location.file.name.startswith('/usr/include') and not cursor.location.file.name.startswith('/usr/lib')):
		if cursor.kind == clang.cindex.CursorKind.CALL_EXPR and cursor.referenced is not None and cursor.referenced.location.file is not None and not str(cursor.referenced.location.file).startswith('/usr/include') and not str(cursor.referenced.location.file).startswith('/usr/lib'):
			#print "Call: ", cursor.location.file.name
			#print "Function Name: ", cursor.referenced.spelling
			#print "Definition: ", cursor.referenced.location.file
			current_file = cursor.location.file.name.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
			definition_file = cursor.referenced.location.file.name.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
			if not cursor.referenced.spelling.startswith("operator"):
				entry = FunctionDefCallEntry(project, current_file, cursor.referenced.spelling, definition_file)
				item_queue.put(entry)
        for c in cursor.get_children():
            parse_ast(c, item_queue, project, level+1)

def runClang(project, all_files, files_changed, commit, include_dirs):
	item_queue = Queue.Queue()
	index = clang.cindex.Index.create()
	#there's very little documentation or examples on the clang python bindings
	#http://eli.thegreenplace.net/2011/07/03/parsing-c-in-python-with-clang/
	#https://gist.github.com/anonymous/2503232

	print "Starting clang processing."
	for f in all_files:
		arg_list = ['-x', 'c++']
		for arg in devknowledge.settings.INCLUDE_PATHS:
			arg_list.append('-I')
			arg_list.append(arg)
		for arg in include_dirs:
			arg_list.append('-I')
			arg_list.append(arg)

		if f in files_changed:
			try:
				tu = index.parse(f, args=arg_list)
				current_file = tu.spelling.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
				entry = FilenameEntry(project, current_file, None)
				item_queue.put(entry)
				#process includes
				for include_location in tu.get_includes():
					if not include_location.include.name.startswith('/usr/include') and not include_location.include.name.startswith('/usr/lib'):
						include_file = include_location.include.name.replace(devknowledge.settings.VERSION_CONTROL_REPOS+project, "")
						entry = FilenameEntry(project, current_file, include_file)
						item_queue.put(entry)

				parse_ast(tu.cursor, item_queue, project)
			except TranslationUnitLoadError:
				print "Error: TranslationUnitLoadError - ", f

	#print "Finished with clang processing."
	del index
	if not item_queue.empty():
		#process FIFO queue for file
		saveQueueToFile(item_queue, commit)

def saveQueueToFile(items, commit):
	if not items.empty():
		#open file
		fo = open("/tmp/devknowledge/"+str(commit)+".txt", "w")
		while not items.empty():
			item = items.get()
			if isinstance(item, FilenameEntry):
				fo.write("file,"+str(item.project)+","+str(item.filename)+","+str(item.include_filename)+"\n")
			if isinstance(item, FunctionDefCallEntry):
				fo.write("function,"+str(item.project)+","+str(item.filename)+","+str(item.function_name)+","+str(item.ending_filename)+"\n")
		fo.close()

def fileGenerator(git_repo):
	return_files = []
	p = subprocess.Popen(["find "+git_repo+" -name '*.cpp' -o -name '*.h' -o -name '*.hpp' -o -name '*.c'"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		return_files.append(line.rstrip("\n"))
	return return_files

def returnHashCommits(git_repo, start_hash):
	hash_commits = []

	found = False
	#provides commits from most recent to oldest
	p = subprocess.Popen(["git --git-dir="+git_repo+"/.git/ --work-tree="+git_repo+" log --pretty=format:%H"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in p.stdout.readlines():
		line = line.rstrip("\n")
		if start_hash == line:
			hash_commits.append(line)
			found = True
		if not found:
			hash_commits.append(line)
	hash_commits.reverse()
	return hash_commits

if __name__ == "__main__":
   main(sys.argv[1:])
