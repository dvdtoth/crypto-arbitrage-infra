from sortedcontainers import SortedDict
from logger import logger
from kafka import KafkaProducer
import sys
import yaml
import json
from CWMetrics import CWMetrics
import websocket
import threading
import time
from multiprocessing import Process, Event
from functools import partial

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

# configurable parameters
consolidatedOrderbookDepth = 30
restartPeriodSeconds = 0.5*3600

def processSnapshot(orderbook,entries):
    updateList = [(float(entry[0]), float(entry[1])) for entry in entries]
    orderbook.update(updateList)


def processDelta(orderbook, entries, metrics):
    for entry in entries:
        if float(entry[1]) > 0:
            orderbook.update([(float(entry[0]), float(entry[1]))])
        else:
            try:
                orderbook.pop(float(entry[0]))
            except KeyError as e:
                logger.error('Error: Poloniex asked to remove price level that doesn''t exist')
                metrics.putError()
                pass


def getTop(orderbook, itemCount = 3, reverse=False):
    entries = []
    sliceBegin = 0
    sliceEnd  = itemCount
    if reverse is True:
        sliceBegin = len(orderbook)-itemCount
        sliceEnd  = len(orderbook)

    for x in orderbook.islice(start=sliceBegin, stop=sliceEnd,reverse=reverse):
        entries.append([float(x),orderbook[x]])

    return entries

        
def on_message(kafka_producer, metrics, orderbooks, ws, message):
    try:
        json_msg = json.loads(message)

        # Is message a snapshot?
        try:
            if json_msg[2][0][0] == 'i':
                channelID = json_msg[0]
                orderbooks[channelID] = dict()
                orderbooks[channelID]['symbol'] = '/'.join(json_msg[2][0][1]['currencyPair'].split('_')[::-1])
                orderbooks[channelID]['asks'] = SortedDict()
                orderbooks[channelID]['bids'] = SortedDict()
                orderbooks[channelID]['timestamp'] = None

                asks = list(json_msg[2][0][1]['orderBook'][0].items())
                bids = list(json_msg[2][0][1]['orderBook'][1].items())

                # Process snapshot
                processSnapshot(orderbook=orderbooks[channelID]['asks'], entries=asks)
                processSnapshot(orderbook=orderbooks[channelID]['bids'], entries=bids)
                orderbooks[channelID]['timestamp'] = time.time()*1e3
                return
        except IndexError:
            pass
        except Exception as error:
            logger.error(type(error).__name__ + " " + str(error.args))

        # Is it just a heartbeat?
        if len(json_msg) < 3:
            return

        # It must be a delta frame
        delta_asks = []
        delta_bids = []
        for entry in json_msg[2]:
            if entry[0] == 'o':
                if entry[1] == 1:
                    delta_bids.append([float(entry[2]),float(entry[3])])
                elif entry[1] == 0:
                    delta_asks.append([float(entry[2]),float(entry[3])])

        channelID = json_msg[0]
        processDelta(orderbook=orderbooks[channelID]['asks'], entries=delta_asks, metrics=metrics)
        processDelta(orderbook=orderbooks[channelID]['bids'], entries=delta_bids, metrics=metrics)
        orderbooks[channelID]['timestamp'] = time.time()*1e3

        # Data conversion
        asks = getTop(orderbook=orderbooks[channelID]['asks'], itemCount=consolidatedOrderbookDepth)
        bids = getTop(orderbook=orderbooks[channelID]['bids'], itemCount=consolidatedOrderbookDepth, reverse=True)

        if bids[0][0] >= asks[0][0]:
          logger.error('Error' + orderbooks[channelID]['symbol'] + ': Bid ' + str(bids[0][0]) + ' is higher than ask ' + str(asks[0][0]) +'(gap:'+str((bids[0][0]-asks[0][0])/asks[0][0]*100)+'%)')

        payload = {}
        payload['exchange'] = "poloniex"
        payload['symbol'] = orderbooks[channelID]['symbol']
        payload['data'] = {}
        payload['data']['asks'] = asks
        payload['data']['bids'] = bids
        payload['timestamp'] = orderbooks[channelID]['timestamp']

        p = json.dumps(payload, separators=(',', ':'))
        kafka_producer.send(config['kafka']['topic'], p)

        #logger.info(orderbooks[channelID]['symbol'] + " asks:"+str(asks)+", bids:"+str(bids) + " timestamp:"+str(payload['timestamp']))
        metrics.put(payload['timestamp'])

    except Exception as error:
        logger.error("Error in Poloniex web socket connection: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()


def on_error(metrics, ws, error):
    logger.error(error)
    metrics.putError()

def on_close(ws):
    logger.info("WebSocket closed")


def on_open(ws):
    logger.info("WebSocket on_open")

    def subscribe(*args):
        for symbol in config['exchange']['symbols']:
            ws.send(json.dumps({'command': 'subscribe', 'channel': '_'.join(symbol.split('/')[::-1])}))

    threading.Thread(target=subscribe).start()


def CryptoArbOrderBookProcess(stopProcessesEvent):
    try:
        # Init Kafka producer
        kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'],
                                       value_serializer=lambda v: json.dumps(v).encode('utf-8'))

        # Init CloudWatch metrics
        metrics = CWMetrics(config['exchange']['name'])

        # Init orderbooks dictionary
        orderbooks = dict()

        websocket.enableTrace(False)
        ws = websocket.WebSocketApp("wss://api2.poloniex.com/",
                                    on_message=partial(on_message, kafka_producer, metrics, orderbooks),
                                    on_error=partial(on_error, metrics),
                                    on_close=on_close)

        ws.on_open = on_open

        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        logger.info('Poloniex websocket started')
        stopProcessesEvent.wait()
        logger.info('Poloniex websocket closed')

    except Exception as error:
        logger.error(type(error).__name__ + " " + str(error.args))
        metrics.putError()


if __name__ == "__main__":
    # Keep on restarting the websocket periodically
    while True:
        stopProcessesEvent = Event()
        process = Process(target=CryptoArbOrderBookProcess, args=(stopProcessesEvent,))

        process.daemon = True
        process.start()

        time.sleep(restartPeriodSeconds)

        stopProcessesEvent.set()
        process.join()

    logger.info("binance-listener exited normally. Bye.")
