#!/usr/bin/python
import hashlib
import os
import urllib2
import time
import reddit
import sys
import re
import cPickle

class SubredditContentManager:
    def __init__(self,content_fetcher,subred,ragent, metadata_dir, ignored_domains=["www.reddit.com"]):
        self.content_fetcher = content_fetcher
        self.subred = subred
        self.ragent = ragent
        self.metadata_dir = metadata_dir
        self.ignored_domains = set(ignored_domains)
    def new_stories(self,nstories=25):
        cnt = 0
        for story in self.ragent.get_subreddit(self.subred).get_top(limit=None):
            if re.findall("://(.*?)/",story.url + "/")[0] in self.ignored_domains:
                continue
            else:
                yield story
    """
    Returns an iterator for the content of upto nstories from this subreddit. if you specify new = True then tries to fetch upto nstories new stories
    """
    def get_subred_content(self,nstories=25,new=False):
        dname = self.metadata_dir + "/" + hashlib.sha1(self.subred).hexdigest()
        fname = dname + "/data"
        data={}
        if os.path.isfile(fname):
            f=open(fname)
            data = cPickle.Unpickler(f).load()
            f.close()
        else:
            if not os.path.isdir(dname):
                os.makedirs(dname) 
            data = {"subreddit":self.subred, "nstories":0,"urls":[]}            
        urls=[]
        tofetch = nstories
        if not new:
            urls = data["urls"][-nstories:]
            tofetch = nstories - len(urls)
        if tofetch > 0:
            for story in self.new_stories(tofetch):
                if story.url:
                    urls.append(story.url)
                    if not story.url in data["urls"]:
                        data["nstories"] = data["nstories"] + 1
                        data["urls"].append(story.url)
        f = open(fname,"w")
        cPickle.Pickler(f).dump(data)
        f.close()
        for url in urls:
            yield self.content_fetcher.fetch(url)

class CachedContentFetcher:
    def __init__(self,storage_dir, retry=3,retry_wait=0.1):
        self.storage_dir = storage_dir
        if not os.path.isdir(storage_dir):
            os.makedirs(self.storage_dir)
        self.retry = retry
        self.retry_wait = retry_wait
    def fetch(self,url):
        fname = self.storage_dir + "/" + hashlib.sha1(url).hexdigest()
        if not os.path.isfile(fname):
            try_cnt = 0
            while try_cnt < self.retry:
                try:
                    content = urllib2.urlopen(url).read()
                    f=open(fname,"w")
                    f.write(content)
                    f.close()
                    break
                except URLError,e:
                    print "Error while fetching URL: %s. Error: %s" % (url,e.reason)
                    time.sleep(self.retry_wait)
            if try_cnt >= self.retry:
                print "Failed to fetch URL: %s" % (url)
                return None
        return filecontents(fname)
def filecontents(fname):
    f=open(fname)
    content = f.read()
    f.close()
    return content
if __name__ == "__main__":
    ragent = reddit.Reddit(user_agent="subreddit-classifier")
    content_fetcher = CachedContentFetcher("./.crawler-data/content/")   
    for subred in sys.argv[1].split(","):
        subred_manager = SubredditContentManager(content_fetcher,subred,ragent, "./.crawler-data/subreddit-data/")
        for content in subred_manager.get_subred_content(new=True):
            print content


