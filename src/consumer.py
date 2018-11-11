#!/usr/bin/env python

# POC for consuming stream from Kafka

import time
import os
import json
from kafka import KafkaConsumer

topic = 'orderbook'

kafka_server = os.environ['KAFKA_SERVER']
kafka_consumer = KafkaConsumer(topic, group_id='my-group', bootstrap_servers=kafka_server)
consumer = KafkaConsumer(bootstrap_servers=kafka_server, auto_offset_reset='latest', value_deserializer=lambda m: json.loads(m.decode('utf-8')))
consumer.subscribe([topic])
for msg in consumer:
    #  print(msg)
    data = json.loads(msg.value)
    print(data['exchange'])