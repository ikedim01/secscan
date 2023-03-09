# AUTOGENERATED! DO NOT EDIT! File to edit: 00_utils.ipynb (unless otherwise specified).

__all__ = ['boto3_available', 'setStockDataRoot', 'stockDataRoot', 'requestUrl', 'setSecUserAgent', 'secIndexUrl',
           'appendSpace', 'getCombTextRec', 'getCombSoupText', 'prTree', 'prAllTagNames', 'downloadSecUrl',
           'secUrlPref', 'secRestDataPref', 'secHeaders', 'secSleepTime', 'accessNoPatStr', 'accessNoPat', 'spacesPat',
           'tagsWithLeftSpace', 'pageUnavailablePat', 'delegates', 'callDelegated', 'checkDelegated',
           'compressGZipBytes', 'decompressGZipBytes', 'pickleToBytes', 'pickleFromBytes', 'pickSave', 'pickLoad',
           'pickLoadIfPath', 'pickSaveToS3', 'pickLoadFromS3', 'pickLoadFromS3Public', 'savePklToDir', 'loadPklFromDir',
           'saveSplitPklToDir', 'loadSplitPklFromDir', 'addMissingOnesF', 'toDateStr', 'toDate', 'isWeekend',
           'dateStrsBetween', 'formatDateStr', 'dateStr8Pat', 'curEasternUSTime', 'easternUSTimeZone', 'sanitizeText',
           'secBrowse', 'printSamp', 'printErrInfoOrAccessNo']

# Cell

from bs4 import BeautifulSoup, Comment, Doctype, NavigableString
import datetime
import gzip
import inspect
from io import BytesIO
import itertools
import json
import os
import pickle
import re
from pytz import timezone
import requests
import sys
import time
import webbrowser
import xml.etree.cElementTree as cElTree

boto3_available = True
try :
    import boto3
except :
    boto3_available = False

# Cell
stockDataRoot = os.path.expanduser(os.path.join('~','secData'))
def setStockDataRoot(loc) :
    "Set location for storing scraped stock data."
    global stockDataRoot
    stockDataRoot = loc

# Cell

def requestUrl(url, timeout=5.0, nTries=5, returnText=False, headers=None, sleepTime=None, **kwargs) :
    """
    Downloads a URL using the requests package.
    If sleepTime is not None, sleeps for the given time to stay under max request rate limits.
    """
    for i in range(nTries) :
        try :
            if sleepTime is not None :
                time.sleep(sleepTime)
            r = requests.get(url, headers=headers, timeout=timeout, params=kwargs)
            r.raise_for_status()
            return r.text if returnText else r
        except Exception as e :
            print('*** Problem','downloading',url,'-',e,'; retrying ...')
            if i >= nTries-1 :
                print('*** UNABLE TO DOWNLOAD ***')
                raise

secUrlPref = 'https://www.sec.gov'
secRestDataPref = 'https://data.sec.gov'
secHeaders = dict(requests.utils.default_headers())
def setSecUserAgent(agentStr) :
    """
    Should be used to set user agent to your email address for requests to the SEC site,
    to help avoid throttling.
    """
    secHeaders['User-Agent'] = agentStr
    #secHeaders['Host'] = 'www.sec.gov'
    #secHeaders['Accept-Encoding'] = 'gzip, deflate'
setSecUserAgent('secscantest@secscan.com')
secSleepTime = 0.1 # sleep time after requests to stay under SEC max request rate (currently 10/sec)
sys.setrecursionlimit(2000) # some filings have deeply nested HTML

accessNoPatStr = r'\d{10}-\d+-\d+'
accessNoPat = re.compile(accessNoPatStr)
def secIndexUrl(accessNo, includePref=False) :
    "Returns the url for the index page of an SEC filing specified by accession number."
    return ((secUrlPref if includePref else '')
            + '/Archives/edgar/data/'+accessNo.replace('-','')
            +'/'+accessNo+'-index.htm')

