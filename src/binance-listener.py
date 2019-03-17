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

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

# Init Kafka producer
kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Init CloudWatch metrics
metrics = CWMetrics(config['exchange']['name'])


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
restartPeriodSeconds = 3*3600

credentials = getCredentials()
client = Client(api_key=credentials['api_key'],
                api_secret=credentials['api_secret'])


def process_message(msg):
    try:
        payload = dict()
        payload['exchange'] = "binance"
        payload['symbol'] = pairBinanceNameMapping[msg['stream']]
        payload['data'] = {}
        payload['data']['asks'] = list(map(lambda entry:[float(entry[0]), float(entry[1])], msg['data']['asks']))
        payload['data']['bids'] = list(map(lambda entry:[float(entry[0]), float(entry[1])], msg['data']['bids']))
        payload['timestamp'] = time.time()*1000

        p = json.dumps(payload, separators=(',', ':'))
        kafka_producer.send(config['kafka']['topic'], p)
    except Exception as error:
        logger.error("Error in Binance web socket connection: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()

pairList = []
pairBinanceNameMapping = dict()
# pairList = ['ethbtc@depth20', 'ltcbtc@depth20']

for pair in config['exchange']['symbols']:
    pairSplit = pair.lower().split('/')
    if pairSplit[0] == "BCH":
        pairSplit[0] = "BCHABC"

    pairElement = pairSplit[0] + pairSplit[1] + '@depth' + str(orderbookDepth)
    pairList.append(pairElement)
    pairBinanceNameMapping[pairElement] = pair

while True:
    try:
        bm = BinanceSocketManager(client)
        bm.start_multiplex_socket(pairList, process_message)
        bm.start()
        time.sleep(restartPeriodSeconds)
        bm.close()
    except Exception as error:
        logger.error("Error restarting Binance Socket Manager: " + type(error).__name__ + " " + str(error.args))
        metrics.putError()
