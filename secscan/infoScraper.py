# AUTOGENERATED! DO NOT EDIT! File to edit: 06_infoScraper.ipynb (unless otherwise specified).

__all__ = ['defaultBaseScrapeDir', 'defaultCikFInfoDir', 'scraperBase']

# Cell

import copy
import json
import os
import re

from secscan import utils, dailyList, basicInfo

defaultBaseScrapeDir = os.path.join(utils.stockDataRoot,'scrapedBase')
defaultCikFInfoDir = os.path.join(utils.stockDataRoot,'cikFInfo')

# Cell

class scraperBase(object) :
    def __init__(self, infoDir, formClass, startD=None, endD=None, fSuff='m.pkl') :
        self.infoDir = infoDir
        self.formClass = formClass
        self.fSuff = fSuff
        self.pickSavePars = {}
        self.pickLoadPars = {}
        self.infoMap = {}
        self.dirtySet = set()
        if startD=='empty' :
            return
        self.loadDays(startD=startD, endD=endD)
    @utils.delegates(utils.pickSave)
    def setPickSavePars(self, **kwargs) :
        self.pickSavePars = dict(kwargs)
    @utils.delegates(utils.pickLoad)
    def setPickLoadPars(self, **kwargs) :
        self.pickLoadPars = dict(kwargs)
    def loadDays(self, startD=None, endD=None) :
        self.infoMap.update(utils.loadSplitPklFromDir(self.infoDir, startK=startD, endK=endD,
                                                      fSuff=self.fSuff, **self.pickLoadPars))
    def save(self) :
        utils.saveSplitPklToDir(self.infoMap, self.infoDir, dirtySet=self.dirtySet,
                                fSuff=self.fSuff, **self.pickSavePars)
        self.dirtySet.clear()
    def saveDays(self, daySet) :
        utils.saveSplitPklToDir(self.infoMap, self.infoDir, dirtySet=daySet,
                                fSuff=self.fSuff, **self.pickSavePars)
        self.dirtySet.difference_update(daySet)
    def scrapeInfo(self, accNo, formType=None) :
        return basicInfo.getSecFormInfo(accNo, formType), None
    def rescrapeInfo(self, accNo, info) :
        raise Exception('rescrapeInfo not implemented for this class')
    def saveXInfo(self, dStr, accNo, xInfo) :
        utils.savePklToDir(os.path.join(self.infoDir,dStr), accNo+'-xinfo.pkl', xInfo, **self.pickSavePars)
    def loadXInfo(self, dStr, accNo) :
        return utils.loadPklFromDir(os.path.join(self.infoDir,dStr), accNo+'-xinfo.pkl', None, **self.pickLoadPars)
    def retryErrs(self, startD=None, endD=None, justShow=False) :
        correctedCount = errCount = 0
        for dStr,dInfo in self.infoMap.items() :
            if ((startD is not None and dStr<startD)
                or (endD is not None and endD<=dStr)) :
                continue
            for accNo in dInfo :
                if dInfo[accNo] == 'ERROR' :
                    errCount += 1
                    if justShow :
                        print(accNo,end=' ')
                        continue
                    print('retrying',accNo)
                    dInfo[accNo] = self.scrapeForAccNo(accNo)
                    if dInfo[accNo] != 'ERROR' :
                        self.dirtySet.add(dStr)
                        correctedCount += 1
        if justShow :
            print('total of',errCount,'errors')
        else :
            print('corrected',correctedCount,'of',errCount,'errors')
    def rescrape(self, startD=None, endD=None, printAllAccNos=False, filterF=None) :
        totCount = changedCount = 0
        for dStr in sorted(self.infoMap.keys(), reverse=True) :
            if ((startD is not None and dStr<startD)
                or (endD is not None and endD<=dStr)) :
                continue
            print('===', dStr, '===', end=' ', flush=True)
            dInfo = self.infoMap[dStr]
            for accNo,info in dInfo.items() :
                if info == 'ERROR' :
                    continue
                if filterF is not None and not filterF(accNo,info) :
                    continue
                if printAllAccNos :
                    print(accNo, end=' ', flush=True)
                totCount += 1
                newInfo = self.rescrapeInfo(accNo,copy.deepcopy(info))
                if info != newInfo :
                    if printAllAccNos :
                        print()
                    else :
                        print(accNo, end=' ', flush=True)
                    for k in sorted(set(info.keys())|set(newInfo.keys())) :
                        if info.get(k) != newInfo.get(k) :
                            print(k, '<<<<<<<', info.get(k),
                                  '>>>>>>>', newInfo.get(k), flush=True)
                    changedCount += 1
                    dInfo[accNo] = newInfo
                    self.dirtySet.add(dStr)
        print()
        print(f'{changedCount} changed of {totCount} total')
        if changedCount > 0 :
            print('call scraper.save() to save')
        else :
            print('no need to save')
    def retryErrsAndSave(self, startD=None, endD=None) :
        self.retryErrs(startD=startD, endD=endD)
        self.save()
    def showErrs(self, startD=None, endD=None) :
        self.retryErrs(startD=startD, endD=endD, justShow=True)
    def checkDates(self, verbose=True) :
        "Prints info on dates present, checking for missing dates."
        dailyList.checkMapDates(self.infoMap, verbose=verbose)
    def printCounts(self, startD=None, endD=None, verbose=True) :
        if verbose :
            print()
            print('Counts by day:')
        tot = 0
        for dStr in sorted(self.infoMap.keys()) :
            if ((startD is not None and dStr<startD)
                or (endD is not None and endD<=dStr)) :
                continue
            dCount = len(self.infoMap[dStr])
            if verbose :
                print(f'{dStr}: {dCount}')
            tot += dCount
        print('Total filings:',tot)
    def scrapeForAccNo(self, accNo, formType=None) :
        try :
            info, xInfo = self.scrapeInfo(accNo, formType)
            if xInfo is not None :
                info['hasXInfo'] = True
                self.saveXInfo(dStr, accNo, xInfo)
            return info
        except Exception as e :
            print('*** ERROR ***',e)
            return 'ERROR'
    def addToCikInfoMap(self, dl, cikInfoMap, ciks=None) :
        """
        Adds to cikInfoMap a mapping cik -> {accNo -> info}
        for all forms with scraped info in self.infoMap.
        The dl argument should be a dailyList object that includes all
        the dates in self.infoMap.
        """
        for dStr,dInfo in self.infoMap.items() :
            if dStr not in dl.dl :
                raise ValueError(f'date {dStr} not found in dailyList!')
            for cik, formType, accNo, fileDate in dl.dl[dStr] :
                if ((ciks is not None and cik not in ciks)
                        or not dailyList.isInFormClass(self.formClass, formType)) :
                    continue
                if accNo not in dInfo :
                    raise ValueError(f'accNo {accNo} not found in scraped info!')
                if cik not in cikInfoMap :
                    cikInfoMap[cik] = {}
                cikInfoMap[cik][accNo] = dInfo[accNo]
    def updateForDays(self, dl, startD=None, endD=None, ciks=None,
                      errLimitPerDay=25, verbose=True, saveAfterEachDay=False,
                      cikInfoMap=None) :
        """
        Update to reflect the filings for dates between startD (inclusive)
        and endD (exclusive). If startD is None, uses the last date already
        in self.infoMap, or the start of the current year if self.infoMap is empty.
        If endD is None, uses today.
        The dl argument should be a dailyList object that includes those dates.
        Optionally restricts to a given set of CIKs.
        If cikInfoMap is supplied, updates it to map cik -> {accNo -> info}
        for all the newly parsed accNos.
        """
        if startD is None :
            if len(self.infoMap) == 0 :
                startD = utils.toDateStr()[:4]+'0101' # start of current year
            else :
                startD = max(self.infoMap.keys())
        for dStr in reversed(utils.dateStrsBetween(startD,endD)) :
            if dStr not in dl.dl :
                print('date',dStr,'not found in dailyList, aborting update!')
                return
            if dStr not in self.infoMap :
                self.infoMap[dStr] = {}
                dayIsDirty = True
            else :
                dayIsDirty = False
            if verbose or dayIsDirty :
                print(f'=========={"NEW " if dayIsDirty else ""}{dStr}==========', end=' ', flush=True)
            errCount = 0
            dInfo = self.infoMap[dStr]
            for cik, formType, accNo, fileDate in dl.dl[dStr] :
                if ((ciks is not None and cik not in ciks)
                        or not dailyList.isInFormClass(self.formClass, formType)) :
                    continue
                if accNo not in dInfo :
                    print(f"'{accNo}'", end=' ', flush=True)
                    dInfo[accNo] = self.scrapeForAccNo(accNo,formType)
                    dayIsDirty = True
                    if dInfo[accNo] == 'ERROR' :
                        errCount += 1
                if cikInfoMap is not None :
                    if cik not in cikInfoMap :
                        cikInfoMap[cik] = {}
                    cikInfoMap[cik][accNo] = dInfo[accNo]
                if errCount >= errLimitPerDay :
                    break
            if dayIsDirty :
                self.dirtySet.add(dStr)
                if saveAfterEachDay :
                    self.save()
            if errCount >= errLimitPerDay :
                print('Error limit exceeded, aborting update!')
                break
    def loadAndUpdate(self, dlOrDir=dailyList.defaultDLDir,
                      startD=None, endD=None, ciks=None, errLimitPerDay=10,
                      verbose=True, saveAfterEachDay=False) :
        """
        Loads a dailyList for the given date range (this must already have been saved),
        and then updates the scraper for the given date range and saves it.
        If startD is None, uses the last date already in self.infoMap, or the start of
        the current year if self.infoMap is empty. If endD is None, uses today.
        Optionally restricts to a given set of CIKs.
        A scraperBase or subclass can be initialized for a date range starting from an empty directory by:
            s = scraperBase(emptyDir, formClass, startD='empty')  # or s = subclass(startD='empty', ...)
            s.loadAndUpdate(startD=drangeStart, endD=drangeEnd)
            s.printCounts()
        assuming the dailyList is already saved for that date range.
        This will also work to extend a scraperBase or subclass to a new date range.
        """
        if isinstance(dlOrDir, dailyList.dailyList) :
            dl = dlOrDir
        else :
            dl = dailyList.dailyList(dlDir=dlOrDir, startD=startD, endD=endD)
        self.loadDays(startD=startD, endD=endD)
        self.updateForDays(dl, startD=startD, endD=endD, ciks=ciks, errLimitPerDay=errLimitPerDay,
                           verbose=verbose, saveAfterEachDay=saveAfterEachDay)
        self.save()