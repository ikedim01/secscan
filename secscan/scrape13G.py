# AUTOGENERATED! DO NOT EDIT! File to edit: 10_scrape13G.ipynb (unless otherwise specified).

__all__ = ['default13GDir', 'getSec13NshAndPctFromText', 'cusipChecksum', 'monthNameToIso', 'getMonthPatStr',
           'parseEventDate', 'parse13GD', 'scraper13G', 'nSharesPatStr', 'nPctPatStr', 'form13NshAndPctPats',
           'purposePat', 'strictCusipPatStr', 'cusipPatStr', 'cusipNumberPatStr', 'cusipSearchPats', 'spaceDashPat',
           'monthNames', 'monthAbbrevStrs', 'monthPatStr', 'dateOfEventPatStr', 'dateOfEventMonthPat1',
           'dateOfEventMonthPat2', 'dateOfEventNumPat1', 'dateOfEventNumPat2', 'updateCik13GDPos']

# Cell

import collections
import itertools
import os
import re

from secscan import utils, dailyList, basicInfo, infoScraper

default13GDir = os.path.join(utils.stockDataRoot,'scraped13G')

# Cell

nSharesPatStr = r'(\d+(?:[,.]\d\d\d)*)'
nPctPatStr = r'(\d+(?:\.\d*)?|\.\d+)'
form13NshAndPctPats = [
    re.compile(r'aggregate\s+amount.{1,100}?' + nSharesPatStr
                + r'.{1,200}?' + r'percent\s+of\s+class.{1,100}?' + nPctPatStr + r'\s*%',
                re.IGNORECASE|re.DOTALL),
    re.compile(r'item\s+9\s*:.*?' + nSharesPatStr
                + r'.*?' + r'item\s+11\s*:.*?' + nPctPatStr + r'\s*%',
                re.IGNORECASE|re.DOTALL),
    re.compile(r'aggregate\s+amount.{1,100}?' + nSharesPatStr
                + r'.{1,200}?' + r'percent\s+of class.{1,100}?(?!\D9\D)\D' + nPctPatStr,
                re.IGNORECASE|re.DOTALL),
]
def getSec13NshAndPctFromText(txt) :
    "Returns a list [(nShares, percent) ... ] parsed from form 13G or 13D."
    for pat in form13NshAndPctPats :
        res = pat.findall(txt)
        if res :
            break
    return res

purposePat = re.compile(r'4\s*\.?\s*purpose\s*of\s*(?:the\s*)?transaction(?:\s*\.?\s*)(.{1,10000}?)'
                        + r'(?:\s*(?:item\s*)?5\s*\.?\s*interest'
                            + r'|\s*(?:item\s*)?6\s*\.?\s*contracts'
                            + r'|\s*(?:item\s*)?7\s*\.?\s*material'
                            + r'|\s*after\s*reasonable\s*inquiry'
                            + r'|\s*$'
                        + r')',
                        re.IGNORECASE|re.DOTALL)

