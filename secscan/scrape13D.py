# AUTOGENERATED! DO NOT EDIT! File to edit: 11_scrape13D.ipynb (unless otherwise specified).

__all__ = ['default13DDir', 'scraper13D', 'get13GDDatesForQ', 'getCombNSSForQ', 'oddballScreen', 'defaultNSSArgs']

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

class scraper13D(scrape13G.scraper13G) :
    @utils.delegates(scrape13G.scraper13G.__init__)
    def __init__(self, infoDir=default13DDir, **kwargs) :
        super().init_for_13D(infoDir, **kwargs)

# Cell

def get13GDDatesForQ(y, qNo) :
    _,kwargs = scrape13F.getPeriodAndNextQStartEnd(y, qNo)
    kwargs['startD'] = str(int(kwargs['startD'][:4])-2) + kwargs['startD'][4:]
    return kwargs

defaultNSSArgs = dict(
    # arguments to scrape13F.filter13FHoldings:
    minFrac=0.01, maxFrac=1.0, minTopNFrac=0.4, minTopN=10, minAUM=None,
    # arguments to scrape13F.holdingsMapToMatrix:
    minMatStocksPerInv=3,
    # arguments to scrape13G.calcBonusMap:
    max13GDBonus=0.2, min13GDBonus=0.02, max13GDCount=50,
)
@utils.delegates(scrape13F.filter13FHoldings, scrape13F.holdingsMapToMatrix, scrape13G.calcBonusMap)
def getCombNSSForQ(y, qNo,
                   cusipNameFilter=lambda cusip,name : name is not None,
                   include13F=True, include13G=False, include13D=False,
                   outsInfoFName='', outDir='ratings', **kwargs) :
    """
    Calculates a matrix of investor holdings for a quarter, based on all 13F filings filed
    during the succeeding quarter, combined with 13G and 13D filings from the previous two
    years through the succeeding quarter.

    Returns mat, ciks, cusips where mat is a matrix of shape (len(ciks), len(cusips))
    in which each row has the fractions held by the corresponding cik in each cusip.

    If cusipNameFilter is specified, this should be a function that gets two arguments (cusip and
    name, where name will be None if no name was found in either the SEC 13F CUSIP name index or
    in the CUSIP-CIK correspondence from 13D and 13G forms), and returns True for cusips to keep.

    Uses scrape13F.filter13FHoldings and scrape13F.holdingsMapToMatrix to filter the returned matrix.
    Uses scrape13G.calcBonusMap to calculate rating bonuses for 13G/D positions.
    """
    kwargs = dict(defaultNSSArgs,**kwargs)
    allCusipCounter = collections.Counter()
    all13FHoldingsMap = {}
    cikNames = utils.loadPklFromDir(dailyList.defaultDLDir, 'cikNames.pkl', {})
    cikNames = dict((cik,name) for cik,(name,dStr) in cikNames.items())
    cusipNames = utils.pickLoad(os.path.join(utils.stockDataRoot,'13FLists',f'{y}Q{qNo}secCusipMap.pkl'))
    if include13G or include13D :
        dates = get13GDDatesForQ(y,qNo)
        scrapedL = []
        if include13G :
            scrapedL.append(scrape13G.scraper13G(**dates))
        if include13D :
            scrapedL.append(scraper13D(**dates))
        cik13GDPosMap = scrape13G.updateCik13GDPos(scrapedL, cusipNames=cusipNames, cikNames=cikNames,
                                                   includeTickers=True)
        cikBonusMaps = [utils.callDelegated(scrape13G.calcBonusMap, kwargs, cik13GDPosMap, allCusipCounter)]
        cik13GDSortedPosMap = dict((cik,sorted(((cusip,pos) for cusip,pos in posMap.items()),
                                        # sort positions largest first, then by name
                                        key=lambda x : (-x[1][2], cusipNames.get(x[0],'CUSIP-'+x[0]).lower())))
                                   for cik,posMap in cik13GDPosMap.items())
    else :
        cikBonusMaps = []
        cik13GDSortedPosMap = {}
    res = scrape13F.getNSSForQ(y, qNo, allCusipCounter=allCusipCounter,
                               cusipFilter=lambda cusip : cusipNameFilter(cusip,cusipNames.get(cusip)),
                               extraHoldingsMaps=cikBonusMaps, include13F=include13F,
                               all13FHoldingsMap=all13FHoldingsMap,
                               **kwargs)
    if outsInfoFName is not None :
        if outDir is None :
            outDir = Path(utils.stockDataRoot)
        else :
            outDir = Path(utils.stockDataRoot)/outDir
        if not outDir.exists() :
            outDir.mkdir()
        mat, ciks, cusips = res
        cikSet = set(ciks)
        mat /= 0.01
        mat = np.minimum(mat,20.0)
        res = {'Y': mat, 'ciks': ciks, 'cusips': cusips, 'cusipinfo': [],
               'deletedcusips': set(cusip for cusip in cusips
                                    if 'DELETED' in cusipNames.get(cusip,''))}
        utils.pickSave(outDir/f'{outsInfoFName}{y}Q{qNo}sInfo.pkl', res,
                       fix_imports=True, protocol=2)
        utils.pickSave(outDir/f'{outsInfoFName}{y}Q{qNo}cusipMap.pkl',
                       dict((cusip, name)
                            for cusip,name in cusipNames.items() if cusip in allCusipCounter),
                       fix_imports=True, protocol=2)
        utils.pickSave(outDir/f'{outsInfoFName}{y}Q{qNo}hold13GD.pkl',cik13GDSortedPosMap,
                       #dict((cik, posMap)
                       #     for cik,posMap in cik13GDSortedPosMap.items() if cik.zfill(10) in cikSet),
                       fix_imports=True, protocol=2)
        utils.pickSave(outDir/f'{outsInfoFName}{y}Q{qNo}hold13F.pkl',all13FHoldingsMap,
                       #dict((cik, posMap)
                       #     for cik,posMap in all13FHoldingsMap.items() if cik.zfill(10) in cikSet),
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