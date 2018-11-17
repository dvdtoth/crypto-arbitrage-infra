#!/usr/bin/env python

import asyncio
import ccxt.async_support as ccxt  # noqa: E402
import sys
import os
import time
import json
from kafka import KafkaProducer
import logging
import yaml

# logger = logging.getLogger('Poller')
# logger.setLevel(logging.DEBUG)

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

# TODO check config params

# Consider recommended ratelimit of exchange, divide it by the number of IPs used
ratelimit = getattr(ccxt, config['exchange']['name'])().rateLimit
delay = ratelimit / int(config['proxy']['ip_pool_size'])

# logger.info(str(config['proxy']['ip_pool_size']) + ' IPs used')
# logger.info('The rate limit is ' + str(ratelimit) + ' delaying by ' + str(delay) + ' ms')

kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

def produce(symbol, tickers):

    payload = {
        'exchange': config['exchange']['name'],
        'symbol': symbol,
        'timestamp': exchange.milliseconds(),
        'data': tickers
    }

    payload = exchange.json(payload)
    # print(payload)
    # logger.info(payload)

    kafka_producer.send(config['kafka']['topic'], payload)


async def main(exchange, symbols):
    # print(symbols)
    i = 0
    while True:
        symbol = symbols[i % len(symbols)]
        # print(symbol)
        # logger.info(exchange.iso8601(exchange.milliseconds()), 'fetching', symbol, 'orderbook from', config['exchange']['name'])
        tickers = await exchange.fetch_tickers(symbol, params={
                        "limit": 40,
                        "sort": "rank"

                    })
        produce(symbol, tickers)
        # logger.info(exchange.iso8601(exchange.milliseconds()), 'fetched', symbol, 'orderbook from', config['exchange']['name'])
        time.sleep(delay / 1000)
        i += 1

# Use getattr to specify exchange, eg. ccxt.gdax
exchange = getattr(ccxt, config['exchange']['name'])({
    'aiohttp_proxy': config['proxy']['address'],
    'verbose': 'true',
    'timeout': 30000
})

asyncio.get_event_loop().run_until_complete(main(exchange, config['exchange']['symbols']))
