from datetime import datetime
import boto3
import time
import sys

#session = boto3.Session(profile_name='crypto')
#cw = session.client('cloudwatch')

class CWMetrics:

    def __init__(self, exchange):

        self.count_interval = 1
        self.exchange = exchange

        self.metric_data = []
        self.last_put_time = 0
        self.count_samples = 0
        self.cloudwatch = boto3.client('cloudwatch')
        #self.cloudwatch = cw

    def put(self, timestamp):

        # count samples for 1 second
        if (int(time.time()) - self.count_interval) < self.last_put_time:
            self.count_samples += 1
        else:
            self.metric_data.append({
                    'MetricName': 'ORDERBOOK_INGEST',
                    'Dimensions': [
                        {
                            'Name': 'Exchange',
                            'Value': self.exchange
                        }
                    ],
                    'Timestamp': datetime.fromtimestamp(timestamp/1000).isoformat(),
                    'Unit': 'Count',
                    'Value': self.count_samples
                })
            self.count_samples = 0
            self.last_put_time = int(time.time())
        # Send batches of 20
        if len(self.metric_data) == 20:
#            print("SENDING BATCH")
 #           print(self.metric_data)
            response = self.cloudwatch.put_metric_data(Namespace='TEST/ORDERBOOK', MetricData=self.metric_data)
            self.metric_data = []
            self.last_put_time = int(time.time())

        # print('SIZE IS:')
        # print(sys.getsizeof(self.metric_data))
        # # Put batch when we reached 150 metrics or 30 seconds
        # if  len(self.metric_data) == 20 or (int(time.time()) - self.count_interval) > self.last_put_time:
        #     print('READY')
        #     print(self.metric_data)
        #     response = self.cloudwatch.put_metric_data(Namespace='TEST/ORDERBOOK', MetricData=self.metric_data)
        #     self.last_put_time = int(time.time())
        #     self.metric_data = []