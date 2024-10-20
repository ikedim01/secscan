# AUTOGENERATED! DO NOT EDIT! File to edit: 14_priceHist.ipynb (unless otherwise specified).

__all__ = ['USExchanges', 'getHistFStuff', 'getDayMap', 'getCombDayMap', 'getCombDayMapWithLookback',
           'getCombDayMapsForRangeWithLookback', 'dayMapCache', 'initTickerMappings', 'tickerNames',
           'getCleanedPriceData', 'getSortedReturns', 'getForwardReturns', 'getClosestReturn', 'genServList',
           'getTextPriceDataset', 'getCombTextDigest', 'getCombTextEmbedding', 'init_openAI', 'cacheEmbeddings',
           'findClosestEmbs', 'makePortEmbDataSet', 'getRecsFromPort', 'textScraperClasses', 'openAI_client',
           'openAI_defKeyPath']

# Cell

import collections
import datetime
import numpy as np
import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import time

from secscan import utils,tickerMap,scrape8K,scrape6K,scrape13D

USExchanges = ['AMEX','NASDAQ','NYSE','OTCBB']

# Cell

def getHistFStuff(exch,dateStr) :
    """
    Returns (fName, fDir, fPath) containing the CSV file of historical prices
    for the given exchange and date.
    """
    fName = exch+'_'+dateStr+'.csv'
    histFDir = os.path.join(utils.stockPriceRoot,fName[:len(exch)+5])
    histFPath = os.path.join(histFDir,fName)
    return fName,histFDir,histFPath

# Cell

def getDayMap(dateStr, exch, symCol='Symbol', priceCol='Open') :
    """
    Parse the CSV file for a single day and exchange.
    Returns a dict:<stock symbol> -> <value>
    """
    fPath = getHistFStuff(exch,dateStr)[2]
    if not os.path.exists(fPath) :
        return {}
    df = pd.read_csv(fPath, na_filter=False)
    dayMap = {}
    for sym,val in zip(df[symCol],df[priceCol]) :
        if isinstance(sym,str) :
            dayMap[sym] = val
        else :
            print(dateStr,exch,'non-string symbol',repr(sym))
    return dayMap

# Cell

@utils.delegates(getDayMap)
def getCombDayMap(dateStr, exchs=USExchanges, checkDups=True, **kwargs) :
    """
    Combines the day maps for a list of exchanges, optionally checking for symbols
    duplicated between exchanges.
    Returns a dict:<stock symbol> -> <value>
    """
    combDayMap = {}
    for exch in exchs :
        m = getDayMap(dateStr,exch,**kwargs)
        if checkDups :
            dupKeys = (set(m.keys()) & combDayMap.keys())
            if len(dupKeys) > 0 :
                print('duplicated keys:',exch,dateStr,sorted(dupKeys)[:10])
        combDayMap.update(m)
    return combDayMap

# Cell

dayMapCache = {}

@utils.delegates(getCombDayMap)
def getCombDayMapWithLookback(forD, lookback=7, **kwargs) :
    """
    Get the day map for a given day, looking back a given number of days -
    i.e. if a stock doesn't trade on a particular day, looks back the specified
    number of days to find the most recent trade.

    Returns a dict:<stock symbol> -> <value>
    """
    d1 = utils.toDate(forD) + datetime.timedelta(-lookback)
    d2 = utils.toDate(forD) + datetime.timedelta(1)
    dayMap = {}
    for d in utils.dateStrsBetween(d1, d2) :
        if d not in dayMapCache :
            dayMapCache[d] = getCombDayMap(d, **kwargs)
        dayMap.update(dayMapCache[d])
    return dayMap

@utils.delegates(getCombDayMapWithLookback)
def getCombDayMapsForRangeWithLookback(d1, d2, **kwargs) :
    """
    Get all the combined day maps from d1 (inclusive) to d2 (exclusive), with lookback.

    Returns a dict:dateStr -> {<stock symbol> -> <value>}
    Skips weekend dates in the returned dict.
    """
    res = {}
    for d in utils.dateStrsBetween(d1, d2, excludeWeekends=True) :
        res[d] = getCombDayMapWithLookback(d, **kwargs)
    return res

# Cell

# Load current SEC ticker <-> cik/name mappings once per run:
tickerNames = cikToTicker = tickerToCik = None
def initTickerMappings() :
    global tickerNames, cikToTicker, tickerToCik
    if tickerNames is None :
        tickerNames = tickerMap.getSecTickerDict(field2='name')
        cikToTicker = tickerMap.getCikToFirstTickerMap()
        tickerToCik = dict((ticker,cik) for cik,ticker in cikToTicker.items())

# Cell

