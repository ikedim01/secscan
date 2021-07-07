# AUTOGENERATED! DO NOT EDIT! File to edit: 05_basicInfo.ipynb (unless otherwise specified).

__all__ = ['getSecFormLinkList', 'getSecFormCikList', 'getTextAfterTag', 'getSecFormInfo', 'companyNameAndCikPat',
           'periodPat', 'periodDatePatStr', 'periodDatePat', 'acceptedPat', 'acceptedDateTimePat']

# Cell

import re

from secscan import utils,dailyList

# Cell

def getSecFormLinkList(indexSoup,accessNo) :
    """
    Returns
        sublinkList,completeTextLink
    where sublinkList is:
        [(name, description, type, sublink), ... ]
    Prints a warning message if the complete text link is missing.
    """
    linkList = []
    completeLink = None
    for row in indexSoup.find_all('tr') :
        entries = row.find_all('td')
        if len(entries)>1 and row.a is not None :
            #print utils.getCombSoupText(entries[3])
            if utils.getCombSoupText(entries[0]).isdigit() and len(entries)>=4 :
                linkList.append((utils.getCombSoupText(row.a),
                                 utils.getCombSoupText(entries[1]),
                                 utils.getCombSoupText(entries[3]),
                                 row.a.get('href','')))
            elif utils.getCombSoupText(entries[1]).lower().startswith('complete') :
                completeLink = row.a.get('href','')
    if not completeLink :
        print('missing complete text link in',utils.secIndexUrl(accessNo,True))
    return linkList, completeLink

companyNameAndCikPat = re.compile(r'(.*)\s*\(.*cik[\s:]*(\d+)',re.IGNORECASE)
def getSecFormCikList(indexSoup,accessNo) :
    """
    Returns list of CIKs for the form: [cik, ... ]
    """
    cikList = []
    for companyNameTag in indexSoup.find_all('span','companyName') :
        companyNameStr = utils.getCombSoupText(companyNameTag)
        m = companyNameAndCikPat.match(companyNameStr)
        if m is None :
            print('missing company name or CIK in',companyNameStr)
            print(utils.secIndexUrl(accessNo,True))
        elif m.group(2) not in cikList :
            cikList.append(m.group(2))
    if len(cikList) == 0 :
        print('no company names in',utils.secIndexUrl(accessNo,True))
    return cikList

def getTextAfterTag(resDict, resKey, top, firstTagPat,
                    firstTagName='div', firstTagClass='infoHead',
                    nextTagName='div', nextTagClass='info',
                    missingMessage=None) :
    """
    Looks for a sequence of two HTML elements specified by name and class,
    with the text of the first element matching a given regular expression.
    If found, stores the text of the second element in resDict[resKey].
    If not found and missingMessage is not None, prints it.
    """
    for firstTag in top.find_all(firstTagName,firstTagClass) :
        if firstTagPat.match(utils.getCombSoupText(firstTag)) :
            nextTag = firstTag.find_next_sibling(nextTagName,nextTagClass)
            if nextTag is not None :
                resDict[resKey] = utils.getCombSoupText(nextTag)
                return
    if missingMessage is not None :
        print(missingMessage)

periodPat = re.compile('period',re.IGNORECASE)
periodDatePatStr = r'\d\d\d\d-\d\d-\d\d'
periodDatePat = re.compile(periodDatePatStr)
acceptedPat = re.compile('accepted',re.IGNORECASE)
acceptedDateTimePat = re.compile('('+periodDatePatStr+r')[ t](\d\d:\d\d:\d\d)',
                                 re.IGNORECASE)

def getSecFormInfo(accessNo) :
    indexSoup = utils.downloadSecUrl(accessNo, toFormat='soup')
    indexFullUrl = utils.secIndexUrl(accessNo,True)
    links, completeLink = getSecFormLinkList(indexSoup,accessNo)
    res = {
        'links': links,
        'complete': completeLink,
        'ciks' : getSecFormCikList(indexSoup,accessNo)
    }
    if (links and dailyList.noPeriodFormTypes.match(links[0][2])) :
        missingPeriodMessage = None
    else :
        missingPeriodMessage = 'missing period in ' + indexFullUrl
    getTextAfterTag(res, 'period', indexSoup, periodPat,
                    missingMessage=missingPeriodMessage)
    if 'period' in res and not periodDatePat.match(res['period']) :
        print('malformed period',res['period'],'in',indexFullUrl)
        del res['period']
    getTextAfterTag(res, 'acceptDateTime', indexSoup, acceptedPat,
                    missingMessage='missing accepted in ' + indexFullUrl)
    if 'acceptDateTime' in res :
        m = acceptedDateTimePat.match(res['acceptDateTime'])
        if not m :
            print('malformed accept date/time',res['acceptDateTime'])
            print('in',indexFullUrl)
        else :
            res['acceptDate'] = m.group(1)
            res['acceptTime'] = m.group(2)
        del res['acceptDateTime']
    return res