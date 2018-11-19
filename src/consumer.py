#!/usr/bin/env python

# POC for consuming stream from Kafka

import time
import os
import json
from kafka import KafkaConsumer
import logging 
logging.basicConfig(level=logging.DEBUG)

topic = 'orderbook'

kafka_server = "kafka.cryptoindex.me:9092"
kafka_consumer = KafkaConsumer(topic, group_id='asd', bootstrap_servers=kafka_server)
consumer = KafkaConsumer(bootstrap_servers=kafka_server, enable_auto_commit=False, auto_offset_reset='latest', value_deserializer=lambda m: json.loads(m.decode('utf-8')))
consumer.subscribe([topic])
for msg in consumer:
     print(msg)
    # data = json.loads(msg.value)
    # print(data['exchange'])