@utils.delegates(getCombDayMapsForRangeWithLookback)
def getCleanedPriceData(d1, d2, minPrice=None, restrictToNames=False, **kwargs) :
    """
    Constructs a price dataset for direct indexing tests.

    First gets all the combined day maps from d1 to d2, with specified lookback,
    and skipping weekend days.

    Then, cuts down to stocks that have values for all the specified days.

    If minPrice is not None, also cuts down to stocks with value > minPrice on all days.

    If restrictToNames is True, also cuts down to stocks present in the SEC ticker list.

    Returns a tuple (syms, symNames, dateStrs, priceMat), where:
    syms is a sorted list of ticker symbols
    symNames is a list of corresponding names from the SEC ticker list ('' if not present)
    dateStrs is a list of date strings in the format '20240624'
    priceMat is a matrix of values with len(syms) rows and len(dateStrs) columns
    """
    dayMaps = getCombDayMapsForRangeWithLookback(d1, d2, **kwargs)
    dateStrs = sorted(dayMaps.keys())
    symsPresentAllDays = sorted(set.intersection(*(set(dayMap.keys())
                                                   for dayMap in dayMaps.values())))
    symsToRemove = set()
    if minPrice is not None :
        for dayMap in dayMaps.values() :
            for sym,val in dayMap.items() :
                if val < minPrice :
                    symsToRemove.add(sym)
    initTickerMappings()
    if restrictToNames :
        for sym in symsPresentAllDays :
            if sym not in tickerNames :
                symsToRemove.add(sym)
    if len(symsToRemove) > 0 :
        symsPresentAllDays = [sym for sym in symsPresentAllDays
                              if sym not in symsToRemove]
    priceMat = np.zeros((len(symsPresentAllDays), len(dateStrs)))
    for dateNo,d in enumerate(dateStrs) :
        dayMap = dayMaps[d]
        for symNo,sym in enumerate(symsPresentAllDays) :
            priceMat[symNo,dateNo] = dayMap[sym]
    symNames = [tickerNames.get(sym,'') for sym in symsPresentAllDays]
    print(len(symsPresentAllDays),'symbols',len(dateStrs),'dates')
    return (symsPresentAllDays, symNames, dateStrs, priceMat)

@utils.delegates(getCleanedPriceData)
def getSortedReturns(d1, d2, highestFirst=True, **kwargs) :
    """
    Gets a sorted list of stock price returns between two dates.

    Returns a list of tuples, sorted by return:
        [(sym, symName, <percent return between d1 and d2>)]
    """
    syms, symNames, dateStrs, priceMat = getCleanedPriceData(d1,
        utils.toDateStr(utils.toDate(d2) + datetime.timedelta(1)),
        **kwargs)
    returns = (priceMat[:,-1]/priceMat[:,0] - 1.0)
    res = sorted(zip(syms,symNames,priceMat[:,0],priceMat[:,-1],returns),
                 key = lambda x : x[-1],
                 reverse = highestFirst)
    print('restricting to named stocks',end=' - ')
    res = [el for el in res if el[1]]
    print('now',len(res),'stocks')
    return res

