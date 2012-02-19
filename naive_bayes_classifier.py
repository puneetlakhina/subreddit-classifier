import crawler
import os
from preprocessor import *
import utils
import math
import getopt
import sys
import reddit
import logging
logger = logging.getLogger(__name__)

class NaiveBayesClassifier:
    def __init__(self, cache_dir="./.classifiers-data/naive-bayes", missing_value_prob=0.0001):
        self.cache_dir = cache_dir
        if not os.path.isdir(cache_dir):
            os.makedirs(self.cache_dir)
        self.preprocessor = ChainedPreprocessor([HtmlPreprocessor(),WordSplitterPreprocessor(),StemmerPreprocessor(), WordDeduper(), NumeralRemover(), StopWordRemovePreprocessor()])
        self.labels_metadata_fname = self.cache_dir + "/labels.metadata"
        self.labels_metadata = utils.read_cached(self.labels_metadata_fname, lambda:{})
        self.missing_prob = missing_value_prob
    def save_metadata(self):
        utils.save_pickled(self.labels_metadata_fname, self.labels_metadata)
    def retrain_label(self, label):
        """
        Retrain using the existing data. for this label
        """
        if not label in self.labels_metadata:
            return
        docids = [].extend(self.labels_metadata[label]["doc_ids"])
        self.__clear_label(label)
        for doc_id in doc_ids:
            words = utils.read_cached(self.cache_dir + "/" + docid , [])
            self.__train_with_words(doc_id,words, label)
    def __clear_label(self, label):
        """
        Clear the data for this label
        """
        self.labels_metadata[label]["word_doc_counts"] = {}
        self.labels_metadata[label]["doc_ids"] = []

    def __init_label(self, label):
        """
        Initialize the label's metadata if its not already present
        """
        self.labels_metadata.setdefault(label, {"doc_ids":[] , "word_doc_counts": {} })

    def __train_with_words(self, docid, words, label):
        if not words:
            return
        self.__init_label(label)
        #Now make sure we havent already used this example for this label
        label_metadata = self.labels_metadata[label]
        if docid in label_metadata["doc_ids"]:
            #We have already processed this url
            return;
        else:
            label_metadata["doc_ids"].append(docid)
            for word in words:
                label_metadata["word_doc_counts"].setdefault(word,1)
                label_metadata["word_doc_counts"][word] = label_metadata["word_doc_counts"][word] + 1
        self.save_metadata()

    def train(self, source_url, content, label):
        docid = utils.get_hash(source_url)
        words = utils.read_cached(self.cache_dir + "/" + docid ,self.preprocessor.process, content)
        self.__train_with_words(docid, words, label)
    def classify(self, url, content):
        words = utils.read_cached(self.cache_dir + "/" + utils.get_hash(url) ,self.preprocessor.process, content)
        argmax = {"label":None, "prob":None}
        probs = {}
        for label,label_data in self.labels_metadata.iteritems():
            prob_sum=0.0
            for word in words:
                tot_doc_count = len(label_data["doc_ids"])
                if word in label_data["word_doc_counts"]:
                    prob = math.log(float(label_data["word_doc_counts"][word])/tot_doc_count)
                    logger.debug("Found word: %s. Prob %f. Count in the %s data: %d" % (word,prob, label, label_data["word_doc_counts"][word]))
                    prob_sum = prob_sum + prob
                else:
                    prob_sum = prob_sum + math.log(self.missing_prob)
            probs[label] = prob_sum
            if not argmax["prob"] or prob_sum > argmax["prob"]:
                argmax["prob"] = prob_sum
                argmax["label"] = label
        logger.debug("URl: %s, debuginfo: %s " % (url,str(probs)))
        return argmax
    def debug_info(self, label):
        return self.labels_metadata[label]
help_str=sys.argv[0] + """
-t training_set_size
-c cross_validation_set_size
-s subreddits(comma separated).May be specified multiple times
-d Print debug info about the subreddits classification data
-r Retrain instead of fetching new content for training. 
-l Log Level (d/i/w/e/c) -> (DEBUG/INFO/WARNING/ERROR/CRITICAL). Default info
-h help
"""
def usage(extra_str=""):
    global help_str
    sys.stderr.write(extra_str + "\n")
    sys.stderr.write(help_str)
    exit(1)
if __name__ == "__main__":
    ts = 0
    cv = 0
    subreddits=[]
    debug_info = False
    retrain=False
    loglevel = logging.INFO
    try:
        opts,args = getopt.getopt(sys.argv[1:],"rt:c:s:dhvl:")
        for opt,val in opts:
            if opt == "-t":
                ts = int(val)
            elif opt == "-c":
                cv = int(val)
            elif opt == "-s":
                subreddits.extend(map(lambda x:x.strip(), val.split(",")))
            elif opt == "-h":
                usage()
            elif opt == "-d":
                debug_info = True
            elif opt == "-r":
                retrain = True
            elif opt == "-l":
                if val == "i":
                    loglevel=logging.INFO
                elif val == "d":
                    loglevel=logging.DEBUG
                elif val == "w":
                    loglevel=logging.WARNING
                elif val == "e":
                    loglevel=logging.ERROR
                elif val == "c":
                    loglevel=logging.CRITICAL
                else:
                    usage("Improper logging level:" + val)
        logging.basicConfig(level=loglevel)
        if ts == 0 and cv == 0 and not debug_info:
            usage("One of training/cross validation set size must be specified. Or debug info flag must be enabled")
        if ts > 0 and retrain:
            usage("Both retrain and trainig set size cant be specified")
        if len(subreddits) == 0:
            usage("No subreddits specified\n")
        classifier = NaiveBayesClassifier()
        content_fetcher = crawler.CachedContentFetcher()
        ragent = reddit.Reddit(user_agent="subreddit-classifier")
        if ts > 0:
            for subreddit in subreddits:    
                logger.debug("Training for subreddit: %s" % subreddit)
                subred_manager = crawler.SubredditContentManager(subreddit,ragent)
                for url,content in subred_manager.get_subred_content(content_fetcher=content_fetcher,nstories=ts):
                    logging.debug("URL:%s" % str(url)) 
                    classifier.train(url, content, subreddit)
        if retrain:
            for subreddit in subreddits:
                print classifier.retrain(subreddit)
        if debug_info:
            for subreddit in subreddits:
                print classifier.debug_info(subreddit)
        if cv > 0:
            logger.debug("Cross validation");
            for subreddit in subreddits:
                subred_manager = crawler.SubredditContentManager(subreddit,ragent)
                for url,content in subred_manager.get_subred_content(content_fetcher=content_fetcher,nstories=cv,new=True):
                    print "Real Class:%s url:%s Classification: %s" % (subreddit,url, str(classifier.classify(url, content)))
    except getopt.GetoptError, err:
        usage()
    
