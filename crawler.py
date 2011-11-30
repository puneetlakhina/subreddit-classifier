#!/usr/bin/python
import hashlib
import os
import urllib2
import time
import reddit
import sys
import re
import cPickle
from BeautifulSoup import BeautifulSoup
from stemming.porter2 import stem
class SubredditContentManager:
    def __init__(self,subred,ragent=None, metadata_dir="./.crawler-data/subreddit-data/", ignored_domains=["www.reddit.com","imgur.com","www.imgur.com","www.youtube.com"]):
        self.subred = subred
        self.ragent = ragent
        self.metadata_dir = metadata_dir
        self.ignored_domains = set(ignored_domains)
        dname = self.metadata_dir + "/" + hashlib.sha1(self.subred).hexdigest()
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
            return unpickled_content(self.fname)
        else:
            data={"subreddit":self.subred, "nstories":0,"urls":[]}
            self.save_data(data)
            return data

    def save_data(self,data):
        save_pickled(self.fname,data)
    
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
        self.save_data(data)
        for url in urls:
            yield content_fetcher.fetch(url)

class CachedContentFetcher:
    def __init__(self,storage_dir="./.crawler-data/content/", retry=3,retry_wait=0.1):
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
                save_pickled(fname,ngrams)
            else:
                words=self.words_preprocessor.process(CachedContentFetcher.fetch(self,url))
                save_pickled(fname,words)
        return unpickled_content(fname)

    def make_n_gram(self,words,n):
        ngrams=[]
        for i in range(0,len(words)-n):
            j=i+n
            ngrams.append("_".join(words[i:j]))
        return ngrams

class ChainedPreprocessor:
    def __init__(self,processor_chain):
        self.processor_chain = processor_chain
    def process(self,content):
        if not content:
            print "No content"
            return;
        for processor in self.processor_chain:
            content = processor.process(content)
        return content
"""
Converts HTML content of a page into text elements only
"""
class HtmlPreprocessor:
    def process(self,content):
        soup = BeautifulSoup(content)
        body = soup.body
        if not body or not body.contents:
            return
        #remove img tags
        #remove script tags
        #remove style tags
        [t.extract() for t in body.findAll(re.compile("^(img)|(script)|(style)|(object)|(video)$"))]
        return ' '.join(body(text = lambda(x): len(x.strip()) > 1))
"""
Split the text into a list of individual words
"""
class WordSplitterPreprocessor: 
    def process(self,content):
        return re.split("[^a-zA-Z0-9']+",content)
