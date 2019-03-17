from binance.websockets import BinanceSocketManager
from binance.client import Client
from logger import logger
from kafka import KafkaProducer
import sys
import time
import yaml
import json
from CWMetrics import CWMetrics
import boto3
from multiprocessing import Process, Event
from functools import partial

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)


# Init AWS Parameter store
def getSSMParam(ssm, paramName):
    return ssm.get_parameter(Name=paramName, WithDecryption=True)['Parameter']['Value']


def getCredentials():
    # Read parameters from AWS SSM
    ssm = boto3.client('ssm', region_name='eu-west-1')

    return {
            'api_key': getSSMParam(ssm, '/prod/exchange/binance/api_key'),
            'api_secret': getSSMParam(ssm, '/prod/exchange/binance/api_secret')
            }


# configurable parameters
orderbookDepth = 20
restartPeriodSeconds = 10#0.5*3600


def process_message(kafka_producer, metrics, msg):
    try:
        payload = dict()
        timestamp = time.time()*1000
        payload['exchange'] = config['exchange']['name']
        payload['symbol'] = pairBinanceNameMapping[msg['stream']]
        payload['data'] = {}
        payload['data']['asks'] = list(map(lambda entry: [float(entry[0]), float(entry[1])], msg['data']['asks']))
        payload['data']['bids'] = list(map(lambda entry: [float(entry[0]), float(entry[1])], msg['data']['bids']))
        payload['timestamp'] = timestamp

        p = json.dumps(payload, separators=(',', ':'))
        kafka_producer.send(config['kafka']['topic'], p)
        metrics.put(timestamp)
        print(p)
    except Exception as error:
        logger.error("Error in Binance web socket connection: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()


def CryptoArbBinanceOrderBookProcess(stopProcessesEvent):
    try:
        # Init Kafka producer
        kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'],
                                       value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        # Init CloudWatch metrics
        metrics = CWMetrics(config['exchange']['name'])

        credentials = getCredentials()
        client = Client(api_key=credentials['api_key'],
                        api_secret=credentials['api_secret'])

        bm = BinanceSocketManager(client)
        bm.start_multiplex_socket(pairList, partial(process_message, kafka_producer, metrics))
        bm.start()
        logger.info('BinanceSocketManager started')
        stopProcessesEvent.wait()
        bm.close()
        logger.info('BinanceSocketManager closed')
    except Exception as error:
        logger.error("Error CryptoArbBinanceOrderBookProcess: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()


pairList = []
pairBinanceNameMapping = dict()
# pairList = ['ethbtc@depth20', 'ltcbtc@depth20']

# Generate pair list
for pair in config['exchange']['symbols']:
    pairSplit = pair.lower().split('/')
    if pairSplit[0] == "BCH":
        pairSplit[0] = "BCHABC"

    pairElement = pairSplit[0] + pairSplit[1] + '@depth' + str(orderbookDepth)
    pairList.append(pairElement)
    pairBinanceNameMapping[pairElement] = pair

# Keep on restarting the BinanceSocketManager process periodically
while True:
    stopProcessesEvent = Event()
    process = Process(target=CryptoArbBinanceOrderBookProcess, args=(stopProcessesEvent,))

    process.daemon = True
    process.start()

    time.sleep(restartPeriodSeconds)

    stopProcessesEvent.set()
    process.join()

logger.info("binance-listener exited normally. Bye.")


