#!/usr/bin/env python

import asyncio
import ccxt.async_support as ccxt  # noqa: E402
import boto3
import sys

# For local development use profile from ~/.aws/credentials
session = boto3.Session(profile_name='crypto')
kinesis = session.client('kinesis', region_name='eu-west-1')

# On AWS assume role
# kinesis = boto3.client('kinesis', region_name='eu-west-1')

producer = sys.argv[1]
stream = 'orderbook-stream'
symbols = 'BTC/USD'
ignore_unchanged = False
last_hash = ''


def produce(orderbook):

    orderbook['exchange'] = producer
    orderbook['symbols'] = symbols
    orderbook['timestamp'] = exchange.milliseconds()
    payload = exchange.json(orderbook)
    print(payload)

    response = kinesis.put_record(
        StreamName=stream, Data=payload, PartitionKey=producer)
    print(response)


async def main(exchange, symbol):
    while True:
        print('--------------------------------------------------------------')
        print(exchange.iso8601(exchange.milliseconds()),
              'fetching', symbol, 'orderbook from', exchange.name)
        orderbook = await exchange.fetch_order_book(symbol, limit=20)
        produce(orderbook)
        print(exchange.iso8601(exchange.milliseconds()),
              'fetched', symbol, 'orderbook from', exchange.name)

# Use getattr to specify exchange, eg. ccxt.gdax
exchange = getattr(ccxt, producer)({
    'enableRateLimit': True,
})

asyncio.get_event_loop().run_until_complete(main(exchange, symbols))