"""
Removes the stop words from a list of words
"""
class StopWordRemovePreprocessor:
    stop_words=set([word.strip() for word in "a's, able, about, above, according, accordingly, across, actually, after, afterwards, again, against, ain't, all, allow, allows, almost, alone, along, already, also, although, always, am, among, amongst, an, and, another, any, anybody, anyhow, anyone, anything, anyway, anyways, anywhere, apart, appear, appreciate, appropriate, are, aren't, around, as, aside, ask, asking, associated, at, available, away, awfully, be, became, because, become, becomes, becoming, been, before, beforehand, behind, being, believe, below, beside, besides, best, better, between, beyond, both, brief, but, by, c'mon, c's, came, can, can't, cannot, cant, cause, causes, certain, certainly, changes, clearly, co, com, come, comes, concerning, consequently, consider, considering, contain, containing, contains, corresponding, could, couldn't, course, currently, definitely, described, despite, did, didn't, different, do, does, doesn't, doing, don't, done, down, downwards, during, each, edu, eg, eight, either, else, elsewhere, enough, entirely, especially, et, etc, even, ever, every, everybody, everyone, everything, everywhere, ex, exactly, example, except, far, few, fifth, first, five, followed, following, follows, for, former, formerly, forth, four, from, further, furthermore, get, gets, getting, given, gives, go, goes, going, gone, got, gotten, greetings, had, hadn't, happens, hardly, has, hasn't, have, haven't, having, he, he's, hello, help, hence, her, here, here's, hereafter, hereby, herein, hereupon, hers, herself, hi, him, himself, his, hither, hopefully, how, howbeit, however, i'd, i'll, i'm, i've, ie, if, ignored, immediate, in, inasmuch, inc, indeed, indicate, indicated, indicates, inner, insofar, instead, into, inward, is, isn't, it, it'd, it'll, it's, its, itself, just, keep, keeps, kept, know, knows, known, last, lately, later, latter, latterly, least, less, lest, let, let's, like, liked, likely, little, look, looking, looks, ltd, mainly, many, may, maybe, me, mean, meanwhile, merely, might, more, moreover, most, mostly, much, must, my, myself, name, namely, nd, near, nearly, necessary, need, needs, neither, never, nevertheless, new, next, nine, no, nobody, non, none, noone, nor, normally, not, nothing, novel, now, nowhere, obviously, of, off, often, oh, ok, okay, old, on, once, one, ones, only, onto, or, other, others, otherwise, ought, our, ours, ourselves, out, outside, over, overall, own, particular, particularly, per, perhaps, placed, please, plus, possible, presumably, probably, provides, que, quite, qv, rather, rd, re, really, reasonably, regarding, regardless, regards, relatively, respectively, right, said, same, saw, say, saying, says, second, secondly, see, seeing, seem, seemed, seeming, seems, seen, self, selves, sensible, sent, serious, seriously, seven, several, shall, she, should, shouldn't, since, six, so, some, somebody, somehow, someone, something, sometime, sometimes, somewhat, somewhere, soon, sorry, specified, specify, specifying, still, sub, such, sup, sure, t's, take, taken, tell, tends, th, than, thank, thanks, thanx, that, that's, thats, the, their, theirs, them, themselves, then, thence, there, there's, thereafter, thereby, therefore, therein, theres, thereupon, these, they, they'd, they'll, they're, they've, think, third, this, thorough, thoroughly, those, though, three, through, throughout, thru, thus, to, together, too, took, toward, towards, tried, tries, truly, try, trying, twice, two, un, under, unfortunately, unless, unlikely, until, unto, up, upon, us, use, used, useful, uses, using, usually, value, various, very, via, viz, vs, want, wants, was, wasn't, way, we, we'd, we'll, we're, we've, welcome, well, went, were, weren't, what, what's, whatever, when, whence, whenever, where, where's, whereafter, whereas, whereby, wherein, whereupon, wherever, whether, which, while, whither, who, who's, whoever, whole, whom, whose, why, will, willing, wish, with, within, without, won't, wonder, would, would, wouldn't, yes, yet, you, you'd, you'll, you're, you've, your, yours, yourself, yourselves, zero".split(",")])
    def process(self,content):
        return filter(lambda x:x.strip() and x not in StopWordRemovePreprocessor.stop_words,content)
        
"""
Stem the list of words using porter2
"""
class StemmerPreprocessor:
    def process(self,contents):
        return map(stem,contents)

def filecontents(fname):
    f=open(fname)
    content = f.read()
    f.close()
    return content

def save_pickled(fname,content):
    f = open(fname,"w")
    cPickle.Pickler(f).dump(content)
    f.close()

def unpickled_content(fname):
    f=open(fname)
    content=cPickle.Unpickler(f).load()
    f.close()
    return content

                                
if __name__ == "__main__":
    ragent = reddit.Reddit(user_agent="subreddit-classifier")
    words_preprocessor = ChainedPreprocessor([HtmlPreprocessor(),WordSplitterPreprocessor(),StemmerPreprocessor(),StopWordRemovePreprocessor()])
    content_fetcher = CachedContentFetcher()   
    for subred in sys.argv[1].split(","):
        subred_manager = SubredditContentManager(subred,ragent, "./.crawler-data/subreddit-data/")
        for content in subred_manager.get_subred_content(new=True,content_fetcher=content_fetcher):
            print content
