Jamii
-----



Dependencies

pygments - http://pygments.org
Version 2.0.1
sudo pip install pygments

Git - http://www.git-scm.com
installed and available from the commandline

Neo4j verion 2.0.X (tested with 2.04)


Make sure this is uncommented:
allow_store_upgrade=true
in conf/Neo4j.properties

Django (Requires 1.6 or greater)

sudo pip install django

python-magic

sudo pip install python-magic

py2neo

https://pypi.python.org/pypi/py2neo/1.6.1

Install this specific version.

sudo python setup.py install


sudo pip install django_extensions

sudo pip install werkzeug

Python Clang bindings

Add to /etc/apt/sources.list file:

#for version 3.5 of LLVM/CLANG
deb http://llvm.org/apt/utopic/ llvm-toolchain-utopic main
deb-src http://llvm.org/apt/utopic/ llvm-toolchain-utopic main

sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 15CF4D18AF4F7421

sudo apt-get update

sudo apt-get install clang-3.5 python-clang-3.5 libclang-3.5-dev

Setup a MySQL user and database (see settings.py file)

This sets up the database:
python manage.py syncdb

Plain server:
python manage.py runserver

Server with werkzeug debugger:
python manage.py runserver_plus


In settings.py, make sure the following variables are set.

VERSION_CONTROL_REPOS - sourcecode repos, make sure read permissions are set
EXPONENTIAL_DECAY - numerical decimal value between 0 and 1
STATICFILES_DIRS - location where CSS, javascript, and images reside
RECURSIVE_LIMIT - integer value defining how far back in history we go before backing off
NEO4J_DATABASE - Neo4j database location
MBOX_ARCHIVES - this is where the processing step looks for mbox files
SECRET_KEY - make sure to change this value as it's important for security reasons

There are additional settings in this file that are optional that you probably
will want to change as well.


Deployment (Apache2):

Debian/Ubuntu package: libapache2-mod-wsgi

https://code.google.com/p/modwsgi/wiki/QuickConfigurationGuide

https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/modwsgi/


/tmp/ directory setup and write permission.

Running:

Make sure you run the scripts (see processing directory) in the following order.

Neo4j should be stopped.  Database is empty.

*Make sure the database graph.db folder does not exist, sometimes this causes errors.*

-s is the hash you want to start processing from.  This script runs clang
and saves all subsequent data about the technical structure to files in /tmp/devknowledge/
These are later processed by the next script.  The reason these are split out is because
there was some sort of weird crashing that happened when trying to use both the python
clang bindings and Neo4j at the same time.  This runs on a single thread.

python run_code_impact_file.py -s 0a8c370a6dcd470e1c84191e1a7ac1fb1fc7a78e

-s is the hash you want to start processing from.  Make sure it's the same as the one you
picked above.  This runs on a single thread.

python run_code_impact_save.py -s 0a8c370a6dcd470e1c84191e1a7ac1fb1fc7a78e

This saves files and developer names/line knowledge to the database.  This is
multi-threaded and should be run on a fast machine with many cores.

python run_processing.py

Parses through #includes to find dependencies.  This should probably be switched
over to using Clang.

python run_dependencies.py

This parses a mbox file with the same name as the project and saves the resulting
communication information.

python run_communication.py

Now start the database and it will upgrade from 1.9 to 2.0.X

Lastly, run the processing to calculate congruence.  This may take awhile.

python run_congruence.py

The final results will be here:

http://localhost:8000/sourcecodeknowledge/project/yourprojectnamehere/


Debugging:

django-extensions has a profiling tool built-in
python manage.py runprofileserver --kcachegrind --prof-path=/home/username/Desktop/profile-data/
Then use KCacheGrind to open the file.

Or to debug the processing file, use cProfile built-in to Python.

python -m cProfile -o profile.prof run_processing.py

Then you can use something like runsnakerun to visualize.

sudo aptitude install runsnakerun OR sudo pip install runsnakerun

runsnake profile.prof


Python embedded bindings (currently dead link as this is no longer maintained)
http://docs.neo4j.org/drivers/python-embedded/snapshot

sudo aptitude install python-jpype

The Python embedded bindings need to be updated for Neo4j 2.0

Make sure to install this specific version.

https://pypi.python.org/pypi/neo4j-embedded/1.9.c2

sudo python setup.py install


Make sure to set the JAVA_HOME variable, I set it via the .bashrc file
export JAVA_HOME=/usr/lib/jvm/java-8-oracle
To check the value: echo $JAVA_HOME


Testing and counts

Count of all nodes
start a=node(*) return count(a);

Count of all relationships
start a=relationship(*) return count(a);

Number of developers
start a=node(*) where has(a.email) return count(a);

Number of individual files
start a=node(*) where has(a.filename) return count(a);

Number of individual functions
start a=node(*) where has(a.function) return count(a);

Number of mailing list threads
start a=node(*) where has(a.subject) return count(a);

Number of commit hash objects:
start a=node(*) where has(a.hash) return count(a);

Number of include relationships
start a=node(*) match a-[r:include]->() return count(r);

Number of depends relationships
start a=node(*) match a-[r:depends]->() return count(r);

Number of calls relationships
start a=node(*) match a-[r:calls]->() return count(r);

Number of has relationships
start a=node(*) match a-[r:has]->() return count(r);

Number of knowledge lines used for calculating expertise
start a=node(*) match a-[r:knowledge]->() return count(r);

Number of expertise calculations
start a=node(*) match a-[r:expertise]->() return count(r);

Number of file_score edges
start a=node(*) match a-[r:file_score]->() return count(r);

Number of interpersonal_score edges
start a=node(*) match a-[r:interpersonal_score]->() return count(r);

Number of communication edges
start a=node(*) match a-[r:communication]->() return count(r);

Number of impact edges
start a=node(*) match a-[r:impact]->() return count(r);


