resource "aws_kinesis_stream" "kinesis" {
  name = "orderbook-stream"
  shard_count = "${var.shard}"
  retention_period = "${var.retention}"
  tags {
    Environment = "test"
  }
}