# from bs4.element import Comment
# def tag_visible(element):
#     if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]'] :
#         return False
#     if isinstance(element, Comment):
#         return False
#     return True
# def getCombSoupText(tag) :
#     "Get the combined text from a BeautifulSoup tag."
#     texts = tag.findAll(text=True)
#     texts = filter(tag_visible,texts)
#     return u" ".join(t.strip() for t in texts)
spacesPat = re.compile(r'\s+')
# def getCombSoupText(tag) :
#     "Get the combined text from a BeautifulSoup tag."
#     return spacesPat.sub(" "," ".join(tag.stripped_strings))
def appendSpace(resL) :
    if resL[-1] != ' ' :
        resL.append(' ')
tagsWithLeftSpace = tagsWithRightSpace = {'p','br','div','table','tr','td','li','pre','code'}
def getCombTextRec(soup, resL) :
    if isinstance(soup,Comment) or isinstance(soup,Doctype) :
        return
    if isinstance(soup,NavigableString) :
        s = soup.string.lstrip()
        if s != soup.string :
            appendSpace(resL)
        ss = s.rstrip()
        if ss != '' :
            resL.append(ss)
        if ss != s :
            resL.append(' ')
        return
    if soup.name in tagsWithLeftSpace :
        appendSpace(resL)
    for c in soup.children :
        getCombTextRec(c,resL)
    if soup.name in tagsWithRightSpace :
        appendSpace(resL)
def getCombSoupText(soup) :
    resL = [' ']
    getCombTextRec(soup,resL)
    return spacesPat.sub(" ",''.join(resL)).strip()

def prTree(soup, level=0) :
    if isinstance(soup,NavigableString) :
        print(level*'|'+('COMMENT' if isinstance(soup,Comment)
                         else ('DOCTYPE' if isinstance(soup,Doctype) else 'TEXT')),
              repr(soup.string))
    else :
        print(level*'|'+'TAG'+repr(soup.name))
        for c in soup.children :
            prTree(c,level+1)
def prAllTagNames(soup) :
    print(sorted(set(tag.name for tag in soup.descendants)))

pageUnavailablePat = re.compile('page is temporarily unavailable',re.IGNORECASE)
def downloadSecUrl(secSubUrlOrAccessNo, toFormat='text', sleepTime=0.1, restData=False) :
    """
    Downloads a page from the SEC site. The page can be specified by
    a sub-URL (ex. /cgi-bin/browse-edgar?CIK=0000716314&owner=exclude),
    or just by an accession number (ex. 0001193125-21-181366), in which
    case the index page for that filing is downloaded.

    Optionally parses the page contents:
    - toFormat=='soup' - parses to a BeautifulSoup object
    - toFormat=='souptext' - parses to a BeautifulSoup object, then gets combined text
    - toFormat=='json' - parses using json.loads
    - toFormat=='xml' - parses using xml.etree.cElementTree.fromstring

    SEC-specific behavior:

    If sleepTime is not None, sleeps for the given time to stay under
    the SEC site's maximum request rate (currently 10 requests/second).

    Checks for an SEC-specific temporary outage message, and raises
    an Exception if it's detected, so that we can detect the problem
    and retry the download later.
    """
    if accessNoPat.match(secSubUrlOrAccessNo) :
        secSubUrl = secIndexUrl(secSubUrlOrAccessNo)
    else :
        secSubUrl = secSubUrlOrAccessNo
        if secSubUrl.startswith('/ix?') :
            secSubUrl = secSubUrl[secSubUrl.index('/',1):]
    fullUrl = (secRestDataPref if restData else secUrlPref) + secSubUrl
    urlContents = requestUrl(fullUrl, returnText=True, headers=secHeaders, sleepTime=sleepTime)
    if pageUnavailablePat.search(urlContents) :
        raise Exception('temporary SEC outage')
    if toFormat=='soup' :
        return BeautifulSoup(urlContents,'html.parser')
    elif toFormat=='souptext' :
        return getCombSoupText(BeautifulSoup(urlContents,'html.parser'))
    elif toFormat=='json' :
        return json.loads(urlContents)
    elif toFormat == 'xml' :
        return cElTree.fromstring(urlContents)
    else :
        return urlContents

