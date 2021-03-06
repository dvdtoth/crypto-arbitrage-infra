from datetime import datetime
import boto3
import time
import sys

#session = boto3.Session(profile_name='crypto')
#cw = session.client('cloudwatch')

class CWMetrics:
    

    def __init__(self, exchange):

        self.count_interval = 5
        self.exchange = exchange

        self.metric_data = []
        self.last_append_time = 0
        self.count_samples = 0
        self.cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
        #self.cloudwatch = cw

    def millisec(self):
        return datetime.fromtimestamp(int(round(time.time()))).isoformat()

    def putCMC(self, timestamp):

        data = [{
                    'MetricName': 'CMC_INGEST',
                    'Timestamp': datetime.fromtimestamp(timestamp/1000).isoformat(),
                    'Unit': 'Count',
                    'Value': 1
                }]
        #response = self.cloudwatch.put_metric_data(Namespace='TEST/CMC', MetricData=data)
        return
    
    def putCMCError(self):

        data = [{
                    'MetricName': 'CMC_ERROR',
                    'Timestamp': self.millisec(),
                    'Unit': 'Count',
                    'Value': 1
                }]
        #response = self.cloudwatch.put_metric_data(Namespace='TEST/CMC', MetricData=data)
        return


    def putError(self):

        error_data = [{
                    'MetricName': 'ORDERBOOK_ERROR',
                    'Dimensions': [
                        {
                            'Name': 'Exchange',
                            'Value': self.exchange
                        }
                    ],
                    'Timestamp': self.millisec(),
                    'Unit': 'Count',
                    'Value': 1
                }]
        #response = self.cloudwatch.put_metric_data(Namespace='TEST/ORDERBOOK', MetricData=error_data)
        return

    def put(self, timestamp):

        # count samples for 5 second
        if (int(time.time()) - self.count_interval) < self.last_append_time:
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
            self.last_append_time = int(time.time())
        # Send batches of 20
        if len(self.metric_data) == 20:
            response = self.cloudwatch.put_metric_data(Namespace='TEST/ORDERBOOK', MetricData=self.metric_data)
            self.metric_data = []