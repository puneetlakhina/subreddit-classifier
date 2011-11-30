#!/usr/bin/python
import crawler
import sys
import reddit
ragent=reddit.Reddit(user_agent="subreddit-classifier") 
words_preprocessor = crawler.ChainedPreprocessor([crawler.HtmlPreprocessor(),crawler.WordSplitterPreprocessor(),crawler.StemmerPreprocessor(),crawler.StopWordRemovePreprocessor()])
ngram_fetcher=crawler.NGramContentFetcher(n=3,words_preprocessor=words_preprocessor)
subred_manager = crawler.SubredditContentManager(sys.argv[1],ragent, "./.crawler-data/subreddit-data/") 
for content in subred_manager.get_subred_content(nstories=2,content_fetcher=ngram_fetcher):
    print content  
