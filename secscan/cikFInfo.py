# AUTOGENERATED! DO NOT EDIT! File to edit: 13_cikFinfo.ipynb (unless otherwise specified).

__all__ = ['defaultCikFInfoDir', 'allScraperClasses', 'cikFPrefLen', 'getCikFInfoDirAndPath', 'jsonValError',
           'loadCikFInfo', 'saveCikFInfo', 'saveAllCikFInfo', 'prSample', 'saveYears']

# Cell

import collections
import json
import os

from secscan import utils, dailyList
from secscan import scrape13F, scrape8K, scrape6K, scrape13G, scrape13D, scrape4

defaultCikFInfoDir = os.path.join(utils.stockDataRoot,'cikFInfo')
allScraperClasses = [scrape13F.scraper13F,scrape8K.scraper8K,scrape6K.scraper6K,
                     scrape13G.scraper13G,scrape13D.scraper13D,scrape4.scraper4]
cikFPrefLen = 4

# Cell

def getCikFInfoDirAndPath(cik, cikFInfoDir=defaultCikFInfoDir) :
    if len(cik)<2 or not cik.isdigit() or cik[0]=='0' :
        raise ValueError(f'invalid CIK "{cik}"')
    fDir = os.path.join(cikFInfoDir,cik[:cikFPrefLen])
    return fDir,os.path.join(fDir,cik+'.json')

def jsonValError(msg, s) :
    if len(s) > 200 :
        s = s[:100] + ' ... ' + s[-100:]
    return ValueError(msg + ' in ' + s)

def loadCikFInfo(cik, cikFInfoDir=defaultCikFInfoDir, returnAsText=False) :
    cik = str(cik).lstrip('0')
    fPath = getCikFInfoDirAndPath(cik, cikFInfoDir)[1]
    if not os.path.exists(fPath) :
        return {}
    with open(fPath,'r',encoding='ascii') as f :
        s = f.read().strip()
    if s[-1] != ',' :
        raise jsonValError('missing ending ,', s)
    if returnAsText :
        return s[:-1]
    return json.loads('{'+s[:-1]+'}')

def saveCikFInfo(cik, cikFInfo, removeDups=False, cikFInfoDir=defaultCikFInfoDir) :
    if removeDups :
        existingCikFInfo = loadCikFInfo(cik, cikFInfoDir=cikFInfoDir)
        cikFInfo = dict((k,v) for k,v in cikFInfo.items() if k not in existingCikFInfo)
    if len(cikFInfo) == 0 :
        return
    s = json.dumps(cikFInfo, indent=0).strip()
    if s[0]!='{' or s[-1]!='}' :
        raise jsonValError('missing start/end {}', s)
    fDir, fPath = getCikFInfoDirAndPath(cik, cikFInfoDir)
    if not os.path.exists(fDir) :
        os.makedirs(fDir)
    with open(fPath,'a',encoding='ascii') as f :
        f.write(s[1:-1])
        f.write(',\n')

def saveAllCikFInfo(startD, endD, scraperClasses,
                    removeDups=True, cikFInfoDir=defaultCikFInfoDir, ciks=None) :
    dl = dailyList.dailyList(startD=startD, endD=endD)
    datesPresent = utils.loadPklFromDir(cikFInfoDir, "dates.pkl", set())
    cikInfoMap = {}
    for scraperClass in scraperClasses :
        scraper = scraperClass(startD=startD, endD=endD)
        for dInfo in scraper.infoMap.values() :
            for info in dInfo.values() :
                if info == 'ERROR' :
                    continue
                if scraper.formClass.startswith('SC 13') :
                    # fill in cik names
                    if 'ciks' in info :
                        info['cikNames'] = []
                        for cik in info['ciks'] :
                            info['cikNames'].append(dl.cikNames.get(cik.lstrip('0'),
                                                            ('CIK'+cik.lstrip('0'),))[0])
                elif scraper.formClass.startswith('INSIDER') :
                    issuerCik = None
                    for cik,cikType in zip(info['ciks'],info['cikTypes']) :
                        if cikType == 'Issuer' :
                            issuerCik = cik
                            break
                    if issuerCik is not None :
                        info['issuerName'] = dl.cikNames.get(issuerCik.lstrip('0'),
                                                             ('CIK'+issuerCik.lstrip('0'),))[0]
                elif scraper.formClass.startswith('13F') :
                    info['holdings'] = scrape13F.get13FHoldingsReportList(info['holdings'],
                                                                          minFrac=0.01)
        scraper.addToCikInfoMap(dl, cikInfoMap, ciks=ciks, excludeDates=datesPresent)
    for cik,cikFInfo in cikInfoMap.items() :
        if (ciks is not None and cik not in ciks) :
            continue
        saveCikFInfo(cik, cikFInfo, removeDups=removeDups, cikFInfoDir=cikFInfoDir)
    datesPresent.update(dl.dl.keys())
    utils.savePklToDir(cikFInfoDir, "dates.pkl", datesPresent)

def prSample(s, n=2, filterF=lambda x : True) :
    res = []
    for dStr,dInfo in s.infoMap.items() :
        for accNo,info in dInfo.items() :
            if filterF(info) :
                print(dStr,accNo,info)
                res.append(info)
                if len(res) >= n :
                    return (res[0] if n==1 else res)

def saveYears(startY, endY,
              removeDups=False, cikFInfoDir=defaultCikFInfoDir, ciks=None) :
    qList = ['0101', '0401', '0701', '1001', '0101']
    for y in range(startY, endY) :
        for qs, qe in zip(qList, qList[1:]) :
            startD, endD = f'{y}{qs}', f'{y+1 if qe=="0101" else y}{qe}'
            print(startD, endD)
            saveAllCikFInfo(startD, endD, allScraperClasses,
                            removeDups=removeDups, cikFInfoDir=cikFInfoDir, ciks=ciks)