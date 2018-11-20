# Orderbook Poller

Includes two microservices:
1, A variable sized proxy mesh
2, Poller containers producing to a Kafka stream

AWS resources are configured in code via terraform, see terraform/README.md

## High-level architecture

![alt text](poller-decoupling.png)
