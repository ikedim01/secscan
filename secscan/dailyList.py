# AUTOGENERATED! DO NOT EDIT! File to edit: 02_dailyList.ipynb (unless otherwise specified).

__all__ = ['defaultDLDir', 'getQStr', 'getSecDailyIndexUrls', 'getDailyFList', 'downloadSecFormList', 'edgarTxtFPat',
           'isInFormClass', 'namedFormClasses', 'noPeriodFormTypes', 'findCikName', 'checkMapDates', 'dailyList',
           'getCikToTickersMap', 'dlCountFilings', 'loadAndUpdateDL']

# Cell

import collections
import csv
import os
import re

from secscan import utils,recentFeed

defaultDLDir = os.path.join(utils.stockDataRoot,'dlMaps')

# Cell

def getQStr(dateStr) :
    """
    Converts a date in YYYYMMDD format to YYYY/QTRn/
    where n is the quarter number from 1 to 4."
    """
    return dateStr[:4] + '/QTR' + str((int(dateStr[4:6])+2) // 3) + '/'

def getSecDailyIndexUrls(dateStr) :
    base = '/Archives/edgar/daily-index/'+getQStr(dateStr)
    return (base+'master.'+dateStr+'.idx', base+'index.json')

edgarTxtFPat = re.compile(
            # gets cik and accession no from a file url within the daily index
            r"\s*edgar/data/(\d+)" # cik - should be same as on the index line
            + r"/("+utils.accessNoPatStr+r")\.txt\s*$", # accession no
            re.IGNORECASE)

def getDailyFList(d, listIndexCache=None) :
    """
    Returns a list of SEC filed forms:
        [(cik, cikName, formType, fileDate, accNo), ... ]
    for the given date or ISO date string, retrieved from
    the SEC daily index.
    """
    dateStr = utils.toDateStr(d)
    listUrl, listIndexUrl = getSecDailyIndexUrls(dateStr)
    if listIndexCache is None or listIndexUrl not in listIndexCache :
        listIndexJson = utils.downloadSecUrl(listIndexUrl, toFormat='json')
        listIndex = set(item['name'] for item in listIndexJson['directory']['item']
                        if item['name'].startswith('master'))
        print(f'### list index {len(listIndex)}',end=' ')
        if listIndexCache is not None :
            listIndexCache[listIndexUrl] = listIndex
    else :
        listIndex = listIndexCache[listIndexUrl]
    if 'master.'+dateStr+'.idx' not in listIndex :
        print('HOLIDAY',end=' ')
        return []
    res = downloadSecFormList(listUrl)
    print('count for',dateStr+':', len(res), end=' ')
    return res

def downloadSecFormList(listUrl) :
    fListRes = utils.downloadSecUrl(listUrl)
    r = csv.reader(fListRes.splitlines(), delimiter='|')
    res = []
    for entry in r :
        if len(entry)==5 and entry[0].isdigit() :
            cik, cikName, formType, fileDate, txtF = entry
        else :
            if len(res) > 0 :
                print('invalid entry', entry)
            continue
        fileDate = fileDate.replace('-','').replace('/','')
        m = edgarTxtFPat.match(txtF)
        if not m :
            print('missing accession no in', entry)
            continue
        if m.group(1) != cik :
            print('cik mismatch in', entry)
        res.append((cik,cikName,formType,fileDate,m.group(2)))
    return res

# Cell

namedFormClasses = {  # readable names for some groups of form types
    'ALL' : '',
    'FINANCIAL' : re.compile('10-[KQ]',re.IGNORECASE),
    'ACTIVIST' : 'SC 13D',
    'FIVEPERCENT' : re.compile('SC 13[DG]',re.IGNORECASE),
    'INVESTOR' : '13F-HR',
    'ALLINVESTOR' : re.compile('13F-HR|SC 13[DG]',re.IGNORECASE),
    'INSIDER' : re.compile('4(?:/A)?$',re.IGNORECASE),
}

noPeriodFormTypes = re.compile('SC 13[DG]|424',re.IGNORECASE)

def isInFormClass(formClass,formType) :
    """
    Says if formType is in formClass, where formClass can be one of the following:
        - None or '' - includes all formTypes
        - namedFormClass - one of the ones above
        - other string - includes formTypes starting with that string
        - regex - includes matching formTypes
    """
    if formClass is None :
        return True
    if isinstance(formClass,str) :
        formClass = formClass.upper()
        if formClass in namedFormClasses :
            formClass = namedFormClasses[formClass]
    if isinstance(formClass,str) :
        return formType.startswith(formClass)
    # else assume it's a regex
    return formClass.match(formType) is not None

# Cell

def findCikName(cikName,oldNames) :
    """
    Checks if a CIK name already appears in a list of old names (case insensitive).
    Returns the position if it appears, else -1.
    """
    cikName = cikName.casefold()
    for i,oldName in enumerate(oldNames) :
        if cikName == oldName.casefold() :
            return i
    return -1

def checkMapDates(dMap, verbose=True) :
    "Prints info on dates present present in a map, checking for missing dates."
    startD = min(dMap.keys())
    endD = max(dMap.keys())
    print(f'start date: {startD}, end date: {endD}')
    nNotPresent = 0
    for dStr in utils.dateStrsBetween(startD,endD) :
        if dStr not in dMap :
            nNotPresent += 1
            if verbose :
                print(dStr,'not present!')
    print(f'total of {len(dMap)} dates, {nNotPresent} missing')

class dailyList(object) :
    def __init__(self, dlDir=defaultDLDir, startD=None, endD=None, fSuff='m.pkl', **pickle_kwargs) :
        """
        Creates a dailyList object and loads lists for the date range [startD..endD), along with
        the full CIK name maps. By default (startD=None, endD=None) loads all dates present.
        Use startD='empty' to create an empty object.
        """
        self.dlDir = dlDir
        self.fSuff = fSuff
        self.pickle_kwargs = dict(pickle_kwargs)
        self.dl = {}
        if startD=='empty' :
            self.cikNames, self.cikOldNames = {}, {}
            return
        self.loadDays(startD=startD, endD=endD)
        self.cikNames = utils.loadPklFromDir(dlDir, 'cikNames.pkl', {}, **pickle_kwargs)
        self.cikOldNames = utils.loadPklFromDir(dlDir, 'cikOldNames.pkl', {}, **pickle_kwargs)
    def loadDays(self, startD=None, endD=None) :
        """
        Loads lists for the given date range into an already created dailyList object.
        """
        self.dl.update(utils.loadSplitPklFromDir(self.dlDir, startK=startD, endK=endD,
                                                 fSuff=self.fSuff, **self.pickle_kwargs))
    def save(self, dirtySet=None) :
        """
        Saves daily lists and name maps to self.dlDir.
        By default just saves days with no list already present.
        See utils.saveSplitPklToDir for other possibilities based on the dirtySet argument.
        """
        utils.saveSplitPklToDir(self.dl, self.dlDir, dirtySet=dirtySet, fSuff=self.fSuff, **self.pickle_kwargs)
        utils.savePklToDir(self.dlDir, 'cikNames.pkl', self.cikNames, **self.pickle_kwargs)
        utils.savePklToDir(self.dlDir, 'cikOldNames.pkl', self.cikOldNames, **self.pickle_kwargs)
    def updateCikNamesFromEntry(self, dStr, cik, cikName) :
        """
        Updates the name maps
            self.cikNames: cik -> (name, latestDateStr)
            self.cikOldNames: cik -> [oldname1, oldname2, ... ]
        to reflect an entry (cik, cikName, ... ) from the daily index for dStr.
        """
        if cik not in self.cikNames : # completely new name
            self.cikNames[cik] = (cikName, dStr)
            return
        # make sure self.cikNames contains the latest name
        if dStr < self.cikNames[cik][1] :
            # name in self.cikNames is newer than this entry
            oldName = cikName
        else :
            # this entry is newer than the name in self.cikNames - update it
            oldName = self.cikNames[cik][0]
            self.cikNames[cik] = (cikName, dStr)
        curName = self.cikNames[cik][0]
        if curName.casefold() == oldName.casefold() :
            # new and old names are the same (case insensitive)
            return
        # oldName is different from curName - update self.cikOldNames:
        if cik not in self.cikOldNames :
            self.cikOldNames[cik] = [oldName]
            return
        # add the old name if it's not in the list of old names:
        oldNames = self.cikOldNames[cik]
        if findCikName(oldName, oldNames) < 0 :
            oldNames.append(oldName)
        # delete the current name if it's in the list of old names:
        i = findCikName(curName, oldNames)
        if i >= 0 :
            del oldNames[i]
    def updateDayUsingL(self, dStr, dailyL, clearDay=True) :
        if clearDay :
            self.dl[dStr] = []
        for cik, cikName, formType, fileDate, accNo in dailyL :
            self.dl[dStr].append((cik, formType, accNo, fileDate))
            self.updateCikNamesFromEntry(dStr, cik, cikName)
    def checkAgainstMaster(self, year=None, quarter=None, fixMissingDate=False) :
        """
        Checks this list against the SEC combined master list.
        Returns True if no missing filings (filings in master but not in this list).
        If missing filings are found:
        - if fixMissingDate is False, returns False.
        - otherwise tries to fix this list by adding the missing filings and adding it,
          and returns True if successful.
        """
        if year is None :
            url = '/Archives/edgar/full-index/master.idx'
        else :
            url = f'/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx'
        masterL = downloadSecFormList(url)
        allAccNos = self.getAllAccNos()
        print('checking against master ...')
        missingL = [tup for tup in masterL if tup[-1] not in allAccNos]
        if len(missingL) == 0 :
            print('no missing filings found!')
            return True
        missingFDates = sorted(set(tup[-2] for tup in missingL))
        print(len(missingL),'missing filings found, fDates',missingFDates)
        print('fTypes',sorted(set(tup[2] for tup in missingL)))
        print('accNos[:50]',sorted(set(tup[-1] for tup in missingL))[:50])
        if not fixMissingDate :
            print('*** RUN WITH fixMissingDate=True TO FIX ***')
            return False
        if len(missingFDates) != 1 :
            print('unable to fix missing dates - ambiguous')
            return False
        dStr = missingFDates[0]
        if dStr not in self.dl :
            print('unable to fix missing dates - unexpected day, not in daily map')
            return False
        print('adding',len(missingL),'entries to',dStr)
        self.updateDayUsingL(dStr, missingL, clearDay=False)
        self.save(dirtySet={dStr})
        return True
    def updateForDays(self, startD=None, endD=None) :
        """
        Update to reflect the filings for dates between startD (inclusive)
        and endD (exclusive). If startD is None, uses the last date already
        in self.dl, or the start of the current year if self.dl is empty.
        If endD is None, uses today.
        Retrieves the filings info from the SEC daily index using getDailyFList.
        """
        if startD is None :
            if len(self.dl) == 0 :
                startD = utils.toDateStr()[:4]+'0101' # start of current year
            else :
                startD = max(self.dl.keys())
        listIndexCache = {}
        for dStr in reversed(utils.dateStrsBetween(startD,endD)) :
            if dStr in self.dl :
                print('SKIP'+dStr, end=' ')
            elif utils.isWeekend(dStr) :
                self.dl[dStr] = []
                print('WEEKEND'+dStr, end=' ')
            else :
                print('UPDATE'+dStr, end=' ')
                self.updateDayUsingL(dStr, getDailyFList(dStr,listIndexCache))
                print('*',end=' ')
    def getAllFormTypes(self) :
        "Returns all form types found."
        res = set()
        for l in self.dl.values() :
            res.update(formType for _,formType,_,_ in  l)
        return res
    def getCiksFiling(self, formClass=None) :
        "Returns all ciks who have filed any forms in formClass."
        res = set()
        for l in self.dl.values() :
            res.update(cik for cik,formType,_,_ in l
                       if isInFormClass(formClass,formType))
        return res
    def getAllAccNos(self) :
        res = set()
        for l in self.dl.values() :
            res.update(accNo for _,_,accNo,_ in l)
        return res
    def getFilingsList(self, ciks=None, formClass=None) :
        """
        Returns a list of filings for the given ciks (may be a set or None for all CIKs),
        that are in formClass. The list is is the form:
            [(dlDate, name, formType, accNo, fileDate),
             ... ]
        and is sorted lexicographically on those fields, except in reverse order on dlDate
        (most recent dates appear first).
        Also returns a dict mapping each cik -> the set of accession numbers for its filings.
        """
        res = []
        accNosByCik = collections.defaultdict(set)
        for dDate,l in self.dl.items() :
            for cik, formType, accNo, fileDate in l :
                if (ciks is None or cik in ciks) and isInFormClass(formClass,formType):
                    res.append((dDate,self.cikNames[cik][0],formType,accNo,fileDate))
                    accNosByCik[cik].add(accNo)
        res.sort()
        res.sort(key = lambda x : x[0], reverse=True)
        return res, accNosByCik
    def restrictedCikNameMap(self, ciks) :
        "Create a dict : cik -> latest name restricted to a given list or set of ciks."
        return dict((cik,self.cikNames[cik][0]) for cik in ciks)
    def checkDates(self, verbose=True) :
        "Prints info on dates present, checking for missing dates."
        checkMapDates(self.dl, verbose=verbose)

def getCikToTickersMap() :
    """
    Retrieves and parses an SEC-maintained list mapping tickers to CIKs.
    Returns a defaultdict: cik -> list of corresponding tickers
    """
    tickersJSON = utils.downloadSecUrl('/files/company_tickers.json', toFormat='json')
    cikToTickers = collections.defaultdict(list)
    for v in tickersJSON.values() :
        cikToTickers[str(v['cik_str'])].append(v['ticker'])
    return cikToTickers

def dlCountFilings(dlDir=defaultDLDir, startD=None, endD=None, ciks=None,
                   formClass=None, noAmend=False,
                   fSuff='m.pkl', **pickle_kwargs) :
    """
    Convenience function to count number of filings in a date range, optionally restricting
    to ciks and formClass.
    """
    dl = dailyList(dlDir=dlDir, startD=startD, endD=endD, fSuff=fSuff, **pickle_kwargs)
    if noAmend :
        formClass = re.compile(formClass+'(?!/)',re.IGNORECASE)
    fList,_ = dl.getFilingsList(ciks=ciks, formClass=formClass)
    return len(fList)

def loadAndUpdateDL(dlDir=defaultDLDir, startD=None, endD=None, uStartD=None, uEndD=None,
                    fSuff='m.pkl', dirtySet=None, **pickle_kwargs) :
    """
    Creates a dailyList object and loads lists for the date range [startD..endD), along with
    the full CIK name maps. By default (startD=None, endD=None) loads all dates present.
    Then updates to reflect the filings for dates between uStartD (inclusive)
    and uEndD (exclusive), and saves. If uStartD is None, uses the last date already
    in the loaded dailyList, or the start of the current year if the loaded dailyList
    is empty. If uEndD is None, uses today.
    Use startD='empty' to start with an empty dailyList.

    A dailyList can be initialized for a date range starting from an empty directory by:
        dl = loadAndUpdateDL(dlDir=emptyDir, startD='empty', uStartD=drangeStart, uEndD=drangeEnd)
    An dailyList in an existing directory can be updated up to and including yesterday by:
        dl = loadAndUpdateDL(dlDir=existingDir)
    """
    dl = dailyList(dlDir=dlDir, startD=startD, endD=endD, fSuff=fSuff, **pickle_kwargs)
    dl.updateForDays(startD=uStartD, endD=uEndD)
    dl.save(dirtySet=dirtySet)
    return dl