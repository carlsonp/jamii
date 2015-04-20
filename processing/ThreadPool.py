from Queue import Queue
from threading import Thread

from time import sleep

#http://code.activestate.com/recipes/577187-python-thread-pool/

class Worker(Thread):

	def __init__(self, tasks):
		#print "Initializing worker thread."
		Thread.__init__(self)
		self.tasks = tasks
		self.daemon = True #this is needed so the main python process exits once these are done
		self.start()

	def run(self):
		while True:
			func, args, kargs = self.tasks.get()
			try:
				#print "About to start function passed."
				func(*args, **kargs)
			except Exception, e:
				print e
			#print "Finishing function call, task done."
			self.tasks.task_done()


class ThreadPool:

	def __init__(self, num_threads):
		#print "Initializing thread pool."
		self.tasks = Queue(int(num_threads))
		for _ in range(num_threads):
			Worker(self.tasks)

	def add_task(self, func, *args, **kargs):
		#print "Adding task."
		#This will block until something in the Queue opens up, thus limiting
		#the number of threads to that specified by the user.
		self.tasks.put((func, args, kargs))
		#sleep(0) #TODO: would this help in yielding to other threads?

	def wait_completion(self):
		self.tasks.join()
