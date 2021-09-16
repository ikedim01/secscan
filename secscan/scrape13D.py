# AUTOGENERATED! DO NOT EDIT! File to edit: 11_scrape13D.ipynb (unless otherwise specified).

__all__ = ['default13DDir', 'scraper13D', 'get13GDDatesForQ', 'getCombNSSForQ']

# Cell

import collections
import itertools
import numpy as np
import os
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
    kwargs['startD'] = str(int(kwargs['startD'][:4])-1) + kwargs['startD'][4:]
    return kwargs

def getCombNSSForQ(y, qNo, minFrac=0.01, maxFrac=1.0, minStocksPerInv=3, maxStocksPerInv=100,
                   minTop10Frac=0.4, minAUM=None, dtype=np.float64,
                   minInvestorsPerStock=2, maxInvestorsPerStock=None,
                   max13GDBonus=0.2, min13GDBonus=0.02, max13GDCount=100) :
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
    If minInvestorsPerStock is specified, restricts to stocks with at least that many investors.
    If maxInvestorsPerStock is specified, restricts to stocks with at most that many investors.

    13GD bonus fractions are 1.0/#positions, but restricted to [min13GDBonus..max13GDBonus]
    If max13GDCount is not None, restricts to investors with at most max13GDCount combined 13G
    and 13D positions.
    """
    dates = get13GDDatesForQ(y,qNo)
    scrapedL = [scrape13G.scraper13G(**dates), scraper13D(**dates)]
    cik13GDPosMap = scrape13G.updateCik13GDPos(scrapedL)
    cikBonusMap = scrape13G.calcBonusMap(cik13GDPosMap, max13GDBonus=max13GDBonus, min13GDBonus=min13GDBonus,
                                         max13GDCount=max13GDCount)
    return scrape13F.getNSSForQ(y, qNo, minFrac=minFrac, maxFrac=maxFrac,
                                minStocksPerInv=minStocksPerInv, maxStocksPerInv=maxStocksPerInv,
                                minTop10Frac=minTop10Frac, minAUM=minAUM, dtype=dtype,
                                minInvestorsPerStock=minInvestorsPerStock,
                                maxInvestorsPerStock=maxInvestorsPerStock,
                                extraHoldingsMaps=[cikBonusMap])