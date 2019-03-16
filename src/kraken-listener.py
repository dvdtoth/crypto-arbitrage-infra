from kraken_wsclient_py import kraken_wsclient_py as client
from sortedcontainers import SortedDict
from logger import logger
from kafka import KafkaProducer
import sys
import yaml
import json
from CWMetrics import CWMetrics

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

metrics = CWMetrics(config['exchange']['name'])
# configurable parameters
orderbookDepthInSubscription = 1000
consolidatedOrderbookDepth = 30

orderbooks = dict()

def processSnapshot(orderbook,entries):
    orderbook.update([(entry[0], float(entry[1])) for entry in entries])

def getSnapshotTimestamp(orderbookA,orderbookB=[]):
    return max([float(entry[2]) for entry in orderbookA+orderbookB])

def processDelta(orderbook,entries):
    for entry in entries:
        if float(entry[1]) > 0:
            orderbook.update([(entry[0], float(entry[1]))])
        else:
            try:
                orderbook.pop(entry[0])
            except KeyError as e:
                logger.error('Error: Kraken asked to remove price level that doesn''t exist')
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

        
def krakenMessageHandler(message):
    try:
        # Is subscription confirmation message?
        if 'event' in message and 'status' in message and 'channelID' in message and 'pair' in message:
            # Was subscription successful?
            if message['event'] == 'subscriptionStatus' and message['status'] == 'subscribed':            
                channelID = message['channelID']
                # create orderbook data structure for trading pair
                orderbooks[channelID] = dict()
                orderbooks[channelID]['symbol'] = translateNamingFromStandardToKraken([message['pair']],reversed=True)[0]
                orderbooks[channelID]['asks'] = SortedDict()
                orderbooks[channelID]['bids'] = SortedDict()
                orderbooks[channelID]['timestamp'] = None
        
        
        # Orderbook message?
        if isinstance(message,list) is False:
            return

        channelID = message[0]
        for payload in message[1:]:
            # Process snapshot
            if 'as' in payload and 'bs' in payload:
                orderbooks[channelID]['asks'] = SortedDict()
                orderbooks[channelID]['bids'] = SortedDict()
                processSnapshot(orderbook=orderbooks[channelID]['asks'], entries=payload['as'])
                processSnapshot(orderbook=orderbooks[channelID]['bids'], entries=payload['bs'])
                orderbooks[channelID]['timestamp']=getSnapshotTimestamp(payload['as'], payload['bs'])*1e3

            # Prodess deltas
            if 'a' in payload:
                processDelta(orderbook=orderbooks[channelID]['asks'],entries=payload['a'])
                orderbooks[channelID]['timestamp']=getSnapshotTimestamp(payload['a'])*1e3
            if 'b' in payload:
                processDelta(orderbook=orderbooks[channelID]['bids'],entries=payload['b'])
                orderbooks[channelID]['timestamp']=getSnapshotTimestamp(payload['b'])*1e3
        
        
        # Data conversion
        asks = getTop(orderbook=orderbooks[channelID]['asks'],itemCount=consolidatedOrderbookDepth)
        bids = getTop(orderbook=orderbooks[channelID]['bids'],itemCount=consolidatedOrderbookDepth,reverse=True)

        if bids[0][0]>=asks[0][0]:
          logger.error('Error' + orderbooks[channelID]['symbol'] + ': Bid ' + str(bids[0][0]) + ' is higher than ask ' + str(asks[0][0]) +'(gap:'+str((bids[0][0]-asks[0][0])/asks[0][0]*100)+'%)')

        payload = {}
        payload['exchange'] = "kraken"
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
        logger.error("Error in Kraken web socket connection: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()

krakenNamingMappings = [('BTC','XBT')]
def translateNamingFromStandardToKraken(symbolsList,reversed=False):
    translatedList = []
    for symbol in symbolsList:
        translatedSymbol = symbol
        for krakenNamingMapping in krakenNamingMappings:
            if reversed is False:
                translatedSymbol = translatedSymbol.replace(krakenNamingMapping[0],krakenNamingMapping[1])
            else:
                translatedSymbol = translatedSymbol.replace(krakenNamingMapping[1],krakenNamingMapping[0])
            translatedList.append(translatedSymbol)
    return translatedList

my_client = client.WssClient()
my_client.subscribe_public(
    subscription={
        'name': 'book',
        'depth': orderbookDepthInSubscription
    },
    #pair=translateNamingFromStandardToKraken(['BTC/USD']),
    pair=translateNamingFromStandardToKraken(symbolsList=config['exchange']['symbols']),
    callback=krakenMessageHandler
)

my_client.start()
