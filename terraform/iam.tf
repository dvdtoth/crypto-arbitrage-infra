/* Define IAM roles and policies for orderbook consumption
   IAM hierarchy:
   policy_document -> policy -> attach -> role 
   Architecture:
   producer -> kinesis-stream -> consumer
*/

resource "aws_iam_role" "producer_role" {
  name = "orderbook-poller"
  path = "/"
  description = "Poller EC2 role"
  assume_role_policy = "${data.aws_iam_policy_document.producer_assume_role_policy.json}"
}

resource "aws_iam_role" "consumer_role" {
  name = "orderbook-analyser"
  path = "/"
  description = "Analyser EC2 role"
  assume_role_policy = "${data.aws_iam_policy_document.consumer_assume_role_policy.json}"
}

data "aws_iam_policy_document" "producer_assume_role_policy" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "consumer_assume_role_policy" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "producer_policy" {
  statement {
    actions = [
      "kinesis:PutRecord",
      "kinesis:PutRecords",
    ]

    resources = [
      "${aws_kinesis_stream.kinesis.arn}",
    ]
  }
}

data "aws_iam_policy_document" "consumer_policy" {
  statement {
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeLimits",
      "kinesis:GetRecords",
      "kinesis:GetShardIterator",
    ]

    resources = [
      "${aws_kinesis_stream.kinesis.arn}",
    ]
  }
}

resource "aws_iam_policy" "producer_policy" {
  name = "kinesis-producer-policy"
  description = "Policy for writing to kinesis"
  policy = "${data.aws_iam_policy_document.producer_policy.json}"
}


resource "aws_iam_policy" "consumer_policy" {
  name = "kinesis-consumer-policy"
  description = "Policy for reading from kinesis"
  policy = "${data.aws_iam_policy_document.consumer_policy.json}"
}

resource "aws_iam_role_policy_attachment" "attach_consumer" {
  role = "${aws_iam_role.consumer_role.name}"
  policy_arn = "${aws_iam_policy.consumer_policy.arn}"
}

resource "aws_iam_role_policy_attachment" "attach_producer" {
  role = "${aws_iam_role.producer_role.name}"
  policy_arn = "${aws_iam_policy.producer_policy.arn}"
}
