#!/usr/bin/python
import hashlib
import os
import urllib2
import time
import reddit
import sys
import re
import utils
class SubredditContentManager:
    def __init__(self,subred,ragent=None, metadata_dir="./.crawler-data/subreddit-data/", ignored_domains=["www.reddit.com","imgur.com","www.imgur.com","www.youtube.com"]):
        self.subred = subred
        self.ragent = ragent
        self.metadata_dir = metadata_dir
        self.ignored_domains = set(ignored_domains)
        dname = self.metadata_dir + "/" + utils.get_hash(self.subred)
        if not os.path.isdir(dname):
            os.makedirs(dname) 
        self.fname = dname + "/data"

    def new_stories(self,nstories=25):
        cnt = 0
        for story in self.ragent.get_subreddit(self.subred).get_top(limit=None):
            if re.findall("://(.*?)/",story.url + "/")[0] in self.ignored_domains:
                continue
            else:
                yield story

    def load_data(self):
        if os.path.isfile(self.fname):
            return utils.unpickled_content(self.fname)
        else:
            data={"subreddit":self.subred, "nstories":0,"urls":[]}
            self.save_data(data)
            return data

    def save_data(self,data):
        utils.save_pickled(self.fname,data)
    
    def get_urls(self,limit=25):
        data=self.load_data()
        return data["urls"][:limit]
    """
    Returns an iterator for the content of upto nstories from this subreddit. if you specify new = True then tries to fetch upto nstories new stories
    """
    def get_subred_content(self,nstories=25,new=False,content_fetcher=None):
        data=self.load_data()
        urls=[]
        tofetch = nstories
        print "nstories to fetch = %d" % nstories
        if not new:
            urls = data["urls"][-nstories:]
            tofetch = nstories - len(urls)
        print " tofetch = %d" % tofetch
        if tofetch > 0:
            print "Fetching new stories from reddit"
            for story in self.new_stories(tofetch):
                if story.url:
                    urls.append(story.url)
                    if not story.url in data["urls"]:
                        data["nstories"] = data["nstories"] + 1
                        data["urls"].append(story.url)
        self.save_data(data)
        print "URLs = %s" % "\n".join(urls)
        for url in urls:
            yield (url,content_fetcher.fetch(url))

class CachedContentFetcher:
    def __init__(self,storage_dir="./.crawler-data/content/", retry=3,retry_wait=0.1):
        self.storage_dir = storage_dir
        if not os.path.isdir(storage_dir):
            os.makedirs(self.storage_dir)
        self.retry = retry
        self.retry_wait = retry_wait

    def fetch(self,url):
        fname = self.storage_dir + "/" + utils.get_hash(url)
        if not os.path.isfile(fname):
            try_cnt = 0
            while try_cnt < self.retry:
                try:
                    print "Fetching: %s" % url
                    content = urllib2.urlopen(url).read()
                    f=open(fname,"w")
                    f.write(content)
                    f.close()
                    break
                except urllib2.URLError,e:
                    print "Error while fetching URL: %s. Error: %s" % (url,e.reason)
                    time.sleep(self.retry_wait)
            if try_cnt >= self.retry:
                print "Failed to fetch URL: %s" % (url)
                return None
        return utils.filecontents(fname)

class NGramContentFetcher(CachedContentFetcher):
    def __init__(self,storage_dir="./.crawled-data/content",words_preprocessor=None,retry=3,retry_wait=0.1,n=1):
        CachedContentFetcher.__init__(self,storage_dir,retry,retry_wait)
        self.words_preprocessor = words_preprocessor
        self.n=n
    """
    Fetch a word split n-grammed representation of the url's content
    """
    def fetch(self,url):
        return self.fetch_ngram(url,ng=self.n)

    def fetch_ngram(self,url,ng=1):
        fname = "%s/%s.words_%d_gram" % (self.storage_dir,hashlib.sha1(url).hexdigest(),ng)
        print fname
        if not os.path.isfile(fname):
            if ng > 1:
                words = self.fetch_ngram(url,ng=1)
                ngrams = self.make_n_gram(words,ng)
                utils.save_pickled(fname,ngrams)
            else:
                words=self.word;s_preprocessor.process(CachedContentFetcher.fetch(self,url))
                utils.save_pickled(fname,words)
        return utils.unpickled_content(fname)

    def make_n_gram(self,words,n):
        ngrams=[]
        for i in range(0,len(words)-n):
            j=i+n
            ngrams.append("_".join(words[i:j]))
        return ngrams

                                
if __name__ == "__main__":
    ragent = reddit.Reddit(user_agent="subreddit-classifier")
    words_preprocessor = ChainedPreprocessor([HtmlPreprocessor(),WordSplitterPreprocessor(),StemmerPreprocessor(),StopWordRemovePreprocessor()])
    content_fetcher = CachedContentFetcher()
    for subred in sys.argv[1].split(","):
        subred_manager = SubredditContentManager(subred,ragent)
        for url,content in subred_manager.get_subred_content(new=True,content_fetcher=content_fetcher):
            print content