# Cell

def delegates(*toFuncs, keepKwargs=False):
    """
    Decorator to specify that a function delegates to one or more delegated functions.
    This will:

    - replace `**kwargs` in the delegating function's signature with the combined
      keyword arguments from the delegated functions, so that these keyword arguments
      are visible using autocomplete in a Jupyter environment

    - add the docstrs for the delegated functions to the end of the delegating function's
      docstr, so the usage documentation for the delegated functions is also visible.
    """
    def _decorator(fromFunc):
        sigFrom = inspect.signature(fromFunc)
        # print(sigFrom)
        sigFromDict = dict(sigFrom.parameters)
        kwargsParam = sigFromDict.pop('kwargs')
        delegatedDict = {}
        docStrs = []
        if fromFunc.__doc__ is not None :
            docStrs.append(fromFunc.__doc__)
        for toFunc in toFuncs :
            argL = []
            for name,param in inspect.signature(toFunc).parameters.items() :
                if param.default!=inspect.Parameter.empty and name not in sigFromDict :
                    delegatedDict[name] = param.replace(kind=inspect.Parameter.KEYWORD_ONLY)
                    argL.append(f'{name}={param.default}')
            docStrs.append('---')
            docStrs.append(f'{toFunc.__qualname__} arguments: ' + ', '.join(argL))
            if toFunc.__doc__ is not None :
                docStrs.append(toFunc.__doc__)
        sigFromDict.update(delegatedDict)
        if keepKwargs:
            sigFromDict['kwargs'] = kwargsParam
        fromFunc.__signature__ = sigFrom.replace(parameters=sigFromDict.values())
        # print(fromFunc.__signature__)
        fromFunc.__doc__ = '\n'.join(docStrs)
        return fromFunc
    return _decorator

def callDelegated(toFunc, kwargs, *args, **extraKwargs) :
    """
    Call a delegated function. This needs to be used from within a delegating function
    if more than one function was delegated to, in order to select the optional arguments
    from kwargs that apply to the delegated function.
    """
    # print('callDelegate',toFunc, kwargs, args, extraKwargs)
    delegatedKwargs = {}
    for name,param in inspect.signature(toFunc).parameters.items() :
        if param.default != inspect.Parameter.empty :
            delegatedKwargs[name] = kwargs.get(name, param.default)
    delegatedKwargs.update(extraKwargs)
    # print(delegatedKwargs)
    return toFunc(*args,**delegatedKwargs)

def checkDelegated(*toFuncs, **kwargs) :
    """
    Raises an exception if kwargs contains any unexpected keyword arguments not included
    in any of the delegated functions toFuncs.
    """
    allKws = set()
    for toFunc in toFuncs :
        allKws.update(name for name,param in inspect.signature(toFunc).parameters.items()
                      if param.default != inspect.Parameter.empty)
    for name,val in kwargs.items() :
        if name not in allKws :
            raise TypeError(f'unexpected keyword argument {name}={val}')

# Cell

def compressGZipBytes(b) :
    "Compress a byte string in-memory using gzip."
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(b)
    return out.getvalue()

def decompressGZipBytes(b) :
    "Decompress a byte string in-memory using gzip."
    inp = BytesIO(b)
    with gzip.GzipFile(fileobj=inp, mode="r") as f:
        return f.read()

@delegates(pickle.dumps)
def pickleToBytes(ob, use_gzip=False, **kwargs) :
    "Pickle an object in-memory, optionally using gzip compression."
    b = pickle.dumps(ob, **kwargs)
    if use_gzip :
        b = compressGZipBytes(b)
    return b

@delegates(pickle.loads)
def pickleFromBytes(b, use_gzip=False, **kwargs) :
    "Unpickle an object in-memory, optionally using gzip compression."
    if use_gzip :
        b = decompressGZipBytes(b)
    return pickle.loads(b, **kwargs)

# Cell

