import sys, os, re, subprocess, getopt
sys.path.append("../")
import devknowledge.settings

from DatabaseThread import dependenciesDatabaseThread, consumerDatabaseThreadManager
import FileDependencies, Util

from ThreadPool import ThreadPool

def main(argv):
	#Parse commandline arguments
	#http://www.tutorialspoint.com/python/python_command_line_arguments.htm
	update_existing = False
	try:
		opts, args = getopt.getopt(argv,"h:u:")
	except getopt.GetoptError:
		print "run_dependencies.py -u <True/False>"
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print "run_dependencies.py -u <True/False>"
		elif opt == "-u":
			if arg == "True":
				update_existing = True

	projects = [d for d in os.listdir(devknowledge.settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, d))]

	if update_existing:
		print "Running in-place update."
		manager = None
	else:
		manager = consumerDatabaseThreadManager("dependencies")

	pool = ThreadPool(devknowledge.settings.CONCURRENT_THREADS)

	#iterate through all projects
	for project in projects:
		if project in devknowledge.settings.PROJECT_FOLDERS:
			all_files, last_lines = Util.returnFilesLastLine(project)
			c_files = Util.returnCandCPlusPlusFiles(all_files, project)
			number_to_process = len(c_files)
			print "Number of files to process: ", number_to_process
			processed_files = 0
			for file in c_files:
				last_line = last_lines[processed_files]
				#print "Project: ", project, " ", file, " number lines: ", last_line

				if update_existing:
					FileDependencies.parseFileDependencies(manager, project, file, c_files, update_existing)
				else:
					pool.add_task(FileDependencies.parseFileDependencies, manager, project, file, c_files, update_existing)

				processed_files += 1

				print "Percent done: %.2f %%" % float(float(processed_files)/float(number_to_process) * 100)
				Util.checkDatabaseFolderSize()
			print "Finishing up writing data to database."
			pool.wait_completion()

	if not update_existing:
		manager.markForFinish()
	print "Done.  Exiting."



if __name__ == "__main__":
   main(sys.argv[1:])
