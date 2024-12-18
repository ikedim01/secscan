# AUTOGENERATED! DO NOT EDIT! File to edit: 09_scrape6K.ipynb (unless otherwise specified).

__all__ = ['default6KDir', 'parse6K', 'scraper6K', 'reg12gStr', 'header6KPat', 'signaturePat', 'skipJunkPat']

# Cell

import collections
import itertools
import os
import re

from secscan import utils, dailyList, basicInfo, infoScraper

default6KDir = os.path.join(utils.stockDataRoot,'scraped6K')

# Cell

reg12gStr = r'12g3(?:\s*.\s*2\s*\(b\))?'
header6KPat = re.compile(r'.*(?:'
               + r'pursuant.{1,20}'+reg12gStr+r'.{1,100}?\b1934\b(?:.{1,40}\bno\b..)?'
               + r'|' + r'is marked.{1,100}'+reg12gStr+'..'
               + r'|' + r'101\s*\(b\)\s*\(7\)(?:\s*only\s*permits.{1,700}on edgar.)?'
               + r'|' + r'101\s*\(b\)\s*\(1\)(?:\s*only\s*permits.{1,150}holders.)?'
               + r'|' + r'20-Fb\)\s*\(1\)'
               + r'|' + r'20-F.{1,40}40-F'
               + r')',re.IGNORECASE)
signaturePat = re.compile(r'.{1,20}signatures?\s*pursuant.{1,200}authorized.(?:.{1,300}(?:officer|president|ceo))?',
                         re.IGNORECASE)
skipJunkPat = re.compile(r'[^a-z]{1,40}',re.IGNORECASE)

def parse6K(accNo, formType=None, textLimit=basicInfo.defaultTextLimit) :
    info = basicInfo.getSecFormInfo(accNo, formType=formType, get99=True, textLimit=textLimit)
    mainText = utils.downloadSecUrl(info['links'][0][3], toFormat='souptext')
    m = header6KPat.match(mainText)
    if m :
        mainText = mainText[m.end():]
        # print(endPos, mainText[endPos:endPos+400])
        # print()
    else :
        print('no header')
    for pat in [signaturePat, skipJunkPat] :
        m = pat.match(mainText)
        if m :
            mainText = mainText[m.end():]
    info['mainText'] = mainText[:textLimit].strip()
    return info

class scraper6K(infoScraper.scraperBase) :
    @utils.delegates(infoScraper.scraperBase.__init__)
    def __init__(self, infoDir=default6KDir, **kwargs) :
        super().__init__(infoDir, '6-K', **kwargs)
    def scrapeInfo(self, accNo, formType=None) :
        return parse6K(accNo, formType), None
    def getTextDigest(self, info) :
        res = []
        if 'mainText' in info :
            res.extend(['START MAIN TEXT.',info['mainText'].strip(),'END MAIN TEXT.'])
        for prText in info.get('text99',[]) :
            if len(prText.strip()) > 0 :
                res.extend(['START PRESS RELEASE.',prText.strip(),'END PRESS RELEASE.'])
        return ' '.join(res)