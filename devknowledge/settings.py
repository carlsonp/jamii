# Django settings for devknowledge project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'django',                      # Or path to database file if using sqlite3.
        'USER': 'django',                      # Not used with sqlite3.
        'PASSWORD': 'djang0',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}


# version control repositories folder
VERSION_CONTROL_REPOS = "/home/user/src/"

# exponential decay amount for knowledge algorithm
EXPONENTIAL_DECAY = 0.01

# Neo4j graph.db location
NEO4J_DATABASE = "/home/user/installs/neo4j-community-2.0.4/data/graph.db"

# mbox archived emails
MBOX_ARCHIVES = "/home/user/Django/devknowledge/mailinglist/"

# Neo4j server address/ip for the REST client
NEO4J_SERVER = "http://localhost:7474/db/data/"

#Cypher session (http://book.py2neo.org/en/latest/cypher/#id2)
NEO4J_SESSION = "http://localhost:7474"

# Max graph.db size (in Megabytes), this ensures we don't go too crazy on the output in case something goes wrong
# This takes some serious time to check so it's best to leave it off for long runs
#NEO4J_DATABASE_SIZE_LIMIT = 10240 # 10 GB

# Number of concurrent threads to spawn for processing (probably best to set this to the number of cores available)
CONCURRENT_THREADS = 4


# only calculate knowledge for the following file extension endings (make sure none are upper-case)
WHITELIST_EXTENSIONS = [".cpp", ".h", ".c", ".hpp", ".hh", ".inl", ".in"]

# Don't traverse the following directories when calculating knowledge
BLACKLIST_FOLDERS = [".git", ".hg"]


# Calculate knowledge for the following project folders
# gecko-dev, kdelibs, etc....
PROJECT_FOLDERS = ["projectname"]


# Max depth for recursive processing for run_processing.py
# Set to 0 for unlimited depth
MAX_RECURSIVE_DEPTH = 10


# extra include locations, delineate by commas
# This is used by clang to find included files
#INCLUDE_PATHS = ["/home/user/src/gecko-dev/"]
INCLUDE_PATHS = []

# Mailing list MBOX files
# used by run_communication.py to parse mailing lists, delineate by commas
MAILING_LIST_FILES = ["gmane.comp.mozilla.devel.builds", "gmane.comp.mozilla.devel.firefox"]


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en//ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
	'/home/user/Django/devknowledge/static/',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5d-1n#$)cbpa*flrdy1@$q0iaqsq244c&amp;3x281bqyrj-dt6($i'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'devknowledge.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'devknowledge.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
	'sourcecodeknowledge',
	'django_extensions',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

#New for Django 1.7
#https://docs.djangoproject.com/en/dev/releases/1.6/#new-test-runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
