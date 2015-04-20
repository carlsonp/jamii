import sys, socket
from datetime import datetime
import Queue, threading

sys.path.append("../")
import devknowledge.settings


class SaveEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["project", "line_number", "epoch", "hash", "author", "email", "filename", "most_recent_hash"]
	def __init__(self, project, line_number, epoch, hash, author, email, filename, most_recent_hash):
		self.project = project
		self.line_number = line_number
		self.epoch = epoch
		self.hash = hash
		self.author = author
		self.email = email
		self.filename = filename
		self.most_recent_hash = most_recent_hash

class FileDependencyEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["project", "fromFilename", "toFilename", "line_number"]
	def __init__(self, project, fromFilename, toFilename, line_number):
		self.project = project
		self.fromFilename = fromFilename
		self.toFilename = toFilename
		self.line_number = line_number

class CommunicationEntry:
	# We use slots here to save memory, a dynamic dictionary is not needed
	__slots__ = ["author", "email", "subject", "body", "epoch"]
	def __init__(self, author, email, subject, body, epoch):
		self.author = author
		self.email = email
		self.subject = subject
		self.body = body
		self.epoch = epoch


class consumerDatabaseThreadManager:

	def __init__(self, system):
		#print "Database manager constructor."
		self.items = Queue.Queue()
		self.run_mutex = ["True"] # we need a list so that it's mutable and passed by reference
		if system == "knowledge":
			self.thread = consumerDatabaseThread(self.items, self.run_mutex)
		elif system == "dependencies":
			self.thread = dependenciesDatabaseThread(self.items, self.run_mutex)
		elif system == "communication":
			self.thread = communicationDatabaseThread(self.items, self.run_mutex)

	def addToQueue(self, save_entry):
		#print "Queue size: ", str(self.items.qsize())
		self.items.put(save_entry)

	def markForFinish(self):
		#print "Waiting for consumer thread to finish."
		self.run_mutex[0] = "False"
		self.thread.join() #this blocks indefinitely


class consumerDatabaseThread(threading.Thread):

	def __init__(self, items, run_mutex):
		#print "Database thread constructor."
		self.items = items
		self.run_mutex = run_mutex
		threading.Thread.__init__(self)
		self.daemon = True #this is needed so the main python process exits once these are done
		self.start()

	def run(self):
		#IMPORTANT:
		#The python embedded bindings for Neo4j use JPype.  Based on the Neo4j mailing list thread
		#entitled [Neo4j] Java segfaults using paste and Python bindings, the Neo4j Python binding
		#needs to be single threaded.  Thus, waiting to import until the thread is ready and running.
		from neo4j import GraphDatabase

		gdb = None
		index_nodes = None

		try:
			#print "Connecting to database: ",devknowledge.settings.NEO4J_DATABASE
			gdb = GraphDatabase(devknowledge.settings.NEO4J_DATABASE)
		except Exception, e:
			print "Error: ",e.message()

		#print "About to create database indexes."
		#create indexes (we only need to do this once, thus why it's outside the main loop)
		with gdb.transaction:
			#create indexes
			#TODO: split filenames and authors into two separate indexes? will this improve performance?
			if (not gdb.node.indexes.exists("index_nodes")):
				index_nodes = gdb.node.indexes.create("index_nodes")
				#print "Created index_nodes"
			else:
				index_nodes = gdb.node.indexes.get("index_nodes")
				#print "Using existing index_nodes"

		#print "About to start main database consumer thread."
		while self.run_mutex[0] == "True" or not self.items.empty():
			if not self.items.empty():
				#Try to perform insertions in blocks of 10,000, lots of tiny single insertions take a LONG time waiting for database lock
				if self.items.qsize() >= 10000:
					num_process = 10000
					wait = False
				elif self.items.qsize() < 10000 and self.run_mutex[0] == "False":
					num_process = self.items.qsize()
					wait = False
				else:
					wait = True
				
				if not wait:
					with gdb.transaction:
						print "Queue size: ", str(self.items.qsize())
						for i in range(0, num_process):
							item = self.items.get()

							#create file node if it doesn't exist
							f = index_nodes['filename'][item.project+item.filename]
							if len(f) == 0:
								f = gdb.node(filename=item.project+item.filename, most_recent_hash=item.most_recent_hash)
								index_nodes['filename'][item.project+item.filename] = f
								#print "Finished creating filename node."
							else:
								f = f[0]
								#print "Using existing filename."

							#create author node if it doesn't exist
							a = index_nodes['author'][item.email]
							if len(a) == 1:
								a = a[0]
								a['knowledge_last_update'] = str(datetime.now())
								a['email'] = item.email
								#print "Finished updating author properties."
							else:
								a = gdb.node(author=item.author, knowledge_last_update=str(datetime.now()), email=item.email)
								index_nodes['author'][item.email] = a
								#print "Finished creating author node."

							# We know at this point that this relationship doesn't exist
							#print "Creating new relationship."
							rel = a.relationships.create("knowledge", f, line_number=item.line_number, hash=item.hash, epoch=item.epoch)

						self.items.task_done()


		#close down database
		#print "Closing database"
		if gdb:
			gdb.shutdown()



