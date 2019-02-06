#!/usr/bin/env python

import asyncio
import ccxt.async_support as ccxt  # noqa: E402
import sys
import os
import time
import json
from kafka import KafkaProducer
from logger import logger
import yaml
from CWMetrics import CWMetrics

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

metrics = CWMetrics(config['exchange']['name'])

# Consider recommended ratelimit of exchange, divide it by the number of IPs used
ratelimit = getattr(ccxt, config['exchange']['name'])().rateLimit
delay = ratelimit / int(config['proxy']['ip_pool_size'])

logger.info(str(config['proxy']['ip_pool_size']) + ' IPs used')
logger.info('Rate limit: ' + str(ratelimit) + ' delaying by " ' + str(delay) + ' ms')

kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

def produce(symbol, orderbook):

    payload = {
        'exchange': config['exchange']['name'],
        'symbol': symbol,
        'timestamp': exchange.milliseconds(),
        'data': orderbook
    }
    payload = exchange.json(payload)
    
    kafka_producer.send(config['kafka']['topic'], payload)
    metrics = CWMetrics(config['exchange']['name'])


async def main(exchange, symbols):

    i = 0
    while True:
        symbol = symbols[i % len(symbols)]
        try:
            logger.info('fetching ' + str(symbol) + ' orderbook from ' + str(config['exchange']['name']))
            orderbook = await exchange.fetch_order_book(symbol, limit=20)
            produce(symbol, orderbook)
        except (ccxt.ExchangeError, ccxt.NetworkError) as error:
            logger.error('Fetch orderbook network/exchange error ' + exchange.name + " " + symbol + ": " + type(error).__name__ + " " + str(error.args))
        except Exception as error:
            logger.error('Fetch orderbook error ' + exchange.name + " " + symbol + ": " + type(error).__name__ + " " + str(error.args))
        time.sleep(delay / 1000)
        i += 1

# Use getattr to specify exchange, eg. ccxt.gdax
exchange = getattr(ccxt, config['exchange']['name'])({
    'aiohttp_proxy': config['proxy']['address'],
    # 'verbose': 'true',
    'timeout': 30000
})

asyncio.get_event_loop().run_until_complete(main(exchange, config['exchange']['symbols']))
