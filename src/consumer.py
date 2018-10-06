#!/usr/bin/env python

# POC example for consuming stream from Kinesis

import boto3
import time

# For local development use profile from ~/.aws/credentials
session = boto3.Session(profile_name='crypto')
kinesis = session.client('kinesis', region_name='eu-west-1')

# On AWS assume role
# kinesis = boto3.client('kinesis', region_name='eu-west-1')

stream = 'orderbook-stream'
# See https://docs.aws.amazon.com/kinesis/latest/APIReference/API_GetShardIterator.html#API_GetShardIterator_RequestSyntax

iterator_type = 'LATEST'
timestamp = 0

stream_description = kinesis.describe_stream(StreamName=stream)
shard_id = stream_description['StreamDescription']['Shards'][0]['ShardId']
shard_iterator = kinesis.get_shard_iterator(
    StreamName=stream, ShardId=shard_id, ShardIteratorType=iterator_type, Timestamp=timestamp)

iterator = shard_iterator['ShardIterator']
response = kinesis.get_records(ShardIterator=iterator, Limit=2)

while 'NextShardIterator' in response:
    response = kinesis.get_records(
        ShardIterator=response['NextShardIterator'], Limit=10000)
    print(response)

    # AWS Kinesis limit is 5 requests/second/shard, run at 250ms to stay on the safe side
    # Multiple consumer clusters should adjust this accordingly
    # See limits: https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html
    time.sleep(0.25)