class dependenciesDatabaseThread(threading.Thread):

	def __init__(self, items, run_mutex):
		#print "Database thread constructor."
		self.items = items
		self.run_mutex = run_mutex
		threading.Thread.__init__(self)
		self.daemon = True #this is needed so the main python process exits once these are done
		self.start()

	def run(self):
		#IMPORTANT:
		#The python embedded bindings for Neo4j use JPype.  Based on the Neo4j mailing list thread
		#entitled [Neo4j] Java segfaults using paste and Python bindings, the Neo4j Python binding
		#needs to be single threaded.  Thus, waiting to import until the thread is ready and running.
		from neo4j import GraphDatabase

		gdb = None
		index_nodes = None

		try:
			#print "Connecting to database: ",devknowledge.settings.NEO4J_DATABASE
			gdb = GraphDatabase(devknowledge.settings.NEO4J_DATABASE)
		except Exception, e:
			print "Error: ",e.message()

		#create indexes (we only need to do this once, thus why it's outside the main loop)
		with gdb.transaction:
			#create indexes
			if (not gdb.node.indexes.exists("index_nodes")):
				index_nodes = gdb.node.indexes.create("index_nodes")
				#print "Created index_nodes"
			else:
				index_nodes = gdb.node.indexes.get("index_nodes")
				#print "Using existing index_nodes"

		#print "About to start main database consumer thread."
		while self.run_mutex[0] == "True" or not self.items.empty():
			if not self.items.empty():
				#Try to perform insertions in blocks of 10,000, lots of tiny single insertions take a LONG time waiting for database lock
				if self.items.qsize() >= 10000:
					num_process = 10000
					wait = False
				elif self.items.qsize() < 10000 and self.run_mutex[0] == "False":
					num_process = self.items.qsize()
					wait = False
				else:
					wait = True

				if not wait:
					with gdb.transaction:
						print "Queue size: ", str(self.items.qsize())
						for i in range(0, num_process):
							item = self.items.get()

							#create file node if it doesn't exist
							to_f = index_nodes['filename'][item.project+item.toFilename]
							if len(to_f) == 0:
								to_f = gdb.node(filename=item.project+item.toFilename)
								index_nodes['filename'][item.project+item.toFilename] = to_f
								print "Creating new toFile, this may be an error."
								print item.toFilename
							else:
								to_f = to_f[0]
								#print "Using existing toFile."
								
							#create file node if it doesn't exist
							from_f = index_nodes['filename'][item.project+item.fromFilename]
							if len(from_f) == 0:
								from_f = gdb.node(filename=item.project+item.fromFilename)
								index_nodes['filename'][item.project+item.fromFilename] = from_f
								print "Creating new fromFile, this may be an error."
								print item.fromFilename
							else:
								from_f = from_f[0]
								#print "Using existing fromFile."

							rel = from_f.relationships.create("depends", to_f, line_number=item.line_number)

						self.items.task_done()

	
		#close down database
		#print "Closing database"
		if gdb:
			gdb.shutdown()


class communicationDatabaseThread(threading.Thread):

	def __init__(self, items, run_mutex):
		#print "Database thread constructor."
		self.items = items
		self.run_mutex = run_mutex
		threading.Thread.__init__(self)
		self.daemon = True #this is needed so the main python process exits once these are done
		self.start()

	def run(self):
		#IMPORTANT:
		#The python embedded bindings for Neo4j use JPype.  Based on the Neo4j mailing list thread
		#entitled [Neo4j] Java segfaults using paste and Python bindings, the Neo4j Python binding
		#needs to be single threaded.  Thus, waiting to import until the thread is ready and running.
		from neo4j import GraphDatabase

		gdb = None
		index_nodes = None

		try:
			#print "Connecting to database: ",devknowledge.settings.NEO4J_DATABASE
			gdb = GraphDatabase(devknowledge.settings.NEO4J_DATABASE)
		except Exception, e:
			print "Error: ",e.message()

		#create indexes (we only need to do this once, thus why it's outside the main loop)
		with gdb.transaction:
			#create indexes
			if (not gdb.node.indexes.exists("index_nodes")):
				index_nodes = gdb.node.indexes.create("index_nodes")
				#print "Created index_nodes"
			else:
				index_nodes = gdb.node.indexes.get("index_nodes")
				#print "Using existing index_nodes"

		#print "About to start main database consumer thread."
		while self.run_mutex[0] == "True" or not self.items.empty():
			if not self.items.empty():
				#Try to perform insertions in blocks of 10,000, lots of tiny single insertions take a LONG time waiting for database lock
				if self.items.qsize() >= 10000:
					num_process = 10000
					wait = False
				elif self.items.qsize() < 10000 and self.run_mutex[0] == "False":
					num_process = self.items.qsize()
					wait = False
				else:
					wait = True

				if not wait:
					with gdb.transaction:
						print "Queue size: ", str(self.items.qsize())
						for i in range(0, num_process):
							item = self.items.get()

							#create thread node if it doesn't exist
							thread = index_nodes['thread'][item.subject]
							if len(thread) == 0:
								thread = gdb.node(subject=item.subject)
								index_nodes['thread'][item.subject] = thread
								#print "Creating new thread node."
							else:
								thread = thread[0]
								#print "Using existing thread node."

							if item.email is not None:
								#create author node if it doesn't exist (check against email address)
								#email is in lowercase at this point
								author = index_nodes['author'][item.email]
								if len(author) == 0:
									author = gdb.node(author=item.author, knowledge_last_update=str(datetime.now()), email=item.email)
									index_nodes['author'][item.email] = author
									#print "Creating new author node."
								else:
									author = author[0]
									#print "Using existing author node."

								# We know at this point that no relationship exists
								if item.body is None:
									rel = author.relationships.create("communication", thread, epoch=str(item.epoch))
								else:
									rel = author.relationships.create("communication", thread, epoch=str(item.epoch), body=item.body)

						self.items.task_done()


		#close down database
		#print "Closing database"
		if gdb:
			gdb.shutdown()
