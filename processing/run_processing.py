import sys, os, re, subprocess, getopt
sys.path.append("../")
import devknowledge.settings

from DatabaseThread import consumerDatabaseThread, consumerDatabaseThreadManager
import Git, Mercurial, Util

from ThreadPool import ThreadPool

def main(argv):
	#Parse commandline arguments
	#http://www.tutorialspoint.com/python/python_command_line_arguments.htm
	update_existing = False
	try:
		opts, args = getopt.getopt(argv,"h:u:")
	except getopt.GetoptError:
		print "run_processing.py -u <True/False>"
		sys.exit(2)
	for opt, arg in opts:
		if opt == "-h":
			print "run_processing.py -u <True/False>"
		elif opt == "-u":
			if arg == "True":
				update_existing = True

	projects = [d for d in os.listdir(devknowledge.settings.VERSION_CONTROL_REPOS) if os.path.isdir(os.path.join(devknowledge.settings.VERSION_CONTROL_REPOS, d))]

	if update_existing:
		print "Running in-place update."
		manager = None
	else:
		manager = consumerDatabaseThreadManager("knowledge")

	pool = ThreadPool(devknowledge.settings.CONCURRENT_THREADS)

	tip_hashes = {}

	all_files = []
	last_line = []

	#iterate through all projects
	for project in projects:
		if project in devknowledge.settings.PROJECT_FOLDERS:
			all_files, last_lines = Util.returnFilesLastLine(project)
			if update_existing:
				#there were issues with threads duplicating authors/files so we just mass add them at the beginning
				print "Starting initial processing of authors/files."
				Git.createFilesAuthorsInIndex(project, all_files)
				print "Finished creating authors/files."
			number_to_process = len(all_files)
			print "Number of files to process: ", number_to_process
			processed_files = 0
			for i in range(0, len(all_files)):
				file = all_files[i]
				last_line = last_lines[i]
				print "Project: ", project, " ", file, " number lines: ", last_line
				project_type = Util.returnProjectType(devknowledge.settings.VERSION_CONTROL_REPOS+project)
				if project_type == "git":
					#run Git analysis
					if project not in tip_hashes:
						#create new head hash cache
						tip_hashes[project] = Util.returnHeadHash(devknowledge.settings.VERSION_CONTROL_REPOS+project)

					if update_existing:
						Git.storeKnowledge(manager, project, file, 1, last_line, update_existing, tip_hashes[project])
					else:
						pool.add_task(Git.storeKnowledge, manager, project, file, 1, last_line, update_existing, tip_hashes[project])
				elif project_type == "hg":
					#run Mercurial analysis
					if project not in tip_hashes:
						#create new tip hash cache
						tip_hashes[project] = Mercurial.returnTipHash(devknowledge.settings.VERSION_CONTROL_REPOS+project)

					pool.add_task(Mercurial.storeKnowledge, manager, project, file, 1, last_line, tip_hashes[project])

				processed_files += 1
				print "Percent done: %.2f %%" % float(float(processed_files)/float(number_to_process) * 100)
				Util.checkDatabaseFolderSize()
			print "Finishing up writing data to database."
			pool.wait_completion()
			if update_existing:
				#prune database of stale file and author nodes
				print "Starting prune of database."
				if project_type == "git":
					Git.pruneDatabaseStaleFiles(all_files, project)
					Git.pruneDatabaseStaleAuthors()
					Git.pruneAllOtherNodes()
				elif project_type == "hg":
					print "Not yet implemented."

	if manager:
		manager.markForFinish()

	print "Done.  Exiting."


if __name__ == "__main__":
   main(sys.argv[1:])
