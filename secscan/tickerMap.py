# AUTOGENERATED! DO NOT EDIT! File to edit: 03_tickerMap.ipynb (unless otherwise specified).

__all__ = ['getSecTickerDict', 'secTickerListUrl']

# Cell

from secscan import utils

# Cell

secTickerListUrl = '/files/company_tickers_exchange.json'
def getSecTickerDict() :
    """
    Creates a dict mapping ticker -> CIK based on download from the SEC.
    """
    secTickerJson = utils.downloadSecUrl(secTickerListUrl, toFormat='json')
    tickerPos = secTickerJson['fields'].index('ticker')
    cikPos = secTickerJson['fields'].index('cik')
    res = {}
    for tup in secTickerJson['data'] :
        ticker, cik = tup[tickerPos], tup[cikPos]
        if ticker not in res or int(res[ticker]) < cik:
            res[ticker] = str(cik)
    return res