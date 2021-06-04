# AUTOGENERATED! DO NOT EDIT! File to edit: 00_utils.ipynb (unless otherwise specified).

__all__ = ['setStockDataRoot', 'stockDataRoot', 'requestUrl', 'downloadSecUrl', 'secIndexUrl', 'downloadSecSoup',
           'getCombString', 'secUrlPref', 'pageUnavailableRE', 'spacesPat', 'openFp', 'pickSave', 'pickLoad',
           'pickLoadIfPath', 'savePklToDir', 'loadPklFromDir', 'saveSplitPklToDir', 'loadSplitPklFromDir', 'toDateStr',
           'toDate', 'dateStrsBetween', 'formatDateStr', 'dateStr8Pat', 'curEasternUSTime', 'easternUSTimeZone',
           'secBrowse', 'printSamp', 'printErrInfoOrAccessNo']

# Cell

from bs4 import BeautifulSoup
import datetime
import gzip
import os
import pickle
import re
from pytz import timezone
import requests
import time
import webbrowser

# Cell
stockDataRoot = os.path.expanduser(os.path.join('~','secData2'))
def setStockDataRoot(loc) :
    "Set location for storing scraped stock data."
    global stockDataRoot
    stockDataRoot = loc

# Cell

def requestUrl(url, timeout=5.0, nTries=5, returnText=False, **kwargs) :
    "Downloads a URL using the requests package."
    for i in range(nTries) :
        try :
            r = requests.get(url,timeout=timeout,params=kwargs)
            r.raise_for_status()
            return r.text if returnText else r
        except Exception as e :
            print('Error','downloading',url,'-',e)
            if i >= nTries-1 :
                raise

secUrlPref = 'https://www.sec.gov'
pageUnavailableRE = re.compile('page is temporarily unavailable',re.IGNORECASE)
def downloadSecUrl(secSubUrl) :
    """
    Downloads a url from the SEC site, also checking for an SEC-specific temporary outage message.
    """
    urlContents = requestUrl(secUrlPref+secSubUrl).text
    if pageUnavailableRE.search(urlContents) :
        raise Exception('temporary SEC outage')
    return urlContents

def secIndexUrl(accessNo, includePref=False) :
    "Returns the url for the index page of an SEC filing specified by accession number."
    return ((secUrlPref if includePref else '')
            + '/Archives/edgar/data/'+accessNo.replace('-','')
            +'/'+accessNo+'-index.htm')

def downloadSecSoup(secSubUrl) :
    return BeautifulSoup(downloadSecUrl(secSubUrl),'html.parser')

spacesPat = re.compile(r'\s+')
def getCombString(tag) :
    "Get the combined text from a BeautifulSoup tag."
    return spacesPat.sub(" "," ".join(tag.stripped_strings))

# Cell

def openFp(fpath, mode, use_gzip) :
    "Open a file for writing or reading, optionally using gzip compression."
    openfunc = gzip.open if use_gzip else open
    return openfunc(fpath,mode)

def pickSave(fpath, ob, use_gzip=False, **kwargs) :
    "Save a pickled object to a file, optionally using gzip compression."
    with openFp(fpath, 'wb', use_gzip) as f :
        pickle.dump(ob, f, **kwargs)

def pickLoad(fpath, use_gzip=False) :
    "Load a pickled object from a file, optionally using gzip compression."
    with openFp(fpath, 'rb', use_gzip) as f :
        return pickle.load(f)

def pickLoadIfPath(path_or_ob, use_gzip=False) :
    """
    If given a path, loads a pickled object from it; otherwise returns
    its argument unchanged (assumes it's an already loaded object).
    """
    if isinstance(path_or_ob,str) :
        return pickLoad(path_or_ob, use_gzip=use_gzip)
    else :
        return path_or_ob

# Cell

def savePklToDir(toDir, fName, ob, use_gzip=False, **kwargs) :
    """
    Saves a pickled object to a file under a directory, optionally using gzip compression.
    Creates the directory if it doesn't exist.
    """
    if not os.path.exists(toDir) :
        os.makedirs(toDir)
    fPath = os.path.join(toDir, fName)
    pickSave(fPath, ob, use_gzip=use_gzip, **kwargs)

def loadPklFromDir(fromDir, fName, defaultVal, use_gzip=False) :
    """
    Load a pickled object from a file under a directory, optionally using gzip compression.
    Returns a default value if the file doesn't exist.
    """
    fPath = os.path.join(fromDir, fName)
    if os.path.exists(fPath) :
        return pickLoad(fPath, use_gzip=use_gzip)
    else :
        return defaultVal

# Cell

def saveSplitPklToDir(m, toDir, fSuff='m.pkl', dirtyMap=None, use_gzip=False, **kwargs) :
    """
    Saves a dict with str keys to a separate file for each key.
    If dirtyMap is True, saves all keys.
    If dirtyMap is None (default), saves only keys that don't yet have a file saved.
    Otherwise, also saves keys k for which dirtyMap.get(k) is true.
    """
    if not os.path.exists(toDir) :
        os.makedirs(toDir)
    for k in sorted(m.keys()) :
        fPath = os.path.join(toDir, k+fSuff)
        if dirtyMap is True :
            needToSave = True
        else :
            needToSave = not os.path.exists(fPath)
            if dirtyMap is not None :
                needToSave = needTooSave or dirtyMap.get(k)
        if needToSave :
            pickSave(fPath, m[k], use_gzip=use_gzip, **kwargs)

def loadSplitPklFromDir(fromDir, startK=None, endK=None, fSuff='m.pkl') :
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
        m[fPref] = pickLoad(os.path.join(fromDir,fName))
    return m

# Cell

def toDateStr(d=None) :
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
        dateStr = d.isoformat()[:10]
    return dateStr.replace('-','').replace('/','')

dateStr8Pat = re.compile(r"(\d\d\d\d)(\d\d)(\d\d)$")
def toDate(d=None) :
    """
    Converts date string in ISO or YYYYMMDD format to date object;
    leaves date objects unchanged;
    None -> today.
    """
    if isinstance(d,str) :
        dateStr = d.replace('-','').replace('/','')
        m = dateStr8Pat.match(dateStr)
        if m is None :
            raise Exception('invalid date str "'+d+'"')
        return datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    if d is None :
        return curEasternUSTime()
    return d

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
        if not (excludeWeekends and d1.weekday()>=5) :
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
            print(i,end=' ')
            printSamp(item,n)
    elif isinstance(m,dict) :
        for k in m.keys()[:n] :
            print(k,end=' ')
            printSamp(m[k],n)
    else :
        print(m)

def printErrInfoOrAccessNo(msg,infOrAccessNo) :
    print(msg,end=' ')
    if isinstance(infOrAccessNo,str) :
        print(secIndexUrl(infOrAccessNo,True))
    else :
        print(infOrAccessNo)