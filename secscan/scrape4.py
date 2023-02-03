# AUTOGENERATED! DO NOT EDIT! File to edit: 12_scrape4.ipynb (unless otherwise specified).

__all__ = ['default4Dir', 'formatF4Num', 'formatTrans', 'getForm4Value', 'parse34', 'scraper4', 'form4ReportingNamePat',
           'form4ReportingCikPat', 'form4TransactionPat', 'form4ValueFieldsAndPats', 'form4ValueFields',
           'form4ValuePats', 'form4ADCodes', 'form4DICodes', 'form4TransactionCodes']

# Cell

import collections
import itertools
import numpy as np
import os
import re

from secscan import utils, dailyList, basicInfo, infoScraper

default4Dir = os.path.join(utils.stockDataRoot,'scraped4')

# Cell

form4ReportingNamePat = re.compile('rptownername',re.IGNORECASE)
form4ReportingCikPat = re.compile('rptownercik',re.IGNORECASE)
form4TransactionPat = re.compile('(non)?derivativetransaction',re.IGNORECASE)
form4ValueFieldsAndPats = (
    ('title',re.compile('(security)?title',re.IGNORECASE)),
    ('trDate',re.compile('(transaction)?date',re.IGNORECASE)),
    ('trCcode',re.compile('(transaction)?code',re.IGNORECASE)),
    ('aOrD',re.compile('(transaction)?acquireddisposedcode',re.IGNORECASE)),
    ('count',re.compile('(transaction)?shares',re.IGNORECASE)),
    ('price',re.compile('(transaction)?pricepershare',re.IGNORECASE)),
    ('ownership',re.compile('natureofownership?',re.IGNORECASE)),
    ('directOrIndirect',re.compile('directorindirectownership',re.IGNORECASE)),
    ('remaining',re.compile('(shares)?ownedfollowingtransaction',re.IGNORECASE)),
)
form4ValueFields = [field for field,_ in form4ValueFieldsAndPats]
form4ValuePats = [pat for _,pat in form4ValueFieldsAndPats]

#Form 4 transaction codes from SEC:
#General Transaction Codes
#P - Open market or private purchase of non-derivative or derivative security
#S - Open market or private sale of non-derivative or derivative security
#V - Transaction voluntarily reported earlier than required
#
#Rule 16b-3 Transaction Codes
#A - Grant, award or other acquisition pursuant to Rule 16b-3(d)
#D - Disposition to the issuer of issuer equity securities pursuant to
#    Rule 16b-3(e)
#F - Payment of exercise price or tax liability by delivering or withholding
#    securities incident to the receipt, exercise or vesting of a security
#    issued in accordance with Rule 16b-3
#I - Discretionary transaction in accordance with Rule 16b-3(f) resulting
#    in acquisition or disposition of issuer securities
#M - Exercise or conversion of derivative security exempted pursuant to
#    Rule 16b-3
#
#Derivative Securities Codes (Except for transactions exempted pursuant to
#            Rule 16b-3)
#C - Conversion of derivative security
#E - Expiration of short derivative position
#H - Expiration (or cancellation) of long derivative position with value
#    received
#O - Exercise of out-of-the-money derivative security
#X - Exercise of in-the-money or at-the-money derivative security
#
#Other Section 16(b) Exempt Transaction and Small Acquisition Codes (except for
#            Rule 16b-3 codes above)
#G - Bona fide gift
#L - Small acquisition under Rule 16a-6
#W - Acquisition or disposition by will or the laws of descent and distribution
#Z - Deposit into or withdrawal from voting trust
#
#Other Transaction Codes
#J - Other acquisition or disposition (describe transaction)
#K - Transaction in equity swap or instrument with similar characteristics
#U - Disposition pursuant to a tender of shares in a change of control
#    transaction
form4ADCodes = {'A':'+', 'D':'-'}
form4DICodes = {'D':'directly owned', 'I':'indirectly owned'}
form4TransactionCodes = {
    'P':'open market buy',
    'S':'open market sell',
    'V':'early report',
    'A':'grant/award R16b-3',
    'D':'disposition to issuer R16b-3',
    'F':'payment by delivering/withholding R16b-3',
    'I':'discretionary transaction R16b-3',
    'M':'exempt derivative exercise R16b-3',
    'C':'conversion of derivative',
    'E':'expiration/short',
    'H':'expiration/long',
    'O':'out-of-the-money exercise',
    'X':'in-the-money exercise',
    'G':'gift',
    'L':'small acquisition R16a-6',
    'W':'inheritance',
    'Z':'transfer with voting trust',
    'J':'other',
    'K':'equity swap',
    'U':'change of control',
}
def formatF4Num(numStr) :
    numStr = numStr.replace(',','')
    try :
        return f'{int(numStr):,}'
    except :
        try :
            return f'{float(numStr):,}'
        except :
            return numStr
def formatTrans(trans) :
    return ' '.join([trans[1],'&nbsp;',trans[0],
        f'<b>{form4ADCodes.get(trans[3].upper(),"???")}{formatF4Num(trans[4])}',
        f'={formatF4Num(trans[8])} @{trans[5]}</b>',
        f'({form4TransactionCodes.get(trans[2].upper(),"???")}, {form4DICodes.get(trans[7].upper(),"???")})',
    ]).lower().capitalize().replace(' a ',' A ').replace(' b ',' B ').replace(' c ',' C ')

def getForm4Value(transSoup,tagPat) :
    tag = transSoup.find(tagPat)
    #if tag :
    #    tag = tag.find('value')
    if tag :
        return utils.getCombSoupText(tag)
    return ''

def parse34(accNo, formType=None) :
    info = basicInfo.getSecFormInfo(accNo, formType)
    links = info['links']
    info['transactions'] = []
    info['reportingName'] = []
    info['reportingCik'] = []
    try :
        form4Soup = utils.downloadSecUrl(links[1][-1], toFormat='soup')
        for trans in form4Soup.find_all(form4TransactionPat) :
            info['transactions'].append(tuple(getForm4Value(trans,vPat) for vPat in form4ValuePats))
        for rNameTag in form4Soup.find_all(form4ReportingNamePat) :
            info['reportingName'].append(utils.getCombSoupText(rNameTag).strip())
        for cikTag in form4Soup.find_all(form4ReportingCikPat) :
            info['reportingCik'].append(utils.getCombSoupText(cikTag).strip().lstrip('0'))
    except Exception as e:
        print('missing or invalid form 4 XML file:',e)
    for k in ['transactions', 'reportingName', 'reportingCik'] :
        if len(info[k]) == 0 :
            print(f'*** NO {k.upper()} ***')
    return info

class scraper4(infoScraper.scraperBase) :
    @utils.delegates(infoScraper.scraperBase.__init__)
    def __init__(self, infoDir=default4Dir, **kwargs) :
        super().__init__(infoDir, 'INSIDER', **kwargs)
    def scrapeInfo(self, accNo, formType=None) :
        return parse34(accNo, formType), None
    def rescrapeInfo(self, accNo, info) :
        return parse34(accNo)