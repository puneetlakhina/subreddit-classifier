import crawler
import os
from preprocessor import *
import utils
import math
import getopt
import sys
import reddit
class NaiveBayesClassifier:
    def __init__(self, cache_dir="./.classifiers-data/naive-bayes"):
        self.cache_dir = cache_dir
        if not os.path.isdir(cache_dir):
            os.makedirs(self.cache_dir)
        self.preprocessor = ChainedPreprocessor([HtmlPreprocessor(),WordSplitterPreprocessor(),StemmerPreprocessor(),StopWordRemovePreprocessor()])
        self.labels_metadata_fname = self.cache_dir + "/labels.metadata"
        self.labels_metadata = utils.read_cached(self.labels_metadata_fname, lambda:{})
    def save_metadata(self):
        utils.save_pickled(self.labels_metadata_fname, self.labels_metadata)
    def train(self, source_url, content, label):
        docid = utils.get_hash(source_url)
        words = utils.read_cached(self.cache_dir + "/" + docid ,self.preprocessor.process, content)
        if not words:
            return
        #Now make sure we havent already used this example for this label
        self.labels_metadata.setdefault(label, {"doc_ids":[] , "word_doc_counts": {} })
        label_metadata = self.labels_metadata[label]
        if docid in label_metadata["doc_ids"]:
            #We have already processed this url
            return;
        else:
            label_metadata["doc_ids"].append(docid)
            words = set(words)
            for word in words:
                label_metadata["word_doc_counts"].setdefault(word,1)
                label_metadata["word_doc_counts"][word] = label_metadata["word_doc_counts"][word] + 1
        self.save_metadata()
    def classify(self, url, content):
        words = utils.read_cached(self.cache_dir + "/" + utils.get_hash(url) ,self.preprocessor.process, content)
        argmax = {"label":None, "prob":None}
        for label,label_data in self.labels_metadata.iteritems():
            prob_sum=0.0
            for word in words:
                tot_doc_count = len(label_data["doc_ids"])
                if word in label_data["word_doc_counts"]:
                    prob_sum = prob_sum + math.log(float(label_data["word_doc_counts"][word])/tot_doc_count)
            
            if not argmax["prob"] or prob_sum > argmax["prob"]:
                argmax["prob"] = prob_sum
                argmax["label"] = label
        print argmax
help_str="%s -t training_set_size\n-c cross_validation_set_size\n-s subreddits(comma separated).May be specified multiple times\n-h help\n-v Verbose\n" % (sys.argv[0])
verbose=False
def usage(extra_str=""):
    global help_str
    sys.stderr.write(extra_str + "\n")
    sys.stderr.write(help_str)
    exit(1)
def debugop(s):
    if verbose:
        print str(s + "\n")
if __name__ == "__main__":
    ts = 0
    cv = 0
    subreddits=[]
    try:
        opts,args = getopt.getopt(sys.argv[1:],"t:c:s:hv")
        for opt,val in opts:
            if opt == "-t":
                ts = int(val)
            elif opt == "-c":
                cv = int(val)
            elif opt == "-s":
                subreddits.extend(map(lambda x:x.strip(), val.split(",")))
            elif opt == "-h":
                usage()
            elif opt == "-v":
                verbose=True
        if ts == 0:
            usage("No Training set size specified")
        if cv == 0:
            usage("No Cross validation set size specified")
        if len(subreddits) == 0:
            usage("No subreddits specified\n")
        classifier = NaiveBayesClassifier()
        content_fetcher = crawler.CachedContentFetcher()
        ragent = reddit.Reddit(user_agent="subreddit-classifier")
        for subreddit in subreddits:    
            debugop("Training for subreddit: %s" % subreddit)
            subred_manager = crawler.SubredditContentManager(subreddit,ragent)
            for url,content in subred_manager.get_subred_content(content_fetcher=content_fetcher,nstories=ts):
                debugop("URL:%s" % str(url)) 
                classifier.train(url, content, subreddit)
        debugop("Cross validation");
        for subreddit in subreddits:
            subred_manager = crawler.SubredditContentManager(subreddit,ragent)
            for url,content in subred_manager.get_subred_content(content_fetcher=content_fetcher,nstories=cv,new=True):
                print "Real Class:%s" % subreddit
                classifier.classify(url, content)
    except getopt.GetoptError, err:
        usage()
    
