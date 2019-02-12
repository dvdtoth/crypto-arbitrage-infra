import asyncio
import websockets
import json
from logger import logger
import sys
from kafka import KafkaProducer
import yaml
import time
from CWMetrics import CWMetrics

# Parse config
with open(sys.argv[1], 'r') as config_file:
    config = yaml.load(config_file)

kafka_producer = KafkaProducer(bootstrap_servers=config['kafka']['address'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

metrics = CWMetrics(config['exchange']['name'])

async def sfoxWebSocket(symbols):
    async with websockets.connect('wss://ws.sfox.com/ws') as ws:
        subscribeMsg = {
            "type": "subscribe",
            "feeds": list(map(lambda symbol:'orderbook.sfox.' + symbol, symbols))
        }
        await ws.send(json.dumps(subscribeMsg))
        resp = await ws.recv()

        try:
            msg = json.loads(resp)
            if msg["type"] != "success":
                logger.error("Subscribtion to SFOX unsuccessful, response type=" + msg["type"])
                metrics.putError(payload['timestamp'])
                return
        except Exception as error:
            logger.error("Failed to subscribe to SFOX web socket: " + type(error).__name__ + " " + str(error.args))
            metrics.putError(payload['timestamp'])

        async for message in ws:
            try:
                msg = json.loads(message)
                symbol = msg['recipient'].split('.')[2].upper()
                symbol = symbol[0:3]+"/"+symbol[3:]
                payload = {}
                payload['exchange'] = "sfox"
                payload['symbol'] = symbol
                payload['data'] = {}
                payload['data']['asks'] = list(map(lambda entry:entry[0:2], msg['payload']['asks']))
                payload['data']['bids'] = list(map(lambda entry:entry[0:2], msg['payload']['bids']))
                payload['timestamp'] = msg['timestamp']/1e6
                
                p = json.dumps(payload, separators=(',', ':'))
                kafka_producer.send(config['kafka']['topic'], p)

                logger.info("Received " + symbol + " prices from SFOX")
                metrics.put(payload['timestamp'])

            except Exception as error:
                logger.warn("Error while parsing SFOX websocket data: " + type(error).__name__ + " " + str(error.args))
                metrics.putError(payload['timestamp'])

asyncio.get_event_loop().run_until_complete(sfoxWebSocket(symbols=config['exchange']['symbols'],))