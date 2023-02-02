# AUTOGENERATED! DO NOT EDIT! File to edit: 04_getCikFilings.ipynb (unless otherwise specified).

__all__ = ['cikRestFilingsUrl', 'appendFilings', 'getRecent']

# Cell

from secscan import utils

# Cell

def cikRestFilingsUrl(cik) :
    return f'/submissions/CIK{str(cik).lstrip("0").zfill(10)}.json'

def appendFilings(res, filingList, startD) :
    fDates = [fDate.replace('-','') for fDate in filingList['filingDate']]
    print(len(fDates),'filings')
    for formType,accNo,fDate in zip(filingList['form'],
                                    filingList['accessionNumber'], fDates) :
        if startD is not None and fDate<startD :
            return True
        res.append((formType,accNo,fDate))
    return False

def getRecent(cik, startD=None, justFirst=True) :
    filingsJson = utils.downloadSecUrl(cikRestFilingsUrl(cik),
                                       restData=True, toFormat='json')['filings']
    res = []
    if appendFilings(res, filingsJson['recent'], startD) or justFirst :
        return res
    for file in filingsJson.get('files', []) :
        print('extra file from',file['filingFrom'],'to',file['filingTo'],end=': ')
        extraList = utils.downloadSecUrl(f'/submissions/{file["name"]}',
                                         restData=True, toFormat='json')
        if appendFilings(res, extraList, startD) :
            break
    return res