@delegates(pickleToBytes)
def pickSave(fpath, ob, **kwargs) :
    "Save a pickled object to a file, optionally using gzip compression."
    with open(fpath, 'wb') as f :
        f.write(pickleToBytes(ob, **kwargs))

@delegates(pickleFromBytes)
def pickLoad(fpath, **kwargs) :
    "Load a pickled object from a file, optionally using gzip compression."
    with open(fpath, 'rb') as f :
        return pickleFromBytes(f.read(), **kwargs)

@delegates(pickLoad)
def pickLoadIfPath(path_or_ob, **kwargs) :
    """
    If given a path, loads a pickled object from it; otherwise returns
    its argument unchanged (assumes it's an already loaded object).
    """
    if isinstance(path_or_ob,str) :
        return pickLoad(path_or_ob, **kwargs)
    else :
        return path_or_ob

# Cell

@delegates(pickleToBytes)
def pickSaveToS3(bucket, key, ob, make_public=False, s3=None, **kwargs) :
    "Save a pickled object to an S3 bucket, optionally using gzip compression."
    if s3 is None : s3 = boto3.client('s3')
    s3Args = dict(Bucket=bucket, Key=key, Body=pickleToBytes(ob, **kwargs))
    if make_public :
        s3Args['ACL'] = 'public-read'
    s3.put_object(**s3Args)

@delegates(pickleFromBytes)
def pickLoadFromS3(bucket, key, s3=None, **kwargs) :
    "Load a pickled object from an S3 bucket, optionally using gzip compression."
    if s3 is None : s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pickleFromBytes(obj['Body'].read(), **kwargs)

@delegates(pickleFromBytes)
def pickLoadFromS3Public(bucket, key, **kwargs) :
    s3PublicUrl = 'https://'+bucket+'.s3.amazonaws.com/'+key
    return pickleFromBytes(requestUrl(s3PublicUrl).content, **kwargs)

# Cell

@delegates(pickSave)
def savePklToDir(toDir, fName, ob, **kwargs) :
    """
    Saves a pickled object to a file under a directory, optionally using gzip compression.
    Creates the directory if it doesn't exist.
    """
    if not os.path.exists(toDir) :
        os.makedirs(toDir)
    pickSave(os.path.join(toDir, fName), ob, **kwargs)

@delegates(pickLoad)
def loadPklFromDir(fromDir, fName, defaultVal, **kwargs) :
    """
    Load a pickled object from a file under a directory, optionally using gzip compression.
    Returns a default value if the file doesn't exist.
    """
    fpath = os.path.join(fromDir, fName)
    if os.path.exists(fpath) :
        return pickLoad(fpath, **kwargs)
    else :
        return defaultVal

# Cell

@delegates(pickSave)
def saveSplitPklToDir(m, toDir, fSuff='m.pkl', dirtySet=None, **kwargs) :
    """
    Saves a dict with str keys to a separate file for each key.
    If dirtySet is True, saves all keys.
    If dirtySet is None (default), saves only keys that don't yet have a file saved.
    Otherwise, also saves keys k in dirtySet.
    """
    if not os.path.exists(toDir) :
        os.makedirs(toDir)
    for k in sorted(m.keys()) :
        fPath = os.path.join(toDir, k+fSuff)
        if dirtySet is True :
            needToSave = True
        else :
            needToSave = not os.path.exists(fPath)
            if dirtySet is not None :
                needToSave = needToSave or (k in dirtySet)
        if needToSave :
            pickSave(fPath, m[k], **kwargs)

@delegates(pickLoad)
def loadSplitPklFromDir(fromDir, startK=None, endK=None, fSuff='m.pkl', **kwargs) :
    """
    Loads a pickled dict with str keys stored with a separate file for each key,
    optionally restricting to keys in [startK .. endK)
    """
    m = {}
    if not os.path.exists(fromDir) :
        return m
    fNames = sorted(fName for fName in os.listdir(fromDir)
                    if fName.endswith(fSuff))
    for fName in fNames :
        fPref = fName[:-len(fSuff)]
        if ((startK is not None and fPref<startK)
                or (endK is not None and endK<=fPref)) :
            continue
        m[fPref] = pickLoad(os.path.join(fromDir,fName), **kwargs)
    return m