def cusipChecksum(cusip) :
    s = 0
    for i,c in enumerate(cusip[:8]) :
        if c.isdigit() :
            v = ord(c) - ord('0')
        elif c.isalpha() :
            v = 10 + ord(c.upper()) - ord('A')
        if (i&1) == 1 :
            v *= 2
        s += (v//10) + (v%10)
    return str((10 - (s%10)) % 10)

strictCusipPatStr = r'[\dA-Z]\d[\dA-Z]\d[\dA-Z]{4}\d'
cusipPatStr = (r'[\dA-Z]\d[\dA-Z][-_\s]*\d[-_\s]*[\dA-Z][-_\s]*[\dA-Z]'
                + r'(?:[-_\s]*[\dA-Z]{2}(?:[-_\s]*\d)?)?')
cusipNumberPatStr = r'cusip\s*(?:number|#|no)'
cusipSearchPats = [re.compile(patStr, re.IGNORECASE|re.DOTALL) for patStr in [
    r'.{1,3000}?[^\dA-Z](' + cusipPatStr + r')[^2-9A-Z]{0,200}?\s*' + cusipNumberPatStr,
    r'.{1,3000}?\s*' + cusipNumberPatStr + r'[^\dA-Z]{0,200}?(' + cusipPatStr + r')[^\dA-Z]',
    r'.{1,2000}?\s(' + strictCusipPatStr + r')\s',
]]
spaceDashPat = re.compile(r'[-\s]*')

monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
monthAbbrevStrs = ''.join(monthName[:3].lower() for monthName in monthNames)
def monthNameToIso(monthName) :
    return str(1+(monthAbbrevStrs.find(monthName[:3].lower())//3)).zfill(2)
def getMonthPatStr() :
    monthNamePatStrs = []
    for monthName in monthNames :
        monthNamePatStr = monthName[:3]
        if monthName != 'May' :
            monthNamePatStr += r'(?:'
            if monthName == 'September' :
                monthNamePatStr += r't|t\.|'
            monthNamePatStr += monthName[3:]
            monthNamePatStr += r'|\.)?'
        monthNamePatStrs.append(monthNamePatStr)
    return '(' + '|'.join(monthNamePatStrs) + ')'
monthPatStr = getMonthPatStr()
dateOfEventPatStr = r'dates?\s*of\s*events?\s*which'
dateOfEventMonthPat1 = re.compile(r'.{1,3000}?[^\dA-Z]'+monthPatStr+r'\s*(\d\d?)(?:\s*th)?'
                                  +r'\s*(?:,|\s)\s*(\d\d\d\d)[^\d].{0,120}?'+dateOfEventPatStr,
                                 re.IGNORECASE|re.DOTALL)
dateOfEventMonthPat2 = re.compile(r'.{1,3000}?[^\dA-Z](\d\d?)(?:\s*th)?\s*'+monthPatStr
                                 +r'(?:,|\s)\s*(\d\d\d\d)[^\d].{0,120}?'+dateOfEventPatStr,
                                 re.IGNORECASE|re.DOTALL)
dateOfEventNumPat1 = re.compile(r'.{1,3000}?[^\d](\d\d?)\s*[-/]\s*(\d\d?)\s*[-/]\s*'
                                +r'(\d\d\d\d)[^\d].{0,120}?'+dateOfEventPatStr,
                                 re.IGNORECASE|re.DOTALL)
dateOfEventNumPat2 = re.compile(r'.{1,3000}?[^\d](\d\d\d\d)\s*[-/]\s*(\d\d?)\s*[-/]\s*'
                                +r'(\d\d?)[^\d].{0,120}?'+dateOfEventPatStr,
                                 re.IGNORECASE|re.DOTALL)
def parseEventDate(info,mainText) :
    m = dateOfEventMonthPat1.match(mainText)
    if m :
        info['eventDate'] = '-'.join([m.group(3),monthNameToIso(m.group(1)),m.group(2).zfill(2)])
        return
    m = dateOfEventMonthPat2.match(mainText)
    if m :
        info['eventDate'] = '-'.join([m.group(3),monthNameToIso(m.group(2)),m.group(1).zfill(2)])
        return
    m = dateOfEventNumPat1.match(mainText)
    if m :
        info['eventDate'] = '-'.join([m.group(3),m.group(1).zfill(2),m.group(2).zfill(2)])
        return
    m = dateOfEventNumPat2.match(mainText)
    if m :
        info['eventDate'] = '-'.join([m.group(1),m.group(2).zfill(2),m.group(3).zfill(2)])
        return
    print('NO EVENT DATE!')


def parse13GD(accNo, formType=None) :
    info = basicInfo.getSecFormInfo(accNo, formType=formType)
    if 'filedByCik' not in info :
        print('No filed by CIK!')
    links = info['links']
    if len(links) == 0 :
        print('NO LINKS LIST!')
        info['positions'] = []
    else :
        toFormat = 'text' if links[0][3].endswith('.txt') else 'souptext'
        mainText = utils.downloadSecUrl(links[0][3], toFormat=toFormat)
        parseEventDate(info,mainText)
        info['positions'] = getSec13NshAndPctFromText(mainText)
        for cusipSearchPat in cusipSearchPats :
            m = cusipSearchPat.match(mainText)
            if m is not None :
                break
        if m is None :
            if not ('0001504304' in info['ciks'] or '0001067621' in info['ciks']) :
                # suppress the message for 0001504304 - Bulldog Investors
                # and 0001067621 - Phillip Goldstein
                # - they don't report CUSIPs in their filings
                print('no CUSIP found!')
        else :
            cusip = spaceDashPat.sub('',m.group(1))
            if len(cusip) == 6 :
                print('adding 10 to CUSIP', cusip, end=' ')
                cusip = cusip + '10'
            if len(cusip) == 8 :
                print('adding checksum to CUSIP', cusip)
                if cusipChecksum('0'+cusip[:7]) == cusip[7] :
                    cusip = '0'+cusip
                else :
                    cusip = cusip + cusipChecksum(cusip)
            if len(cusip)!=9 or cusip[8]!=cusipChecksum(cusip) :
                print('invalid CUSIP!',cusip)
            info['cusip'] = cusip.upper()
            # print('CUSIP-'+cusip,end=' ')
        if formType is None :
            formType = links[0][2]
        if formType.upper().startswith('SC 13D') :
            m = purposePat.search(mainText)
            if m is None :
                print('no purpose!', end=' ')
            else :
                info['purpose'] = m.group(1)
    if len(info['positions']) == 0 :
        print('no positions found!')
    return info #,mainText

class scraper13G(infoScraper.scraperBase) :
    def __init__(self, infoDir=default13GDir, startD=None, endD=None, fSuff='m.pkl', **pickle_kwargs) :
        super().__init__(infoDir, 'SC 13G', startD=startD, endD=endD, fSuff=fSuff, **pickle_kwargs)
    def scrapeInfo(self, accNo, formType=None) :
        return parse13GD(accNo, formType=formType), None

# Cell

def updateCik13GDPos(scrapers, cik13GDPosMap=None) :
    """
    Generate or update a combined dict of percentage holdings:
        cik13GDPosMap: cik -> {cusip -> (eventDate, accNo, pct)}
    based on a list of 13G and 13D scrapers.
    """
    if cik13GDPosMap is None :
        cik13GDPosMap = collections.defaultdict(dict)
    cikTo13GDs = collections.defaultdict(list)
    count = 0
    for scraper in scrapers :
        for dStr, accNoToInfo in scraper.infoMap.items() :
            for accNo, info in accNoToInfo.items() :
                if info == 'ERROR' :
                    print('ERR',accNo)
                elif 'filedByCik' not in info :
                    print('No filed by CIK',accNo)
                elif 'cusip' not in info :
                    print('no CUSIP',accNo)
                elif len(info['positions']) == 0 :
                    print('no positions found',accNo)
                elif 'eventDate' not in info :
                    print('no event date',info)
                else :
                    cikTo13GDs[info['filedByCik'].lstrip('0')].append(
                        (info['cusip'], info['eventDate'], accNo, max(float(pct) for _,pct in info['positions'])))
                    count += 1
    print('total of',len(cikTo13GDs),'ciks,',count,'13G/D filings')
    for cik, cik13GDList in cikTo13GDs.items() :
        posMap = cik13GDPosMap[cik]
        for tup in cik13GDList :
            cusip = tup[0]
            if cusip not in posMap or posMap[cusip] < tup[1:] :
                posMap[cusip] = tup[1:]
    return cik13GDPosMap