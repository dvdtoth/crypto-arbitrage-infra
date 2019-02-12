import pysher
import time
import json
from logger import logger
import sys
from kafka import KafkaProducer
import yaml
from functools import partial
from CWMetrics import CWMetrics

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

metrics = CWMetrics(config['exchange']['name'])

kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Init pusher
pusher = pysher.Pusher(key="de504dc5763aeef9ff52")

def orderbookHandler(symbols, dataraw):
    data = json.loads(dataraw)
    symbolBase = symbols.upper()[0:3]
    symbolQuote = symbols.upper()[3:]
    payload = {}
    payload['exchange'] = "bitstamp"
    payload['symbol'] = symbolBase + "/" + symbolQuote
    payload['data'] = {}
    payload['data']['asks'] = list(map(lambda entry:[float(entry[0]), float(entry[1])], data['asks']))
    payload['data']['bids'] = list(map(lambda entry:[float(entry[0]), float(entry[1])], data['bids']))
    payload['timestamp'] = int(float(data['microtimestamp'])/1e3)
    print(payload['timestamp'])

    p = json.dumps(payload, separators=(',', ':'))
    kafka_producer.send(config['kafka']['topic'], p)

    logger.info("Received " + symbolBase+"/" + symbolQuote + " prices from Bitstamp")
    metrics.put(payload['timestamp'])

def connectHandler(data):
    try:
        pairs = config['exchange']['symbols']

        # subscribe to all the relevant channels
        for pair in pairs:
            pair = pair.lower().replace('/','')
            if pair == 'btcusd':
                channel = pusher.subscribe('order_book')
            else:
                channel = pusher.subscribe('order_book_' + pair)
            channel.bind('data', partial(orderbookHandler, pair))

    except Exception as error:
        logger.error("Error in Bitstamp web socket connection: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()

pusher.connection.bind('pusher:connection_established', connectHandler)
pusher.connect()

while True:
    time.sleep(1)