# Cell

def addMissingOnesF(dateStr) :
    if len(dateStr) == 4 :
        return dateStr + '0101'
    if len(dateStr) == 6 :
        return dateStr + '01'
    return dateStr

def toDateStr(d=None, addMissingOnes=False) :
    """
    Converts date object or ISO format date string to YYYYMMDD format string;
    leaves YYYYMMDD format strings unchanged;
    None -> today.
    """
    if isinstance(d,str) :
        dateStr = d
    else :
        if d is None :
            d = curEasternUSTime()
        elif isinstance(d,int) :
            d = curEasternUSTime() + datetime.timedelta(d)
        dateStr = d.isoformat()[:10]
    dateStr = dateStr.replace('-','').replace('/','')
    if addMissingOnes :
        dateStr = addMissingOnesF(dateStr)
    return dateStr

dateStr8Pat = re.compile(r"(\d\d\d\d)(\d\d)(\d\d)$")
def toDate(d=None, addMissingOnes=False) :
    """
    Converts date string in ISO or YYYYMMDD format to date object;
    leaves date objects unchanged;
    None -> today.
    """
    if isinstance(d,str) :
        dateStr = d.replace('-','').replace('/','')
        if addMissingOnes :
            dateStr = addMissingOnesF(dateStr)
        m = dateStr8Pat.match(dateStr)
        if m is None :
            raise Exception('invalid date str "'+d+'"')
        return datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    if d is None :
        return curEasternUSTime()
    if isinstance(d,int) :
        return curEasternUSTime() + datetime.timedelta(d)
    return d

def isWeekend(d) :
    "Says if date string or date object is on a weekend (Saturday or Sunday)."
    return toDate(d).weekday() >= 5

def dateStrsBetween(d1,d2=None,excludeWeekends=False) :
    """
    Returns a list of date strings in YYYYMMDD format from d1 (inclusive)
    to d2 (exclusive), optionally excluding weekends.
    """
    d1 = toDate(d1)
    d2Str = toDateStr(d2)
    res = []
    while True :
        d1Str = toDateStr(d1)
        if d1Str >= d2Str :
            break
        if not (excludeWeekends and isWeekend(d1)) :
            res.append(d1Str)
        d1 = d1 + datetime.timedelta(1)
    return res

def formatDateStr(dStr,sep='-') :
    "Convert YYYYMMDD format date string to YYYY-MM-DD."
    return sep.join((dStr[:4],dStr[4:6],dStr[6:8]))

# Cell

easternUSTimeZone = timezone('US/Eastern')
def curEasternUSTime() :
    return datetime.datetime.now(easternUSTimeZone)

# Cell

def sanitizeText(s) :
    if '&' in s[-10:] :
        s = s[:s.rindex('&')]
    return s

# Cell

def secBrowse(accessNo) :
    "Open the index page of an SEC filing specified by accession number in a web browser."
    webbrowser.open_new_tab(secIndexUrl(accessNo,True))

def printSamp(m,n=10) :
    """
    Prints a sample of n items from object m , where m is a list or dict;
    for other objects just prints the whole thing.
    """
    if isinstance(m,list) :
        for i,item in enumerate(m[:n]) :
            print(f'[{i}]',end=' ')
            printSamp(item,n)
    elif isinstance(m,dict) :
        for k,v in itertools.islice(m.items(),n) :
            print(repr(k),end=': ')
            printSamp(v,n)
    else :
        print(repr(m))

def printErrInfoOrAccessNo(msg,infoOrAccessNo) :
    print(msg,end=' ')
    if isinstance(infoOrAccessNo,str) and accessNoPat.match(infoOrAccessNo) :
        print(secIndexUrl(infoOrAccessNo,True))
    else :
        print(repr(infOrAccessNo))