# urls.py

from django.conf.urls import patterns, url

from sourcecodeknowledge import views


urlpatterns = patterns('',
	# ex: /sourcecodeknowledge/
	url(r'^$', views.index, name='index'),
	# ex: /sourcecodeknowledge/project/about/
	url(r'^project/(?P<project>([^/])+)/about/$', views.about, name="about"),
	# ex: /sourcecodeknowledge/project/myproject/
	url(r'^project/(?P<project>([^/])+)/$', views.project, name='project'),
	# ex: /sourcecodeknowledge/project/myproject/expertise/
	url(r'^project/(?P<project>([^/])+)/expertise/$', views.expertise, name='expertise'),
	# ex: /sourcecodeknowledge/project/myproject/codeimpact/
	url(r'^project/(?P<project>([^/])+)/codeimpact/$', views.codeimpact, name='codeimpact'),
	# ex: /sourcecodeknowledge/project/myproject/getcommits/
	url(r'^project/(?P<project>([^/])+)/getcommits/$', views.getcommits, name='getcommits'),
	# ex: /sourcecodeknowledge/project/myproject/codeimpactgraph/
	url(r'^project/(?P<project>([^/])+)/codeimpactgraph/$', views.codeimpactgraph, name='codeimpactgraph'),
	# ex: /sourcecodeknowledge/project/myproject/commit/hash/
	url(r'^project/(?P<project>([^/])+)/commit/(?P<commit>.*)/$', views.commit, name='commit'),
	# ex: /sourcecodeknowledge/project/myproject/expertise/subfolder/myfolder/
	url(r'^project/(?P<project>([^/])+)/expertise/subfolder/(?P<subfolder>.+)/$', views.expertise, name='expertise'),
	# ex: /sourcecodeknowledge/project/myproject/expertise/file/subfolders/file.txt
	url(r'^project/(?P<project>([^/])+)/expertise/file/(?P<file>.+)/$', views.file, name='file'),
	# ex: /sourcecodeknowledge/project/myproject/communication/
	url(r'^project/(?P<project>([^/])+)/communication/$', views.communicationindex, name='communicationindex'),
	# ex: /sourcecodeknowledge/project/myproject/developers/
	url(r'^project/(?P<project>([^/])+)/developers/$', views.developers, name='developers'),
	# ex: /sourcecodeknowledge/project/myproject/finddevelopers/developer
	url(r'^project/(?P<project>([^/])+)/finddevelopers/(?P<developer>.+)/$', views.finddevelopers, name='finddevelopers'),
	# ex: /sourcecodeknowledge/project/myproject/developers/letter/unknown/page/3/
	url(r'^project/(?P<project>([^/])+)/developers/letter/(?P<letter>.+)/page/(?P<page>[0-9]+)/$', views.developers, name='developers'),
	# ex: /sourcecodeknowledge/project/myproject/searchdevelopers/
	url(r'^project/(?P<project>([^/])+)/searchdevelopers/$', views.searchdevelopers, name='searchdevelopers'),
	# ex: /sourcecodeknowledge/project/myproject/congruence/developer/dev_email/
	url(r'^project/(?P<project>([^/])+)/congruence/developer/(?P<dev_email>.*)/$', views.congruence, name='congruence'),
)