@utils.delegates(getCleanedPriceData)
def getForwardReturns(d1, d2, weekdaysForward=20, **kwargs) :
    """
    Calculates a matrix of forward percentage returns looking ahead weekdaysForward
    weekdays for each date from d1 (inclusive) to d2 (exclusive). Only weekdays are
    included in the matrix to avoid over-emphasizing forward returns from Fridays.

    Returns a tuple (syms, symNames, dateStrs, returnMat), as for getCleanedPriceData,
    except returnMat is a matrix of forward returns looking ahead from each day.
    """
    d3 = utils.toDateStr(utils.toDate(d2)
                         + datetime.timedelta(weekdaysForward + 2*((weekdaysForward+4)//5)))
    syms, symNames, dateStrs, priceMat = getCleanedPriceData(d1,d3,**kwargs)
    dateStrs = [d for d in dateStrs if d<d2]
    returnMat = np.zeros((len(syms), len(dateStrs)))
    for j in range(len(dateStrs)) :
        returnMat[:,j] = (priceMat[:,j+weekdaysForward]/priceMat[:,j] - 1.0)
    return (syms, symNames, dateStrs, returnMat)

def getClosestReturn(sym, syms, symNames, dateStrs, returnMat, fName=None, n=20) :
    """
    Finds the symbols with the closest average forward return to a given symbol.

    Returns a list:
        [(sym, symName, <total absolute value of forward return differences>)]
    """
    rowNo = syms.index(sym)
    diffs = ((returnMat - returnMat[rowNo])**2).sum(axis=1)
    symsAndDiffs = list(zip(syms,symNames,diffs))
    symsAndDiffs.sort(key=lambda x : x[2])
    if n is not None :
        symsAndDiffs = symsAndDiffs[:n]
    if fName is not None :
        genServList(fName,symsAndDiffs)
    return symsAndDiffs


def genServList(fName, syms) :
    """
    Save a list of stock symbols and CIKs in display format for my secscrape server.
    """
    print('saving serv list',fName)
    initTickerMappings()
    with open(os.path.expanduser(os.path.join('~','Dropbox',
                    'sw','secScripts',fName+'.txt')),'w') as f :
        for sym in syms :
            if isinstance(sym,tuple) :
                sym = sym[0]
            if sym not in tickerToCik :
                print('skipping',sym,'(no CIK)')
            else :
                f.write(f"    {tickerToCik[sym]} # {sym}\n")

# Cell

textScraperClasses = [
    scrape8K.scraper8K, scrape6K.scraper6K, scrape13D.scraper13D
]

@utils.delegates(getCombDayMapWithLookback)
def getTextPriceDataset(d1, d2, d3, d4, minPrice=None, **kwargs) :
    """
    Constructs a text/price dataset for text-based prediction tests.

    First gets day maps from d3 and d4, with specified lookback.

    Then, cuts down to stocks that have values for both days.

    If minPrice is not None, also cuts down to stocks with value > minPrice on both days.

    Then, creates a dict symTexts mapping each stock symbol to a digest of the text for
    that symbol between dates d1 and d2, scraped from SEC 8-K and 6-K filings.

    Then, cuts down to stocks for which some text was found between dates d1 and d2.

    Returns a tuple (symsWithPrices, dmStart, dmEnd, mReturns, symTexts), where:
    symsWithPrices is a sorted list of ticker symbols that passed the filters above.
    dmStart, dmEnd is d3, d4
    mReturns is a dict: sym -> <return between d3 and d4>
    symTexts is a dict: sym -> [text1, text2, ... ], earlier texts first
    """
    dmStart = getCombDayMapWithLookback(d3, **kwargs)
    dmEnd = getCombDayMapWithLookback(d4, **kwargs)
    symsWithPrices = sorted(set(dmStart.keys()).intersection(dmEnd.keys()))
    print(len(symsWithPrices),'stock symbols found')
    if minPrice is not None :
        print('restricting to price >=',minPrice,end=' ... ')
        symsWithPrices = [sym for sym in symsWithPrices
                          if dmStart[sym]>=minPrice and dmEnd[sym]>=minPrice]
        print('now',len(symsWithPrices),'stocks')
    print('restricting to CIKs',end=' ... ')
    initTickerMappings()
    symsWithPrices = [sym for sym in symsWithPrices if sym in tickerToCik]
    print('now',len(symsWithPrices),'stocks')
    scraperL = []
    for cl in textScraperClasses :
        print('loading',cl,end=' ... ')
        scraperL.append(cl(startD=d1, endD=d2))
        scraperL[-1].printCounts(verbose=False)
    print('getting CIK texts',end=' ... ')
    symsWithPricesAsSet = set(symsWithPrices)
    symTexts = collections.defaultdict(list)
    dStrList = utils.dateStrsBetween(d1, d2)
    nDays = len(dStrList)
    initTickerMappings()
    for dNo,d in enumerate(dStrList) :
        for s in scraperL :
            for accNo,info in s.infoMap[d].items() :
                if info == 'ERROR' :
                    continue
                ciks = [cik.lstrip('0') for cik in info.get('ciks',[])]
                ciks = [cik for cik in ciks
                        if cikToTicker.get(cik,'-') in symsWithPricesAsSet]
                if len(ciks)==0 :
                    continue
                tDigest = s.getTextDigest(info).strip()
                if tDigest == '' :
                    continue
                fDesc = f'FORM {s.formClass} -{nDays-dNo} DAYS.'
                tDigest = 'START ' + fDesc + ' ' + tDigest + ' END ' + fDesc
                for cik in ciks :
                    symTexts[cikToTicker[cik]].append(tDigest)
    print(len(symTexts),'stocks with CIK text found')
    symsWithPrices = [sym for sym in symsWithPrices if sym in symTexts]
    dmStart = dict((sym,val) for sym,val in dmStart.items() if sym in symTexts)
    dmEnd = dict((sym,val) for sym,val in dmEnd.items() if sym in symTexts)
    mReturns = dict((sym, dmEnd[sym]/dmStart[sym] - 1.0)
                    for sym in symsWithPrices)
    return symsWithPrices, dmStart, dmEnd, mReturns, symTexts

def getCombTextDigest(sym, symTexts, maxLen=8191) :
    """
    Returns a combined text digest for a symbol, where symTexts maps symbols
    to lists of text digests, earliest first. Just concatenates all the most
    recent text digests that will fit into the given character limit.
    """
    textL = []
    totLen = 0
    for txt in reversed(symTexts[sym]) :
        # stay below limit, while keeping newest texts
        print('text length',len(txt),txt[:20],end='... ')
        if totLen + len(txt) + 1 > maxLen :
            print('limit exceeded, stopping',end=' ')
            break
        textL.append(txt)
        totLen += (len(txt) + 1)
    textL.reverse() # order old to new
    textL.append('')
    return '\n'.join(textL)

openAI_client = None

@utils.delegates(getCombTextDigest)
def getCombTextEmbedding(sym, symTexts, model='text-embedding-3-small', **kwargs) :
    """
    Calls the OpenAI API to get the embedding for the combined text digest for a given symbol.
    """
    combText = getCombTextDigest(sym, symTexts, **kwargs)
    print('symbol',sym,'text length',len(combText))
    response = openAI_client.embeddings.create(input=combText, model=model)
    return np.array(response.data[0].embedding)

openAI_defKeyPath = os.path.join('..','xyzzy.txt')

def init_openAI(keyPath=openAI_defKeyPath) :
    global openAI_client
    from openai import OpenAI
    #from openai.embeddings_utils import get_embedding, cosine_similarity
    with open(keyPath,'r') as f :
        openAI_api_key = f.read()
    openAI_client = OpenAI(api_key=openAI_api_key)

@utils.delegates(getCombTextEmbedding)
def cacheEmbeddings(fName, syms, symTexts, verbose=False, sleepTime=0.25, **kwargs) :
    """
    Caches the embeddings for the combined text digests for the given symbols
    in the named file under utils.stockDataRoot, subdir 'embeddings'.
    """
    fDir = os.path.join(utils.stockDataRoot,'embeddings')
    embCache = utils.loadPklFromDir(fDir,fName,{})
    dirty = False
    nMissing = 0
    for sym in syms :
        if sym in embCache :
            if verbose :
                print(sym,'loaded',end='; ')
        elif openAI_client is None :
            print('MISSING',sym,end='; ')
            nMissing += 1
        else :
            print('getting',sym,'embedding',end=' ')
            if sleepTime is not None :
                time.sleep(sleepTime)
            embCache[sym] = getCombTextEmbedding(sym, symTexts, **kwargs)
            dirty = True
    if nMissing > 0 :
        print()
        print('total of',nMissing,'missing embeddings')
        raise MemoryError('openAI client not initialized '
                          + '- initialize it and rerun to get embeddings')
    if dirty :
        print('saving cache to',fName)
        utils.savePklToDir(fDir,fName,embCache)
    print(len(embCache),'embeddings in cache')
    return embCache

def findClosestEmbs(toSym, syms, cemb, fName=None, n=20,
                    distFunc=lambda x,y : x.dot(y), reverse=True) :
    """
    Finds the symbols in the given list with the embeddings closest to the given symbol,
    using the given distance function. The embeddings must have been previously cached
    using cacheEmbeddings.
    """
    distL = [(sym, distFunc(cemb[toSym],cemb[sym]))
               for sym in syms]
    distL.sort(key = lambda x : x[1], reverse=reverse)
    if n is not None :
        distL = distL[:n]
    if fName is not None :
        genServList(fName, distL)
    return distL

def makePortEmbDataSet(portSyms, syms, cemb, posWeight=1.0, negWeight=0.001) :
    """
    Create a data set for training classification models based on a given list of portfolio symbols.
    The embeddings for the portfolio symbols will have y=1 and weight=posWeight,
    while those for the non-portfolio symbols will have y=0 and weight=negWeight.
    """
    x = np.zeros((len(syms), len(cemb[syms[0]])))
    y = np.zeros(len(syms), dtype=np.int32)
    weights = np.zeros(len(syms))
    for i,sym in enumerate(syms) :
        x[i] = cemb[sym]
        if sym in portSyms :
            y[i] = 1
            weights[i] = posWeight
        else :
            weights[i] = negWeight
    return x,y,weights

@utils.delegates(makePortEmbDataSet)
def getRecsFromPort(portSyms, syms, cemb,
                    n=30, model=None, **kwargs) :
    """
    Fit a classification model based on the given portfolio of symbols
    and a cache of other embeddings. Returns the best predicted symbols
    from among the given symbol list.
    """
    dd = makePortEmbDataSet(portSyms, syms, cemb, **kwargs)
    if model is None :
        model = LogisticRegression()
    model.fit(*dd)
    ypred = model.predict_log_proba(dd[0])
    res = sorted(zip(syms,np.exp(ypred)[:,0]),key=lambda x : x[1])[:n]
    initTickerMappings()
    return [(sym,('* ' if sym in portSyms else '') + tickerNames[sym],p)
            for sym,p in res]