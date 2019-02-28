import cbpro
from decimal import *
from logger import logger
import sys
import yaml
import json
from kafka import KafkaProducer
import dateutil.parser
import time
from CWMetrics import CWMetrics

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

metrics = CWMetrics(config['exchange']['name'])

kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

class CryptoArbOrderBook(cbpro.OrderBook):
    def __init__(self, maxEntryCount=10, product_id='BTC-USD', log_to=None):
        self.maxEntryCount = maxEntryCount
        self.asksConsolidatedOld = []
        self.bidsConsolidatedOld = []
        return super().__init__(product_id=product_id, log_to=log_to)

    def on_message(self, message):
        book=self.get_current_book()
        if len(book["asks"])>0 and len(book["bids"])>0:
            asksConsolidated = self.getConsolidatedOrderbook(book["asks"], reverse=False)
            bidsConsolidated = self.getConsolidatedOrderbook(book["bids"], reverse=True)
            logger.info("asks:"+str(asksConsolidated)+", bids:"+str(bidsConsolidated))

            if self.asksConsolidatedOld != asksConsolidated or self.bidsConsolidatedOld != bidsConsolidated:
                payload = {}
                payload['exchange'] = "coinbasepro"
                payload['symbol'] = message['product_id'].replace('-','/')
                payload['data'] = {}
                payload['data']['asks'] = asksConsolidated
                payload['data']['bids'] = bidsConsolidated
                payload['timestamp'] = time.mktime(dateutil.parser.parse(message['time']).timetuple())

                p = json.dumps(payload, separators=(',', ':'))
                kafka_producer.send(config['kafka']['topic'], p)

                logger.info("Received " + payload['symbol'] + " prices from coinbasepro")
                metrics.put(payload['timestamp'])

                self.asksConsolidatedOld = asksConsolidated
                self.bidsConsolidatedOld = bidsConsolidated

            if book["asks"][0][0]<=book["bids"][-1][0]:
                logger.error("Bid higher than ask")
                metrics.putError()

        return super().on_message(message)

    def getConsolidatedOrderbook(self,entries,reverse=False):
        orderbook = []
        
        size = Decimal(0)
        sizeAccumulator = 0

        if reverse:
            price = entries[-1][0]
            entries = reversed(entries)
        else:
            price = entries[0][0]

        for entry in entries:
            if entry[0] == price:
                size += entry[1]
            else:
                orderbook.append([float(price), float(size)])
                sizeAccumulator += size
                if len(orderbook) >= self.maxEntryCount:
                    break
                price = entry[0]
                size = entry[1]
        
        return orderbook
        
    
pairs = config['exchange']['symbols']

# start orderbooks
ordersbooks = []
for pair in pairs:
    orderbook = CryptoArbOrderBook(product_id=pair.replace('/','-'))
    ordersbooks.append(orderbook)
    orderbook.start()

while True:
    time.sleep(1)

# stop orderbooks
for orderbook in ordersbooks:
    orderbook.close()
