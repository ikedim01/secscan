# AUTOGENERATED! DO NOT EDIT! File to edit: 11_scrape13D.ipynb (unless otherwise specified).

__all__ = ['default13DDir', 'scraper13D', 'get13GDDatesForQ', 'getCombNSSForQ', 'oddballScreen']

# Cell

import collections
import itertools
import numpy as np
import os
from pathlib import Path
import re

from secscan import utils, dailyList, basicInfo, infoScraper, scrape13F, scrape13G

default13DDir = os.path.join(utils.stockDataRoot,'scraped13D')

# Cell

class scraper13D(infoScraper.scraperBase) :
    def __init__(self, infoDir=default13DDir, startD=None, endD=None, fSuff='m.pkl', **pickle_kwargs) :
        super().__init__(infoDir, 'SC 13D', startD=startD, endD=endD, fSuff=fSuff, **pickle_kwargs)
    def scrapeInfo(self, accNo, formType=None) :
        return scrape13G.parse13GD(accNo, formType=formType), None

# Cell

def get13GDDatesForQ(y, qNo) :
    _,kwargs = scrape13F.getPeriodAndNextQStartEnd(y, qNo)
    kwargs['startD'] = str(int(kwargs['startD'][:4])-2) + kwargs['startD'][4:]
    return kwargs

def getCombNSSForQ(y, qNo, minFrac=0.01, maxFrac=1.0, minStocksPerInv=3, maxStocksPerInv=100,
                   minTop10Frac=0.4, minAUM=None, dtype=np.float64,
                   minInvestorsPerStock=None, maxInvestorsPerStock=None,
                   minAllInvestorsPerStock=2, maxAllInvestorsPerStock=None, cusipFilter=None,
                   max13GDBonus=0.2, min13GDBonus=0.02, max13GDCount=100,
                   include13F=True, include13G=False, include13D=False,
                   outsInfoFName='', outDir=None) :
    """
    Calculates a matrix of investor holdings for a quarter, based on all 13F filings filed
    during the succeeding quarter, combined with 13G and 13D filings from the previous year
    up through the succeeding quarter.

    Returns mat, ciks, cusips where mat is a matrix of shape (len(ciks), len(cusips))
    in which each row has the fractions held by the corresponding cik in each cusip.

    If minFrac and/or maxFrac is supplied, restricts to stocks with fraction of
    total portfolio >=minFrac and/or <=maxFrac.

    If minStocksPerInv, maxStocksPerInv, minTop10Frac or minAUM are specified, omits
    investors with too few stocks, too many stocks, too small a fraction in the
    top 10 holdings, or too small a total stock value.
    If minInvestorsPerStock is specified, restricts to stocks with at least that many investors
    in the returned matrix; likewise, maxInvestorsPerStock can be used to give an upper bound.
    If minAllInvestorsPerStock or maxAllInvestorsPerStock is specified, restricts based on a count
    of all investors that have any position in each stock.
    If cusipFilter is specified, this should be a function that returns True for cusips to keep.

    13GD bonus fractions are 1.0/#positions, but restricted to [min13GDBonus..max13GDBonus]
    If max13GDCount is not None, restricts to investors with at most max13GDCount combined 13G
    and 13D positions.
    """
    if minAllInvestorsPerStock is not None or maxAllInvestorsPerStock is not None :
        allCusipCounter = collections.Counter()
    else :
        allCusipCounter = None
    cikNames = utils.loadPklFromDir(dailyList.defaultDLDir, 'cikNames.pkl', {})
    cikNames = dict((cik,name) for cik,(name,dStr) in cikNames.items())
    cusipNames = utils.pickLoad(os.path.join(utils.stockDataRoot,'cusipMap.pkl'))
    cik13GDSortedPosMap = None
    if include13G or include13D :
        dates = get13GDDatesForQ(y,qNo)
        scrapedL = []
        if include13G :
            scrapedL.append(scrape13G.scraper13G(**dates))
        if include13D :
            scrapedL.append(scraper13D(**dates))
        cik13GDPosMap = scrape13G.updateCik13GDPos(scrapedL, cusipNames=cusipNames, cikNames=cikNames)
        cikBonusMaps = [scrape13G.calcBonusMap(cik13GDPosMap,
                                               max13GDBonus=max13GDBonus, min13GDBonus=min13GDBonus,
                                               max13GDCount=max13GDCount, allCusipCounter=allCusipCounter)]
        cik13GDSortedPosMap = dict((cik,sorted(((cusip,pos[-1]) for cusip,pos in posMap.items()),
                                        # sort positions largest first, then by name
                                        key=lambda x : (-x[1], cusipNames.get(x[0],'CUSIP-'+x[0]).lower())))
                                   for cik,posMap in cik13GDPosMap.items())
    else :
        cikBonusMaps = []
    res = scrape13F.getNSSForQ(y, qNo, minFrac=minFrac, maxFrac=maxFrac,
                                minStocksPerInv=minStocksPerInv, maxStocksPerInv=maxStocksPerInv,
                                minTop10Frac=minTop10Frac, minAUM=minAUM, dtype=dtype,
                                minInvestorsPerStock=minInvestorsPerStock,
                                maxInvestorsPerStock=maxInvestorsPerStock,
                                minAllInvestorsPerStock=minAllInvestorsPerStock,
                                maxAllInvestorsPerStock=maxAllInvestorsPerStock,
                                allCusipCounter=allCusipCounter, cusipFilter=cusipFilter,
                                extraHoldingsMaps=cikBonusMaps, include13F=include13F)
    if outsInfoFName is not None :
        if outDir is None :
            outDir = Path(utils.stockDataRoot)
        else :
            outDir = Path(utils.stockDataRoot)/outDir
        if not outDir.exists() :
            outDir.mkdir()
        mat, ciks, cusips = res
        cusipSet = set(cusips)
        mat /= 0.01
        mat = np.minimum(mat,20.0)
        res = {'Y': mat, 'ciks': ciks, 'cusips': cusips, 'cusipinfo': []}
        utils.pickSave(outDir/f'{outsInfoFName}{y}Q{qNo}sInfo.pkl', res,
                       fix_imports=True, protocol=2)
        utils.pickSave(outDir/f'cusipMap.pkl',
                       dict((cusip,name) for cusip,name in cusipNames.items() if cusip in cusipSet),
                       fix_imports=True, protocol=2)
        if cik13GDSortedPosMap is not None :
            utils.pickSave(outDir/f'{outsInfoFName}{y}Q{qNo}hold13GD.pkl', cik13GDSortedPosMap,
                           fix_imports=True, protocol=2)
    return res

def oddballScreen(yNo, qNo) :
    """
    Screens for stocks that only one investor reports holding.
    These will mostly be mistakes, so I try to remove the mistakes using cusipFilter.
    """
    cusipNames = utils.pickLoad(os.path.join(utils.stockDataRoot,'cusipMap.pkl'))
    mat, ciks, cusips = getCombNSSForQ(yNo, qNo, max13GDCount=50, include13F=True, include13G=True, include13D=True,
                                       minAllInvestorsPerStock=None, maxAllInvestorsPerStock=1,
                                       cusipFilter = lambda x : x in cusipNames and 'DELETED' not in cusipNames[x])
    return [cusipNames[cusip] for cusip in cusips]