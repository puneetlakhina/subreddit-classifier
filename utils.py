import cPickle
import hashlib
import os
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
"""
If file fname exists unpickle the contents and return it. If it doesnt exist, 
call fn with the arguments and store a pickled representation of the return value in fname. Also return the result of call to fn
"""
def read_cached(fname, fn, *args):
    if not os.path.isfile(fname):
        result = fn(*args)
        save_pickled(fname, result)
        return result
    else:
        return unpickled_content(fname)
"""
Returns the hexdigest of the content
"""
def get_hash(content):
    return hashlib.sha1(content).hexdigest()
