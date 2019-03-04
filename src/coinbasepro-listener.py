import cbpro
from decimal import *
from logger import logger
import sys
import yaml
import json
from kafka import KafkaProducer
import dateutil.parser
import time
from multiprocessing import Process, Event
from CWMetrics import CWMetrics

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)


class CryptoArbOrderBook(cbpro.OrderBook):
    def __init__(self, maxEntryCount=10, timeLimiterSeconds=0.025, product_id='BTC-USD', log_to=None):
        self.maxEntryCount = maxEntryCount
        self.asksConsolidatedOld = []
        self.bidsConsolidatedOld = []
        self.timeLastRun = time.time()
        self.timeLimiterSeconds = timeLimiterSeconds
        self.metrics = CWMetrics(config['exchange']['name'])
        self.kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'],
                                            value_serializer=lambda v: json.dumps(v).encode('utf-8'))

        super().__init__(product_id=product_id, log_to=log_to)

    def on_message(self, message):
        try:
            logger.info(message)
            super().on_message(message)
        except Exception as err:
            logger.error("Error during calling cbpro.Orderbook on_message:" + str(err))
            return
                
        if (time.time() - self.timeLastRun) > self.timeLimiterSeconds:
            try:
                book = self.get_current_book()
                if len(book["asks"])>0 and len(book["bids"])>0:
                    asksConsolidated = self.getConsolidatedOrderbook(book["asks"], reverse=False)
                    bidsConsolidated = self.getConsolidatedOrderbook(book["bids"], reverse=True)
                    #print("asks:"+str(asksConsolidated)+", bids:"+str(bidsConsolidated))

                    if self.asksConsolidatedOld != asksConsolidated or self.bidsConsolidatedOld != bidsConsolidated:
                        payload = {}
                        payload['exchange'] = "coinbasepro"
                        payload['symbol'] = message['product_id'].replace('-','/')
                        payload['data'] = {}
                        payload['data']['asks'] = asksConsolidated
                        payload['data']['bids'] = bidsConsolidated
                        dt = dateutil.parser.parse(message['time'])
                        payload['timestamp'] = int(time.mktime(dt.timetuple()) * 1000 + dt.microsecond / 1000)

                        p = json.dumps(payload, separators=(',', ':'))
                        self.kafka_producer.send(config['kafka']['topic'], p)

                        logger.info("Received " + payload['symbol'] + " prices from coinbasepro")
                        self.metrics.put(payload['timestamp'])

                        self.asksConsolidatedOld = asksConsolidated
                        self.bidsConsolidatedOld = bidsConsolidated

                    if book["asks"][0][0] <= book["bids"][-1][0]:
                        logger.error("Bid higher than ask")
                        self.metrics.putError()
            except Exception as err:
                logger.error("Error during message processing:" + str(err))
            finally:
                self.timeLastRun = time.time()

    def getConsolidatedOrderbook(self, entries, reverse=False):
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
        
def CryptoArbOrderBookProcess(pair,stopProcessesEvent):
    orderbook=CryptoArbOrderBook(product_id=pair.replace('/', '-'))
    orderbook.start()
    stopProcessesEvent.wait()
    orderbook.close()

pairs = config['exchange']['symbols']


while True:
    stopProcessesEvent = Event()
    processes = [Process(target=CryptoArbOrderBookProcess, args=(pair, stopProcessesEvent)) for pair in pairs]

    # start order books
    for process in processes:
        process.daemon = True
        process.start()

    time.sleep(10)

    stopProcessesEvent.set()
    for process in processes:
        process.join()

logger.info("coinbaseproWebsocket exited normally. Bye.")


