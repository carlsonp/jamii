import os, urllib2

# Update these to append and update local mailing list archives.
mailing_lists = ["gmane.comp.kde.devel.general", "gmane.comp.mozilla.devel.firefox", "gmane.comp.mozilla.devel.platform"]
mailing_list_posts = [66151, 949, 6031]
#####################################

mailing_cache = [0, 0, 0]

if not os.path.exists("gmane"):
	os.makedirs("gmane")

#read cache file if it exists
if os.path.isfile("cache.txt"):
	with open("cache.txt", "r") as f:
		content = f.readlines()
		line_counter = 0
		for line in content:
			mailing_cache[line_counter] = line
			line_counter += 1
	f.close()


#http://gmane.org/export.php
#http://docs.python.org/2.7/howto/urllib2.html
for i in range(0, len(mailing_lists)):
	#process single mailing list
	with open("gmane/"+mailing_lists[i], "a") as f:
		for j in range(int(mailing_cache[i]), mailing_list_posts[i], 1500):
			if (j+1500) > mailing_list_posts[i]:
				#print "http://download.gmane.org/"+mailing_lists[i]+"/"+str(j)+"/"+str(mailing_list_posts[i]+1)
				response = urllib2.urlopen("http://download.gmane.org/"+mailing_lists[i]+"/"+str(j)+"/"+str(mailing_list_posts[i]+1))
			else:
				#print "http://download.gmane.org/"+mailing_lists[i]+"/"+str(j)+"/"+str(j+1500)
				response = urllib2.urlopen("http://download.gmane.org/"+mailing_lists[i]+"/"+str(j)+"/"+str(j+1500))
			f.write(response.read()) #note, the resulting file is NOT utf-8 encoded
			print "Percent done: %.2f %%" % float(float(j)/float(mailing_list_posts[i]) * 100)
	f.close()


#write cache file
with open("cache.txt", "w") as f:
	for post in mailing_list_posts:
		f.write(str(post) + "\n")
f.close()
