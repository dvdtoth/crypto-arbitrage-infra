# Initialize CW metrics with some errors

from CWMetrics import CWMetrics

exchanges = ['kraken', 'oanda', 'binance', 'bitstamp', 'coinbasepro', 'poloniex', 'sfox']
for x in exchanges: 
    metrics = CWMetrics(x)
    metrics.putError()

metrics.putCMCError()