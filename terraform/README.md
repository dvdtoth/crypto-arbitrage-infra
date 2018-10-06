#☣  CryptoArbitrage terraform

This plan creates the following:
- Kinesis stream
- IAM roles and policies for kinesis producer and consumer

##Architecture
exchange poller (producers) -> kinesis-stream -> orderbook analyser (consumers)

##☝ Prerequisites
AWS profile named "crypto" with keys set up in your local ~/aws/credentials
Eg:

```
[crypto]
aws_access_key_id=YOURKEY
aws_secret_access_key=YOURSECRET
```

##Usage

`brew install terraform`

Create:
`terraform init`
`terraform apply -var-file="test.tfvars"`

Review any changes:
`terraform plan -var-file="test.tfvars"`

Destroy:
`terraform destroy`
