# AUTOGENERATED! DO NOT EDIT! File to edit: 03_tickerMap.ipynb (unless otherwise specified).

__all__ = ['getSecTickerJson', 'getSecTickerDict', 'getCikToTickersMap', 'getCikToFirstTickerMap', 'secTickerListUrl',
           'defaultSecTickerPath']

# Cell

import collections
import json
import os

from secscan import utils

# Cell

secTickerListUrl = '/files/company_tickers_exchange.json'
defaultSecTickerPath = os.path.join(utils.stockDataRoot,'secTickerList.json')

def getSecTickerJson(secTickerPath=defaultSecTickerPath) :
    """
    Downloads a current list mapping ticker to CIK, name and exchange from the SEC.
    if secTickerPath is supplied and not None, keeps the downloaded list in the
    specified path and only updates it once a day.
    """
    if secTickerPath is None or not utils.wasUpdatedToday(secTickerPath) :
        secTickerJson = utils.downloadSecUrl(secTickerListUrl, toFormat='json')
        print('loaded SEC ticker list,',len(secTickerJson['data']),'entries')
        if secTickerPath is None :
            return secTickerJson
        with open(secTickerPath,'w') as f :
            f.write(json.dumps(secTickerJson, indent=0))
    with open(secTickerPath,'r') as f :
        return json.loads(f.read())

@utils.delegates(getSecTickerJson)
def getSecTickerDict(field1='ticker', field2='cik', multiValue='last', **kwargs) :
    """
    Return mappings among ticker, cik, name, and exchange based on a
    downloaded list from the SEC. Returns a dict: field1 -> field2 values.

    The multivalue argument specifies how to handle multiple field2 values
    found for the same field1 value:
    'list' - stores a list of all field2 values found
    'first' - just stores the first field2 value found
    'last' - just stores the last field2 value found
    """
    secTickerJson = getSecTickerJson(**kwargs)
    fieldList, dataList = secTickerJson['fields'], secTickerJson['data']
    field1Pos, field2Pos = fieldList.index(field1), fieldList.index(field2)
    res = collections.defaultdict(list) if multiValue=='list' else {}
    for tup in dataList :
        field1Val, field2Val = str(tup[field1Pos]), str(tup[field2Pos])
        if multiValue=='list' :
            res[field1Val].append(field2Val)
        elif multiValue=='last' or field1Val not in res :
            res[field1Val] = field2Val
    print(f'dict: {field1}->{field2} [multiValue={multiValue}] has {len(res)} keys',end='')
    if multiValue != 'list' :
        print(f' with {len(set(res.values()))} unique values',end='')
    print()
    return res

@utils.delegates(getSecTickerJson)
def getCikToTickersMap(**kwargs) :
    """
    Returns a dict: cik -> <list of corresponding tickers from the SEC list>
    """
    return getSecTickerDict(field1='cik', field2='ticker', multiValue='list', **kwargs)

@utils.delegates(getSecTickerJson)
def getCikToFirstTickerMap(**kwargs) :
    """
    Returns a dict: cik -> <first ticker for cik found on the SEC list>
    """
    return getSecTickerDict(field1='cik', field2='ticker', multiValue='first', **kwargs)


## Old code using company_tickers.json:
# def getCikToTickersMap() :
#     """
#     Retrieves and parses an SEC-maintained list mapping tickers to CIKs.
#     Returns a defaultdict: cik -> list of corresponding tickers
#     """
#     tickersJSON = utils.downloadSecUrl('/files/company_tickers.json', toFormat='json')
#     cikToTickers = collections.defaultdict(list)
#     for v in tickersJSON.values() :
#         cikToTickers[str(v['cik_str'])].append(v['ticker'])
#     return cikToTickers